"""Ticket field enrichment services and external feature point providers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from aica.config import ServerConfig
from aica.models import TicketSummaryFields
from aica.server_api import ChattodoServerClient, ChattodoServerError
from aica.text_sanitize import sanitize_text


@dataclass(frozen=True)
class FeaturePointResult:
    value: str = ""
    matched: bool = False
    provider_name: str = ""
    raw_status: str = ""
    error_message: str = ""


class FeaturePointProvider(Protocol):
    def resolve(self, *, issue_product: str, problem_desc: str) -> FeaturePointResult:
        """Return a normalized feature point result for the given ticket context."""


class NullFeaturePointProvider:
    def resolve(self, *, issue_product: str, problem_desc: str) -> FeaturePointResult:
        return FeaturePointResult()


class ChattodoFeaturePointProvider:
    def __init__(self, config: ServerConfig) -> None:
        self._config = config

    def resolve(self, *, issue_product: str, problem_desc: str) -> FeaturePointResult:
        try:
            value = ChattodoServerClient.from_config(self._config).match_feature_point(
                product_line=issue_product,
                desc=problem_desc,
            )
        except ChattodoServerError as exc:
            return FeaturePointResult(
                provider_name="chattodo",
                raw_status="request_failed",
                error_message=str(exc),
            )
        return FeaturePointResult(
            value=value,
            matched=bool(value),
            provider_name="chattodo",
            raw_status="ok",
        )


def build_feature_point_provider(*, server_config: ServerConfig | None = None) -> FeaturePointProvider:
    if server_config is not None and bool(getattr(server_config, "enabled", False)):
        return ChattodoFeaturePointProvider(server_config)
    return NullFeaturePointProvider()


@dataclass
class EnrichmentOutcome:
    summary_fields: TicketSummaryFields
    errors: list[str]


@dataclass(frozen=True)
class RootCauseResult:
    description: str = ""
    category: str = ""
    error_message: str = ""


class RootCauseProvider(Protocol):
    def generate(self, *, problem_desc: str, conclusion: str) -> RootCauseResult:
        """Return root cause description and category for a ticket context."""


class NullRootCauseProvider:
    def generate(self, *, problem_desc: str, conclusion: str) -> RootCauseResult:
        return RootCauseResult()


class ChattodoRootCauseProvider:
    def __init__(self, config: ServerConfig) -> None:
        self._config = config

    def generate(self, *, problem_desc: str, conclusion: str) -> RootCauseResult:
        try:
            payload = ChattodoServerClient.from_config(self._config).generate_root_cause(
                task_desc=problem_desc,
                answer=conclusion,
            )
        except ChattodoServerError as exc:
            return RootCauseResult(error_message=str(exc))
        return RootCauseResult(
            description=sanitize_text(payload.get("root_cause_description")).strip(),
            category=sanitize_text(payload.get("root_cause_category")).strip(),
        )


def build_root_cause_provider(*, server_config: ServerConfig | None = None) -> RootCauseProvider:
    if server_config is not None and bool(getattr(server_config, "enabled", False)):
        return ChattodoRootCauseProvider(server_config)
    return NullRootCauseProvider()


@dataclass(frozen=True)
class TicketEnrichmentJob:
    todo_id: str
    previous_fields: TicketSummaryFields
    current_fields: TicketSummaryFields
    previous_problem_desc: str
    current_problem_desc: str
    previous_conclusion: str
    current_conclusion: str


class TicketEnrichmentService:
    def __init__(
        self,
        *,
        feature_point_provider: FeaturePointProvider | None = None,
        root_cause_provider: RootCauseProvider | None = None,
    ) -> None:
        self._feature_point_provider = feature_point_provider or NullFeaturePointProvider()
        self._root_cause_provider = root_cause_provider or NullRootCauseProvider()

    def enrich_for_update(
        self,
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
        previous_conclusion: str,
        current_conclusion: str,
    ) -> EnrichmentOutcome:
        fields = TicketSummaryFields.from_dict(current_fields.to_dict())
        errors: list[str] = []

        if self._should_refresh_feature_point(
            previous_fields=previous_fields,
            current_fields=fields,
            previous_problem_desc=previous_problem_desc,
            current_problem_desc=current_problem_desc,
        ):
            result = self._feature_point_provider.resolve(
                issue_product=fields.issue_product,
                problem_desc=current_problem_desc,
            )
            if result.value:
                fields.feature_point = result.value
                fields.feature_point_source = "auto"
            elif result.error_message:
                errors.append(f"功能点生成失败: {result.error_message}")

        generated_root_cause: RootCauseResult | None = None
        if self._should_refresh_root_cause_desc(
            previous_fields=previous_fields,
            current_fields=fields,
            previous_problem_desc=previous_problem_desc,
            current_problem_desc=current_problem_desc,
            previous_conclusion=previous_conclusion,
            current_conclusion=current_conclusion,
        ):
            generated_root_cause = self._generate_root_cause(
                problem_desc=current_problem_desc,
                conclusion=current_conclusion,
            )
            if generated_root_cause.description:
                fields.root_cause_desc = generated_root_cause.description
                fields.root_cause_desc_source = "auto"
            if generated_root_cause.category:
                fields.root_cause = generated_root_cause.category
                fields.root_cause_source = "auto"
            if generated_root_cause.description or generated_root_cause.category:
                pass
            elif generated_root_cause.error_message:
                errors.append(f"根因生成失败: {generated_root_cause.error_message}")
            else:
                errors.append("根因描述生成失败")

        if self._should_refresh_root_cause(
            previous_fields=previous_fields,
            current_fields=fields,
            previous_problem_desc=previous_problem_desc,
            current_problem_desc=current_problem_desc,
            previous_conclusion=previous_conclusion,
            current_conclusion=current_conclusion,
        ):
            if generated_root_cause is None:
                generated_root_cause = self._generate_root_cause(
                    problem_desc=current_problem_desc,
                    conclusion=current_conclusion,
                )
                if generated_root_cause.description and not fields.root_cause_desc:
                    fields.root_cause_desc = generated_root_cause.description
                    fields.root_cause_desc_source = "auto"
            if generated_root_cause.category:
                fields.root_cause = generated_root_cause.category
                fields.root_cause_source = "auto"

        return EnrichmentOutcome(summary_fields=fields, errors=errors)

    @staticmethod
    def _should_refresh_feature_point(
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
    ) -> bool:
        if not current_fields.issue_product.strip() or not current_problem_desc.strip():
            return False
        if not current_fields.feature_point.strip():
            return True
        if current_fields.feature_point_source != "auto":
            return False
        return (
            sanitize_text(previous_fields.product_line) != sanitize_text(current_fields.product_line)
            or sanitize_text(previous_problem_desc) != sanitize_text(current_problem_desc)
        )

    @staticmethod
    def _should_refresh_root_cause_desc(
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
        previous_conclusion: str,
        current_conclusion: str,
    ) -> bool:
        if not current_problem_desc.strip() or not current_conclusion.strip():
            return False
        if sanitize_text(previous_conclusion) != sanitize_text(current_conclusion):
            return True
        if not current_fields.root_cause_desc.strip():
            return True
        if current_fields.root_cause_desc_source != "auto":
            return False
        return (
            sanitize_text(previous_problem_desc) != sanitize_text(current_problem_desc)
            or sanitize_text(previous_conclusion) != sanitize_text(current_conclusion)
            or sanitize_text(previous_fields.root_cause_desc) != sanitize_text(current_fields.root_cause_desc)
        )

    @staticmethod
    def _should_refresh_root_cause(
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
        previous_conclusion: str,
        current_conclusion: str,
    ) -> bool:
        if not current_problem_desc.strip() or not current_conclusion.strip():
            return False
        if sanitize_text(previous_conclusion) != sanitize_text(current_conclusion):
            return True
        if not current_fields.root_cause.strip():
            return True
        if current_fields.root_cause_source != "auto":
            return False
        return (
            sanitize_text(previous_problem_desc) != sanitize_text(current_problem_desc)
            or sanitize_text(previous_conclusion) != sanitize_text(current_conclusion)
            or sanitize_text(previous_fields.root_cause_desc) != sanitize_text(current_fields.root_cause_desc)
            or sanitize_text(previous_fields.root_cause) != sanitize_text(current_fields.root_cause)
        )

    def _generate_root_cause(self, *, problem_desc: str, conclusion: str) -> RootCauseResult:
        generated = self._root_cause_provider.generate(
            problem_desc=problem_desc,
            conclusion=conclusion,
        )
        if generated.description or generated.category or generated.error_message:
            return generated
        return RootCauseResult(error_message="根因生成服务未配置")

def build_ticket_enrichment_job(*, previous_todo, current_todo) -> TicketEnrichmentJob:
    return TicketEnrichmentJob(
        todo_id=sanitize_text(getattr(current_todo, "id", "")),
        previous_fields=TicketSummaryFields.from_dict(getattr(previous_todo, "summary_fields").to_dict()),
        current_fields=TicketSummaryFields.from_dict(getattr(current_todo, "summary_fields").to_dict()),
        previous_problem_desc=sanitize_text(getattr(previous_todo, "current_summary", "")),
        current_problem_desc=sanitize_text(getattr(current_todo, "current_summary", "")),
        previous_conclusion=sanitize_text(getattr(getattr(previous_todo, "conclusion", None), "content", "")),
        current_conclusion=sanitize_text(getattr(getattr(current_todo, "conclusion", None), "content", "")),
    )


def is_ticket_enrichment_job_still_current(todo, job: TicketEnrichmentJob) -> bool:
    if sanitize_text(getattr(todo, "id", "")) != sanitize_text(job.todo_id):
        return False
    current_fields = getattr(todo, "summary_fields", TicketSummaryFields())
    current_product_line = sanitize_text(getattr(current_fields, "product_line", ""))
    return (
        sanitize_text(getattr(todo, "current_summary", "")) == sanitize_text(job.current_problem_desc)
        and sanitize_text(getattr(getattr(todo, "conclusion", None), "content", "")) == sanitize_text(job.current_conclusion)
        and current_product_line == sanitize_text(job.current_fields.product_line)
    )


def merge_async_enrichment_fields(
    *,
    current_fields: TicketSummaryFields,
    enriched_fields: TicketSummaryFields,
    conclusion_changed: bool = False,
) -> TicketSummaryFields:
    merged = TicketSummaryFields.from_dict(current_fields.to_dict())
    if merged.feature_point_source != "manual":
        merged.feature_point = enriched_fields.feature_point
        merged.feature_point_source = enriched_fields.feature_point_source
    if conclusion_changed or merged.root_cause_desc_source != "manual":
        merged.root_cause_desc = enriched_fields.root_cause_desc
        merged.root_cause_desc_source = enriched_fields.root_cause_desc_source
    if conclusion_changed or (merged.root_cause_source != "manual" and merged.root_cause_desc_source != "manual"):
        merged.root_cause = enriched_fields.root_cause
        merged.root_cause_source = enriched_fields.root_cause_source
    return merged


def summarize_enrichment_errors(errors: list[str]) -> str:
    messages: list[str] = []
    seen: set[str] = set()
    for item in errors:
        normalized = sanitize_text(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        messages.append(normalized)
    return "；".join(messages)


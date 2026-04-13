"""Ticket field enrichment services and external feature point providers."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol

import requests

from aica.config import FeaturePointProviderConfig
from aica.llm.service import LLMService
from aica.llm.types import Message
from aica.models import TicketSummaryFields
from aica.text_sanitize import sanitize_text


ROOT_CAUSE_OPTIONS: tuple[str, ...] = (
    "需求理解偏差",
    "产品设计缺陷",
    "配置错误",
    "数据问题",
    "权限问题",
    "环境问题",
    "接口/依赖异常",
    "代码缺陷",
    "操作不当",
    "待确认",
)


@dataclass(frozen=True)
class FeaturePointResult:
    value: str = ""
    matched: bool = False
    provider_name: str = ""
    raw_status: str = ""
    error_message: str = ""


class FeaturePointProvider(Protocol):
    def resolve(self, *, product_line: str, problem_desc: str) -> FeaturePointResult:
        """Return a normalized feature point result for the given ticket context."""


class NullFeaturePointProvider:
    def resolve(self, *, product_line: str, problem_desc: str) -> FeaturePointResult:
        return FeaturePointResult()


class HttpFeaturePointProvider:
    def __init__(self, config: FeaturePointProviderConfig) -> None:
        self._base_url = str(config.base_url or "").strip()
        self._api_key = str(config.api_key or "").strip()
        self._timeout_seconds = max(1, int(config.timeout_seconds))

    def resolve(self, *, product_line: str, problem_desc: str) -> FeaturePointResult:
        if not self._base_url:
            return FeaturePointResult(error_message="feature point provider not configured")

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["X-API-Key"] = self._api_key

        payload = {
            "product_line": sanitize_text(product_line),
            "problem_desc": sanitize_text(problem_desc),
        }
        try:
            response = requests.post(
                self._base_url,
                json=payload,
                headers=headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return FeaturePointResult(
                provider_name="http",
                raw_status="request_failed",
                error_message=str(exc),
            )

        try:
            body = response.json()
        except ValueError:
            return FeaturePointResult(
                provider_name="http",
                raw_status="invalid_json",
                error_message="response is not valid JSON",
            )

        value = _extract_feature_point_value(body)
        return FeaturePointResult(
            value=value,
            matched=bool(value),
            provider_name="http",
            raw_status=_extract_status(body, response.status_code),
        )


def build_feature_point_provider(config: FeaturePointProviderConfig) -> FeaturePointProvider:
    if not config.enabled:
        return NullFeaturePointProvider()
    if str(config.provider or "").strip().lower() == "http":
        return HttpFeaturePointProvider(config)
    return NullFeaturePointProvider()


@dataclass
class EnrichmentOutcome:
    summary_fields: TicketSummaryFields
    errors: list[str]


class TicketEnrichmentService:
    def __init__(
        self,
        *,
        feature_point_provider: FeaturePointProvider | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self._feature_point_provider = feature_point_provider or NullFeaturePointProvider()
        self._llm_service = llm_service

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
                product_line=fields.product_line,
                problem_desc=current_problem_desc,
            )
            if result.value:
                fields.feature_point = result.value
                fields.feature_point_source = "auto"
            elif result.error_message:
                errors.append(f"功能点生成失败: {result.error_message}")

        if self._should_refresh_root_cause_desc(
            previous_fields=previous_fields,
            current_fields=fields,
            previous_problem_desc=previous_problem_desc,
            current_problem_desc=current_problem_desc,
            previous_conclusion=previous_conclusion,
            current_conclusion=current_conclusion,
        ):
            generated_desc = self._generate_root_cause_desc(
                problem_desc=current_problem_desc,
                conclusion=current_conclusion,
            )
            if generated_desc:
                fields.root_cause_desc = generated_desc
                fields.root_cause_desc_source = "auto"
            elif self._llm_service is not None:
                errors.append("根因描述生成失败")

        if self._should_refresh_root_cause(
            previous_fields=previous_fields,
            current_fields=fields,
            previous_problem_desc=previous_problem_desc,
            current_problem_desc=current_problem_desc,
            previous_conclusion=previous_conclusion,
            current_conclusion=current_conclusion,
        ):
            generated_root_cause = self._classify_root_cause(
                problem_desc=current_problem_desc,
                conclusion=current_conclusion,
                root_cause_desc=fields.root_cause_desc,
            )
            if generated_root_cause:
                fields.root_cause = generated_root_cause
                fields.root_cause_source = "auto"
            elif self._llm_service is not None:
                errors.append("问题根因生成失败")

        return EnrichmentOutcome(summary_fields=fields, errors=errors)

    @staticmethod
    def _should_refresh_feature_point(
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
    ) -> bool:
        if not current_fields.product_line.strip() or not current_problem_desc.strip():
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

    def _generate_root_cause_desc(self, *, problem_desc: str, conclusion: str) -> str:
        if self._llm_service is None:
            return ""
        prompt = (
            "请根据问题描述和当前结论，总结一句简洁的根因描述。"
            "只输出根因描述本身，不要输出标题、编号、解释。"
        )
        try:
            result = self._llm_service.run_task(
                "analysis",
                messages=[
                    Message(role="system", content=prompt),
                    Message(
                        role="user",
                        content=f"问题描述：{problem_desc}\n当前结论：{conclusion}",
                    ),
                ],
                temperature=0.1,
            )
        except Exception:  # noqa: BLE001
            return ""
        return _normalize_llm_text(result, limit=120)

    def _classify_root_cause(
        self,
        *,
        problem_desc: str,
        conclusion: str,
        root_cause_desc: str,
    ) -> str:
        if self._llm_service is None:
            return ""
        options = "、".join(ROOT_CAUSE_OPTIONS)
        prompt = (
            "请从给定枚举中选择一个最贴切的问题根因分类。"
            f"可选值：{options}。"
            "只输出枚举值本身，不要补充解释。"
        )
        try:
            result = self._llm_service.run_task(
                "analysis",
                messages=[
                    Message(role="system", content=prompt),
                    Message(
                        role="user",
                        content=(
                            f"问题描述：{problem_desc}\n"
                            f"当前结论：{conclusion}\n"
                            f"根因描述：{root_cause_desc}"
                        ),
                    ),
                ],
                temperature=0.0,
            )
        except Exception:  # noqa: BLE001
            return ""
        normalized = _normalize_llm_text(result, limit=30)
        return _match_root_cause_option(normalized)


def _extract_feature_point_value(payload: object) -> str:
    if isinstance(payload, dict):
        direct = sanitize_text(payload.get("feature_point") or payload.get("featurePoint"))
        if direct:
            return direct
        data = payload.get("data")
        if isinstance(data, dict):
            nested = sanitize_text(data.get("feature_point") or data.get("featurePoint"))
            if nested:
                return nested
        candidates = payload.get("candidates")
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict):
                    candidate = sanitize_text(item.get("feature_point") or item.get("featurePoint") or item.get("name"))
                else:
                    candidate = sanitize_text(item)
                if candidate:
                    return candidate
    if isinstance(payload, list):
        for item in payload:
            candidate = _extract_feature_point_value(item)
            if candidate:
                return candidate
    return ""


def _extract_status(payload: object, status_code: int) -> str:
    if isinstance(payload, dict):
        value = sanitize_text(payload.get("status") or payload.get("code") or payload.get("message"))
        if value:
            return value
    return str(status_code)


def _normalize_llm_text(value: str, *, limit: int) -> str:
    text = sanitize_text(value).strip()
    if text.startswith("```"):
        text = text.strip("`")
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            text = sanitize_text(parsed.get("result") or parsed.get("value") or "")
    text = text.splitlines()[0].strip() if text else ""
    text = text.lstrip("-0123456789.、:： ").strip()
    return text[:limit]


def _match_root_cause_option(value: str) -> str:
    if value in ROOT_CAUSE_OPTIONS:
        return value
    for option in ROOT_CAUSE_OPTIONS:
        if option in value or value in option:
            return option
    return "待确认" if value else ""

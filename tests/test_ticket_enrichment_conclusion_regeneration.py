from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.ticket_enrichment import ROOT_CAUSE_OPTIONS, TicketEnrichmentService, merge_async_enrichment_fields


class _SequentialLLMService:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, object]] = []

    def run_task(self, task_name: str, *, messages, temperature: float = 0.2, **_kwargs) -> str:  # noqa: ANN001
        self.calls.append(
            {
                "task_name": task_name,
                "messages": list(messages),
                "temperature": temperature,
            }
        )
        if not self._responses:
            raise AssertionError("unexpected llm call")
        return self._responses.pop(0)


def test_conclusion_change_regenerates_root_cause_fields_even_if_previous_values_were_manual() -> None:
    service = TicketEnrichmentService(
        llm_service=_SequentialLLMService(["new root cause desc", ROOT_CAUSE_OPTIONS[0]])
    )

    outcome = service.enrich_for_update(
        previous_fields=TicketSummaryFields(
            product_line="product",
            root_cause_desc="manual desc",
            root_cause_desc_source="manual",
            root_cause="manual cause",
            root_cause_source="manual",
        ),
        current_fields=TicketSummaryFields(
            product_line="product",
            root_cause_desc="manual desc",
            root_cause_desc_source="manual",
            root_cause="manual cause",
            root_cause_source="manual",
        ),
        previous_problem_desc="problem desc",
        current_problem_desc="problem desc",
        previous_conclusion="old conclusion",
        current_conclusion="new conclusion",
    )

    assert outcome.summary_fields.root_cause_desc == "new root cause desc"
    assert outcome.summary_fields.root_cause_desc_source == "auto"
    assert outcome.summary_fields.root_cause == ROOT_CAUSE_OPTIONS[0]
    assert outcome.summary_fields.root_cause_source == "auto"


def test_async_merge_overrides_manual_root_cause_fields_when_conclusion_changed() -> None:
    current_fields = TicketSummaryFields(
        product_line="product",
        feature_point="manual feature point",
        feature_point_source="manual",
        root_cause_desc="manual desc",
        root_cause_desc_source="manual",
        root_cause="manual cause",
        root_cause_source="manual",
    )
    enriched_fields = TicketSummaryFields(
        product_line="product",
        feature_point="auto feature point",
        feature_point_source="auto",
        root_cause_desc="auto desc",
        root_cause_desc_source="auto",
        root_cause="auto cause",
        root_cause_source="auto",
    )

    merged = merge_async_enrichment_fields(
        current_fields=current_fields,
        enriched_fields=enriched_fields,
        conclusion_changed=True,
    )

    assert merged.feature_point == "manual feature point"
    assert merged.feature_point_source == "manual"
    assert merged.root_cause_desc == "auto desc"
    assert merged.root_cause_desc_source == "auto"
    assert merged.root_cause == "auto cause"
    assert merged.root_cause_source == "auto"

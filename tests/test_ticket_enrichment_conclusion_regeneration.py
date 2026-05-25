from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.ticket_enrichment import RootCauseResult, TicketEnrichmentService, merge_async_enrichment_fields


class _RootCauseProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(self, *, problem_desc: str, conclusion: str) -> RootCauseResult:
        self.calls.append({"problem_desc": problem_desc, "conclusion": conclusion})
        return RootCauseResult(description="new root cause desc", category="环境问题/服务器宕机")


def test_conclusion_change_regenerates_root_cause_fields_even_if_previous_values_were_manual() -> None:
    provider = _RootCauseProvider()
    service = TicketEnrichmentService(root_cause_provider=provider)

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

    assert provider.calls == [{"problem_desc": "problem desc", "conclusion": "new conclusion"}]
    assert outcome.summary_fields.root_cause_desc == "new root cause desc"
    assert outcome.summary_fields.root_cause_desc_source == "auto"
    assert outcome.summary_fields.root_cause == "环境问题/服务器宕机"
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

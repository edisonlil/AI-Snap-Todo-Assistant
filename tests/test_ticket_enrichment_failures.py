from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.ticket_enrichment import TicketEnrichmentService, summarize_enrichment_errors


def test_enrich_for_update_reports_root_cause_failures_when_llm_is_missing() -> None:
    service = TicketEnrichmentService(llm_service=None)

    outcome = service.enrich_for_update(
        previous_fields=TicketSummaryFields(product_line="product"),
        current_fields=TicketSummaryFields(product_line="product"),
        previous_problem_desc="",
        current_problem_desc="user report",
        previous_conclusion="",
        current_conclusion="config missing",
    )

    assert outcome.summary_fields.root_cause_desc == ""
    assert outcome.summary_fields.root_cause == ""
    assert len(outcome.errors) == 2


def test_summarize_enrichment_errors_deduplicates_messages() -> None:
    message = summarize_enrichment_errors(
        [
            "根因描述生成失败",
            "问题根因生成失败",
            "根因描述生成失败",
            "",
        ]
    )

    assert message == "根因描述生成失败；问题根因生成失败"

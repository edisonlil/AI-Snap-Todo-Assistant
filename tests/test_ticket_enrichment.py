from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.ticket_enrichment import (
    build_ticket_enrichment_job,
    is_ticket_enrichment_job_still_current,
    merge_async_enrichment_fields,
)
from aica.todo_models import TodoConclusion, TodoItem


def _build_todo(
    *,
    todo_id: str = "todo-1",
    current_summary: str = "现象描述",
    product_line: str = "产品线A",
    conclusion: str = "定位到配置缺失",
    feature_point: str = "",
    feature_point_source: str = "",
    root_cause_desc: str = "",
    root_cause_desc_source: str = "",
    root_cause: str = "",
    root_cause_source: str = "",
) -> TodoItem:
    return TodoItem(
        id=todo_id,
        title="测试待办",
        current_summary=current_summary,
        summary_fields=TicketSummaryFields(
            product_line=product_line,
            feature_point=feature_point,
            feature_point_source=feature_point_source,
            root_cause_desc=root_cause_desc,
            root_cause_desc_source=root_cause_desc_source,
            root_cause=root_cause,
            root_cause_source=root_cause_source,
        ),
        conclusion=TodoConclusion(content=conclusion),
        timeline=[],
    )


def test_ticket_enrichment_job_detects_stale_saved_context() -> None:
    previous = _build_todo(current_summary="旧描述", conclusion="")
    current = _build_todo(current_summary="新描述", conclusion="新结论", product_line="产品线B")
    job = build_ticket_enrichment_job(previous_todo=previous, current_todo=current)

    assert is_ticket_enrichment_job_still_current(current, job) is True

    changed_summary = _build_todo(current_summary="又改了描述", conclusion="新结论", product_line="产品线B")
    assert is_ticket_enrichment_job_still_current(changed_summary, job) is False

    changed_conclusion = _build_todo(current_summary="新描述", conclusion="又改了结论", product_line="产品线B")
    assert is_ticket_enrichment_job_still_current(changed_conclusion, job) is False

    changed_product_line = _build_todo(current_summary="新描述", conclusion="新结论", product_line="产品线C")
    assert is_ticket_enrichment_job_still_current(changed_product_line, job) is False


def test_merge_async_enrichment_fields_preserves_manual_overrides() -> None:
    current_fields = TicketSummaryFields(
        product_line="产品线A",
        feature_point="手动功能点",
        feature_point_source="manual",
        root_cause_desc="手动根因描述",
        root_cause_desc_source="manual",
        root_cause="手动根因分类",
        root_cause_source="manual",
    )
    enriched_fields = TicketSummaryFields(
        product_line="产品线A",
        feature_point="自动功能点",
        feature_point_source="auto",
        root_cause_desc="自动根因描述",
        root_cause_desc_source="auto",
        root_cause="自动根因分类",
        root_cause_source="auto",
    )

    merged = merge_async_enrichment_fields(
        current_fields=current_fields,
        enriched_fields=enriched_fields,
    )

    assert merged.feature_point == "手动功能点"
    assert merged.feature_point_source == "manual"
    assert merged.root_cause_desc == "手动根因描述"
    assert merged.root_cause_desc_source == "manual"
    assert merged.root_cause == "手动根因分类"
    assert merged.root_cause_source == "manual"


def test_merge_async_enrichment_fields_applies_auto_values_when_fields_are_not_manual() -> None:
    current_fields = TicketSummaryFields(
        product_line="产品线A",
        feature_point="",
        feature_point_source="",
        root_cause_desc="",
        root_cause_desc_source="",
        root_cause="",
        root_cause_source="",
    )
    enriched_fields = TicketSummaryFields(
        product_line="产品线A",
        feature_point="自动功能点",
        feature_point_source="auto",
        root_cause_desc="自动根因描述",
        root_cause_desc_source="auto",
        root_cause="自动根因分类",
        root_cause_source="auto",
    )

    merged = merge_async_enrichment_fields(
        current_fields=current_fields,
        enriched_fields=enriched_fields,
    )

    assert merged.feature_point == "自动功能点"
    assert merged.feature_point_source == "auto"
    assert merged.root_cause_desc == "自动根因描述"
    assert merged.root_cause_desc_source == "auto"
    assert merged.root_cause == "自动根因分类"
    assert merged.root_cause_source == "auto"

"""Adapters from shared context-summary results to log-analysis models."""
from __future__ import annotations

from ..context_summary.models import ContextSummaryPoint, build_context_summary_request_for_todo
from ..context_summary.service import ContextSummaryService
from .models import InvestigationContextSummary, LogAnalysisCommand
from ..todo.models import TodoItem
from ..text_sanitize import sanitize_text


def summarize_investigation_context(
    todo: TodoItem,
    parsed_command: LogAnalysisCommand,
    *,
    summary_service: ContextSummaryService | None = None,
) -> InvestigationContextSummary:
    service = summary_service or ContextSummaryService()
    summary_result = service.summarize(
        build_context_summary_request_for_todo(
            todo,
            summary_goal="log_analysis_context",
            description=sanitize_text(todo.current_summary).strip() or sanitize_text(todo.title).strip(),
            extra_context={
                "trad_id": parsed_command.trad_id,
                "request_id": parsed_command.request_id,
                "focus_terms": list(parsed_command.focus_terms),
            },
            max_items=12,
            max_chars=2200,
        )
    )
    actions = _select_points(summary_result.key_points, "action", limit=5)
    facts = _select_points(summary_result.key_points, "fact", limit=5)
    suspects = _select_points(summary_result.key_points, "suspect", limit=5)
    fallback_points = _select_points(summary_result.key_points, "finding", limit=5)
    current_focus = list(summary_result.next_focus)
    if parsed_command.trad_id and f"tradId={parsed_command.trad_id}" not in current_focus:
        current_focus.insert(0, f"tradId={parsed_command.trad_id}")
    if parsed_command.request_id and f"request_id={parsed_command.request_id}" not in current_focus:
        insert_at = 1 if current_focus and current_focus[0].startswith("tradId=") else 0
        current_focus.insert(insert_at, f"request_id={parsed_command.request_id}")
    for item in parsed_command.focus_terms:
        normalized = sanitize_text(item).strip()
        if normalized and normalized not in current_focus:
            current_focus.append(normalized)

    return InvestigationContextSummary(
        problem_summary=summary_result.problem_brief or sanitize_text(todo.current_summary).strip() or sanitize_text(todo.title).strip(),
        actions_taken=actions or fallback_points[:2],
        confirmed_facts=facts or fallback_points[:3],
        suspected_causes=suspects,
        open_questions=list(summary_result.open_questions),
        current_focus=current_focus[:6],
    )


def _select_points(points: list[ContextSummaryPoint], category: str, *, limit: int) -> list[str]:
    result: list[str] = []
    for item in points:
        if sanitize_text(item.category).strip() != category:
            continue
        text = sanitize_text(item.text).strip()
        if text:
            result.append(text)
        if len(result) >= limit:
            break
    return result

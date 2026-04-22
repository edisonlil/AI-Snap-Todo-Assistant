"""Helpers for keeping Todo conclusions and conclusion timeline cards in sync."""
from __future__ import annotations

from .text_sanitize import sanitize_text
from .todo_models import TimelineEvent, TodoConclusion

_CONCLUSION_KIND = "conclusion"
_CONCLUSION_SCENARIO = "结论更新"
_CLEARED_CONCLUSION_TEXT = "结论已清空"


def build_conclusion_timeline_content(
    content: str,
    attachment_names: list[str],
) -> str:
    normalized_content = sanitize_text(content).strip() or _CLEARED_CONCLUSION_TEXT
    normalized_attachment_names = [
        sanitize_text(name).strip()
        for name in attachment_names
        if sanitize_text(name).strip()
    ]
    suffix = f"\n附件: {', '.join(normalized_attachment_names[:5])}" if normalized_attachment_names else ""
    return f"{normalized_content}{suffix}".strip()


def sync_conclusion_timeline(
    timeline: list[TimelineEvent],
    conclusion: TodoConclusion,
) -> list[TimelineEvent]:
    remaining: list[TimelineEvent] = []
    existing_event: TimelineEvent | None = None
    for event in timeline:
        if str(event.kind or "").strip() == _CONCLUSION_KIND:
            if existing_event is None:
                existing_event = event
            continue
        remaining.append(event)

    attachment_names = [attachment.name for attachment in conclusion.attachments if attachment.name]
    has_meaningful_conclusion = bool(
        sanitize_text(conclusion.content).strip() or attachment_names
    )
    if not has_meaningful_conclusion and existing_event is None:
        return list(timeline)

    timestamp = (
        sanitize_text(conclusion.updated_at)
        or (existing_event.created_at if existing_event is not None else "")
        or (existing_event.timestamp if existing_event is not None else "")
    )
    conclusion_event = TimelineEvent(
        id=existing_event.id if existing_event is not None else "",
        timestamp=timestamp,
        created_at=(existing_event.created_at if existing_event is not None else timestamp),
        kind=_CONCLUSION_KIND,
        scenario=_CONCLUSION_SCENARIO,
        content=build_conclusion_timeline_content(conclusion.content, attachment_names),
        attachments=[],
    )
    return remaining + [conclusion_event]

"""Helpers that bridge SQLite rows and existing Todo domain models."""
from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from aica.models import (
    EvidenceItem,
    TicketSnapshot,
    TicketSummaryFields,
    UNKNOWN_TEXT,
    merge_evidence_items,
    merge_timeline_with_evidence,
)
from aica.text_sanitize import sanitize_text
from aica.todo_models import (
    TimelineAttachment,
    TimelineEvent,
    TodoItem,
    TodoProjectLink,
    TodoStatus,
)


def now_iso() -> str:
    return datetime.now().isoformat()


def sanitize_string_dict(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in payload.items():
        text_key = sanitize_text(key)
        if not text_key:
            continue
        normalized[text_key] = sanitize_text(value)
    return normalized


def parse_json_object(raw_value: Any) -> dict[str, Any]:
    if isinstance(raw_value, dict):
        return raw_value
    text = str(raw_value or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def normalize_group_alias(alias_name: str) -> str:
    cleaned = sanitize_text(alias_name)
    if not cleaned:
        return ""
    return re.sub(r"\s+", " ", cleaned).strip().casefold()


def build_summary_fields(
    *,
    group_name: str,
    environment: str,
    ticket_type: str,
    project_snapshot: dict[str, str] | None = None,
) -> TicketSummaryFields:
    fields = TicketSummaryFields(
        group_name=group_name,
        environment=environment,
        product_line="",
        ticket_type=ticket_type,
    )
    product_line = sanitize_text((project_snapshot or {}).get("product_line", ""))
    fields.product_line = product_line or UNKNOWN_TEXT
    return fields


def build_project_link(payload: dict[str, Any] | None) -> TodoProjectLink:
    return TodoProjectLink.from_dict(payload or {})


def build_todo_item(
    *,
    todo_row: dict[str, Any],
    timeline_rows: list[dict[str, Any]],
    attachment_rows: list[dict[str, Any]],
    project_link_row: dict[str, Any] | None = None,
) -> TodoItem:
    grouped_attachments: dict[str, list[TimelineAttachment]] = defaultdict(list)
    for row in attachment_rows:
        event_id = sanitize_text(row.get("event_id", ""))
        if not event_id:
            continue
        grouped_attachments[event_id].append(
            TimelineAttachment(
                id=str(row.get("id", str(uuid.uuid4()))),
                name=row.get("name", ""),
                path=row.get("path", ""),
                size_bytes=row.get("size_bytes", 0),
            )
        )

    project_link = build_project_link(project_link_row)
    summary_fields = build_summary_fields(
        group_name=str(todo_row.get("group_name", "")),
        environment=str(todo_row.get("environment", "")),
        ticket_type=str(todo_row.get("ticket_type", "")),
        project_snapshot=project_link.project_snapshot,
    )

    timeline = [
        TimelineEvent(
            id=str(row.get("id", str(uuid.uuid4()))),
            timestamp=str(row.get("timestamp", now_iso())),
            kind=str(row.get("kind", "analysis")),
            scenario=str(row.get("scenario", "")),
            content=str(row.get("content", "")),
            attachments=grouped_attachments.get(str(row.get("id", "")), []),
        )
        for row in timeline_rows
    ]
    return TodoItem(
        id=str(todo_row.get("id", str(uuid.uuid4()))),
        title=str(todo_row.get("title", "")),
        summary_fields=summary_fields,
        current_summary=str(todo_row.get("current_summary", "")),
        created_at=str(todo_row.get("created_at", now_iso())),
        updated_at=str(todo_row.get("updated_at", now_iso())),
        status=str(todo_row.get("status", TodoStatus.OPEN)),
        timeline=timeline,
        project_link=project_link,
    )


def deserialize_legacy_todo_item(payload: dict[str, Any]) -> TodoItem:
    summary_fields = TicketSummaryFields.from_dict(payload.get("summary_fields"))
    if payload.get("summary") and not payload.get("current_summary"):
        summary_fields, current_summary = migrate_legacy_summary(
            payload.get("summary", ""),
            summary_fields,
        )
    else:
        current_summary = str(payload.get("current_summary", ""))

    timeline_payload = payload.get("timeline", [])
    timeline = [
        deserialize_legacy_timeline_event(event)
        for event in timeline_payload
        if isinstance(event, dict)
    ]
    return TodoItem(
        id=str(payload.get("id", str(uuid.uuid4()))),
        title=str(payload.get("title", "")),
        summary_fields=summary_fields,
        current_summary=current_summary,
        created_at=str(payload.get("created_at", now_iso())),
        updated_at=str(payload.get("updated_at", now_iso())),
        status=str(payload.get("status", TodoStatus.OPEN)),
        timeline=timeline,
        project_link=TodoProjectLink.from_dict(payload.get("project_link")),
    )


def deserialize_legacy_timeline_event(payload: dict[str, Any]) -> TimelineEvent:
    content = str(
        payload.get("content")
        or payload.get("summary")
        or payload.get("detail")
        or ""
    ).strip()
    evidence_items = deserialize_legacy_evidence_items(payload.get("evidence_items", []))
    attachments = deserialize_legacy_timeline_attachments(payload.get("attachments", []))
    return TimelineEvent(
        id=str(payload.get("id", str(uuid.uuid4()))),
        timestamp=str(payload.get("timestamp", now_iso())),
        kind=str(payload.get("kind", "analysis")),
        scenario=str(payload.get("scenario", "")),
        content=merge_timeline_with_evidence(content, evidence_items),
        attachments=attachments,
    )


def deserialize_legacy_timeline_attachments(payload: Any) -> list[TimelineAttachment]:
    if not isinstance(payload, list):
        return []
    attachments: list[TimelineAttachment] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        attachment = TimelineAttachment(
            id=str(item.get("id", str(uuid.uuid4()))),
            name=item.get("name", ""),
            path=item.get("path", ""),
            size_bytes=item.get("size_bytes", item.get("sizeBytes", 0)),
        )
        if attachment.name and attachment.path:
            attachments.append(attachment)
    return attachments


def deserialize_legacy_evidence_items(payload: Any) -> list[EvidenceItem]:
    if not isinstance(payload, list):
        return []
    evidence_items: list[EvidenceItem] = []
    for item in payload:
        evidence = EvidenceItem.from_dict(item)
        if evidence is not None:
            evidence_items.append(evidence)
    return merge_evidence_items(evidence_items)


def migrate_legacy_summary(
    legacy_summary: str,
    existing_fields: TicketSummaryFields,
) -> tuple[TicketSummaryFields, str]:
    cleaned = str(legacy_summary or "").strip()
    if not cleaned:
        return existing_fields, ""
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            snapshot = TicketSnapshot.from_dict(payload)
            return snapshot.fields, snapshot.current_summary
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return existing_fields, cleaned

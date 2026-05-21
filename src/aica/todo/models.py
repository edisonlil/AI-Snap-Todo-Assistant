"""Todo domain models shared by repositories, events, and UI."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from ..models import TicketSummaryFields
from ..text_sanitize import sanitize_text


class TodoStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class TimelineAttachment:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    path: str = ""
    size_bytes: int = 0

    def __post_init__(self) -> None:
        self.id = sanitize_text(self.id) or str(uuid.uuid4())
        self.name = sanitize_text(self.name)
        self.path = sanitize_text(self.path)
        try:
            self.size_bytes = max(0, int(self.size_bytes))
        except (TypeError, ValueError):
            self.size_bytes = 0


@dataclass
class TimelineEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_now_iso)
    kind: str = "analysis"
    scenario: str = ""
    event_type: str = "default"
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = ""
    content: str = ""
    attachments: list[TimelineAttachment] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        self.id = sanitize_text(self.id) or str(uuid.uuid4())
        self.timestamp = sanitize_text(self.timestamp) or _now_iso()
        self.kind = sanitize_text(self.kind) or "analysis"
        self.scenario = sanitize_text(self.scenario)
        self.event_type = sanitize_text(self.event_type) or "default"
        self.payload = dict(self.payload) if isinstance(self.payload, dict) else {}
        self.status = sanitize_text(self.status)
        self.content = sanitize_text(self.content)
        self.created_at = sanitize_text(self.created_at) or self.timestamp or _now_iso()


@dataclass
class TodoConclusion:
    content: str = ""
    updated_at: str = ""
    attachments: list[TimelineAttachment] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.content = sanitize_text(self.content)
        self.updated_at = sanitize_text(self.updated_at)
        self.attachments = [
            attachment
            if isinstance(attachment, TimelineAttachment)
            else TimelineAttachment(**dict(attachment or {}))
            for attachment in list(self.attachments or [])
        ]


@dataclass
class TodoProjectLink:
    todo_id: str = ""
    project_id: str = ""
    match_status: str = ""
    match_reason: str = ""
    matched_group_name: str = ""
    matched_alias: str = ""
    project_snapshot: dict[str, str] = field(default_factory=dict)
    matched_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        self.todo_id = sanitize_text(self.todo_id)
        self.project_id = sanitize_text(self.project_id)
        self.match_status = sanitize_text(self.match_status)
        self.match_reason = sanitize_text(self.match_reason)
        self.matched_group_name = sanitize_text(self.matched_group_name)
        self.matched_alias = sanitize_text(self.matched_alias)
        self.project_snapshot = {
            sanitize_text(key): sanitize_text(value)
            for key, value in dict(self.project_snapshot or {}).items()
            if sanitize_text(key)
        }
        self.matched_at = sanitize_text(self.matched_at)
        self.updated_at = sanitize_text(self.updated_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "todo_id": self.todo_id,
            "project_id": self.project_id,
            "match_status": self.match_status,
            "match_reason": self.match_reason,
            "matched_group_name": self.matched_group_name,
            "matched_alias": self.matched_alias,
            "project_snapshot": dict(self.project_snapshot),
            "matched_at": self.matched_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "TodoProjectLink":
        payload = payload or {}
        return cls(
            todo_id=payload.get("todo_id", ""),
            project_id=payload.get("project_id", ""),
            match_status=payload.get("match_status", ""),
            match_reason=payload.get("match_reason", ""),
            matched_group_name=payload.get("matched_group_name", ""),
            matched_alias=payload.get("matched_alias", ""),
            project_snapshot=payload.get("project_snapshot", {}),
            matched_at=payload.get("matched_at", ""),
            updated_at=payload.get("updated_at", ""),
        )


@dataclass
class TodoItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "鏈垎绫讳换鍔?"
    summary_fields: TicketSummaryFields = field(default_factory=TicketSummaryFields)
    current_summary: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    completed_at: str = ""
    status: str = TodoStatus.OPEN
    timeline: list[TimelineEvent] = field(default_factory=list)
    conclusion: TodoConclusion = field(default_factory=TodoConclusion)
    project_link: TodoProjectLink = field(default_factory=TodoProjectLink)

    def __post_init__(self) -> None:
        self.id = sanitize_text(self.id) or str(uuid.uuid4())
        self.title = sanitize_text(self.title) or "鏈垎绫讳换鍔?"
        self.current_summary = sanitize_text(self.current_summary)
        self.created_at = sanitize_text(self.created_at) or _now_iso()
        self.updated_at = sanitize_text(self.updated_at) or _now_iso()
        self.completed_at = sanitize_text(self.completed_at)
        self.status = sanitize_text(self.status) or TodoStatus.OPEN
        if not isinstance(self.conclusion, TodoConclusion):
            self.conclusion = TodoConclusion(**dict(self.conclusion or {}))
        if not isinstance(self.project_link, TodoProjectLink):
            self.project_link = TodoProjectLink.from_dict(self.project_link)

    @property
    def timeline_count(self) -> int:
        return len(self.timeline)

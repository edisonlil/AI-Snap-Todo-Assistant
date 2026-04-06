"""Todo domain models and local persistence."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from .models import TicketSnapshot, TicketSummaryFields


class TodoStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class TimelineEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_now_iso)
    kind: str = "analysis"
    scenario: str = ""
    content: str = ""


@dataclass
class TodoItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "未分类任务"
    summary_fields: TicketSummaryFields = field(default_factory=TicketSummaryFields)
    current_summary: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    status: str = TodoStatus.OPEN
    timeline: list[TimelineEvent] = field(default_factory=list)

    @property
    def timeline_count(self) -> int:
        return len(self.timeline)


class TodoStore:
    """Persists active todos to a local JSON file."""

    def __init__(self, store_path: str | None = None):
        if store_path is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".aica")
            store_path = os.path.join(data_dir, "todos.json")
        self._path = store_path

    @property
    def path(self) -> str:
        return self._path

    def list_active_todos(self) -> list[TodoItem]:
        items = [item for item in self._load_items() if item.status == TodoStatus.OPEN]
        return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def get_todo(self, todo_id: str) -> TodoItem | None:
        for item in self._load_items():
            if item.id == todo_id:
                return item
        return None

    def create_todo_from_analysis(self, snapshot: TicketSnapshot, scenario: str) -> TodoItem:
        todo = TodoItem(
            title=snapshot.title,
            summary_fields=snapshot.fields,
            current_summary=snapshot.current_summary,
            timeline=[
                TimelineEvent(
                    scenario=scenario,
                    content=snapshot.timeline_entry,
                )
            ],
        )
        items = self._load_items()
        items.append(todo)
        self._save_items(items)
        return todo

    def append_analysis_to_todo(
        self,
        todo_id: str,
        snapshot: TicketSnapshot,
        scenario: str,
    ) -> TodoItem | None:
        items = self._load_items()
        for item in items:
            if item.id != todo_id:
                continue
            item.timeline.append(
                TimelineEvent(
                    scenario=scenario,
                    content=snapshot.timeline_entry,
                )
            )
            item.title = snapshot.title or item.title
            item.summary_fields = snapshot.fields
            item.current_summary = snapshot.current_summary
            item.updated_at = _now_iso()
            self._save_items(items)
            return item
        return None

    def complete_todo(self, todo_id: str) -> bool:
        items = self._load_items()
        updated = False
        for item in items:
            if item.id != todo_id:
                continue
            item.status = TodoStatus.DONE
            item.updated_at = _now_iso()
            updated = True
            break
        if updated:
            self._save_items(items)
        return updated

    def delete_todo(self, todo_id: str) -> bool:
        items = self._load_items()
        remaining = [item for item in items if item.id != todo_id]
        if len(remaining) == len(items):
            return False
        self._save_items(remaining)
        return True

    def update_todo(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        current_summary: str | None = None,
        summary_fields: TicketSummaryFields | None = None,
        timeline: list[TimelineEvent] | None = None,
    ) -> TodoItem | None:
        items = self._load_items()
        for item in items:
            if item.id != todo_id:
                continue
            if title is not None:
                item.title = title.strip() or item.title
            if current_summary is not None:
                item.current_summary = current_summary.strip()
            if summary_fields is not None:
                item.summary_fields = summary_fields
            if timeline is not None:
                item.timeline = timeline
            item.updated_at = _now_iso()
            self._save_items(items)
            return item
        return None

    def _load_items(self) -> list[TodoItem]:
        if not os.path.exists(self._path):
            return []
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, list):
                return []
            return [self._deserialize_item(item) for item in payload if isinstance(item, dict)]
        except Exception:
            return []

    def _save_items(self, items: list[TodoItem]) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        payload = [self._serialize_item(item) for item in items]
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _serialize_item(self, item: TodoItem) -> dict[str, Any]:
        payload = asdict(item)
        payload["summary_fields"] = item.summary_fields.to_dict()
        return payload

    def _deserialize_item(self, payload: dict[str, Any]) -> TodoItem:
        summary_fields = TicketSummaryFields.from_dict(payload.get("summary_fields"))
        if payload.get("summary") and not payload.get("current_summary"):
            summary_fields, current_summary = self._migrate_legacy_summary(
                payload.get("summary", ""),
                summary_fields,
            )
        else:
            current_summary = str(payload.get("current_summary", ""))

        timeline_payload = payload.get("timeline", [])
        timeline = [self._deserialize_timeline_event(event) for event in timeline_payload if isinstance(event, dict)]
        return TodoItem(
            id=str(payload.get("id", str(uuid.uuid4()))),
            title=str(payload.get("title", "未分类任务")),
            summary_fields=summary_fields,
            current_summary=current_summary,
            created_at=str(payload.get("created_at", _now_iso())),
            updated_at=str(payload.get("updated_at", _now_iso())),
            status=str(payload.get("status", TodoStatus.OPEN)),
            timeline=timeline,
        )

    def _deserialize_timeline_event(self, payload: dict[str, Any]) -> TimelineEvent:
        content = str(
            payload.get("content")
            or payload.get("summary")
            or payload.get("detail")
            or ""
        ).strip()
        return TimelineEvent(
            id=str(payload.get("id", str(uuid.uuid4()))),
            timestamp=str(payload.get("timestamp", _now_iso())),
            kind=str(payload.get("kind", "analysis")),
            scenario=str(payload.get("scenario", "")),
            content=content,
        )

    def _migrate_legacy_summary(
        self,
        legacy_summary: str,
        existing_fields: TicketSummaryFields,
    ) -> tuple[TicketSummaryFields, str]:
        cleaned = legacy_summary.strip()
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

"""Todo domain models and local persistence."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class TodoStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


def _now_iso() -> str:
    return datetime.now().isoformat()


def _extract_title_and_summary(analysis_text: str) -> tuple[str, str]:
    raw = analysis_text.strip()
    if not raw:
        return "[未分类]", ""

    cleaned = raw
    if cleaned.startswith("```") and cleaned.endswith("```"):
        parts = cleaned.split("\n", 1)
        cleaned = parts[1] if len(parts) > 1 else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    title = ""
    summary = raw
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            title = str(
                payload.get("task_desc")
                or payload.get("title")
                or payload.get("summary")
                or ""
            ).strip()
            summary = json.dumps(payload, ensure_ascii=False, indent=2)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    if not title:
        lines = [line.strip("-• \t") for line in raw.splitlines() if line.strip()]
        title = lines[0] if lines else "[未分类]"

    title = title[:60] or "[未分类]"
    return title, summary[:500]


@dataclass
class TimelineEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_now_iso)
    kind: str = "analysis"
    scenario: str = ""
    summary: str = ""
    detail: str = ""


@dataclass
class TodoItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "[未分类]"
    summary: str = ""
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

    def create_todo_from_analysis(self, analysis_text: str, scenario: str) -> TodoItem:
        title, summary = _extract_title_and_summary(analysis_text)
        event = TimelineEvent(
            scenario=scenario,
            summary=summary,
            detail=analysis_text,
        )
        todo = TodoItem(
            title=title,
            summary=summary,
            timeline=[event],
        )
        items = self._load_items()
        items.append(todo)
        self._save_items(items)
        return todo

    def append_analysis_to_todo(self, todo_id: str, analysis_text: str, scenario: str) -> TodoItem | None:
        items = self._load_items()
        for item in items:
            if item.id != todo_id:
                continue
            title, summary = _extract_title_and_summary(analysis_text)
            item.timeline.append(
                TimelineEvent(
                    scenario=scenario,
                    summary=summary,
                    detail=analysis_text,
                )
            )
            if title and item.title == "[未分类]":
                item.title = title
            item.summary = summary
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

    def update_todo(self, todo_id: str, *, title: str | None = None, summary: str | None = None) -> TodoItem | None:
        items = self._load_items()
        for item in items:
            if item.id != todo_id:
                continue
            if title is not None:
                item.title = title.strip() or item.title
            if summary is not None:
                item.summary = summary.strip()
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
        return asdict(item)

    def _deserialize_item(self, payload: dict[str, Any]) -> TodoItem:
        timeline_payload = payload.get("timeline", [])
        timeline = [
            TimelineEvent(**event)
            for event in timeline_payload
            if isinstance(event, dict)
        ]
        return TodoItem(
            id=str(payload.get("id", str(uuid.uuid4()))),
            title=str(payload.get("title", "[未分类]")),
            summary=str(payload.get("summary", "")),
            created_at=str(payload.get("created_at", _now_iso())),
            updated_at=str(payload.get("updated_at", _now_iso())),
            status=str(payload.get("status", TodoStatus.OPEN)),
            timeline=timeline,
        )

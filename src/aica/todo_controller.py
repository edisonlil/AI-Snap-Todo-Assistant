"""Application-facing coordination for Todo state and workflows."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .models import (
    TicketSnapshot,
    TicketSummaryFields,
    merge_summary_fields_for_append,
)
from .todo_store import TimelineEvent, TodoItem, TodoStore


@dataclass(frozen=True)
class SaveAnalysisResult:
    action: str
    todo: TodoItem


class TodoController:
    """Coordinates Todo workflow state between UI and persistence."""

    def __init__(self, store: TodoStore):
        self._store = store
        self._selected_todo_id: str | None = None
        self._detail_todo_id: str | None = None

    @property
    def selected_todo_id(self) -> str | None:
        return self._selected_todo_id

    @property
    def detail_todo_id(self) -> str | None:
        return self._detail_todo_id

    def get_active_todos(self) -> list[TodoItem]:
        return self._store.list_active_todos()

    def get_todo_detail(self, todo_id: str) -> TodoItem | None:
        todo = self._store.get_todo(todo_id)
        if todo is not None:
            self._detail_todo_id = todo_id
        return todo

    def get_selected_todo(self) -> TodoItem | None:
        if self._selected_todo_id is None:
            return None
        return self._store.get_todo(self._selected_todo_id)

    def close_detail(self) -> None:
        self._detail_todo_id = None

    def toggle_selected_todo(self, todo_id: str) -> str | None:
        self._selected_todo_id = None if self._selected_todo_id == todo_id else todo_id
        return self._selected_todo_id

    def clear_selected_todo(self) -> None:
        self._selected_todo_id = None

    @staticmethod
    def _normalize_timeline_text(text: str) -> str:
        return re.sub(r"[\s\u3000，。；：、,.!?！？“”\"'‘’（）()【】\[\]<>《》]+", "", str(text or ""))

    @classmethod
    def _extract_incremental_timeline_entry(cls, todo: TodoItem, timeline_entry: str) -> str:
        original = str(timeline_entry or "").strip()
        if not original:
            return original

        existing_sources = [todo.current_summary] + [event.content for event in todo.timeline[-5:]]
        existing_text = "".join(
            cls._normalize_timeline_text(source)
            for source in existing_sources
            if str(source or "").strip()
        )
        clauses = [
            clause.strip(" ，。；：、,.!?！？")
            for clause in re.split(r"[，。；：、,.!?！？\n]+", original)
            if clause.strip(" ，。；：、,.!?！？")
        ]

        first_new_index: int | None = None
        for index, clause in enumerate(clauses):
            normalized_clause = cls._normalize_timeline_text(clause)
            if len(normalized_clause) < 2:
                continue
            if not existing_text or normalized_clause not in existing_text:
                first_new_index = index
                break

        incremental_clauses: list[str] = []
        seen: set[str] = set()
        start_index = first_new_index if first_new_index is not None else 0
        for clause in clauses[start_index:]:
            normalized_clause = cls._normalize_timeline_text(clause)
            if len(normalized_clause) < 2 or normalized_clause in seen:
                continue
            seen.add(normalized_clause)
            if first_new_index is not None and normalized_clause in existing_text:
                continue
            incremental_clauses.append(clause)

        if incremental_clauses and first_new_index is not None:
            return "，".join(incremental_clauses)

        trimmed = original
        for source in existing_sources:
            source_text = str(source or "").strip()
            if source_text and trimmed.startswith(source_text):
                trimmed = trimmed[len(source_text):].strip(" ，。；：、,.!?！？")
        return trimmed or original

    @classmethod
    def _normalize_snapshot_for_append(cls, todo: TodoItem, snapshot: TicketSnapshot) -> TicketSnapshot:
        return TicketSnapshot(
            title=todo.title,
            fields=merge_summary_fields_for_append(todo.summary_fields, snapshot.fields),
            current_summary=todo.current_summary,
            timeline_entry=cls._extract_incremental_timeline_entry(todo, snapshot.timeline_entry),
            evidence_items=[],
        )

    def save_analysis_result(self, snapshot: TicketSnapshot, scenario: str) -> SaveAnalysisResult:
        if self._selected_todo_id:
            selected_todo = self.get_selected_todo()
            if selected_todo is not None:
                snapshot = self._normalize_snapshot_for_append(selected_todo, snapshot)
            todo = self._store.append_analysis_to_todo(
                self._selected_todo_id,
                snapshot,
                scenario,
            )
            if todo is not None:
                self._selected_todo_id = None
                return SaveAnalysisResult(action="append", todo=todo)

        todo = self._store.create_todo_from_analysis(snapshot, scenario)
        return SaveAnalysisResult(action="create", todo=todo)

    def complete_todo(self, todo_id: str) -> bool:
        completed = self._store.complete_todo(todo_id)
        if not completed:
            return False

        if self._selected_todo_id == todo_id:
            self._selected_todo_id = None
        if self._detail_todo_id == todo_id:
            self._detail_todo_id = None
        return True

    def delete_todo(self, todo_id: str) -> bool:
        deleted = self._store.delete_todo(todo_id)
        if not deleted:
            return False
        if self._selected_todo_id == todo_id:
            self._selected_todo_id = None
        if self._detail_todo_id == todo_id:
            self._detail_todo_id = None
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
        return self._store.update_todo(
            todo_id,
            title=title,
            current_summary=current_summary,
            summary_fields=summary_fields,
            timeline=timeline,
        )

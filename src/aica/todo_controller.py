"""Application-facing coordination for Todo state and workflows."""
from __future__ import annotations

from dataclasses import dataclass

from .models import TicketSnapshot, TicketSummaryFields
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

    def save_analysis_result(self, snapshot: TicketSnapshot, scenario: str) -> SaveAnalysisResult:
        if self._selected_todo_id:
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

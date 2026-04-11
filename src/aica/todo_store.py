"""Todo storage compatibility wrapper."""
from __future__ import annotations

from .models import TicketSnapshot, TicketSummaryFields
from .storage.sqlite.repositories import SQLiteTodoRepository
from .todo_models import TimelineAttachment, TimelineEvent, TodoItem, TodoProjectLink, TodoStatus


class TodoStore:
    """Compatibility wrapper backed by the default SQLite Todo repository."""

    def __init__(self, store_path: str | None = None):
        self._repository = SQLiteTodoRepository(store_path)

    @property
    def path(self) -> str:
        return self._repository.path

    def list_active_todos(self) -> list[TodoItem]:
        return self._repository.list_active_todos()

    def get_todo(self, todo_id: str) -> TodoItem | None:
        return self._repository.get_todo(todo_id)

    def create_todo_from_analysis(self, snapshot: TicketSnapshot, scenario: str) -> TodoItem:
        return self._repository.create_todo_from_analysis(snapshot, scenario)

    def append_analysis_to_todo(
        self,
        todo_id: str,
        snapshot: TicketSnapshot,
        scenario: str,
    ) -> TodoItem | None:
        return self._repository.append_analysis_to_todo(todo_id, snapshot, scenario)

    def complete_todo(self, todo_id: str) -> bool:
        return self._repository.complete_todo(todo_id)

    def delete_todo(self, todo_id: str) -> bool:
        return self._repository.delete_todo(todo_id)

    def update_todo(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        current_summary: str | None = None,
        summary_fields: TicketSummaryFields | None = None,
        timeline: list[TimelineEvent] | None = None,
    ) -> TodoItem | None:
        return self._repository.update_todo(
            todo_id,
            title=title,
            current_summary=current_summary,
            summary_fields=summary_fields,
            timeline=timeline,
        )

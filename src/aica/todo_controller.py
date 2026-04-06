"""Application-facing coordination for Todo state and workflows."""
from __future__ import annotations

from dataclasses import dataclass

from .todo_store import TodoItem, TodoStore


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

    def close_detail(self) -> None:
        self._detail_todo_id = None

    def toggle_selected_todo(self, todo_id: str) -> str | None:
        self._selected_todo_id = None if self._selected_todo_id == todo_id else todo_id
        return self._selected_todo_id

    def clear_selected_todo(self) -> None:
        self._selected_todo_id = None

    def save_analysis_result(self, result_text: str, scenario: str) -> SaveAnalysisResult:
        if self._selected_todo_id:
            todo = self._store.append_analysis_to_todo(
                self._selected_todo_id,
                result_text,
                scenario,
            )
            if todo is not None:
                self._selected_todo_id = None
                return SaveAnalysisResult(action="append", todo=todo)

        todo = self._store.create_todo_from_analysis(result_text, scenario)
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

    def update_todo(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        summary: str | None = None,
    ) -> TodoItem | None:
        return self._store.update_todo(todo_id, title=title, summary=summary)

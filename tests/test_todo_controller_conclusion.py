from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.todo.controller import TodoController
from aica.todo.models import TimelineEvent, TodoConclusion, TodoItem


class _Store:
    def __init__(self, todo: TodoItem) -> None:
        self.todo = todo

    def get_todo(self, todo_id: str) -> TodoItem | None:
        if self.todo.id != todo_id:
            return None
        return deepcopy(self.todo)

    def update_todo(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        current_summary: str | None = None,
        current_summary_attachments=None,
        summary_fields: TicketSummaryFields | None = None,
        timeline=None,
        conclusion: TodoConclusion | None = None,
    ) -> TodoItem | None:
        if self.todo.id != todo_id:
            return None
        if title is not None:
            self.todo.title = title
        if current_summary is not None:
            self.todo.current_summary = current_summary
        if current_summary_attachments is not None:
            self.todo.current_summary_attachments = current_summary_attachments
        if summary_fields is not None:
            self.todo.summary_fields = summary_fields
        if timeline is not None:
            self.todo.timeline = timeline
        if conclusion is not None:
            self.todo.conclusion = conclusion
        return deepcopy(self.todo)


def _build_todo() -> TodoItem:
    return TodoItem(
        id="todo-1",
        title="测试待办",
        current_summary="当前描述",
        summary_fields=TicketSummaryFields(product_line="产品线A"),
        conclusion=TodoConclusion(),
        timeline=[
            TimelineEvent(
                id="manual-1",
                timestamp="2026-04-22T09:00:00",
                kind="manual",
                scenario="问题跟进",
                content="先排查",
            )
        ],
    )


def test_update_todo_adds_conclusion_timeline_entry_when_conclusion_changes() -> None:
    controller = TodoController(_Store(_build_todo()))

    updated = controller.update_todo(
        "todo-1",
        conclusion=TodoConclusion(content="已定位为配置缺失", updated_at="2026-04-22T10:00:00"),
        run_enrichment=False,
    )

    assert updated is not None
    assert [event.kind for event in updated.timeline] == ["manual", "conclusion"]
    assert updated.timeline[-1].content == "已定位为配置缺失"


def test_update_todo_removes_conclusion_timeline_entry_when_conclusion_is_cleared() -> None:
    todo = _build_todo()
    todo.conclusion = TodoConclusion(content="旧结论", updated_at="2026-04-22T10:00:00")
    todo.timeline.append(
        TimelineEvent(
            id="conclusion-1",
            timestamp="2026-04-22T10:00:00",
            kind="conclusion",
            scenario="结论更新",
            content="旧结论",
        )
    )
    controller = TodoController(_Store(todo))

    updated = controller.update_todo(
        "todo-1",
        conclusion=TodoConclusion(content="", updated_at="2026-04-22T11:00:00"),
        run_enrichment=False,
    )

    assert updated is not None
    assert [event.kind for event in updated.timeline] == ["manual"]

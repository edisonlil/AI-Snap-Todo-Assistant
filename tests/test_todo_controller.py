from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.todo.controller import TodoController
from aica.todo.models import TimelineAttachment, TodoConclusion, TodoItem


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


class _FakeEnrichmentService:
    def __init__(self) -> None:
        self.calls = 0

    def enrich_for_update(self, **kwargs):
        self.calls += 1
        fields = TicketSummaryFields.from_dict(kwargs["current_fields"].to_dict())
        fields.root_cause_desc = "异步生成的根因描述"
        fields.root_cause_desc_source = "auto"
        return type("Outcome", (), {"summary_fields": fields, "errors": []})()


def _build_todo() -> TodoItem:
    return TodoItem(
        id="todo-1",
        title="测试待办",
        current_summary="当前描述",
        summary_fields=TicketSummaryFields(product_line="产品线A"),
        conclusion=TodoConclusion(content="当前结论"),
        timeline=[],
    )


def test_update_todo_can_skip_enrichment() -> None:
    service = _FakeEnrichmentService()
    controller = TodoController(_Store(_build_todo()), enrichment_service=service)

    updated = controller.update_todo(
        "todo-1",
        summary_fields=TicketSummaryFields(product_line="产品线A"),
        run_enrichment=False,
    )

    assert updated is not None
    assert service.calls == 0


def test_update_todo_runs_enrichment_by_default() -> None:
    service = _FakeEnrichmentService()
    controller = TodoController(_Store(_build_todo()), enrichment_service=service)

    updated = controller.update_todo(
        "todo-1",
        summary_fields=TicketSummaryFields(product_line="产品线A"),
    )

    assert updated is not None
    assert service.calls == 1
    assert updated.summary_fields.root_cause_desc == "异步生成的根因描述"


def test_update_todo_passes_current_summary_attachments() -> None:
    controller = TodoController(_Store(_build_todo()), enrichment_service=None)
    attachments = [TimelineAttachment(id="att-1", name="a.txt", path="/tmp/a.txt", size_bytes=1)]

    updated = controller.update_todo(
        "todo-1",
        current_summary_attachments=attachments,
        run_enrichment=False,
    )

    assert updated is not None
    assert updated.current_summary_attachments == attachments

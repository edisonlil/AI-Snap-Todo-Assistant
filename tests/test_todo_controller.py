from pathlib import Path

from aica.models import EvidenceItem, TicketSnapshot, TicketSummaryFields, UNKNOWN_TEXT
from aica.ticket_field_resolver import DEFAULT_PRODUCT_LINE, TICKET_TYPE_OPTIONS
from aica.todo_controller import TodoController
from aica.todo_store import TimelineEvent, TodoStore


def _build_controller(tmp_path: Path) -> TodoController:
    store = TodoStore(str(tmp_path / "todos.json"))
    return TodoController(store)


def _snapshot(
    title: str,
    summary: str,
    timeline: str,
    *,
    group_name: str = "group-a",
    environment: str = "prod",
    product_line: str = "line-a",
    ticket_type: str = TICKET_TYPE_OPTIONS[0],
    evidence_items: list[EvidenceItem] | None = None,
) -> TicketSnapshot:
    return TicketSnapshot(
        title=title,
        fields=TicketSummaryFields(
            group_name=group_name,
            environment=environment,
            product_line=product_line,
            ticket_type=ticket_type,
        ),
        current_summary=summary,
        timeline_entry=timeline,
        evidence_items=evidence_items or [],
    )


def test_save_analysis_creates_todo_when_nothing_selected(tmp_path: Path):
    controller = _build_controller(tmp_path)

    result = controller.save_analysis_result(
        _snapshot("upload failed", "check whether file still exists", "customer reported upload failed"),
        "todo assistant",
    )

    assert result.action == "create"
    assert result.todo.timeline_count == 1
    assert result.todo.current_summary == "check whether file still exists"
    assert controller.selected_todo_id is None


def test_save_analysis_appends_to_selected_todo_and_clears_selection(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )
    controller.toggle_selected_todo(created.todo.id)

    result = controller.save_analysis_result(
        _snapshot(
            "new title from screenshot",
            "new summary from screenshot",
            "second follow-up",
            group_name="new-group",
            environment="staging",
        ),
        "todo assistant",
    )

    assert result.action == "append"
    assert result.todo.id == created.todo.id
    assert result.todo.timeline_count == 2
    assert result.todo.title == "upload failed"
    assert result.todo.current_summary == "initial summary"
    assert result.todo.summary_fields.group_name == "group-a"
    assert result.todo.summary_fields.environment == "prod"
    assert result.todo.timeline[-1].content == "second follow-up"
    assert controller.selected_todo_id is None


def test_save_analysis_append_backfills_unknown_fields_only(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot(
            "upload failed",
            "initial summary",
            "first follow-up",
            group_name=UNKNOWN_TEXT,
            environment=UNKNOWN_TEXT,
        ),
        "todo assistant",
    )
    controller.toggle_selected_todo(created.todo.id)

    result = controller.save_analysis_result(
        _snapshot(
            "new title from screenshot",
            "new summary from screenshot",
            "second follow-up",
            group_name="recognized-group",
            environment="staging",
        ),
        "todo assistant",
    )

    assert result.action == "append"
    assert result.todo.title == "upload failed"
    assert result.todo.current_summary == "initial summary"
    assert result.todo.summary_fields.group_name == "recognized-group"
    assert result.todo.summary_fields.environment == "staging"
    assert result.todo.summary_fields.product_line == DEFAULT_PRODUCT_LINE


def test_save_analysis_append_keeps_details_in_timeline_only(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "工单跟进",
    )
    controller.toggle_selected_todo(created.todo.id)

    result = controller.save_analysis_result(
        _snapshot(
            "new title from screenshot",
            "new summary from screenshot",
            "客户补充了接口参数",
            evidence_items=[
                EvidenceItem(
                    type="request_param",
                    label="task_id",
                    value="abc123",
                    source_image_index=2,
                    scene_type="api_detail",
                )
            ],
        ),
        "参数与接口详情",
    )

    assert result.action == "append"
    assert result.todo.current_summary == "initial summary"
    assert "task_id" not in result.todo.current_summary
    assert "task_id" in result.todo.timeline[-1].content


def test_update_todo_updates_fields_and_timeline(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )

    updated = controller.update_todo(
        created.todo.id,
        title="new title",
        current_summary="new summary",
        summary_fields=TicketSummaryFields(
            group_name="new-group",
            environment="test",
            product_line="new-line",
            ticket_type=TICKET_TYPE_OPTIONS[1],
        ),
        timeline=[TimelineEvent(content="edited timeline")],
    )

    assert updated is not None
    assert updated.title == "new title"
    assert updated.current_summary == "new summary"
    assert updated.summary_fields.group_name == "new-group"
    assert updated.summary_fields.product_line == DEFAULT_PRODUCT_LINE
    assert updated.summary_fields.ticket_type == TICKET_TYPE_OPTIONS[1]


def test_delete_todo_clears_selection_and_removes_item(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("title", "summary", "timeline"),
        "todo assistant",
    )
    controller.toggle_selected_todo(created.todo.id)

    assert controller.delete_todo(created.todo.id)
    assert controller.selected_todo_id is None
    assert controller.get_active_todos() == []

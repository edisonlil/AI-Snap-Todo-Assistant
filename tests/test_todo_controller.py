from pathlib import Path

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.ticket_field_resolver import DEFAULT_PRODUCT_LINE
from aica.todo_controller import TodoController
from aica.todo_store import TimelineEvent, TodoStore


def _build_controller(tmp_path: Path) -> TodoController:
    store = TodoStore(str(tmp_path / "todos.json"))
    return TodoController(store)


def _snapshot(title: str, summary: str, timeline: str) -> TicketSnapshot:
    return TicketSnapshot(
        title=title,
        fields=TicketSummaryFields(
            group_name="客户群",
            environment="生产",
            product_line="AI-SNAP",
            ticket_type="问题排查",
        ),
        current_summary=summary,
        timeline_entry=timeline,
    )


def test_save_analysis_creates_todo_when_nothing_selected(tmp_path: Path):
    controller = _build_controller(tmp_path)

    result = controller.save_analysis_result(
        _snapshot("上传失败", "确认上传实体文件是否仍存在", "客户反馈上传失败"),
        "工单待办助手",
    )

    assert result.action == "create"
    assert result.todo.timeline_count == 1
    assert result.todo.current_summary == "确认上传实体文件是否仍存在"
    assert controller.selected_todo_id is None


def test_save_analysis_appends_to_selected_todo_and_clears_selection(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("上传失败", "初始摘要", "首条跟进"),
        "工单待办助手",
    )
    controller.toggle_selected_todo(created.todo.id)

    result = controller.save_analysis_result(
        _snapshot("上传失败", "已定位网关层", "新增跟进"),
        "工单待办助手",
    )

    assert result.action == "append"
    assert result.todo.id == created.todo.id
    assert result.todo.timeline_count == 2
    assert controller.selected_todo_id is None


def test_update_todo_updates_fields_and_timeline(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("标题", "摘要", "时间线"),
        "工单待办助手",
    )

    updated = controller.update_todo(
        created.todo.id,
        title="新标题",
        current_summary="新摘要",
        summary_fields=TicketSummaryFields(
            group_name="新群聊",
            environment="测试",
            product_line="新产品",
            ticket_type="配置咨询",
        ),
        timeline=[TimelineEvent(content="人工修改的时间线")],
    )

    assert updated is not None
    assert updated.title == "新标题"
    assert updated.current_summary == "新摘要"
    assert updated.summary_fields.group_name == "新群聊"
    assert updated.summary_fields.product_line == DEFAULT_PRODUCT_LINE
    assert updated.summary_fields.ticket_type == "咨询类"


def test_delete_todo_clears_selection_and_removes_item(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result(
        _snapshot("标题", "摘要", "时间线"),
        "工单待办助手",
    )
    controller.toggle_selected_todo(created.todo.id)

    assert controller.delete_todo(created.todo.id)
    assert controller.selected_todo_id is None
    assert controller.get_active_todos() == []

from pathlib import Path

from aica.todo_controller import TodoController
from aica.todo_store import TodoStore


def _build_controller(tmp_path: Path) -> TodoController:
    store = TodoStore(str(tmp_path / "todos.json"))
    return TodoController(store)


def test_save_analysis_creates_todo_when_nothing_selected(tmp_path: Path):
    controller = _build_controller(tmp_path)

    result = controller.save_analysis_result("客户反馈接口超时，需要排查网关日志", "工单提取")

    assert result.action == "create"
    assert result.todo.timeline_count == 1
    assert controller.selected_todo_id is None
    assert len(controller.get_active_todos()) == 1


def test_save_analysis_appends_to_selected_todo_and_clears_selection(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result("首条记录", "工单提取")
    controller.toggle_selected_todo(created.todo.id)

    result = controller.save_analysis_result("新增截图显示 500 错误", "工单提取")

    assert result.action == "append"
    assert result.todo.id == created.todo.id
    assert result.todo.timeline_count == 2
    assert controller.selected_todo_id is None


def test_toggle_selected_todo_supports_select_and_deselect(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result("待处理事项", "工单提取")

    assert controller.toggle_selected_todo(created.todo.id) == created.todo.id
    assert controller.toggle_selected_todo(created.todo.id) is None


def test_complete_todo_clears_selection_and_detail_state(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result("待完成任务", "工单提取")
    controller.toggle_selected_todo(created.todo.id)
    detail = controller.get_todo_detail(created.todo.id)

    assert detail is not None
    assert controller.complete_todo(created.todo.id)
    assert controller.selected_todo_id is None
    assert controller.detail_todo_id is None
    assert controller.get_active_todos() == []


def test_get_todo_detail_tracks_open_detail_state(tmp_path: Path):
    controller = _build_controller(tmp_path)
    created = controller.save_analysis_result("查看详情", "工单提取")

    detail = controller.get_todo_detail(created.todo.id)

    assert detail is not None
    assert controller.detail_todo_id == created.todo.id
    controller.close_detail()
    assert controller.detail_todo_id is None

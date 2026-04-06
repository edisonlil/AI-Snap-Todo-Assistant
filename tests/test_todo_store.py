from pathlib import Path

from aica.todo_store import TodoStore


def test_create_todo_from_analysis_persists_item(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))

    todo = store.create_todo_from_analysis("客户反馈接口超时，需要排查网关日志", "工单提取")

    todos = store.list_active_todos()
    assert len(todos) == 1
    assert todos[0].id == todo.id
    assert todos[0].timeline_count == 1
    assert "接口超时" in todos[0].title


def test_append_analysis_updates_existing_todo(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis("首条记录", "工单提取")

    updated = store.append_analysis_to_todo(todo.id, "新增截图显示 500 错误", "工单提取")

    assert updated is not None
    assert updated.timeline_count == 2
    assert "500" in updated.summary


def test_complete_todo_removes_item_from_active_list(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis("待完成任务", "工单提取")

    assert store.complete_todo(todo.id)
    assert store.list_active_todos() == []


def test_update_todo_persists_changes(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis("原始内容", "工单提取")

    updated = store.update_todo(todo.id, title="新标题", summary="新摘要")

    assert updated is not None
    reloaded = store.get_todo(todo.id)
    assert reloaded is not None
    assert reloaded.title == "新标题"
    assert reloaded.summary == "新摘要"

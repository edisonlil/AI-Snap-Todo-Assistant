import json
from pathlib import Path

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.ticket_field_resolver import DEFAULT_PRODUCT_LINE
from aica.todo_store import TimelineEvent, TodoStore


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


def test_create_todo_from_analysis_persists_structured_item(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))

    todo = store.create_todo_from_analysis(
        _snapshot("上传失败", "确认上传实体文件是否仍存在", "客户反馈上传实体文件失败，需要排查"),
        "工单待办助手",
    )

    todos = store.list_active_todos()
    assert len(todos) == 1
    assert todos[0].id == todo.id
    assert todos[0].title == "上传失败"
    assert todos[0].summary_fields.group_name == "客户群"
    assert todos[0].current_summary == "确认上传实体文件是否仍存在"
    assert todos[0].timeline[0].content == "客户反馈上传实体文件失败，需要排查"


def test_append_analysis_updates_existing_todo(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("上传失败", "初始摘要", "首条记录"),
        "工单待办助手",
    )

    updated = store.append_analysis_to_todo(
        todo.id,
        _snapshot("上传失败", "已定位到网关层", "新增跟进：观察到 500 错误"),
        "工单待办助手",
    )

    assert updated is not None
    assert updated.timeline_count == 2
    assert updated.current_summary == "已定位到网关层"
    assert updated.timeline[-1].content == "新增跟进：观察到 500 错误"


def test_update_todo_persists_fields_and_timeline(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("原始标题", "原始摘要", "原始时间线"),
        "工单待办助手",
    )

    updated = store.update_todo(
        todo.id,
        title="新标题",
        current_summary="新摘要",
        summary_fields=TicketSummaryFields(
            group_name="新群聊",
            environment="测试",
            product_line="新产品线",
            ticket_type="配置咨询",
        ),
        timeline=[TimelineEvent(content="人工编辑后的时间线")],
    )

    assert updated is not None
    reloaded = store.get_todo(todo.id)
    assert reloaded is not None
    assert reloaded.title == "新标题"
    assert reloaded.current_summary == "新摘要"
    assert reloaded.summary_fields.product_line == DEFAULT_PRODUCT_LINE
    assert reloaded.summary_fields.ticket_type == "咨询类"
    assert reloaded.timeline[0].content == "人工编辑后的时间线"


def test_legacy_summary_json_is_migrated(tmp_path: Path):
    path = tmp_path / "todos.json"
    legacy_payload = [
        {
            "id": "1",
            "title": "旧任务",
            "summary": json.dumps(
                {
                    "group_name": "老群聊",
                    "environment": "生产",
                    "product_line": "老产品",
                    "ticket_type": "问题排查",
                    "current_summary": "旧摘要",
                },
                ensure_ascii=False,
            ),
            "status": "open",
            "timeline": [{"summary": "旧时间线"}],
        }
    ]
    path.write_text(json.dumps(legacy_payload, ensure_ascii=False), encoding="utf-8")

    store = TodoStore(str(path))
    todo = store.get_todo("1")

    assert todo is not None
    assert todo.summary_fields.group_name == "老群聊"
    assert todo.summary_fields.product_line == DEFAULT_PRODUCT_LINE
    assert todo.summary_fields.ticket_type == "排查类"
    assert todo.current_summary == "旧摘要"
    assert todo.timeline[0].content == "旧时间线"

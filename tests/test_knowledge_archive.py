from __future__ import annotations

from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.knowledge_archive import KnowledgeArchiveEventHandler, archive_completed_todo
from aica.models import TicketSummaryFields
from aica.todo.events import TodoDomainEvent
from aica.todo.models import TimelineAttachment, TimelineEvent, TodoConclusion, TodoItem, TodoStatus


class _RecordingLLM:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[dict[str, object]] = []

    def run_task(self, task_name: str, *, messages, temperature: float = 0.2, **kwargs):  # noqa: ANN001
        self.calls.append(
            {
                "task_name": task_name,
                "messages": list(messages),
                "temperature": temperature,
                "kwargs": dict(kwargs),
            }
        )
        return self.response_text


def _build_todo(*, ticket_type: str = "排查类", summary: str = "OA系统上传Word后文字显示为粗体") -> TodoItem:
    return TodoItem(
        id="9f32d1ab-cdef-1234-5678-abcdef123456",
        title="OA系统上传Word后文字显示为粗体",
        current_summary=summary,
        status=TodoStatus.DONE,
        completed_at="2026-04-30T18:20:00",
        updated_at="2026-04-30T18:20:00",
        summary_fields=TicketSummaryFields(
            group_name="公系统升级-使用沟通群",
            environment="生产",
            product_line="WPS协作",
            ticket_type=ticket_type,
            ticket_version="",
            feature_point="OA上传Word",
            root_cause="兼容性",
            root_cause_desc="Word样式兼容处理异常",
        ),
        conclusion=TodoConclusion(content="已确认问题与Word样式兼容处理逻辑有关。", updated_at="2026-04-30T18:19:00"),
        timeline=[
            TimelineEvent(
                id="event-1",
                timestamp="2026-04-30T18:00:00",
                kind="follow_up",
                scenario="客户反馈",
                content="客户反馈上传Word后页面文字显示为粗体。",
                attachments=[
                    TimelineAttachment(
                        id="att-1",
                        name="screenshot.png",
                        path="",
                        size_bytes=128,
                    )
                ],
            )
        ],
    )


def test_archive_completed_todo_writes_solution_and_product_index() -> None:
    base_dir = Path.cwd() / ".tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = base_dir / f"knowledge-archive-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    attachment_path = temp_dir / "screenshot.png"
    attachment_path.write_bytes(b"fake-image")
    todo = _build_todo()
    todo.timeline[0].attachments[0].path = str(attachment_path)
    llm = _RecordingLLM("# Word上传后文字显示粗体处理方案\n\n## 问题结论\n\n已完成兼容处理。")

    note_path = archive_completed_todo(todo, llm_service=llm, archive_root=temp_dir)

    assert note_path is not None
    assert note_path.exists()
    assert "WPS协作" in note_path.as_posix()
    assert "未提供" in note_path.as_posix()
    assert "排查类" in note_path.as_posix()
    assert note_path.name == f"{todo.title}.md"
    assert "9f32d1ab" not in note_path.name
    assert not note_path.name.startswith("aica_")

    content = note_path.read_text(encoding="utf-8")
    assert f"\n# {todo.title}" not in content
    assert "aica_9f32d1ab" not in content
    assert "group_name:" not in content
    assert "公系统升级-使用沟通群" not in content
    assert "environment:" not in content
    assert "生产" not in content
    assert "product_line: \"WPS协作\"" in content
    assert "ticket_type: \"排查类\"" in content
    assert f"title: \"{todo.title}\"" in content
    assert "## 问题概览" in content
    assert "## 问题概览\n\n-" in content
    assert "## 基本信息" in content
    assert "## 基本信息\n\n|" in content
    assert "## 解决方案" in content
    assert "## 解决方案\n\n-" in content
    assert "## 关联证据" in content
    assert "### 证据 1：客户反馈" in content
    assert "## 时间线回顾" not in content
    assert "## 时间线图示" not in content
    assert "## 附件图示" not in content
    assert "assets/screenshot.png" in content

    copied_attachment = note_path.parent / "assets" / "screenshot.png"
    assert copied_attachment.exists()
    assert not (note_path.parent / f"{note_path.stem}_assets").exists()
    assert not (note_path.parent / "assets" / "screenshot_1.png").exists()

    index_path = temp_dir / "WPS协作" / "_wiki" / "WPS协作 Wiki 索引.md"
    index_content = index_path.read_text(encoding="utf-8")
    assert note_path.name in index_content
    assert "排查类" in index_content

    assert len(llm.calls) == 1
    user_prompt = str(llm.calls[0]["messages"][1].content)
    assert "公系统升级-使用沟通群" not in user_prompt
    assert "环境:" not in user_prompt
    assert "生产" not in user_prompt


def test_knowledge_archive_event_handler_skips_operation_todos() -> None:
    base_dir = Path.cwd() / ".tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = base_dir / f"knowledge-archive-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    todo = _build_todo(ticket_type="操作类", summary="请帮忙开通权限")
    runtime_calls: list[str] = []

    class _TodoStore:
        def get_todo(self, todo_id: str) -> TodoItem | None:
            return todo if todo_id == todo.id else None

    def _runtime_config():
        runtime_calls.append("called")
        return object()

    handler = KnowledgeArchiveEventHandler(
        todo_store=_TodoStore(),
        runtime_config_provider=_runtime_config,
        archive_root=temp_dir,
    )

    handler.handle(TodoDomainEvent.completed(todo, "工单完成"))

    assert runtime_calls == []
    assert not list(temp_dir.rglob("*.md"))

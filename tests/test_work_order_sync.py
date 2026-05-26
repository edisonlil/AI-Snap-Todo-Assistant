from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import ServerConfig  # noqa: E402
from aica.models import TicketSummaryFields  # noqa: E402
from aica.server_api import ChattodoServerError  # noqa: E402
from aica.todo.events import TodoDomainEvent  # noqa: E402
from aica.todo.models import TimelineAttachment, TimelineEvent, TodoItem, TodoProjectLink, TodoStatus  # noqa: E402
from aica.todo.work_order_sync import WorkOrderSyncEventHandler, build_work_order_payload  # noqa: E402


def _todo(*, status: str = TodoStatus.OPEN) -> TodoItem:
    return TodoItem(
        id="todo-1",
        title="上传失败",
        current_summary="客户反馈上传时报错 500",
        status=status,
        created_at="2026-05-24T00:50:00+08:00",
        updated_at="2026-05-24T01:00:00+08:00",
        summary_fields=TicketSummaryFields(
            group_name="客户支持群",
            environment="生产",
            product_line="私网文档中台",
            ticket_type="排查类",
            ach_no="ACH-001",
            ach_filled_at="2026-05-24T00:45:00+08:00",
            ticket_version="v1",
            feature_point="文档中台-上传-失败",
            root_cause="环境问题",
            root_cause_desc="上游服务超时",
        ),
        project_link=TodoProjectLink(
            todo_id="todo-1",
            match_status="manual",
            project_snapshot={
                "project_name": "广州项目",
                "task_order_no": "PJ-001",
                "product_version": "release_1",
                "project_manager": "Alice",
            },
        ),
        timeline=[
            TimelineEvent(
                id="timeline-1",
                timestamp="2026-05-24T00:55:00+08:00",
                kind="analysis",
                scenario="截图分析",
                content="建议检查服务日志",
                attachments=[
                    TimelineAttachment(
                        id="att-1",
                        name="install-log.txt",
                        path="C:/tmp/install-log.txt",
                        size_bytes=2048,
                    )
                ],
            )
        ],
    )


def test_build_work_order_payload_maps_todo_snapshot() -> None:
    event = TodoDomainEvent.created(_todo(), "工单待办助手")

    payload = build_work_order_payload(event)

    assert payload["source_system"] == "Chattodo"
    assert payload["external_id"] == "todo-1"
    assert payload["external_order_no"] == "todo-1"
    assert payload["external_filled_at"] == "2026-05-24T00:45:00+08:00"
    assert payload["ach_order_no"] == "ACH-001"
    assert payload["ach_filled_at"] == "2026-05-24T00:45:00+08:00"
    assert payload["title"] == "上传失败"
    assert payload["status"] == "in_progress"
    assert payload["project_hit_status"] == "matched"
    assert payload["project"] == {
        "task_order_no": "PJ-001",
        "display_name": "广州项目",
        "linked": True,
    }
    assert payload["chat_group"] == {"group_name": "客户支持群", "linked": True}
    assert payload["function_point"] == {
        "full_name": "文档中台-上传-失败",
        "linked": True,
    }
    assert payload["product_version"] == "release_1"
    assert payload["root_cause_description"] == "上游服务超时"
    assert payload["timeline"] == [
        {
            "external_timeline_id": "timeline-1",
            "occurred_at": "2026-05-24T00:55:00+08:00",
            "event_type": "截图分析",
            "title": "截图分析",
            "content": "建议检查服务日志",
            "source_system": "Chattodo",
            "attachments": [
                    {
                        "external_attachment_id": "att-1",
                        "file_name": "install-log.txt",
                        "file_size": 2048,
                        "content_type": "text/plain",
                        "_local_path": "C:/tmp/install-log.txt",
                    }
                ],
            }
        ]


def test_build_work_order_payload_maps_done_and_deleted_status() -> None:
    completed = build_work_order_payload(TodoDomainEvent.completed(_todo(status=TodoStatus.DONE), "完成"))
    deleted = build_work_order_payload(TodoDomainEvent.deleted(_todo(), "删除"))
    reopened = build_work_order_payload(TodoDomainEvent.reopened(_todo(), "重新打开"))

    assert completed["status"] == "completed"
    assert deleted["status"] == "cancelled"
    assert reopened["status"] == "in_progress"
    assert deleted["external_order_no"] == "todo-1"


class _BindingStore:
    def __init__(self) -> None:
        self.upserts: list[dict[str, object]] = []
        self.status_updates: list[dict[str, object]] = []

    def upsert_binding(self, todo_id, integration_id, external_id, **kwargs):  # noqa: ANN001
        self.upserts.append(
            {
                "todo_id": todo_id,
                "integration_id": integration_id,
                "external_id": external_id,
                **kwargs,
            }
        )

    def update_sync_status(self, todo_id, integration_id, **kwargs):  # noqa: ANN001
        self.status_updates.append(
            {
                "todo_id": todo_id,
                "integration_id": integration_id,
                **kwargs,
            }
        )


class _Client:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response or {
            "success": True,
            "data": {"item": {"id": 1001}},
        }
        self.error = error
        self.payloads: list[dict[str, object]] = []
        self.uploads: list[dict[str, object]] = []

    def upsert_work_order(self, payload: dict[str, object]) -> dict[str, object]:
        if self.error is not None:
            raise self.error
        self.payloads.append(payload)
        return self.response

    def upload_workbench_file(  # noqa: ANN001
        self,
        file_path,
        *,
        file_name: str = "",
        content_type: str = "",
        source_system: str = "",
        external_order_no: str = "",
        external_timeline_id: str = "",
        external_attachment_id: str = "",
    ):
        self.uploads.append(
            {
                "file_path": str(file_path),
                "file_name": file_name,
                "content_type": content_type,
                "source_system": source_system,
                "external_order_no": external_order_no,
                "external_timeline_id": external_timeline_id,
                "external_attachment_id": external_attachment_id,
            }
        )
        return {
            "success": True,
            "data": {
                "file_object_id": "file-123",
                "url": "/api/files/file-123/download",
                "preview_url": "/api/files/file-123/preview",
            },
        }


def test_work_order_sync_handler_upserts_binding() -> None:
    store = _BindingStore()
    client = _Client()
    handler = WorkOrderSyncEventHandler(
        binding_store=store,  # type: ignore[arg-type]
        config_provider=lambda: SimpleNamespace(
            server=ServerConfig(enabled=True, base_url="https://server.example.com", api_key="key")
        ),
        client_factory=lambda _config: client,
    )

    handler.handle(TodoDomainEvent.created(_todo(), "创建"))

    assert client.payloads[0]["external_order_no"] == "todo-1"
    assert store.upserts[0]["external_id"] == "1001"
    assert store.upserts[0]["sync_status"] == "ok:synced"


def test_work_order_sync_handler_uploads_local_attachments(tmp_path: Path) -> None:
    attachment_path = tmp_path / "xiezuo20260526-170105.png"
    attachment_path.write_bytes(b"png")
    todo = _todo()
    todo.timeline[0].attachments[0].name = attachment_path.name
    todo.timeline[0].attachments[0].path = str(attachment_path)
    todo.timeline[0].attachments[0].size_bytes = attachment_path.stat().st_size
    store = _BindingStore()
    client = _Client()
    handler = WorkOrderSyncEventHandler(
        binding_store=store,  # type: ignore[arg-type]
        config_provider=lambda: ServerConfig(enabled=True, base_url="https://server.example.com", api_key="key"),
        client_factory=lambda _config: client,
    )

    handler.handle(TodoDomainEvent.updated(todo, "闄勪欢", ["timeline"]))

    attachment = client.payloads[0]["timeline"][0]["attachments"][0]  # type: ignore[index]
    assert client.uploads == [
        {
            "file_path": str(attachment_path),
            "file_name": attachment_path.name,
            "content_type": "image/png",
            "source_system": "Chattodo",
            "external_order_no": "todo-1",
            "external_timeline_id": "timeline-1",
            "external_attachment_id": "att-1",
        }
    ]
    assert attachment["external_attachment_id"] == "att-1"
    assert attachment["file_object_id"] == "file-123"
    assert attachment["url"] == "/api/files/file-123/download"
    assert attachment["preview_url"] == "/api/files/file-123/preview"
    assert "_local_path" not in attachment


def test_work_order_sync_handler_skips_attachment_without_download_source() -> None:
    todo = _todo()
    todo.timeline[0].attachments[0].path = ""
    store = _BindingStore()
    client = _Client()
    handler = WorkOrderSyncEventHandler(
        binding_store=store,  # type: ignore[arg-type]
        config_provider=lambda: ServerConfig(enabled=True, base_url="https://server.example.com", api_key="key"),
        client_factory=lambda _config: client,
    )

    handler.handle(TodoDomainEvent.updated(todo, "闄勪欢", ["timeline"]))

    assert client.uploads == []
    assert "attachments" not in client.payloads[0]["timeline"][0]  # type: ignore[index]


def test_work_order_sync_handler_marks_deleted_and_failures() -> None:
    deleted_store = _BindingStore()
    deleted_client = _Client()
    deleted_handler = WorkOrderSyncEventHandler(
        binding_store=deleted_store,  # type: ignore[arg-type]
        config_provider=lambda: ServerConfig(enabled=True, base_url="https://server.example.com", api_key="key"),
        client_factory=lambda _config: deleted_client,
    )

    deleted_handler.handle(TodoDomainEvent.deleted(_todo(), "删除"))

    assert deleted_client.payloads[0]["status"] == "cancelled"
    assert deleted_store.upserts[0]["sync_status"] == "ok:cancelled"
    assert deleted_store.upserts[0]["deleted_locally"] is True

    failed_store = _BindingStore()
    failed_handler = WorkOrderSyncEventHandler(
        binding_store=failed_store,  # type: ignore[arg-type]
        config_provider=lambda: ServerConfig(enabled=True, base_url="https://server.example.com", api_key="key"),
        client_factory=lambda _config: _Client(error=ChattodoServerError("boom")),
    )

    failed_handler.handle(TodoDomainEvent.created(_todo(), "创建"))

    assert failed_store.status_updates[0]["sync_status"] == "failed:boom"

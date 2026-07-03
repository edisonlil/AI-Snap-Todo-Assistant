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
from aica.todo.work_order_sync import (  # noqa: E402
    WorkOrderSyncEventHandler,
    build_work_order_payload,
    pull_my_in_progress_work_orders,
    refresh_missing_ach_work_orders,
    sync_all_my_work_orders,
    todo_from_server_work_order,
)


def _todo(*, status: str = TodoStatus.OPEN) -> TodoItem:
    return TodoItem(
        id="todo-1",
        title="上传失败",
        current_summary="客户反馈上传时报错 500",
        current_summary_attachments=[
            TimelineAttachment(
                id="summary-att-1",
                name="screen.png",
                path="C:/tmp/screen.png",
                size_bytes=1024,
            )
        ],
        status=status,
        created_at="2026-05-24T00:50:00+08:00",
        updated_at="2026-05-24T01:00:00+08:00",
        summary_fields=TicketSummaryFields(
            group_name="客户支持群",
            environment="生产",
            product_line="私网文档中台",
            product_module="文档中台",
            issue_product="客户环境",
            ticket_type="排查类",
            reproduction_probability="偶现",
            customer_environment_code="env-prod",
            customer_environment_value="生产环境",
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
    assert payload["customer_environment"] == "生产环境"
    assert payload["reproduction_probability"] == "偶现"
    assert payload["product_module"] == "文档中台"
    assert payload["issue_product"] == "客户环境"
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
    assert payload["product_version"] == "v1"
    assert payload["root_cause_description"] == "上游服务超时"
    assert payload["attachments"] == [
        {
            "external_attachment_id": "summary-att-1",
            "file_name": "screen.png",
            "file_size": 1024,
            "content_type": "image/png",
            "_local_path": "C:/tmp/screen.png",
        }
    ]
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


class _TodoStore:
    def __init__(self, todos: list[TodoItem]) -> None:
        self.todos = list(todos)
        self.imported: list[TodoItem] = []

    def list_todos(self, *, query: str = "", status: str = "all") -> list[TodoItem]:
        normalized_status = str(status or "all").strip().lower()
        if normalized_status == "done_missing_ach":
            return [
                todo
                for todo in self.todos
                if todo.status == TodoStatus.DONE and not str(todo.summary_fields.ach_no or "").strip()
            ]
        if normalized_status == "all":
            return list(self.todos)
        return [todo for todo in self.todos if str(todo.status or "").strip().lower() == normalized_status]

    def upsert_imported_todo(self, todo: TodoItem) -> TodoItem | None:
        self.imported.append(todo)
        self.todos.append(todo)
        return todo

    def update_todo(self, todo_id: str, *, summary_fields: TicketSummaryFields) -> TodoItem | None:
        for todo in self.todos:
            if todo.id != todo_id:
                continue
            todo.summary_fields = summary_fields
            return todo
        return None


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

    def sync_my_work_orders(self, items: list[dict[str, object]]) -> dict[str, object]:
        self.payloads.extend(items)
        return {
            "success": True,
            "data": {
                "created_count": 1,
                "updated_count": 1,
                "skipped_count": 0,
                "total_count": len(items),
                "results": [
                    {"index": index, "status": "updated", "id": 1000 + index}
                    for index, _item in enumerate(items)
                ],
            },
        }

    def pull_my_in_progress_work_orders(self, **kwargs):  # noqa: ANN001
        self.payloads.append(kwargs)
        return self.response

    def get_work_order_ach_statuses(self, external_order_nos, **kwargs):  # noqa: ANN001
        self.payloads.append({"external_order_nos": list(external_order_nos), **kwargs})
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
    assert "_local_path" not in attachment


def test_work_order_sync_handler_uploads_current_summary_attachments(tmp_path: Path) -> None:
    attachment_path = tmp_path / "screen.png"
    attachment_path.write_bytes(b"png")
    todo = _todo()
    todo.current_summary_attachments[0].name = attachment_path.name
    todo.current_summary_attachments[0].path = str(attachment_path)
    todo.current_summary_attachments[0].size_bytes = attachment_path.stat().st_size
    store = _BindingStore()
    client = _Client()
    handler = WorkOrderSyncEventHandler(
        binding_store=store,  # type: ignore[arg-type]
        config_provider=lambda: ServerConfig(enabled=True, base_url="https://server.example.com", api_key="key"),
        client_factory=lambda _config: client,
    )

    handler.handle(TodoDomainEvent.updated(todo, "当前描述附件", ["current_summary_attachments"]))

    attachment = client.payloads[0]["attachments"][0]  # type: ignore[index]
    assert client.uploads[0] == {
        "file_path": str(attachment_path),
        "file_name": attachment_path.name,
        "content_type": "image/png",
        "source_system": "Chattodo",
        "external_order_no": "todo-1",
        "external_timeline_id": "",
        "external_attachment_id": "summary-att-1",
    }
    assert attachment["external_attachment_id"] == "summary-att-1"
    assert attachment["file_object_id"] == "file-123"


def test_build_work_order_payload_keeps_empty_current_summary_attachments() -> None:
    todo = _todo()
    todo.current_summary_attachments = []

    payload = build_work_order_payload(TodoDomainEvent.updated(todo, "当前描述附件清空", ["current_summary_attachments"]))

    assert payload["attachments"] == []


def test_work_order_sync_handler_clears_removed_current_summary_attachments(tmp_path: Path) -> None:
    attachment_path = tmp_path / "screen.png"
    attachment_path.write_bytes(b"png")
    todo = _todo()
    todo.current_summary_attachments[0].name = attachment_path.name
    todo.current_summary_attachments[0].path = str(attachment_path)
    todo.current_summary_attachments[0].size_bytes = attachment_path.stat().st_size
    todo.current_summary_attachments = []
    store = _BindingStore()
    client = _Client()
    handler = WorkOrderSyncEventHandler(
        binding_store=store,  # type: ignore[arg-type]
        config_provider=lambda: ServerConfig(enabled=True, base_url="https://server.example.com", api_key="key"),
        client_factory=lambda _config: client,
    )

    handler.handle(TodoDomainEvent.updated(todo, "当前描述附件移除", ["current_summary_attachments"]))

    assert client.payloads[0]["attachments"] == []
    assert client.uploads == []


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


def test_sync_all_my_work_orders_batches_and_records_bindings() -> None:
    todo = _todo()
    store = _TodoStore([todo])
    binding_store = _BindingStore()
    client = _Client()

    result = sync_all_my_work_orders(client, store, binding_store)  # type: ignore[arg-type]

    assert result.total_count == 1
    assert result.updated_count == 1
    assert client.payloads[0]["external_order_no"] == "todo-1"
    assert binding_store.upserts[0]["external_id"] == "1000"
    assert binding_store.upserts[0]["sync_status"] == "ok:updated"


def test_todo_from_server_work_order_maps_pull_payload() -> None:
    todo = todo_from_server_work_order(
        {
            "id": 102,
            "external_id": "server-local-2",
            "external_order_no": "WO-002",
            "external_filled_at": "2026-05-24T00:50:00+08:00",
            "ach_order_no": "ACH-002",
            "ach_filled_at": "2026-05-24T08:30:00+08:00",
            "title": "需要下拉的工单",
            "description": "问题描述",
            "status": "in_progress",
            "project_hit_status": "matched",
            "project_local_id": "project-local-1",
            "project_task_order_no": "PJ-24080225",
            "project_snapshot": "某客户文档中台项目",
            "group_name": "客户支持群",
            "environment": "生产环境",
            "work_order_type": "排查类",
            "reproduction_probability": "必现",
            "customer_environment": "预发环境",
            "product_line": "私网文档中台",
            "product_module": "文档中台",
            "issue_product": "客户环境",
            "product_version": "v1.2.3",
            "function_point": "文档中台-上传-失败",
            "root_cause": "待分析",
            "root_cause_description": "上游超时",
            "timeline": [
                {
                    "external_timeline_id": "timeline-1",
                    "occurred_at": "2026-05-24T00:55:00+08:00",
                    "event_type": "工单跟进",
                    "content": "建议升级后重试",
                    "attachments": [
                        {
                            "external_attachment_id": "att-1",
                            "file_object_id": "123",
                            "file_name": "install-log.txt",
                            "file_size": 2048,
                            "url": "https://example.com/install-log.txt",
                        }
                    ],
                }
            ],
        }
    )

    assert todo.id == "WO-002"
    assert todo.status == TodoStatus.OPEN
    assert todo.summary_fields.reproduction_probability == "必现"
    assert todo.summary_fields.customer_environment_value == "预发环境"
    assert todo.summary_fields.product_module == "文档中台"
    assert todo.summary_fields.issue_product == "客户环境"
    assert todo.summary_fields.ach_no == "ACH-002"
    assert todo.summary_fields.feature_point == "文档中台-上传-失败"
    assert todo.project_link.match_status == "matched"
    assert todo.project_link.project_id == "project-local-1"
    assert todo.project_link.project_snapshot["project_id"] == "project-local-1"
    assert todo.project_link.project_snapshot["task_order_no"] == "PJ-24080225"
    assert todo.timeline[0].attachments[0].file_object_id == "123"
    assert todo.timeline[0].attachments[0].path == "https://example.com/install-log.txt"


def test_todo_from_server_work_order_normalizes_issue_product_path() -> None:
    todo = todo_from_server_work_order(
        {
            "external_order_no": "WO-003",
            "title": "问题所属产品需要规范化",
            "issue_product": "产品A / 模块B ／ 功能C",
        }
    )

    assert todo.summary_fields.issue_product == "产品A/模块B/功能C"


def test_todo_from_server_work_order_keeps_other_customer_environment_field_empty_when_missing() -> None:
    todo = todo_from_server_work_order(
        {
            "id": "WO-004",
            "title": "客户环境半字段返回",
            "customer_environment": "生产环境",
        }
    )

    assert todo.summary_fields.customer_environment_code == ""
    assert todo.summary_fields.customer_environment_value == "生产环境"


def test_todo_from_server_work_order_uses_file_id_when_url_missing() -> None:
    todo = todo_from_server_work_order(
        {
            "id": "1001",
            "external_id": "WO-003",
            "external_order_no": "WO-003",
            "title": "附件无 URL",
            "status": "in_progress",
            "timeline": [
                {
                    "external_timeline_id": "timeline-1",
                    "content": "附件只返回 file id",
                    "attachments": [
                        {
                            "external_attachment_id": "att-1",
                            "file_object_id": "file-123",
                            "file_name": "install-log.txt",
                            "file_size": 2048,
                        }
                    ],
                }
            ],
        }
    )

    assert todo.timeline[0].attachments[0].file_object_id == "file-123"
    assert todo.timeline[0].attachments[0].path == ""


def test_pull_my_in_progress_work_orders_imports_new_items_and_skips_existing() -> None:
    store = _TodoStore([_todo()])
    binding_store = _BindingStore()
    client = _Client(
        response={
            "success": True,
            "data": {
                "items": [
                    {"external_order_no": "todo-1", "title": "重复工单"},
                    {"id": 102, "external_order_no": "WO-002", "title": "新工单"},
                ],
                "pagination": {"page": 1, "page_size": 100, "total": 2},
            },
        }
    )

    result = pull_my_in_progress_work_orders(client, store, binding_store)  # type: ignore[arg-type]

    assert result.created_count == 1
    assert result.skipped_count == 1
    assert store.imported[0].id == "WO-002"
    assert client.payloads[0]["existing_external_order_nos"] == ["todo-1"]
    assert binding_store.upserts[0]["external_id"] == "102"
    assert binding_store.upserts[0]["sync_status"] == "ok:pulled"


def test_refresh_missing_ach_work_orders_updates_completed_candidates_only() -> None:
    missing_ach = _todo(status=TodoStatus.DONE)
    missing_ach.id = "todo-missing"
    missing_ach.summary_fields = TicketSummaryFields.from_dict(
        {**missing_ach.summary_fields.to_dict(), "ach_no": "", "ach_filled_at": ""}
    )
    has_ach = _todo(status=TodoStatus.DONE)
    has_ach.id = "todo-has-ach"
    open_missing = _todo(status=TodoStatus.OPEN)
    open_missing.id = "todo-open"
    open_missing.summary_fields = TicketSummaryFields.from_dict(
        {**open_missing.summary_fields.to_dict(), "ach_no": "", "ach_filled_at": ""}
    )
    store = _TodoStore([missing_ach, has_ach, open_missing])
    client = _Client(
        response={
            "success": True,
            "data": {
                "items": [
                    {
                        "external_order_no": "todo-missing",
                        "ach_order_no": "ACH-2026",
                        "ach_filled_at": "2026-05-29T10:00:00+08:00",
                    },
                    {
                        "external_order_no": "todo-open",
                        "ach_order_no": "ACH-OPEN",
                    },
                ],
                "pagination": {"page": 1, "page_size": 100, "total": 2},
            },
        }
    )

    result = refresh_missing_ach_work_orders(client, store)  # type: ignore[arg-type]

    assert result.updated_count == 1
    assert missing_ach.summary_fields.ach_no == "ACH-2026"
    assert missing_ach.summary_fields.ach_filled_at == "2026-05-29T10:00:00+08:00"
    assert open_missing.summary_fields.ach_no == ""
    assert client.payloads[0]["external_order_nos"] == ["todo-missing"]

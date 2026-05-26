"""Built-in Chattodo work-order synchronization."""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from aica.config import ServerConfig
from aica.server_api import ChattodoServerClient, ChattodoServerError
from aica.text_sanitize import sanitize_text
from aica.todo.events import (
    TodoBindingStore,
    TodoDomainEvent,
    TodoDomainEventType,
    TodoEventHandler,
)


INTEGRATION_ID = "chattodo-work-order"
SOURCE_SYSTEM = "Chattodo"


class WorkOrderClient(Protocol):
    def upsert_work_order(self, payload: dict[str, object]) -> dict[str, Any]:
        """Create or update a work order on the server."""

    def upload_workbench_file(
        self,
        file_path: str | Path,
        *,
        file_name: str = "",
        content_type: str = "",
        source_system: str = "",
        external_order_no: str = "",
        external_timeline_id: str = "",
        external_attachment_id: str = "",
    ) -> dict[str, Any]:
        """Upload a local attachment and return its server file object."""

def _clean(value: Any) -> str:
    return sanitize_text(value).strip()


def _is_unknown(value: Any) -> bool:
    return _clean(value) in {"", "未知", "待补充"}


def _first_meaningful(*values: Any) -> str:
    for value in values:
        text = _clean(value)
        if text and not _is_unknown(text):
            return text
    return ""


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if value == "":
        return False
    if value == []:
        return False
    return True


def _status_for_event(event: TodoDomainEvent) -> str:
    if event.event_type == TodoDomainEventType.DELETED:
        return "cancelled"
    status = _clean(event.todo_snapshot.get("status")).lower()
    if status == "done":
        return "completed"
    return "in_progress"


def _project_hit_status(value: Any) -> str:
    status = _clean(value).lower()
    if status in {"matched", "manual"}:
        return "matched"
    if status == "expired":
        return "expired"
    return ""


def _linked_from_text(value: Any) -> bool:
    return bool(_first_meaningful(value))


def _timeline_event_type(item: dict[str, Any]) -> str:
    kind = _clean(item.get("kind")).lower()
    if kind == "conclusion":
        return "工单结论"
    if kind == "log_analysis":
        return "日志分析"
    scenario = _clean(item.get("scenario"))
    raw_type = _clean(item.get("type") or item.get("event_type"))
    if scenario:
        return scenario
    if raw_type and raw_type != "default":
        return raw_type
    return "工单跟进"


def _attachment_payload(item: dict[str, Any]) -> dict[str, object]:
    file_name = _clean(item.get("name") or item.get("file_name"))
    payload: dict[str, object] = {
        "external_attachment_id": _clean(item.get("id") or item.get("external_attachment_id")),
        "file_name": file_name,
    }
    try:
        file_size = max(0, int(item.get("size_bytes") or item.get("file_size") or 0))
    except (TypeError, ValueError):
        file_size = 0
    if file_size:
        payload["file_size"] = file_size
    content_type = _clean(item.get("content_type"))
    if not content_type and file_name:
        content_type = mimetypes.guess_type(file_name)[0] or ""
    if content_type:
        payload["content_type"] = content_type
    url = _clean(item.get("url"))
    if url:
        payload["url"] = url
    file_object_id = _clean(item.get("file_object_id"))
    if file_object_id:
        payload["file_object_id"] = file_object_id
    preview_url = _clean(item.get("preview_url"))
    if preview_url:
        payload["preview_url"] = preview_url
    path = _clean(item.get("path"))
    if path:
        payload["_local_path"] = path
    return {key: value for key, value in payload.items() if _has_value(value)}


def _timeline_payload(item: dict[str, Any]) -> dict[str, object]:
    event_type = _timeline_event_type(item)
    payload: dict[str, object] = {
        "external_timeline_id": _clean(item.get("id") or item.get("external_timeline_id")),
        "occurred_at": _clean(item.get("timestamp") or item.get("occurred_at") or item.get("created_at")),
        "event_type": event_type,
        "title": _clean(item.get("title")) or event_type,
        "content": _clean(item.get("content")),
        "source_system": SOURCE_SYSTEM,
    }
    attachments = [
        _attachment_payload(dict(attachment))
        for attachment in list(item.get("attachments") or [])
        if isinstance(attachment, dict) and _clean(attachment.get("name") or attachment.get("file_name"))
    ]
    if attachments:
        payload["attachments"] = attachments
    return {key: value for key, value in payload.items() if _has_value(value)}


def build_work_order_payload(event: TodoDomainEvent) -> dict[str, object]:
    snapshot = dict(event.todo_snapshot or {})
    fields = dict(snapshot.get("summary_fields") or {})
    project_link = dict(snapshot.get("project_link") or {})
    project_snapshot = dict(project_link.get("project_snapshot") or {})
    title = _clean(snapshot.get("title")) or "未分类任务"
    project_status = _project_hit_status(project_link.get("match_status"))
    feature_point = _first_meaningful(fields.get("feature_point"))
    group_name = _first_meaningful(fields.get("group_name"))
    product_version = _first_meaningful(project_snapshot.get("product_version"), fields.get("ticket_version"))

    payload: dict[str, object] = {
        "source_system": SOURCE_SYSTEM,
        "external_id": _clean(snapshot.get("id")),
        "external_order_no": _clean(snapshot.get("id")),
        "external_filled_at": _clean(fields.get("ach_filled_at") or snapshot.get("created_at")),
        "ach_order_no": _clean(fields.get("ach_no")),
        "ach_filled_at": _clean(fields.get("ach_filled_at")),
        "title": title,
        "description": _clean(snapshot.get("current_summary")),
        "status": _status_for_event(event),
        "group_name": group_name,
        "environment": _first_meaningful(fields.get("environment")),
        "work_order_type": _first_meaningful(fields.get("ticket_type")),
        "product_line": _first_meaningful(fields.get("product_line"), project_snapshot.get("product_line")),
        "product_version": product_version,
        "function_point_name": feature_point,
        "root_cause": _first_meaningful(fields.get("root_cause")),
        "root_cause_description": _first_meaningful(fields.get("root_cause_desc")),
        "project_manager": _first_meaningful(project_snapshot.get("project_manager")),
    }
    if project_status:
        payload["project_hit_status"] = project_status

    project_task_order_no = _first_meaningful(project_snapshot.get("task_order_no"))
    project_display_name = _first_meaningful(project_snapshot.get("project_name"))
    if project_task_order_no or project_display_name or project_status:
        payload["project"] = {
            key: value
            for key, value in {
                "task_order_no": project_task_order_no,
                "display_name": project_display_name,
                "linked": project_status in {"matched", "expired"},
            }.items()
            if _has_value(value)
        }

    if group_name:
        payload["chat_group"] = {
            "group_name": group_name,
            "linked": _linked_from_text(group_name),
        }

    if feature_point:
        payload["function_point"] = {
            "full_name": feature_point,
            "linked": _linked_from_text(feature_point),
        }

    timeline = [
        _timeline_payload(dict(item))
        for item in list(snapshot.get("timeline") or [])
        if isinstance(item, dict)
    ]
    if timeline:
        payload["timeline"] = timeline

    return {key: value for key, value in payload.items() if _has_value(value)}


def _server_item_external_id(response: dict[str, Any]) -> str:
    data = response.get("data")
    item = data.get("item") if isinstance(data, dict) else None
    if isinstance(item, dict):
        return _clean(item.get("id") or item.get("external_order_no") or item.get("external_id"))
    return ""


def _file_object_payload(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if isinstance(data, dict):
        for key in ("file", "file_object", "item"):
            value = data.get(key)
            if isinstance(value, dict):
                return dict(value)
        return dict(data)
    return {}


def _uploaded_attachment_payload(attachment: dict[str, object], file_object: dict[str, Any]) -> dict[str, object]:
    payload = {key: value for key, value in attachment.items() if key != "_local_path"}
    for source_key, target_key in (
        ("file_object_id", "file_object_id"),
        ("id", "file_object_id"),
        ("url", "url"),
        ("download_url", "url"),
        ("preview_url", "preview_url"),
    ):
        value = _clean(file_object.get(source_key))
        if value and not _clean(payload.get(target_key)):
            payload[target_key] = value
    if not _clean(payload.get("file_object_id")) and not _clean(payload.get("url")):
        raise ChattodoServerError("附件上传成功但服务端未返回 file_object_id 或 url。")
    return {key: value for key, value in payload.items() if _has_value(value)}


def _prepare_attachment_for_sync(
    client: WorkOrderClient,
    attachment: dict[str, object],
    *,
    external_order_no: str,
    external_timeline_id: str,
) -> dict[str, object] | None:
    has_download = bool(_clean(attachment.get("url")) or _clean(attachment.get("file_object_id")))
    if has_download:
        return {key: value for key, value in attachment.items() if key != "_local_path" and _has_value(value)}

    local_path = _clean(attachment.get("_local_path"))
    if not local_path:
        return None
    file_path = Path(local_path).expanduser()
    if not file_path.is_file():
        return None
    response = client.upload_workbench_file(
        file_path,
        file_name=_clean(attachment.get("file_name")) or file_path.name,
        content_type=_clean(attachment.get("content_type")),
        source_system=SOURCE_SYSTEM,
        external_order_no=external_order_no,
        external_timeline_id=external_timeline_id,
        external_attachment_id=_clean(attachment.get("external_attachment_id")),
    )
    return _uploaded_attachment_payload(attachment, _file_object_payload(response))


def _prepare_payload_attachments(client: WorkOrderClient, payload: dict[str, object]) -> dict[str, object]:
    prepared_payload = dict(payload)
    timeline = prepared_payload.get("timeline")
    if not isinstance(timeline, list):
        return prepared_payload
    external_order_no = _clean(prepared_payload.get("external_order_no"))
    prepared_timeline: list[object] = []
    for item in timeline:
        if not isinstance(item, dict):
            prepared_timeline.append(item)
            continue
        prepared_item = dict(item)
        attachments = prepared_item.get("attachments")
        if isinstance(attachments, list):
            prepared_attachments: list[dict[str, object]] = []
            external_timeline_id = _clean(prepared_item.get("external_timeline_id"))
            for attachment in attachments:
                if not isinstance(attachment, dict):
                    continue
                prepared_attachment = _prepare_attachment_for_sync(
                    client,
                    dict(attachment),
                    external_order_no=external_order_no,
                    external_timeline_id=external_timeline_id,
                )
                if prepared_attachment is not None:
                    prepared_attachments.append(prepared_attachment)
            if prepared_attachments:
                prepared_item["attachments"] = prepared_attachments
            else:
                prepared_item.pop("attachments", None)
        prepared_timeline.append({key: value for key, value in prepared_item.items() if _has_value(value)})
    prepared_payload["timeline"] = prepared_timeline
    return {key: value for key, value in prepared_payload.items() if _has_value(value)}


@dataclass
class WorkOrderSyncEventHandler(TodoEventHandler):
    binding_store: TodoBindingStore
    config_provider: Any
    client_factory: Any = ChattodoServerClient.from_config
    integration_id: str = INTEGRATION_ID

    def handle(self, event: TodoDomainEvent) -> None:
        config = self.config_provider()
        server_config = getattr(config, "server", config)
        if not self._is_enabled(server_config):
            return
        try:
            client: WorkOrderClient = self.client_factory(server_config)
            payload = build_work_order_payload(event)
            payload = _prepare_payload_attachments(client, payload)
            response = client.upsert_work_order(payload)
        except ChattodoServerError as exc:
            self.binding_store.update_sync_status(
                event.todo_id,
                self.integration_id,
                event=event,
                sync_status=f"failed:{_clean(exc)}",
                deleted_locally=event.event_type == TodoDomainEventType.DELETED,
            )
            return
        external_id = _server_item_external_id(response) or _clean(payload.get("external_order_no"))
        action = "cancelled" if event.event_type == TodoDomainEventType.DELETED else "synced"
        if external_id:
            self.binding_store.upsert_binding(
                event.todo_id,
                self.integration_id,
                external_id,
                event=event,
                sync_status=f"ok:{action}",
                metadata={"response": response.get("data", {}) if isinstance(response, dict) else {}},
                deleted_locally=event.event_type == TodoDomainEventType.DELETED,
            )
            return
        self.binding_store.update_sync_status(
            event.todo_id,
            self.integration_id,
            event=event,
            sync_status=f"ok:{action}",
            deleted_locally=event.event_type == TodoDomainEventType.DELETED,
        )

    @staticmethod
    def _is_enabled(server_config: ServerConfig) -> bool:
        return (
            bool(getattr(server_config, "enabled", False))
            and bool(_clean(getattr(server_config, "base_url", "")))
            and bool(_clean(getattr(server_config, "api_key", "")))
        )

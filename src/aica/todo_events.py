"""Todo domain events, external integrations, and binding persistence."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import traceback
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from .paths import (
    error_log_file as default_error_log_file,
    integrations_file as default_integrations_file,
)
from .storage.sqlite.repositories import SQLiteBindingRepository
from .text_sanitize import (
    find_invalid_surrogate_paths,
    sanitize_json_like,
    sanitize_text,
    strip_invalid_surrogates,
)
from .todo_store import TimelineAttachment, TimelineEvent, TodoItem


def _now_iso() -> str:
    return datetime.now().isoformat()


def _sanitize_text(value: Any) -> str:
    return sanitize_text(value)


def _normalize_metadata(payload: Any) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def _append_integration_log(message: str) -> None:
    try:
        log_file = default_error_log_file()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            sanitized_message = strip_invalid_surrogates(message)
            handle.write(f"\n[todo_event_sync] {_now_iso()} {sanitized_message}\n")
    except OSError:
        pass


def _integration_subprocess_options() -> dict[str, Any]:
    if os.name != "nt":
        return {}

    startupinfo_factory = getattr(subprocess, "STARTUPINFO", None)
    startf_use_show_window = getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if startupinfo_factory is None:
        return {"creationflags": create_no_window} if create_no_window else {}

    startupinfo = startupinfo_factory()
    startupinfo.dwFlags |= startf_use_show_window
    startupinfo.wShowWindow = 0
    options: dict[str, Any] = {"startupinfo": startupinfo}
    if create_no_window:
        options["creationflags"] = create_no_window
    return options


def serialize_timeline_attachment(attachment: TimelineAttachment) -> dict[str, Any]:
    return {
        "id": attachment.id,
        "name": attachment.name,
        "path": attachment.path,
        "size_bytes": attachment.size_bytes,
    }


def serialize_timeline_event(event: TimelineEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "timestamp": event.timestamp,
        "kind": event.kind,
        "scenario": event.scenario,
        "content": event.content,
        "attachments": [serialize_timeline_attachment(item) for item in event.attachments],
    }


def serialize_todo_item(todo: TodoItem) -> dict[str, Any]:
    return {
        "id": todo.id,
        "title": todo.title,
        "status": todo.status,
        "summary_fields": todo.summary_fields.to_dict(),
        "current_summary": todo.current_summary,
        "created_at": todo.created_at,
        "updated_at": todo.updated_at,
        "timeline": [serialize_timeline_event(event) for event in todo.timeline],
        "project_link": todo.project_link.to_dict(),
    }


class TodoDomainEventType(StrEnum):
    CREATED = "created"
    APPENDED = "appended"
    UPDATED = "updated"
    COMPLETED = "completed"
    DELETED = "deleted"
    MANUAL_SYNC = "manual_sync"


@dataclass
class TodoBinding:
    todo_id: str
    integration_id: str
    external_id: str = ""
    external_url: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    last_event_id: str = ""
    last_event_type: str = ""
    last_sync_status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    deleted_locally: bool = False

    def __post_init__(self) -> None:
        self.todo_id = _sanitize_text(self.todo_id)
        self.integration_id = _sanitize_text(self.integration_id)
        self.external_id = _sanitize_text(self.external_id)
        self.external_url = _sanitize_text(self.external_url)
        self.last_event_id = _sanitize_text(self.last_event_id)
        self.last_event_type = _sanitize_text(self.last_event_type)
        self.last_sync_status = _sanitize_text(self.last_sync_status)
        self.metadata = _normalize_metadata(self.metadata)
        self.deleted_locally = bool(self.deleted_locally)

    @property
    def is_bound(self) -> bool:
        return bool(self.external_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "todo_id": self.todo_id,
            "integration_id": self.integration_id,
            "external_id": self.external_id,
            "external_url": self.external_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_event_id": self.last_event_id,
            "last_event_type": self.last_event_type,
            "last_sync_status": self.last_sync_status,
            "metadata": self.metadata,
            "deleted_locally": self.deleted_locally,
        }

    @classmethod
    def from_dict(cls, payload: object) -> TodoBinding | None:
        if not isinstance(payload, dict):
            return None
        todo_id = _sanitize_text(payload.get("todo_id"))
        integration_id = _sanitize_text(payload.get("integration_id"))
        external_id = _sanitize_text(payload.get("external_id"))
        if not (todo_id and integration_id):
            return None
        return cls(
            todo_id=todo_id,
            integration_id=integration_id,
            external_id=external_id,
            external_url=payload.get("external_url", ""),
            created_at=_sanitize_text(payload.get("created_at")) or _now_iso(),
            updated_at=_sanitize_text(payload.get("updated_at")) or _now_iso(),
            last_event_id=payload.get("last_event_id", ""),
            last_event_type=payload.get("last_event_type", ""),
            last_sync_status=payload.get("last_sync_status", ""),
            metadata=payload.get("metadata", {}),
            deleted_locally=payload.get("deleted_locally", False),
        )


@dataclass(frozen=True)
class TodoDomainEvent:
    event_id: str
    event_type: TodoDomainEventType
    occurred_at: str
    scenario: str
    todo_id: str
    todo_snapshot: dict[str, Any]
    delta: dict[str, Any]
    bindings: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def created(cls, todo: TodoItem, scenario: str) -> TodoDomainEvent:
        timeline_event = todo.timeline[0] if todo.timeline else None
        delta = {"timeline_event": serialize_timeline_event(timeline_event)} if timeline_event is not None else {}
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=TodoDomainEventType.CREATED,
            occurred_at=_now_iso(),
            scenario=_sanitize_text(scenario),
            todo_id=todo.id,
            todo_snapshot=serialize_todo_item(todo),
            delta=delta,
        )

    @classmethod
    def appended(cls, todo: TodoItem, scenario: str) -> TodoDomainEvent:
        timeline_event = todo.timeline[-1] if todo.timeline else None
        delta = {"timeline_event": serialize_timeline_event(timeline_event)} if timeline_event is not None else {}
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=TodoDomainEventType.APPENDED,
            occurred_at=_now_iso(),
            scenario=_sanitize_text(scenario),
            todo_id=todo.id,
            todo_snapshot=serialize_todo_item(todo),
            delta=delta,
        )

    @classmethod
    def updated(
        cls,
        todo: TodoItem,
        scenario: str,
        changed_fields: list[str] | None = None,
    ) -> TodoDomainEvent:
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=TodoDomainEventType.UPDATED,
            occurred_at=_now_iso(),
            scenario=_sanitize_text(scenario),
            todo_id=todo.id,
            todo_snapshot=serialize_todo_item(todo),
            delta={"changed_fields": list(changed_fields or [])},
        )

    @classmethod
    def completed(cls, todo: TodoItem, scenario: str) -> TodoDomainEvent:
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=TodoDomainEventType.COMPLETED,
            occurred_at=_now_iso(),
            scenario=_sanitize_text(scenario),
            todo_id=todo.id,
            todo_snapshot=serialize_todo_item(todo),
            delta={"status_change": {"from": "open", "to": "done"}},
        )

    @classmethod
    def deleted(cls, todo: TodoItem, scenario: str) -> TodoDomainEvent:
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=TodoDomainEventType.DELETED,
            occurred_at=_now_iso(),
            scenario=_sanitize_text(scenario),
            todo_id=todo.id,
            todo_snapshot=serialize_todo_item(todo),
            delta={"deleted": True},
        )

    @classmethod
    def manual_sync(cls, todo: TodoItem, scenario: str) -> TodoDomainEvent:
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=TodoDomainEventType.MANUAL_SYNC,
            occurred_at=_now_iso(),
            scenario=_sanitize_text(scenario),
            todo_id=todo.id,
            todo_snapshot=serialize_todo_item(todo),
            delta={"trigger": "manual"},
        )

    def with_bindings(self, bindings: list[dict[str, Any]]) -> TodoDomainEvent:
        return replace(self, bindings=list(bindings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": str(self.event_type),
            "occurred_at": self.occurred_at,
            "scenario": self.scenario,
            "todo_id": self.todo_id,
            "todo_snapshot": self.todo_snapshot,
            "delta": self.delta,
            "bindings": self.bindings,
        }


class TodoEventPublisher(Protocol):
    def publish(self, event: TodoDomainEvent) -> None:
        """Publish a Todo domain event."""


class TodoEventHandler(Protocol):
    def handle(self, event: TodoDomainEvent) -> None:
        """Handle a Todo domain event."""


@dataclass(frozen=True)
class TodoIntegrationConfig:
    id: str
    type: str
    command: str
    args: list[str] = field(default_factory=list)
    cwd: str = ""
    timeout_seconds: int = 8
    enabled: bool = True
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: object) -> TodoIntegrationConfig | None:
        if not isinstance(payload, dict):
            return None
        integration_id = _sanitize_text(payload.get("id"))
        integration_type = _sanitize_text(payload.get("type"))
        command = _sanitize_text(payload.get("command"))
        args_payload = payload.get("args", [])
        args = [str(item) for item in args_payload if str(item).strip()] if isinstance(args_payload, list) else []
        env_payload = payload.get("env", {})
        env = {str(key): str(value) for key, value in env_payload.items()} if isinstance(env_payload, dict) else {}
        timeout_seconds = 8
        try:
            timeout_seconds = max(1, int(payload.get("timeout_seconds", 8)))
        except (TypeError, ValueError):
            timeout_seconds = 8
        if not (integration_id and integration_type == "script" and command):
            return None
        return cls(
            id=integration_id,
            type=integration_type,
            command=command,
            args=args,
            cwd=_sanitize_text(payload.get("cwd")),
            timeout_seconds=timeout_seconds,
            enabled=bool(payload.get("enabled", True)),
            env=env,
        )


class TodoIntegrationRegistry:
    def __init__(self, config_path: str | None = None) -> None:
        self._path = config_path or str(default_integrations_file())

    def list_integrations(self) -> list[TodoIntegrationConfig]:
        path = Path(self._path)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            _append_integration_log(f"Failed to read integrations config: {path}")
            return []
        raw_items = payload.get("todo_event_integrations", []) if isinstance(payload, dict) else []
        if not isinstance(raw_items, list):
            return []
        integrations: list[TodoIntegrationConfig] = []
        for item in raw_items:
            integration = TodoIntegrationConfig.from_dict(item)
            if integration is not None and integration.enabled:
                integrations.append(integration)
        return integrations


class TodoBindingStore:
    def __init__(self, store_path: str | None = None) -> None:
        self._repository = SQLiteBindingRepository(store_path)
        self._lock = threading.Lock()

    @property
    def path(self) -> str:
        return self._repository.path

    def list_bindings(self, todo_id: str) -> list[TodoBinding]:
        with self._lock:
            payloads = self._repository.list_bindings(todo_id)
        items: list[TodoBinding] = []
        for payload in payloads:
            binding = TodoBinding.from_dict(payload)
            if binding is not None:
                items.append(binding)
        return items

    def list_binding_payloads(self, todo_id: str) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.list_bindings(todo_id)]

    def list_records(self, todo_id: str) -> list[TodoBinding]:
        with self._lock:
            payloads = self._repository.list_records(todo_id)
        items: list[TodoBinding] = []
        for payload in payloads:
            binding = TodoBinding.from_dict(payload)
            if binding is not None:
                items.append(binding)
        return items

    def list_record_payloads(self, todo_id: str) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.list_records(todo_id)]

    def get_binding(self, todo_id: str, integration_id: str) -> TodoBinding | None:
        with self._lock:
            payload = self._repository.get_binding(todo_id, integration_id)
        return TodoBinding.from_dict(payload) if payload is not None else None

    def get_record(self, todo_id: str, integration_id: str) -> TodoBinding | None:
        with self._lock:
            payload = self._repository.get_record(todo_id, integration_id)
        return TodoBinding.from_dict(payload) if payload is not None else None

    def has_binding(self, todo_id: str, integration_id: str) -> bool:
        with self._lock:
            return self._repository.has_binding(todo_id, integration_id)

    def upsert_binding(
        self,
        todo_id: str,
        integration_id: str,
        external_id: str,
        *,
        external_url: str = "",
        event: TodoDomainEvent | None = None,
        sync_status: str = "",
        metadata: dict[str, Any] | None = None,
        deleted_locally: bool | None = None,
    ) -> TodoBinding | None:
        with self._lock:
            payload = self._repository.upsert_binding(
                todo_id,
                integration_id,
                external_id,
                external_url=external_url,
                event_id=event.event_id if event is not None else "",
                event_type=str(event.event_type) if event is not None else "",
                sync_status=sync_status,
                metadata=metadata,
                deleted_locally=deleted_locally,
            )
        return TodoBinding.from_dict(payload) if payload is not None else None

    def update_sync_status(
        self,
        todo_id: str,
        integration_id: str,
        *,
        event: TodoDomainEvent | None = None,
        sync_status: str = "",
        metadata: dict[str, Any] | None = None,
        deleted_locally: bool | None = None,
        external_url: str = "",
    ) -> TodoBinding | None:
        with self._lock:
            payload = self._repository.update_sync_status(
                todo_id,
                integration_id,
                event_id=event.event_id if event is not None else "",
                event_type=str(event.event_type) if event is not None else "",
                sync_status=sync_status,
                metadata=metadata,
                deleted_locally=deleted_locally,
                external_url=external_url,
            )
        return TodoBinding.from_dict(payload) if payload is not None else None

    def mark_deleted_locally(self, todo_id: str, integration_id: str) -> TodoBinding | None:
        return self.update_sync_status(
            todo_id,
            integration_id,
            sync_status="deleted_locally",
            deleted_locally=True,
        )


class TodoEventBus(TodoEventPublisher):
    def __init__(
        self,
        handlers: list[TodoEventHandler] | None = None,
        *,
        binding_store: TodoBindingStore | None = None,
        async_dispatch: bool = True,
    ) -> None:
        self._handlers = list(handlers or [])
        self._binding_store = binding_store
        self._async_dispatch = async_dispatch

    def publish(self, event: TodoDomainEvent) -> None:
        self.dispatch(event)

    def dispatch(self, event: TodoDomainEvent, *, async_dispatch: bool | None = None) -> None:
        if not self._handlers:
            return
        dispatch_event = event
        if self._binding_store is not None:
            dispatch_event = event.with_bindings(self._binding_store.list_binding_payloads(event.todo_id))
        should_dispatch_async = self._async_dispatch if async_dispatch is None else async_dispatch
        for handler in self._handlers:
            if should_dispatch_async:
                worker = threading.Thread(
                    target=self._safe_handle,
                    args=(handler, dispatch_event),
                    daemon=True,
                )
                worker.start()
            else:
                self._safe_handle(handler, dispatch_event)

    @staticmethod
    def _safe_handle(handler: TodoEventHandler, event: TodoDomainEvent) -> None:
        try:
            handler.handle(event)
        except Exception:
            _append_integration_log(traceback.format_exc())


class ScriptEventHandler(TodoEventHandler):
    def __init__(
        self,
        *,
        binding_store: TodoBindingStore,
        integration_registry: TodoIntegrationRegistry | None = None,
    ) -> None:
        self._binding_store = binding_store
        self._integration_registry = integration_registry or TodoIntegrationRegistry()

    def handle(self, event: TodoDomainEvent) -> None:
        for integration in self._integration_registry.list_integrations():
            if (
                self._requires_existing_binding(event.event_type)
                and not self._binding_store.has_binding(event.todo_id, integration.id)
            ):
                self._binding_store.update_sync_status(
                    event.todo_id,
                    integration.id,
                    event=event,
                    sync_status="skipped:missing_binding",
                    deleted_locally=event.event_type == TodoDomainEventType.DELETED,
                )
                _append_integration_log(
                    f"Skip integration without binding [{integration.id}] for event {event.event_type}"
                )
                continue
            self._handle_integration(event, integration)

    @staticmethod
    def _requires_existing_binding(event_type: TodoDomainEventType) -> bool:
        return event_type not in {
            TodoDomainEventType.CREATED,
            TodoDomainEventType.APPENDED,
            TodoDomainEventType.MANUAL_SYNC,
        }

    def _handle_integration(self, event: TodoDomainEvent, integration: TodoIntegrationConfig) -> None:
        raw_payload = event.to_dict()
        invalid_paths = find_invalid_surrogate_paths(raw_payload)
        if invalid_paths:
            joined_paths = ", ".join(invalid_paths[:8])
            if len(invalid_paths) > 8:
                joined_paths += f", ... (+{len(invalid_paths) - 8} more)"
            _append_integration_log(
                "Sanitized invalid Unicode before integration "
                f"[{integration.id}] event={event.event_type} todo_id={event.todo_id} paths={joined_paths}"
            )
        payload_text = json.dumps(sanitize_json_like(raw_payload), ensure_ascii=True)
        env = os.environ.copy()
        env.update(integration.env)
        env["AICA_INTEGRATION_ID"] = integration.id
        env["AICA_TODO_EVENT_TYPE"] = str(event.event_type)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")
        command = [integration.command, *integration.args]

        try:
            result = subprocess.run(
                command,
                input=payload_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=integration.timeout_seconds,
                cwd=integration.cwd or None,
                env=env,
                check=False,
                **_integration_subprocess_options(),
            )
        except FileNotFoundError:
            self._update_existing_binding(
                event,
                integration.id,
                sync_status="failed:command_not_found",
                deleted_locally=event.event_type == TodoDomainEventType.DELETED,
            )
            _append_integration_log(f"Integration command not found: {command[0]}")
            return
        except subprocess.TimeoutExpired:
            self._update_existing_binding(
                event,
                integration.id,
                sync_status="failed:timeout",
                deleted_locally=event.event_type == TodoDomainEventType.DELETED,
            )
            _append_integration_log(
                f"Integration timed out after {integration.timeout_seconds}s: {integration.id}"
            )
            return
        except Exception:
            self._update_existing_binding(
                event,
                integration.id,
                sync_status="failed:exception",
                deleted_locally=event.event_type == TodoDomainEventType.DELETED,
            )
            _append_integration_log(traceback.format_exc())
            return

        if result.stderr.strip():
            _append_integration_log(
                f"Integration stderr [{integration.id}]: {result.stderr.strip()}"
            )

        if result.returncode != 0:
            self._update_existing_binding(
                event,
                integration.id,
                sync_status=f"failed:returncode:{result.returncode}",
                deleted_locally=event.event_type == TodoDomainEventType.DELETED,
            )
            _append_integration_log(
                f"Integration exited with {result.returncode}: {integration.id}"
            )
            return

        ack_payload: dict[str, Any] = {}
        stdout_text = result.stdout.strip()
        if stdout_text:
            try:
                parsed = json.loads(stdout_text)
            except json.JSONDecodeError:
                self._update_existing_binding(
                    event,
                    integration.id,
                    sync_status="failed:invalid_ack",
                    deleted_locally=event.event_type == TodoDomainEventType.DELETED,
                )
                _append_integration_log(f"Invalid JSON ack from integration: {integration.id}")
                return
            if isinstance(parsed, dict):
                ack_payload = parsed

        ack_integration_id = integration.id
        raw_ack_integration_id = _sanitize_text(ack_payload.get("integration_id"))
        if raw_ack_integration_id and raw_ack_integration_id != integration.id:
            _append_integration_log(
                f"Ignore mismatched integration_id in ack: expected={integration.id}, actual={raw_ack_integration_id}"
            )
        external_id = _sanitize_text(ack_payload.get("external_id"))
        external_url = _sanitize_text(ack_payload.get("external_url"))
        metadata = _normalize_metadata(ack_payload.get("metadata"))
        ok = bool(ack_payload.get("ok", True))
        action = _sanitize_text(ack_payload.get("action")) or "noop"
        deleted_locally = event.event_type == TodoDomainEventType.DELETED
        sync_status = f"{'ok' if ok else 'failed'}:{action}"

        if external_id:
            self._binding_store.upsert_binding(
                event.todo_id,
                ack_integration_id,
                external_id,
                external_url=external_url,
                event=event,
                sync_status=sync_status,
                metadata=metadata,
                deleted_locally=deleted_locally,
            )
            return

        self._update_existing_binding(
            event,
            ack_integration_id,
            sync_status=sync_status,
            metadata=metadata,
            external_url=external_url,
            deleted_locally=deleted_locally,
        )

    def _update_existing_binding(
        self,
        event: TodoDomainEvent,
        integration_id: str,
        *,
        sync_status: str,
        metadata: dict[str, Any] | None = None,
        external_url: str = "",
        deleted_locally: bool = False,
    ) -> None:
        self._binding_store.update_sync_status(
            event.todo_id,
            integration_id,
            event=event,
            sync_status=sync_status,
            metadata=metadata,
            external_url=external_url,
            deleted_locally=deleted_locally,
        )

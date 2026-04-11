import json
import sys
import textwrap
from pathlib import Path

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.todo_controller import TodoController
from aica.todo_events import (
    ScriptEventHandler,
    TodoBindingStore,
    TodoDomainEvent,
    TodoDomainEventType,
    TodoEventBus,
    TodoIntegrationRegistry,
    _integration_subprocess_options,
)
from aica.todo_store import TimelineEvent, TodoItem, TodoStore


class _Publisher:
    def __init__(self) -> None:
        self.events: list[TodoDomainEvent] = []

    def publish(self, event: TodoDomainEvent) -> None:
        self.events.append(event)


def _snapshot(
    title: str,
    summary: str,
    timeline: str,
    *,
    group_name: str = "group-a",
    environment: str = "prod",
    product_line: str = "line-a",
    ticket_type: str = "排查类",
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
    )


def _build_controller(tmp_path: Path, publisher=None) -> TodoController:
    store = TodoStore(str(tmp_path / "todos.json"))
    return TodoController(store, event_publisher=publisher)


def _write_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "sync_todo.py"
    script_path.write_text(
        textwrap.dedent(
            """
            import json
            import os
            import sys

            event = json.load(sys.stdin)
            mode = os.environ.get("TEST_ACK_MODE", "")

            if mode == "return_extid":
                payload = {
                    "ok": True,
                    "action": "created",
                    "external_id": "EXT-001",
                    "external_url": "https://platform.example.com/ticket/EXT-001",
                }
                print(json.dumps(payload, ensure_ascii=False))
                raise SystemExit(0)

            if mode == "return_no_id":
                print(json.dumps({"ok": True, "action": "noop"}, ensure_ascii=False))
                raise SystemExit(0)

            if mode == "late_bind":
                print(json.dumps({"ok": True, "action": "updated", "external_id": "EXT-LATE"}, ensure_ascii=False))
                raise SystemExit(0)

            if mode == "no_id_update":
                print(json.dumps({"ok": True, "action": "updated"}, ensure_ascii=False))
                raise SystemExit(0)

            if mode == "invalid_json":
                sys.stdout.write("not-json")
                raise SystemExit(0)

            if mode == "fail":
                sys.stderr.write("boom")
                raise SystemExit(2)

            bindings = event.get("bindings", [])
            payload = {
                "ok": True,
                "action": "updated",
                "external_id": bindings[0]["external_id"] if bindings else "",
            }
            print(json.dumps(payload, ensure_ascii=False))
            """
        ).strip(),
        encoding="utf-8",
    )
    return script_path


def _write_integrations_config(tmp_path: Path, script_path: Path, *, mode: str) -> Path:
    config_path = tmp_path / "integrations.json"
    config_path.write_text(
        json.dumps(
            {
                "todo_event_integrations": [
                    {
                        "id": "company-platform",
                        "enabled": True,
                        "type": "script",
                        "command": sys.executable,
                        "args": [str(script_path)],
                        "cwd": str(tmp_path),
                        "timeout_seconds": 8,
                        "env": {
                            "TEST_ACK_MODE": mode,
                        },
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return config_path


def _write_logger_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "logger_todo.py"
    script_path.write_text(
        textwrap.dedent(
            """
            import json
            import sys
            from pathlib import Path

            event = json.load(sys.stdin)
            output_path = Path("event-log.json")
            output_path.write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"ok": True, "action": "logged"}, ensure_ascii=False))
            """
        ).strip(),
        encoding="utf-8",
    )
    return script_path


def _write_raw_stdin_probe_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "stdin_probe.py"
    script_path.write_text(
        textwrap.dedent(
            """
            import json
            import os
            import sys
            from pathlib import Path

            raw = sys.stdin.read()
            Path("raw-stdin.json").write_text(raw, encoding="utf-8")
            payload = {
                "ok": True,
                "action": "logged",
                "metadata": {
                    "stdin_encoding": sys.stdin.encoding,
                    "stdin_errors": sys.stdin.errors,
                    "pythonioencoding": os.environ.get("PYTHONIOENCODING", ""),
                    "pythonutf8": os.environ.get("PYTHONUTF8", ""),
                },
            }
            print(json.dumps(payload, ensure_ascii=False))
            """
        ).strip(),
        encoding="utf-8",
    )
    return script_path


def _build_event_bus(tmp_path: Path, *, mode: str) -> tuple[TodoEventBus, TodoBindingStore]:
    script_path = _write_script(tmp_path)
    config_path = _write_integrations_config(tmp_path, script_path, mode=mode)
    binding_store = TodoBindingStore(str(tmp_path / "todo_bindings.json"))
    handler = ScriptEventHandler(
        binding_store=binding_store,
        integration_registry=TodoIntegrationRegistry(str(config_path)),
    )
    return TodoEventBus(
        handlers=[handler],
        binding_store=binding_store,
        async_dispatch=False,
    ), binding_store


def _build_logger_event_bus(tmp_path: Path) -> tuple[TodoEventBus, TodoBindingStore]:
    script_path = _write_logger_script(tmp_path)
    config_path = _write_integrations_config(tmp_path, script_path, mode="")
    binding_store = TodoBindingStore(str(tmp_path / "todo_bindings.json"))
    handler = ScriptEventHandler(
        binding_store=binding_store,
        integration_registry=TodoIntegrationRegistry(str(config_path)),
    )
    return TodoEventBus(
        handlers=[handler],
        binding_store=binding_store,
        async_dispatch=False,
    ), binding_store


def _build_probe_event_bus(tmp_path: Path) -> tuple[TodoEventBus, TodoBindingStore]:
    script_path = _write_raw_stdin_probe_script(tmp_path)
    config_path = _write_integrations_config(tmp_path, script_path, mode="")
    binding_store = TodoBindingStore(str(tmp_path / "todo_bindings.json"))
    handler = ScriptEventHandler(
        binding_store=binding_store,
        integration_registry=TodoIntegrationRegistry(str(config_path)),
    )
    return TodoEventBus(
        handlers=[handler],
        binding_store=binding_store,
        async_dispatch=False,
    ), binding_store


def test_save_analysis_publishes_created_event(tmp_path: Path):
    publisher = _Publisher()
    controller = _build_controller(tmp_path, publisher)

    result = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )

    assert result.action == "create"
    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.event_type == TodoDomainEventType.CREATED
    assert event.todo_id == result.todo.id
    assert event.delta["timeline_event"]["content"] == "first follow-up"


def test_append_analysis_publishes_appended_event(tmp_path: Path):
    publisher = _Publisher()
    controller = _build_controller(tmp_path, publisher)
    created = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )
    controller.toggle_selected_todo(created.todo.id)
    publisher.events.clear()

    result = controller.save_analysis_result(
        _snapshot("new title", "new summary", "second follow-up"),
        "todo assistant",
    )

    assert result.action == "append"
    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.event_type == TodoDomainEventType.APPENDED
    assert event.delta["timeline_event"]["content"] == "second follow-up"


def test_complete_todo_publishes_completed_event(tmp_path: Path):
    publisher = _Publisher()
    controller = _build_controller(tmp_path, publisher)
    created = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "工单待办助手",
    )
    publisher.events.clear()

    assert controller.complete_todo(created.todo.id)

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.event_type == TodoDomainEventType.COMPLETED
    assert event.todo_snapshot["status"] == "done"
    assert event.scenario == "工单待办助手"


def test_delete_todo_publishes_deleted_event_with_predelete_snapshot(tmp_path: Path):
    publisher = _Publisher()
    controller = _build_controller(tmp_path, publisher)
    created = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "工单待办助手",
    )
    publisher.events.clear()

    assert controller.delete_todo(created.todo.id)

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.event_type == TodoDomainEventType.DELETED
    assert event.todo_snapshot["title"] == "upload failed"
    assert event.delta == {"deleted": True}


def test_update_todo_publishes_updated_event(tmp_path: Path):
    publisher = _Publisher()
    controller = _build_controller(tmp_path, publisher)
    created = controller.save_analysis_result(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )
    publisher.events.clear()

    controller.update_todo(created.todo.id, title="new title")

    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.event_type == TodoDomainEventType.UPDATED
    assert event.todo_snapshot["title"] == "new title"
    assert event.delta == {"changed_fields": ["title"]}


def test_manual_sync_event_uses_manual_trigger_delta(tmp_path: Path):
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )

    event = TodoDomainEvent.manual_sync(todo, "todo assistant")

    assert event.event_type == TodoDomainEventType.MANUAL_SYNC
    assert event.delta == {"trigger": "manual"}


def test_script_handler_persists_binding_when_created_ack_contains_external_id(tmp_path: Path):
    event_bus, binding_store = _build_event_bus(tmp_path, mode="return_extid")
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )

    event_bus.publish(TodoDomainEvent.created(todo, "todo assistant"))

    binding = binding_store.get_binding(todo.id, "company-platform")
    assert binding is not None
    assert binding.external_id == "EXT-001"
    assert binding.external_url.endswith("EXT-001")

    todos_payload = json.loads((tmp_path / "todos.json").read_text(encoding="utf-8"))
    assert "external_id" not in json.dumps(todos_payload, ensure_ascii=False)


def test_script_handler_does_not_create_binding_without_external_id(tmp_path: Path):
    event_bus, binding_store = _build_event_bus(tmp_path, mode="return_no_id")
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )

    event_bus.publish(TodoDomainEvent.created(todo, "todo assistant"))

    assert binding_store.get_binding(todo.id, "company-platform") is None
    record = binding_store.get_record(todo.id, "company-platform")
    assert record is not None
    assert record.last_sync_status == "ok:noop"


def test_script_handler_can_backfill_binding_from_appended_event(tmp_path: Path):
    event_bus, binding_store = _build_event_bus(tmp_path, mode="late_bind")
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )
    updated = store.append_analysis_to_todo(
        todo.id,
        _snapshot("upload failed", "initial summary", "second follow-up"),
        "todo assistant",
    )

    assert updated is not None
    event_bus.publish(TodoDomainEvent.appended(updated, "todo assistant"))

    binding = binding_store.get_binding(todo.id, "company-platform")
    assert binding is not None
    assert binding.external_id == "EXT-LATE"


def test_script_handler_skips_unbound_non_create_events(tmp_path: Path):
    event_bus, binding_store = _build_event_bus(tmp_path, mode="late_bind")
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )

    event_bus.publish(TodoDomainEvent.completed(todo, "todo assistant"))

    assert binding_store.get_binding(todo.id, "company-platform") is None
    record = binding_store.get_record(todo.id, "company-platform")
    assert record is not None
    assert record.last_sync_status == "skipped:missing_binding"


def test_script_handler_keeps_existing_binding_when_ack_has_no_external_id(tmp_path: Path):
    event_bus, binding_store = _build_event_bus(tmp_path, mode="no_id_update")
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )
    binding_store.upsert_binding(
        todo.id,
        "company-platform",
        "EXT-KEEP",
        sync_status="ok:created",
    )

    reloaded = store.get_todo(todo.id)
    assert reloaded is not None
    event_bus.publish(TodoDomainEvent.completed(reloaded, "todo assistant"))

    binding = binding_store.get_binding(todo.id, "company-platform")
    assert binding is not None
    assert binding.external_id == "EXT-KEEP"
    assert binding.last_sync_status == "ok:updated"


def test_script_handler_invalid_ack_does_not_overwrite_existing_binding(tmp_path: Path):
    event_bus, binding_store = _build_event_bus(tmp_path, mode="invalid_json")
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )
    binding_store.upsert_binding(
        todo.id,
        "company-platform",
        "EXT-KEEP",
        sync_status="ok:created",
    )

    event_bus.publish(TodoDomainEvent.completed(todo, "todo assistant"))

    binding = binding_store.get_binding(todo.id, "company-platform")
    assert binding is not None
    assert binding.external_id == "EXT-KEEP"
    assert binding.last_sync_status == "failed:invalid_ack"


def test_script_handler_processes_updated_event_when_binding_exists(tmp_path: Path):
    event_bus, binding_store = _build_event_bus(tmp_path, mode="")
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )
    binding_store.upsert_binding(
        todo.id,
        "company-platform",
        "EXT-KEEP",
        sync_status="ok:created",
    )

    reloaded = store.get_todo(todo.id)
    assert reloaded is not None
    reloaded.title = "edited title"
    event_bus.publish(TodoDomainEvent.updated(reloaded, "todo assistant", ["title"]))

    binding = binding_store.get_binding(todo.id, "company-platform")
    assert binding is not None
    assert binding.external_id == "EXT-KEEP"
    assert binding.last_event_type == "updated"
    assert binding.last_sync_status == "ok:updated"


def test_script_handler_allows_manual_sync_without_existing_binding(tmp_path: Path):
    event_bus, binding_store = _build_event_bus(tmp_path, mode="late_bind")
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("upload failed", "initial summary", "first follow-up"),
        "todo assistant",
    )

    event_bus.publish(TodoDomainEvent.manual_sync(todo, "todo assistant"))

    binding = binding_store.get_binding(todo.id, "company-platform")
    assert binding is not None
    assert binding.external_id == "EXT-LATE"
    assert binding.last_event_type == "manual_sync"


def test_script_handler_sanitizes_surrogates_before_sending_event(tmp_path: Path):
    event_bus, binding_store = _build_logger_event_bus(tmp_path)
    todo = TodoItem(
        title="bad\udcae title",
        current_summary="summary with \udcaa surrogate",
        timeline=[TimelineEvent(content="timeline \udcae detail", scenario="todo assistant")],
    )

    event_bus.publish(TodoDomainEvent.created(todo, "todo assistant"))

    record = binding_store.get_record(todo.id, "company-platform")
    assert record is not None
    assert record.last_sync_status == "ok:logged"

    payload = json.loads((tmp_path / "event-log.json").read_text(encoding="utf-8"))
    assert payload["todo_snapshot"]["title"] == "bad\ufffd title"
    assert payload["todo_snapshot"]["current_summary"] == "summary with \ufffd surrogate"
    assert payload["todo_snapshot"]["timeline"][0]["content"] == "timeline \ufffd detail"


def test_script_handler_uses_ascii_safe_json_and_python_utf8_env(tmp_path: Path):
    event_bus, binding_store = _build_probe_event_bus(tmp_path)
    store = TodoStore(str(tmp_path / "todos.json"))
    todo = store.create_todo_from_analysis(
        _snapshot("中文💡标题", "中文💪摘要", "中文💮跟进"),
        "todo assistant",
    )

    event_bus.publish(TodoDomainEvent.created(todo, "todo assistant"))

    record = binding_store.get_record(todo.id, "company-platform")
    assert record is not None
    assert record.last_sync_status == "ok:logged"
    assert record.metadata["pythonioencoding"] == "utf-8"
    assert record.metadata["pythonutf8"] == "1"

    raw_stdin = (tmp_path / "raw-stdin.json").read_text(encoding="utf-8")
    assert "\\u4e2d\\u6587" in raw_stdin
    assert "\\ud83d\\udca1" in raw_stdin
    assert "中文" not in raw_stdin


def test_integration_subprocess_options_returns_hidden_window_flags_on_windows(monkeypatch):
    from aica import todo_events as module

    class _StartupInfo:
        def __init__(self) -> None:
            self.dwFlags = 0
            self.wShowWindow = None

    monkeypatch.setattr(module.os, "name", "nt", raising=False)
    monkeypatch.setattr(module.subprocess, "STARTUPINFO", _StartupInfo, raising=False)
    monkeypatch.setattr(module.subprocess, "STARTF_USESHOWWINDOW", 1, raising=False)
    monkeypatch.setattr(module.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)

    options = _integration_subprocess_options()

    assert options["creationflags"] == 0x08000000
    assert options["startupinfo"].dwFlags & 1
    assert options["startupinfo"].wShowWindow == 0


def test_integration_subprocess_options_returns_empty_on_non_windows(monkeypatch):
    from aica import todo_events as module

    monkeypatch.setattr(module.os, "name", "posix", raising=False)

    assert _integration_subprocess_options() == {}

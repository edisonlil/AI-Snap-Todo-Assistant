from __future__ import annotations

from datetime import datetime
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aica.control_panel as control_panel  # noqa: E402
from aica.config import ConfigManager  # noqa: E402
from aica.models import TicketSummaryFields  # noqa: E402
from aica.todo_models import TodoConclusion, TodoItem, TodoProjectLink, TodoStatus  # noqa: E402


class _Clipboard:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, value: str) -> None:
        self.text = value


class _FakeTodoStore:
    def __init__(self, todo: TodoItem) -> None:
        self._todo = todo
        self._deleted = False

    def list_todos(self, *, query: str = "", status: str = "open") -> list[TodoItem]:
        if self._deleted:
            return []
        normalized_status = str(status or TodoStatus.OPEN).strip().lower() or TodoStatus.OPEN
        if normalized_status == "all":
            return [self._todo]
        if normalized_status == "done_missing_ach":
            if self._todo.status == TodoStatus.DONE and not str(self._todo.summary_fields.ach_no or "").strip():
                return [self._todo]
            return []
        if normalized_status == "today_done":
            today = datetime.now().strftime("%Y-%m-%d")
            if self._todo.status == TodoStatus.DONE and str(self._todo.completed_at or "").startswith(today):
                return [self._todo]
            return []
        if str(self._todo.status or "").strip() == normalized_status:
            return [self._todo]
        return []

    def get_todo(self, todo_id: str) -> TodoItem | None:
        if self._deleted:
            return None
        if todo_id == self._todo.id:
            return self._todo
        return None

    def reopen_todo(self, todo_id: str) -> bool:
        if todo_id != self._todo.id:
            return False
        self._todo.status = TodoStatus.OPEN
        self._todo.completed_at = ""
        self._todo.updated_at = "2026-04-21T10:00:00"
        return True

    def delete_todo(self, todo_id: str) -> bool:
        if self._deleted or todo_id != self._todo.id:
            return False
        self._deleted = True
        return True

    def update_todo(self, todo_id: str, *, summary_fields: TicketSummaryFields) -> TodoItem | None:
        if self._deleted or todo_id != self._todo.id:
            return None
        self._todo.summary_fields = summary_fields
        self._todo.updated_at = "2026-04-21T10:05:00"
        return self._todo

    def relink_open_unresolved_todos(self) -> int:
        return 0


class _FakeProjectRepository:
    def list_projects(self, *, query: str = "", include_expired: bool = True) -> list[object]:
        return []


def _build_todo() -> TodoItem:
    return TodoItem(
        id="ticket-1",
        title="copy ticket test",
        current_summary="copy ticket test summary",
        summary_fields=TicketSummaryFields(
            group_name="test-group",
            environment="prod",
            ticket_type="investigation",
        ),
        conclusion=TodoConclusion(content="resolved"),
        project_link=TodoProjectLink(
            project_snapshot={
                "project_name": "Demo Project",
                "customer_name": "Demo Customer",
                "task_order_no": "WO-001",
            }
        ),
    )


def _build_bridge(monkeypatch: pytest.MonkeyPatch, todo: TodoItem) -> control_panel._ControlPanelBridge:
    temp_dir = Path(tempfile.mkdtemp(prefix="control-panel-", dir=Path.cwd()))

    monkeypatch.setattr(control_panel, "AnalysisMetricsStore", lambda: SimpleNamespace())
    monkeypatch.setattr(
        control_panel,
        "AnalysisRulesManager",
        lambda: SimpleNamespace(config=SimpleNamespace(scene_rules={"default": {}})),
    )
    monkeypatch.setattr(control_panel, "PromptDebugStore", lambda: SimpleNamespace(list_records=lambda limit=1: []))
    monkeypatch.setattr(control_panel, "load_integration_config", lambda _path: {})
    monkeypatch.setattr(control_panel, "list_script_integrations", lambda _payload: [])
    monkeypatch.setattr(control_panel, "SQLiteProjectRepository", lambda _path: _FakeProjectRepository())
    monkeypatch.setattr(control_panel, "TodoStore", lambda _path: _FakeTodoStore(todo))
    monkeypatch.setattr(control_panel, "app_data_dir", lambda: temp_dir)
    monkeypatch.setattr(control_panel, "log_dir", lambda: temp_dir / "logs")
    monkeypatch.setattr(control_panel, "aica_database_file", lambda: temp_dir / "aica.db")
    monkeypatch.setattr(control_panel, "integrations_file", lambda: temp_dir / "integrations.json")

    return control_panel._ControlPanelBridge(ConfigManager(str(temp_dir / "config.json")))


def _notification_messages(bridge: control_panel._ControlPanelBridge) -> list[str]:
    return [str(item["message"]) for item in bridge.notificationBridge.notifications]


def test_copy_ticket_keeps_success_message_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    clipboard = _Clipboard()

    monkeypatch.setattr(control_panel.QApplication, "clipboard", lambda: clipboard)
    bridge = _build_bridge(monkeypatch, todo)
    bridge._status_message = "should be cleared"

    bridge.copyTicket(todo.id)

    assert "copy ticket test" in clipboard.text
    assert bridge.statusMessage == ""
    assert bridge.errorMessage == ""
    assert _notification_messages(bridge) == ["工单内容已复制"]


def test_reopen_selected_ticket_updates_detail_and_respects_done_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    todo = _build_todo()
    todo.status = TodoStatus.DONE
    todo.completed_at = "2026-04-21T09:30:00"
    todo.updated_at = todo.completed_at

    bridge = _build_bridge(monkeypatch, todo)
    refresh_events: list[str] = []
    bridge.todoListRefreshRequested.connect(lambda: refresh_events.append("refresh"))

    bridge.listTickets("", "done")
    bridge.openTicketDetail(todo.id)
    bridge.reopenSelectedTicket()

    assert bridge.ticketStatusFilter == "done"
    assert bridge.selectedTicket["id"] == todo.id
    assert bridge.selectedTicket["status"] == TodoStatus.OPEN
    assert bridge.selectedTicket["statusLabel"] == "进行中"
    assert bridge.selectedTicket["completedAt"] == ""
    assert bridge.selectedTicket["completedAtLabel"] == ""
    assert bridge.tickets == []
    assert refresh_events == ["refresh"]
    assert _notification_messages(bridge)[-1] == "工单已重新打开"

    bridge.backToTicketList()

    assert bridge.selectedTicket["id"] == ""
    assert bridge.tickets == []


def test_save_selected_ticket_field_pushes_success_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("ach_no", "ACH-2026")

    assert bridge.selectedTicket["achNo"] == "ACH-2026"
    assert _notification_messages(bridge)[-1] == "ach单号已保存"


def test_refresh_selected_ticket_feature_point_pushes_error_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    todo = _build_todo()
    todo.summary_fields.product_line = ""
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)

    bridge.refreshSelectedTicketFeaturePoint()

    assert _notification_messages(bridge)[-1] == "缺少产品线，无法刷新功能点。"


def test_delete_selected_ticket_pushes_success_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)

    bridge.deleteSelectedTicket()

    assert bridge.selectedTicket["id"] == ""
    assert bridge.tickets == []
    assert _notification_messages(bridge)[-1] == "工单已删除：copy ticket test"

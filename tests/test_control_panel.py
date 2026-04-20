from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aica.control_panel as control_panel  # noqa: E402
from aica.config import ConfigManager  # noqa: E402
from aica.models import TicketSummaryFields  # noqa: E402
from aica.todo_models import TodoConclusion, TodoItem, TodoProjectLink  # noqa: E402


class _Clipboard:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, value: str) -> None:
        self.text = value


class _FakeTodoStore:
    def __init__(self, todo: TodoItem) -> None:
        self._todo = todo

    def list_todos(self, *, query: str = "", status: str = "open") -> list[TodoItem]:
        return [self._todo]

    def get_todo(self, todo_id: str) -> TodoItem | None:
        if todo_id == self._todo.id:
            return self._todo
        return None

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


def test_copy_ticket_keeps_success_message_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    clipboard = _Clipboard()
    temp_dir = Path(tempfile.mkdtemp(prefix="control-panel-", dir=Path.cwd()))

    monkeypatch.setattr(control_panel.QApplication, "clipboard", lambda: clipboard)
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

    bridge = control_panel._ControlPanelBridge(ConfigManager(str(temp_dir / "config.json")))
    bridge._status_message = "should be cleared"

    bridge.copyTicket(todo.id)

    assert "copy ticket test" in clipboard.text
    assert bridge.statusMessage == ""
    assert bridge.errorMessage == ""

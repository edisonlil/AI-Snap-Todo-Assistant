from pathlib import Path

from aica.analysis_rules import AnalysisRuleConfig
from aica.config import ConfigManager
from aica.control_panel import _ControlPanelBridge
from aica.models import TicketSnapshot, TicketSummaryFields
from aica.storage.contracts import ProjectRecord
from aica.storage.sqlite.repositories import SQLiteProjectRepository
from aica.todo_store import TodoStore


class _StubAnalysisRulesManager:
    def __init__(self):
        self.config = AnalysisRuleConfig()

    def reload(self):
        return self.config

    def update_debug_config(self, enabled, max_records):
        self.config.debug.enabled = bool(enabled)
        self.config.debug.max_records = int(max_records)

    def update_scene_user_rules(self, scene_type, rules):
        self.config.scene_rules[scene_type] = rules

    def update_scene_rule(self, scene_type, rule):
        self.config.scenes[scene_type] = rule

    def save(self):
        return self.config


class _StubPromptDebugStore:
    def list_records(self, limit=60):
        return []

    def load_record(self, trace_id):
        return None


def _snapshot(title: str, summary: str, timeline: str, *, group_name: str) -> TicketSnapshot:
    return TicketSnapshot(
        title=title,
        fields=TicketSummaryFields(
            group_name=group_name,
            environment="prod",
            product_line="",
            ticket_type="incident",
        ),
        current_summary=summary,
        timeline_entry=timeline,
    )


def test_control_panel_bridge_exposes_ticket_section_and_detail(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "aica.db"
    config_path = tmp_path / "config.json"
    integrations_path = tmp_path / "integrations.json"
    analysis_rules_path = tmp_path / "analysis_rules.json"
    prompt_debug_path = tmp_path / "prompt_debug"
    data_dir = tmp_path / "data"
    log_dir = tmp_path / "logs"

    monkeypatch.setattr("aica.control_panel.AnalysisRulesManager", _StubAnalysisRulesManager)
    monkeypatch.setattr("aica.control_panel.PromptDebugStore", _StubPromptDebugStore)
    monkeypatch.setattr("aica.control_panel.aica_database_file", lambda: db_path)
    monkeypatch.setattr("aica.control_panel.integrations_file", lambda: integrations_path)
    monkeypatch.setattr("aica.control_panel.analysis_rules_file", lambda: analysis_rules_path)
    monkeypatch.setattr("aica.control_panel.prompt_debug_dir", lambda: prompt_debug_path)
    monkeypatch.setattr("aica.control_panel.storage_config_file", lambda: tmp_path / "storage.json")
    monkeypatch.setattr("aica.control_panel.config_file", lambda: config_path)
    monkeypatch.setattr("aica.control_panel.app_data_dir", lambda: data_dir)
    monkeypatch.setattr("aica.control_panel.log_dir", lambda: log_dir)
    monkeypatch.setattr("aica.control_panel.error_log_file", lambda: log_dir / "error.log")
    monkeypatch.setattr("aica.control_panel.feedback_dir", lambda: data_dir / "feedback")
    monkeypatch.setattr("aica.control_panel.load_integration_config", lambda path: {})
    monkeypatch.setattr("aica.control_panel.list_script_integrations", lambda payload: [])

    repository = SQLiteProjectRepository(db_path)
    repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Phoenix Project",
            task_order_no="WO-1",
            product_version="v1",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("support-room",),
        )
    )
    store = TodoStore(str(db_path))
    open_todo = store.create_todo_from_analysis(
        _snapshot("login failed", "need follow-up", "first timeline", group_name="support-room"),
        "todo assistant",
    )
    done_todo = store.create_todo_from_analysis(
        _snapshot("closed incident", "resolved", "closed timeline", group_name="archive-room"),
        "todo assistant",
    )
    assert store.complete_todo(done_todo.id) is True

    bridge = _ControlPanelBridge(ConfigManager(str(config_path)))

    business_group = next(group for group in bridge.sectionGroups if group["id"] == "business")
    assert [item["id"] for item in business_group["items"]] == ["projects", "tickets"]
    assert bridge.currentSectionMeta["title"]

    bridge.setCurrentSection("tickets")
    assert bridge.currentSection == "tickets"
    assert bridge.currentSectionMeta["primaryActionLabel"] == "刷新列表"
    assert [item["id"] for item in bridge.tickets] == [open_todo.id]

    bridge.listTickets("closed", "all")
    assert [item["id"] for item in bridge.tickets] == [done_todo.id]

    bridge.openTicketDetail(open_todo.id)
    assert bridge.selectedTicket["id"] == open_todo.id
    assert bridge.selectedTicket["projectName"] == "Phoenix Project"
    assert bridge.selectedTicket["projectStatus"] == "matched"
    assert bridge.selectedTicket["ticketVersion"] == "v1"
    assert bridge.selectedTicket["projectSnapshotVersion"] == "v1"
    assert bridge.selectedTicket["timeline"][0]["content"] == "first timeline"

    bridge.saveSelectedTicketVersion("v1-hotfix")
    assert bridge.selectedTicket["ticketVersion"] == "v1-hotfix"
    assert bridge.selectedTicket["projectSnapshotVersion"] == "v1"

    saved_todo = store.get_todo(open_todo.id)
    assert saved_todo is not None
    assert saved_todo.summary_fields.ticket_version == "v1-hotfix"
    assert repository.get_project_by_task_order_no("WO-1").product_version == "v1"

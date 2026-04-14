from pathlib import Path

from aica.analysis_rules import AnalysisRuleConfig
from aica.config import ConfigManager
from aica.control_panel import _ControlPanelBridge
from aica.models import TicketSnapshot, TicketSummaryFields, UNKNOWN_TEXT
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


def _snapshot(title: str, summary: str, timeline: str, *, group_name: str, product_line: str = "") -> TicketSnapshot:
    return TicketSnapshot(
        title=title,
        fields=TicketSummaryFields(
            group_name=group_name,
            environment="prod",
            product_line=product_line,
            ticket_type="incident",
        ),
        current_summary=summary,
        timeline_entry=timeline,
    )


def _patch_control_panel_dependencies(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
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
    return db_path, config_path


def test_control_panel_bridge_exposes_ticket_section_and_detail(monkeypatch, tmp_path: Path):
    db_path, config_path = _patch_control_panel_dependencies(monkeypatch, tmp_path)

    provider_calls = []

    class _StubFeaturePointProvider:
        def resolve(self, *, product_line: str, problem_desc: str):
            provider_calls.append((product_line, problem_desc))
            return type("FeaturePointResult", (), {"value": "login-module", "error_message": ""})()

    monkeypatch.setattr("aica.control_panel.build_feature_point_provider", lambda config: _StubFeaturePointProvider())

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
        _snapshot("login failed", "need follow-up", "first timeline", group_name="support-room", product_line="AICA"),
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
    assert bridge.selectedTicket["productLine"] == "AICA"
    assert bridge.selectedTicket["ticketVersion"] == "v1"
    assert bridge.selectedTicket["achNo"] == ""
    assert bridge.selectedTicket["projectSnapshotVersion"] == "v1"
    assert bridge.selectedTicket["timeline"][0]["content"] == "first timeline"

    bridge.refreshSelectedTicketFeaturePoint()
    assert bridge.selectedTicket["featurePoint"] == "login-module"
    assert bridge.statusMessage == "功能点已刷新"
    assert provider_calls == [("AICA", "need follow-up")]
    refreshed_todo = store.get_todo(open_todo.id)
    assert refreshed_todo is not None
    assert refreshed_todo.summary_fields.feature_point == "login-module"
    assert refreshed_todo.summary_fields.feature_point_source == "auto"

    bridge.saveSelectedTicketField("ach_no", "ACH-2026-001")
    bridge.saveSelectedTicketVersion("v1-hotfix")
    assert bridge.selectedTicket["ticketVersion"] == "v1-hotfix"
    assert bridge.selectedTicket["achNo"] == "ACH-2026-001"
    assert bridge.selectedTicket["achFilledAt"]
    first_ach_filled_at = bridge.selectedTicket["achFilledAt"]
    assert bridge.selectedTicket["projectSnapshotVersion"] == "v1"

    bridge.saveSelectedTicketField("ach_no", "ACH-2026-002")
    assert bridge.selectedTicket["achNo"] == "ACH-2026-002"
    assert bridge.selectedTicket["achFilledAt"] == first_ach_filled_at

    bridge.saveSelectedTicketField("feature_point", "导出模块")
    bridge.saveSelectedTicketField("root_cause", "配置错误")
    bridge.saveSelectedTicketField("root_cause_desc", "导出接口参数错误")

    assert bridge.selectedTicket["featurePoint"] == "导出模块"
    assert bridge.selectedTicket["rootCause"] == "配置错误"
    assert bridge.selectedTicket["rootCauseDesc"] == "导出接口参数错误"

    saved_todo = store.get_todo(open_todo.id)
    assert saved_todo is not None
    assert saved_todo.summary_fields.ach_no == "ACH-2026-002"
    assert saved_todo.summary_fields.ach_filled_at == first_ach_filled_at
    assert saved_todo.summary_fields.ticket_version == "v1-hotfix"
    assert saved_todo.summary_fields.feature_point == "导出模块"
    assert saved_todo.summary_fields.feature_point_source == "manual"
    assert saved_todo.summary_fields.root_cause == "配置错误"
    assert saved_todo.summary_fields.root_cause_source == "manual"
    assert saved_todo.summary_fields.root_cause_desc == "导出接口参数错误"
    assert saved_todo.summary_fields.root_cause_desc_source == "manual"
    assert repository.get_project_by_task_order_no("WO-1").product_version == "v1"

    bridge.saveSelectedTicketField("ach_no", "")
    assert bridge.selectedTicket["achNo"] == ""
    assert bridge.selectedTicket["achFilledAt"] == ""

    bridge.listTickets("", "done_missing_ach")
    assert [item["id"] for item in bridge.tickets] == [done_todo.id]


def test_control_panel_feature_point_refresh_requires_product_line(monkeypatch, tmp_path: Path):
    db_path, config_path = _patch_control_panel_dependencies(monkeypatch, tmp_path)

    provider_calls = []

    class _StubFeaturePointProvider:
        def resolve(self, *, product_line: str, problem_desc: str):
            provider_calls.append((product_line, problem_desc))
            return type("FeaturePointResult", (), {"value": "unused", "error_message": ""})()

    monkeypatch.setattr("aica.control_panel.build_feature_point_provider", lambda config: _StubFeaturePointProvider())

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

    bridge = _ControlPanelBridge(ConfigManager(str(config_path)))
    bridge.setCurrentSection("tickets")
    bridge.openTicketDetail(open_todo.id)

    assert bridge.selectedTicket["productLine"] == UNKNOWN_TEXT

    bridge.refreshSelectedTicketFeaturePoint()

    assert provider_calls == []
    assert "产品线" in bridge.errorMessage
    assert bridge.selectedTicket["featurePoint"] == ""


def test_control_panel_feature_point_refresh_keeps_existing_value_when_provider_returns_empty(monkeypatch, tmp_path: Path):
    db_path, config_path = _patch_control_panel_dependencies(monkeypatch, tmp_path)

    provider_calls = []

    class _StubFeaturePointProvider:
        def resolve(self, *, product_line: str, problem_desc: str):
            provider_calls.append((product_line, problem_desc))
            return type("FeaturePointResult", (), {"value": "", "error_message": ""})()

    monkeypatch.setattr("aica.control_panel.build_feature_point_provider", lambda config: _StubFeaturePointProvider())

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
        _snapshot("login failed", "need follow-up", "first timeline", group_name="support-room", product_line="AICA"),
        "todo assistant",
    )
    updated_todo = store.update_todo(
        open_todo.id,
        summary_fields=TicketSummaryFields.from_dict(
            {
                **open_todo.summary_fields.to_dict(),
                "feature_point": "existing-point",
                "feature_point_source": "manual",
            }
        ),
    )
    assert updated_todo is not None

    bridge = _ControlPanelBridge(ConfigManager(str(config_path)))
    bridge.setCurrentSection("tickets")
    bridge.openTicketDetail(open_todo.id)

    bridge.refreshSelectedTicketFeaturePoint()

    assert provider_calls == [("AICA", "need follow-up")]
    assert "有效结果" in bridge.errorMessage
    assert bridge.selectedTicket["featurePoint"] == "existing-point"
    refreshed_todo = store.get_todo(open_todo.id)
    assert refreshed_todo is not None
    assert refreshed_todo.summary_fields.feature_point == "existing-point"
    assert refreshed_todo.summary_fields.feature_point_source == "manual"

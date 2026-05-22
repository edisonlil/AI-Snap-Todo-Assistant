from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aica.control_panel as control_panel  # noqa: E402
from aica.analysis.metrics import ModelLatencySummary  # noqa: E402
from aica.config import ConfigManager  # noqa: E402
from aica.environment_access import EnvironmentAccessEntryRecord, ProjectEnvironmentBundle, ProjectEnvironmentRecord  # noqa: E402
from aica.models import TicketSummaryFields  # noqa: E402
from aica.otp_secret_extractor import OtpSecretExtractResult  # noqa: E402
from aica.todo.models import TodoConclusion, TodoItem, TodoProjectLink, TodoStatus  # noqa: E402


class _Clipboard:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, value: str) -> None:
        self.text = value


class _TextClipboard:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text

    def image(self) -> object | None:
        return None

    def mimeData(self) -> object | None:
        return None


class _FakeTodoStore:
    def __init__(self, todo: TodoItem) -> None:
        self._todo = todo
        self._deleted = False
        self._unlink_should_fail = False

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

    def unlink_todo_project(self, todo_id: str) -> TodoItem | None:
        if self._unlink_should_fail or self._deleted or todo_id != self._todo.id:
            return None
        self._todo.summary_fields = TicketSummaryFields.from_dict(
            {
                **self._todo.summary_fields.to_dict(),
                "product_line": "",
                "ticket_version": "",
            }
        )
        self._todo.project_link = TodoProjectLink(todo_id=self._todo.id)
        self._todo.updated_at = "2026-04-21T10:10:00"
        return self._todo

    def relink_open_unresolved_todos(self) -> int:
        return 0

    def relink_open_unresolved_todos_by_aliases(self, _aliases: list[str]) -> int:
        return 0


class _FakeProjectRepository:
    def list_projects(self, *, query: str = "", include_expired: bool = True) -> list[object]:
        return []

    def get_project_by_task_order_no(self, task_order_no: str) -> object | None:
        return None

    def upsert_project(self, project: object) -> object:
        return project

    def delete_project(self, project_id: str) -> bool:
        return True


class _FakeEnvironmentRepository:
    def __init__(self) -> None:
        self._environments: dict[str, ProjectEnvironmentRecord] = {}
        self._entries_by_environment: dict[str, list[EnvironmentAccessEntryRecord]] = {}
        self._entries_by_id: dict[str, EnvironmentAccessEntryRecord] = {}

    @property
    def path(self) -> str:
        return ""

    def list_global_environments(self, *, include_inactive: bool = False) -> list[ProjectEnvironmentBundle]:
        return self._list_by_scope("global")

    def list_project_environments(self, project_id: str, *, include_inactive: bool = False) -> list[ProjectEnvironmentBundle]:
        return self._list_by_scope("project", project_id=project_id)

    def list_effective_environments(self, project_id: str, *, include_inactive: bool = False) -> list[ProjectEnvironmentBundle]:
        return [*self.list_project_environments(project_id), *self.list_global_environments()]

    def _list_by_scope(self, scope: str, *, project_id: str = "") -> list[ProjectEnvironmentBundle]:
        bundles: list[ProjectEnvironmentBundle] = []
        for environment in self._environments.values():
            if environment.scope != scope:
                continue
            if scope == "project" and environment.project_id != project_id:
                continue
            bundles.append(
                ProjectEnvironmentBundle(
                    environment=environment,
                    source_scope=environment.scope,
                    entries=tuple(self._entries_by_environment.get(environment.id, [])),
                )
            )
        return bundles

    def get_project_environment(self, environment_id: str) -> ProjectEnvironmentRecord | None:
        return self._environments.get(environment_id)

    def get_access_entry(self, entry_id: str) -> EnvironmentAccessEntryRecord | None:
        return self._entries_by_id.get(entry_id)

    def upsert_project_environment(self, environment: ProjectEnvironmentRecord) -> ProjectEnvironmentRecord:
        next_id = environment.id or f"env-{len(self._environments) + 1}"
        saved = ProjectEnvironmentRecord(
            id=next_id,
            project_id=environment.project_id,
            env_name=environment.env_name,
            scope=environment.scope,
            env_type=environment.env_type,
            sort_order=environment.sort_order,
            is_active=environment.is_active,
            note=environment.note,
            created_at=environment.created_at,
            updated_at=environment.updated_at,
        )
        self._environments[next_id] = saved
        self._entries_by_environment.setdefault(next_id, [])
        return saved

    def replace_access_entries(
        self,
        environment_id: str,
        entries: list[EnvironmentAccessEntryRecord],
    ) -> list[EnvironmentAccessEntryRecord]:
        old_entries = self._entries_by_environment.get(environment_id, [])
        for item in old_entries:
            self._entries_by_id.pop(item.id, None)

        saved_entries: list[EnvironmentAccessEntryRecord] = []
        for index, entry in enumerate(entries, start=1):
            entry_id = entry.id or f"{environment_id}-entry-{index}"
            saved = EnvironmentAccessEntryRecord(
                id=entry_id,
                environment_id=environment_id,
                access_name=entry.access_name,
                scope=entry.scope,
                source_scope=entry.source_scope,
                is_project_override=entry.is_project_override,
                access_type=entry.access_type,
                url_or_host=entry.url_or_host,
                username=entry.username,
                password_encrypted=entry.password_encrypted,
                otp_secret_encrypted=entry.otp_secret_encrypted,
                requires_otp=entry.requires_otp,
                note=entry.note,
                open_command=entry.open_command,
                sort_order=entry.sort_order,
                is_active=entry.is_active,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
            saved_entries.append(saved)
            self._entries_by_id[entry_id] = saved
        self._entries_by_environment[environment_id] = saved_entries
        return saved_entries

    def delete_project_environment(self, environment_id: str) -> bool:
        removed = self._environments.pop(environment_id, None)
        for item in self._entries_by_environment.pop(environment_id, []):
            self._entries_by_id.pop(item.id, None)
        return removed is not None


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
    fake_environment_repository = _FakeEnvironmentRepository()

    monkeypatch.setattr(control_panel, "AnalysisMetricsStore", lambda: SimpleNamespace())
    monkeypatch.setattr(
        control_panel,
        "AnalysisRulesManager",
        lambda: SimpleNamespace(config=SimpleNamespace(scene_rules={"default": {}}), reload=lambda: SimpleNamespace(scene_rules={"default": {}})),
    )
    monkeypatch.setattr(control_panel, "PromptDebugStore", lambda: SimpleNamespace(list_records=lambda limit=1: [], load_record=lambda _id: None))
    monkeypatch.setattr(control_panel, "load_integration_config", lambda _path: {})
    monkeypatch.setattr(control_panel, "list_script_integrations", lambda _payload: [])
    monkeypatch.setattr(control_panel, "SQLiteProjectRepository", lambda _path: _FakeProjectRepository())
    monkeypatch.setattr(control_panel, "SQLiteProjectEnvironmentRepository", lambda _path: fake_environment_repository)
    monkeypatch.setattr(control_panel, "TodoStore", lambda _path: _FakeTodoStore(todo))
    monkeypatch.setattr(control_panel, "app_data_dir", lambda: temp_dir)
    monkeypatch.setattr(control_panel, "log_dir", lambda: temp_dir / "logs")
    monkeypatch.setattr(control_panel, "aica_database_file", lambda: temp_dir / "aica.db")
    monkeypatch.setattr(control_panel, "integrations_file", lambda: temp_dir / "integrations.json")

    return control_panel._ControlPanelBridge(ConfigManager(str(temp_dir / "config.json")))


def _notification_messages(bridge: control_panel._ControlPanelBridge) -> list[str]:
    return [str(item["message"]) for item in bridge.notificationBridge.notifications]


def test_task_bindings_use_readable_chinese_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge._analysis_metrics = SimpleNamespace(get_summary=lambda *_args: None)

    bindings = {item["id"]: item for item in bridge.taskBindings}

    assert bindings["analysis"]["label"] == "截图分析"
    assert bindings["plan_export"]["label"] == "方案导出"
    assert bindings["context_summary"]["label"] == "上下文摘要"
    assert bindings["log_analysis"]["label"] == "日志分析"
    assert {item["performanceSummary"] for item in bindings.values()} == {"暂无耗时样本"}


def test_plan_export_model_options_include_text_only_models(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge._analysis_metrics = SimpleNamespace(get_summary=lambda *_args: None)

    options = bridge._build_model_options("plan_export", "siliconflow")  # noqa: SLF001

    values = {item["value"] for item in options}
    assert "qwen25-vl-72b" in values
    assert "qwen3-8b" in values


def test_model_options_show_name_only_and_keep_details(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge._analysis_metrics = SimpleNamespace(
        get_summary=lambda *_args: ModelLatencySummary(
            sample_count=3,
            success_count=3,
            last_latency_ms=432,
            avg_latency_ms=666,
            p90_latency_ms=1200,
        )
    )

    options = bridge._build_model_options("analysis", "siliconflow")  # noqa: SLF001
    option = next(item for item in options if item["value"] == "qwen25-vl-72b")

    assert option["text"] == "Qwen/Qwen2.5-VL-72B-Instruct"
    assert "vision_chat" in option["details"]
    assert "最近 432ms" in option["details"]


def test_model_options_use_middle_dot_metric_separator() -> None:
    label = control_panel._append_metric_suffix(
        "Qwen/Qwen2.5-VL-72B-Instruct (vision_chat, text_chat)",
        ModelLatencySummary(
            sample_count=20,
            success_count=20,
            last_latency_ms=8200,
            avg_latency_ms=10300,
            p90_latency_ms=12300,
        ),
    )

    assert " · 最近 8.2s · 平均 10.3s · P90 12.3s · 样本 20" in label
    assert " 路 " not in label


def test_import_otp_qr_image_path_accepts_file_url(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    image_path = Path.cwd() / "otp.png"

    def fake_extract(path: object) -> OtpSecretExtractResult:
        assert str(path).replace("\\", "/").endswith("/otp.png")
        return OtpSecretExtractResult(
            type="totp",
            secret="JBSWY3DPEHPK3PXP",
            raw_payload="otpauth://totp/demo:admin?secret=JBSWY3DPEHPK3PXP",
        )

    monkeypatch.setattr(control_panel, "extract_otp_secret_from_qr_image", fake_extract)

    result = bridge.importOtpConfigFromQrImagePath(image_path.as_uri())

    assert result["success"] is True
    assert result["otpConfig"].startswith("otpauth://")
    assert str(result["previewImageUrl"]).startswith("file:///")
    assert result["source"] == "drop"
    assert bridge.statusMessage == "OTP 配置已从拖拽二维码导入"


def test_import_otp_from_clipboard_text(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    monkeypatch.setattr(
        control_panel.QApplication,
        "clipboard",
        lambda: _TextClipboard("otpauth://totp/demo:admin?secret=JBSWY3DPEHPK3PXP"),
    )

    result = bridge.importOtpConfigFromClipboardQr()

    assert result["success"] is True
    assert result["secret"] == "JBSWY3DPEHPK3PXP"
    assert result["previewImageUrl"] == ""
    assert result["source"] == "clipboard_text"
    assert bridge.statusMessage == "OTP 配置已从剪贴板导入"


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
    assert _notification_messages(bridge)


def test_control_panel_readable_chinese_copy_and_locations(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    copy_text = control_panel._format_ticket_copy_text(
        {
            "title": "标题A",
            "conclusionContent": "结论B",
            "customerName": "客户C",
            "projectName": "项目D",
            "featurePoint": "功能E",
            "ticketVersion": "V7",
            "rootCause": "分类F",
            "rootCauseDesc": "描述G",
            "productLine": "文档中台",
            "summary": "说明H",
        }
    )

    assert "标题: 标题A" in copy_text
    assert "项目名称: 项目D" in copy_text
    assert "产品: 文档中台/V7" in copy_text
    assert [item["title"] for item in bridge.locations] == [
        "本地数据目录",
        "知识库归档目录",
        "反馈目录",
        "分析规则文件",
        "Prompt 调试目录",
        "错误日志目录",
        "脚本集成配置目录",
    ]
    locations = {item["id"]: item for item in bridge.locations}
    assert locations["knowledge_base_dir"]["description"].endswith("knowledge_base")


def test_server_config_updates_and_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.updateProviderField("siliconflow", "api_key", "model-key")
    bridge.updateServerField("enabled", "true")
    bridge.updateServerField("base_url", "https://server.example.com")
    bridge.updateServerField("api_key", "server-key")
    bridge.updateServerField("timeout_seconds", "45")

    assert bridge.serverConfig == {
        "enabled": True,
        "baseUrl": "https://server.example.com",
        "apiKey": "server-key",
        "timeoutSeconds": "45",
    }

    bridge.saveConfig()

    saved = bridge._config_manager.load()
    assert saved.server.enabled is True
    assert saved.server.base_url == "https://server.example.com"
    assert saved.server.api_key == "server-key"
    assert saved.server.timeout_seconds == 45
    assert bridge.statusMessage


def test_server_config_rejects_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.updateProviderField("siliconflow", "api_key", "model-key")
    bridge.updateServerField("timeout_seconds", "0")
    bridge.saveConfig()

    assert "服务端超时时间" in bridge.errorMessage


def test_reopen_selected_ticket_updates_detail_and_respects_done_filter(monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert bridge.selectedTicket["completedAt"] == ""
    assert bridge.tickets == []
    assert refresh_events == ["refresh"]
    assert _notification_messages(bridge)

    bridge.backToTicketList()

    assert bridge.selectedTicket["id"] == ""
    assert bridge.tickets == []


def test_save_selected_ticket_field_pushes_success_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("ach_no", "ACH-2026")

    assert bridge.selectedTicket["achNo"] == "ACH-2026"
    assert _notification_messages(bridge)


def test_external_ticket_refresh_updates_list_and_selected_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)
    refresh_events: list[str] = []
    bridge.todoListRefreshRequested.connect(lambda: refresh_events.append("refresh"))

    todo.title = "updated title"
    todo.current_summary = "updated summary"
    todo.summary_fields = TicketSummaryFields.from_dict(
        {
            **todo.summary_fields.to_dict(),
            "ach_no": "ACH-2026",
        }
    )

    bridge.refresh_ticket_payloads_from_store()

    assert bridge.tickets[0]["title"] == "updated title"
    assert bridge.selectedTicket["currentSummary"] == "updated summary"
    assert bridge.selectedTicket["achNo"] == "ACH-2026"
    assert refresh_events == []
    assert _notification_messages(bridge) == []


def test_unlink_selected_ticket_project_updates_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.summary_fields.product_line = "WPS协作"
    todo.summary_fields.ticket_version = "release_dc_v7"
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="matched",
        matched_alias="test-group",
        project_snapshot={
            "project_id": "project-1",
            "project_name": "Demo Project",
            "customer_name": "Demo Customer",
            "task_order_no": "WO-001",
            "product_line": "WPS协作",
            "product_version": "release_dc_v7",
            "project_manager": "Alice",
        },
    )
    bridge = _build_bridge(monkeypatch, todo)
    refresh_events: list[str] = []
    bridge.todoListRefreshRequested.connect(lambda: refresh_events.append("refresh"))

    bridge.openTicketDetail(todo.id)
    bridge.unlinkSelectedTicketProject()

    assert bridge.selectedTicket["id"] == todo.id
    assert bridge.selectedTicket["projectStatus"] == ""
    assert bridge.selectedTicket["projectStatusLabel"] == "未匹配项目"
    assert bridge.selectedTicket["projectName"] == ""
    assert bridge.selectedTicket["customerName"] == ""
    assert bridge.selectedTicket["taskOrderNo"] == ""
    assert bridge.selectedTicket["projectManager"] == ""
    assert bridge.selectedTicket["productLine"] == ""
    assert bridge.selectedTicket["ticketVersion"] == ""
    assert bridge.statusMessage == "已解除项目关联"
    assert bridge.errorMessage == ""
    assert refresh_events == ["refresh"]
    assert _notification_messages(bridge)


def test_unlink_selected_ticket_project_failure_pushes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)
    bridge._todo_store._unlink_should_fail = True  # noqa: SLF001

    bridge.unlinkSelectedTicketProject()

    assert bridge.selectedTicket["id"] == todo.id
    assert bridge.errorMessage == "解除关联失败，请稍后重试。"
    assert bridge.statusMessage == ""


def test_unlink_selected_ticket_project_without_selection_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.unlinkSelectedTicketProject()

    assert bridge.selectedTicket["id"] == ""
    assert bridge.errorMessage == ""


def test_refresh_selected_ticket_feature_point_pushes_error_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.summary_fields.product_line = ""
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)

    bridge.refreshSelectedTicketFeaturePoint()

    assert bridge.errorMessage


def test_legacy_environment_sections_map_to_unified_section(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.setCurrentSection("project_environments")
    assert bridge.currentSection == "environments"
    assert bridge.environmentScopeFilter == "project"

    bridge.setCurrentSection("global_environments")
    assert bridge.currentSection == "environments"
    assert bridge.environmentScopeFilter == "global"


def test_logo_source_uses_runtime_asset_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    asset_path = Path.cwd() / "assets" / "aica_icon.png"
    bridge = _build_bridge(monkeypatch, todo)

    monkeypatch.setattr(control_panel, "asset_file", lambda _name: asset_path)

    assert bridge.logoSource == asset_path.as_uri()
    assert bridge.refreshFeaturePointIconSource == asset_path.as_uri()


def test_delete_selected_ticket_pushes_success_notification(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)

    bridge.deleteSelectedTicket()

    assert bridge.selectedTicket["id"] == ""
    assert bridge.tickets == []
    assert _notification_messages(bridge)


def test_global_environment_crud_and_qr_import(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.saveGlobalEnvironment(
        {
            "name": "253-environment",
            "type": "shared",
            "note": "shared env",
            "sortOrder": 0,
            "isActive": True,
        }
    )

    assert bridge.globalEnvironmentGroups[0]["name"] == "253-environment"
    assert "entries" not in bridge.globalEnvironmentGroups[0]
    environment_id = str(bridge.globalEnvironmentGroups[0]["id"])

    monkeypatch.setattr(
        control_panel.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(Path.cwd() / "otp.png"), "png"),
    )
    monkeypatch.setattr(
        control_panel,
        "extract_otp_secret_from_qr_image",
        lambda _path: SimpleNamespace(
            secret="JBSWY3DPEHPK3PXP",
            issuer="demo",
            account="demo",
            algorithm="SHA1",
            digits=6,
            period=30,
            label="demo",
            raw_payload="otpauth://totp/demo?secret=JBSWY3DPEHPK3PXP",
        ),
    )

    result = bridge.importOtpConfigFromQrImage({})
    assert result["success"] is True
    assert str(result["otpConfig"]).startswith("otpauth://")

    bridge.saveGlobalEnvironmentAccessEntry(
        environment_id,
        {
            "name": "console",
            "type": "web",
            "urlOrHost": "https://example.com",
            "username": "admin",
            "password": "secret-pass",
            "otpConfig": result["otpConfig"],
            "requiresOtp": True,
            "note": "shared console",
            "openCommand": "",
            "sortOrder": 1,
            "isActive": True,
            "clearPassword": False,
            "clearOtpConfig": False,
        },
    )

    assert "entries" not in bridge.globalEnvironmentGroups[0]

    bridge.openEnvironmentDetail(environment_id)

    assert bridge.selectedEnvironment["entries"][0]["hasOtpConfig"] is True
    assert bridge.selectedEnvironment["entries"][0]["scope"] == "global"
    assert bridge.selectedEnvironment["entries"][0]["urlOrHost"] == "https://example.com"


def test_project_environment_access_entry_preserves_existing_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.saveProjectEnvironment(
        "project-1",
        {
            "name": "project env",
            "type": "project",
            "note": "",
            "sortOrder": 0,
            "isActive": True,
        },
    )
    environment_id = str(bridge.projectEnvironmentGroups[0]["id"])
    assert "entries" not in bridge.projectEnvironmentGroups[0]
    bridge.saveProjectEnvironmentAccessEntry(
        environment_id,
        {
            "name": "console",
            "type": "web",
            "urlOrHost": "https://example.com",
            "username": "admin",
            "password": "first-pass",
            "otpConfig": "otpauth://totp/demo?secret=JBSWY3DPEHPK3PXP",
            "requiresOtp": True,
            "note": "",
            "openCommand": "",
            "sortOrder": 1,
            "isActive": True,
            "clearPassword": False,
            "clearOtpConfig": False,
        },
    )

    bridge.openEnvironmentDetail(environment_id)

    entry_id = str(bridge.selectedEnvironment["entries"][0]["id"])
    bridge.saveProjectEnvironmentAccessEntry(
        environment_id,
        {
            "id": entry_id,
            "name": "console",
            "type": "web",
            "urlOrHost": "https://example.com/next",
            "username": "admin",
            "password": "",
            "otpConfig": "",
            "requiresOtp": True,
            "note": "updated",
            "openCommand": "",
            "sortOrder": 1,
            "isActive": True,
            "clearPassword": False,
            "clearOtpConfig": False,
        },
    )

    saved_entry = bridge._environment_repository.get_access_entry(entry_id)
    assert saved_entry is not None
    assert saved_entry.password_encrypted == "first-pass"
    assert saved_entry.otp_secret_encrypted.startswith("otpauth://")
    assert "entries" not in bridge.projectEnvironmentGroups[0]
    assert bridge.selectedEnvironment["entries"][0]["urlOrHost"] == "https://example.com/next"

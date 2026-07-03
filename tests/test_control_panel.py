from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import aica.control_panel as control_panel  # noqa: E402
from aica.analysis.metrics import ModelLatencySummary  # noqa: E402
from aica.config import ConfigManager, ServerConfig  # noqa: E402
from aica.environment_access import EnvironmentAccessEntryRecord, ProjectEnvironmentBundle, ProjectEnvironmentRecord  # noqa: E402
from aica.models import TicketSummaryFields  # noqa: E402
from aica.otp_secret_extractor import OtpSecretExtractResult  # noqa: E402
from aica.storage.contracts import ProjectRecord, ProjectVersionRecord  # noqa: E402
from aica.todo.models import TodoConclusion, TodoItem, TodoProjectLink, TodoStatus  # noqa: E402


class _TextClipboard:
    def __init__(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text

    def image(self) -> object | None:
        return None

    def mimeData(self) -> object | None:
        return None


class _FeaturePointWorkflowResponse:
    status_code = 200
    text = ""

    def json(self) -> dict[str, object]:
        return {
            "answer": "自动匹配功能点",
            "trace_id": "trace_001",
            "usage": {"total_tokens": 10},
        }


class _FeaturePointWorkflowSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> object:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _FeaturePointWorkflowResponse()


class _EventPublisher:
    def __init__(self) -> None:
        self.events = []

    def publish(self, event) -> None:  # noqa: ANN001
        self.events.append(event)


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
    def __init__(self) -> None:
        self.projects: dict[str, ProjectRecord] = {}
        self.project_versions: dict[str, list[ProjectVersionRecord]] = {}

    def list_projects(self, query: str = "", *, include_expired: bool = True) -> list[ProjectRecord]:
        normalized_query = str(query or "").strip().casefold()
        projects = list(self.projects.values())
        if normalized_query:
            projects = [
                project
                for project in projects
                if normalized_query in project.project_name.casefold()
                or normalized_query in project.task_order_no.casefold()
                or any(normalized_query in alias.casefold() for alias in project.aliases)
            ]
        return projects

    def get_project_by_task_order_no(self, task_order_no: str) -> ProjectRecord | None:
        return next(
            (project for project in self.projects.values() if project.task_order_no == task_order_no),
            None,
        )

    def get_project_by_id(self, project_id: str) -> ProjectRecord | None:
        return self.projects.get(project_id)

    def upsert_project(self, project: ProjectRecord) -> ProjectRecord:
        self.projects[project.id] = project
        return project

    def delete_project(self, project_id: str) -> bool:
        return self.projects.pop(project_id, None) is not None

    def list_project_versions(self, project_id: str) -> list[ProjectVersionRecord]:
        return list(self.project_versions.get(project_id, []))


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
            product_line="PC Office",
            product_module="PC Office-文字",
            ticket_type="investigation",
            reproduction_probability="偶现",
            customer_environment_code="env-prod",
            customer_environment_value="生产环境",
            issue_product="产品A/模块B/功能C",
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


def _build_bridge(
    monkeypatch: pytest.MonkeyPatch,
    todo: TodoItem,
    *,
    event_publisher: object | None = None,
) -> control_panel._ControlPanelBridge:
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
    monkeypatch.setattr(
        control_panel,
        "CustomerEnvironmentDictionaryWorker",
        lambda *, config_manager, parent=None: SimpleNamespace(
            finished=control_panel._Signal(),
            error=control_panel._Signal(),
            start=lambda: None,
            deleteLater=lambda: None,
        ),
    )
    monkeypatch.setattr(control_panel, "app_data_dir", lambda: temp_dir)
    monkeypatch.setattr(control_panel, "log_dir", lambda: temp_dir / "logs")
    monkeypatch.setattr(control_panel, "aica_database_file", lambda: temp_dir / "aica.db")
    monkeypatch.setattr(control_panel, "integrations_file", lambda: temp_dir / "integrations.json")

    return control_panel._ControlPanelBridge(
        ConfigManager(str(temp_dir / "config.json")),
        event_publisher=event_publisher,
    )


def _notification_messages(bridge: control_panel._ControlPanelBridge) -> list[str]:
    return [str(item["message"]) for item in bridge.notificationBridge.notifications]


def test_control_panel_bridge_defers_projects_and_tickets_until_needed(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    assert bridge.projects == []
    assert bridge.tickets == []
    assert bridge._projects_loaded is False  # noqa: SLF001
    assert bridge._tickets_loaded is False  # noqa: SLF001

    bridge.setCurrentSection("projects")
    assert bridge._projects_loaded is True  # noqa: SLF001

    bridge.setCurrentSection("tickets")
    assert bridge._tickets_loaded is True  # noqa: SLF001


def test_task_bindings_use_readable_chinese_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._analysis_metrics = SimpleNamespace(get_summary=lambda *_args: None)

    bindings = {item["id"]: item for item in bridge.taskBindings}

    assert bindings["analysis"]["label"] == "截图分析"
    assert bindings["plan_export"]["label"] == "方案导出"
    assert bindings["context_summary"]["label"] == "上下文摘要"
    assert bindings["log_analysis"]["label"] == "日志分析"
    assert {item["performanceSummary"] for item in bindings.values()} == {"暂无耗时样本"}


def test_control_panel_bridge_exposes_macos_platform_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    monkeypatch.setattr(
        control_panel,
        "RUNTIME_CAPABILITIES",
        SimpleNamespace(is_macos=True, is_windows=False, ui_font="PingFang SC"),
    )

    bridge = _build_bridge(monkeypatch, todo)

    assert bridge.isMacos is True


def test_control_panel_bridge_loads_cached_custom_field_options_on_startup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    temp_dir = tmp_path / "control-panel-cache"
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "customer_environment_options_cache.json").write_text(
        json.dumps(
            {
                "items": [
                    {"code": "env-prod", "value": "生产环境", "text": "生产环境", "sortOrder": 1},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (temp_dir / "issue_product_options_cache.json").write_text(
        json.dumps(
            {
                "items": [
                    {"code": "product-1", "value": "产品A/模块B/功能C", "text": "产品A/模块B/功能C", "sortOrder": 2},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="", dir=None: str(temp_dir))

    bridge = _build_bridge(monkeypatch, _build_todo())

    assert bridge.customerEnvironmentOptions[0]["text"] == "生产环境"
    assert bridge.issueProductOptions[0]["text"] == "产品A/模块B/功能C"


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


def test_control_panel_readable_chinese_locations(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

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

    assert bridge.serverLoginRequired is True

    bridge.updateServerField("enabled", "true")
    bridge.updateServerField("base_url", "https://server.example.com")
    bridge.updateServerField("api_key", "server-key")
    bridge.updateServerField("timeout_seconds", "45")

    assert bridge.serverLoginRequired is True
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
    assert next(provider for provider in saved.providers if provider.id == "siliconflow").api_key == ""
    assert bridge.statusMessage


def test_server_config_values_do_not_unlock_login_until_login_clicked(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.updateServerField("base_url", "https://server.example.com")
    bridge.updateServerField("api_key", "server-key")

    assert bridge.serverLoginRequired is True

    bridge.saveConfig()

    assert bridge.serverLoginRequired is True


def test_system_settings_persists_timeline_polish_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    assert bridge.enableTimelinePolish is True

    bridge.updateEnableTimelinePolish(False)
    bridge.saveConfig()

    saved = bridge._config_manager.load()
    assert saved.enable_timeline_polish is False
    assert bridge.enableTimelinePolish is False


def test_system_settings_persists_todo_detail_conclusion_only_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    assert bridge.todoDetailConclusionOnlyMode is False

    bridge.updateTodoDetailConclusionOnlyMode(True)
    bridge.saveConfig()

    saved = bridge._config_manager.load()
    assert saved.todo_detail_conclusion_only_mode is True
    assert bridge.todoDetailConclusionOnlyMode is True


def test_server_login_requires_base_url_and_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.saveServerLogin()
    assert bridge.serverLoginRequired is True
    assert bridge.errorMessage == "请填写服务端地址"

    bridge.updateServerField("base_url", "https://server.example.com")
    bridge.saveServerLogin()
    assert bridge.serverLoginRequired is True
    assert bridge.errorMessage == "请填写 API Key"


def test_server_login_enables_and_persists_server_config(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.updateServerField("base_url", "https://server.example.com")
    bridge.updateServerField("api_key", "server-key")
    bridge.saveServerLogin()

    saved = bridge._config_manager.load()
    assert saved.server.enabled is True
    assert saved.server.base_url == "https://server.example.com"
    assert saved.server.api_key == "server-key"
    assert bridge.serverLoginRequired is False
    assert bridge.statusMessage == "登录信息已保存"


def test_server_login_not_required_when_saved_config_is_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.updateServerField("base_url", "https://server.example.com")
    bridge.updateServerField("api_key", "server-key")
    bridge.saveServerLogin()

    reloaded = control_panel._ControlPanelBridge(bridge._config_manager)

    assert reloaded.serverLoginRequired is False


def test_server_login_resets_invalid_hidden_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.updateServerField("base_url", "https://server.example.com")
    bridge.updateServerField("api_key", "server-key")
    bridge.updateServerField("timeout_seconds", "0")
    bridge.saveServerLogin()

    saved = bridge._config_manager.load()
    assert saved.server.timeout_seconds == 30
    assert bridge.serverLoginRequired is False


def test_server_identity_refresh_updates_bridge_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.updateServerField("base_url", "https://server.example.com")
    bridge.updateServerField("api_key", "server-key")
    bridge.updateServerField("enabled", "true")

    class _FakeServerIdentityWorker:
        def __init__(self, *, config_manager, parent=None) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.deleted = False

        def start(self) -> None:
            self.finished.emit(
                {
                    "id": 1,
                    "username": "admin",
                    "full_name": "平台管理员",
                    "email": "admin@example.com",
                    "phone": "",
                    "is_active": True,
                }
            )

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "ServerIdentityWorker", _FakeServerIdentityWorker)

    bridge.refreshServerIdentity()

    assert bridge.serverIdentityLoading is False
    assert bridge.serverIdentity == {
        "id": "1",
        "fullName": "平台管理员",
        "username": "admin",
        "email": "admin@example.com",
        "phone": "",
        "subtitle": "admin",
        "detail": "admin@example.com",
        "isActive": True,
    }


def test_server_config_rejects_invalid_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.updateServerField("timeout_seconds", "0")
    bridge.saveConfig()

    assert "服务端超时时间" in bridge.errorMessage


def test_sync_projects_from_server_updates_project_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge._config.server = ServerConfig(
        enabled=True,
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=30,
    )
    bridge._config_manager.save(bridge._config)

    class _FakeWorker:
        def __init__(self, *, config_manager, db_path, parent=None) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.deleted = False

        def start(self) -> None:
            project = ProjectRecord(
                id="project-1",
                project_name="服务端项目",
                customer_name="服务端客户",
                task_order_no="TASK-001",
                aliases=("服务端群",),
            )
            bridge._project_repository.upsert_project(project)
            self.finished.emit(
                SimpleNamespace(
                    created_count=1,
                    updated_count=0,
                    skipped_count=0,
                    relinked_count=0,
                    error_rows=[],
                )
            )

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "ProjectServerSyncWorker", _FakeWorker)
    refresh_events: list[str] = []
    syncing_states: list[bool] = []
    bridge.dataChanged.connect(lambda: syncing_states.append(bridge.projectServerSyncing))
    bridge.todoListRefreshRequested.connect(lambda: refresh_events.append("refresh"))

    bridge.syncProjectsFromServer()

    assert bridge.lastProjectImportSummary == "新增 1 个，更新 0 个，跳过 0 个，关联 0 个"
    assert bridge.projects[0]["projectName"] == "服务端项目"
    assert bridge.projects[0]["taskOrderNo"] == "TASK-001"
    assert bridge.projects[0]["aliases"] == ["服务端群"]
    assert refresh_events == ["refresh"]
    assert True in syncing_states
    assert bridge.projectServerSyncing is False
    assert bridge.projectServerSyncMessage == ""


def test_sync_work_orders_to_server_updates_status(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    class _FakeWorker:
        def __init__(self, *, config_manager, db_path, parent=None) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.deleted = False

        def start(self) -> None:
            self.finished.emit(
                SimpleNamespace(
                    created_count=1,
                    updated_count=2,
                    skipped_count=0,
                    total_count=3,
                    results=[],
                )
            )

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "WorkOrderPushSyncWorker", _FakeWorker)
    refresh_events: list[str] = []
    syncing_states: list[bool] = []
    bridge.dataChanged.connect(lambda: syncing_states.append(bridge.workOrderSyncing))
    bridge.todoListRefreshRequested.connect(lambda: refresh_events.append("refresh"))

    bridge.syncWorkOrdersToServer()

    assert "新增 1 条，更新 2 条，跳过 0 条，共 3 条" in bridge.statusMessage
    assert bridge.workOrderSyncing is False
    assert bridge.workOrderSyncMessage == ""
    assert refresh_events == ["refresh"]
    assert True in syncing_states


def test_pull_work_orders_from_server_updates_ticket_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    class _FakeWorker:
        def __init__(self, *, config_manager, db_path, parent=None) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.deleted = False

        def start(self) -> None:
            bridge._todo_store._todo.title = "服务端新工单"  # noqa: SLF001
            self.finished.emit(
                SimpleNamespace(
                    created_count=1,
                    skipped_count=1,
                    total_count=2,
                    page_count=1,
                )
            )

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "WorkOrderPullSyncWorker", _FakeWorker)
    refresh_events: list[str] = []
    bridge.todoListRefreshRequested.connect(lambda: refresh_events.append("refresh"))

    bridge.pullWorkOrdersFromServer()

    assert bridge.tickets[0]["title"] == "服务端新工单"
    assert "新增 1 条，跳过 1 条，扫描 2 条" in bridge.statusMessage
    assert bridge.workOrderSyncing is False
    assert bridge.workOrderSyncMessage == ""


def test_done_missing_ach_filter_starts_async_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.status = TodoStatus.DONE
    todo.completed_at = "2026-05-29T09:00:00"
    created_workers: list[object] = []

    class _FakeWorker:
        finished = control_panel.pyqtSignal(object)
        error = control_panel.pyqtSignal(str)

        def __init__(self, *, config_manager, db_path, todo_ids, parent=None) -> None:  # noqa: ANN001
            self.todo_ids = todo_ids
            self.deleted = False
            created_workers.append(self)

        def start(self) -> None:
            self.finished.emit(SimpleNamespace(updated_count=0))

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "MissingAchRefreshWorker", _FakeWorker)
    bridge = _build_bridge(monkeypatch, todo)

    bridge.listTickets("", "done_missing_ach")
    bridge.listTickets("", "done_missing_ach")

    assert len(created_workers) == 1
    assert created_workers[0].todo_ids == ["ticket-1"]
    assert created_workers[0].deleted is True


def test_open_ticket_detail_starts_missing_ach_refresh_for_selected_ticket(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.status = TodoStatus.DONE
    todo.completed_at = "2026-05-29T09:00:00"
    created_workers: list[object] = []

    class _FakeWorker:
        finished = control_panel.pyqtSignal(object)
        error = control_panel.pyqtSignal(str)

        def __init__(self, *, config_manager, db_path, todo_ids, parent=None) -> None:  # noqa: ANN001
            self.todo_ids = todo_ids
            created_workers.append(self)

        def start(self) -> None:
            self.finished.emit(SimpleNamespace(updated_count=0))

        def deleteLater(self) -> None:
            return None

    monkeypatch.setattr(control_panel, "MissingAchRefreshWorker", _FakeWorker)
    bridge = _build_bridge(monkeypatch, todo)

    bridge.openTicketDetail("ticket-1")

    assert len(created_workers) == 1
    assert created_workers[0].todo_ids == ["ticket-1"]


def test_save_project_pushes_new_aliases_to_server_async(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._config.server = ServerConfig(
        enabled=True,
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=30,
    )
    bridge._config_manager.save(bridge._config)
    existing = ProjectRecord(
        id="project-1",
        project_name="Demo Project",
        customer_name="Demo Customer",
        task_order_no="TASK-001",
        aliases=("old-group",),
    )
    bridge._project_repository.upsert_project(existing)
    bridge._refresh_project_payloads()
    created_workers: list[object] = []

    class _FakeChatGroupsWorker:
        def __init__(self, *, config_manager, task_order_no, group_names, parent=None) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.task_order_no = task_order_no
            self.group_names = list(group_names)
            self.deleted = False
            created_workers.append(self)

        def start(self) -> None:
            self.finished.emit(self.task_order_no, self.group_names)

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "ProjectChatGroupsSyncWorker", _FakeChatGroupsWorker)

    bridge.saveProject(
        {
            "id": "project-1",
            "projectName": "Demo Project",
            "customerName": "Demo Customer",
            "taskOrderNo": "TASK-001",
            "aliases": ["old-group", "new-group", "new-group"],
        }
    )

    assert len(created_workers) == 1
    worker = created_workers[0]
    assert worker.task_order_no == "TASK-001"
    assert worker.group_names == ["new-group"]
    assert worker.deleted is True


def test_save_project_pushes_project_update_to_server_async(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._config.server = ServerConfig(
        enabled=True,
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=30,
    )
    bridge._config_manager.save(bridge._config)
    created_update_workers: list[object] = []

    class _FakeUpdateWorker:
        def __init__(self, *, config_manager, payload, parent=None) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.payload = dict(payload)
            self.deleted = False
            created_update_workers.append(self)

        def start(self) -> None:
            self.finished.emit(self.payload["task_order_no"])

        def deleteLater(self) -> None:
            self.deleted = True

    class _FakeChatGroupsWorker:
        def __init__(self, **_kwargs) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()

        def start(self) -> None:
            return None

        def deleteLater(self) -> None:
            return None

    monkeypatch.setattr(control_panel, "ProjectUpdateSyncWorker", _FakeUpdateWorker)
    monkeypatch.setattr(control_panel, "ProjectChatGroupsSyncWorker", _FakeChatGroupsWorker)
    bridge._project_repository.project_versions["project-1"] = [  # noqa: SLF001
        ProjectVersionRecord(
            id="version-1",
            project_id="project-1",
            issue_product="文档中台",
            environment="测试环境",
            version="003",
            created_at="2026-07-01T00:00:00",
            updated_at="2026-07-01T00:00:00",
        )
    ]

    bridge.saveProject(
        {
            "id": "project-1",
            "projectName": "Demo Project",
            "customerName": "Demo Customer",
            "taskOrderNo": "TASK-001",
            "productLine": "Product Line",
            "projectManager": "Alice",
            "projectLevel": "important",
            "followUpStartedAt": "2026-05-23T00:00:00",
            "supportEndedAt": "2026-12-31T23:59:59",
            "aliases": ["group-a"],
        }
    )

    assert len(created_update_workers) == 1
    worker = created_update_workers[0]
    assert worker.payload == {
        "task_order_no": "TASK-001",
        "project_name": "Demo Project",
        "customer_name": "Demo Customer",
        "product_line": "Product Line",
        "project_manager": "Alice",
        "project_level": "important",
        "follow_up_started_at": "2026-05-23T00:00:00",
        "support_ended_at": "2026-12-31T23:59:59",
        "versions": [
            {
                "product_line": "文档中台",
                "environment": "测试环境",
                "version": "003",
            }
        ],
    }
    assert worker.deleted is True


def test_save_project_does_not_push_unchanged_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._config.server = ServerConfig(
        enabled=True,
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=30,
    )
    bridge._config_manager.save(bridge._config)
    existing = ProjectRecord(
        id="project-1",
        project_name="Demo Project",
        customer_name="Demo Customer",
        task_order_no="TASK-001",
        aliases=("old-group",),
    )
    bridge._project_repository.upsert_project(existing)
    bridge._refresh_project_payloads()
    created_workers: list[object] = []

    class _FakeChatGroupsWorker:
        def __init__(self, **kwargs) -> None:
            created_workers.append(self)

    monkeypatch.setattr(control_panel, "ProjectChatGroupsSyncWorker", _FakeChatGroupsWorker)

    bridge.saveProject(
        {
            "id": "project-1",
            "projectName": "Demo Project",
            "customerName": "Demo Customer",
            "taskOrderNo": "TASK-001",
            "aliases": ["old-group"],
        }
    )

    assert created_workers == []


def test_save_project_does_not_push_project_update_when_only_aliases_change(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._config.server = ServerConfig(
        enabled=True,
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=30,
    )
    bridge._config_manager.save(bridge._config)
    existing = ProjectRecord(
        id="project-1",
        project_name="Demo Project",
        customer_name="Demo Customer",
        task_order_no="TASK-001",
        aliases=("old-group",),
        product_line="Product Line",
        project_manager="Alice",
        project_level="important",
        follow_up_started_at="2026-05-23T00:00:00",
        support_ended_at="2026-12-31T23:59:59",
    )
    bridge._project_repository.upsert_project(existing)
    bridge._refresh_project_payloads()
    created_update_workers: list[object] = []

    class _FakeUpdateWorker:
        def __init__(self, **_kwargs) -> None:
            created_update_workers.append(self)

    class _FakeChatGroupsWorker:
        def __init__(self, **_kwargs) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()

        def start(self) -> None:
            return None

        def deleteLater(self) -> None:
            return None

    monkeypatch.setattr(control_panel, "ProjectUpdateSyncWorker", _FakeUpdateWorker)
    monkeypatch.setattr(control_panel, "ProjectChatGroupsSyncWorker", _FakeChatGroupsWorker)

    bridge.saveProject(
        {
            "id": "project-1",
            "projectName": "Demo Project",
            "customerName": "Demo Customer",
            "taskOrderNo": "TASK-001",
            "productLine": "Product Line",
            "projectManager": "Alice",
            "projectLevel": "important",
            "followUpStartedAt": "2026-05-23T00:00:00",
            "supportEndedAt": "2026-12-31T23:59:59",
            "aliases": ["old-group", "new-group"],
        }
    )

    assert created_update_workers == []


def test_save_project_emits_project_saved(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    saved_project_ids: list[str] = []
    bridge.projectSaved.connect(saved_project_ids.append)

    bridge.saveProject(
        {
            "projectName": "Demo Project",
            "customerName": "Demo Customer",
            "taskOrderNo": "TASK-001",
            "productLine": "私网文档中心;zhongt",
            "aliases": ["new-group"],
        }
    )

    assert saved_project_ids
    saved_project = bridge._project_repository.get_project_by_task_order_no("TASK-001")  # noqa: SLF001
    assert saved_project is not None
    assert saved_project_ids == [saved_project.id]


def test_save_project_does_not_start_server_workers_when_server_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    created_update_workers: list[object] = []
    created_chat_group_workers: list[object] = []

    class _FakeUpdateWorker:
        def __init__(self, **_kwargs) -> None:
            created_update_workers.append(self)

    class _FakeChatGroupsWorker:
        def __init__(self, **_kwargs) -> None:
            created_chat_group_workers.append(self)

    monkeypatch.setattr(control_panel, "ProjectUpdateSyncWorker", _FakeUpdateWorker)
    monkeypatch.setattr(control_panel, "ProjectChatGroupsSyncWorker", _FakeChatGroupsWorker)

    bridge.saveProject(
        {
            "projectName": "Demo Project",
            "customerName": "Demo Customer",
            "taskOrderNo": "TASK-001",
            "productLine": "Product Line",
            "aliases": ["new-group"],
        }
    )

    assert bridge.errorMessage == ""
    assert bridge.statusMessage.startswith("已保存项目 Demo Project")
    assert created_update_workers == []
    assert created_chat_group_workers == []


def test_project_update_payload_includes_changed_project_fields() -> None:
    existing = ProjectRecord(
        id="project-1",
        project_name="Old Project",
        customer_name="Old Customer",
        task_order_no="TASK-001",
        product_line="Old Line",
        project_manager="Old Manager",
        project_level="normal",
        follow_up_started_at="2026-05-01T00:00:00",
        support_ended_at="2026-12-01T23:59:59",
    )
    updated = ProjectRecord(
        id="project-1",
        project_name="New Project",
        customer_name="Old Customer",
        task_order_no="TASK-001",
        product_line="New Line",
        project_manager="Old Manager",
        project_level="important",
        follow_up_started_at="2026-05-01T00:00:00",
        support_ended_at="2026-12-31T23:59:59",
    )

    payload = control_panel._project_update_payload(updated, existing)  # noqa: SLF001

    assert payload == {
        "task_order_no": "TASK-001",
        "project_name": "New Project",
        "product_line": "New Line",
        "project_level": "important",
        "support_ended_at": "2026-12-31T23:59:59",
    }


def test_project_update_payload_includes_versions() -> None:
    project = ProjectRecord(
        id="project-1",
        project_name="Demo Project",
        customer_name="Demo Customer",
        task_order_no="TASK-001",
    )
    project_versions = [
        ProjectVersionRecord(
            id="version-1",
            project_id="project-1",
            issue_product="文档中台",
            environment="测试环境",
            version="003",
        ),
        ProjectVersionRecord(
            id="version-2",
            project_id="project-1",
            issue_product="WPS Office PC端",
            environment="生产环境",
            version="Xxxx",
        ),
    ]

    payload = control_panel._project_update_payload(project, project, project_versions=project_versions)  # noqa: SLF001

    assert payload == {
        "task_order_no": "TASK-001",
        "versions": [
            {
                "product_line": "文档中台",
                "environment": "测试环境",
                "version": "003",
            },
            {
                "product_line": "WPS Office PC端",
                "environment": "生产环境",
                "version": "Xxxx",
            },
        ],
    }


def test_save_selected_ticket_version_pushes_project_versions_to_server(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="manual",
        project_snapshot={
            "project_name": "Demo Project",
            "customer_name": "Demo Customer",
            "task_order_no": "WO-001",
        },
    )
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._config.server = ServerConfig(
        enabled=True,
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=30,
    )
    bridge._config_manager.save(bridge._config)
    project = ProjectRecord(
        id="project-1",
        project_name="Demo Project",
        customer_name="Demo Customer",
        task_order_no="WO-001",
        product_line="PC Office",
        aliases=("test-group",),
    )
    bridge._project_repository.upsert_project(project)  # noqa: SLF001
    bridge._refresh_project_payloads()  # noqa: SLF001
    bridge.openTicketDetail(todo.id)
    original_update_todo = bridge._todo_store.update_todo  # noqa: SLF001
    created_update_workers: list[object] = []

    class _FakeUpdateWorker:
        def __init__(self, *, config_manager, payload, parent=None) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.payload = dict(payload)
            self.deleted = False
            created_update_workers.append(self)

        def start(self) -> None:
            self.finished.emit(self.payload["task_order_no"])

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "ProjectUpdateSyncWorker", _FakeUpdateWorker)

    def _update_todo_with_project_versions(todo_id: str, *, summary_fields: TicketSummaryFields):  # noqa: ANN001
        updated = original_update_todo(todo_id, summary_fields=summary_fields)
        bridge._project_repository.project_versions["project-1"] = [  # noqa: SLF001
            ProjectVersionRecord(
                id="version-1",
                project_id="project-1",
                issue_product="产品A/模块B/功能C",
                environment="prod",
                version=str(summary_fields.ticket_version or "").strip(),
                created_at="2026-07-01T00:00:00",
                updated_at="2026-07-01T00:00:00",
            )
        ]
        return updated

    bridge._todo_store.update_todo = _update_todo_with_project_versions  # type: ignore[method-assign]  # noqa: SLF001

    bridge.saveSelectedTicketField("ticket_version", "release_2026_07")

    assert len(created_update_workers) == 1
    assert created_update_workers[0].payload == {
        "task_order_no": "WO-001",
        "versions": [
            {
                "product_line": "产品A/模块B/功能C",
                "environment": "prod",
                "version": "release_2026_07",
            }
        ],
    }


def test_reopen_selected_ticket_updates_detail_and_respects_done_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.status = TodoStatus.DONE
    todo.completed_at = "2026-04-21T09:30:00"
    todo.updated_at = todo.completed_at

    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
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


def test_reopen_selected_ticket_publishes_reopened_event(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.status = TodoStatus.DONE
    publisher = _EventPublisher()
    temp_dir = Path(tempfile.mkdtemp(prefix="control-panel-", dir=Path.cwd()))

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
    monkeypatch.setattr(control_panel, "SQLiteProjectEnvironmentRepository", lambda _path: _FakeEnvironmentRepository())
    monkeypatch.setattr(control_panel, "TodoStore", lambda _path: _FakeTodoStore(todo))
    monkeypatch.setattr(control_panel, "app_data_dir", lambda: temp_dir)
    monkeypatch.setattr(control_panel, "log_dir", lambda: temp_dir / "logs")
    monkeypatch.setattr(control_panel, "aica_database_file", lambda: temp_dir / "aica.db")
    monkeypatch.setattr(control_panel, "integrations_file", lambda: temp_dir / "integrations.json")
    bridge = control_panel._ControlPanelBridge(
        ConfigManager(str(temp_dir / "config.json")),
        event_publisher=publisher,
    )

    bridge.listTickets("", "done")
    bridge.openTicketDetail(todo.id)
    bridge.reopenSelectedTicket()

    assert [str(event.event_type) for event in publisher.events] == ["reopened"]
    assert publisher.events[0].todo_snapshot["status"] == TodoStatus.OPEN


def test_save_selected_ticket_field_ignores_readonly_ach_no(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("ach_no", "ACH-2026")

    assert bridge.selectedTicket["achNo"] == ""
    assert publisher.events == []


def test_selected_ticket_exposes_customer_environment_value_and_options(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge._customer_environment_options = [  # noqa: SLF001
        {"code": "env-prod", "value": "生产环境", "text": "生产环境", "sortOrder": 1},
        {"code": "env-uat", "value": "预发环境", "text": "预发环境", "sortOrder": 2},
    ]

    bridge.openTicketDetail(todo.id)

    assert bridge.selectedTicket["customerEnvironmentValue"] == "生产环境"
    assert bridge.selectedTicket["customerEnvironmentOptions"][0]["text"] == "生产环境"


def test_selected_ticket_exposes_reproduction_probability(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.openTicketDetail(todo.id)

    assert bridge.selectedTicket["reproductionProbability"] == "偶现"


def test_selected_ticket_reproduction_probability_defaults_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.summary_fields = TicketSummaryFields.from_dict(
        {
            **todo.summary_fields.to_dict(),
            "reproduction_probability": "",
        }
    )
    bridge = _build_bridge(monkeypatch, todo)

    bridge.openTicketDetail(todo.id)

    assert bridge.selectedTicket["reproductionProbability"] == "未知"


def test_save_selected_ticket_customer_environment_maps_code_to_value(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._customer_environment_options = [  # noqa: SLF001
        {"code": "env-prod", "value": "生产环境", "text": "生产环境", "sortOrder": 1},
        {"code": "env-uat", "value": "预发环境", "text": "预发环境", "sortOrder": 2},
    ]
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("customer_environment", "预发环境")

    assert bridge.selectedTicket["customerEnvironmentValue"] == "预发环境"
    assert [str(event.event_type) for event in publisher.events] == ["updated"]


def test_save_selected_ticket_reproduction_probability_updates_summary_field(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("reproduction_probability", "必现")

    assert bridge.selectedTicket["reproductionProbability"] == "必现"
    assert [str(event.event_type) for event in publisher.events] == ["updated"]


def test_selected_ticket_exposes_issue_product_value_and_options(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge._issue_product_options = [  # noqa: SLF001
        {"code": "p1", "value": "产品A/模块B/功能C", "text": "产品A/模块B/功能C", "sortOrder": 1},
        {"code": "p2", "value": "产品A/模块B/功能D", "text": "产品A/模块B/功能D", "sortOrder": 2},
    ]

    bridge.openTicketDetail(todo.id)

    assert bridge.selectedTicket["issueProduct"] == "产品A/模块B/功能C"
    assert bridge.selectedTicket["issueProductOptions"][0]["text"] == "产品A/模块B/功能C"


def test_issue_product_refresh_persists_option_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    temp_dir = tmp_path / "control-panel-cache-write"
    temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="", dir=None: str(temp_dir))
    bridge = _build_bridge(monkeypatch, _build_todo())

    bridge._handle_issue_product_options_finished(  # noqa: SLF001
        [
            {"code": "product-2", "value": "产品X/模块Y/功能Z", "sort_order": 3},
        ]
    )

    payload = json.loads((temp_dir / "issue_product_options_cache.json").read_text(encoding="utf-8"))
    assert payload["items"][0]["value"] == "产品X/模块Y/功能Z"
    assert payload["items"][0]["sortOrder"] == 3


def test_ticket_list_payload_includes_issue_product(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.listTickets("", "open")

    assert bridge.tickets[0]["issueProduct"] == "产品A/模块B/功能C"


def test_save_selected_ticket_issue_product_updates_summary_field(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._issue_product_options = [  # noqa: SLF001
        {"code": "p1", "value": "产品A/模块B/功能C", "text": "产品A/模块B/功能C", "sortOrder": 1},
        {"code": "p2", "value": "产品X/模块Y/功能Z", "text": "产品X/模块Y/功能Z", "sortOrder": 2},
    ]
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("issue_product", "产品X/模块Y/功能Z")

    assert bridge.selectedTicket["issueProduct"] == "产品X/模块Y/功能Z"
    assert [str(event.event_type) for event in publisher.events] == ["updated"]


def test_save_selected_ticket_issue_product_normalizes_path(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("issue_product", "产品A / 模块B ／ 功能C")

    assert bridge.selectedTicket["issueProduct"] == "产品A/模块B/功能C"
    assert bridge._todo_store.get_todo(todo.id).summary_fields.issue_product == "产品A/模块B/功能C"  # noqa: SLF001


def test_selected_ticket_exposes_feature_point_search_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge.openTicketDetail(todo.id)
    bridge._feature_point_options = [{"value": "文档中台-运维平台-页面跑版-兼容问题", "text": "文档中台-运维平台-页面跑版-兼容问题"}]  # noqa: SLF001
    bridge._feature_point_loading = True  # noqa: SLF001
    bridge._feature_point_error = "功能点选项加载失败。"  # noqa: SLF001
    bridge._refresh_selected_ticket_payload()  # noqa: SLF001

    assert bridge.selectedTicket["featurePointOptions"] == [
        {"value": "文档中台-运维平台-页面跑版-兼容问题", "text": "文档中台-运维平台-页面跑版-兼容问题"}
    ]
    assert bridge.selectedTicket["featurePointLoading"] is True
    assert bridge.selectedTicket["featurePointError"] == "功能点选项加载失败。"


def test_save_selected_ticket_feature_point_updates_summary_field_as_manual(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("feature_point", "文档中台-运维平台-页面跑版-兼容问题")

    assert bridge.selectedTicket["featurePoint"] == "文档中台-运维平台-页面跑版-兼容问题"
    assert bridge._todo_store.get_todo(todo.id).summary_fields.feature_point_source == "manual"  # noqa: SLF001
    assert [str(event.event_type) for event in publisher.events] == ["updated"]


def test_save_selected_ticket_version_refreshes_project_versions_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="manual",
        project_snapshot={
            "project_name": "Demo Project",
            "customer_name": "Demo Customer",
            "task_order_no": "WO-001",
        },
    )
    bridge = _build_bridge(monkeypatch, todo)
    project = ProjectRecord(
        id="project-1",
        project_name="Demo Project",
        customer_name="Demo Customer",
        task_order_no="WO-001",
        product_line="PC Office",
        aliases=("test-group",),
    )
    bridge._project_repository.upsert_project(project)  # noqa: SLF001
    bridge._refresh_project_payloads()  # noqa: SLF001
    bridge.openTicketDetail(todo.id)
    original_update_todo = bridge._todo_store.update_todo  # noqa: SLF001

    def _update_todo_with_project_versions(todo_id: str, *, summary_fields: TicketSummaryFields):  # noqa: ANN001
        updated = original_update_todo(todo_id, summary_fields=summary_fields)
        bridge._project_repository.project_versions["project-1"] = [  # noqa: SLF001
            ProjectVersionRecord(
                id="version-1",
                project_id="project-1",
                issue_product="产品A/模块B/功能C",
                environment="prod",
                version=str(summary_fields.ticket_version or "").strip(),
                created_at="2026-07-01T00:00:00",
                updated_at="2026-07-01T00:00:00",
            )
        ]
        return updated

    bridge._todo_store.update_todo = _update_todo_with_project_versions  # type: ignore[method-assign]  # noqa: SLF001

    bridge.saveSelectedTicketField("ticket_version", "release_2026_07")

    matching_project = next(item for item in bridge.projects if item["id"] == "project-1")
    assert matching_project["projectVersions"][0]["issueProduct"] == "产品A/模块B/功能C"
    assert matching_project["projectVersions"][0]["environment"] == "prod"
    assert matching_project["projectVersions"][0]["version"] == "release_2026_07"


def test_selected_ticket_exposes_product_line_and_module_options(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.openTicketDetail(todo.id)

    assert bridge.selectedTicket["productLine"] == "PC Office"
    assert bridge.selectedTicket["productLineOptions"][0]["text"] == "PC Office"
    assert bridge.selectedTicket["productModule"] == "PC Office-文字"
    assert bridge.selectedTicket["productModuleOptions"][0]["text"] == "PC Office-文字"


def test_selected_ticket_hides_unknown_environment_and_product_line(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.summary_fields = TicketSummaryFields(
        group_name="test-group",
        environment="",
        product_line="",
        product_module="",
        ticket_type="investigation",
    )
    bridge = _build_bridge(monkeypatch, todo)

    bridge.openTicketDetail(todo.id)

    assert bridge.selectedTicket["environment"] == ""
    assert bridge.selectedTicket["productLine"] == ""


def test_save_selected_ticket_environment_updates_summary_field(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("environment", "pre")

    assert bridge.selectedTicket["environment"] == "pre"
    assert bridge._todo_store.get_todo(todo.id).summary_fields.environment == "pre"  # noqa: SLF001
    assert [str(event.event_type) for event in publisher.events] == ["updated"]


def test_save_selected_ticket_environment_backfills_ticket_version(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="manual",
        project_snapshot={
            "project_name": "Demo Project",
            "customer_name": "Demo Customer",
            "task_order_no": "WO-001",
        },
    )
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    project = ProjectRecord(
        id="project-1",
        project_name="Demo Project",
        customer_name="Demo Customer",
        task_order_no="WO-001",
        product_line="PC Office",
        aliases=("test-group",),
    )
    bridge._project_repository.upsert_project(project)  # noqa: SLF001
    bridge._project_repository.project_versions["project-1"] = [  # noqa: SLF001
        ProjectVersionRecord(
            id="version-1",
            project_id="project-1",
            issue_product="产品A/模块B/功能C",
            environment="正式环境",
            version="release_dc_v7.0.2504b.20250424",
            created_at="2026-07-01T00:00:00",
            updated_at="2026-07-01T00:00:00",
        )
    ]
    bridge._refresh_project_payloads()  # noqa: SLF001
    bridge.openTicketDetail(todo.id)

    original_update_todo = bridge._todo_store.update_todo  # noqa: SLF001

    def _update_todo_with_backfill(todo_id: str, *, summary_fields: TicketSummaryFields):  # noqa: ANN001
        updated = original_update_todo(todo_id, summary_fields=summary_fields)
        updated.summary_fields = TicketSummaryFields.from_dict(
            {
                **updated.summary_fields.to_dict(),
                "ticket_version": "release_dc_v7.0.2504b.20250424",
            }
        )
        bridge._todo_store._todo = updated  # type: ignore[attr-defined]  # noqa: SLF001
        return updated

    bridge._todo_store.update_todo = _update_todo_with_backfill  # type: ignore[method-assign]  # noqa: SLF001

    bridge.saveSelectedTicketField("environment", "正式环境")

    assert bridge.selectedTicket["environment"] == "正式环境"
    assert bridge.selectedTicket["ticketVersion"] == "release_dc_v7.0.2504b.20250424"


def test_save_selected_ticket_product_line_clears_invalid_module(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("product_line", "WPS会议")

    assert bridge.selectedTicket["productLine"] == "WPS会议"
    assert bridge.selectedTicket["productModule"] == ""
    assert [str(event.event_type) for event in publisher.events] == ["updated"]


def test_save_selected_ticket_product_module_uses_current_product_line(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge.openTicketDetail(todo.id)

    bridge.saveSelectedTicketField("product_module", "PC Office-表格")

    assert bridge.selectedTicket["productLine"] == "PC Office"
    assert bridge.selectedTicket["productModule"] == "PC Office-表格"
    assert [str(event.event_type) for event in publisher.events] == ["updated"]


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
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
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
    assert bridge.selectedTicket["customerEnvironmentValue"] == "生产环境"
    assert bridge.selectedTicket["ticketVersion"] == ""
    assert bridge.statusMessage == "已解除项目关联"
    assert bridge.errorMessage == ""
    assert [str(event.event_type) for event in publisher.events] == ["updated"]
    assert publisher.events[0].delta == {"changed_fields": ["summary_fields", "project_link"]}
    assert refresh_events == ["refresh"]
    assert _notification_messages(bridge)


def test_manual_selected_ticket_project_detail_prefers_project_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="manual",
        project_snapshot={
            "project_id": "project-1",
            "project_name": "Demo Project",
            "task_order_no": "WO-001",
        },
    )
    bridge = _build_bridge(monkeypatch, todo)

    bridge.openTicketDetail(todo.id)

    assert bridge.selectedTicket["projectStatus"] == "manual"
    assert bridge.selectedTicket["projectStatusDetail"] == "Demo Project / WO-001"


def test_manual_selected_ticket_project_detail_falls_back_without_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.project_link = TodoProjectLink(
        todo_id=todo.id,
        project_id="project-1",
        match_status="manual",
    )
    bridge = _build_bridge(monkeypatch, todo)

    bridge.openTicketDetail(todo.id)

    assert bridge.selectedTicket["projectStatus"] == "manual"
    assert bridge.selectedTicket["projectStatusDetail"] == "当前工单使用了手动项目关联结果。"


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
    todo.summary_fields.issue_product = ""
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge.openTicketDetail(todo.id)

    bridge.refreshSelectedTicketFeaturePoint()

    assert bridge.errorMessage


def test_refresh_selected_ticket_feature_point_uses_server_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.summary_fields.product_line = "协作产品线"
    todo.summary_fields.issue_product = "产品A/模块B/功能C"
    todo.summary_fields.feature_point = "旧功能点"
    todo.current_summary = "用户反馈保存失败"
    session = _FeaturePointWorkflowSession()
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge._config.server = ServerConfig(
        enabled=True,
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=18,
    )
    bridge._config_manager.save(bridge._config)
    bridge.openTicketDetail(todo.id)
    monkeypatch.setattr("aica.server_api.requests.Session", lambda: session)

    bridge.refreshSelectedTicketFeaturePoint()

    assert bridge.errorMessage == ""
    assert bridge.statusMessage == "功能点已刷新"
    assert bridge.selectedTicket["featurePoint"] == "自动匹配功能点"
    assert todo.summary_fields.feature_point_source == "auto"
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/workflow-mphzwo1h/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "product_line": "产品A/模块B/功能C",
            "desc": "用户反馈保存失败",
        }
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 18


def test_refresh_selected_ticket_feature_point_waits_for_async_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    todo.summary_fields.product_line = "协作产品线"
    todo.summary_fields.issue_product = "产品A/模块B/功能C"
    todo.summary_fields.feature_point = "旧功能点"
    todo.current_summary = "用户反馈保存失败"
    publisher = _EventPublisher()
    bridge = _build_bridge(monkeypatch, todo, event_publisher=publisher)
    bridge.openTicketDetail(todo.id)
    created_workers: list[object] = []

    class _FakeFeaturePointWorker:
        def __init__(
            self,
            *,
            config_manager,
            todo_id,
            request_id,
            issue_product,
            problem_desc,
            parent=None,
        ) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.todo_id = todo_id
            self.request_id = request_id
            self.issue_product = issue_product
            self.problem_desc = problem_desc
            self.started = False
            self.deleted = False
            created_workers.append(self)

        def start(self) -> None:
            self.started = True

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "FeaturePointRefreshWorker", _FakeFeaturePointWorker)

    bridge.refreshSelectedTicketFeaturePoint()

    assert len(created_workers) == 1
    worker = created_workers[0]
    assert worker.started is True
    assert bridge.statusMessage == "功能点正在刷新..."
    assert bridge.selectedTicket["featurePoint"] == "旧功能点"
    assert worker.issue_product == "产品A/模块B/功能C"
    assert worker.problem_desc == "用户反馈保存失败"

    worker.finished.emit(worker.todo_id, worker.request_id, "异步功能点")

    assert bridge.selectedTicket["featurePoint"] == "异步功能点"
    assert todo.summary_fields.feature_point_source == "auto"
    assert bridge.statusMessage == "功能点已刷新"
    assert [str(event.event_type) for event in publisher.events] == ["updated"]
    assert publisher.events[0].todo_snapshot["summary_fields"]["feature_point"] == "异步功能点"
    assert worker.deleted is True


def test_search_selected_ticket_feature_point_options_waits_for_async_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge._config.server = ServerConfig(  # noqa: SLF001
        enabled=True,
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=18,
    )
    bridge._config_manager.save(bridge._config)  # noqa: SLF001
    bridge.openTicketDetail(todo.id)
    created_workers: list[object] = []

    class _FakeFeaturePointOptionsWorker:
        def __init__(
            self,
            *,
            config_manager,
            todo_id,
            request_id,
            query,
            parent=None,
        ) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.todo_id = todo_id
            self.request_id = request_id
            self.query = query
            self.started = False
            self.deleted = False
            created_workers.append(self)

        def start(self) -> None:
            self.started = True

        def deleteLater(self) -> None:
            self.deleted = True

    monkeypatch.setattr(control_panel, "FeaturePointOptionsWorker", _FakeFeaturePointOptionsWorker)

    bridge.searchSelectedTicketFeaturePointOptions("页面跑版")

    assert len(created_workers) == 1
    worker = created_workers[0]
    assert worker.started is True
    assert worker.query == "页面跑版"
    assert bridge.selectedTicket["featurePointLoading"] is True
    assert bridge.selectedTicket["featurePointOptions"] == []

    worker.finished.emit(
        worker.todo_id,
        worker.request_id,
        [{"value": "文档中台-运维平台-页面跑版-兼容问题", "text": "文档中台-运维平台-页面跑版-兼容问题"}],
    )

    assert bridge.selectedTicket["featurePointLoading"] is False
    assert bridge.selectedTicket["featurePointError"] == ""
    assert bridge.selectedTicket["featurePointOptions"] == [
        {"value": "文档中台-运维平台-页面跑版-兼容问题", "text": "文档中台-运维平台-页面跑版-兼容问题"}
    ]
    assert worker.deleted is True


def test_search_selected_ticket_feature_point_options_discards_stale_worker_result(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)
    bridge._config.server = ServerConfig(  # noqa: SLF001
        enabled=True,
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=18,
    )
    bridge._config_manager.save(bridge._config)  # noqa: SLF001
    bridge.openTicketDetail(todo.id)
    created_workers: list[object] = []

    class _FakeFeaturePointOptionsWorker:
        def __init__(
            self,
            *,
            config_manager,
            todo_id,
            request_id,
            query,
            parent=None,
        ) -> None:
            self.finished = control_panel._Signal()
            self.error = control_panel._Signal()
            self.todo_id = todo_id
            self.request_id = request_id
            self.query = query
            created_workers.append(self)

        def start(self) -> None:
            return None

        def deleteLater(self) -> None:
            return None

    monkeypatch.setattr(control_panel, "FeaturePointOptionsWorker", _FakeFeaturePointOptionsWorker)

    bridge.searchSelectedTicketFeaturePointOptions("页面")
    bridge.searchSelectedTicketFeaturePointOptions("跑版")

    assert len(created_workers) == 2

    created_workers[0].finished.emit(
        created_workers[0].todo_id,
        created_workers[0].request_id,
        [{"value": "旧结果", "text": "旧结果"}],
    )

    assert bridge.selectedTicket["featurePointOptions"] == []
    assert bridge.selectedTicket["featurePointLoading"] is True

    created_workers[1].finished.emit(
        created_workers[1].todo_id,
        created_workers[1].request_id,
        [{"value": "新结果", "text": "新结果"}],
    )

    assert bridge.selectedTicket["featurePointOptions"] == [{"value": "新结果", "text": "新结果"}]
    assert bridge.selectedTicket["featurePointLoading"] is False


def test_legacy_environment_sections_map_to_unified_section(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    bridge.setCurrentSection("project_environments")
    assert bridge.currentSection == "environments"
    assert bridge.environmentScopeFilter == "project"

    bridge.setCurrentSection("global_environments")
    assert bridge.currentSection == "environments"
    assert bridge.environmentScopeFilter == "global"


def test_model_and_rules_sections_are_hidden_from_navigation(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    section_ids = {item["id"] for item in bridge.sections}
    grouped_section_ids = {
        item["id"]
        for group in bridge.sectionGroups
        for item in group["items"]
    }

    assert "models" not in section_ids
    assert "models" not in grouped_section_ids
    assert "analysis_rules" not in section_ids
    assert "analysis_rules" not in grouped_section_ids
    assert bridge.currentSection == "server"

    bridge.setCurrentSection("models")

    assert bridge.currentSection == "server"
    assert bridge.currentSectionMeta["title"] == "服务端集成"

    bridge.setCurrentSection("analysis_rules")

    assert bridge.currentSection == "server"
    assert bridge.currentSectionMeta["title"] == "服务端集成"


def test_hotkeys_menu_uses_settings_label(monkeypatch: pytest.MonkeyPatch) -> None:
    todo = _build_todo()
    bridge = _build_bridge(monkeypatch, todo)

    hotkey_item = next(item for item in bridge.sections if item["id"] == "hotkeys")

    assert hotkey_item["title"] == "系统设置"
    bridge.setCurrentSection("hotkeys")
    assert bridge.currentSectionMeta["title"] == "系统设置"


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

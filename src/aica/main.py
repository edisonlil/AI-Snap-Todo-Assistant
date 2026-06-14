"""AICA entrypoint: initialize app and connect the main workflow."""
from __future__ import annotations

import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import uuid

from PyQt6.QtCore import QEvent, QObject, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from aica.analysis.flow import AnalysisFlowCoordinator
from aica.analysis.metrics import AnalysisMetricsStore
from aica.app_commands import (
    AppCommandServer,
    COMMAND_CAPTURE,
    COMMAND_OPEN_PANEL,
    COMMAND_QUIT,
    parse_startup_command,
    send_app_command,
)
from aica.app_notifications import AppNotificationBridge, AppNotificationWindow
from aica.todo.assist_analysis import build_assist_analysis_cache_key, build_assist_todo_payload
from aica.build_expiration import build_expiration_message, should_enforce_build_expiration, get_build_expiration_status
from aica.capture_session import CaptureSession
from aica.capture_ui_flow import CaptureUiFlow
from aica.config import ConfigManager
from aica.context_summary.models import build_context_summary_request_for_todo
from aica.control_panel import ControlPanelWindow
from aica.hotkey import HotkeyManager
from aica.knowledge_archive import KnowledgeArchiveEventHandler
from aica.llm.service import LLMService, ModelResolutionError
from aica.log_analysis.models import LogAnalysisTask
from aica.log_analysis.orchestrator import LogAnalysisOrchestrator
from aica.log_analysis.store import LogAnalysisTaskStore
from aica.log_analysis.worker import LogAnalysisWorker
from aica.models import TicketSummaryFields
from aica.overlay import OverlayWindow
from aica.paths import error_log_file, icon_file
from aica.result_flow import ResultFlowCoordinator
from aica.runtime import RUNTIME_CAPABILITIES, hotkey_failure_message
from aica.single_instance import SingleInstanceGuard, show_already_running_message
from aica.ticket_enrichment import (
    TicketEnrichmentService,
    build_feature_point_provider,
    build_root_cause_provider,
    build_ticket_enrichment_job,
    is_ticket_enrichment_job_still_current,
    merge_async_enrichment_fields,
    summarize_enrichment_errors,
)
from aica.ticket_enrichment_worker import TicketEnrichmentWorker
from aica.todo.controller import TodoController
from aica.todo.detail_panel import TodoDetailPanel
from aica.todo.detail_save_policy import should_run_ticket_enrichment_for_todo_detail_save
from aica.todo.events import ScriptEventHandler, TodoBindingStore, TodoEventBus
from aica.todo.panel import TodoPanel
from aica.todo.store import TodoConclusion, TodoStore
from aica.todo.work_order_sync import WorkOrderSyncEventHandler
from aica.theme_controller import ThemeController
from aica.toolbar import FloatingToolbar
from aica.worker import (
    AIWorker,
    AssistAnalysisWorker,
    MultiCaptureAIWorker,
    StageSummaryWorker,
)
from aica.windows_taskbar import install_windows_taskbar_tasks


_APP_NAME = "Chattodo"
_WINDOWS_APP_USER_MODEL_ID = "edison.Chattodo"


class _ApplicationActivationFilter(QObject):
    """Open the control panel when the macOS Dock icon activates the app."""

    def __init__(self, activated_callback, parent=None):
        super().__init__(parent)
        self._activated_callback = activated_callback

    def eventFilter(self, _watched, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.ApplicationActivate:
            self._activated_callback()
        return False


class _AppCommandDispatcher(QObject):
    command_received = pyqtSignal(str)

    def dispatch(self, command: str) -> None:
        self.command_received.emit(command)


def _handle_application_state_changed(state, show_control_panel) -> None:
    if state == Qt.ApplicationState.ApplicationActive:
        show_control_panel("server")


def _resolve_error_log_file() -> Path:
    candidates = [error_log_file()]
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        candidates.append(Path(local_app_data) / "AICA" / "error.log")
    temp_dir = os.getenv("TEMP", "").strip() or os.getenv("TMP", "").strip()
    if temp_dir:
        candidates.append(Path(temp_dir) / "AICA" / "error.log")
    candidates.append(Path.cwd() / "aica_error.log")

    for candidate in candidates:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            continue
    return Path.cwd() / "aica_error.log"


def _append_startup_log(log_file: Path, message: str) -> None:
    try:
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().isoformat()}] {message}\n")
    except Exception:
        pass


def _write_unhandled_exception(log_file: Path, exc_type, exc_value, exc_tb) -> None:
    try:
        formatted = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    except Exception as format_error:
        formatted = (
            f"{getattr(exc_type, '__name__', 'UnknownError')}: {exc_value}\n"
            f"格式化异常堆栈失败: {format_error}\n"
        )

    try:
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"\n{'=' * 60}\n")
            handle.write(f"时间: {datetime.now().isoformat()}\n")
            handle.write(formatted)
    except Exception:
        pass


def _request_shutdown_after_unhandled_exception(exit_code: int = 1) -> None:
    app = QApplication.instance()
    if app is not None:
        try:
            app.exit(exit_code)
        except Exception:
            pass


def _setup_exception_handler() -> Path:
    """Install a global exception hook and persist uncaught errors to disk."""
    log_file = _resolve_error_log_file()
    _append_startup_log(log_file, "startup: exception handler ready")
    handling_exception = False

    def exception_hook(exc_type, exc_value, exc_tb):
        nonlocal handling_exception
        _write_unhandled_exception(log_file, exc_type, exc_value, exc_tb)

        if handling_exception:
            _request_shutdown_after_unhandled_exception()
            return

        handling_exception = True
        try:
            if QApplication.instance() is None:
                _append_startup_log(log_file, "unhandled exception dialog skipped: QApplication unavailable")
            else:
                try:
                    QMessageBox.critical(
                        None,
                        "程序错误",
                        f"发生未处理异常，已记录到日志:\n{log_file}\n\n{exc_type.__name__}: {exc_value}",
                    )
                except Exception as dialog_error:
                    _append_startup_log(
                        log_file,
                        f"unhandled exception dialog failed: {dialog_error}",
                    )
        finally:
            _request_shutdown_after_unhandled_exception()

    sys.excepthook = exception_hook
    return log_file


def _build_hotkey_manager(config_mgr: ConfigManager, initial_config) -> HotkeyManager:
    default_hotkey = RUNTIME_CAPABILITIES.default_capture_hotkey
    try:
        return HotkeyManager(
            initial_config.hotkeys.capture,
            platform_id=RUNTIME_CAPABILITIES.platform_id,
        )
    except ValueError:
        initial_config.hotkeys.capture = default_hotkey
        config_mgr.save(initial_config)
        return HotkeyManager(default_hotkey, platform_id=RUNTIME_CAPABILITIES.platform_id)


def _resolve_todo_detail_draft(payload: dict[str, object]) -> tuple[str, str, TicketSummaryFields, TodoConclusion]:
    draft_payload = payload.get("draft")
    source = dict(draft_payload or {}) if isinstance(draft_payload, dict) else dict(payload)
    summary_fields = TicketSummaryFields.from_dict(source.get("summary_fields"))
    conclusion_payload = source.get("conclusion")
    conclusion = (
        conclusion_payload
        if isinstance(conclusion_payload, TodoConclusion)
        else TodoConclusion(**dict(conclusion_payload or {}))
    )
    return (
        str(source.get("title", "")),
        str(source.get("current_summary", "")),
        summary_fields,
        conclusion,
    )


def _start_hotkey_listener(hotkey_mgr: HotkeyManager, startup_log_file: Path) -> Exception | None:
    try:
        hotkey_mgr.start()
        _append_startup_log(startup_log_file, "startup: hotkey listener started")
        return None
    except Exception as exc:  # pragma: no cover - exercised via tests with monkeypatch
        _append_startup_log(
            startup_log_file,
            f"startup: hotkey listener failed: {exc}\n{traceback.format_exc()}",
        )
        return exc


def _show_build_expired_message(now: datetime | None = None) -> None:
    QMessageBox.critical(
        None,
        "版本支持到期,请重新下载使用",
        build_expiration_message(now=now),
    )


def _build_is_expired(now: datetime | None = None) -> bool:
    if not should_enforce_build_expiration():
        return False
    return get_build_expiration_status(now=now).expired


def _set_windows_app_user_model_id(startup_log_file: Path) -> None:
    if not RUNTIME_CAPABILITIES.is_windows:
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_WINDOWS_APP_USER_MODEL_ID)
        _append_startup_log(
            startup_log_file,
            f"startup: windows app user model id set={_WINDOWS_APP_USER_MODEL_ID}",
        )
    except Exception as exc:
        _append_startup_log(startup_log_file, f"startup: windows app user model id failed: {exc}")


def _install_windows_taskbar_handlers(startup_log_file: Path) -> None:
    if not RUNTIME_CAPABILITIES.is_windows:
        return
    installed = install_windows_taskbar_tasks()
    _append_startup_log(
        startup_log_file,
        f"startup: windows taskbar tasks installed={installed}",
    )


def _apply_application_icon(app: QApplication, startup_log_file: Path) -> QIcon:
    app_icon_path = icon_file()
    app_icon = QIcon(str(app_icon_path))
    app.setApplicationName(_APP_NAME)
    app.setWindowIcon(app_icon)
    _append_startup_log(
        startup_log_file,
        f"startup: app icon path={app_icon_path} exists={app_icon_path.exists()}",
    )
    return app_icon


def _show_startup_control_panel(control_panel: ControlPanelWindow, startup_log_file: Path) -> None:
    control_panel.show_panel("server")
    _append_startup_log(startup_log_file, "startup: control panel shown")


def _install_macos_dock_handlers(
    app: QApplication,
    *,
    show_control_panel,
    request_capture,
    startup_log_file: Path,
):
    if not RUNTIME_CAPABILITIES.is_macos:
        return None

    dock_menu = QMenu()
    action_capture = QAction("开始截图", app)
    action_capture.triggered.connect(lambda: request_capture("dock"))
    dock_menu.addAction(action_capture)

    set_as_dock_menu = getattr(dock_menu, "setAsDockMenu", None)
    if callable(set_as_dock_menu):
        set_as_dock_menu()
        _append_startup_log(startup_log_file, "startup: macos dock menu installed")
    else:
        _append_startup_log(startup_log_file, "startup: macos dock menu unavailable")

    activation_filter = _ApplicationActivationFilter(lambda: show_control_panel("server"), app)
    app.installEventFilter(activation_filter)
    app.applicationStateChanged.connect(
        lambda state: _handle_application_state_changed(state, show_control_panel)
    )
    _append_startup_log(startup_log_file, "startup: macos dock activation handler installed")
    return SimpleNamespace(
        dock_menu=dock_menu,
        activation_filter=activation_filter,
        actions=(action_capture,),
    )


def main() -> None:
    startup_command = parse_startup_command(sys.argv)
    instance_guard = SingleInstanceGuard()
    if not instance_guard.acquire():
        if startup_command is not None and send_app_command(startup_command):
            return
        show_already_running_message()
        return

    startup_log_file = _setup_exception_handler()
    _append_startup_log(startup_log_file, "startup: main entered")

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    _set_windows_app_user_model_id(startup_log_file)
    _install_windows_taskbar_handlers(startup_log_file)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app_icon = _apply_application_icon(app, startup_log_file)
    app.setFont(QFont(RUNTIME_CAPABILITIES.ui_font))
    _append_startup_log(startup_log_file, "startup: QApplication ready")

    if _build_is_expired():
        _append_startup_log(startup_log_file, "startup: packaged build expired")
        _show_build_expired_message()
        return

    config_mgr = ConfigManager()
    initial_config = config_mgr.load()
    theme_controller = ThemeController(initial_config.theme)
    app.setFont(QFont(str(theme_controller.tokens.get("uiFont") or RUNTIME_CAPABILITIES.ui_font)))
    theme_controller.themeChanged.connect(
        lambda: app.setFont(QFont(str(theme_controller.tokens.get("uiFont") or RUNTIME_CAPABILITIES.ui_font)))
    )
    hotkey_mgr = _build_hotkey_manager(config_mgr, initial_config)
    _append_startup_log(startup_log_file, f"startup: capture hotkey configured={hotkey_mgr.hotkey}")
    notification_bridge = AppNotificationBridge()
    notification_window = AppNotificationWindow(notification_bridge, theme_controller=theme_controller)
    command_dispatcher = _AppCommandDispatcher()
    command_server = AppCommandServer(command_dispatcher.dispatch)
    try:
        command_server.start()
        _append_startup_log(startup_log_file, "startup: command server started")
    except Exception as exc:
        _append_startup_log(startup_log_file, f"startup: command server failed: {exc}")
    control_panel = None
    toolbar = FloatingToolbar(theme_controller=theme_controller)
    todo_store = TodoStore()
    log_analysis_store = LogAnalysisTaskStore()
    binding_store = TodoBindingStore()
    todo_event_bus = TodoEventBus(
        handlers=[
            WorkOrderSyncEventHandler(
                binding_store=binding_store,
                config_provider=config_mgr.load,
            ),
            ScriptEventHandler(binding_store=binding_store),
            KnowledgeArchiveEventHandler(
                todo_store=todo_store,
                runtime_config_provider=lambda: _build_runtime_config(config_mgr.load()),
            ),
        ],
        binding_store=binding_store,
    )
    todo_controller = TodoController(todo_store, event_publisher=todo_event_bus)
    control_panel = ControlPanelWindow(
        config_mgr,
        theme_controller=theme_controller,
        notification_bridge=notification_bridge,
        event_publisher=todo_event_bus,
    )
    control_panel.setWindowIcon(app_icon)
    todo_panel = TodoPanel(theme_controller=theme_controller)
    todo_detail_panel = TodoDetailPanel(notification_bridge=notification_bridge, theme_controller=theme_controller)
    todo_detail_panel.set_pinned(todo_panel.pinned)
    toolbar.set_scenario_selector_visible(True)

    capture_session = CaptureSession()
    analysis_metrics_store = AnalysisMetricsStore()
    log_analysis_workers: list[LogAnalysisWorker] = []
    stage_summary_workers: list[StageSummaryWorker] = []
    assist_analysis_workers: list[AssistAnalysisWorker] = []
    ticket_enrichment_workers: list[TicketEnrichmentWorker] = []
    pending_ticket_enrichment_jobs: dict[str, tuple[str, object]] = {}
    pending_assist_analysis_keys: set[str] = set()
    capture_ui = CaptureUiFlow(
        toolbar=toolbar,
        todo_panel=todo_panel,
        todo_detail_panel=todo_detail_panel,
        capture_session=capture_session,
    )
    def _resolve_tray_icon_path() -> Path:
        if not RUNTIME_CAPABILITIES.is_macos:
            return icon_file()
        style_hints = app.styleHints()
        is_dark_mode = False
        color_scheme = getattr(style_hints, "colorScheme", None)
        if callable(color_scheme):
            is_dark_mode = color_scheme() == Qt.ColorScheme.Dark
        return icon_file(dark_mode=is_dark_mode)

    tray_icon_path = _resolve_tray_icon_path()
    tray_icon = QSystemTrayIcon(QIcon(str(tray_icon_path)), app)
    tray_icon.setToolTip("AICA")
    _append_startup_log(
        startup_log_file,
        f"startup: tray icon path={tray_icon_path} exists={tray_icon_path.exists()}",
    )

    def _update_tray_icon() -> None:
        current_path = _resolve_tray_icon_path()
        tray_icon.setIcon(QIcon(str(current_path)))
        _append_startup_log(
            startup_log_file,
            f"startup: tray icon updated path={current_path} exists={current_path.exists()}",
        )

    def _show_control_panel(section_id: str = "server") -> None:
        control_panel.show_panel(section_id)

    def _show_missing_settings_message() -> None:
        QMessageBox.information(
            None,
            "请先完成设置",
            "当前未配置可用的服务端地址或本地截图分析模型。\n请点击系统托盘中的 Chattodo 图标，打开控制面板完成设置。",
        )

    def _request_capture(source: str) -> None:
        _append_startup_log(startup_log_file, f"capture: request source={source}")
        if analysis_flow.capture_locked:
            _append_startup_log(startup_log_file, "capture: ignored because analysis capture is locked")
            return
        if toolbar.is_loading():
            _append_startup_log(startup_log_file, "capture: ignored because toolbar is loading")
            return
        if capture_session.current_capture is not None:
            _append_startup_log(startup_log_file, "capture: ignored because a capture is already active")
            return

        if capture_ui.any_overlay_visible():
            _append_startup_log(startup_log_file, "capture: hiding active overlays")
            _hide_overlays(reset=True)
            capture_session.active_overlay = None
            toolbar.hide()
            _refresh_todo_panel()
        else:
            _append_startup_log(startup_log_file, "capture: scheduling overlays")
            toolbar.hide()
            QTimer.singleShot(50, _show_overlays)

    def _quit_application() -> None:
        tray_icon.hide()
        notification_window.hide()
        control_panel.hide()
        app.quit()

    def _handle_app_command(command: str) -> None:
        _append_startup_log(startup_log_file, f"command: received={command}")
        if command == COMMAND_OPEN_PANEL:
            _show_control_panel("server")
        elif command == COMMAND_CAPTURE:
            _request_capture("taskbar")
        elif command == COMMAND_QUIT:
            _quit_application()

    tray_menu = QMenu()
    action_capture = QAction("开始截图", app)
    action_open_panel = QAction("打开控制面板", app)
    action_exit = QAction("退出", app)
    action_capture.triggered.connect(lambda: _request_capture("tray"))
    action_open_panel.triggered.connect(lambda: _show_control_panel("server"))
    action_exit.triggered.connect(_quit_application)
    tray_menu.addAction(action_capture)
    tray_menu.addSeparator()
    tray_menu.addAction(action_open_panel)
    tray_menu.addSeparator()
    tray_menu.addAction(action_exit)
    tray_icon.setContextMenu(tray_menu)
    macos_dock_handlers = _install_macos_dock_handlers(
        app,
        show_control_panel=_show_control_panel,
        request_capture=_request_capture,
        startup_log_file=startup_log_file,
    )

    def _on_tray_activated(reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            _show_control_panel("server")

    tray_icon.activated.connect(_on_tray_activated)
    style_hints = app.styleHints()
    color_scheme_changed = getattr(style_hints, "colorSchemeChanged", None)
    if RUNTIME_CAPABILITIES.is_macos and color_scheme_changed is not None:
        color_scheme_changed.connect(lambda *_args: _update_tray_icon())
    def _refresh_todo_panel() -> None:
        todo_panel.set_todos(
            todo_controller.get_active_todos(),
            todo_controller.selected_todo_id,
        )

    def _show_todo_detail(todo_id: str) -> None:
        todo = todo_controller.get_todo_detail(todo_id)
        if todo is None:
            return
        timeline_ids = [event.id for event in todo.timeline]
        todo_detail_panel.show_todo(
            todo,
            todo_panel.frameGeometry(),
            sync_records=binding_store.list_record_payloads(todo_id),
            task_status_map=log_analysis_store.list_task_status_by_timeline_ids(todo_id, timeline_ids),
        )

    def _build_selected_todo_context() -> object:
        todo = todo_controller.get_selected_todo()
        if todo is None:
            return ""
        return build_context_summary_request_for_todo(
            todo,
            summary_goal="append_screenshot_context",
            description=str(todo.current_summary or "").strip() or str(todo.title or "").strip(),
            max_items=10,
            max_chars=2000,
        )

    def _save_analysis_to_todo(snapshot) -> tuple[str, str]:
        previous_todo = todo_controller.get_selected_todo()
        save_result = todo_controller.save_analysis_result(
            snapshot,
            toolbar.get_current_scenario(),
        )
        _refresh_todo_panel()
        _start_ticket_enrichment(previous_todo or save_result.todo, save_result.todo)
        _start_assist_analysis_prewarm(save_result.todo)
        return save_result.action, save_result.todo.title

    def _show_overlays() -> None:
        screens = app.screens()
        _append_startup_log(startup_log_file, f"capture: show overlays requested screens={len(screens)}")
        capture_ui.rebuild_overlays(
            screens,
            overlay_factory=lambda screen: OverlayWindow(screen, theme_controller=theme_controller),
            on_selection_complete=_on_selection_complete,
            on_selection_changed=_on_selection_changed,
            on_cancel=_on_cancel,
        )
        capture_ui.show_overlays()
        visible_count = sum(1 for overlay in capture_ui.overlays if overlay.isVisible())
        _append_startup_log(
            startup_log_file,
            f"capture: overlays shown total={len(capture_ui.overlays)} visible={visible_count}",
        )

    def _hide_overlays(*, reset: bool = True, preserve_active: bool = False) -> None:
        capture_ui.hide_overlays(reset=reset, preserve_active=preserve_active)

    def _sync_capture_from_active_overlay() -> bool:
        return capture_session.sync_from_active_overlay()

    def _clear_capture_state() -> None:
        capture_ui.clear_capture_state(_refresh_todo_panel)

    def _release_capture_mode() -> None:
        capture_ui.release_capture_mode(_refresh_todo_panel)

    def _restore_toolbar_for_current_capture() -> None:
        capture_ui.restore_toolbar_for_current_capture()

    def _queue_current_capture() -> bool:
        return capture_ui.queue_current_capture()

    def _build_runtime_config(config):
        llm_service = LLMService(config)
        server_config = config.server
        server_ready = (
            bool(getattr(server_config, "enabled", False))
            and str(getattr(server_config, "base_url", "") or "").strip()
            and str(getattr(server_config, "api_key", "") or "").strip()
        )
        try:
            analysis_timeout_seconds = llm_service.resolve_task_model("analysis").reference.timeout_seconds
        except ModelResolutionError:
            if not server_ready:
                raise
            analysis_timeout_seconds = max(1, int(getattr(server_config, "timeout_seconds", 30) or 30))
        try:
            plan_export_timeout_seconds = llm_service.resolve_task_model("plan_export").reference.timeout_seconds
        except ModelResolutionError:
            plan_export_timeout_seconds = 30
        return SimpleNamespace(
            app_config=config,
            llm_service=llm_service,
            server_config=server_config,
            analysis_model_label="Chattodo 服务端优先 / 本地兜底",
            analysis_timeout_seconds=analysis_timeout_seconds,
            plan_export_timeout_seconds=plan_export_timeout_seconds,
        )

    def _build_ticket_enrichment_service(config):
        return TicketEnrichmentService(
            feature_point_provider=build_feature_point_provider(server_config=config.server),
            root_cause_provider=build_root_cause_provider(server_config=config.server),
        )

    def _cleanup_ticket_enrichment_worker(worker: TicketEnrichmentWorker) -> None:
        if worker in ticket_enrichment_workers:
            ticket_enrichment_workers.remove(worker)
        worker.deleteLater()

    def _notify_ticket_enrichment_issue(message: str, *, level: str = "warning") -> None:
        normalized = str(message or "").strip()
        if not normalized:
            return
        notification_bridge.notify(
            level,
            f"待办字段后台生成未完成：{normalized}",
            4800,
            "ticket_enrichment",
        )

    def _on_ticket_enrichment_finished(todo_id: str, request_id: str, outcome: object) -> None:
        pending = pending_ticket_enrichment_jobs.get(todo_id)
        if pending is None or pending[0] != request_id:
            return
        _, job = pending
        pending_ticket_enrichment_jobs.pop(todo_id, None)
        current_todo = todo_store.get_todo(todo_id)
        if current_todo is None or not is_ticket_enrichment_job_still_current(current_todo, job):
            return
        error_message = summarize_enrichment_errors(list(getattr(outcome, "errors", []) or []))
        if error_message:
            _notify_ticket_enrichment_issue(error_message)
        enriched_fields = TicketSummaryFields.from_dict(
            getattr(outcome, "summary_fields", current_todo.summary_fields).to_dict()
        )
        merged_fields = merge_async_enrichment_fields(
            current_fields=current_todo.summary_fields,
            enriched_fields=enriched_fields,
            conclusion_changed=str(job.previous_conclusion or "").strip() != str(job.current_conclusion or "").strip(),
        )
        if merged_fields.to_dict() == current_todo.summary_fields.to_dict():
            return
        updated = todo_controller.update_todo(
            todo_id,
            summary_fields=merged_fields,
            run_enrichment=False,
        )
        if updated is None:
            return
        if todo_controller.detail_todo_id == todo_id:
            _show_todo_detail(todo_id)
        _refresh_todo_panel()

    def _on_ticket_enrichment_error(todo_id: str, request_id: str, message: str) -> None:
        pending = pending_ticket_enrichment_jobs.get(todo_id)
        if pending is not None and pending[0] == request_id:
            pending_ticket_enrichment_jobs.pop(todo_id, None)
            _notify_ticket_enrichment_issue(
                str(message or "").strip() or "后台任务执行失败",
                level="error",
            )

    def _start_ticket_enrichment(previous_todo, current_todo) -> None:
        if previous_todo is None or current_todo is None:
            return
        request_id = str(uuid.uuid4())
        job = build_ticket_enrichment_job(previous_todo=previous_todo, current_todo=current_todo)
        pending_ticket_enrichment_jobs[current_todo.id] = (request_id, job)
        worker = TicketEnrichmentWorker(
            enrichment_service=_build_ticket_enrichment_service(config_mgr.load()),
            request_id=request_id,
            job=job,
        )
        ticket_enrichment_workers.append(worker)
        worker.finished.connect(_on_ticket_enrichment_finished)
        worker.finished.connect(lambda _todo_id, _request_id, _outcome, current=worker: _cleanup_ticket_enrichment_worker(current))
        worker.error.connect(_on_ticket_enrichment_error)
        worker.error.connect(lambda _todo_id, _request_id, _message, current=worker: _cleanup_ticket_enrichment_worker(current))
        worker.start()

    result_flow = ResultFlowCoordinator(
        get_scenario=toolbar.get_current_scenario,
        get_model=lambda: "Chattodo 服务端 / 截图分析",
        save_result_to_todo=_save_analysis_to_todo,
        clear_capture_state=_clear_capture_state,
        theme_controller=theme_controller,
    )

    def _on_hotkey() -> None:
        _request_capture("hotkey")

    def _on_selection_complete(rect: QRect, cropped: QPixmap) -> None:
        selected_overlay = app.sender()
        if not isinstance(selected_overlay, OverlayWindow):
            return
        capture_ui.handle_selection_complete(selected_overlay, rect, cropped)

    def _on_selection_changed(rect: QRect) -> None:
        capture_ui.handle_selection_changed(rect)

    def _ensure_api_key_configured():
        config = config_mgr.load()
        server_config = config.server
        server_ready = (
            bool(getattr(server_config, "enabled", False))
            and str(getattr(server_config, "base_url", "") or "").strip()
            and str(getattr(server_config, "api_key", "") or "").strip()
        )
        if not server_ready:
            try:
                LLMService(config).resolve_task_model("analysis")
            except ModelResolutionError:
                _show_missing_settings_message()
                return None
        try:
            return _build_runtime_config(config)
        except ModelResolutionError:
            _show_missing_settings_message()
            return None

    def _handle_analysis_finished(
        result,
        feedback_image_base64: str,
        analysis_stats=None,
        prompt_trace_id: str = "",
        prompt_version: str = "built-in",
    ) -> None:
        result_flow.handle_ai_finished(
            result,
            feedback_image_base64=feedback_image_base64,
            analysis_stats=analysis_stats,
            prompt_trace_id=prompt_trace_id,
            prompt_version=prompt_version,
        )

    analysis_flow = AnalysisFlowCoordinator(
        capture_session=capture_session,
        toolbar=toolbar,
        get_scenario=toolbar.get_current_scenario,
        get_analysis_intent=toolbar.build_analysis_intent,
        get_analysis_context=_build_selected_todo_context,
        ensure_api_key_configured=_ensure_api_key_configured,
        hide_overlays=_hide_overlays,
        restore_toolbar_for_current_capture=_restore_toolbar_for_current_capture,
        on_finished=_handle_analysis_finished,
        single_worker_factory=AIWorker,
        multi_worker_factory=MultiCaptureAIWorker,
        show_warning=lambda title, message: QMessageBox.warning(None, title, message),
        record_analysis_metrics=lambda stats, success: analysis_metrics_store.record(stats, success=success),
        show_loading=lambda: (_refresh_todo_panel(), todo_panel.set_analysis_loading(True)),
        hide_loading=lambda: todo_panel.set_analysis_loading(False),
    )

    def _on_summarize() -> None:
        print(
            "[DEBUG] _on_summarize called, "
            f"current_selection={capture_session.current_selection}, "
            f"session_count={len(capture_session.queued_captures)}"
        )
        analysis_flow.start_analysis()

    def _on_continue_capture() -> None:
        if not _queue_current_capture():
            return
        _release_capture_mode()

    def _on_cancel() -> None:
        _clear_capture_state()

    def _on_copy_capture() -> None:
        if not _sync_capture_from_active_overlay():
            QMessageBox.warning(None, "错误", "当前没有可复制的截图")
            return

        QApplication.clipboard().setPixmap(capture_session.current_capture)
        _clear_capture_state()

    def _on_edit_mode_changed(mode: str) -> None:
        if capture_session.active_overlay is not None:
            capture_session.active_overlay.set_edit_mode(mode)

    def _on_undo_annotation() -> None:
        if capture_session.active_overlay is None:
            return
        capture_session.active_overlay.undo_last_annotation()
        _sync_capture_from_active_overlay()

    def _on_clear_annotations() -> None:
        if capture_session.active_overlay is None:
            return
        capture_session.active_overlay.clear_annotations()
        _sync_capture_from_active_overlay()

    def _on_todo_selected(todo_id: str) -> None:
        todo_controller.toggle_selected_todo(todo_id)
        _refresh_todo_panel()

    def _on_todo_completed(todo_id: str) -> None:
        was_detail_open = todo_controller.detail_todo_id == todo_id
        if todo_controller.complete_todo(todo_id):
            if was_detail_open:
                todo_detail_panel.hide()
            else:
                _refresh_todo_panel()
                return
        _refresh_todo_panel()

    def _on_todo_selection_cleared() -> None:
        todo_controller.clear_selected_todo()
        _refresh_todo_panel()

    def _on_todo_detail_requested(todo_id: str) -> None:
        _show_todo_detail(todo_id)

    def _on_todo_detail_saved(todo_id: str, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        previous_todo = todo_store.get_todo(todo_id)
        action = str(payload.get("action", "")).strip()
        save_mode = payload.get("saveMode")
        title, current_summary, summary_fields, conclusion = _resolve_todo_detail_draft(payload)
        timeline_payload = payload.get("timeline", [])
        if action == "append_timeline_entry":
            current_todo = todo_store.get_todo(todo_id)
            if current_todo is None:
                return
            event_payload = payload.get("event")
            event = (
                event_payload
                if hasattr(event_payload, "id")
                else None
            )
            if event is None:
                return
            timeline_payload = [*current_todo.timeline, event]
        elif action == "save_conclusion":
            timeline_payload = None
        updated = todo_controller.update_todo(
            todo_id,
            title=title,
            current_summary=current_summary,
            summary_fields=summary_fields,
            timeline=timeline_payload,
            conclusion=conclusion,
            run_enrichment=False,
        )
        if updated is None:
            return
        if should_run_ticket_enrichment_for_todo_detail_save(action, save_mode):
            _start_ticket_enrichment(previous_todo, updated)
        todo_detail_panel.show_todo(
            updated,
            todo_panel.frameGeometry(),
            sync_records=binding_store.list_record_payloads(todo_id),
            task_status_map=log_analysis_store.list_task_status_by_timeline_ids(
                todo_id,
                [event.id for event in updated.timeline],
            ),
            preserve_position=True,
        )
        _refresh_todo_panel()
        control_panel.refresh_tickets_from_store()

    log_analysis_orchestrator = LogAnalysisOrchestrator(
        todo_store=todo_store,
        task_store=log_analysis_store,
        app_config=initial_config,
    )

    def _cleanup_log_analysis_worker(worker: LogAnalysisWorker) -> None:
        if worker in log_analysis_workers:
            log_analysis_workers.remove(worker)
        worker.deleteLater()

    def _cleanup_stage_summary_worker(worker: StageSummaryWorker) -> None:
        if worker in stage_summary_workers:
            stage_summary_workers.remove(worker)

    def _cleanup_assist_analysis_worker(worker: AssistAnalysisWorker) -> None:
        if worker in assist_analysis_workers:
            assist_analysis_workers.remove(worker)
        worker.deleteLater()

    def _clear_pending_assist_analysis_key(payload: object) -> None:
        if not isinstance(payload, dict):
            return
        if not bool(payload.get("isFinal", True)):
            return
        cache_key = str(payload.get("cacheKey", "") or "").strip()
        if cache_key:
            pending_assist_analysis_keys.discard(cache_key)

    def _on_log_analysis_finished(task_id: str) -> None:
        task = log_analysis_store.get_task(task_id)
        if task is not None and todo_controller.detail_todo_id == task.todo_id:
            _show_todo_detail(task.todo_id)
        _refresh_todo_panel()

    def _on_log_analysis_error(task_id: str, _message: str) -> None:
        task = log_analysis_store.get_task(task_id)
        if task is not None and todo_controller.detail_todo_id == task.todo_id:
            _show_todo_detail(task.todo_id)
        _refresh_todo_panel()

    def _on_log_analysis_progress(task_id: str) -> None:
        task = log_analysis_store.get_task(task_id)
        if task is None:
            return
        if todo_controller.detail_todo_id == task.todo_id:
            _show_todo_detail(task.todo_id)

    def _on_log_analysis_requested(todo_id: str, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        task = log_analysis_store.create_task(
            LogAnalysisTask(
                todo_id=todo_id,
                timeline_entry_id=str(payload.get("timelineEntryId", "")),
                status="queued",
                current_step="正在收集附件...",
                raw_command=str(payload.get("rawCommand", "")),
                parsed_focus_json=dict(payload.get("parsedFocus", {}) or {}),
                attachment_snapshot_json=list(payload.get("attachments", []) or []),
            )
        )
        worker = LogAnalysisWorker(orchestrator=log_analysis_orchestrator, task_id=task.id)
        log_analysis_workers.append(worker)
        worker.progress.connect(_on_log_analysis_progress)
        worker.finished.connect(_on_log_analysis_finished)
        worker.finished.connect(lambda _task_id, current=worker: _cleanup_log_analysis_worker(current))
        worker.error.connect(_on_log_analysis_error)
        worker.error.connect(lambda _task_id, _message, current=worker: _cleanup_log_analysis_worker(current))
        worker.start()
        if todo_controller.detail_todo_id == todo_id:
            _show_todo_detail(todo_id)

    def _on_todo_detail_closed() -> None:
        todo_controller.close_detail()
        _refresh_todo_panel()

    def _on_todo_detail_completed(todo_id: str) -> None:
        if todo_controller.complete_todo(todo_id):
            todo_detail_panel.hide()
        _refresh_todo_panel()

    def _on_todo_detail_deleted(todo_id: str) -> None:
        if todo_controller.delete_todo(todo_id):
            todo_detail_panel.hide()
        _refresh_todo_panel()

    def _on_todo_detail_manual_sync(todo_id: str) -> None:
        event = todo_controller.build_manual_sync_event(todo_id)
        if event is None:
            return
        todo_event_bus.dispatch(event, async_dispatch=True)
        _show_todo_detail(todo_id)
        _refresh_todo_panel()

    def _on_stage_summary_finished(todo_id: str, request_id: str, summary_text: str, notice: str) -> None:
        todo_detail_panel.apply_stage_summary_result(todo_id, request_id, summary_text, notice)

    def _on_stage_summary_error(todo_id: str, request_id: str, message: str) -> None:
        todo_detail_panel.apply_stage_summary_error(todo_id, request_id, message)

    def _on_assist_analysis_finished(todo_id: str, request_id: str, payload: object) -> None:
        todo_detail_panel.apply_assist_analysis_result(todo_id, request_id, payload)

    def _on_assist_analysis_error(todo_id: str, request_id: str, message: str) -> None:
        todo_detail_panel.apply_assist_analysis_error(todo_id, request_id, message)

    def _build_assist_worker_payload(todo, *, previous_result: object | None = None) -> dict[str, object]:
        todo_payload = build_assist_todo_payload(todo)
        payload: dict[str, object] = {
            "requestId": str(uuid.uuid4()),
            "todoPayload": todo_payload,
            "cacheKey": build_assist_analysis_cache_key(todo.id, todo_payload),
        }
        if previous_result is not None:
            payload["previousResult"] = previous_result
        return payload

    def _start_assist_analysis_review(todo, previous_result: object) -> None:
        payload = _build_assist_worker_payload(todo, previous_result=previous_result)
        pending_assist_analysis_keys.add(str(payload["cacheKey"]))
        worker = AssistAnalysisWorker(
            llm_service=LLMService(config_mgr.load()),
            todo_id=todo.id,
            request_id=str(payload["requestId"]),
            payload=payload,
            phase="review",
        )
        assist_analysis_workers.append(worker)
        worker.result_ready.connect(_on_assist_analysis_review_finished)
        worker.finished.connect(lambda current=worker: _cleanup_assist_analysis_worker(current))
        worker.error.connect(lambda _todo_id, _request_id, _message, current=worker: _cleanup_assist_analysis_worker(current))
        worker.start()

    def _on_assist_analysis_prewarm_finished(todo_id: str, _request_id: str, payload: object) -> None:
        todo_detail_panel.cache_assist_analysis_result(todo_id, payload)
        _clear_pending_assist_analysis_key(payload)
        if not isinstance(payload, dict) or not bool(payload.get("isFinal", True)):
            return
        latest = todo_store.get_todo(todo_id)
        if latest is not None:
            _start_assist_analysis_review(latest, payload)

    def _on_assist_analysis_review_finished(todo_id: str, _request_id: str, payload: object) -> None:
        _clear_pending_assist_analysis_key(payload)
        if isinstance(payload, dict) and bool(payload.get("shouldUpdate", True)):
            todo_detail_panel.cache_assist_analysis_result(todo_id, payload)

    def _start_assist_analysis_prewarm(todo) -> None:
        if todo is None:
            return
        payload = _build_assist_worker_payload(todo)
        cache_key = str(payload["cacheKey"])
        if cache_key in pending_assist_analysis_keys:
            return
        pending_assist_analysis_keys.add(cache_key)
        worker = AssistAnalysisWorker(
            llm_service=LLMService(config_mgr.load()),
            todo_id=todo.id,
            request_id=str(payload["requestId"]),
            payload=payload,
            phase="initial",
        )
        assist_analysis_workers.append(worker)
        worker.result_ready.connect(_on_assist_analysis_prewarm_finished)
        worker.finished.connect(lambda current=worker: _cleanup_assist_analysis_worker(current))
        worker.error.connect(lambda _todo_id, _request_id, _message, current=worker: _cleanup_assist_analysis_worker(current))
        worker.start()

    def _start_stage_summary_worker(todo_id: str, request_id: str, mode: str, payload: dict[str, object]) -> None:
        config = config_mgr.load()
        worker = StageSummaryWorker(
            llm_service=LLMService(config),
            todo_id=todo_id,
            request_id=request_id,
            mode=mode,
            payload=payload,
            server_config=config.server,
        )
        stage_summary_workers.append(worker)
        worker.finished.connect(_on_stage_summary_finished)
        worker.finished.connect(lambda _todo_id, _request_id, _text, _notice, current=worker: _cleanup_stage_summary_worker(current))
        worker.error.connect(_on_stage_summary_error)
        worker.error.connect(lambda _todo_id, _request_id, _message, current=worker: _cleanup_stage_summary_worker(current))
        worker.start()

    def _on_assist_analysis_requested(todo_id: str, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        request_id = str(payload.get("requestId", "")).strip()
        if not request_id:
            return
        cache_key = str(payload.get("cacheKey", "") or "").strip()
        if not cache_key and isinstance(payload.get("todoPayload"), dict):
            cache_key = build_assist_analysis_cache_key(todo_id, payload.get("todoPayload"))
            payload = {**payload, "cacheKey": cache_key}
        if cache_key and cache_key in pending_assist_analysis_keys:
            return
        if cache_key:
            pending_assist_analysis_keys.add(cache_key)
        config = config_mgr.load()
        worker = AssistAnalysisWorker(
            llm_service=LLMService(config),
            todo_id=todo_id,
            request_id=request_id,
            payload=payload,
        )
        assist_analysis_workers.append(worker)
        worker.result_ready.connect(_on_assist_analysis_finished)
        worker.result_ready.connect(lambda _todo_id, _request_id, _payload: _clear_pending_assist_analysis_key(_payload))
        worker.finished.connect(lambda current=worker: _cleanup_assist_analysis_worker(current))
        worker.error.connect(_on_assist_analysis_error)
        worker.error.connect(lambda _todo_id, _request_id, _message, key=cache_key: pending_assist_analysis_keys.discard(key) if key else None)
        worker.error.connect(lambda _todo_id, _request_id, _message, current=worker: _cleanup_assist_analysis_worker(current))
        worker.start()

    def _on_stage_summary_requested(todo_id: str, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        request_id = str(payload.get("requestId", "")).strip()
        if not request_id:
            return
        _start_stage_summary_worker(todo_id, request_id, "rollup", payload)

    def _on_stage_summary_rewrite_requested(todo_id: str, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        request_id = str(payload.get("requestId", "")).strip()
        if not request_id:
            return
        _start_stage_summary_worker(todo_id, request_id, "rewrite", payload)

    def _on_control_panel_saved(saved_config) -> None:
        try:
            hotkey_mgr.update_hotkey(saved_config.hotkeys.capture)
        except ValueError:
            hotkey_mgr.update_hotkey(RUNTIME_CAPABILITIES.default_capture_hotkey)
        log_analysis_orchestrator.update_app_config(saved_config)

    def _on_project_saved(project_id: str) -> None:
        normalized_project_id = str(project_id or "").strip()
        current_todo_id = todo_controller.detail_todo_id
        if current_todo_id is None:
            return
        todo = todo_store.get_todo(current_todo_id)
        if todo is None:
            return
        if str(todo.project_link.project_id or "").strip() == normalized_project_id:
            if not todo_detail_panel.refresh_project_product_lines(project_id):
                _show_todo_detail(current_todo_id)
            return
        refreshed_todo = todo_controller.get_todo_detail(current_todo_id)
        if refreshed_todo is not None and str(refreshed_todo.project_link.project_id or "").strip() == normalized_project_id:
            _show_todo_detail(current_todo_id)

    control_panel.config_saved.connect(_on_control_panel_saved)
    control_panel.todo_list_refresh_requested.connect(_refresh_todo_panel)
    control_panel.project_saved.connect(_on_project_saved)
    hotkey_mgr.hotkey_triggered.connect(_on_hotkey)
    toolbar.summarize_clicked.connect(_on_summarize)
    toolbar.continue_capture_clicked.connect(_on_continue_capture)
    toolbar.copy_clicked.connect(_on_copy_capture)
    toolbar.cancel_clicked.connect(_on_cancel)
    toolbar.edit_mode_changed.connect(_on_edit_mode_changed)
    toolbar.undo_clicked.connect(_on_undo_annotation)
    toolbar.clear_annotations_clicked.connect(_on_clear_annotations)
    todo_panel.todo_selected.connect(_on_todo_selected)
    todo_panel.todo_completed.connect(_on_todo_completed)
    todo_panel.selection_cleared.connect(_on_todo_selection_cleared)
    todo_panel.detail_requested.connect(_on_todo_detail_requested)
    todo_panel.pinned_changed.connect(todo_detail_panel.set_pinned)
    todo_detail_panel.save_requested.connect(_on_todo_detail_saved)
    todo_detail_panel.log_analysis_requested.connect(_on_log_analysis_requested)
    todo_detail_panel.closed.connect(_on_todo_detail_closed)
    todo_detail_panel.complete_requested.connect(_on_todo_detail_completed)
    todo_detail_panel.delete_requested.connect(_on_todo_detail_deleted)
    todo_detail_panel.manual_sync_requested.connect(_on_todo_detail_manual_sync)
    todo_detail_panel.stage_summary_requested.connect(_on_stage_summary_requested)
    todo_detail_panel.stage_summary_rewrite_requested.connect(_on_stage_summary_rewrite_requested)
    todo_detail_panel.assist_analysis_requested.connect(_on_assist_analysis_requested)
    command_dispatcher.command_received.connect(_handle_app_command)
    if startup_command is not None:
        QTimer.singleShot(0, lambda command=startup_command: _handle_app_command(command))

    try:
        _refresh_todo_panel()
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray_icon.show()
            _append_startup_log(startup_log_file, "startup: tray icon shown")
            _show_startup_control_panel(control_panel, startup_log_file)
        else:
            _append_startup_log(startup_log_file, "startup: system tray unavailable")
            _show_startup_control_panel(control_panel, startup_log_file)
        hotkey_error = _start_hotkey_listener(hotkey_mgr, startup_log_file)
        if hotkey_error is not None:
            QMessageBox.warning(
                None,
                "截图热键不可用",
                hotkey_failure_message(
                    hotkey_mgr.hotkey,
                    hotkey_error,
                    log_file=startup_log_file,
                    platform_id=RUNTIME_CAPABILITIES.platform_id,
                ),
            )
        sys.exit(app.exec())
    finally:
        tray_icon.hide()
        notification_window.hide()
        control_panel.hide()
        command_server.stop()
        hotkey_mgr.stop()
        instance_guard.release()


if __name__ == "__main__":
    main()

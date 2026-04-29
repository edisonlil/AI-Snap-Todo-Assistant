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

from PyQt6.QtCore import QRect, QTimer, Qt
from PyQt6.QtGui import QAction, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon

from aica.analysis_flow import AnalysisFlowCoordinator
from aica.analysis_metrics import AnalysisMetricsStore
from aica.app_notifications import AppNotificationBridge, AppNotificationWindow
from aica.assist_analysis import build_assist_analysis_cache_key, build_assist_todo_payload
from aica.build_expiration import build_expiration_message, should_enforce_build_expiration, get_build_expiration_status
from aica.capture_session import CaptureSession
from aica.capture_ui_flow import CaptureUiFlow
from aica.config import ConfigManager
from aica.context_summary_models import build_context_summary_request_for_todo
from aica.control_panel import ControlPanelWindow
from aica.hotkey import HotkeyManager
from aica.llm.service import LLMService, ModelResolutionError
from aica.log_analysis_models import LogAnalysisTask
from aica.log_analysis_orchestrator import LogAnalysisOrchestrator
from aica.log_analysis_store import LogAnalysisTaskStore
from aica.log_analysis_worker import LogAnalysisWorker
from aica.loading_dialog import LoadingDialog
from aica.models import TicketSummaryFields
from aica.overlay import OverlayWindow
from aica.paths import error_log_file, icon_file
from aica.result_flow import ResultFlowCoordinator
from aica.runtime import RUNTIME_CAPABILITIES, hotkey_failure_message
from aica.single_instance import SingleInstanceGuard, show_already_running_message
from aica.ticket_enrichment import (
    TicketEnrichmentService,
    build_feature_point_provider,
    build_ticket_enrichment_job,
    is_ticket_enrichment_job_still_current,
    merge_async_enrichment_fields,
    summarize_enrichment_errors,
)
from aica.ticket_enrichment_worker import TicketEnrichmentWorker
from aica.todo_controller import TodoController
from aica.todo_detail_panel import TodoDetailPanel
from aica.todo_detail_save_policy import should_run_ticket_enrichment_for_todo_detail_save
from aica.todo_events import ScriptEventHandler, TodoBindingStore, TodoEventBus
from aica.todo_panel import TodoPanel
from aica.todo_store import TodoConclusion, TodoStore
from aica.toolbar import FloatingToolbar
from aica.worker import (
    AIWorker,
    AssistAnalysisWorker,
    MultiCaptureAIWorker,
    PlanExportWorker,
    StageSummaryWorker,
    build_plan_export_filename,
)


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


def _setup_exception_handler() -> Path:
    """Install a global exception hook and persist uncaught errors to disk."""
    log_file = _resolve_error_log_file()
    _append_startup_log(log_file, "startup: exception handler ready")

    def exception_hook(exc_type, exc_value, exc_tb):
        try:
            with log_file.open("a", encoding="utf-8") as handle:
                handle.write(f"\n{'=' * 60}\n")
                handle.write(f"时间: {datetime.now().isoformat()}\n")
                handle.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        except Exception:
            pass

        QMessageBox.critical(
            None,
            "程序错误",
            f"发生未处理异常，已记录到日志:\n{log_file}\n\n{exc_type.__name__}: {exc_value}",
        )

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


def _notify_plan_export_error(notification_bridge: AppNotificationBridge, message: str) -> None:
    normalized = str(message or "").strip()
    if not normalized:
        return
    notification_bridge.notify("error", normalized, 5200, "plan_export")


def _notify_plan_export_success(notification_bridge: AppNotificationBridge, export_path: str) -> None:
    normalized = str(export_path or "").strip()
    if not normalized:
        return
    notification_bridge.notify("success", f"方案已导出到: {normalized}", 3600, "plan_export")


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


def main() -> None:
    instance_guard = SingleInstanceGuard()
    if not instance_guard.acquire():
        show_already_running_message()
        return

    startup_log_file = _setup_exception_handler()
    _append_startup_log(startup_log_file, "startup: main entered")

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont(RUNTIME_CAPABILITIES.ui_font))
    _append_startup_log(startup_log_file, "startup: QApplication ready")

    if _build_is_expired():
        _append_startup_log(startup_log_file, "startup: packaged build expired")
        _show_build_expired_message()
        return

    config_mgr = ConfigManager()
    initial_config = config_mgr.load()
    hotkey_mgr = _build_hotkey_manager(config_mgr, initial_config)
    notification_bridge = AppNotificationBridge()
    notification_window = AppNotificationWindow(notification_bridge)
    control_panel = ControlPanelWindow(config_mgr, notification_bridge=notification_bridge)
    toolbar = FloatingToolbar()
    todo_store = TodoStore()
    log_analysis_store = LogAnalysisTaskStore()
    binding_store = TodoBindingStore()
    todo_event_bus = TodoEventBus(
        handlers=[ScriptEventHandler(binding_store=binding_store)],
        binding_store=binding_store,
    )
    todo_controller = TodoController(todo_store, event_publisher=todo_event_bus)
    todo_panel = TodoPanel()
    todo_detail_panel = TodoDetailPanel(notification_bridge=notification_bridge)
    todo_detail_panel.set_pinned(todo_panel.pinned)
    loading_dialog = LoadingDialog()
    toolbar.set_scenario_selector_visible(True)

    capture_session = CaptureSession()
    analysis_metrics_store = AnalysisMetricsStore()
    plan_export_workers: list[PlanExportWorker] = []
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

    def _show_control_panel(section_id: str = "models") -> None:
        control_panel.show_panel(section_id)

    def _show_missing_settings_message() -> None:
        QMessageBox.information(
            None,
            "请先完成设置",
            "当前未配置可用的 API Key 或模型绑定。\n请点击系统托盘中的 AICA 图标，打开控制面板完成设置。",
        )

    def _quit_application() -> None:
        tray_icon.hide()
        notification_window.hide()
        control_panel.hide()
        app.quit()

    tray_menu = QMenu()
    action_open_panel = QAction("打开控制面板", app)
    action_exit = QAction("退出", app)
    action_open_panel.triggered.connect(lambda: _show_control_panel("models"))
    action_exit.triggered.connect(_quit_application)
    tray_menu.addAction(action_open_panel)
    tray_menu.addSeparator()
    tray_menu.addAction(action_exit)
    tray_icon.setContextMenu(tray_menu)

    def _on_tray_activated(reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            _show_control_panel("models")

    tray_icon.activated.connect(_on_tray_activated)
    style_hints = app.styleHints()
    color_scheme_changed = getattr(style_hints, "colorSchemeChanged", None)
    if RUNTIME_CAPABILITIES.is_macos and color_scheme_changed is not None:
        color_scheme_changed.connect(lambda *_args: _update_tray_icon())
    todo_panel.geometry_changed.connect(
        lambda: loading_dialog.show_loading(todo_panel) if loading_dialog.isVisible() else None
    )

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
        save_result = todo_controller.save_analysis_result(
            snapshot,
            toolbar.get_current_scenario(),
        )
        _refresh_todo_panel()
        _start_assist_analysis_prewarm(save_result.todo)
        return save_result.action, save_result.todo.title

    def _show_overlays() -> None:
        capture_ui.rebuild_overlays(
            app.screens(),
            overlay_factory=OverlayWindow,
            on_selection_complete=_on_selection_complete,
            on_selection_changed=_on_selection_changed,
            on_cancel=_on_cancel,
        )
        capture_ui.show_overlays()

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

    def _cleanup_plan_export_worker(worker: PlanExportWorker) -> None:
        if worker in plan_export_workers:
            plan_export_workers.remove(worker)
        worker.deleteLater()

    def _build_runtime_config(config):
        llm_service = LLMService(config)
        analysis_ref = llm_service.resolve_task_model("analysis").reference
        plan_export_ref = llm_service.resolve_task_model("plan_export").reference
        return SimpleNamespace(
            app_config=config,
            llm_service=llm_service,
            analysis_timeout_seconds=analysis_ref.timeout_seconds,
            plan_export_timeout_seconds=plan_export_ref.timeout_seconds,
        )

    def _build_ticket_enrichment_service(config):
        runtime_config = None
        try:
            runtime_config = _build_runtime_config(config)
        except ModelResolutionError:
            runtime_config = None
        llm_service = runtime_config.llm_service if runtime_config is not None else None
        return TicketEnrichmentService(
            feature_point_provider=build_feature_point_provider(config.ticket_enrichment.feature_point),
            llm_service=llm_service,
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

    def _on_plan_export_finished(export_path: str) -> None:
        sender = app.sender()
        if isinstance(sender, PlanExportWorker):
            _cleanup_plan_export_worker(sender)
        _notify_plan_export_success(notification_bridge, export_path)

    def _on_plan_export_error(message: str) -> None:
        sender = app.sender()
        if isinstance(sender, PlanExportWorker):
            _cleanup_plan_export_worker(sender)
        _notify_plan_export_error(notification_bridge, message)

    def _on_todo_export_plan_requested(todo_id: str, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        config = _ensure_api_key_configured()
        if config is None:
            return

        default_name = build_plan_export_filename(str(payload.get("title", "")))
        export_path, _ = QFileDialog.getSaveFileName(
            None,
            "导出方案",
            default_name,
            "Markdown 文件 (*.md)",
        )
        if not export_path:
            return
        if not export_path.lower().endswith(".md"):
            export_path = f"{export_path}.md"

        worker = PlanExportWorker(
            config.llm_service,
            config.llm_service.describe_task_model("plan_export"),
            config.plan_export_timeout_seconds,
            payload,
            export_path,
        )
        plan_export_workers.append(worker)
        worker.finished.connect(_on_plan_export_finished)
        worker.error.connect(_on_plan_export_error)
        worker.start()

    result_flow = ResultFlowCoordinator(
        get_scenario=toolbar.get_current_scenario,
        get_model=lambda: _build_runtime_config(config_mgr.load()).llm_service.describe_task_model("analysis"),
        save_result_to_todo=_save_analysis_to_todo,
        clear_capture_state=_clear_capture_state,
    )

    def _on_hotkey() -> None:
        if analysis_flow.capture_locked or toolbar.is_loading() or capture_session.current_capture is not None:
            return

        if capture_ui.any_overlay_visible():
            _hide_overlays(reset=True)
            capture_session.active_overlay = None
            toolbar.hide()
            _refresh_todo_panel()
        else:
            toolbar.hide()
            QTimer.singleShot(50, _show_overlays)

    def _on_selection_complete(rect: QRect, cropped: QPixmap) -> None:
        selected_overlay = app.sender()
        if not isinstance(selected_overlay, OverlayWindow):
            return
        capture_ui.handle_selection_complete(selected_overlay, rect, cropped)

    def _on_selection_changed(rect: QRect) -> None:
        capture_ui.handle_selection_changed(rect)

    def _ensure_api_key_configured():
        config = config_mgr.load()
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
        show_loading=lambda: (_refresh_todo_panel(), loading_dialog.show_loading(todo_panel)),
        hide_loading=loading_dialog.hide_loading,
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
        worker.finished.connect(_on_assist_analysis_review_finished)
        worker.finished.connect(lambda _todo_id, _request_id, _payload, current=worker: _cleanup_assist_analysis_worker(current))
        worker.error.connect(lambda _todo_id, _request_id, _message, current=worker: _cleanup_assist_analysis_worker(current))
        worker.start()

    def _on_assist_analysis_prewarm_finished(todo_id: str, _request_id: str, payload: object) -> None:
        _clear_pending_assist_analysis_key(payload)
        todo_detail_panel.cache_assist_analysis_result(todo_id, payload)
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
        worker.finished.connect(_on_assist_analysis_prewarm_finished)
        worker.finished.connect(lambda _todo_id, _request_id, _payload, current=worker: _cleanup_assist_analysis_worker(current))
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
        worker.finished.connect(_on_assist_analysis_finished)
        worker.finished.connect(lambda _todo_id, _request_id, _payload: _clear_pending_assist_analysis_key(_payload))
        worker.finished.connect(lambda _todo_id, _request_id, _payload, current=worker: _cleanup_assist_analysis_worker(current))
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

    control_panel.config_saved.connect(_on_control_panel_saved)
    control_panel.todo_list_refresh_requested.connect(_refresh_todo_panel)
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
    todo_detail_panel.export_plan_requested.connect(_on_todo_export_plan_requested)
    todo_detail_panel.manual_sync_requested.connect(_on_todo_detail_manual_sync)
    todo_detail_panel.stage_summary_requested.connect(_on_stage_summary_requested)
    todo_detail_panel.stage_summary_rewrite_requested.connect(_on_stage_summary_rewrite_requested)
    todo_detail_panel.assist_analysis_requested.connect(_on_assist_analysis_requested)

    try:
        _refresh_todo_panel()
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray_icon.show()
            _append_startup_log(startup_log_file, "startup: tray icon shown")
        else:
            _append_startup_log(startup_log_file, "startup: system tray unavailable")
            _show_control_panel("models")
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
        hotkey_mgr.stop()
        instance_guard.release()


if __name__ == "__main__":
    main()

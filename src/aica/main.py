"""AICA entrypoint: initialize app and connect the main workflow."""
from __future__ import annotations

import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import QRect, QTimer
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon

from aica.analysis_flow import AnalysisFlowCoordinator
from aica.analysis_metrics import AnalysisMetricsStore
from aica.capture_session import CaptureSession
from aica.capture_ui_flow import CaptureUiFlow
from aica.config import DEFAULT_CAPTURE_HOTKEY, ConfigManager
from aica.control_panel import ControlPanelWindow
from aica.feedback import FeedbackData
from aica.hotkey import HotkeyManager
from aica.llm.service import LLMService, ModelResolutionError
from aica.models import TicketSummaryFields
from aica.overlay import OverlayWindow
from aica.paths import error_log_file, icon_file
from aica.prompts import PromptManager
from aica.result_flow import ResultFlowCoordinator
from aica.single_instance import SingleInstanceGuard, show_already_running_message
from aica.todo_controller import TodoController
from aica.todo_detail_panel import TodoDetailPanel
from aica.todo_events import ScriptEventHandler, TodoBindingStore, TodoEventBus
from aica.todo_panel import TodoPanel
from aica.todo_store import TodoStore
from aica.toolbar import FloatingToolbar
from aica.worker import (
    AIWorker,
    FeedbackOptimizeWorker,
    MultiCaptureAIWorker,
    PlanExportWorker,
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


def _format_ts(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%m-%d %H:%M")
    except ValueError:
        return value


def main() -> None:
    instance_guard = SingleInstanceGuard()
    if not instance_guard.acquire():
        show_already_running_message()
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    startup_log_file = _setup_exception_handler()
    _append_startup_log(startup_log_file, "startup: main entered")

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    _append_startup_log(startup_log_file, "startup: QApplication ready")

    config_mgr = ConfigManager()
    initial_config = config_mgr.load()
    prompt_mgr = PromptManager()
    try:
        hotkey_mgr = HotkeyManager(initial_config.hotkeys.capture)
    except ValueError:
        initial_config.hotkeys.capture = DEFAULT_CAPTURE_HOTKEY
        config_mgr.save(initial_config)
        hotkey_mgr = HotkeyManager(initial_config.hotkeys.capture)
    control_panel = ControlPanelWindow(config_mgr)
    toolbar = FloatingToolbar()
    todo_store = TodoStore()
    binding_store = TodoBindingStore()
    todo_event_bus = TodoEventBus(
        handlers=[ScriptEventHandler(binding_store=binding_store)],
        binding_store=binding_store,
    )
    todo_controller = TodoController(todo_store, event_publisher=todo_event_bus)
    todo_panel = TodoPanel()
    todo_detail_panel = TodoDetailPanel()
    toolbar.set_scenario_selector_visible(True)

    capture_session = CaptureSession()
    analysis_metrics_store = AnalysisMetricsStore()
    feedback_workers: list[FeedbackOptimizeWorker] = []
    plan_export_workers: list[PlanExportWorker] = []
    capture_ui = CaptureUiFlow(
        toolbar=toolbar,
        todo_panel=todo_panel,
        todo_detail_panel=todo_detail_panel,
        capture_session=capture_session,
    )
    tray_icon_path = icon_file()
    tray_icon = QSystemTrayIcon(QIcon(str(tray_icon_path)), app)
    tray_icon.setToolTip("AICA")
    _append_startup_log(
        startup_log_file,
        f"startup: tray icon path={tray_icon_path} exists={tray_icon_path.exists()}",
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

    def _refresh_todo_panel() -> None:
        todo_panel.set_todos(
            todo_controller.get_active_todos(),
            todo_controller.selected_todo_id,
        )

    def _show_todo_detail(todo_id: str) -> None:
        todo = todo_controller.get_todo_detail(todo_id)
        if todo is None:
            return
        todo_detail_panel.show_todo(
            todo,
            todo_panel.frameGeometry(),
            sync_records=binding_store.list_record_payloads(todo_id),
        )

    def _build_selected_todo_context() -> str:
        todo = todo_controller.get_selected_todo()
        if todo is None:
            return ""
        timeline_lines = [
            f"- {_format_ts(event.timestamp)} {event.content}"
            for event in todo.timeline[-5:]
            if event.content.strip()
        ]
        evidence_lines = []
        return (
            "以下内容是当前已选中待办的历史上下文，仅供参考，不要直接复述为本次分析结果。\n"
            "请重点根据当前这张新截图提炼新增信息。\n"
            "current_summary 是创建时摘要，后续追加时不要改写旧摘要；"
            "请把本次新增进展写入 timeline_entry，把参数、日志、TraceId、URL 等排查依据写入 evidence_items。\n\n"
            f"待办标题: {todo.title}\n"
            f"群聊名称: {todo.summary_fields.group_name}\n"
            f"环境: {todo.summary_fields.environment}\n"
            f"产品线: {todo.summary_fields.product_line}\n"
            f"工单类型: {todo.summary_fields.ticket_type}\n"
            f"当前摘要: {todo.current_summary}\n"
            "最近时间线:\n"
            + ("\n".join(timeline_lines) if timeline_lines else "- 暂无")
            + "\n关键证据:\n"
            + ("\n".join(evidence_lines) if evidence_lines else "- 暂无")
        )

    def _build_selected_todo_context() -> str:
        todo = todo_controller.get_selected_todo()
        if todo is None:
            return ""
        timeline_lines = [
            f"- {_format_ts(event.timestamp)} {event.content}"
            for event in todo.timeline[-5:]
            if event.content.strip()
        ]
        return (
            "以下内容是当前已选中待办的历史上下文，仅供参考，不要直接复述为本次分析结果。\n"
            "请重点根据当前这张新截图提炼新增信息。\n"
            "current_summary 是创建时摘要，后续追加时不要改写旧摘要；"
            "请把本次新增进展写入 timeline_entry，如果有参数、日志、TraceId、URL 等细节，也直接写在 timeline_entry 里。\n\n"
            f"待办标题: {todo.title}\n"
            f"群聊名称: {todo.summary_fields.group_name}\n"
            f"环境: {todo.summary_fields.environment}\n"
            f"产品线: {todo.summary_fields.product_line}\n"
            f"工单类型: {todo.summary_fields.ticket_type}\n"
            f"当前摘要: {todo.current_summary}\n"
            "最近时间线:\n"
            + ("\n".join(timeline_lines) if timeline_lines else "- 暂无")
        )

    def _save_analysis_to_todo(snapshot) -> tuple[str, str]:
        save_result = todo_controller.save_analysis_result(
            snapshot,
            toolbar.get_current_scenario(),
        )
        _refresh_todo_panel()
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

    def _cleanup_feedback_worker(worker: FeedbackOptimizeWorker) -> None:
        if worker in feedback_workers:
            feedback_workers.remove(worker)
        worker.deleteLater()

    def _cleanup_plan_export_worker(worker: PlanExportWorker) -> None:
        if worker in plan_export_workers:
            plan_export_workers.remove(worker)
        worker.deleteLater()

    def _build_runtime_config(config):
        llm_service = LLMService(config)
        analysis_ref = llm_service.resolve_task_model("analysis").reference
        plan_export_ref = llm_service.resolve_task_model("plan_export").reference
        prompt_ref = llm_service.resolve_task_model("prompt_optimization").reference
        return SimpleNamespace(
            app_config=config,
            llm_service=llm_service,
            analysis_timeout_seconds=analysis_ref.timeout_seconds,
            plan_export_timeout_seconds=plan_export_ref.timeout_seconds,
            prompt_optimization_timeout_seconds=prompt_ref.timeout_seconds,
        )

    def _on_feedback_optimization_finished(summary: dict) -> None:
        nonlocal prompt_mgr

        sender = app.sender()
        if isinstance(sender, FeedbackOptimizeWorker):
            _cleanup_feedback_worker(sender)

        updated_parts = []
        if summary.get("immediate_prompt_updated"):
            updated_parts.append("Immediate prompt tuning applied from this feedback.")
        if summary.get("threshold_prompt_updated"):
            updated_parts.append("Threshold-based prompt optimization applied.")

        if updated_parts:
            prompt_mgr = PromptManager()
            QMessageBox.information(
                None,
                "Prompt Updated",
                f"Scenario: {summary.get('scenario', '')}\n\n" + "\n".join(updated_parts),
            )

    def _on_feedback_optimization_error(message: str) -> None:
        sender = app.sender()
        if isinstance(sender, FeedbackOptimizeWorker):
            _cleanup_feedback_worker(sender)
        print(f"Feedback background optimization failed: {message}")

    def _start_feedback_optimization(feedback: FeedbackData) -> None:
        try:
            runtime_config = _build_runtime_config(config_mgr.load())
        except ModelResolutionError:
            return

        worker = FeedbackOptimizeWorker(
            runtime_config.llm_service,
            runtime_config.prompt_optimization_timeout_seconds,
            feedback,
        )
        feedback_workers.append(worker)
        worker.finished.connect(_on_feedback_optimization_finished)
        worker.error.connect(_on_feedback_optimization_error)
        worker.start()

    def _on_plan_export_finished(export_path: str) -> None:
        sender = app.sender()
        if isinstance(sender, PlanExportWorker):
            _cleanup_plan_export_worker(sender)
        QMessageBox.information(None, "导出成功", f"方案已导出到:\n{export_path}")

    def _on_plan_export_error(message: str) -> None:
        sender = app.sender()
        if isinstance(sender, PlanExportWorker):
            _cleanup_plan_export_worker(sender)
        QMessageBox.warning(None, "导出失败", message)

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
        start_feedback_optimization=_start_feedback_optimization,
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

    def _handle_analysis_finished(result, feedback_image_base64: str, analysis_stats=None) -> None:
        result_flow.handle_ai_finished(
            result,
            feedback_image_base64=feedback_image_base64,
            analysis_stats=analysis_stats,
        )

    analysis_flow = AnalysisFlowCoordinator(
        capture_session=capture_session,
        toolbar=toolbar,
        prompt_manager=prompt_mgr,
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

    def _on_scenario_changed(scenario_name: str) -> None:
        _ = scenario_name

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
        summary_fields = TicketSummaryFields.from_dict(payload.get("summary_fields"))
        timeline_payload = payload.get("timeline", [])
        updated = todo_controller.update_todo(
            todo_id,
            title=str(payload.get("title", "")),
            current_summary=str(payload.get("current_summary", "")),
            summary_fields=summary_fields,
            timeline=timeline_payload,
        )
        if updated is None:
            return
        todo_detail_panel.show_todo(
            updated,
            todo_panel.frameGeometry(),
            sync_records=binding_store.list_record_payloads(todo_id),
        )
        _refresh_todo_panel()

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

    def _on_control_panel_saved(saved_config) -> None:
        try:
            hotkey_mgr.update_hotkey(saved_config.hotkeys.capture)
        except ValueError:
            hotkey_mgr.update_hotkey(DEFAULT_CAPTURE_HOTKEY)

    control_panel.config_saved.connect(_on_control_panel_saved)
    hotkey_mgr.hotkey_triggered.connect(_on_hotkey)
    toolbar.summarize_clicked.connect(_on_summarize)
    toolbar.continue_capture_clicked.connect(_on_continue_capture)
    toolbar.copy_clicked.connect(_on_copy_capture)
    toolbar.cancel_clicked.connect(_on_cancel)
    toolbar.scenario_changed.connect(_on_scenario_changed)
    toolbar.edit_mode_changed.connect(_on_edit_mode_changed)
    toolbar.undo_clicked.connect(_on_undo_annotation)
    toolbar.clear_annotations_clicked.connect(_on_clear_annotations)
    todo_panel.todo_selected.connect(_on_todo_selected)
    todo_panel.todo_completed.connect(_on_todo_completed)
    todo_panel.selection_cleared.connect(_on_todo_selection_cleared)
    todo_panel.detail_requested.connect(_on_todo_detail_requested)
    todo_detail_panel.save_requested.connect(_on_todo_detail_saved)
    todo_detail_panel.closed.connect(_on_todo_detail_closed)
    todo_detail_panel.complete_requested.connect(_on_todo_detail_completed)
    todo_detail_panel.delete_requested.connect(_on_todo_detail_deleted)
    todo_detail_panel.export_plan_requested.connect(_on_todo_export_plan_requested)
    todo_detail_panel.manual_sync_requested.connect(_on_todo_detail_manual_sync)

    try:
        _refresh_todo_panel()
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray_icon.show()
            _append_startup_log(startup_log_file, "startup: tray icon shown")
        else:
            _append_startup_log(startup_log_file, "startup: system tray unavailable")
            _show_control_panel("models")
        try:
            hotkey_mgr.start()
            _append_startup_log(startup_log_file, "startup: hotkey listener started")
        except Exception as exc:
            _append_startup_log(
                startup_log_file,
                f"startup: hotkey listener failed: {exc}\n{traceback.format_exc()}",
            )
            QMessageBox.warning(
                None,
                "???????",
                f"???????????????????\n???????????????????\n\n??: {startup_log_file}\n{exc}",
            )
        sys.exit(app.exec())
    finally:
        tray_icon.hide()
        control_panel.hide()
        hotkey_mgr.stop()
        instance_guard.release()


if __name__ == "__main__":
    main()

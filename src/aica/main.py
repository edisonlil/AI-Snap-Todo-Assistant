"""AICA entrypoint: initialize app and connect the main workflow."""
from __future__ import annotations

import ctypes
import os
import sys
import traceback
from datetime import datetime

from PyQt6.QtCore import QRect, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox

from aica.api_key_dialog import ApiKeyDialog
from aica.analysis_flow import AnalysisFlowCoordinator
from aica.capture_session import CaptureSession
from aica.capture_ui_flow import CaptureUiFlow
from aica.config import ConfigManager
from aica.feedback import FeedbackData
from aica.hotkey import HotkeyManager
from aica.models import TicketSummaryFields
from aica.overlay import OverlayWindow
from aica.prompts import PromptManager
from aica.result_flow import ResultFlowCoordinator
from aica.single_instance import SingleInstanceGuard, show_already_running_message
from aica.todo_controller import TodoController
from aica.todo_detail_panel import TodoDetailPanel
from aica.todo_panel import TodoPanel
from aica.todo_store import TodoStore
from aica.toolbar import FloatingToolbar
from aica.worker import AIWorker, FeedbackOptimizeWorker, MultiCaptureAIWorker


def _setup_exception_handler() -> None:
    """Install a global exception hook and persist uncaught errors to disk."""
    log_dir = os.path.join(os.path.expanduser("~"), ".aica")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "error.log")

    def exception_hook(exc_type, exc_value, exc_tb):
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(f"\n{'=' * 60}\n")
            handle.write(f"时间: {datetime.now().isoformat()}\n")
            handle.write("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))

        QMessageBox.critical(
            None,
            "程序错误",
            f"发生未处理异常，已记录到日志:\n{log_file}\n\n{exc_type.__name__}: {exc_value}",
        )

    sys.excepthook = exception_hook


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

    _setup_exception_handler()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config_mgr = ConfigManager()
    prompt_mgr = PromptManager()
    hotkey_mgr = HotkeyManager()
    toolbar = FloatingToolbar()
    todo_store = TodoStore()
    todo_controller = TodoController(todo_store)
    todo_panel = TodoPanel()
    todo_detail_panel = TodoDetailPanel()

    toolbar.set_scenarios(prompt_mgr.list_scenarios())
    toolbar.set_current_scenario(prompt_mgr.get_current_scenario_name())
    toolbar.set_scenario_selector_visible(False)

    capture_session = CaptureSession()
    feedback_workers: list[FeedbackOptimizeWorker] = []
    capture_ui = CaptureUiFlow(
        toolbar=toolbar,
        todo_panel=todo_panel,
        todo_detail_panel=todo_detail_panel,
        capture_session=capture_session,
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
        todo_detail_panel.show_todo(todo, todo_panel.frameGeometry())

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
            "当前正在追加到一个已有待办，请结合已有上下文生成本次跟进记录。\n"
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

    def _restore_toolbar_for_current_capture() -> None:
        capture_ui.restore_toolbar_for_current_capture()

    def _queue_current_capture() -> bool:
        return capture_ui.queue_current_capture()

    def _cleanup_feedback_worker(worker: FeedbackOptimizeWorker) -> None:
        if worker in feedback_workers:
            feedback_workers.remove(worker)
        worker.deleteLater()

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
            toolbar.set_scenarios(prompt_mgr.list_scenarios())
            toolbar.set_current_scenario(prompt_mgr.get_current_scenario_name())
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
        config = config_mgr.load()
        if not config.api_key:
            return

        worker = FeedbackOptimizeWorker(
            config.api_key,
            config.model,
            config.api_base_url,
            config.timeout_seconds,
            feedback,
        )
        feedback_workers.append(worker)
        worker.finished.connect(_on_feedback_optimization_finished)
        worker.error.connect(_on_feedback_optimization_error)
        worker.start()

    result_flow = ResultFlowCoordinator(
        get_scenario=toolbar.get_current_scenario,
        get_model=lambda: config_mgr.load().model,
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
        if config.api_key:
            return config

        dialog = ApiKeyDialog(config_mgr)
        if dialog.exec():
            saved_config = dialog.get_saved_config()
            if saved_config is not None and saved_config.api_key:
                return saved_config
        return None

    def _handle_analysis_finished(result, feedback_image_base64: str) -> None:
        result_flow.handle_ai_finished(
            result,
            feedback_image_base64=feedback_image_base64,
        )

    analysis_flow = AnalysisFlowCoordinator(
        capture_session=capture_session,
        toolbar=toolbar,
        prompt_manager=prompt_mgr,
        get_scenario=toolbar.get_current_scenario,
        get_analysis_context=_build_selected_todo_context,
        ensure_api_key_configured=_ensure_api_key_configured,
        hide_overlays=_hide_overlays,
        restore_toolbar_for_current_capture=_restore_toolbar_for_current_capture,
        on_finished=_handle_analysis_finished,
        single_worker_factory=AIWorker,
        multi_worker_factory=MultiCaptureAIWorker,
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
        _hide_overlays(reset=True)
        toolbar.hide()
        QTimer.singleShot(50, _show_overlays)

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
        if prompt_mgr.set_current_scenario(scenario_name):
            toolbar.set_current_scenario(scenario_name)

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
        _refresh_todo_panel()
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

    try:
        _refresh_todo_panel()
        hotkey_mgr.start()
        sys.exit(app.exec())
    finally:
        hotkey_mgr.stop()
        instance_guard.release()


if __name__ == "__main__":
    main()

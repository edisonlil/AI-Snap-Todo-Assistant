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
from aica.config import ConfigManager
from aica.feedback import FeedbackData
from aica.feedback_panel import FeedbackPanel
from aica.hotkey import HotkeyManager
from aica.overlay import OverlayWindow
from aica.prompts import PromptManager
from aica.result_dialog import ResultDialog
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
    overlays: list[OverlayWindow] = []
    toolbar = FloatingToolbar()
    todo_store = TodoStore()
    todo_controller = TodoController(todo_store)
    todo_panel = TodoPanel()
    todo_detail_panel = TodoDetailPanel()

    toolbar.set_scenarios(prompt_mgr.list_scenarios())
    toolbar.set_current_scenario(prompt_mgr.get_current_scenario_name())

    current_selection: QRect | None = None
    current_capture: QPixmap | None = None
    active_overlay: OverlayWindow | None = None
    capture_session: list[QPixmap] = []
    current_worker = None
    feedback_workers: list[FeedbackOptimizeWorker] = []
    capture_locked = False

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

    def _save_analysis_to_todo(result_text: str) -> tuple[str, str]:
        save_result = todo_controller.save_analysis_result(
            result_text,
            toolbar.get_current_scenario(),
        )
        _refresh_todo_panel()
        return save_result.action, save_result.todo.title

    def _rebuild_overlays() -> None:
        nonlocal overlays
        for current_overlay in overlays:
            current_overlay.hide()
            current_overlay.deleteLater()

        overlays = [OverlayWindow(screen) for screen in app.screens()]
        for current_overlay in overlays:
            current_overlay.selection_complete.connect(_on_selection_complete)
            current_overlay.selection_changed.connect(_on_selection_changed)
            current_overlay.cancelled.connect(_on_cancel)

    def _show_overlays() -> None:
        nonlocal active_overlay
        active_overlay = None
        todo_panel.hide()
        todo_detail_panel.hide()
        _rebuild_overlays()
        toolbar.attach_to_overlay(None)
        toolbar.set_edit_mode("move")
        for current_overlay in overlays:
            current_overlay.show_overlay()

    def _hide_overlays(*, reset: bool = True, preserve_active: bool = False) -> None:
        for current_overlay in overlays:
            if preserve_active and current_overlay is active_overlay:
                current_overlay.suspend_overlay()
            elif reset:
                current_overlay.dismiss_overlay()
            else:
                current_overlay.suspend_overlay()

    def _sync_capture_from_active_overlay() -> bool:
        nonlocal current_selection, current_capture
        if active_overlay is None or not active_overlay.has_selection():
            return current_capture is not None and current_selection is not None

        selection = active_overlay.current_global_selection()
        capture = active_overlay.export_selection_pixmap()
        if selection is None or capture.isNull():
            return False

        current_selection = selection
        current_capture = capture
        return True

    def _clear_capture_state() -> None:
        nonlocal current_selection, current_capture, active_overlay, capture_session
        _hide_overlays(reset=True)
        current_selection = None
        current_capture = None
        active_overlay = None
        capture_session = []
        toolbar.attach_to_overlay(None)
        toolbar.set_single_capture_mode()
        toolbar.hide()
        _refresh_todo_panel()

    def _restore_toolbar_for_current_capture() -> None:
        if not _sync_capture_from_active_overlay():
            return

        if active_overlay is not None:
            active_overlay.resume_overlay()

        if capture_session:
            toolbar.set_multi_capture_mode(_session_capture_count())
        else:
            toolbar.set_single_capture_mode()
        if active_overlay is not None:
            active_overlay.set_edit_mode("move")
        toolbar.show_at(current_selection)

    def _session_capture_count() -> int:
        return len(capture_session) + (1 if current_capture is not None else 0)

    def _queue_current_capture() -> bool:
        nonlocal current_selection, current_capture, active_overlay
        if not _sync_capture_from_active_overlay():
            return False

        capture_session.append(current_capture)
        current_selection = None
        current_capture = None

        if active_overlay is not None:
            active_overlay.dismiss_overlay()
        active_overlay = None
        return True

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

    def _on_hotkey() -> None:
        nonlocal capture_locked, active_overlay
        if capture_locked or toolbar.is_loading() or current_capture is not None:
            return

        if any(current_overlay.isVisible() for current_overlay in overlays):
            _hide_overlays(reset=True)
            active_overlay = None
            toolbar.hide()
            _refresh_todo_panel()
        else:
            toolbar.hide()
            QTimer.singleShot(50, _show_overlays)

    def _on_selection_complete(rect: QRect, cropped: QPixmap) -> None:
        nonlocal current_selection, current_capture, active_overlay
        selected_overlay = app.sender()
        if not isinstance(selected_overlay, OverlayWindow):
            return

        for current_overlay in overlays:
            if current_overlay is selected_overlay:
                active_overlay = current_overlay
                current_overlay.lock_selection()
                current_overlay.raise_()
            else:
                current_overlay.dismiss_overlay()

        toolbar.attach_to_overlay(selected_overlay)
        current_selection = rect
        current_capture = cropped
        toolbar.set_edit_mode("move")
        if capture_session:
            toolbar.set_multi_capture_mode(_session_capture_count())
        else:
            toolbar.set_single_capture_mode()
        toolbar.show_at(rect)

    def _on_selection_changed(rect: QRect) -> None:
        nonlocal current_selection
        current_selection = rect
        if not toolbar.is_loading():
            toolbar.show_at(rect)

    def _create_analysis_worker(images: list[QPixmap], config):
        if len(images) == 1:
            return AIWorker(
                images[0],
                config.api_key,
                config.model,
                config.api_base_url,
                config.timeout_seconds,
                prompt_manager=prompt_mgr,
                scenario=toolbar.get_current_scenario(),
            )
        return MultiCaptureAIWorker(
            images,
            config.api_key,
            config.model,
            config.api_base_url,
            config.timeout_seconds,
            prompt_manager=prompt_mgr,
            scenario=toolbar.get_current_scenario(),
        )

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

    def _on_summarize() -> None:
        nonlocal current_worker, capture_locked
        print(f"[DEBUG] _on_summarize called, current_selection={current_selection}, session_count={len(capture_session)}")
        if capture_locked or not _sync_capture_from_active_overlay():
            return

        images_to_analyze = [*capture_session, current_capture]
        if not images_to_analyze:
            return

        capture_locked = True
        _hide_overlays(reset=False, preserve_active=True)
        toolbar.hide()

        config = _ensure_api_key_configured()
        if config is None:
            capture_locked = False
            _restore_toolbar_for_current_capture()
            return

        toolbar.set_loading(True)
        current_worker = _create_analysis_worker(images_to_analyze, config)
        current_worker.finished.connect(_on_ai_finished)
        current_worker.error.connect(_on_ai_error)
        current_worker.parse_error.connect(_on_ai_parse_error)
        current_worker.start()

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

        QApplication.clipboard().setPixmap(current_capture)
        _clear_capture_state()

    def _on_edit_mode_changed(mode: str) -> None:
        if active_overlay is not None:
            active_overlay.set_edit_mode(mode)

    def _on_undo_annotation() -> None:
        if active_overlay is None:
            return
        active_overlay.undo_last_annotation()
        _sync_capture_from_active_overlay()

    def _on_clear_annotations() -> None:
        if active_overlay is None:
            return
        active_overlay.clear_annotations()
        _sync_capture_from_active_overlay()

    def _on_ai_finished(result) -> None:
        import pyperclip

        nonlocal capture_locked
        toolbar.set_loading(False)

        def on_save_result(result_str):
            pyperclip.copy(result_str)
            action, todo_title = _save_analysis_to_todo(result_str)
            if action == "append":
                message = f"结果已复制到剪贴板，并已追加到待办：\n{todo_title}"
            else:
                message = f"结果已复制到剪贴板，并已创建待办：\n{todo_title}"
            QMessageBox.information(None, "完成", message)
            _clear_capture_state()

        def on_feedback(result_str, feedback_data):
            result_dialog.close()

            feedback_data.original_result = str(result)
            feedback_data.edited_result = result_str
            feedback_data.user_edited = str(result) != result_str
            feedback_data.image_base64 = getattr(current_worker, "_feedback_image_base64", "")
            feedback_data.correction = {"raw": result_str}

            def on_save_feedback(fb_data, optimize_now):
                if optimize_now:
                    QMessageBox.information(
                        None,
                        "Feedback Saved",
                        "Feedback saved. Prompt optimization is running in the background.",
                    )
                    _start_feedback_optimization(fb_data)
                else:
                    QMessageBox.information(None, "Feedback Saved", "Feedback saved.")
                _clear_capture_state()

            config = config_mgr.load()
            feedback_panel = FeedbackPanel(
                result_str,
                feedback_data,
                toolbar.get_current_scenario(),
                config.model,
                save_callback=on_save_feedback,
                parent=None,
            )
            feedback_panel.exec()

        config = config_mgr.load()
        result_dialog = ResultDialog(
            result,
            toolbar.get_current_scenario(),
            config.model,
            feedback_callback=on_feedback,
            save_callback=on_save_result,
            parent=None,
        )
        result_dialog.exec()
        _clear_capture_state()
        capture_locked = False

    def _on_ai_error(message: str) -> None:
        nonlocal capture_locked
        toolbar.set_loading(False)
        capture_locked = False
        QMessageBox.critical(None, "错误", message)
        _restore_toolbar_for_current_capture()

    def _on_ai_parse_error(raw_text: str) -> None:
        import pyperclip

        nonlocal capture_locked
        pyperclip.copy(raw_text)
        toolbar.set_loading(False)
        capture_locked = False
        QMessageBox.warning(None, "格式异常", "AI 返回格式异常，已将原始内容写入剪贴板")
        _restore_toolbar_for_current_capture()

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

    def _on_todo_detail_saved(todo_id: str, title: str, summary: str) -> None:
        updated = todo_controller.update_todo(todo_id, title=title, summary=summary)
        if updated is None:
            return
        _refresh_todo_panel()
        _show_todo_detail(todo_id)

    def _on_todo_detail_closed() -> None:
        todo_controller.close_detail()
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

    try:
        _refresh_todo_panel()
        hotkey_mgr.start()
        sys.exit(app.exec())
    finally:
        hotkey_mgr.stop()
        instance_guard.release()


if __name__ == "__main__":
    main()

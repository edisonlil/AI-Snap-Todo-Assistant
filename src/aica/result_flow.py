"""Coordinates result review, save, and feedback follow-up."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from aica.feedback import FeedbackData


@dataclass(frozen=True)
class SavedTodoResult:
    action: str
    todo_title: str


class ResultFlowCoordinator:
    """Owns the post-analysis dialog flow and its side effects."""

    def __init__(
        self,
        *,
        get_scenario: Callable[[], str],
        get_model: Callable[[], str],
        save_result_to_todo: Callable[[str], tuple[str, str]],
        clear_capture_state: Callable[[], None],
        start_feedback_optimization: Callable[[FeedbackData], None],
    ):
        self._get_scenario = get_scenario
        self._get_model = get_model
        self._save_result_to_todo = save_result_to_todo
        self._clear_capture_state = clear_capture_state
        self._start_feedback_optimization = start_feedback_optimization

    @staticmethod
    def build_saved_todo_message(saved: SavedTodoResult) -> str:
        if saved.action == "append":
            return f"结果已复制到剪贴板，并已追加到待办：\n{saved.todo_title}"
        return f"结果已复制到剪贴板，并已创建待办：\n{saved.todo_title}"

    @staticmethod
    def populate_feedback_data(
        *,
        result,
        edited_result: str,
        feedback_data: FeedbackData,
        feedback_image_base64: str,
    ) -> FeedbackData:
        feedback_data.original_result = str(result)
        feedback_data.edited_result = edited_result
        feedback_data.user_edited = str(result) != edited_result
        feedback_data.image_base64 = feedback_image_base64
        feedback_data.correction = {"raw": edited_result}
        return feedback_data

    def handle_ai_finished(self, result, *, feedback_image_base64: str = "") -> None:
        import pyperclip
        from PyQt6.QtWidgets import QMessageBox

        from aica.feedback_panel import FeedbackPanel
        from aica.result_dialog import ResultDialog

        scenario = self._get_scenario()
        model = self._get_model()
        result_dialog: ResultDialog | None = None

        def on_save_result(result_str: str) -> None:
            pyperclip.copy(result_str)
            action, todo_title = self._save_result_to_todo(result_str)
            QMessageBox.information(
                None,
                "完成",
                self.build_saved_todo_message(SavedTodoResult(action=action, todo_title=todo_title)),
            )
            self._clear_capture_state()

        def on_feedback(result_str: str, feedback_data: FeedbackData) -> None:
            nonlocal result_dialog
            if result_dialog is not None:
                result_dialog.close()

            populated = self.populate_feedback_data(
                result=result,
                edited_result=result_str,
                feedback_data=feedback_data,
                feedback_image_base64=feedback_image_base64,
            )

            def on_save_feedback(saved_feedback: FeedbackData, optimize_now: bool) -> None:
                if optimize_now:
                    QMessageBox.information(
                        None,
                        "Feedback Saved",
                        "Feedback saved. Prompt optimization is running in the background.",
                    )
                    self._start_feedback_optimization(saved_feedback)
                else:
                    QMessageBox.information(None, "Feedback Saved", "Feedback saved.")
                self._clear_capture_state()

            feedback_panel = FeedbackPanel(
                result_str,
                populated,
                scenario,
                model,
                save_callback=on_save_feedback,
                parent=None,
            )
            feedback_panel.exec()

        result_dialog = ResultDialog(
            result,
            scenario,
            model,
            feedback_callback=on_feedback,
            save_callback=on_save_result,
            parent=None,
        )
        result_dialog.exec()
        self._clear_capture_state()

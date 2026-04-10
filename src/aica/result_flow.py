"""Coordinates result review, save, and feedback follow-up."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from aica.analysis_metrics import AnalysisRunStats
from aica.feedback import FeedbackData
from aica.models import TicketSnapshot


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
        save_result_to_todo: Callable[[TicketSnapshot], tuple[str, str]],
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
            return f"\u7ed3\u679c\u5df2\u590d\u5236\u5230\u526a\u8d34\u677f\uff0c\u5e76\u5df2\u8ffd\u52a0\u5230\u5f85\u529e\uff1a\n{saved.todo_title}"
        return f"\u7ed3\u679c\u5df2\u590d\u5236\u5230\u526a\u8d34\u677f\uff0c\u5e76\u5df2\u521b\u5efa\u5f85\u529e\uff1a\n{saved.todo_title}"

    @staticmethod
    def populate_feedback_data(
        *,
        result: TicketSnapshot,
        edited_result: TicketSnapshot,
        feedback_data: FeedbackData,
        feedback_image_base64: str,
    ) -> FeedbackData:
        feedback_data.original_result = str(result)
        feedback_data.edited_result = str(edited_result)
        feedback_data.user_edited = result.to_dict() != edited_result.to_dict()
        feedback_data.image_base64 = feedback_image_base64
        feedback_data.correction = edited_result.to_dict()
        return feedback_data

    def handle_ai_finished(
        self,
        result: TicketSnapshot,
        *,
        feedback_image_base64: str = "",
        analysis_stats: AnalysisRunStats | None = None,
    ) -> None:
        import pyperclip
        from PyQt6.QtWidgets import QMessageBox

        from aica.feedback_panel import FeedbackPanel
        from aica.result_dialog import ResultDialog

        scenario = self._get_scenario()
        model = analysis_stats.display_name if analysis_stats is not None else self._get_model()
        result_dialog: ResultDialog | None = None

        def on_save_result(snapshot: TicketSnapshot) -> None:
            pyperclip.copy(str(snapshot))
            self._save_result_to_todo(snapshot)
            self._clear_capture_state()

        def on_feedback(snapshot: TicketSnapshot, feedback_data: FeedbackData) -> None:
            nonlocal result_dialog
            if result_dialog is not None:
                result_dialog.close()

            populated = self.populate_feedback_data(
                result=result,
                edited_result=snapshot,
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
                str(snapshot),
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
            analysis_stats=analysis_stats,
            feedback_callback=on_feedback,
            save_callback=on_save_result,
            parent=None,
        )
        result_dialog.exec()
        self._clear_capture_state()

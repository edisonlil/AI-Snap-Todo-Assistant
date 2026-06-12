"""Coordinates result review, save, and feedback follow-up."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from aica.analysis.metrics import AnalysisRunStats
from aica.feedback import FeedbackData
from aica.models import TicketSnapshot
from aica.theme_controller import ThemeController


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
        theme_controller: ThemeController | None = None,
    ):
        self._get_scenario = get_scenario
        self._get_model = get_model
        self._save_result_to_todo = save_result_to_todo
        self._clear_capture_state = clear_capture_state
        self._theme_controller = theme_controller or ThemeController()

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
        prompt_trace_id: str = "",
        prompt_version: str = "built-in",
    ) -> FeedbackData:
        feedback_data.original_result = str(result)
        feedback_data.edited_result = str(edited_result)
        feedback_data.user_edited = result.to_dict() != edited_result.to_dict()
        feedback_data.image_base64 = feedback_image_base64
        feedback_data.correction = edited_result.to_dict()
        feedback_data.prompt_trace_id = str(prompt_trace_id or "").strip()
        feedback_data.prompt_version = str(prompt_version or "built-in")
        return feedback_data

    def handle_ai_finished(
        self,
        result: TicketSnapshot,
        *,
        feedback_image_base64: str = "",
        analysis_stats: AnalysisRunStats | None = None,
        prompt_trace_id: str = "",
        prompt_version: str = "built-in",
    ) -> None:
        import pyperclip

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
                prompt_trace_id=prompt_trace_id,
                prompt_version=prompt_version,
            )

            def on_save_feedback(saved_feedback: FeedbackData) -> None:
                self._clear_capture_state()

            feedback_panel = FeedbackPanel(
                str(snapshot),
                populated,
                scenario,
                model,
                save_callback=on_save_feedback,
                parent=None,
                theme_controller=self._theme_controller,
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
            theme_controller=self._theme_controller,
        )
        result_dialog.exec()
        self._clear_capture_state()

"""Coordinates result review and save follow-up."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from aica.analysis.metrics import AnalysisRunStats
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

        from aica.result_dialog import ResultDialog

        scenario = self._get_scenario()
        model = analysis_stats.display_name if analysis_stats is not None else self._get_model()

        def on_save_result(snapshot: TicketSnapshot) -> None:
            pyperclip.copy(str(snapshot))
            self._save_result_to_todo(snapshot)
            self._clear_capture_state()

        result_dialog = ResultDialog(
            result,
            scenario,
            model,
            analysis_stats=analysis_stats,
            save_callback=on_save_result,
            parent=None,
            theme_controller=self._theme_controller,
        )
        result_dialog.exec()
        self._clear_capture_state()

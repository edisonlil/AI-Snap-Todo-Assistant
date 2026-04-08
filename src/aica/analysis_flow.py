"""Coordinates analysis worker lifecycle and recovery flows."""
from __future__ import annotations

from typing import Any, Callable


class AnalysisFlowCoordinator:
    """Owns analysis start, worker selection, and error recovery."""

    def __init__(
        self,
        *,
        capture_session,
        toolbar,
        prompt_manager,
        get_scenario: Callable[[], str],
        get_analysis_intent: Callable[[int], Any | None] | None,
        get_analysis_context: Callable[[], str] | None,
        ensure_api_key_configured: Callable[[], Any | None],
        hide_overlays: Callable[..., None],
        restore_toolbar_for_current_capture: Callable[[], None],
        on_finished: Callable[[object, str], None],
        single_worker_factory: Callable[..., Any] | None = None,
        multi_worker_factory: Callable[..., Any] | None = None,
        show_critical: Callable[[str, str], None] | None = None,
        show_warning: Callable[[str, str], None] | None = None,
        copy_to_clipboard: Callable[[str], None] | None = None,
    ):
        self._capture_session = capture_session
        self._toolbar = toolbar
        self._prompt_manager = prompt_manager
        self._get_scenario = get_scenario
        self._get_analysis_intent = get_analysis_intent
        self._get_analysis_context = get_analysis_context
        self._ensure_api_key_configured = ensure_api_key_configured
        self._hide_overlays = hide_overlays
        self._restore_toolbar_for_current_capture = restore_toolbar_for_current_capture
        self._on_finished = on_finished
        self._single_worker_factory = single_worker_factory
        self._multi_worker_factory = multi_worker_factory
        self._show_critical = show_critical
        self._show_warning = show_warning
        self._copy_to_clipboard = copy_to_clipboard
        self._current_worker: Any | None = None
        self._capture_locked = False

    @property
    def capture_locked(self) -> bool:
        return self._capture_locked

    @property
    def current_worker(self) -> Any | None:
        return self._current_worker

    def build_worker(self, images: list[Any], config: Any) -> Any:
        if self._single_worker_factory is None or self._multi_worker_factory is None:
            from aica.worker import AIWorker, MultiCaptureAIWorker

            self._single_worker_factory = AIWorker
            self._multi_worker_factory = MultiCaptureAIWorker

        scenario = self._get_scenario()
        analysis_intent = self._get_analysis_intent(len(images)) if self._get_analysis_intent is not None else None
        context_text = self._get_analysis_context() if self._get_analysis_context is not None else ""
        worker_kwargs = dict(
            api_key=config.api_key,
            model=config.model,
            api_url=config.api_base_url,
            timeout=config.timeout_seconds,
            prompt_manager=self._prompt_manager,
            scenario=scenario,
            analysis_intent=analysis_intent,
            context_text=context_text,
        )
        if len(images) == 1:
            return self._single_worker_factory(images[0], **worker_kwargs)
        return self._multi_worker_factory(images, **worker_kwargs)

    def start_analysis(self) -> bool:
        if self._capture_locked or not self._capture_session.sync_from_active_overlay():
            return False

        images_to_analyze = self._capture_session.images_for_analysis()
        if not images_to_analyze:
            return False

        analysis_intent = self._get_analysis_intent(len(images_to_analyze)) if self._get_analysis_intent is not None else None
        if analysis_intent is None:
            if self._show_warning is not None:
                self._show_warning("缺少场景", "请先选择本次截图的分析场景")
            return False

        self._capture_locked = True
        self._hide_overlays(reset=False, preserve_active=True)
        self._toolbar.hide()

        config = self._ensure_api_key_configured()
        if config is None:
            self._capture_locked = False
            self._restore_toolbar_for_current_capture()
            return False

        self._toolbar.set_loading(True)
        self._current_worker = self.build_worker(images_to_analyze, config)
        self._current_worker.finished.connect(self._handle_finished)
        self._current_worker.error.connect(self._handle_error)
        self._current_worker.parse_error.connect(self._handle_parse_error)
        self._current_worker.start()
        return True

    def _handle_finished(self, result) -> None:
        self._toolbar.set_loading(False)
        feedback_image_base64 = getattr(self._current_worker, "_feedback_image_base64", "")
        self._capture_locked = False
        self._on_finished(result, feedback_image_base64)

    def _handle_error(self, message: str) -> None:
        self._toolbar.set_loading(False)
        self._capture_locked = False
        if self._show_critical is None:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.critical(None, "错误", message)
        else:
            self._show_critical("错误", message)
        self._restore_toolbar_for_current_capture()

    def _handle_parse_error(self, raw_text: str) -> None:
        if self._copy_to_clipboard is None:
            import pyperclip

            pyperclip.copy(raw_text)
        else:
            self._copy_to_clipboard(raw_text)

        self._toolbar.set_loading(False)
        self._capture_locked = False
        warning_message = "AI 返回格式异常，已将原始内容写入剪贴板"
        if self._show_warning is None:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(None, "格式异常", warning_message)
        else:
            self._show_warning("格式异常", warning_message)
        self._restore_toolbar_for_current_capture()

"""Coordinates overlay windows and toolbar state for capture UI."""
from __future__ import annotations

from typing import Any, Callable


class CaptureUiFlow:
    """Owns overlay lifecycle and toolbar synchronization for capture mode."""

    def __init__(self, *, toolbar, todo_panel, todo_detail_panel, capture_session):
        self._toolbar = toolbar
        self._todo_panel = todo_panel
        self._todo_detail_panel = todo_detail_panel
        self._capture_session = capture_session
        self._overlays: list[Any] = []

    @property
    def overlays(self) -> list[Any]:
        return self._overlays

    def rebuild_overlays(
        self,
        screens: list[Any],
        *,
        overlay_factory: Callable[[Any], Any],
        on_selection_complete: Callable,
        on_selection_changed: Callable,
        on_cancel: Callable,
    ) -> None:
        for overlay in self._overlays:
            overlay.hide()
            overlay.deleteLater()

        self._overlays = [overlay_factory(screen) for screen in screens]
        for overlay in self._overlays:
            overlay.selection_complete.connect(on_selection_complete)
            overlay.selection_changed.connect(on_selection_changed)
            overlay.cancelled.connect(on_cancel)

    def show_overlays(self) -> None:
        self._capture_session.active_overlay = None
        self._todo_panel.hide()
        self._todo_detail_panel.hide()
        self._toolbar.attach_to_overlay(None)
        self._toolbar.set_edit_mode("move")
        for overlay in self._overlays:
            overlay.show_overlay()

    def hide_overlays(self, *, reset: bool = True, preserve_active: bool = False) -> None:
        for overlay in self._overlays:
            if preserve_active and overlay is self._capture_session.active_overlay:
                overlay.suspend_overlay()
            elif reset:
                overlay.dismiss_overlay()
            else:
                overlay.suspend_overlay()

    def clear_capture_state(self, refresh_todo_panel: Callable[[], None]) -> None:
        self.hide_overlays(reset=True)
        self._capture_session.clear()
        self._toolbar.attach_to_overlay(None)
        self._toolbar.set_single_capture_mode()
        self._toolbar.hide()
        refresh_todo_panel()

    def restore_toolbar_for_current_capture(self) -> None:
        if not self._capture_session.sync_from_active_overlay():
            return

        active_overlay = self._capture_session.active_overlay
        if active_overlay is not None:
            active_overlay.resume_overlay()

        if self._capture_session.queued_captures:
            self._toolbar.set_multi_capture_mode(self._capture_session.session_capture_count())
        else:
            self._toolbar.set_single_capture_mode()

        if active_overlay is not None:
            active_overlay.set_edit_mode("move")
        self._toolbar.show_at(self._capture_session.current_selection)

    def queue_current_capture(self) -> bool:
        previous_overlay = self._capture_session.active_overlay
        queued = self._capture_session.queue_current_capture()
        if queued and previous_overlay is not None:
            previous_overlay.dismiss_overlay()
        return queued

    def handle_selection_complete(self, selected_overlay: Any, rect: Any, cropped: Any) -> None:
        for overlay in self._overlays:
            if overlay is selected_overlay:
                self._capture_session.active_overlay = overlay
                overlay.lock_selection()
                overlay.raise_()
            else:
                overlay.dismiss_overlay()

        self._toolbar.attach_to_overlay(selected_overlay)
        self._capture_session.set_active_capture(rect, cropped, selected_overlay)
        self._toolbar.set_edit_mode("move")
        if self._capture_session.queued_captures:
            self._toolbar.set_multi_capture_mode(self._capture_session.session_capture_count())
        else:
            self._toolbar.set_single_capture_mode()
        self._toolbar.show_at(rect)

    def handle_selection_changed(self, rect: Any) -> None:
        self._capture_session.current_selection = rect
        if not self._toolbar.is_loading():
            self._toolbar.show_at(rect)

    def any_overlay_visible(self) -> bool:
        return any(overlay.isVisible() for overlay in self._overlays)

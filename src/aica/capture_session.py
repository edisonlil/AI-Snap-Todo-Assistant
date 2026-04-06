"""State container for the active capture workflow."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CaptureSession:
    """Tracks the active overlay selection and queued captures."""

    current_selection: Any | None = None
    current_capture: Any | None = None
    active_overlay: Any | None = None
    queued_captures: list[Any] = field(default_factory=list)

    def has_pending_capture(self) -> bool:
        return self.current_selection is not None and self.current_capture is not None

    def sync_from_active_overlay(self) -> bool:
        if self.active_overlay is None or not self.active_overlay.has_selection():
            return self.has_pending_capture()

        selection = self.active_overlay.current_global_selection()
        capture = self.active_overlay.export_selection_pixmap()
        if selection is None or capture.isNull():
            return False

        self.current_selection = selection
        self.current_capture = capture
        return True

    def set_active_capture(self, selection: Any, capture: Any, overlay: Any) -> None:
        self.current_selection = selection
        self.current_capture = capture
        self.active_overlay = overlay

    def clear(self) -> None:
        self.current_selection = None
        self.current_capture = None
        self.active_overlay = None
        self.queued_captures = []

    def session_capture_count(self) -> int:
        return len(self.queued_captures) + (1 if self.current_capture is not None else 0)

    def queue_current_capture(self) -> bool:
        if not self.sync_from_active_overlay() or self.current_capture is None:
            return False

        self.queued_captures.append(self.current_capture)
        self.current_selection = None
        self.current_capture = None
        self.active_overlay = None
        return True

    def images_for_analysis(self) -> list[Any]:
        if self.current_capture is None:
            return [*self.queued_captures]
        return [*self.queued_captures, self.current_capture]

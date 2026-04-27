from __future__ import annotations

from pathlib import Path
import sys

from PyQt6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.loading_dialog import LoadingDialog  # noqa: E402


def test_hide_loading_clears_top_reserved_space_without_reopening() -> None:
    app = QApplication.instance() or QApplication([])
    dialog = LoadingDialog()
    reserved_space_calls: list[int] = []

    class _AnchorWidget:
        def set_top_reserved_space(self, height: int) -> None:
            reserved_space_calls.append(height)
            if height == 0 and dialog.isVisible():
                dialog.show_loading(self)

    anchor = _AnchorWidget()

    dialog.show_loading(anchor)
    app.processEvents()

    dialog.hide_loading()
    app.processEvents()

    assert reserved_space_calls == [70, 0]
    assert not dialog.isVisible()
    assert dialog._anchor_widget is None

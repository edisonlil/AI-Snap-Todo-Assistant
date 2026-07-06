from __future__ import annotations

from pathlib import Path


def test_export_selection_pixmap_flattens_transparent_capture_before_annotations() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "aica" / "overlay.py").read_text(encoding="utf-8")
    body = source.split("def export_selection_pixmap", 1)[1].split("def _reset_editor_state", 1)[0]

    assert "annotated = self._flatten_transparent_pixmap(cropped)" in body
    assert body.index("annotated = self._flatten_transparent_pixmap(cropped)") < body.index("painter = QPainter(annotated)")


def test_overlay_flatten_helper_paints_transparent_pixels_onto_white_background() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "aica" / "overlay.py").read_text(encoding="utf-8")
    helper = source.split("def _flatten_transparent_pixmap", 1)[1].split("def _reset_editor_state", 1)[0]

    assert "if not image.hasAlphaChannel()" in helper
    assert "flattened.fill(QColor(255, 255, 255))" in helper
    assert "painter.drawImage(0, 0, image)" in helper

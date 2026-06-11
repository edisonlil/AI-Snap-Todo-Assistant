from __future__ import annotations

from pathlib import Path


def test_page_runtime_exposes_standard_slots() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "PageRuntime.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "property alias filterContent: filterSlot.data" in qml_text
    assert "property alias actionContent: actionSlot.data" in qml_text
    assert "property alias listContent: listSlot.data" in qml_text
    assert "property alias footerContent: footerSlot.data" in qml_text


def test_page_runtime_keeps_header_capability_disabled_by_default() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "PageRuntime.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "property bool showHeader: false" in qml_text
    assert "visible: root.showHeader && (root.title.length > 0 || root.description.length > 0)" in qml_text


def test_page_runtime_uses_theme_tokens_without_new_palette() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "PageRuntime.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "theme.panelBg" in qml_text
    assert "theme.panelLine" in qml_text
    assert "theme.titleInk" in qml_text
    assert "theme.bodyInk" in qml_text
    assert "theme.accent" in qml_text
    assert "#" not in qml_text

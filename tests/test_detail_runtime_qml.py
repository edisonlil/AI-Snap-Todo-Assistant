from __future__ import annotations

from pathlib import Path


def _detail_runtime_source() -> str:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "DetailRuntime.qml"
    return qml_path.read_text(encoding="utf-8")


def test_detail_runtime_exposes_standard_slots() -> None:
    qml_text = _detail_runtime_source()

    assert "property alias actionContent: actionSlot.data" in qml_text
    assert "property alias bodyContent: bodySlot.data" in qml_text
    assert "property alias footerContent: footerSlot.data" in qml_text


def test_detail_runtime_keeps_back_button_enabled_by_default() -> None:
    qml_text = _detail_runtime_source()

    assert 'property string backLabel: "返回列表"' in qml_text
    assert "property bool showBackButton: true" in qml_text
    assert "ControlPanelPlainButton {" in qml_text
    assert "onClicked: root.backRequested()" in qml_text


def test_detail_runtime_uses_existing_theme_tokens_without_new_palette() -> None:
    qml_text = _detail_runtime_source()

    assert "theme.panelBg" in qml_text
    assert "theme.panelLine" in qml_text
    assert "theme.titleInk" in qml_text
    assert "theme.bodyInk" in qml_text
    assert "theme.buttonDefaultBg" in qml_text
    assert "theme.buttonPrimaryBg" in qml_text
    assert "#" not in qml_text

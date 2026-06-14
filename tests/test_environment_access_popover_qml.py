from __future__ import annotations

from pathlib import Path


QML_DIR = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml"


def _qml(file_name: str) -> str:
    return (QML_DIR / file_name).read_text(encoding="utf-8")


def test_environment_access_popover_receives_full_theme_tokens() -> None:
    source = _qml("TodoDetailPanel.qml")

    assert "theme: root.themeTokens" in source
    assert "theme: root\n" not in source


def test_environment_access_popover_uses_shared_theme_tokens() -> None:
    source = _qml("EnvironmentAccessPopover.qml")

    expected_tokens = [
        "readonly property color panelBg: theme.panelBg",
        "readonly property color panelAltBg: theme.panelAltBg",
        "readonly property color fieldLine: theme.fieldLine",
        "readonly property color accent: theme.accent",
        "color: root.panelBg",
        "color: root.panelAltBg",
        "color: root.accent",
        "border.color: root.fieldLine",
    ]
    for token in expected_tokens:
        assert token in source

    control_panel_component_tokens = [
        "theme.button",
        "theme.form",
        "theme.component",
        "buttonPrimary",
        "buttonDefault",
        "buttonBorder",
        "formField",
        "componentRadius",
        "componentHeight",
    ]
    for token in control_panel_component_tokens:
        assert token not in source

    for line in source.splitlines():
        stripped = line.strip()
        assert not stripped.startswith(("color: \"#", "border.color: \"#")), stripped
        assert "ctx.strokeStyle = \"#" not in stripped, stripped

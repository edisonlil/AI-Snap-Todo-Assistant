from __future__ import annotations

from pathlib import Path


def test_assist_troubleshooting_qml_reads_dynamic_error_code_results() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "AssistTroubleshootingWindow.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "assistErrorCodeResults" in qml_text
    assert "模拟 2 条结果" not in qml_text
    assert 'readonly property color contentFill: root.themeTokens.panelAltBg || "#F5F5F5"' in qml_text


def test_assist_troubleshooting_case_card_is_height_limited_and_clipped() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "AssistTroubleshootingWindow.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "readonly property real resultCardMaxHeight" in qml_text
    assert "Math.min(resultCardColumn.implicitHeight + 20, panel.resultCardMaxHeight)" in qml_text
    assert "clip: true" in qml_text
    assert "引用到跟进" not in qml_text

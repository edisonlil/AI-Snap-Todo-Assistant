from __future__ import annotations

from pathlib import Path


def test_assist_troubleshooting_qml_reads_dynamic_error_code_results() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "AssistTroubleshootingWindow.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "assistErrorCodeResults" in qml_text
    assert "模拟 2 条结果" not in qml_text
    assert 'readonly property color contentFill: root.themeTokens.panelAltBg || "#F5F5F5"' in qml_text

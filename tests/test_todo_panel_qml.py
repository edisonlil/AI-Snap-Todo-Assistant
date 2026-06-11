from __future__ import annotations

from pathlib import Path


def test_todo_panel_qml_uses_fallback_bridge_for_runtime_bindings() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "readonly property var bridge:" in qml_text
    assert "id: fallbackBridge" in qml_text
    assert "todoPanelBridge." not in qml_text


def test_todo_panel_qml_reads_header_status_from_bridge() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert 'text: root.bridge.headerStatusText' in qml_text
    assert 'text: root.bridge.todoCount + " 进行中"' not in qml_text

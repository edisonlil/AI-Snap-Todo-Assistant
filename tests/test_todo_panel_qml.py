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


def test_todo_panel_mini_status_matches_collapsed_toolbar_segment() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")
    mini_status = qml_text.split("id: miniStatus", 1)[1].split("id: miniActions", 1)[0]

    assert 'source: root.bridge.logoSource' in mini_status
    assert 'text: root.bridge.miniStatusText' in mini_status
    assert mini_status.index('source: root.bridge.logoSource') < mini_status.index('text: root.bridge.miniStatusText')
    assert "readonly property bool mirrorForEdge: root.dockedLeft && !root.miniHovering" in mini_status
    assert "anchors.left: parent.left" in mini_status
    assert "layoutDirection: mirrorForEdge ? Qt.RightToLeft : Qt.LeftToRight" in mini_status
    assert "width: Math.max(" in mini_status
    assert "anchors.leftMargin: 13" in mini_status
    assert "sourceSize.width: 24" in mini_status
    assert "sourceSize.height: 24" in mini_status
    assert "width: Math.max(0, miniStatus.width - 24 - miniStatus.spacing)" in mini_status
    assert "elide: Text.ElideRight" in mini_status
    assert "wrapMode: Text.NoWrap" in mini_status
    assert "maximumLineCount: 1" in mini_status


def test_todo_panel_mini_actions_fade_in_for_hover_strip() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")
    mini_actions = qml_text.split("id: miniActions", 1)[1].split("id: miniMouseArea", 1)[0]

    assert "opacity: root.miniHovering ? 1 : 0" in mini_actions
    assert "anchors.right: parent.right" in mini_actions
    assert "layoutDirection: root.dockedLeft ? Qt.RightToLeft : Qt.LeftToRight" not in mini_actions
    assert 'text: "+"' in mini_actions
    assert "root.bridge.pinned ? 0 : 32" in mini_actions


def test_todo_panel_mini_badge_keeps_outer_radius_and_flat_screen_edge() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")
    mini_surface = qml_text.split("id: miniSurface", 1)[1].split("id: miniStatus", 1)[0]

    assert "radius: root.miniRadius" in mini_surface
    assert "x: root.dockedLeft ? 0 : parent.width - root.miniRadius" in mini_surface
    assert "width: root.miniRadius" in mini_surface
    assert "radius: 0" in mini_surface
    assert "visible: !root.miniHovering" in mini_surface


def test_todo_panel_delegate_selection_uses_bridge_selected_todo_id() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TodoPanel.qml"
    qml_text = qml_path.read_text(encoding="utf-8")
    assert "readonly property bool selected: root.bridge.selectedTodoId === modelData.id" in qml_text
    assert "modelData.selected" not in qml_text
    assert 'color: selected ? root.accentSoft : "transparent"' in qml_text
    assert "border.color: selected ? root.accent : root.panelLine" in qml_text
    assert "color: root.accent" in qml_text
    assert "color: selected ? root.accent : root.titleInk" in qml_text

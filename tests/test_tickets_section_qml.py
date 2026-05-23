from __future__ import annotations

from pathlib import Path


def test_tickets_section_table_supports_horizontal_scroll() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TicketsSection.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "id: tableHorizontalFlickable" in qml_text
    assert "flickableDirection: Flickable.HorizontalFlick" in qml_text
    assert "ScrollBar.horizontal" in qml_text
    assert "property real tableContentWidth" in qml_text
    assert "width: Math.max(tableHorizontalFlickable.width, tableFlickable.tableContentWidth)" in qml_text
    assert "anchors.bottom: paginationBar.top" not in qml_text


def test_tickets_section_rows_open_detail_without_covering_actions() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TicketsSection.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "id: rowDetailMouseArea" in qml_text
    assert "parent.width - tableFlickable.sidePadding - tableFlickable.actionColumnWidth" in qml_text
    assert "controlPanelBridge.openTicketDetail(modelData.id)" in qml_text
    assert "id: copyMouseArea" in qml_text
    assert "id: detailMouseArea" in qml_text
    assert qml_text.count("mouse.accepted = true") >= 3

from __future__ import annotations

from pathlib import Path


def test_tickets_section_uses_page_runtime_slots() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TicketsSection.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "PageRuntime {" in qml_text
    assert "filterContent: Flow" in qml_text
    assert "actionContent: ColumnLayout" in qml_text
    assert "listContent: ColumnLayout" in qml_text
    assert "footerContent: Rectangle" in qml_text
    page_runtime_start = qml_text.index("PageRuntime {")
    filter_content_start = qml_text.index("filterContent: Flow")
    page_runtime_header = qml_text[page_runtime_start:filter_content_start]
    assert "title:" not in page_runtime_header
    assert "description:" not in page_runtime_header
    assert qml_text.index("filterContent: Flow") < qml_text.index("actionContent: ColumnLayout")
    assert qml_text.index("actionContent: ColumnLayout") < qml_text.index("listContent: ColumnLayout")
    assert qml_text.index("listContent: ColumnLayout") < qml_text.index("footerContent: Rectangle")


def test_tickets_section_table_supports_horizontal_scroll() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TicketsSection.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "id: tableHorizontalFlickable" in qml_text
    assert "flickableDirection: Flickable.HorizontalFlick" in qml_text
    assert "ScrollBar.horizontal" in qml_text
    assert "property real tableContentWidth" in qml_text
    assert "width: Math.max(tableHorizontalFlickable.width, tableFlickable.tableContentWidth)" in qml_text
    assert "anchors.bottom: paginationBar.top" not in qml_text
    assert "anchors.bottomMargin: paginationBar.height" not in qml_text


def test_tickets_section_rows_open_detail_without_covering_actions() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TicketsSection.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "id: rowDetailMouseArea" in qml_text
    assert "parent.width - tableFlickable.sidePadding - tableFlickable.actionColumnWidth" in qml_text
    assert "controlPanelBridge.openTicketDetail(modelData.id)" in qml_text
    assert "id: copyMouseArea" not in qml_text
    assert "id: detailMouseArea" in qml_text
    assert qml_text.count("mouse.accepted = true") >= 2


def test_tickets_section_uses_numbered_pagination() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TicketsSection.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "function ticketPaginationItems()" in qml_text
    assert 'type: "gap"' in qml_text
    assert "id: previousPageButton" in qml_text
    assert "id: nextPageButton" in qml_text
    assert "Row {\n                id: paginationSummary" in qml_text
    assert "anchors.right: parent.right" in qml_text
    assert "paginationBar.compactLayout" not in qml_text
    assert "width: 28" in qml_text
    assert "height: 28" in qml_text
    assert "model: ticketSection.ticketPaginationItems()" in qml_text
    assert '"10 / \\u9875"' in qml_text
    assert '"\\u5171 " + ticketSection.ticketTotalCount + " \\u6761"' in qml_text
    assert '"\\u5171 " + ticketSection.ticketTotalPages + " \\u9875"' in qml_text
    assert '"\\u4e0a\\u4e00\\u9875"' not in qml_text
    assert '"\\u4e0b\\u4e00\\u9875"' not in qml_text


def test_tickets_section_includes_customer_environment_dropdown() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TicketsSection.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert 'label: "客户环境"' in qml_text
    assert "SingleSelectCascadeField {" in qml_text
    assert "customerEnvironmentOptions" in qml_text
    assert 'saveSelectedTicketField("customer_environment"' in qml_text
    assert "customerEnvironmentValue" in qml_text


def test_tickets_section_retries_customer_environment_edit_after_dictionary_load() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "TicketsSection.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "property bool pendingCustomerEnvironmentEdit: false" in qml_text
    assert "function requestCustomerEnvironmentEdit()" in qml_text
    assert "controlPanelBridge.refreshCustomerEnvironmentOptions()" in qml_text
    assert "function resumePendingCustomerEnvironmentEdit()" in qml_text
    assert "ticketSection.resumePendingCustomerEnvironmentEdit()" in qml_text


def test_dropdown_popups_anchor_below_editor_actions() -> None:
    single_select_qml = (
        Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "SingleSelectCascadeField.qml"
    ).read_text(encoding="utf-8")
    root_cause_qml = (
        Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "RootCauseCascadeField.qml"
    ).read_text(encoding="utf-8")

    assert "return editorColumn.mapToItem(rootField, 0, editorColumn.height + 8)" in single_select_qml
    assert "return cascadeEditor.mapToItem(rootField, 0, cascadeEditor.height + 8)" in root_cause_qml
    assert "y: rootField.popupAnchorPoint().y" in single_select_qml
    assert "y: rootField.popupAnchorPoint().y" in root_cause_qml

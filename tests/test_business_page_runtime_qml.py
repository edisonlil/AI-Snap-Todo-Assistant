from __future__ import annotations

from pathlib import Path


QML_DIR = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml"


def _qml(file_name: str) -> str:
    return (QML_DIR / file_name).read_text(encoding="utf-8")


def test_project_list_uses_page_runtime_and_detail_uses_detail_runtime() -> None:
    qml_text = _qml("ProjectsSection.qml")

    assert "PageRuntime {" in qml_text
    assert "DetailRuntime {" in qml_text
    assert "filterContent: RowLayout" in qml_text
    assert "actionContent: RowLayout" in qml_text
    assert "listContent: RowLayout" in qml_text
    assert "bodyContent: ColumnLayout" in qml_text
    assert "visible: theme.projectViewMode === \"list\"" in qml_text
    assert "visible: theme.projectViewMode === \"detail\"" in qml_text
    assert qml_text.index("PageRuntime {") < qml_text.index("visible: theme.projectViewMode === \"detail\"")
    assert qml_text.index("PageRuntime {") < qml_text.index("DetailRuntime {")
    assert "onBackRequested: theme.showProjectList()" in qml_text


def test_project_detail_form_uses_stable_grid_layout() -> None:
    qml_text = _qml("ProjectsSection.qml")
    detail_source = qml_text[qml_text.index("DetailRuntime {") :]

    assert "readonly property bool compactForm: width < 760" in detail_source
    assert "GridLayout {" in detail_source
    assert "columns: projectFormColumn.compactForm ? 1 : 2" in detail_source
    assert "Layout.columnSpan: projectFormColumn.compactForm ? 1 : 2" in detail_source
    assert "Layout.preferredWidth: 1" in detail_source
    assert "Layout.preferredWidth: 92" in detail_source
    assert "Layout.preferredWidth: 86" in detail_source


def test_business_runtime_surfaces_use_compact_filled_cards() -> None:
    page_runtime = _qml("PageRuntime.qml")
    detail_runtime = _qml("DetailRuntime.qml")
    section_card = _qml("ControlPanelSectionCard.qml")

    assert "property int sectionRadius: 12" in page_runtime
    assert "readonly property color surfaceColor: theme.panelAltBg" in page_runtime
    assert "border.width: 0" in page_runtime
    assert "radius: 12" in detail_runtime
    assert "readonly property color surfaceColor: theme.panelAltBg" in detail_runtime
    assert "radius: 12" in section_card


def test_environment_list_uses_page_runtime_and_detail_uses_detail_runtime() -> None:
    qml_text = _qml("EnvironmentsSection.qml")
    environment_manager = _qml("EnvironmentManagerSection.qml")

    assert "PageRuntime {" in qml_text
    assert "filterContent: ColumnLayout" in qml_text
    assert "actionContent: RowLayout" in qml_text
    assert "listContent: Item" in qml_text
    assert "listFramed: false" in qml_text
    assert "Flickable {" in qml_text
    assert "GridLayout {" in qml_text
    assert "id: environmentGrid" in qml_text
    assert "readonly property int gridColumns: width >= 1076 ? 4 : (width >= 796 ? 3 : (width >= 532 ? 2 : 1))" in qml_text
    assert "readonly property real gridCardWidth" in qml_text
    assert "visible: root.environmentViewMode === \"list\"" in qml_text
    assert "EnvironmentManagerSection {" in qml_text
    assert qml_text.index("PageRuntime {") < qml_text.index("EnvironmentManagerSection {")
    assert "DetailRuntime {" in environment_manager
    assert "bodyContent: ColumnLayout" in environment_manager
    assert "onBackRequested: root.backRequested()" in environment_manager


def test_access_editor_form_uses_aligned_grid_layout() -> None:
    qml_text = _qml("EnvironmentManagerSection.qml")
    access_source = qml_text[qml_text.index("id: accessForm") :]

    assert "readonly property bool compactForm: width < 760" in access_source
    assert "columns: accessForm.compactForm ? 1 : 2" in access_source
    assert "Layout.columnSpan: accessForm.compactForm ? 1 : 2" in access_source
    assert "Layout.preferredWidth: 1" in access_source
    assert "id: nameTypeRow" in access_source
    assert "Layout.preferredWidth: 220" in access_source
    assert "id: credentialsRow" in access_source
    assert "id: sortOrderInline" in access_source
    assert "Layout.preferredWidth: 152" in access_source
    assert "Layout.maximumWidth: 152" in access_source
    assert "width: 112" in access_source
    assert "Layout.preferredWidth: 86" in access_source
    assert "Layout.preferredWidth: 116" in access_source


def test_ticket_list_uses_page_runtime_and_detail_uses_detail_runtime() -> None:
    qml_text = _qml("TicketsSection.qml")

    assert "PageRuntime {" in qml_text
    assert "DetailRuntime {" in qml_text
    assert "filterContent: Flow" in qml_text
    assert "actionContent: ColumnLayout" in qml_text
    assert "listContent: ColumnLayout" in qml_text
    assert "visible: controlPanelBridge.selectedTicket.id.length === 0" in qml_text
    assert "visible: controlPanelBridge.selectedTicket.id.length > 0" in qml_text
    assert qml_text.index("PageRuntime {") < qml_text.index("DetailRuntime {")
    detail_source = qml_text[qml_text.index("DetailRuntime {") :]
    assert "ticketSection.cancelDeleteSelectedTicket()" in detail_source
    assert "ticketSection.cancelUnlinkSelectedTicketProject()" in detail_source
    assert "controlPanelBridge.backToTicketList()" in detail_source


def test_control_panel_settings_pages_keep_native_layouts() -> None:
    qml_text = _qml("ControlPanel.qml")

    assert "PageRuntime {" not in qml_text
    assert 'visible: root.currentSection === "models"' in qml_text
    assert 'visible: root.currentSection === "theme"' in qml_text
    assert 'visible: root.currentSection === "analysis_rules"' in qml_text


def test_control_panel_uses_macos_self_drawn_traffic_lights() -> None:
    qml_text = _qml("ControlPanel.qml")

    assert "readonly property bool isMacos: controlPanelBridge ? controlPanelBridge.isMacos : false" in qml_text
    assert "component MacosTrafficLightButton: Rectangle" in qml_text
    assert 'fillColor: "#FF5F57"' in qml_text
    assert 'fillColor: "#FFBD2E"' in qml_text
    assert 'fillColor: "#28C840"' in qml_text
    assert "visible: root.isMacos" in qml_text
    assert "visible: !root.isMacos" in qml_text
    assert "font.pixelSize: 23" in qml_text
    assert "elide: Text.ElideRight" in qml_text

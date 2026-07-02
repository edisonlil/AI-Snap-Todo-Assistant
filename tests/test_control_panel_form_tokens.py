from __future__ import annotations

from pathlib import Path


QML_DIR = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml"


def _qml(file_name: str) -> str:
    return (QML_DIR / file_name).read_text(encoding="utf-8")


def test_control_panel_form_components_consume_form_tokens() -> None:
    component_files = [
        "ControlPanelSettingsInput.qml",
        "ControlPanelSettingsCombo.qml",
        "ControlPanelSettingsArea.qml",
        "ControlPanelSettingsSpinBox.qml",
        "ControlPanelPixelInput.qml",
        "ControlPanelSettingsCheckBox.qml",
        "ControlPanelDateField.qml",
        "ControlPanelSegmentButton.qml",
        "ControlPanelChip.qml",
    ]

    for file_name in component_files:
        source = _qml(file_name)
        assert "form" in source, file_name

    assert "theme.componentHeight || theme.formFieldHeight || 36" in _qml("ControlPanelSettingsInput.qml")
    assert "theme.formPopupItemHeight || 38" in _qml("ControlPanelSettingsCombo.qml")
    assert "theme.componentRadius || theme.formFieldRadius || 8" in _qml("ControlPanelDateField.qml")
    assert "theme.componentHeight || theme.formFieldHeight || 36" in _qml("ControlPanelPixelInput.qml")
    assert "theme.componentRadius || theme.formFieldRadius || 8" in _qml("ControlPanelPixelInput.qml")
    assert "theme.formChipHeight || 28" in _qml("ControlPanelChip.qml")
    assert 'text: "px"' in _qml("ControlPanelPixelInput.qml")
    assert "Keys.onUpPressed" in _qml("ControlPanelPixelInput.qml")
    assert "Keys.onDownPressed" in _qml("ControlPanelPixelInput.qml")


def test_control_panel_sections_use_shared_form_components() -> None:
    projects = _qml("ProjectsSection.qml")
    environments = _qml("EnvironmentsSection.qml")
    environment_manager = _qml("EnvironmentManagerSection.qml")
    control_panel = _qml("ControlPanel.qml")
    tickets = _qml("TicketsSection.qml")

    assert "ControlPanelDateField {" in projects
    assert "ControlPanelChip {" in projects
    assert "ControlPanelSettingsCheckBox {" in projects
    assert "ControlPanelSegmentButton {" in environments
    assert "ControlPanelSettingsArea {" in environment_manager
    assert "ControlPanelSettingsSpinBox {" in environment_manager
    assert "component SettingsInput: ControlPanelSettingsInput" in control_panel
    assert "component SettingsCombo: ControlPanelSettingsCombo" in control_panel
    assert "component MultiLineInput: ControlPanelSettingsArea" in control_panel
    assert "component ModelFieldInput: ControlPanelSettingsInput" in control_panel
    assert "component ModelFieldCombo: ControlPanelSettingsCombo" in control_panel
    assert "ticketSearchInput" in tickets
    assert "ticketTypeCombo" in tickets
    ticket_filter_source = tickets[tickets.index("id: ticketSearchInput"):tickets.index("actionContent:")]
    assert "height: 40" not in ticket_filter_source


def test_project_alias_chips_render_normalized_alias_text() -> None:
    projects = _qml("ProjectsSection.qml")
    control_panel = _qml("ControlPanel.qml")

    assert "function projectAliasText(value)" in control_panel
    assert "function normalizedProjectAliases(values)" in control_panel
    assert "aliases: normalizedProjectAliases(source.aliases)" in control_panel
    assert "required property var modelData" in projects
    assert "required property var modelData" in control_panel
    assert "label: theme.projectAliasText(modelData)" in projects
    assert "label: root.projectAliasText(modelData)" in control_panel
    assert "label: modelData" not in projects
    assert "label: modelData" not in control_panel


def test_control_panel_buttons_use_shared_button_tokens() -> None:
    button = _qml("ControlPanelPlainButton.qml")
    control_panel = _qml("ControlPanel.qml")

    assert "theme.buttonRadius || 8" in button
    assert "theme.buttonHeight || 36" in button
    assert "theme.buttonPrimaryBg" in button
    assert "theme.buttonPrimaryBgHover" in button
    assert "theme.buttonPrimaryBgPressed" in button
    assert "buttonMouse.containsMouse" in button
    assert "component PlainButton: ControlPanelPlainButton" in control_panel


def test_control_panel_shows_server_login_gate_when_required() -> None:
    control_panel = _qml("ControlPanel.qml")

    assert "readonly property bool serverLoginRequired" in control_panel
    assert "visible: root.serverLoginRequired" in control_panel
    assert "visible: !root.serverLoginRequired" in control_panel
    assert 'text: "登录 Chattodo"' in control_panel
    assert "controlPanelBridge.saveServerLogin()" in control_panel


def test_control_panel_sidebar_renders_server_identity_card() -> None:
    control_panel = _qml("ControlPanel.qml")

    assert "readonly property var serverIdentity" in control_panel
    assert "readonly property bool serverIdentityLoading" in control_panel
    assert "function sidebarGreetingName()" in control_panel
    assert "id: sidebarGreeting" in control_panel
    assert 'text: "你好，" + root.sidebarGreetingName()' in control_panel
    assert "color: root.titleInk" in control_panel
    assert "font.pixelSize: 13" in control_panel
    assert "anchors.bottom: parent.bottom" in control_panel
    assert "anchors.bottomMargin: 18" in control_panel
    assert "anchors.bottom: sidebarGreeting.top" in control_panel


def test_control_panel_spin_box_is_custom_drawn() -> None:
    spin_box = _qml("ControlPanelSettingsSpinBox.qml")

    assert "SpinBox {" not in spin_box
    assert "Rectangle {" in spin_box
    assert "signal valueModified" in spin_box
    assert "TextInput {" in spin_box
    assert "MouseArea {" in spin_box


def test_control_panel_settings_combo_supports_typed_fuzzy_filtering() -> None:
    combo = _qml("ControlPanelSettingsCombo.qml")

    assert "editable: true" in combo
    assert "property string filterText" in combo
    assert "function fuzzyMatch(text, query)" in combo
    assert "function filteredOptions()" in combo
    assert "TextField {" in combo
    assert "model: combo.popup.visible ? combo.filteredOptions() : null" in combo
    assert "text: modelData.label" in combo
    assert "onTextEdited: {" in combo

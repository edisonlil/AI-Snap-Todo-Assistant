import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: globalEnvSection
    required property var theme

    visible: controlPanelBridge.currentSection === "global_environments"
    spacing: 0

    EnvironmentManagerSection {
        theme: globalEnvSection.theme
        scopeMode: "global"
        groupsModel: controlPanelBridge.globalEnvironmentGroups
        Layout.fillWidth: true
    }
}

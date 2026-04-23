import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var theme

    visible: controlPanelBridge.currentSection === "environments"
    spacing: 14

    readonly property bool isProjectScope: controlPanelBridge.environmentScopeFilter === "project"
    readonly property var scopeOptions: [
        { value: "global", text: "全局环境" },
        { value: "project", text: "项目环境" }
    ]
    property string searchText: ""
    property var projectOptions: buildProjectOptions()
    property var filteredGroups: buildFilteredGroups()

    function buildProjectOptions() {
        var projects = controlPanelBridge.projects || []
        var options = []
        for (var index = 0; index < projects.length; index += 1) {
            var item = projects[index]
            var label = item.projectName || item.taskOrderNo || item.id || ""
            if ((item.taskOrderNo || "").length > 0 && (item.projectName || "").length > 0) {
                label = item.projectName + " / " + item.taskOrderNo
            }
            options.push({
                value: item.id || "",
                text: label
            })
        }
        return options
    }

    function currentGroups() {
        return isProjectScope ? (controlPanelBridge.projectEnvironmentGroups || []) : (controlPanelBridge.globalEnvironmentGroups || [])
    }

    function groupMatches(groupItem, keyword) {
        if (!keyword.length) {
            return true
        }
        if (theme.fuzzyMatch(groupItem.name || "", keyword) ||
                theme.fuzzyMatch(groupItem.type || "", keyword) ||
                theme.fuzzyMatch(groupItem.note || "", keyword) ||
                theme.fuzzyMatch(groupItem.scopeLabel || "", keyword)) {
            return true
        }
        var entries = groupItem.entries || []
        for (var entryIndex = 0; entryIndex < entries.length; entryIndex += 1) {
            var entry = entries[entryIndex]
            if (theme.fuzzyMatch(entry.name || "", keyword) ||
                    theme.fuzzyMatch(entry.urlOrHost || "", keyword) ||
                    theme.fuzzyMatch(entry.username || "", keyword) ||
                    theme.fuzzyMatch(entry.note || "", keyword)) {
                return true
            }
        }
        return false
    }

    function buildFilteredGroups() {
        var keyword = (searchText || "").trim()
        var sourceGroups = currentGroups()
        if (!keyword.length) {
            return sourceGroups
        }
        var result = []
        for (var index = 0; index < sourceGroups.length; index += 1) {
            var groupItem = sourceGroups[index]
            if (groupMatches(groupItem, keyword)) {
                result.push(groupItem)
            }
        }
        return result
    }

    function ensureProjectSelection() {
        if (!isProjectScope) {
            return
        }
        var selectedProjectId = controlPanelBridge.projectEnvironmentProjectId || ""
        for (var index = 0; index < projectOptions.length; index += 1) {
            if (projectOptions[index].value === selectedProjectId) {
                return
            }
        }
        if (projectOptions.length > 0) {
            controlPanelBridge.listProjectEnvironments(projectOptions[0].value)
            return
        }
        controlPanelBridge.listProjectEnvironments("")
    }

    function refreshCurrentScope() {
        if (isProjectScope) {
            ensureProjectSelection()
            return
        }
        controlPanelBridge.listGlobalEnvironments()
    }

    function emptyStateMessage() {
        if (isProjectScope && projectOptions.length === 0) {
            return "当前还没有可选项目，请先在项目管理中创建或导入项目。"
        }
        if ((searchText || "").trim().length > 0) {
            return "没有匹配的环境或访问项。"
        }
        return ""
    }

    onVisibleChanged: {
        if (visible) {
            refreshCurrentScope()
        }
    }

    Component.onCompleted: {
        if (visible) {
            refreshCurrentScope()
        }
    }

    Connections {
        target: controlPanelBridge
        function onDataChanged() {
            if (root.visible && root.isProjectScope) {
                root.ensureProjectSelection()
            }
        }
    }

    ControlPanelSectionCard {
        theme: root.theme
        Layout.fillWidth: true
        implicitHeight: filterContent.implicitHeight + 24
        color: theme.panelBg

        ColumnLayout {
            id: filterContent
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                ControlPanelSettingsInput {
                    id: searchInput
                    theme: root.theme
                    Layout.fillWidth: true
                    placeholderText: "搜索环境名 / URL / 项目名"
                    text: root.searchText
                    onTextEdited: root.searchText = text
                }

                Repeater {
                    model: root.scopeOptions

                    delegate: Rectangle {
                        radius: 16
                        implicitWidth: scopeLabel.implicitWidth + 28
                        implicitHeight: 42
                        color: controlPanelBridge.environmentScopeFilter === modelData.value ? theme.accentSoft : theme.inputBg
                        border.width: 1
                        border.color: controlPanelBridge.environmentScopeFilter === modelData.value ? theme.accent : theme.panelLine

                        Text {
                            id: scopeLabel
                            anchors.centerIn: parent
                            text: modelData.text
                            color: controlPanelBridge.environmentScopeFilter === modelData.value ? theme.accent : theme.titleInk
                            font.family: theme.uiFont
                            font.pixelSize: 12
                            font.weight: controlPanelBridge.environmentScopeFilter === modelData.value ? 700 : 500
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: controlPanelBridge.setEnvironmentScopeFilter(modelData.value)
                        }
                    }
                }
            }

            RowLayout {
                visible: root.isProjectScope
                Layout.fillWidth: true
                spacing: 10

                Text {
                    text: "当前项目"
                    color: theme.labelInk
                    font.family: theme.uiFont
                    font.pixelSize: 12
                }

                ControlPanelSettingsCombo {
                    theme: root.theme
                    Layout.fillWidth: true
                    model: root.projectOptions
                    currentIndex: Math.max(0, theme.optionIndex(root.projectOptions, controlPanelBridge.projectEnvironmentProjectId || ""))
                    enabled: root.projectOptions.length > 0
                    onActivated: controlPanelBridge.listProjectEnvironments(root.projectOptions[currentIndex].value)
                }
            }
        }
    }

    EnvironmentManagerSection {
        theme: root.theme
        scopeMode: root.isProjectScope ? "project" : "global"
        projectId: controlPanelBridge.projectEnvironmentProjectId || ""
        groupsModel: root.filteredGroups
        emptyStateText: root.emptyStateMessage()
        Layout.fillWidth: true
    }
}

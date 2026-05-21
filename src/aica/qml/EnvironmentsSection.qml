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
    property string environmentViewMode: "list"
    property bool creatingEnvironment: false
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
        return theme.fuzzyMatch(groupItem.name || "", keyword)
            || theme.fuzzyMatch(groupItem.type || "", keyword)
            || theme.fuzzyMatch(groupItem.note || "", keyword)
            || theme.fuzzyMatch(groupItem.scopeLabel || "", keyword)
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
            return "请先维护项目，再为项目绑定环境。"
        }
        if ((searchText || "").trim().length > 0) {
            return "没有匹配的环境，请调整搜索关键词。"
        }
        return "当前范围下还没有环境。"
    }

    function showEnvironmentList() {
        environmentViewMode = "list"
        creatingEnvironment = false
        controlPanelBridge.closeEnvironmentDetail()
    }

    function startCreateEnvironment() {
        if (isProjectScope && !(controlPanelBridge.projectEnvironmentProjectId || "").length) {
            return
        }
        creatingEnvironment = true
        environmentViewMode = "detail"
        controlPanelBridge.closeEnvironmentDetail()
    }

    function openEnvironmentDetail(environmentId) {
        creatingEnvironment = false
        environmentViewMode = "detail"
        controlPanelBridge.openEnvironmentDetail(environmentId)
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
            if (root.environmentViewMode === "detail" && !root.creatingEnvironment
                    && !(controlPanelBridge.selectedEnvironmentId || "").length) {
                root.environmentViewMode = "list"
            }
            if (root.creatingEnvironment && (controlPanelBridge.selectedEnvironmentId || "").length) {
                root.creatingEnvironment = false
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
                    placeholderText: "搜索环境名称、类型或备注"
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
                            onClicked: {
                                root.environmentViewMode = "list"
                                root.creatingEnvironment = false
                                controlPanelBridge.setEnvironmentScopeFilter(modelData.value)
                            }
                        }
                    }
                }
            }

            RowLayout {
                visible: root.isProjectScope
                Layout.fillWidth: true
                spacing: 10

                Text {
                    text: "所属项目"
                    color: theme.labelInk
                    font.family: theme.uiFont
                    font.pixelSize: 12
                }

                ControlPanelSettingsCombo {
                    theme: root.theme
                    Layout.fillWidth: true
                    popupMaxHeight: 240
                    popupItemMinHeight: 48
                    popupTextMaximumLineCount: 2
                    model: root.projectOptions
                    currentIndex: Math.max(0, theme.optionIndex(root.projectOptions, controlPanelBridge.projectEnvironmentProjectId || ""))
                    enabled: root.projectOptions.length > 0
                    onActivated: {
                        root.environmentViewMode = "list"
                        root.creatingEnvironment = false
                        controlPanelBridge.listProjectEnvironments(root.projectOptions[currentIndex].value)
                    }
                }
            }
        }
    }

    ControlPanelSectionCard {
        visible: root.environmentViewMode === "list"
        theme: root.theme
        Layout.fillWidth: true
        implicitHeight: listContent.implicitHeight + 24
        color: theme.panelBg

        ColumnLayout {
            id: listContent
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            RowLayout {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: root.isProjectScope ? "项目环境列表" : "全局环境列表"
                        color: theme.titleInk
                        font.family: theme.uiFont
                        font.pixelSize: 15
                        font.weight: 700
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "列表页只保留环境摘要。点击进入详情后，再维护环境配置和访问信息。"
                        color: theme.labelInk
                        font.family: theme.uiFont
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                    }
                }

                ControlPanelPlainButton {
                    theme: root.theme
                    label: "新建环境"
                    visible: !root.isProjectScope || (controlPanelBridge.projectEnvironmentProjectId || "").length > 0
                    onClicked: root.startCreateEnvironment()
                }
            }

            Text {
                visible: root.filteredGroups.length === 0
                Layout.fillWidth: true
                text: root.emptyStateMessage()
                color: theme.bodyInk
                font.family: theme.uiFont
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }

            Repeater {
                model: root.filteredGroups

                delegate: Rectangle {
                    Layout.fillWidth: true
                    radius: 18
                    color: theme.panelAltBg
                    border.width: 1
                    border.color: theme.panelLine
                    implicitHeight: cardColumn.implicitHeight + 24

                    ColumnLayout {
                        id: cardColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Text {
                                    text: modelData.name || ""
                                    color: theme.titleInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 14
                                    font.weight: 700
                                }

                                Text {
                                    visible: (modelData.type || "").length > 0 || (modelData.note || "").length > 0
                                    Layout.fillWidth: true
                                    text: ((modelData.type || "").length > 0 ? ("类型：" + modelData.type) : "")
                                          + (((modelData.type || "").length > 0 && (modelData.note || "").length > 0) ? " · " : "")
                                          + ((modelData.note || "").length > 0 ? modelData.note : "")
                                    color: theme.bodyInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }
                            }

                            Rectangle {
                                radius: 10
                                color: modelData.isGlobal ? "#EEF4FF" : "#EEF7EF"
                                border.width: 1
                                border.color: modelData.isGlobal ? "#C8D8FF" : "#C8E2CD"
                                implicitWidth: scopeText.implicitWidth + 16
                                implicitHeight: 24

                                Text {
                                    id: scopeText
                                    anchors.centerIn: parent
                                    text: modelData.scopeLabel || ""
                                    color: modelData.isGlobal ? "#26418F" : "#17663A"
                                    font.family: theme.uiFont
                                    font.pixelSize: 10
                                    font.weight: 700
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                text: "访问项 " + Number(modelData.entryCount || 0) + " 个"
                                color: theme.labelInk
                                font.family: theme.uiFont
                                font.pixelSize: 11
                            }

                            Text {
                                text: !!modelData.isActive ? "已启用" : "已停用"
                                color: !!modelData.isActive ? "#17663A" : theme.labelInk
                                font.family: theme.uiFont
                                font.pixelSize: 11
                                font.weight: 600
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            ControlPanelPlainButton {
                                theme: root.theme
                                label: "查看详情"
                                onClicked: root.openEnvironmentDetail(modelData.id)
                            }
                        }
                    }
                }
            }
        }
    }

    EnvironmentManagerSection {
        visible: root.environmentViewMode === "detail"
        theme: root.theme
        scopeMode: root.isProjectScope ? "project" : "global"
        projectId: controlPanelBridge.projectEnvironmentProjectId || ""
        selectedEnvironment: controlPanelBridge.selectedEnvironment
        creatingEnvironment: root.creatingEnvironment
        Layout.fillWidth: true
        onBackRequested: root.showEnvironmentList()
    }
}

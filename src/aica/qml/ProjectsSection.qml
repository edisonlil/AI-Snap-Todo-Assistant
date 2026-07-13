import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: projectSection
    required property var theme
    property string detailSubTab: "aliases"

    visible: controlPanelBridge.currentSection === "projects"
    spacing: 0

    Connections {
        target: theme

        function onProjectViewModeChanged() {
            if (theme.projectViewMode === "detail") {
                projectSection.detailSubTab = theme.projectDraft.id.length > 0 ? "versions" : "aliases"
            }
        }

        function onProjectDraftChanged() {
            if (theme.projectViewMode === "detail" && !theme.projectDraft.id.length) {
                projectSection.detailSubTab = "aliases"
            }
        }
    }

    PageRuntime {
        visible: theme.projectViewMode === "list"
        theme: projectSection.theme
        Layout.fillWidth: true
        Layout.fillHeight: true
        listMinimumHeight: 520

        filterContent: RowLayout {
            Layout.fillWidth: true
            spacing: 10

                ControlPanelSettingsInput {
                    id: projectSearchInput
                    theme: projectSection.theme
                    Layout.fillWidth: true
                    text: controlPanelBridge.projectQuery
                    placeholderText: "搜索项目名称 / 任务单号 / 群名别名"
                    onTextEdited: controlPanelBridge.listProjects(text, includeExpiredCheck.checked)
                }

                ControlPanelSettingsCheckBox {
                    id: includeExpiredCheck
                    theme: projectSection.theme
                    checked: controlPanelBridge.includeExpiredProjects
                    text: "包含过保项目"
                    onToggled: controlPanelBridge.listProjects(projectSearchInput.text, checked)
                }
            }

        actionContent: RowLayout {
            Layout.fillWidth: true
            spacing: 10

                ControlPanelPlainButton {
                    theme: projectSection.theme
                    label: controlPanelBridge.projectServerSyncing ? "拉取中..." : "从服务端拉取"
                    enabled: !controlPanelBridge.projectServerSyncing
                    onClicked: controlPanelBridge.syncProjectsFromServer()
                }

                ControlPanelPlainButton {
                    theme: projectSection.theme
                    label: "新建项目"
                    onClicked: theme.startNewProjectDraft()
                }

                ControlPanelPlainButton {
                    theme: projectSection.theme
                    label: "补关联未解决待办"
                    onClicked: controlPanelBridge.relinkOpenUnresolvedTodos()
                }

                RowLayout {
                    visible: controlPanelBridge.projectServerSyncing
                    spacing: 6

                    BusyIndicator {
                        running: controlPanelBridge.projectServerSyncing
                        implicitWidth: 24
                        implicitHeight: 24
                    }

                    Text {
                        text: controlPanelBridge.projectServerSyncMessage
                        color: theme.labelInk
                        font.family: theme.uiFont
                        font.pixelSize: 11
                    }
                }
            }

        footerContent: Text {
            visible: controlPanelBridge.lastProjectImportSummary.length > 0
            Layout.fillWidth: true
            Layout.margins: 12
            text: controlPanelBridge.lastProjectImportSummary
            color: theme.labelInk
            font.family: theme.uiFont
            font.pixelSize: 11
            wrapMode: Text.Wrap
        }

        listContent: RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 340
                    implicitHeight: 520
                    radius: 12
                    color: "transparent"
                    border.width: 0

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        Text {
                            text: "项目列表"
                            color: theme.titleInk
                            font.family: theme.uiFont
                            font.pixelSize: 14
                            font.weight: 700
                        }

                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 8
                            model: controlPanelBridge.projects

                            delegate: Rectangle {
                                property bool currentProject: theme.projectDraft.id === modelData.id
                                width: ListView.view.width
                                height: projectInfoColumn.implicitHeight + 20
                                radius: 12
                                color: currentProject ? theme.accentSoft : theme.panelBg
                                border.width: currentProject ? 1 : 0
                                border.color: currentProject ? theme.accent : theme.panelLine

                                Column {
                                    id: projectInfoColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 6

                                    Row {
                                        width: parent.width
                                        spacing: 8

                                        Text {
                                            width: parent.width - expireBadge.width - parent.spacing
                                            text: modelData.projectName
                                            color: theme.titleInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 13
                                            font.weight: 700
                                            elide: Text.ElideRight
                                        }

                                        Rectangle {
                                            id: expireBadge
                                            radius: 10
                                            color: modelData.isExpired ? "#FFF1ED" : "#E9F7EF"
                                            border.width: 1
                                            border.color: modelData.isExpired ? "#F4C7BC" : "#B6DEC5"
                                            implicitWidth: expireBadgeText.implicitWidth + 18
                                            implicitHeight: 24

                                            Text {
                                                id: expireBadgeText
                                                anchors.centerIn: parent
                                                text: modelData.isExpired ? "已过保" : "未过保"
                                                color: modelData.isExpired ? "#9A3412" : "#17663A"
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 700
                                            }
                                        }
                                    }

                                    Text {
                                        width: parent.width
                                        text: "任务单号: " + modelData.taskOrderNo
                                        color: theme.bodyInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 11
                                        wrapMode: Text.WrapAnywhere
                                    }

                                    Text {
                                        width: parent.width
                                        text: "过保日期: " + (theme.displayProjectDate(modelData.supportEndedAt) || "未填写")
                                        color: theme.labelInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 11
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: theme.loadProjectDraft(modelData)
                                }
                            }
                        }
                    }
                }

            }
        }

    DetailRuntime {
        visible: theme.projectViewMode === "detail"
        theme: projectSection.theme
        Layout.fillWidth: true
        title: theme.projectDraft.id.length > 0 ? "编辑项目" : "新建项目"
        description: "保存时会校验群名别名冲突，并只补关联未完成且未解决关联状态的待办。"
        onBackRequested: theme.showProjectList()

        actionContent: RowLayout {
            spacing: 10

            ControlPanelPlainButton {
                visible: theme.projectDraft.id.length > 0
                theme: projectSection.theme
                Layout.preferredWidth: 86
                label: "删除项目"
                onClicked: theme.deleteCurrentProject()
            }

            ControlPanelPlainButton {
                theme: projectSection.theme
                Layout.preferredWidth: 86
                label: "保存项目"
                primary: true
                strokeWidth: 0
                onClicked: theme.saveCurrentProject()
            }
        }

        bodyContent: ColumnLayout {
                        id: projectFormColumn
                        readonly property bool compactForm: width < 760

                        Layout.fillWidth: true
                        spacing: 10

                        GridLayout {
                            Layout.fillWidth: true
                            columns: projectFormColumn.compactForm ? 1 : 2
                            columnSpacing: 10
                            rowSpacing: 10

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                Layout.columnSpan: projectFormColumn.compactForm ? 1 : 2
                                text: theme.projectDraft.projectName
                                placeholderText: "项目名称"
                                onTextEdited: theme.updateProjectDraft("projectName", text)
                            }

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                text: theme.projectDraft.taskOrderNo
                                placeholderText: "任务单号"
                                onTextEdited: theme.updateProjectDraft("taskOrderNo", text)
                            }

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                text: theme.projectDraft.customerName
                                placeholderText: "客户名称"
                                onTextEdited: theme.updateProjectDraft("customerName", text)
                            }

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                text: theme.projectDraft.projectManager
                                placeholderText: "项目经理"
                                onTextEdited: theme.updateProjectDraft("projectManager", text)
                            }

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                text: theme.projectDraft.productLine
                                placeholderText: "产品线"
                                onTextEdited: theme.updateProjectDraft("productLine", text)
                            }

                            ControlPanelDateField {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                theme: projectSection.theme
                                text: theme.displayProjectDate(theme.projectDraft.followUpStartedAt)
                                placeholderText: "跟进开始日期"
                                onClicked: controlPanelBridge.chooseProjectDate("followUpStartedAt", theme.projectDraft.followUpStartedAt)
                            }

                            ControlPanelDateField {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                theme: projectSection.theme
                                text: theme.displayProjectDate(theme.projectDraft.supportEndedAt)
                                placeholderText: "过保日期"
                                onClicked: controlPanelBridge.chooseProjectDate("supportEndedAt", theme.projectDraft.supportEndedAt)
                            }

                            ControlPanelSettingsCombo {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                Layout.preferredWidth: 1
                                model: theme.projectLevelOptions
                                currentIndex: theme.optionIndex(theme.projectLevelOptions, theme.normalizedProjectLevel(theme.projectDraft.projectLevel))
                                onActivated: if (currentIndex >= 0) theme.updateProjectDraft("projectLevel", theme.projectLevelOptions[currentIndex].value)
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 0

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 0

                                    Repeater {
                                        model: [
                                            {
                                                key: "versions",
                                                label: "版本信息",
                                                count: (theme.projectDraft.projectVersions || []).length
                                            },
                                            {
                                                key: "aliases",
                                                label: "关联群聊",
                                                count: theme.projectDraft.aliases.length
                                            }
                                        ]

                                        delegate: Item {
                                            required property var modelData

                                            Layout.preferredWidth: projectDetailTabLabel.implicitWidth + 28
                                            Layout.minimumWidth: projectDetailTabLabel.implicitWidth + 28
                                            Layout.fillHeight: true
                                            implicitHeight: 44

                                            Text {
                                                id: projectDetailTabLabel
                                                anchors.left: parent.left
                                                anchors.verticalCenter: parent.verticalCenter
                                                anchors.leftMargin: 4
                                                text: modelData.label + " (" + modelData.count + ")"
                                                color: projectSection.detailSubTab === modelData.key ? theme.titleInk : "#6B7280"
                                                font.family: theme.uiFont
                                                font.pixelSize: 13
                                                font.weight: projectSection.detailSubTab === modelData.key ? 700 : 500
                                            }

                                            Rectangle {
                                                visible: projectSection.detailSubTab === modelData.key
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                anchors.bottom: parent.bottom
                                                height: 2
                                                radius: 1
                                                color: theme.titleInk
                                            }

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: projectSection.detailSubTab = modelData.key
                                            }
                                        }
                                    }

                                    Item {
                                        Layout.fillWidth: true
                                    }
                                }

                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 1
                                    color: theme.panelLine
                                }
                            }

                            ColumnLayout {
                                visible: projectSection.detailSubTab === "versions"
                                Layout.fillWidth: true
                                spacing: 8

                                Text {
                                    visible: (theme.projectDraft.projectVersions || []).length === 0
                                    text: "暂无版本记录"
                                    color: projectSection.theme.labelInk
                                    font.family: projectSection.theme.uiFont
                                    font.pixelSize: 11
                                }

                                Item {
                                    visible: (theme.projectDraft.projectVersions || []).length > 0
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: Math.min(324, 43 + (theme.projectDraft.projectVersions || []).length * 52)
                                    clip: true

                                    Item {
                                        id: projectVersionTable
                                        anchors.fill: parent
                                        clip: true
                                        property real sidePadding: 18
                                        property real columnSpacing: 12
                                        property real tableInnerWidth: Math.max(760, width - sidePadding * 2 - columnSpacing * 3)
                                        property real tableContentWidth: tableInnerWidth + sidePadding * 2 + columnSpacing * 3
                                        property real issueProductColumnWidth: Math.round(tableInnerWidth * 0.36)
                                        property real environmentColumnWidth: Math.round(tableInnerWidth * 0.18)
                                        property real versionColumnWidth: Math.round(tableInnerWidth * 0.26)
                                        property real updatedColumnWidth: Math.round(tableInnerWidth * 0.20)

                                        Flickable {
                                            id: projectVersionTableHorizontalFlickable
                                            anchors.fill: parent
                                            clip: true
                                            boundsBehavior: Flickable.StopAtBounds
                                            contentWidth: projectVersionTableColumn.width
                                            contentHeight: height
                                            flickableDirection: Flickable.HorizontalFlick
                                            interactive: contentWidth > width

                                            ScrollBar.horizontal: ScrollBar {
                                                policy: ScrollBar.AsNeeded
                                            }

                                            Column {
                                                id: projectVersionTableColumn
                                                width: Math.max(projectVersionTableHorizontalFlickable.width, projectVersionTable.tableContentWidth)
                                                spacing: 0

                                                Rectangle {
                                                    id: projectVersionTableHeader
                                                    width: parent.width
                                                    height: 42
                                                    color: "transparent"

                                                    RowLayout {
                                                        anchors.fill: parent
                                                        anchors.leftMargin: projectVersionTable.sidePadding
                                                        anchors.rightMargin: projectVersionTable.sidePadding
                                                        spacing: projectVersionTable.columnSpacing

                                                        Text {
                                                            Layout.preferredWidth: projectVersionTable.issueProductColumnWidth
                                                            text: "问题所属产品"
                                                            color: "#7A857F"
                                                            font.family: theme.uiFont
                                                            font.pixelSize: 11
                                                            font.weight: 600
                                                            verticalAlignment: Text.AlignVCenter
                                                        }

                                                        Text {
                                                            Layout.preferredWidth: projectVersionTable.environmentColumnWidth
                                                            text: "环境"
                                                            color: "#7A857F"
                                                            font.family: theme.uiFont
                                                            font.pixelSize: 11
                                                            font.weight: 600
                                                            verticalAlignment: Text.AlignVCenter
                                                        }

                                                        Text {
                                                            Layout.preferredWidth: projectVersionTable.versionColumnWidth
                                                            text: "版本"
                                                            color: "#7A857F"
                                                            font.family: theme.uiFont
                                                            font.pixelSize: 11
                                                            font.weight: 600
                                                            verticalAlignment: Text.AlignVCenter
                                                        }

                                                        Text {
                                                            Layout.preferredWidth: projectVersionTable.updatedColumnWidth
                                                            text: "更新时间"
                                                            color: "#7A857F"
                                                            font.family: theme.uiFont
                                                            font.pixelSize: 11
                                                            font.weight: 600
                                                            horizontalAlignment: Text.AlignHCenter
                                                            verticalAlignment: Text.AlignVCenter
                                                        }
                                                    }
                                                }

                                                Rectangle {
                                                    width: parent.width
                                                    height: 1
                                                    color: theme.panelLine
                                                }

                                                ListView {
                                                    id: projectVersionTableView
                                                    width: parent.width
                                                    height: Math.max(0, projectVersionTableHorizontalFlickable.height - projectVersionTableHeader.height - 1)
                                                    clip: true
                                                    spacing: 0
                                                    model: theme.projectDraft.projectVersions || []
                                                    boundsBehavior: Flickable.StopAtBounds

                                                    delegate: Item {
                                                        required property var modelData

                                                        width: projectVersionTableView.width
                                                        height: 52

                                                        RowLayout {
                                                            anchors.fill: parent
                                                            anchors.leftMargin: projectVersionTable.sidePadding
                                                            anchors.rightMargin: projectVersionTable.sidePadding
                                                            spacing: projectVersionTable.columnSpacing

                                                            SelectableText {
                                                                Layout.preferredWidth: projectVersionTable.issueProductColumnWidth
                                                                text: modelData.issueProduct || "未填写"
                                                                color: theme.titleInk
                                                                font.family: theme.uiFont
                                                                font.pixelSize: 12
                                                                font.weight: 500
                                                                verticalAlignment: Text.AlignVCenter
                                                                wrapMode: TextEdit.NoWrap
                                                                clip: true
                                                            }

                                                            SelectableText {
                                                                Layout.preferredWidth: projectVersionTable.environmentColumnWidth
                                                                text: modelData.environment || "未填写"
                                                                color: theme.bodyInk
                                                                font.family: theme.uiFont
                                                                font.pixelSize: 12
                                                                verticalAlignment: Text.AlignVCenter
                                                                wrapMode: TextEdit.NoWrap
                                                                clip: true
                                                            }

                                                            SelectableText {
                                                                Layout.preferredWidth: projectVersionTable.versionColumnWidth
                                                                text: modelData.version || "未填写"
                                                                color: theme.bodyInk
                                                                font.family: theme.uiFont
                                                                font.pixelSize: 12
                                                                verticalAlignment: Text.AlignVCenter
                                                                wrapMode: TextEdit.NoWrap
                                                                clip: true
                                                            }

                                                            SelectableText {
                                                                Layout.preferredWidth: projectVersionTable.updatedColumnWidth
                                                                text: modelData.updatedAtLabel || "未更新"
                                                                color: "#6D7885"
                                                                font.family: theme.uiFont
                                                                font.pixelSize: 12
                                                                horizontalAlignment: Text.AlignHCenter
                                                                verticalAlignment: Text.AlignVCenter
                                                                wrapMode: TextEdit.NoWrap
                                                                clip: true
                                                            }
                                                        }

                                                        Rectangle {
                                                            visible: index < (theme.projectDraft.projectVersions || []).length - 1
                                                            anchors.bottom: parent.bottom
                                                            anchors.left: parent.left
                                                            anchors.right: parent.right
                                                            anchors.leftMargin: projectVersionTable.sidePadding
                                                            anchors.rightMargin: projectVersionTable.sidePadding
                                                            height: 1
                                                            color: theme.panelLine
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            ColumnLayout {
                                visible: projectSection.detailSubTab === "aliases"
                                Layout.fillWidth: true
                                spacing: 8

                                Text {
                                    visible: theme.projectDraft.aliases.length === 0
                                    text: "暂无群名别名"
                                    color: projectSection.theme.labelInk
                                    font.family: projectSection.theme.uiFont
                                    font.pixelSize: 11
                                }

                                Flow {
                                    Layout.fillWidth: true
                                    width: parent.width
                                    spacing: 8

                                    Repeater {
                                        model: theme.projectDraft.aliases

                                        delegate: ControlPanelChip {
                                            required property var modelData

                                            theme: projectSection.theme
                                            label: theme.projectAliasText(modelData)
                                            onRemoveClicked: theme.removeProjectAlias(theme.projectAliasText(modelData))
                                        }
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10

                                    ControlPanelSettingsInput {
                                        theme: projectSection.theme
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 0
                                        text: theme.projectAliasInput
                                        placeholderText: "输入群名别名"
                                        onTextEdited: theme.projectAliasInput = text
                                        onAccepted: theme.addProjectAlias()
                                    }

                                    ControlPanelPlainButton {
                                        theme: projectSection.theme
                                        Layout.preferredWidth: 92
                                        label: "添加别名"
                                        onClicked: theme.addProjectAlias()
                                    }
                                }
                            }
                        }

                    }
    }
}

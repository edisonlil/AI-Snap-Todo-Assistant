import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: projectSection
    required property var theme

    visible: controlPanelBridge.currentSection === "projects"
    spacing: 0

    ControlPanelSectionCard {
        theme: projectSection.theme
        Layout.fillWidth: true
        implicitHeight: projectManagerContent.implicitHeight + 32
        color: theme.panelBg

        ColumnLayout {
            id: projectManagerContent
            anchors.fill: parent
            anchors.margins: 16
            spacing: 14

            RowLayout {
                visible: theme.projectViewMode === "list"
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

            RowLayout {
                visible: theme.projectViewMode === "list"
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

            Text {
                visible: theme.projectViewMode === "list" && controlPanelBridge.lastProjectImportSummary.length > 0
                Layout.fillWidth: true
                text: controlPanelBridge.lastProjectImportSummary
                color: theme.labelInk
                font.family: theme.uiFont
                font.pixelSize: 11
                wrapMode: Text.Wrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Rectangle {
                    visible: theme.projectViewMode === "list"
                    Layout.fillWidth: true
                    Layout.preferredWidth: 340
                    implicitHeight: 520
                    radius: 18
                    color: theme.panelBg
                    border.width: 1
                    border.color: theme.panelLine

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
                                radius: 14
                                color: currentProject ? theme.accentSoft : theme.panelBg
                                border.width: 1
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

                Rectangle {
                    visible: theme.projectViewMode === "detail"
                    Layout.fillWidth: true
                    implicitHeight: projectFormColumn.implicitHeight + 24
                    radius: 18
                    color: theme.panelBg
                    border.width: 1
                    border.color: theme.panelLine

                    ColumnLayout {
                        id: projectFormColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ControlPanelPlainButton {
                                theme: projectSection.theme
                                label: "返回列表"
                                onClicked: theme.showProjectList()
                            }

                            Item {
                                Layout.fillWidth: true
                            }
                        }

                        Text {
                            text: theme.projectDraft.id.length > 0 ? "编辑项目" : "新建项目"
                            color: theme.titleInk
                            font.family: theme.uiFont
                            font.pixelSize: 14
                            font.weight: 700
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "保存时会校验群名别名冲突，并只补关联未完成且未解决关联状态的待办。"
                            color: theme.labelInk
                            font.family: theme.uiFont
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                text: theme.projectDraft.projectName
                                placeholderText: "项目名称"
                                onTextEdited: theme.updateProjectDraft("projectName", text)
                            }

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                text: theme.projectDraft.taskOrderNo
                                placeholderText: "任务单号"
                                onTextEdited: theme.updateProjectDraft("taskOrderNo", text)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                text: theme.projectDraft.customerName
                                placeholderText: "客户名称"
                                onTextEdited: theme.updateProjectDraft("customerName", text)
                            }

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                text: theme.projectDraft.projectManager
                                placeholderText: "项目经理"
                                onTextEdited: theme.updateProjectDraft("projectManager", text)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                text: theme.projectDraft.productLine
                                placeholderText: "产品线"
                                onTextEdited: theme.updateProjectDraft("productLine", text)
                            }

                            ControlPanelSettingsInput {
                                theme: projectSection.theme
                                Layout.fillWidth: true
                                text: theme.projectDraft.productVersion
                                placeholderText: "产品版本"
                                onTextEdited: theme.updateProjectDraft("productVersion", text)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ControlPanelDateField {
                                Layout.fillWidth: true
                                theme: projectSection.theme
                                text: theme.displayProjectDate(theme.projectDraft.followUpStartedAt)
                                placeholderText: "跟进开始日期"
                                onClicked: controlPanelBridge.chooseProjectDate("followUpStartedAt", theme.projectDraft.followUpStartedAt)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ControlPanelDateField {
                                Layout.fillWidth: true
                                theme: projectSection.theme
                                text: theme.displayProjectDate(theme.projectDraft.supportEndedAt)
                                placeholderText: "过保日期"
                                onClicked: controlPanelBridge.chooseProjectDate("supportEndedAt", theme.projectDraft.supportEndedAt)
                            }
                        }

                        ControlPanelSettingsCombo {
                            theme: projectSection.theme
                            Layout.fillWidth: true
                            model: theme.projectLevelOptions
                            currentIndex: theme.optionIndex(theme.projectLevelOptions, theme.normalizedProjectLevel(theme.projectDraft.projectLevel))
                            onActivated: if (currentIndex >= 0) theme.updateProjectDraft("projectLevel", theme.projectLevelOptions[currentIndex].value)
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
                                text: theme.projectAliasInput
                                placeholderText: "输入群名别名"
                                onTextEdited: theme.projectAliasInput = text
                                onAccepted: theme.addProjectAlias()
                            }

                            ControlPanelPlainButton {
                                theme: projectSection.theme
                                label: "添加别名"
                                onClicked: theme.addProjectAlias()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            ControlPanelPlainButton {
                                theme: projectSection.theme
                                label: "重置"
                                onClicked: theme.startNewProjectDraft()
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            ControlPanelPlainButton {
                                visible: theme.projectDraft.id.length > 0
                                theme: projectSection.theme
                                label: "删除项目"
                                onClicked: theme.deleteCurrentProject()
                            }

                            ControlPanelPlainButton {
                                theme: projectSection.theme
                                label: "保存项目"
                                fillColor: theme.accent
                                inkColor: "#FFFFFF"
                                strokeWidth: 0
                                onClicked: theme.saveCurrentProject()
                            }
                        }
                    }
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: ticketSection
    required property var theme

    visible: controlPanelBridge.currentSection === "tickets"
    spacing: 0

    property var statusOptions: [
        { value: "open", text: "进行中" },
        { value: "done", text: "已完成" },
        { value: "all", text: "全部状态" }
    ]

    function currentStatusValue() {
        var index = ticketStatusCombo.currentIndex
        if (index < 0 || index >= statusOptions.length) {
            return "open"
        }
        return statusOptions[index].value
    }

    component StatusPill: Rectangle {
        required property var theme
        property string label: ""
        property string tone: "default"

        radius: 11
        implicitWidth: pillText.implicitWidth + 18
        implicitHeight: 24
        border.width: 1
        color: tone === "matched" ? "#E7F5ED"
             : tone === "warning" ? "#FFF4E8"
             : tone === "done" ? "#EEF4FF"
             : tone === "open" ? "#EAF7F1"
             : "#F8F1E7"
        border.color: tone === "matched" ? "#B6DEC5"
                    : tone === "warning" ? "#F2C998"
                    : tone === "done" ? "#C8D8FF"
                    : tone === "open" ? "#B9DCCB"
                    : theme.panelLine

        Text {
            id: pillText
            anchors.centerIn: parent
            text: parent.label
            color: tone === "warning" ? "#9A4B00"
                 : tone === "done" ? "#315AA6"
                 : tone === "matched" || tone === "open" ? "#17663A"
                 : theme.bodyInk
            font.family: theme.uiFont
            font.pixelSize: 11
            font.weight: 700
        }
    }

    ControlPanelSectionCard {
        theme: ticketSection.theme
        Layout.fillWidth: true
        implicitHeight: ticketContent.implicitHeight + 32
        color: "#F6F0E6"

        ColumnLayout {
            id: ticketContent
            anchors.fill: parent
            anchors.margins: 16
            spacing: 14

            RowLayout {
                visible: controlPanelBridge.selectedTicket.id.length === 0
                Layout.fillWidth: true
                spacing: 10

                ControlPanelSettingsInput {
                    id: ticketSearchInput
                    theme: ticketSection.theme
                    Layout.fillWidth: true
                    text: controlPanelBridge.ticketQuery
                    placeholderText: "搜索标题 / 摘要 / 群名 / 项目名 / 工单类型"
                    onTextEdited: controlPanelBridge.listTickets(text, ticketSection.currentStatusValue())
                }

                ControlPanelSettingsCombo {
                    id: ticketStatusCombo
                    theme: ticketSection.theme
                    Layout.preferredWidth: 160
                    model: ticketSection.statusOptions
                    currentIndex: ticketSection.theme.optionIndex(ticketSection.statusOptions, controlPanelBridge.ticketStatusFilter)
                    onActivated: if (currentIndex >= 0) controlPanelBridge.listTickets(ticketSearchInput.text, ticketSection.statusOptions[currentIndex].value)
                }
            }

            Text {
                visible: controlPanelBridge.selectedTicket.id.length === 0 && controlPanelBridge.tickets.length === 0
                Layout.fillWidth: true
                text: "当前筛选条件下没有工单。"
                color: theme.labelInk
                font.family: theme.uiFont
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }

            Rectangle {
                visible: controlPanelBridge.selectedTicket.id.length === 0 && controlPanelBridge.tickets.length > 0
                Layout.fillWidth: true
                implicitHeight: 560
                radius: 18
                color: "#FFF9F1"
                border.width: 1
                border.color: theme.panelLine

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "工单列表"
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
                        model: controlPanelBridge.tickets

                        delegate: Rectangle {
                            width: ListView.view.width
                            height: ticketInfoColumn.implicitHeight + 20
                            radius: 14
                            color: "#FFFCF7"
                            border.width: 1
                            border.color: theme.panelLine

                            Column {
                                id: ticketInfoColumn
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 6

                                Row {
                                    width: parent.width
                                    spacing: 8

                                    Text {
                                        width: parent.width - statusBadge.width - projectBadge.width - (parent.spacing * 2)
                                        text: modelData.title
                                        color: theme.titleInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 13
                                        font.weight: 700
                                        elide: Text.ElideRight
                                    }

                                    StatusPill {
                                        id: statusBadge
                                        theme: ticketSection.theme
                                        label: modelData.statusLabel
                                        tone: modelData.statusTone
                                    }

                                    StatusPill {
                                        id: projectBadge
                                        theme: ticketSection.theme
                                        label: modelData.projectStatusLabel
                                        tone: modelData.projectStatusTone
                                    }
                                }

                                Text {
                                    width: parent.width
                                    text: (modelData.summary || "").length > 0 ? modelData.summary : "暂无摘要"
                                    color: theme.bodyInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: "群名: " + (modelData.groupName || "未填写") + " / 环境: " + (modelData.environment || "未填写")
                                    color: theme.bodyInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: "工单类型: " + (modelData.ticketType || "未填写")
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.projectStatusDetail
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: "最近更新: " + (modelData.updatedAtLabel || "未知") + " / 跟进: " + modelData.timelineCount + " 条"
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: controlPanelBridge.openTicketDetail(modelData.id)
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                visible: controlPanelBridge.selectedTicket.id.length > 0
                Layout.fillWidth: true
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    ControlPanelPlainButton {
                        theme: ticketSection.theme
                        label: "返回列表"
                        onClicked: controlPanelBridge.backToTicketList()
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: 18
                    color: "#FFF9F1"
                    border.width: 1
                    border.color: theme.panelLine
                    implicitHeight: ticketDetailColumn.implicitHeight + 24

                    ColumnLayout {
                        id: ticketDetailColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                text: controlPanelBridge.selectedTicket.title || "未分类任务"
                                color: theme.titleInk
                                font.family: theme.uiFont
                                font.pixelSize: 15
                                font.weight: 700
                                wrapMode: Text.Wrap
                            }

                            StatusPill {
                                theme: ticketSection.theme
                                label: controlPanelBridge.selectedTicket.statusLabel
                                tone: controlPanelBridge.selectedTicket.statusTone
                            }

                            StatusPill {
                                theme: ticketSection.theme
                                label: controlPanelBridge.selectedTicket.projectStatusLabel
                                tone: controlPanelBridge.selectedTicket.projectStatusTone
                            }
                        }

                        Text {
                            text: "摘要"
                            color: theme.titleInk
                            font.family: theme.uiFont
                            font.pixelSize: 13
                            font.weight: 700
                        }

                        Text {
                            Layout.fillWidth: true
                            text: (controlPanelBridge.selectedTicket.currentSummary || "").length > 0 ? controlPanelBridge.selectedTicket.currentSummary : "暂无摘要"
                            color: theme.bodyInk
                            font.family: theme.uiFont
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        Flow {
                            Layout.fillWidth: true
                            width: parent.width
                            spacing: 8

                            StatusPill {
                                theme: ticketSection.theme
                                label: controlPanelBridge.selectedTicket.ticketType || "未填写工单类型"
                                tone: "default"
                            }

                            StatusPill {
                                theme: ticketSection.theme
                                label: "群名: " + (controlPanelBridge.selectedTicket.groupName || "未填写")
                                tone: "default"
                            }

                            StatusPill {
                                theme: ticketSection.theme
                                label: "环境: " + (controlPanelBridge.selectedTicket.environment || "未填写")
                                tone: "default"
                            }

                            StatusPill {
                                theme: ticketSection.theme
                                label: "创建: " + (controlPanelBridge.selectedTicket.createdAtLabel || "未知")
                                tone: "default"
                            }

                            StatusPill {
                                theme: ticketSection.theme
                                label: "更新: " + (controlPanelBridge.selectedTicket.updatedAtLabel || "未知")
                                tone: "default"
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            radius: 16
                            color: "#FFFEFC"
                            border.width: 1
                            border.color: theme.panelLine
                            implicitHeight: projectInfoColumn.implicitHeight + 20

                            ColumnLayout {
                                id: projectInfoColumn
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 6

                                Text {
                                    text: "项目关联"
                                    color: theme.titleInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 13
                                    font.weight: 700
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: controlPanelBridge.selectedTicket.projectStatusDetail
                                    color: theme.bodyInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    visible: (controlPanelBridge.selectedTicket.projectName || "").length > 0
                                    Layout.fillWidth: true
                                    text: "项目: " + controlPanelBridge.selectedTicket.projectName + ((controlPanelBridge.selectedTicket.taskOrderNo || "").length > 0 ? " / " + controlPanelBridge.selectedTicket.taskOrderNo : "")
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    visible: (controlPanelBridge.selectedTicket.productLine || "").length > 0 || (controlPanelBridge.selectedTicket.productVersion || "").length > 0
                                    Layout.fillWidth: true
                                    text: "产品: " + (controlPanelBridge.selectedTicket.productLine || "未填写") + " / 版本: " + (controlPanelBridge.selectedTicket.productVersion || "未填写")
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    visible: (controlPanelBridge.selectedTicket.projectManager || "").length > 0
                                    Layout.fillWidth: true
                                    text: "项目经理: " + controlPanelBridge.selectedTicket.projectManager
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        Text {
                            text: "历史跟进"
                            color: theme.titleInk
                            font.family: theme.uiFont
                            font.pixelSize: 13
                            font.weight: 700
                        }

                        Repeater {
                            model: controlPanelBridge.selectedTicket.timeline

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                radius: 16
                                color: "#FFFEFC"
                                border.width: 1
                                border.color: theme.panelLine
                                implicitHeight: timelineColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: timelineColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        Text {
                                            text: modelData.timestampLabel || modelData.timestamp
                                            color: theme.titleInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 12
                                            font.weight: 700
                                        }

                                        Text {
                                            text: modelData.scenario
                                            color: theme.labelInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 11
                                        }

                                        Item {
                                            Layout.fillWidth: true
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.content
                                        color: theme.bodyInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 12
                                        wrapMode: Text.Wrap
                                    }

                                    Flow {
                                        visible: modelData.attachments.length > 0
                                        Layout.fillWidth: true
                                        width: parent.width
                                        spacing: 8

                                        Repeater {
                                            model: modelData.attachments

                                            delegate: Rectangle {
                                                radius: 14
                                                color: "#F4F7FB"
                                                border.width: 1
                                                border.color: "#D8E1EF"
                                                width: attachmentText.implicitWidth + 24
                                                height: 30

                                                Text {
                                                    id: attachmentText
                                                    anchors.centerIn: parent
                                                    text: modelData.name + " (" + modelData.sizeLabel + ")"
                                                    color: theme.bodyInk
                                                    font.family: theme.uiFont
                                                    font.pixelSize: 11
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

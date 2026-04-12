import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: ticketSection
    required property var theme

    visible: controlPanelBridge.currentSection === "tickets"
    spacing: 0
    readonly property bool compactDetailLayout: ticketSection.width < 920

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
                spacing: 18

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
                    radius: 22
                    color: "#FFFCF8"
                    border.width: 1
                    border.color: "#ECE4D8"
                    implicitHeight: ticketDetailColumn.implicitHeight + 40

                    ColumnLayout {
                        id: ticketDetailColumn
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 28

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                Layout.fillWidth: true
                                text: controlPanelBridge.selectedTicket.title || "未分类任务"
                                color: theme.titleInk
                                font.family: theme.uiFont
                                font.pixelSize: 25
                                font.weight: 700
                                wrapMode: Text.Wrap
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: 8

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

                                StatusPill {
                                    theme: ticketSection.theme
                                    label: controlPanelBridge.selectedTicket.ticketType || "未填写工单类型"
                                    tone: "default"
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                text: (controlPanelBridge.selectedTicket.currentSummary || "").length > 0 ? controlPanelBridge.selectedTicket.currentSummary : "暂无摘要"
                                color: theme.labelInk
                                font.family: theme.uiFont
                                font.pixelSize: 13
                                lineHeight: 1.35
                                wrapMode: Text.Wrap
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 1
                            color: "#E9E0D3"
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: ticketSection.compactDetailLayout ? 1 : 2
                            columnSpacing: ticketSection.compactDetailLayout ? 0 : 40
                            rowSpacing: 24

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                spacing: 18

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text {
                                        text: "历史跟进"
                                        color: theme.titleInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 14
                                        font.weight: 700
                                    }

                                    Text {
                                        text: controlPanelBridge.selectedTicket.timelineCount + " 条记录，按最近更新排序"
                                        color: theme.labelInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 11
                                    }
                                }

                                Repeater {
                                    model: controlPanelBridge.selectedTicket.timeline

                                    delegate: Item {
                                        Layout.fillWidth: true
                                        implicitHeight: timelineEntryRow.implicitHeight

                                        RowLayout {
                                            id: timelineEntryRow
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            spacing: 16

                                            Item {
                                                Layout.preferredWidth: 16
                                                Layout.alignment: Qt.AlignTop
                                                implicitWidth: 16
                                                implicitHeight: timelineEntryContent.implicitHeight

                                                Rectangle {
                                                    x: 4
                                                    y: 8
                                                    width: 8
                                                    height: 8
                                                    radius: 4
                                                    color: theme.accent
                                                }

                                                Rectangle {
                                                    visible: index < controlPanelBridge.selectedTicket.timeline.length - 1
                                                    x: 7
                                                    y: 24
                                                    width: 2
                                                    height: Math.max(0, parent.height - 24)
                                                    radius: 1
                                                    color: "#E4DCCF"
                                                }
                                            }

                                            ColumnLayout {
                                                id: timelineEntryContent
                                                Layout.fillWidth: true
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
                                                    lineHeight: 1.45
                                                    wrapMode: Text.Wrap
                                                }

                                                Flow {
                                                    visible: modelData.attachments.length > 0
                                                    Layout.fillWidth: true
                                                    spacing: 8

                                                    Repeater {
                                                        model: modelData.attachments

                                                        delegate: Rectangle {
                                                            radius: 14
                                                            color: "#F6F2EA"
                                                            border.width: 1
                                                            border.color: "#E5DCD0"
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

                                                Rectangle {
                                                    visible: index < controlPanelBridge.selectedTicket.timeline.length - 1
                                                    Layout.fillWidth: true
                                                    implicitHeight: 1
                                                    color: "#EEE5D8"
                                                    Layout.topMargin: 8
                                                }
                                            }
                                        }
                                    }
                                }

                                Text {
                                    visible: controlPanelBridge.selectedTicket.timeline.length === 0
                                    Layout.fillWidth: true
                                    text: "暂无跟进记录"
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 12
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredWidth: 288
                                Layout.alignment: Qt.AlignTop
                                radius: 18
                                color: "#FBF8F2"
                                border.width: 1
                                border.color: "#EEE4D8"
                                implicitHeight: detailSidebar.implicitHeight + 28

                                ColumnLayout {
                                    id: detailSidebar
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 18

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 12

                                        Text {
                                            text: "基本信息"
                                            color: theme.titleInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 13
                                            font.weight: 700
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 10

                                            Text {
                                                text: "群名"
                                                color: theme.labelInk
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: controlPanelBridge.selectedTicket.groupName || "未填写"
                                                color: theme.bodyInk
                                                font.family: theme.uiFont
                                                font.pixelSize: 12
                                                wrapMode: Text.Wrap
                                            }

                                            Text {
                                                text: "环境"
                                                color: theme.labelInk
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: controlPanelBridge.selectedTicket.environment || "未填写"
                                                color: theme.bodyInk
                                                font.family: theme.uiFont
                                                font.pixelSize: 12
                                                wrapMode: Text.Wrap
                                            }

                                            Text {
                                                text: "创建时间"
                                                color: theme.labelInk
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: controlPanelBridge.selectedTicket.createdAtLabel || "未知"
                                                color: theme.bodyInk
                                                font.family: theme.uiFont
                                                font.pixelSize: 12
                                                wrapMode: Text.Wrap
                                            }

                                            Text {
                                                text: "最近更新"
                                                color: theme.labelInk
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: controlPanelBridge.selectedTicket.updatedAtLabel || "未知"
                                                color: theme.bodyInk
                                                font.family: theme.uiFont
                                                font.pixelSize: 12
                                                wrapMode: Text.Wrap
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 1
                                        color: "#E9E0D3"
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 12

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
                                            lineHeight: 1.35
                                            wrapMode: Text.Wrap
                                        }

                                        Text {
                                            visible: (controlPanelBridge.selectedTicket.projectName || "").length > 0
                                            text: "项目"
                                            color: theme.labelInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 11
                                            font.weight: 600
                                        }

                                        Text {
                                            visible: (controlPanelBridge.selectedTicket.projectName || "").length > 0
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.selectedTicket.projectName + ((controlPanelBridge.selectedTicket.taskOrderNo || "").length > 0 ? " / " + controlPanelBridge.selectedTicket.taskOrderNo : "")
                                            color: theme.bodyInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.Wrap
                                        }

                                        Text {
                                            text: "产品线"
                                            color: theme.labelInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 11
                                            font.weight: 600
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.selectedTicket.productLine || "未填写"
                                            color: theme.bodyInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.Wrap
                                        }

                                        Text {
                                            text: "工单版本"
                                            color: theme.labelInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 11
                                            font.weight: 600
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 8

                                            ControlPanelSettingsInput {
                                                id: ticketVersionInput
                                                theme: ticketSection.theme
                                                Layout.fillWidth: true
                                                text: controlPanelBridge.selectedTicket.ticketVersion || ""
                                                placeholderText: "工单版本"
                                            }

                                            ControlPanelPlainButton {
                                                theme: ticketSection.theme
                                                label: "保存"
                                                onClicked: controlPanelBridge.saveSelectedTicketVersion(ticketVersionInput.text)
                                            }
                                        }

                                        Text {
                                            visible: (controlPanelBridge.selectedTicket.projectSnapshotVersion || "").length > 0
                                                && (controlPanelBridge.selectedTicket.projectSnapshotVersion || "") !== (controlPanelBridge.selectedTicket.ticketVersion || "")
                                            text: "关联项目快照版本"
                                            color: theme.labelInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 11
                                            font.weight: 600
                                        }

                                        Text {
                                            visible: (controlPanelBridge.selectedTicket.projectSnapshotVersion || "").length > 0
                                                && (controlPanelBridge.selectedTicket.projectSnapshotVersion || "") !== (controlPanelBridge.selectedTicket.ticketVersion || "")
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.selectedTicket.projectSnapshotVersion
                                            color: theme.bodyInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.Wrap
                                        }

                                        Text {
                                            visible: (controlPanelBridge.selectedTicket.projectManager || "").length > 0
                                            text: "项目经理"
                                            color: theme.labelInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 11
                                            font.weight: 600
                                        }

                                        Text {
                                            visible: (controlPanelBridge.selectedTicket.projectManager || "").length > 0
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.selectedTicket.projectManager
                                            color: theme.bodyInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.Wrap
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

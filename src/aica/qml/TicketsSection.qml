import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: ticketSection
    required property var theme

    visible: controlPanelBridge.currentSection === "tickets"
    spacing: 0
    readonly property int detailGridColumns: ticketSection.width < 720 ? 1 : ticketSection.width < 1080 ? 2 : ticketSection.width < 1440 ? 3 : 4
    readonly property bool compactDetailLayout: ticketSection.width < 920
    property string ticketFieldEditingName: ""
    property string ticketFieldSavingName: ""
    property string ticketFieldDraft: ""
    property string ticketFieldOriginal: ""
    property string ticketFieldPending: ""

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

    function currentTicketFieldValue(fieldName) {
        if (fieldName === "ticketVersion") {
            return controlPanelBridge.selectedTicket.ticketVersion || ""
        }
        if (fieldName === "featurePoint") {
            return controlPanelBridge.selectedTicket.featurePoint || ""
        }
        if (fieldName === "rootCause") {
            return controlPanelBridge.selectedTicket.rootCause || ""
        }
        if (fieldName === "rootCauseDesc") {
            return controlPanelBridge.selectedTicket.rootCauseDesc || ""
        }
        return ""
    }

    function syncTicketFieldState() {
        var currentName = ticketFieldSavingName || ticketFieldEditingName
        if (!currentName || ticketFieldEditingName.length > 0) {
            return
        }
        var currentValue = currentTicketFieldValue(currentName)
        if (currentValue === ticketFieldPending || currentValue === ticketFieldOriginal) {
            ticketFieldEditingName = ""
            ticketFieldSavingName = ""
            ticketFieldDraft = currentValue
            ticketFieldOriginal = currentValue
            ticketFieldPending = ""
        }
    }

    function beginTicketFieldEdit(fieldName) {
        if (ticketFieldSavingName.length > 0) {
            return
        }
        ticketFieldEditingName = fieldName
        ticketFieldOriginal = currentTicketFieldValue(fieldName)
        ticketFieldDraft = ticketFieldOriginal
        ticketFieldPending = ""
    }

    function cancelTicketFieldEdit() {
        ticketFieldEditingName = ""
        ticketFieldSavingName = ""
        ticketFieldPending = ""
        ticketFieldDraft = ticketFieldOriginal
    }

    function commitTicketFieldEdit(saveAction) {
        if (!ticketFieldEditingName || ticketFieldSavingName.length > 0) {
            return
        }
        var nextValue = (ticketFieldDraft || "").trim()
        if (nextValue === ticketFieldOriginal) {
            ticketFieldEditingName = ""
            return
        }
        ticketFieldPending = nextValue
        ticketFieldSavingName = ticketFieldEditingName
        ticketFieldEditingName = ""
        Qt.callLater(function() {
            if (ticketFieldSavingName.length === 0 || ticketFieldPending !== nextValue) {
                return
            }
            if (saveAction === "ticket_version") {
                controlPanelBridge.saveSelectedTicketVersion(nextValue)
            } else {
                controlPanelBridge.saveSelectedTicketField(saveAction, nextValue)
            }
        })
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

    component DetailField: Rectangle {
        id: fieldRoot
        required property var theme
        property string label: ""
        property string value: ""
        property string placeholderText: "未填写"
        property string draftValue: ""
        property bool editable: false
        property bool editing: false
        property bool saving: false
        property bool multiline: false
        property bool compact: false
        signal clicked
        signal accepted(string value)
        signal canceled

        radius: 0
        color: "transparent"
        border.width: 0
        implicitHeight: fieldColumn.implicitHeight + 14

        ColumnLayout {
            id: fieldColumn
            anchors.fill: parent
            anchors.leftMargin: 6
            anchors.rightMargin: 6
            anchors.topMargin: 4
            anchors.bottomMargin: 10
            spacing: 5

            Text {
                Layout.fillWidth: true
                text: fieldRoot.label
                color: theme.labelInk
                font.family: theme.uiFont
                font.pixelSize: 10
                font.weight: 500
                elide: Text.ElideRight
                opacity: 0.72
            }

            Item {
                Layout.fillWidth: true
                implicitHeight: fieldValueRow.implicitHeight

                RowLayout {
                    id: fieldValueRow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    spacing: 8

                    BusyIndicator {
                        visible: fieldRoot.saving
                        running: fieldRoot.saving
                        Layout.preferredWidth: 16
                        Layout.preferredHeight: 16
                    }

                    ControlPanelSettingsInput {
                        id: inlineEditor
                        visible: fieldRoot.editable && fieldRoot.editing
                        theme: fieldRoot.theme
                        Layout.fillWidth: true
                        text: fieldRoot.draftValue
                        placeholderText: fieldRoot.placeholderText
                        leftPadding: 0
                        rightPadding: 0
                        topPadding: 0
                        bottomPadding: 8
                        background: Rectangle {
                            color: "transparent"
                            border.width: 0

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 1
                                color: inlineEditor.activeFocus ? fieldRoot.theme.accent : "#D8CCBE"
                                opacity: inlineEditor.activeFocus ? 1 : 0.9
                            }
                        }

                        onTextEdited: fieldRoot.draftValue = text
                        onAccepted: fieldRoot.accepted(fieldRoot.draftValue)
                        Keys.onEscapePressed: fieldRoot.canceled()
                    }

                    Item {
                        visible: !fieldRoot.editing
                        Layout.fillWidth: true
                        implicitHeight: fieldText.implicitHeight + (fieldRoot.multiline ? 4 : 0)

                        Text {
                            id: fieldText
                            anchors.left: parent.left
                            anchors.right: fieldAction.left
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.rightMargin: 10
                            text: fieldRoot.value.length > 0 ? fieldRoot.value : fieldRoot.placeholderText
                            color: fieldRoot.value.length > 0 ? theme.titleInk : "#A2907A"
                            font.family: theme.uiFont
                            font.pixelSize: fieldRoot.compact ? 12 : 13
                            font.weight: fieldRoot.value.length > 0 ? 500 : 400
                            wrapMode: fieldRoot.multiline ? Text.Wrap : Text.NoWrap
                            elide: fieldRoot.multiline ? Text.ElideNone : Text.ElideRight
                        }

                        Text {
                            id: fieldAction
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            visible: fieldRoot.editable && fieldHover.containsMouse && !fieldRoot.saving
                            text: "✎"
                            color: theme.accent
                            font.family: theme.uiFont
                            font.pixelSize: 11
                            opacity: 0.75
                        }

                        MouseArea {
                            id: fieldHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: fieldRoot.editable && !fieldRoot.saving ? Qt.PointingHandCursor : Qt.ArrowCursor
                            enabled: fieldRoot.editable && !fieldRoot.saving
                            onClicked: fieldRoot.clicked()
                        }
                    }

                    RowLayout {
                        visible: fieldRoot.editable && fieldRoot.editing
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 10

                        Text {
                            text: "保存"
                            color: fieldRoot.theme.accent
                            font.family: fieldRoot.theme.uiFont
                            font.pixelSize: 11
                            font.weight: 600

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: fieldRoot.accepted(fieldRoot.draftValue)
                            }
                        }

                        Text {
                            text: "取消"
                            color: fieldRoot.theme.labelInk
                            font.family: fieldRoot.theme.uiFont
                            font.pixelSize: 11
                            font.weight: 500
                            opacity: 0.88

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: fieldRoot.canceled()
                            }
                        }
                    }
                }

                Rectangle {
                    visible: !fieldRoot.editing
                    Layout.fillWidth: true
                    implicitHeight: 1
                    color: "#E8DFD2"
                    opacity: 0.85
                }
            }
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

                Connections {
                    target: controlPanelBridge
                    function onDataChanged() {
                        ticketSection.syncTicketFieldState()
                    }
                }

                Component.onCompleted: ticketSection.syncTicketFieldState()

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
                            columns: ticketSection.detailGridColumns
                            columnSpacing: 12
                            rowSpacing: 12

                            ColumnLayout {
                                Layout.row: 1
                                Layout.columnSpan: ticketSection.detailGridColumns
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

                            Item {
                                Layout.row: 0
                                Layout.columnSpan: ticketSection.detailGridColumns
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                implicitHeight: detailSidebar.implicitHeight + 18

                                ColumnLayout {
                                    id: detailSidebar
                                    anchors.fill: parent
                                    anchors.topMargin: 4
                                    anchors.bottomMargin: 4
                                    spacing: 10

                                    Text {
                                        Layout.fillWidth: true
                                        text: "关键信息"
                                        color: theme.titleInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 14
                                        font.weight: 700
                                    }

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: ticketSection.detailGridColumns
                                        columnSpacing: 10
                                        rowSpacing: 8

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            Layout.columnSpan: ticketSection.detailGridColumns
                                            label: "项目关联"
                                            value: controlPanelBridge.selectedTicket.projectStatusDetail
                                            placeholderText: "暂无项目关联信息"
                                            multiline: true
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "群名"
                                            value: controlPanelBridge.selectedTicket.groupName
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "环境"
                                            value: controlPanelBridge.selectedTicket.environment
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "工单类型"
                                            value: controlPanelBridge.selectedTicket.ticketType
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "产品线"
                                            value: controlPanelBridge.selectedTicket.productLine
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "\u7248\u672c\u53f7"
                                            value: ticketSection.ticketFieldEditingName === "ticketVersion" ? ticketSection.ticketFieldDraft : controlPanelBridge.selectedTicket.ticketVersion
                                            placeholderText: "\u672a\u586b\u5199"
                                            editable: true
                                            editing: ticketSection.ticketFieldEditingName === "ticketVersion"
                                            saving: ticketSection.ticketFieldSavingName === "ticketVersion"
                                            compact: ticketSection.detailGridColumns === 1
                                            draftValue: ticketSection.ticketFieldDraft
                                            onClicked: ticketSection.beginTicketFieldEdit("ticketVersion")
                                            onAccepted: function(value) {
                                                ticketSection.ticketFieldDraft = value
                                                ticketSection.commitTicketFieldEdit("ticket_version")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit()
                                        }
                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "\u529f\u80fd\u70b9"
                                            value: ticketSection.ticketFieldEditingName === "featurePoint" ? ticketSection.ticketFieldDraft : controlPanelBridge.selectedTicket.featurePoint
                                            placeholderText: "\u672a\u751f\u6210"
                                            editable: true
                                            editing: ticketSection.ticketFieldEditingName === "featurePoint"
                                            saving: ticketSection.ticketFieldSavingName === "featurePoint"
                                            compact: ticketSection.detailGridColumns === 1
                                            draftValue: ticketSection.ticketFieldDraft
                                            onClicked: ticketSection.beginTicketFieldEdit("featurePoint")
                                            onAccepted: function(value) {
                                                ticketSection.ticketFieldDraft = value
                                                ticketSection.commitTicketFieldEdit("feature_point")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit()
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "\u95ee\u9898\u6839\u56e0"
                                            value: ticketSection.ticketFieldEditingName === "rootCause" ? ticketSection.ticketFieldDraft : controlPanelBridge.selectedTicket.rootCause
                                            placeholderText: "\u672a\u751f\u6210"
                                            editable: true
                                            editing: ticketSection.ticketFieldEditingName === "rootCause"
                                            saving: ticketSection.ticketFieldSavingName === "rootCause"
                                            compact: ticketSection.detailGridColumns === 1
                                            draftValue: ticketSection.ticketFieldDraft
                                            onClicked: ticketSection.beginTicketFieldEdit("rootCause")
                                            onAccepted: function(value) {
                                                ticketSection.ticketFieldDraft = value
                                                ticketSection.commitTicketFieldEdit("root_cause")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit()
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "项目经理"
                                            value: controlPanelBridge.selectedTicket.projectManager
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "创建时间"
                                            value: controlPanelBridge.selectedTicket.createdAtLabel
                                            placeholderText: "未知"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "最近更新"
                                            value: controlPanelBridge.selectedTicket.updatedAtLabel
                                            placeholderText: "未知"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            Layout.columnSpan: ticketSection.detailGridColumns
                                            label: "\u6839\u56e0\u63cf\u8ff0"
                                            value: ticketSection.ticketFieldEditingName === "rootCauseDesc" ? ticketSection.ticketFieldDraft : controlPanelBridge.selectedTicket.rootCauseDesc
                                            placeholderText: "\u672a\u751f\u6210"
                                            multiline: true
                                            editable: true
                                            editing: ticketSection.ticketFieldEditingName === "rootCauseDesc"
                                            saving: ticketSection.ticketFieldSavingName === "rootCauseDesc"
                                            draftValue: ticketSection.ticketFieldDraft
                                            onClicked: ticketSection.beginTicketFieldEdit("rootCauseDesc")
                                            onAccepted: function(value) {
                                                ticketSection.ticketFieldDraft = value
                                                ticketSection.commitTicketFieldEdit("root_cause_desc")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit()
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            Layout.columnSpan: ticketSection.detailGridColumns
                                            visible: (controlPanelBridge.selectedTicket.projectSnapshotVersion || "").length > 0
                                                && (controlPanelBridge.selectedTicket.projectSnapshotVersion || "") !== (controlPanelBridge.selectedTicket.ticketVersion || "")
                                            label: "关联项目快照版本"
                                            value: controlPanelBridge.selectedTicket.projectSnapshotVersion
                                            placeholderText: "未填写"
                                            multiline: true
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

import QtQuick

Rectangle {
    id: root
    width: 396
    height: 760
    color: "transparent"
    focus: true

    readonly property color shellBg: "#F1F0EC"
    readonly property color panelBg: "#F1F0EC"
    readonly property color panelLine: "#E9EDF4"
    readonly property color sectionLine: "#EEF2F6"
    readonly property color titleInk: "#18202E"
    readonly property color bodyInk: "#4A5565"
    readonly property color labelInk: "#9AA4B3"
    readonly property color mutedInk: "#B3BBC8"
    readonly property color fieldBg: "#F7F7F4"
    readonly property color fieldLine: "#E7EDF5"
    readonly property color timelineBg: "#F7F7F4"
    readonly property color accent: "#3D7CFF"
    readonly property color accentTint: "#EEF4FF"
    readonly property string uiFont: "Microsoft YaHei UI"
    readonly property int outerPadding: 24
    readonly property int contentTopPadding: 16
    readonly property int sectionGap: 16
    readonly property int cardRadius: 24
    readonly property int contentWidth: width - outerPadding * 2
    readonly property int fieldGap: 12
    readonly property int fieldWidth: (contentWidth - fieldGap) / 2
    readonly property int fieldCardHeight: 64
    readonly property int fieldTextInset: 16
    readonly property int labelGap: 8
    readonly property int titleWeight: 600
    readonly property int sectionWeight: 600
    readonly property int labelWeight: 500
    readonly property int bodyWeight: 400
    property bool syncingFields: false
    property string activeAttachmentEventId: ""

    function syncFields() {
        syncingFields = true
        activeAttachmentEventId = todoDetailBridge.timelineCount > 0 ? todoDetailBridge.timeline[0].id : ""
        titleEdit.text = todoDetailBridge.title
        groupNameEdit.text = todoDetailBridge.groupName
        environmentEdit.text = todoDetailBridge.environment
        productLineEdit.text = todoDetailBridge.productLine
        ticketTypeEdit.text = todoDetailBridge.ticketType
        summaryEdit.text = todoDetailBridge.currentSummary
        syncingFields = false
    }

    function pushField(name, value) {
        if (!syncingFields) {
            todoDetailBridge.updateField(name, value)
        }
    }

    function markAttachmentTarget(eventId) {
        activeAttachmentEventId = eventId || ""
    }

    function formatFileSize(sizeBytes) {
        var value = Number(sizeBytes || 0)
        if (value <= 0) {
            return ""
        }
        if (value < 1024) {
            return value + " B"
        }
        if (value < 1024 * 1024) {
            return (value / 1024).toFixed(1) + " KB"
        }
        return (value / (1024 * 1024)).toFixed(1) + " MB"
    }

    Connections {
        target: todoDetailBridge
        function onDataChanged() {
            root.syncFields()
        }
        function onTimelineChanged() {
            if (root.activeAttachmentEventId.length === 0 && todoDetailBridge.timelineCount > 0) {
                root.activeAttachmentEventId = todoDetailBridge.timeline[0].id
            }
        }
    }

    Shortcut {
        sequence: StandardKey.Paste
        enabled: root.activeAttachmentEventId.length > 0
        onActivated: todoDetailBridge.requestClipboardImagePaste(root.activeAttachmentEventId)
    }

    Rectangle {
        anchors.fill: parent
        radius: root.cardRadius
        color: root.panelBg
        border.width: 0
        border.color: root.panelLine
        antialiasing: true

        Rectangle {
            anchors.fill: parent
            anchors.margins: 0
            radius: root.cardRadius
            color: root.shellBg
            opacity: 0.2
        }

        Item {
            anchors.fill: parent

            Item {
                id: header
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 54

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    onPressed: function(mouse) {
                        todoDetailBridge.beginPanelDrag(mouse.x, mouse.y)
                    }
                    onPositionChanged: function(mouse) {
                        if (mouse.buttons & Qt.LeftButton) {
                            todoDetailBridge.updatePanelDrag()
                        }
                    }
                    onReleased: todoDetailBridge.finishPanelDrag()
                    onCanceled: todoDetailBridge.finishPanelDrag()
                }

                Text {
                    x: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    text: "待办详情"
                    color: root.titleInk
                    font.family: root.uiFont
                    font.pixelSize: 17
                    font.weight: root.titleWeight
                }

                Row {
                    z: 1
                    anchors.right: parent.right
                    anchors.rightMargin: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 20

                    Rectangle {
                        width: exportText.implicitWidth
                        height: exportText.implicitHeight
                        radius: 0
                        color: "transparent"
                        border.width: 0
                        border.color: root.fieldLine

                        Text {
                            id: exportText
                            anchors.centerIn: parent
                            text: "导出方案"
                            color: root.accent
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.labelWeight
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: todoDetailBridge.exportPlan()
                        }
                    }

                    Rectangle {
                        width: closeText.implicitWidth
                        height: closeText.implicitHeight
                        radius: 0
                        color: "transparent"
                        border.width: 0
                        border.color: root.fieldLine

                        Text {
                            id: closeText
                            anchors.centerIn: parent
                            text: "关闭"
                            color: "#707A89"
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.labelWeight
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: todoDetailBridge.closePanel()
                        }
                    }

                    Rectangle {
                        width: saveText.implicitWidth
                        height: saveText.implicitHeight
                        radius: 0
                        color: "transparent"
                        border.width: 0
                        border.color: root.fieldLine

                        Text {
                            id: saveText
                            anchors.centerIn: parent
                            text: "保存"
                            color: "#586375"
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.labelWeight
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: todoDetailBridge.saveTodo()
                        }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                height: 1
                color: root.sectionLine
            }

            Flickable {
                id: flick
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                anchors.bottom: parent.bottom
                clip: true
                contentWidth: width
                contentHeight: contentColumn.implicitHeight + 24
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: contentColumn
                    x: root.outerPadding
                    y: root.contentTopPadding
                    width: root.contentWidth
                    spacing: root.sectionGap

                    Item {
                        width: parent.width
                        height: Math.max(42, titleEdit.contentHeight + 6)

                        TextEdit {
                            id: titleEdit
                            anchors.fill: parent
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                            textFormat: TextEdit.PlainText
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 16
                            font.weight: root.titleWeight
                            verticalAlignment: TextEdit.AlignTop
                            onTextChanged: root.pushField("title", text)
                        }
                    }

                    Item {
                        width: parent.width
                        height: root.fieldCardHeight * 2 + root.fieldGap

                        Column {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            width: root.fieldWidth
                            spacing: root.fieldGap

                            Rectangle {
                                width: parent.width
                                height: root.fieldCardHeight
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: root.fieldTextInset
                                    y: 13
                                    text: "群聊名称"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: groupNameEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
                                    height: 22
                                    clip: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("group_name", text)
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: root.fieldCardHeight
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: root.fieldTextInset
                                    y: 13
                                    text: "产品线"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: productLineEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
                                    height: 22
                                    clip: true
                                    readOnly: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                }
                            }
                        }

                        Column {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            width: root.fieldWidth
                            spacing: root.fieldGap

                            Rectangle {
                                width: parent.width
                                height: root.fieldCardHeight
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: root.fieldTextInset
                                    y: 13
                                    text: "环境"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: environmentEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
                                    height: 22
                                    clip: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("environment", text)
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: root.fieldCardHeight
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: root.fieldTextInset
                                    y: 13
                                    text: "工单类型"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: ticketTypeEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
                                    height: 22
                                    clip: true
                                    readOnly: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                }
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: root.labelGap

                        Text {
                            text: "当前描述"
                            color: root.labelInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.sectionWeight
                        }

                        Rectangle {
                            width: parent.width
                            height: 120
                            radius: 18
                            color: "#FFFFFF"
                            border.width: 0
                            border.color: root.fieldLine

                            Flickable {
                                id: summaryFlick
                                anchors.fill: parent
                                anchors.margins: 14
                                clip: true
                                contentWidth: width
                                contentHeight: Math.max(height, summaryEdit.contentHeight + 4)
                                boundsBehavior: Flickable.StopAtBounds

                                TextEdit {
                                    id: summaryEdit
                                    width: parent.width
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    textFormat: TextEdit.PlainText
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("current_summary", text)
                                }
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.rightMargin: 8
                                y: 10 + (summaryFlick.contentY / Math.max(1, summaryFlick.contentHeight - summaryFlick.height)) * (parent.height - height - 20)
                                width: 4
                                height: Math.max(28, (summaryFlick.height / Math.max(summaryFlick.contentHeight, 1)) * (parent.height - 20))
                                radius: 2
                                color: "#C3CAD6"
                                visible: summaryFlick.contentHeight > summaryFlick.height + 2
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 10
                        visible: false

                        Text {
                            text: "关键证据"
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 14
                            font.weight: root.sectionWeight
                        }

                        Repeater {
                            model: []

                            delegate: Rectangle {
                                width: contentColumn.width
                                height: Math.max(72, evidenceValue.contentHeight + 40)
                                radius: 16
                                color: "#FFFFFF"
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: 14
                                    y: 12
                                    text: (modelData.label || modelData.type) + " · " + modelData.type
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                Text {
                                    id: evidenceValue
                                    x: 14
                                    y: 30
                                    width: parent.width - 84
                                    wrapMode: Text.Wrap
                                    text: modelData.value
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.bodyWeight
                                }

                                Text {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 14
                                    y: 12
                                    text: "删除"
                                    color: "#E35B66"
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {}
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 48
                        radius: 18
                        color: root.fieldBg
                        border.width: 0
                        border.color: root.fieldLine

                        Text {
                            x: 14
                            anchors.verticalCenter: parent.verticalCenter
                            text: "今天创建: " + todoDetailBridge.createdAtLabel
                            color: root.mutedInk
                            font.family: root.uiFont
                            font.pixelSize: 11
                            font.weight: root.bodyWeight
                        }

                        Text {
                            x: 136
                            anchors.verticalCenter: parent.verticalCenter
                            text: "更新于: " + todoDetailBridge.updatedAtLabel
                            color: root.mutedInk
                            font.family: root.uiFont
                            font.pixelSize: 11
                            font.weight: root.bodyWeight
                        }

                        Item {
                            visible: false
                            anchors.left: parent.left
                            anchors.right: deleteText.left
                            anchors.rightMargin: 18
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.leftMargin: 16

                            Column {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                Text {
                                    text: "今天创建: " + todoDetailBridge.createdAtLabel
                                    color: root.mutedInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.bodyWeight
                                }

                                Text {
                                    text: "更新于: " + todoDetailBridge.updatedAtLabel
                                    color: root.mutedInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.bodyWeight
                                }
                            }
                        }

                        Text {
                            id: deleteText
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.right: completeButton.left
                            anchors.rightMargin: 12
                            text: "删除"
                            color: "#E35B66"
                            font.family: root.uiFont
                            font.pixelSize: 11
                            font.weight: root.labelWeight

                            MouseArea {
                                anchors.fill: parent
                                onClicked: todoDetailBridge.deleteTodo()
                            }
                        }

                        Rectangle {
                            id: completeButton
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            width: 62
                            height: 30
                            radius: 15
                            color: root.accentTint
                            border.width: 0
                            border.color: "transparent"

                            Text {
                                anchors.centerIn: parent
                                text: "完成"
                                color: root.accent
                                font.family: root.uiFont
                                font.pixelSize: 12
                                font.weight: root.labelWeight
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: todoDetailBridge.completeTodo()
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: root.sectionLine
                    }

                    Column {
                        width: parent.width
                        spacing: 12

                        Item {
                            width: parent.width
                            height: 26

                            Text {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                text: "时间线历史"
                                color: root.titleInk
                                font.family: root.uiFont
                                font.pixelSize: 15
                                font.weight: root.sectionWeight
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 86
                                anchors.verticalCenter: parent.verticalCenter
                                text: todoDetailBridge.timelineCount > 0 ? todoDetailBridge.timelineCount + " 条" : ""
                                color: root.mutedInk
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.bodyWeight
                            }

                            Text {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                text: todoDetailBridge.timelineExpanded ? "收起" : "展开"
                                color: "#98A2B2"
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.labelWeight

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: todoDetailBridge.toggleTimeline()
                                }
                            }
                        }

                        Column {
                            width: parent.width
                            spacing: 10
                            visible: todoDetailBridge.timelineExpanded

                            Rectangle {
                                width: parent.width
                                height: Math.max(112, addTimelineEdit.contentHeight + 58)
                                radius: 18
                                color: "#FFFFFF"
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: 16
                                    y: 14
                                    text: "手动跟进"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextEdit {
                                    id: addTimelineEdit
                                    x: 16
                                    y: 36
                                    width: parent.width - 96
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    textFormat: TextEdit.PlainText
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                }

                                Text {
                                    x: 16
                                    y: 36
                                    width: parent.width - 96
                                    visible: addTimelineEdit.text.length === 0 && !addTimelineEdit.activeFocus
                                    text: "输入最新跟进、结论或待办，点击后可添加到时间线"
                                    wrapMode: Text.Wrap
                                    color: root.mutedInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.bodyWeight
                                }

                                Rectangle {
                                    width: 64
                                    height: 30
                                    radius: 15
                                    anchors.right: parent.right
                                    anchors.rightMargin: 14
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 14
                                    color: addTimelineEdit.text.trim().length > 0 ? root.accentTint : root.fieldBg
                                    border.width: 0
                                    border.color: "transparent"

                                    Text {
                                        anchors.centerIn: parent
                                        text: "添加"
                                        color: addTimelineEdit.text.trim().length > 0 ? root.accent : root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 12
                                        font.weight: root.labelWeight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: addTimelineEdit.text.trim().length > 0
                                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: {
                                            todoDetailBridge.addTimelineEntry(addTimelineEdit.text)
                                            addTimelineEdit.text = ""
                                        }
                                    }
                                }
                            }

                            Repeater {
                                model: todoDetailBridge.timeline

                                delegate: Rectangle {
                                    id: timelineCard
                                    property bool editing: false
                                    property string eventId: modelData.id
                                    property string originalContent: modelData.content
                                    property bool dropActive: dropZone.containsDrag
                                    property bool attachmentTarget: root.activeAttachmentEventId === eventId
                                    property bool attachmentsExpanded: false

                                    width: contentColumn.width
                                    height: Math.max(124, entryColumn.implicitHeight + 28)
                                    radius: 18
                                    color: root.timelineBg
                                    border.width: editing || dropActive || attachmentTarget ? 1 : 0
                                    border.color: dropActive ? root.accent : (editing || attachmentTarget ? "#D7E5FF" : root.fieldLine)

                                    Column {
                                        id: entryColumn
                                        x: 16
                                        y: 14
                                        width: parent.width - 32
                                        spacing: 10

                                        Item {
                                            width: parent.width
                                            height: 40

                                            Rectangle {
                                                x: 0
                                                y: 4
                                                width: 8
                                                height: 8
                                                radius: 4
                                                color: modelData.kind === "manual" ? root.accent : "#D7DDE8"
                                            }

                                            Column {
                                                x: 16
                                                y: 0
                                                spacing: 4

                                                Text {
                                                    text: modelData.timeLabel
                                                    color: root.mutedInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.bodyWeight
                                                }

                                                Text {
                                                    text: modelData.scenario
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight
                                                }
                                            }

                                            Row {
                                                anchors.right: parent.right
                                                anchors.top: parent.top
                                                spacing: 12

                                                Text {
                                                    text: editing ? "编辑中" : "点击编辑"
                                                    color: editing ? root.accent : root.mutedInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight
                                                }

                                                Text {
                                                    visible: editing
                                                    text: "保存"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            todoDetailBridge.commitTimelineContent(timelineCard.eventId, timelineEditor.text)
                                                            timelineCard.originalContent = timelineEditor.text
                                                            timelineCard.editing = false
                                                        }
                                                    }
                                                }

                                                Text {
                                                    visible: editing
                                                    text: "取消"
                                                    color: root.mutedInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            timelineEditor.text = timelineCard.originalContent
                                                            todoDetailBridge.updateTimelineContent(timelineCard.eventId, timelineCard.originalContent)
                                                            timelineCard.editing = false
                                                        }
                                                    }
                                                }

                                                Text {
                                                    text: "上传附件"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            root.markAttachmentTarget(timelineCard.eventId)
                                                            todoDetailBridge.requestAttachmentSelection(timelineCard.eventId)
                                                        }
                                                    }
                                                }

                                                Text {
                                                    text: "粘贴截图"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            root.markAttachmentTarget(timelineCard.eventId)
                                                            todoDetailBridge.requestClipboardImagePaste(timelineCard.eventId)
                                                        }
                                                    }
                                                }

                                                Text {
                                                    text: "删除"
                                                    color: "#E35B66"
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: todoDetailBridge.deleteTimelineEntry(timelineCard.eventId)
                                                    }
                                                }
                                            }
                                        }

                                        Text {
                                            id: timelinePreview
                                            visible: !editing
                                            width: parent.width
                                            wrapMode: Text.Wrap
                                            text: modelData.content
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: root.bodyWeight

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    root.markAttachmentTarget(timelineCard.eventId)
                                                    timelineCard.originalContent = modelData.content
                                                    timelineCard.editing = true
                                                }
                                            }
                                        }

                                        TextEdit {
                                            id: timelineEditor
                                            visible: editing
                                            width: parent.width
                                            height: Math.max(60, contentHeight + 4)
                                            wrapMode: TextEdit.Wrap
                                            selectByMouse: true
                                            textFormat: TextEdit.PlainText
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: root.bodyWeight
                                            text: modelData.content
                                            onVisibleChanged: {
                                                if (visible) {
                                                    root.markAttachmentTarget(timelineCard.eventId)
                                                    timelineCard.originalContent = modelData.content
                                                    forceActiveFocus()
                                                    cursorPosition = length
                                                }
                                            }
                                            onTextChanged: todoDetailBridge.updateTimelineContent(timelineCard.eventId, text)
                                        }

                                        Column {
                                            width: parent.width
                                            spacing: 8
                                            visible: modelData.attachmentCount > 0

                                            Rectangle {
                                                width: parent.width
                                                height: 34
                                                radius: 12
                                                color: "#FFFFFF"
                                                border.width: 0
                                                border.color: root.fieldLine

                                                Text {
                                                    x: 12
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: "附件 " + modelData.attachmentCount
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight
                                                }

                                                Text {
                                                    anchors.right: parent.right
                                                    anchors.rightMargin: 12
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: timelineCard.attachmentsExpanded ? "收起" : "展开"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            root.markAttachmentTarget(timelineCard.eventId)
                                                            timelineCard.attachmentsExpanded = !timelineCard.attachmentsExpanded
                                                        }
                                                    }
                                                }
                                            }

                                            Column {
                                                width: parent.width
                                                spacing: 8
                                                visible: timelineCard.attachmentsExpanded

                                                Repeater {
                                                    model: modelData.attachments

                                                    delegate: Rectangle {
                                                        width: entryColumn.width
                                                        height: modelData.isImage ? 74 : 42
                                                        radius: 12
                                                        color: "#FFFFFF"
                                                        border.width: 0
                                                        border.color: root.fieldLine

                                                        Item {
                                                            anchors.fill: parent
                                                            anchors.margins: 8

                                                            Rectangle {
                                                                id: previewThumb
                                                                width: modelData.isImage ? 58 : 48
                                                                height: modelData.isImage ? 58 : 26
                                                                anchors.left: parent.left
                                                                anchors.verticalCenter: parent.verticalCenter
                                                                radius: modelData.isImage ? 10 : 8
                                                                color: modelData.isPreviewable ? root.accentTint : root.fieldBg
                                                                visible: modelData.isPreviewable
                                                                border.width: 0
                                                                border.color: "transparent"

                                                                Image {
                                                                    anchors.fill: parent
                                                                    anchors.margins: 1
                                                                    fillMode: Image.PreserveAspectCrop
                                                                    visible: modelData.isImage
                                                                    source: modelData.fileUrl
                                                                    asynchronous: true
                                                                    cache: false
                                                                    smooth: true
                                                                    clip: true
                                                                }

                                                                Text {
                                                                    anchors.centerIn: parent
                                                                    visible: modelData.isVideo
                                                                    text: "视频"
                                                                    color: root.accent
                                                                    font.family: root.uiFont
                                                                    font.pixelSize: 11
                                                                    font.weight: root.labelWeight
                                                                }

                                                                MouseArea {
                                                                    anchors.fill: parent
                                                                    cursorShape: Qt.PointingHandCursor
                                                                    onClicked: {
                                                                        root.markAttachmentTarget(timelineCard.eventId)
                                                                        todoDetailBridge.previewAttachment(modelData.path)
                                                                    }
                                                                }
                                                            }

                                                            Column {
                                                                anchors.left: previewThumb.visible ? previewThumb.right : parent.left
                                                                anchors.leftMargin: previewThumb.visible ? 12 : 4
                                                                anchors.right: actionRow.left
                                                                anchors.rightMargin: 8
                                                                anchors.verticalCenter: parent.verticalCenter
                                                                spacing: 4

                                                                Text {
                                                                    width: parent.width
                                                                    elide: Text.ElideMiddle
                                                                    text: modelData.name
                                                                    color: root.bodyInk
                                                                    font.family: root.uiFont
                                                                    font.pixelSize: 11
                                                                    font.weight: root.bodyWeight
                                                                }

                                                                Text {
                                                                    width: parent.width
                                                                    elide: Text.ElideRight
                                                                    text: {
                                                                        var sizeLabel = root.formatFileSize(modelData.sizeBytes)
                                                                        if (modelData.isPreviewable) {
                                                                            return sizeLabel.length > 0 ? sizeLabel + " · 可预览" : "可预览"
                                                                        }
                                                                        return sizeLabel
                                                                    }
                                                                    color: root.mutedInk
                                                                    font.family: root.uiFont
                                                                    font.pixelSize: 10
                                                                    font.weight: root.bodyWeight
                                                                }
                                                            }

                                                            Row {
                                                                id: actionRow
                                                                anchors.right: parent.right
                                                                anchors.verticalCenter: parent.verticalCenter
                                                                spacing: 10

                                                                Text {
                                                                    visible: modelData.isPreviewable
                                                                    text: "预览"
                                                                    color: root.accent
                                                                    font.family: root.uiFont
                                                                    font.pixelSize: 10
                                                                    font.weight: root.labelWeight

                                                                    MouseArea {
                                                                        anchors.fill: parent
                                                                        cursorShape: Qt.PointingHandCursor
                                                                        onClicked: {
                                                                            root.markAttachmentTarget(timelineCard.eventId)
                                                                            todoDetailBridge.previewAttachment(modelData.path)
                                                                        }
                                                                    }
                                                                }

                                                                Text {
                                                                    id: removeAttachment
                                                                    text: "移除"
                                                                    color: "#E35B66"
                                                                    font.family: root.uiFont
                                                                    font.pixelSize: 10
                                                                    font.weight: root.labelWeight

                                                                    MouseArea {
                                                                        anchors.fill: parent
                                                                        cursorShape: Qt.PointingHandCursor
                                                                        onClicked: {
                                                                            root.markAttachmentTarget(timelineCard.eventId)
                                                                            todoDetailBridge.removeTimelineAttachment(timelineCard.eventId, modelData.id)
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

                                    DropArea {
                                        id: dropZone
                                        anchors.fill: parent
                                        enabled: !timelineCard.editing

                                        onEntered: function(drag) {
                                            if (drag.hasUrls) {
                                                drag.acceptProposedAction()
                                            }
                                        }

                                        onDropped: function(drop) {
                                            if (!drop.hasUrls) {
                                                return
                                            }
                                            root.markAttachmentTarget(timelineCard.eventId)
                                            todoDetailBridge.addTimelineAttachmentsFromUrls(timelineCard.eventId, drop.urls)
                                            drop.acceptProposedAction()
                                        }
                                    }

                                    Rectangle {
                                        anchors.fill: parent
                                        radius: parent.radius
                                        color: root.accentTint
                                        opacity: dropActive ? 0.88 : 0
                                        visible: dropActive
                                        border.width: 1
                                        border.color: root.accent

                                        Text {
                                            anchors.centerIn: parent
                                            text: "释放即可上传附件"
                                            color: root.accent
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: root.sectionWeight
                                        }
                                    }

                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 78
                                radius: 18
                                color: root.timelineBg
                                border.width: 0
                                border.color: root.fieldLine
                                visible: todoDetailBridge.timelineCount === 0

                                Text {
                                    anchors.centerIn: parent
                                    text: "暂无时间线记录"
                                    color: root.mutedInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.bodyWeight
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    visible: flick.contentHeight > flick.height + 2
                    anchors.right: parent.right
                    anchors.rightMargin: 4
                    y: 8 + (flick.contentY / Math.max(1, flick.contentHeight - flick.height)) * (parent.height - height - 16)
                    width: 4
                    height: Math.max(48, (flick.height / Math.max(flick.contentHeight, 1)) * (parent.height - 16))
                    radius: 2
                    color: "#BEC6D2"
                }
            }
        }
    }

    Component.onCompleted: syncFields()
}

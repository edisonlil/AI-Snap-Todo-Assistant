import QtQuick

Rectangle {
    id: root
    width: 396
    height: 760
    color: "transparent"

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

    function syncFields() {
        syncingFields = true
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

    Connections {
        target: todoDetailBridge
        function onDataChanged() {
            root.syncFields()
        }
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
                    anchors.right: parent.right
                    anchors.rightMargin: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 20

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

                            Repeater {
                                model: todoDetailBridge.timeline

                                delegate: Rectangle {
                                    width: contentColumn.width
                                    height: Math.max(96, timelineContent.contentHeight + 70)
                                    radius: 18
                                    color: root.timelineBg
                                    border.width: 0
                                    border.color: root.fieldLine

                                    Rectangle {
                                        x: 16
                                        y: 18
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: "#D7DDE8"
                                    }

                                    Text {
                                        x: 32
                                        y: 14
                                        text: modelData.timeLabel
                                        color: root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.bodyWeight
                                    }

                                    Text {
                                        x: 32
                                        y: 34
                                        text: modelData.scenario
                                        color: root.labelInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight
                                    }

                                    TextEdit {
                                        id: timelineContent
                                        x: 16
                                        y: 60
                                        width: parent.width - 32
                                        wrapMode: TextEdit.Wrap
                                        selectByMouse: true
                                        textFormat: TextEdit.PlainText
                                        color: root.bodyInk
                                        font.family: root.uiFont
                                        font.pixelSize: 13
                                        font.weight: root.bodyWeight
                                        text: modelData.content
                                        onTextChanged: {
                                            if (!root.syncingFields) {
                                                todoDetailBridge.updateTimelineContent(modelData.id, text)
                                            }
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

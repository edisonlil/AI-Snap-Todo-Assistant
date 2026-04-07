import QtQuick

Rectangle {
    id: root
    width: 396
    height: 760
    color: "transparent"

    readonly property color shellBg: "#F6F8FB"
    readonly property color panelBg: "#FEFEFE"
    readonly property color panelLine: "#E9EDF4"
    readonly property color sectionLine: "#EEF2F6"
    readonly property color titleInk: "#18202E"
    readonly property color bodyInk: "#4A5565"
    readonly property color labelInk: "#9AA4B3"
    readonly property color mutedInk: "#B3BBC8"
    readonly property color fieldBg: "#F7F9FC"
    readonly property color fieldLine: "#E7EDF5"
    readonly property color timelineBg: "#F6F8FC"
    readonly property color accent: "#3D7CFF"
    readonly property color accentTint: "#EEF4FF"
    readonly property string uiFont: "Microsoft YaHei UI"
    readonly property int outerPadding: 22
    readonly property int sectionGap: 18
    readonly property int cardRadius: 24
    readonly property int contentWidth: width - outerPadding * 2
    readonly property int fieldInset: 14
    readonly property int fieldGap: 12
    readonly property int fieldWidth: (contentWidth - fieldGap - fieldInset * 2) / 2
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
        border.width: 1
        border.color: root.panelLine
        antialiasing: true

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: root.cardRadius - 1
            color: root.shellBg
            opacity: 0.26
        }

        Item {
            anchors.fill: parent

            Item {
                id: header
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 70

                Text {
                    x: root.outerPadding
                    y: 24
                    text: "待办详情"
                    color: root.titleInk
                    font.family: root.uiFont
                    font.pixelSize: 20
                    font.weight: root.titleWeight
                }

                Row {
                    anchors.right: parent.right
                    anchors.rightMargin: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8

                    Rectangle {
                        width: 52
                        height: 30
                        radius: 15
                        color: "#FFFFFF"
                        border.width: 0
                        border.color: root.fieldLine

                        Text {
                            anchors.centerIn: parent
                            text: "关闭"
                            color: "#707A89"
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.labelWeight
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: todoDetailBridge.closePanel()
                        }
                    }

                    Rectangle {
                        width: 52
                        height: 30
                        radius: 15
                        color: "#F7F9FD"
                        border.width: 0
                        border.color: root.fieldLine

                        Text {
                            anchors.centerIn: parent
                            text: "保存"
                            color: "#586375"
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.labelWeight
                        }

                        MouseArea {
                            anchors.fill: parent
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
                contentHeight: contentColumn.implicitHeight + 28
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: contentColumn
                    x: root.outerPadding
                    y: 22
                    width: root.contentWidth
                    spacing: root.sectionGap

                    Item {
                        width: parent.width
                        height: Math.max(44, titleEdit.contentHeight + 6)

                        TextEdit {
                            id: titleEdit
                            anchors.fill: parent
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                            textFormat: TextEdit.PlainText
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 18
                            font.weight: root.titleWeight
                            verticalAlignment: TextEdit.AlignTop
                            onTextChanged: root.pushField("title", text)
                        }
                    }

                    Item {
                        width: parent.width
                        height: 146

                        Column {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            width: root.fieldWidth
                            spacing: root.fieldGap

                            Rectangle {
                                width: parent.width
                                height: 62
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: 14
                                    y: 12
                                    text: "群聊名称"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: groupNameEdit
                                    x: 14
                                    y: 32
                                    width: parent.width - 28
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
                                height: 62
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: 14
                                    y: 12
                                    text: "产品线"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: productLineEdit
                                    x: 14
                                    y: 32
                                    width: parent.width - 28
                                    height: 22
                                    clip: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("product_line", text)
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
                                height: 62
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: 14
                                    y: 12
                                    text: "环境"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: environmentEdit
                                    x: 14
                                    y: 32
                                    width: parent.width - 28
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
                                height: 62
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: 14
                                    y: 12
                                    text: "工单类型"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: ticketTypeEdit
                                    x: 14
                                    y: 32
                                    width: parent.width - 28
                                    height: 22
                                    clip: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("ticket_type", text)
                                }
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 10

                        Text {
                            text: "当前描述"
                            color: root.labelInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.sectionWeight
                        }

                        Rectangle {
                            width: parent.width
                            height: 126
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
                                contentHeight: Math.max(height, summaryEdit.contentHeight + 2)
                                boundsBehavior: Flickable.StopAtBounds

                                TextEdit {
                                    id: summaryEdit
                                    width: parent.width
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    textFormat: TextEdit.PlainText
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 14
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("current_summary", text)
                                }
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.rightMargin: 6
                                y: 8 + (summaryFlick.contentY / Math.max(1, summaryFlick.contentHeight - summaryFlick.height)) * (parent.height - height - 16)
                                width: 4
                                height: Math.max(28, (summaryFlick.height / Math.max(summaryFlick.contentHeight, 1)) * (parent.height - 16))
                                radius: 2
                                color: "#C3CAD6"
                                visible: summaryFlick.contentHeight > summaryFlick.height + 2
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 56
                        radius: 18
                        color: root.fieldBg
                        border.width: 0
                        border.color: root.fieldLine

                        Text {
                            x: 14
                            y: 20
                            text: "今天创建: " + todoDetailBridge.createdAtLabel
                            color: root.mutedInk
                            font.family: root.uiFont
                            font.pixelSize: 11
                            font.weight: root.bodyWeight
                        }

                        Text {
                            x: 136
                            y: 20
                            text: "更新于: " + todoDetailBridge.updatedAtLabel
                            color: root.mutedInk
                            font.family: root.uiFont
                            font.pixelSize: 11
                            font.weight: root.bodyWeight
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.right: completeButton.left
                            anchors.rightMargin: 12
                            text: "删除"
                            color: "#B0B8C4"
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
                            anchors.rightMargin: 10
                            width: 62
                            height: 30
                            radius: 15
                            color: root.accentTint
                            border.width: 1
                            border.color: "#D9E6FF"

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
                            height: 24

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
                                anchors.leftMargin: 72
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
                                    height: Math.max(108, timelineContent.contentHeight + 58)
                                    radius: 18
                                    color: root.timelineBg
                                    border.width: 0
                                    border.color: root.fieldLine

                                    Rectangle {
                                        x: 14
                                        y: 16
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: "#D7DDE8"
                                    }

                                    Text {
                                        x: 28
                                        y: 12
                                        text: modelData.timeLabel
                                        color: root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.bodyWeight
                                    }

                                    Text {
                                        x: 28
                                        y: 30
                                        text: modelData.scenario
                                        color: root.labelInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight
                                    }

                                    TextEdit {
                                        id: timelineContent
                                        x: 14
                                        y: 52
                                        width: parent.width - 28
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

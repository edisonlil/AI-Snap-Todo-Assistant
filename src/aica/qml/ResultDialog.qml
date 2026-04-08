import QtQuick

Rectangle {
    id: root
    width: 760
    height: 560
    color: "transparent"

    readonly property color shellBg: "#F1F0EC"
    readonly property color panelBg: "#F1F0EC"
    readonly property color titleInk: "#18202E"
    readonly property color bodyInk: "#4A5565"
    readonly property color labelInk: "#9AA4B3"
    readonly property color mutedInk: "#A9B1BD"
    readonly property color fieldBg: "#F7F7F4"
    readonly property color fieldLine: "#E7E4DD"
    readonly property string uiFont: "Microsoft YaHei UI"
    readonly property int outerPadding: 22
    readonly property int cardRadius: 28
    readonly property int sectionGap: 10
    readonly property int contentWidth: width - outerPadding * 2
    readonly property int fieldGap: 14
    readonly property int fieldWidth: (contentWidth - fieldGap) / 2
    readonly property int titleWeight: 600
    readonly property int sectionWeight: 600
    readonly property int labelWeight: 500
    readonly property int bodyWeight: 400
    property bool syncingFields: false

    function syncFields() {
        syncingFields = true
        titleEdit.text = resultDialogBridge.title
        groupNameEdit.text = resultDialogBridge.groupName
        environmentEdit.text = resultDialogBridge.environment
        productLineEdit.text = resultDialogBridge.productLine
        ticketTypeEdit.text = resultDialogBridge.ticketType
        summaryEdit.text = resultDialogBridge.recognitionConclusion
        syncingFields = false
    }

    function pushField(name, value) {
        if (!syncingFields) {
            resultDialogBridge.updateField(name, value)
        }
    }

    Connections {
        target: resultDialogBridge
        function onDataChanged() {
            root.syncFields()
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.cardRadius
        color: root.panelBg
        antialiasing: true

        Rectangle {
            anchors.fill: parent
            radius: root.cardRadius
            color: root.shellBg
            opacity: 0.18
        }

        Item {
            anchors.fill: parent

            Item {
                id: header
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 52

                Text {
                    x: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    text: "\u5de5\u5355\u5f85\u529e\u786e\u8ba4"
                    color: root.titleInk
                    font.family: root.uiFont
                    font.pixelSize: 18
                    font.weight: root.titleWeight
                }

                Row {
                    anchors.right: parent.right
                    anchors.rightMargin: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 20

                    Text {
                        text: "\u5173\u95ed"
                        color: "#707A89"
                        font.family: root.uiFont
                        font.pixelSize: 12
                        font.weight: root.labelWeight

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: resultDialogBridge.closeDialog()
                        }
                    }

                    Text {
                        text: "\u4fdd\u5b58"
                        color: "#586375"
                        font.family: root.uiFont
                        font.pixelSize: 12
                        font.weight: root.labelWeight

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: resultDialogBridge.saveDialog()
                        }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                height: 1
                color: root.fieldLine
            }

            Rectangle {
                id: footerBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: root.outerPadding
                anchors.rightMargin: root.outerPadding
                anchors.bottomMargin: 16
                height: 46
                radius: 18
                color: root.fieldBg

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 148
                    elide: Text.ElideRight
                    text: resultDialogBridge.saveHint
                    color: root.mutedInk
                    font.family: root.uiFont
                    font.pixelSize: 11
                    font.weight: root.bodyWeight
                }

                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    visible: resultDialogBridge.showFeedbackAction
                    text: "\u53cd\u9988\u4fee\u6b63"
                    color: "#B7793F"
                    font.family: root.uiFont
                    font.pixelSize: 12
                    font.weight: root.labelWeight

                    MouseArea {
                        anchors.fill: parent
                        visible: parent.visible
                        cursorShape: Qt.PointingHandCursor
                        onClicked: resultDialogBridge.feedbackDialog()
                    }
                }
            }

            Flickable {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                anchors.bottom: footerBar.top
                anchors.bottomMargin: 10
                clip: true
                contentWidth: width
                contentHeight: contentColumn.implicitHeight + 12
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: contentColumn
                    x: root.outerPadding
                    y: 12
                    width: root.contentWidth
                    spacing: root.sectionGap

                    Row {
                        spacing: 6

                        Rectangle {
                            height: 24
                            width: scenarioText.implicitWidth + 16
                            radius: 13
                            color: "#FCFBF8"

                            Text {
                                id: scenarioText
                                anchors.centerIn: parent
                                text: resultDialogBridge.scenario
                                color: "#5B6574"
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.labelWeight
                            }
                        }

                        Rectangle {
                            height: 24
                            width: Math.min(contentColumn.width - 110, modelText.implicitWidth + 16)
                            radius: 13
                            color: "#FCFBF8"

                            Text {
                                id: modelText
                                anchors.centerIn: parent
                                width: parent.width - 14
                                elide: Text.ElideMiddle
                                horizontalAlignment: Text.AlignHCenter
                                text: resultDialogBridge.model
                                color: "#5B6574"
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.labelWeight
                            }
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(38, titleEdit.contentHeight + 4)

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
                        height: 120

                        Column {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            width: root.fieldWidth
                            spacing: root.fieldGap

                            Rectangle {
                                width: parent.width
                                height: 52
                                radius: 16
                                color: root.fieldBg

                                Text {
                                    x: 14
                                    y: 12
                                    text: "\u7fa4\u804a\u540d\u79f0"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: groupNameEdit
                                    x: 14
                                    y: 27
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
                                height: 52
                                radius: 16
                                color: root.fieldBg

                                Text {
                                    x: 14
                                    y: 12
                                    text: "\u4ea7\u54c1\u7ebf"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: productLineEdit
                                    x: 14
                                    y: 27
                                    width: parent.width - 28
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
                                height: 52
                                radius: 16
                                color: root.fieldBg

                                Text {
                                    x: 14
                                    y: 12
                                    text: "\u73af\u5883"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: environmentEdit
                                    x: 14
                                    y: 27
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
                                height: 52
                                radius: 16
                                color: root.fieldBg

                                Text {
                                    x: 14
                                    y: 12
                                    text: "\u5de5\u5355\u7c7b\u578b"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: ticketTypeEdit
                                    x: 14
                                    y: 27
                                    width: parent.width - 28
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
                        spacing: 6

                        Text {
                            text: "\u672c\u6b21\u8bc6\u522b\u7ed3\u8bba"
                            color: root.labelInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.sectionWeight
                        }

                        Rectangle {
                            width: parent.width
                            height: 176
                            radius: 20
                            color: "#FCFBF8"

                            Flickable {
                                id: summaryFlick
                                anchors.fill: parent
                                anchors.margins: 12
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
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("timeline_entry", text)
                                }
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.rightMargin: 6
                                y: 8 + (summaryFlick.contentY / Math.max(1, summaryFlick.contentHeight - summaryFlick.height)) * (parent.height - height - 16)
                                width: 4
                                height: Math.max(30, (summaryFlick.height / Math.max(summaryFlick.contentHeight, 1)) * (parent.height - 16))
                                radius: 2
                                color: "#C7CDD7"
                                visible: summaryFlick.contentHeight > summaryFlick.height + 2
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 8
                        visible: false

                        Text {
                            text: "关键证据"
                            color: root.labelInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.sectionWeight
                        }

                        Repeater {
                            model: []

                            delegate: Rectangle {
                                width: contentColumn.width
                                height: Math.max(64, evidenceValue.contentHeight + 36)
                                radius: 16
                                color: "#FCFBF8"

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
                                    text: "移除"
                                    color: "#C77B48"
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
                }

                Rectangle {
                    visible: parent.contentHeight > parent.height + 2
                    anchors.right: parent.right
                    anchors.rightMargin: 4
                    y: 8 + (parent.contentY / Math.max(1, parent.contentHeight - parent.height)) * (parent.height - height - 16)
                    width: 4
                    height: Math.max(56, (parent.height / Math.max(parent.contentHeight, 1)) * (parent.height - 16))
                    radius: 2
                    color: "#BEC6D2"
                }
            }
        }
    }

    Component.onCompleted: syncFields()
}

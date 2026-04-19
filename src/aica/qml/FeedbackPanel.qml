import QtQuick

Rectangle {
    id: root
    width: 780
    height: 580
    color: "#FFFFFF"

    readonly property string uiFont: feedbackPanelBridge ? feedbackPanelBridge.uiFont : "Microsoft YaHei UI"
    readonly property string monospaceFont: feedbackPanelBridge ? feedbackPanelBridge.monospaceFont : "Consolas"
    readonly property color ink: "#111827"
    readonly property color subtleInk: "#667085"
    readonly property color chipInk: "#344054"
    readonly property color panelLine: "#E5E7EB"
    readonly property color fieldLine: "#D7DCE2"
    readonly property color accent: "#1677FF"
    readonly property color cardBg: "#FFFFFF"
    readonly property color chipBg: "#F8FAFC"
    readonly property color editorBg: "#FFFFFF"
    readonly property int outerPadding: 16
    readonly property int cardRadius: 10
    readonly property int sectionGap: 10
    readonly property int labelWeight: 600
    readonly property int titleWeight: 700
    readonly property int bodyWeight: 400

    property bool syncingFields: false

    function syncFields() {
        syncingFields = true
        resultEdit.text = feedbackPanelBridge.resultText
        notesEdit.text = feedbackPanelBridge.notesText
        syncingFields = false
    }

    function pushResult(value) {
        if (!syncingFields) {
            feedbackPanelBridge.updateResultText(value)
        }
    }

    function pushNotes(value) {
        if (!syncingFields) {
            feedbackPanelBridge.updateNotesText(value)
        }
    }

    Connections {
        target: feedbackPanelBridge

        function onDataChanged() {
            root.syncFields()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "#FFFFFF"

        Column {
            anchors.fill: parent
            anchors.margins: root.outerPadding
            spacing: root.sectionGap

            Row {
                width: parent.width
                spacing: 12

                Column {
                    width: parent.width - closeText.width - 12
                    spacing: 6

                    Text {
                        text: "\u53cd\u9988\u4fee\u6b63"
                        color: root.ink
                        font.family: root.uiFont
                        font.pixelSize: 18
                        font.weight: root.titleWeight
                    }

                    Row {
                        spacing: 6

                        Rectangle {
                            height: 24
                            width: scenarioText.implicitWidth + 16
                            radius: 7
                            color: root.chipBg
                            border.width: 1
                            border.color: root.panelLine

                            Text {
                                id: scenarioText
                                anchors.centerIn: parent
                                text: feedbackPanelBridge.scenario
                                color: root.chipInk
                                font.family: root.uiFont
                                font.pixelSize: 10
                                font.weight: root.labelWeight
                            }
                        }

                        Rectangle {
                            height: 24
                            width: Math.min(parent.width - scenarioText.implicitWidth - 22, modelText.implicitWidth + 16)
                            radius: 7
                            color: root.chipBg
                            border.width: 1
                            border.color: root.panelLine

                            Text {
                                id: modelText
                                anchors.centerIn: parent
                                width: parent.width - 12
                                elide: Text.ElideMiddle
                                horizontalAlignment: Text.AlignHCenter
                                text: feedbackPanelBridge.model
                                color: root.chipInk
                                font.family: root.uiFont
                                font.pixelSize: 10
                                font.weight: root.labelWeight
                            }
                        }
                    }

                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        text: "\u5c06\u7ed3\u679c\u4fee\u6b63\u4e3a\u4f60\u771f\u6b63\u60f3\u8981\u7684\u5185\u5bb9\uff0c\u53ef\u8865\u5145\u9519\u8bef\u539f\u56e0\u6216\u683c\u5f0f\u8981\u6c42\u3002"
                        color: root.subtleInk
                        font.family: root.uiFont
                        font.pixelSize: 12
                        font.weight: root.bodyWeight
                    }
                }

                Text {
                    id: closeText
                    text: "\u5173\u95ed"
                    color: root.ink
                    font.family: root.uiFont
                    font.pixelSize: 11
                    font.weight: root.labelWeight

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: feedbackPanelBridge.closePanel()
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: Math.max(320, parent.height - notesCard.height - footerBar.height - 52)
                radius: root.cardRadius
                color: root.cardBg
                border.width: 1
                border.color: root.panelLine

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text {
                        text: "\u4fee\u6b63\u540e\u7684\u7ed3\u679c"
                        color: root.ink
                        font.family: root.uiFont
                        font.pixelSize: 13
                        font.weight: root.titleWeight
                    }

                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        text: "\u76f4\u63a5\u4fee\u6539\u6210\u4f60\u771f\u6b63\u60f3\u8981\u7684\u8f93\u51fa\u7ed3\u679c\u3002"
                        color: root.subtleInk
                        font.family: root.uiFont
                        font.pixelSize: 11
                        font.weight: root.bodyWeight
                    }

                    Rectangle {
                        width: parent.width
                        height: parent.height - 52
                        radius: root.cardRadius
                        color: root.editorBg
                        border.width: 1
                        border.color: resultEdit.activeFocus ? root.accent : root.fieldLine

                        Flickable {
                            id: resultFlick
                            anchors.fill: parent
                            anchors.margins: 12
                            clip: true
                            contentWidth: width
                            contentHeight: Math.max(height, resultEdit.contentHeight + 4)
                            boundsBehavior: Flickable.StopAtBounds

                            TextEdit {
                                id: resultEdit
                                width: parent.width
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                textFormat: TextEdit.PlainText
                                color: root.ink
                                font.family: root.monospaceFont
                                font.pixelSize: 12
                                onTextChanged: root.pushResult(text)
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: notesCard
                width: parent.width
                height: 158
                radius: root.cardRadius
                color: root.cardBg
                border.width: 1
                border.color: root.panelLine

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Text {
                        text: "\u8865\u5145\u8bf4\u660e"
                        color: root.ink
                        font.family: root.uiFont
                        font.pixelSize: 13
                        font.weight: root.titleWeight
                    }

                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        text: "\u53ef\u9009\u586b\u5199\uff1a\u54ea\u91cc\u9519\u4e86\uff0c\u4e3a\u4ec0\u4e48\u9519\uff0c\u4ee5\u540e\u5e0c\u671b\u5b83\u9075\u5faa\u4ec0\u4e48\u683c\u5f0f\u6216\u7ea6\u675f\u3002"
                        color: root.subtleInk
                        font.family: root.uiFont
                        font.pixelSize: 11
                        font.weight: root.bodyWeight
                    }

                    Rectangle {
                        width: parent.width
                        height: 86
                        radius: root.cardRadius
                        color: root.editorBg
                        border.width: 1
                        border.color: notesEdit.activeFocus ? root.accent : root.fieldLine

                        Flickable {
                            anchors.fill: parent
                            anchors.margins: 10
                            clip: true
                            contentWidth: width
                            contentHeight: Math.max(height, notesEdit.contentHeight + 4)
                            boundsBehavior: Flickable.StopAtBounds

                            TextEdit {
                                id: notesEdit
                                width: parent.width
                                wrapMode: TextEdit.Wrap
                                selectByMouse: true
                                textFormat: TextEdit.PlainText
                                color: root.ink
                                font.family: root.uiFont
                                font.pixelSize: 12
                                onTextChanged: root.pushNotes(text)
                            }

                            Text {
                                visible: notesEdit.text.length === 0 && !notesEdit.activeFocus
                                width: parent.width
                                wrapMode: Text.Wrap
                                text: "\u8865\u5145\u80cc\u666f\u3001\u9650\u5236\u6761\u4ef6\u3001\u98ce\u683c\u8981\u6c42\u6216\u7ea0\u9519\u539f\u56e0"
                                color: "#98A2B3"
                                font.family: root.uiFont
                                font.pixelSize: 12
                                font.weight: root.bodyWeight
                            }
                        }
                    }
                }
            }

            Rectangle {
                id: footerBar
                width: parent.width
                height: 44
                radius: root.cardRadius
                color: "#FFFFFF"
                border.width: 1
                border.color: root.panelLine

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - saveText.width - 42
                    elide: Text.ElideRight
                    text: "\u4fdd\u5b58\u540e\u4f1a\u4fdd\u7559\u7ea0\u9519\u5185\u5bb9\uff0c\u5e76\u5173\u8054\u672c\u6b21\u5206\u6790\u7684 Prompt Trace\u3002"
                    color: root.subtleInk
                    font.family: root.uiFont
                    font.pixelSize: 11
                    font.weight: root.bodyWeight
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    width: saveText.implicitWidth + 28
                    height: 28
                    radius: 9
                    color: feedbackPanelBridge.saveEnabled ? root.accent : "#D0D5DD"

                    Text {
                        id: saveText
                        anchors.centerIn: parent
                        text: "\u4fdd\u5b58\u53cd\u9988"
                        color: "#FFFFFF"
                        font.family: root.uiFont
                        font.pixelSize: 11
                        font.weight: root.labelWeight
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: feedbackPanelBridge.saveEnabled
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: feedbackPanelBridge.savePanel()
                    }
                }
            }
        }
    }

    Component.onCompleted: root.syncFields()
}

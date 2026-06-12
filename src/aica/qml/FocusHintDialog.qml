import QtQuick

Rectangle {
    id: root
    width: 460
    height: 248
    color: "transparent"

    readonly property var themeTokens: typeof theme !== "undefined" ? theme : ({})
    readonly property color bodyInk: themeTokens.bodyInk || "#4A5565"
    readonly property color mutedInk: themeTokens.mutedInk || "#A9B1BD"
    readonly property color fieldBg: themeTokens.fieldBg || "#F5F5F5"
    readonly property color fieldLine: themeTokens.fieldLine || "#E5E7EB"
    readonly property color accent: themeTokens.accent || "#2A313F"
    readonly property string uiFont: themeTokens.uiFont || (focusHintBridge ? focusHintBridge.uiFont : "Microsoft YaHei UI")
    readonly property int radiusLg: themeTokens.radiusLg || 20
    readonly property int fontBody: themeTokens.fontBody || 12
    readonly property int fontBodyLg: themeTokens.fontBodyLg || 13
    readonly property int outerPadding: 10
    readonly property int labelWeight: 500
    readonly property int bodyWeight: 400

    property bool syncingFields: false

    function syncFields() {
        syncingFields = true
        hintEdit.text = focusHintBridge.hintText
        syncingFields = false
    }

    function pushValue(text) {
        if (!syncingFields) {
            focusHintBridge.updateHint(text)
        }
    }

    Connections {
        target: focusHintBridge

        function onDataChanged() {
            root.syncFields()
        }
    }

    Item {
        anchors.fill: parent

        Text {
            id: closeAction
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 10
            anchors.rightMargin: 14
            text: "关闭"
            color: root.bodyInk
            font.family: root.uiFont
            font.pixelSize: root.fontBody
            font.weight: root.labelWeight

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: focusHintBridge.closeDialog()
            }
        }

        Rectangle {
            id: inputCard
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: closeAction.bottom
            anchors.bottom: parent.bottom
            anchors.leftMargin: root.outerPadding
            anchors.rightMargin: root.outerPadding
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            radius: root.radiusLg
            color: root.fieldBg
            border.width: 1
            border.color: hintEdit.activeFocus ? root.accent : root.fieldLine

            Flickable {
                id: hintFlick
                anchors.fill: parent
                anchors.margins: 16
                clip: true
                contentWidth: width
                contentHeight: Math.max(height, hintEdit.contentHeight + 4)
                boundsBehavior: Flickable.StopAtBounds

                TextEdit {
                    id: hintEdit
                    x: 0
                    y: 0
                    width: parent.width
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    textFormat: TextEdit.PlainText
                    color: root.bodyInk
                    font.family: root.uiFont
                    font.pixelSize: root.fontBodyLg
                    font.weight: root.bodyWeight
                    activeFocusOnPress: true
                    onTextChanged: root.pushValue(text)

                    Keys.onReturnPressed: function(event) {
                        if (event.modifiers & Qt.ShiftModifier) {
                            return
                        }
                        focusHintBridge.confirmDialog()
                        event.accepted = true
                    }

                    Keys.onEnterPressed: function(event) {
                        if (event.modifiers & Qt.ShiftModifier) {
                            return
                        }
                        focusHintBridge.confirmDialog()
                        event.accepted = true
                    }

                    Keys.onEscapePressed: function(event) {
                        focusHintBridge.closeDialog()
                        event.accepted = true
                    }
                }

                Text {
                    id: hintPlaceholder
                    x: 0
                    y: 0
                    visible: hintEdit.text.length === 0 && !hintEdit.activeFocus
                    width: parent.width
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignTop
                    text: "补一句你这次最想让 AI 提取的重点。留空也可以，系统会按当前场景默认策略分析。按回车可直接确认。"
                    color: root.mutedInk
                    font.family: root.uiFont
                    font.pixelSize: root.fontBodyLg
                    font.weight: root.bodyWeight
                }
            }
        }
    }

    Component.onCompleted: {
        syncFields()
        hintEdit.forceActiveFocus()
    }
}

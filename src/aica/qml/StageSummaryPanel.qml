import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    required property var theme
    property bool busy: false
    property string summaryText: ""
    property string errorText: ""
    property bool hasSummary: false
    signal closeClicked
    signal copyClicked
    signal refreshClicked
    signal presetRewriteRequested(string key)
    signal customRewriteRequested(string text)

    readonly property color panelBorder: "#ECEEF2"
    readonly property color titleText: "#111111"
    readonly property color bodyText: "#222222"
    readonly property color mutedText: "#999999"
    readonly property color chipBorder: "#D8DEE8"
    readonly property color chipText: "#5F6C80"
    readonly property color subtleFill: "#FAFAFA"
    readonly property color primaryFill: "#171F2E"
    readonly property color primaryInk: "#FFFFFF"
    readonly property color secondaryBorder: "#D7DDE6"
    readonly property color secondaryInk: "#334155"

    function submitCustomRewrite() {
        var value = rewriteEdit.text.trim()
        if (value.length === 0 || root.busy) {
            return
        }
        root.customRewriteRequested(value)
        rewriteEdit.text = ""
    }

    color: "#FFFFFF"
    radius: 18
    border.width: 1
    border.color: root.panelBorder
    implicitHeight: panelColumn.implicitHeight + 24

    Column {
        id: panelColumn
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12

        Item {
            width: parent.width
            height: Math.max(closeButton.height, headerColumn.implicitHeight)

            Column {
                id: headerColumn
                anchors.left: parent.left
                anchors.right: closeButton.left
                anchors.rightMargin: 10
                anchors.top: parent.top
                spacing: 4

                Text {
                    text: "阶段总结"
                    color: root.titleText
                    font.family: root.theme.uiFont
                    font.pixelSize: 15
                    font.weight: 700
                }

                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "系统已先整理出一版结果，你可以直接复制，也可以做轻量调整，不做开放聊天。"
                    color: root.mutedText
                    font.family: root.theme.uiFont
                    font.pixelSize: 12
                    font.weight: 400
                }
            }

            Rectangle {
                id: closeButton
                width: 20
                height: 20
                radius: 6
                anchors.right: parent.right
                anchors.top: parent.top
                color: closeMouse.containsMouse ? "#F3F4F6" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "×"
                    color: closeMouse.containsMouse ? "#667085" : root.mutedText
                    font.family: root.theme.uiFont
                    font.pixelSize: 15
                    font.weight: 400
                }

                MouseArea {
                    id: closeMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.closeClicked()
                }
            }
        }

        Rectangle {
            width: parent.width
            color: root.subtleFill
            radius: 12
            border.width: 0
            height: Math.max(92, contentLoader.item ? (contentLoader.item.implicitHeight || contentLoader.item.height) + 20 : 92)

            Loader {
                id: contentLoader
                anchors.fill: parent
                anchors.margins: 10
                sourceComponent: root.busy && !root.hasSummary ? loadingComponent : contentComponent
            }
        }

        Flow {
            width: parent.width
            spacing: 6

            Repeater {
                model: [
                    { key: "shorter", label: "更简短" },
                    { key: "customer", label: "偏客户" },
                    { key: "rd", label: "偏研发" },
                    { key: "materials", label: "强调已收集材料" }
                ]

                delegate: Rectangle {
                    width: chipTextItem.implicitWidth + 20
                    height: 28
                    radius: 14
                    color: "#FFFFFF"
                    border.width: 1
                    border.color: root.chipBorder
                    opacity: (!root.busy && root.hasSummary) ? 1 : 0.58

                    Text {
                        id: chipTextItem
                        anchors.centerIn: parent
                        text: modelData.label
                        color: root.chipText
                        font.family: root.theme.uiFont
                        font.pixelSize: 12
                        font.weight: 500
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: !root.busy && root.hasSummary
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: root.presetRewriteRequested(modelData.key)
                    }
                }
            }
        }

        Row {
            width: parent.width
            spacing: 8
            layoutDirection: Qt.RightToLeft

            Rectangle {
                width: refreshContent.implicitWidth + 22
                height: 32
                radius: 10
                color: root.primaryFill
                border.width: 0
                opacity: root.busy ? 0.92 : 1

                Row {
                    id: refreshContent
                    anchors.centerIn: parent
                    spacing: 6

                    BusyIndicator {
                        width: 14
                        height: 14
                        running: root.busy
                        visible: root.busy
                    }

                    Text {
                        text: root.busy ? "整理中..." : "重新整理"
                        color: root.primaryInk
                        font.family: root.theme.uiFont
                        font.pixelSize: 12
                        font.weight: 600
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: !root.busy
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: root.refreshClicked()
                }
            }

            Rectangle {
                width: copyText.implicitWidth + 22
                height: 32
                radius: 10
                color: "transparent"
                border.width: 1
                border.color: root.secondaryBorder
                opacity: (!root.busy && root.hasSummary) ? 1 : 0.58

                Text {
                    id: copyText
                    anchors.centerIn: parent
                    text: "复制内容"
                    color: root.secondaryInk
                    font.family: root.theme.uiFont
                    font.pixelSize: 12
                    font.weight: 500
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: !root.busy && root.hasSummary
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: root.copyClicked()
                }
            }
        }

        Rectangle {
            width: parent.width
            height: Math.max(64, rewriteEdit.contentHeight + 18)
            radius: 12
            color: root.subtleFill
            border.width: 0

            TextEdit {
                id: rewriteEdit
                x: 12
                y: 10
                width: parent.width - 100
                height: parent.height - 20
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                textFormat: TextEdit.PlainText
                color: root.bodyText
                font.family: root.theme.uiFont
                font.pixelSize: 13
                font.weight: 400
                rightPadding: 8
                bottomPadding: 8

                Keys.onReturnPressed: function(event) {
                    if (event.modifiers & Qt.ShiftModifier) {
                        return
                    }
                    root.submitCustomRewrite()
                    event.accepted = true
                }

                Keys.onEnterPressed: function(event) {
                    if (event.modifiers & Qt.ShiftModifier) {
                        return
                    }
                    root.submitCustomRewrite()
                    event.accepted = true
                }
            }

            Text {
                visible: rewriteEdit.text.length === 0 && !rewriteEdit.activeFocus
                x: 12
                y: 11
                width: parent.width - 104
                wrapMode: Text.Wrap
                text: "补充你的修改要求（如：偏客户表达）"
                color: root.mutedText
                font.family: root.theme.uiFont
                font.pixelSize: 12
                font.weight: 400
            }

            Rectangle {
                width: inlineActionText.implicitWidth + 18
                height: 28
                radius: 10
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                color: "#FFFFFF"
                border.width: 1
                border.color: root.secondaryBorder
                opacity: (!root.busy && rewriteEdit.text.trim().length > 0) ? 1 : 0.58

                Text {
                    id: inlineActionText
                    anchors.centerIn: parent
                    text: "重新生成"
                    color: root.secondaryInk
                    font.family: root.theme.uiFont
                    font.pixelSize: 12
                    font.weight: 500
                }

                MouseArea {
                    anchors.fill: parent
                    enabled: !root.busy && rewriteEdit.text.trim().length > 0
                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: root.submitCustomRewrite()
                }
            }
        }
    }

    Component {
        id: loadingComponent

        Item {
            implicitHeight: 72

            Column {
                anchors.centerIn: parent
                spacing: 8

                BusyIndicator {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 18
                    height: 18
                    running: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "正在整理当前阶段进展..."
                    color: root.mutedText
                    font.family: root.theme.uiFont
                    font.pixelSize: 12
                    font.weight: 400
                }
            }
        }
    }

    Component {
        id: contentComponent

        Item {
            implicitHeight: Math.max(markdownView.contentHeight, errorTextItem.visible ? errorTextItem.y + errorTextItem.implicitHeight : 0)

            TextEdit {
                id: markdownView
                width: Math.min(parent.width, 320)
                readOnly: true
                selectByMouse: true
                selectByKeyboard: true
                wrapMode: TextEdit.Wrap
                textFormat: TextEdit.MarkdownText
                text: root.hasSummary ? root.summaryText : (root.errorText.length > 0 ? root.errorText : "暂无可查看的阶段总结")
                color: root.hasSummary ? root.bodyText : root.mutedText
                font.family: root.theme.uiFont
                font.pixelSize: 13
                font.weight: 400
            }

            Text {
                id: errorTextItem
                y: markdownView.contentHeight + 8
                width: parent.width
                visible: root.errorText.length > 0 && root.hasSummary
                wrapMode: Text.Wrap
                text: root.errorText
                color: "#C66A16"
                font.family: root.theme.uiFont
                font.pixelSize: 11
                font.weight: 400
            }
        }
    }
}

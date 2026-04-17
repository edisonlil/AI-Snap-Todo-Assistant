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
    signal dragStarted(real offsetX, real offsetY)
    signal dragMoved()
    signal dragFinished()

    readonly property color panelBorder: "#E3E7EF"
    readonly property color titleText: "#18202E"
    readonly property color bodyText: "#334155"
    readonly property color mutedText: "#7E8A9A"
    readonly property color subtleText: "#98A2B2"
    readonly property color chipBorder: "#D7DDE6"
    readonly property color chipText: "#516074"
    readonly property color chipHover: "#F7F9FC"
    readonly property color subtleFill: "#F7F8FA"
    readonly property color sectionFill: "#FBFBFC"
    readonly property color primaryFill: "#18202E"
    readonly property color primaryInk: "#FFFFFF"
    readonly property color secondaryBorder: "#D7DDE6"
    readonly property color secondaryInk: "#334155"
    readonly property color statusFill: "#EEF4FF"
    readonly property color statusInk: "#3D7CFF"

    function submitCustomRewrite() {
        var value = rewriteEdit.text.trim()
        if (value.length === 0 || root.busy) {
            return
        }
        root.customRewriteRequested(value)
        rewriteEdit.text = ""
    }

    color: "#FFFFFF"
    radius: 20
    border.width: 1
    border.color: root.panelBorder
    antialiasing: true
    clip: true

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: 8
        anchors.leftMargin: 3
        anchors.rightMargin: -3
        anchors.bottomMargin: -6
        radius: root.radius + 2
        color: "#10233D"
        opacity: 0.08
        z: -1
    }

    Column {
        id: panelColumn
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        Item {
            id: headerBar
            width: parent.width
            height: 58

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                onPressed: function(mouse) {
                    root.dragStarted(mouse.x, mouse.y)
                }
                onPositionChanged: function(mouse) {
                    if (mouse.buttons & Qt.LeftButton) {
                        root.dragMoved()
                    }
                }
                onReleased: root.dragFinished()
                onCanceled: root.dragFinished()
            }

            Column {
                anchors.left: parent.left
                anchors.right: closeButton.left
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 5

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
                    text: "系统已先整理出一版结果，你可以直接复制，也可以做轻量调整"
                    color: root.mutedText
                    font.family: root.theme.uiFont
                    font.pixelSize: 12
                    font.weight: 400
                }
            }

            Rectangle {
                id: closeButton
                width: 28
                height: 28
                radius: 10
                anchors.right: parent.right
                anchors.top: parent.top
                color: closeMouse.containsMouse ? "#F2F4F7" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "×"
                    color: closeMouse.containsMouse ? "#667085" : root.mutedText
                    font.family: root.theme.uiFont
                    font.pixelSize: 16
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
            height: 1
            color: "#F0F2F5"
        }

        Rectangle {
            width: parent.width
            height: 30
            radius: 15
            color: root.sectionFill
            border.width: 1
            border.color: "#EEF2F6"
            visible: root.busy || root.hasSummary || root.errorText.length > 0

            Row {
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                BusyIndicator {
                    width: 14
                    height: 14
                    running: root.busy
                    visible: root.busy
                }

                Text {
                    text: root.busy ? "整理中" : (root.hasSummary ? "已生成，可继续微调" : "整理结果")
                    color: root.busy ? root.statusInk : root.mutedText
                    font.family: root.theme.uiFont
                    font.pixelSize: 11
                    font.weight: 500
                }
            }
        }

        Column {
            width: parent.width
            spacing: 8

            Text {
                text: "内容区"
                color: root.subtleText
                font.family: root.theme.uiFont
                font.pixelSize: 11
                font.weight: 500
            }

            Rectangle {
                width: parent.width
                height: 206
                radius: 14
                color: root.subtleFill
                border.width: 1
                border.color: "#EEF2F6"

                Loader {
                    id: contentLoader
                    anchors.fill: parent
                    anchors.margins: 12
                    sourceComponent: root.busy && !root.hasSummary ? loadingComponent : contentComponent
                }
            }
        }

        Column {
            width: parent.width
            spacing: 8

            Text {
                text: "操作区"
                color: root.subtleText
                font.family: root.theme.uiFont
                font.pixelSize: 11
                font.weight: 500
            }

            Row {
                width: parent.width
                spacing: 8

                Rectangle {
                    width: (parent.width - 8) / 2
                    height: 34
                    radius: 11
                    color: "transparent"
                    border.width: 1
                    border.color: root.secondaryBorder
                    opacity: (!root.busy && root.hasSummary) ? 1 : 0.58

                    Text {
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

                Rectangle {
                    width: (parent.width - 8) / 2
                    height: 34
                    radius: 11
                    color: root.primaryFill
                    border.width: 0
                    opacity: root.busy ? 0.92 : 1

                    Row {
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
            }
        }

        Column {
            width: parent.width
            spacing: 8

            Text {
                text: "快速调整"
                color: root.subtleText
                font.family: root.theme.uiFont
                font.pixelSize: 11
                font.weight: 500
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
                        height: 30
                        radius: 15
                        color: chipMouse.containsMouse ? root.chipHover : "#FFFFFF"
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
                            id: chipMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: !root.busy && root.hasSummary
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: root.presetRewriteRequested(modelData.key)
                        }
                    }
                }
            }
        }

        Column {
            width: parent.width
            spacing: 8

            Text {
                text: "自定义调整"
                color: root.subtleText
                font.family: root.theme.uiFont
                font.pixelSize: 11
                font.weight: 500
            }

            Rectangle {
                width: parent.width
                height: 112
                radius: 14
                color: root.subtleFill
                border.width: 1
                border.color: "#EEF2F6"

                TextEdit {
                    id: rewriteEdit
                    x: 12
                    y: 11
                    width: parent.width - 24
                    height: parent.height - 56
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    textFormat: TextEdit.PlainText
                    color: root.bodyText
                    font.family: root.theme.uiFont
                    font.pixelSize: 13
                    font.weight: 400
                    rightPadding: 4
                    bottomPadding: 6

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
                    width: parent.width - 24
                    wrapMode: Text.Wrap
                    text: "输入你的调整要求，例如：更像发给客户、保留关键动作、减少背景说明"
                    color: root.mutedText
                    font.family: root.theme.uiFont
                    font.pixelSize: 12
                    font.weight: 400
                }

                Rectangle {
                    width: adjustText.implicitWidth + 22
                    height: 30
                    radius: 10
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 12
                    color: "#FFFFFF"
                    border.width: 1
                    border.color: root.secondaryBorder
                    opacity: (!root.busy && rewriteEdit.text.trim().length > 0) ? 1 : 0.58

                    Text {
                        id: adjustText
                        anchors.centerIn: parent
                        text: "调整"
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
    }

    Component {
        id: loadingComponent

        Item {
            Column {
                anchors.centerIn: parent
                spacing: 10

                BusyIndicator {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 18
                    height: 18
                    running: true
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "正在整理当前阶段总结..."
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
            Flickable {
                id: summaryFlick
                anchors.fill: parent
                clip: true
                contentWidth: width
                contentHeight: Math.max(height, summaryTextView.contentHeight + (errorTextItem.visible ? errorTextItem.implicitHeight + 14 : 0))
                boundsBehavior: Flickable.StopAtBounds

                TextEdit {
                    id: summaryTextView
                    width: parent.width - (summaryScrollBar.visible ? 10 : 0)
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
                    y: summaryTextView.contentHeight + 10
                    width: parent.width - (summaryScrollBar.visible ? 10 : 0)
                    visible: root.errorText.length > 0 && root.hasSummary
                    wrapMode: Text.Wrap
                    text: root.errorText
                    color: "#C66A16"
                    font.family: root.theme.uiFont
                    font.pixelSize: 11
                    font.weight: 400
                }
            }

            Rectangle {
                id: summaryScrollBar
                anchors.right: parent.right
                anchors.rightMargin: 0
                y: (summaryFlick.contentY / Math.max(1, summaryFlick.contentHeight - summaryFlick.height)) * (parent.height - height)
                width: 4
                height: Math.max(30, (summaryFlick.height / Math.max(summaryFlick.contentHeight, 1)) * parent.height)
                radius: 2
                color: "#C8D0DB"
                visible: summaryFlick.contentHeight > summaryFlick.height + 2
            }
        }
    }
}

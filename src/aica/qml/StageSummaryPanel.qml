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

    readonly property color cardBorder: "#ECEFF3"
    readonly property color sectionBorder: "#F1F4F7"
    readonly property color bodyText: "#374151"
    readonly property color mutedText: "#94A3B8"
    readonly property color titleText: "#111827"
    readonly property color chipBorder: "#D9E0EA"
    readonly property color inputBorder: "#DFE5EC"
    readonly property color activeBorder: "#9FB8FF"

    color: "#FFFFFF"
    radius: 24
    border.width: 1
    border.color: root.cardBorder
    implicitHeight: panelColumn.implicitHeight

    function submitCustomRewrite() {
        var value = rewriteEdit.text.trim()
        if (value.length === 0 || root.busy) {
            return
        }
        root.customRewriteRequested(value)
        rewriteEdit.text = ""
    }

    Column {
        id: panelColumn
        width: parent.width
        spacing: 0

        Item {
            width: parent.width
            height: headerContent.implicitHeight + 28

            Column {
                id: headerContent
                anchors.left: parent.left
                anchors.right: closeButton.left
                anchors.leftMargin: 18
                anchors.rightMargin: 14
                anchors.top: parent.top
                anchors.topMargin: 14
                spacing: 6

                Text {
                    text: "阶段总结"
                    color: root.titleText
                    font.family: root.theme.uiFont
                    font.pixelSize: 16
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
                width: 24
                height: 24
                radius: 8
                anchors.right: parent.right
                anchors.rightMargin: 14
                anchors.top: parent.top
                anchors.topMargin: 14
                color: closeMouse.containsMouse ? "#F3F4F6" : "transparent"

                Text {
                    anchors.centerIn: parent
                    text: "×"
                    color: closeMouse.containsMouse ? "#6B7280" : root.mutedText
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
            color: root.sectionBorder
        }

        Column {
            width: parent.width
            spacing: 0
            padding: 16

            Rectangle {
                id: summaryBox
                width: parent.width - 32
                height: Math.max(204, (summaryLoader.item ? (summaryLoader.item.implicitHeight || summaryLoader.item.height) : 0) + 32)
                radius: 18
                color: "#FCFCFB"
                border.width: 1
                border.color: "#EDF1F6"

                Loader {
                    id: summaryLoader
                    anchors.fill: parent
                    anchors.margins: 16
                    sourceComponent: (!root.hasSummary && root.busy) ? loadingComponent : summaryComponent
                }
            }

            Row {
                width: parent.width - 32
                spacing: 10
                topPadding: 16
                bottomPadding: 16

                Rectangle {
                    width: copyText.implicitWidth + 28
                    height: 38
                    radius: 12
                    color: "#111827"
                    border.width: 1
                    border.color: "#111827"

                    Text {
                        id: copyText
                        anchors.centerIn: parent
                        text: "复制内容"
                        color: "#FFFFFF"
                        font.family: root.theme.uiFont
                        font.pixelSize: 13
                        font.weight: 700
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: root.hasSummary
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: root.copyClicked()
                    }
                }

                Rectangle {
                    width: refreshText.implicitWidth + 28
                    height: 38
                    radius: 12
                    color: "#FFFFFF"
                    border.width: 1
                    border.color: root.chipBorder

                    Text {
                        id: refreshText
                        anchors.centerIn: parent
                        text: root.busy ? "整理中..." : "重新整理"
                        color: root.bodyText
                        font.family: root.theme.uiFont
                        font.pixelSize: 13
                        font.weight: 500
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: !root.busy
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: root.refreshClicked()
                    }
                }
            }

            Rectangle {
                width: parent.width - 32
                height: 1
                color: root.sectionBorder
            }

            Text {
                width: parent.width - 32
                topPadding: 14
                bottomPadding: 8
                text: "快速调整"
                color: "#6B7280"
                font.family: root.theme.uiFont
                font.pixelSize: 13
                font.weight: 600
            }

            Flow {
                width: parent.width - 32
                spacing: 8

                Repeater {
                    model: [
                        { key: "shorter", label: "更简短" },
                        { key: "customer", label: "偏客户" },
                        { key: "rd", label: "偏研发" },
                        { key: "materials", label: "强调已收集材料" }
                    ]

                    delegate: Rectangle {
                        width: chipLabel.implicitWidth + 24
                        height: 30
                        radius: 15
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: root.chipBorder
                        opacity: (!root.busy && root.hasSummary) ? 1 : 0.58

                        Text {
                            id: chipLabel
                            anchors.centerIn: parent
                            text: modelData.label
                            color: "#475569"
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

            Text {
                width: parent.width - 32
                topPadding: 10
                bottomPadding: 8
                text: "自定义调整"
                color: "#6B7280"
                font.family: root.theme.uiFont
                font.pixelSize: 13
                font.weight: 600
            }

            Rectangle {
                width: parent.width - 32
                height: Math.max(104, rewriteEdit.contentHeight + 34)
                radius: 18
                color: "#FFFFFF"
                border.width: 1
                border.color: rewriteEdit.activeFocus ? root.activeBorder : root.inputBorder

                TextEdit {
                    id: rewriteEdit
                    x: 16
                    y: 14
                    width: parent.width - 32
                    height: parent.height - 28
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    textFormat: TextEdit.PlainText
                    color: root.bodyText
                    font.family: root.theme.uiFont
                    font.pixelSize: 13
                    font.weight: 400
                    rightPadding: 72
                    bottomPadding: 34

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
                    x: 16
                    y: 14
                    width: parent.width - 86
                    wrapMode: Text.Wrap
                    text: "例如：语气更稳一点；强调我已经收集了样张和日志；更适合发给客户"
                    color: "#9CA3AF"
                    font.family: root.theme.uiFont
                    font.pixelSize: 12
                    font.weight: 400
                }

                Rectangle {
                    width: adjustText.implicitWidth + 22
                    height: 30
                    radius: 15
                    anchors.right: parent.right
                    anchors.rightMargin: 10
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 10
                    color: "#FFFFFF"
                    border.width: 1
                    border.color: root.chipBorder
                    opacity: (!root.busy && rewriteEdit.text.trim().length > 0) ? 1 : 0.68

                    Text {
                        id: adjustText
                        anchors.centerIn: parent
                        text: "调整"
                        color: root.bodyText
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

            Text {
                width: parent.width - 32
                topPadding: 10
                text: "先给一版，再做轻量改写。这里不是聊天窗口，只围绕当前总结做收敛式调整。"
                wrapMode: Text.Wrap
                color: "#9CA3AF"
                font.family: root.theme.uiFont
                font.pixelSize: 12
                font.weight: 400
            }
        }
    }

    Component {
        id: loadingComponent

        Item {
            implicitHeight: 26

            Row {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                spacing: 10

                BusyIndicator {
                    width: 18
                    height: 18
                    running: true
                }

                Text {
                    text: "正在整理当前阶段进展..."
                    color: root.mutedText
                    font.family: root.theme.uiFont
                    font.pixelSize: 13
                    font.weight: 400
                }
            }
        }
    }

    Component {
        id: summaryComponent

        Item {
            implicitHeight: Math.max(summaryEdit.contentHeight, errorTextItem.visible ? errorTextItem.y + errorTextItem.implicitHeight : 0)

            TextEdit {
                id: summaryEdit
                width: parent.width
                readOnly: true
                selectByMouse: true
                selectByKeyboard: true
                wrapMode: TextEdit.Wrap
                textFormat: TextEdit.PlainText
                text: root.hasSummary ? root.summaryText : (root.errorText.length > 0 ? root.errorText : "暂无可查看的阶段总结")
                color: root.hasSummary ? root.bodyText : root.mutedText
                font.family: root.theme.uiFont
                font.pixelSize: 14
                font.weight: 400
            }

            Text {
                id: errorTextItem
                y: summaryEdit.contentHeight + 10
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

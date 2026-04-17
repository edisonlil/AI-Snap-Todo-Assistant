import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    width: 332
    height: 632
    color: "transparent"
    readonly property string uiFont: "Microsoft YaHei UI"

    Rectangle {
        id: panel
        anchors.fill: parent
        property bool busy: todoDetailBridge.stageSummaryBusy
        property string summaryText: todoDetailBridge.stageSummaryText
        property string errorText: todoDetailBridge.stageSummaryError
        property bool hasSummary: todoDetailBridge.hasStageSummary

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
        readonly property color statusInk: "#3D7CFF"

        function submitCustomRewrite() {
            var value = rewriteEdit.text.trim()
            if (value.length === 0 || panel.busy) {
                return
            }
            panel.customRewriteRequested(value)
            rewriteEdit.text = ""
        }

        onCloseClicked: todoDetailBridge.toggleStageSummary()
        onCopyClicked: todoDetailBridge.copyStageSummary()
        onRefreshClicked: todoDetailBridge.refreshStageSummary()
        onPresetRewriteRequested: function(key) {
            todoDetailBridge.rewriteStageSummaryWithPreset(key)
        }
        onCustomRewriteRequested: function(text) {
            todoDetailBridge.rewriteStageSummary(text)
        }
        onDragStarted: function(offsetX, offsetY) {
            stageSummaryWindowBridge.beginPanelDrag(offsetX, offsetY)
        }
        onDragMoved: stageSummaryWindowBridge.updatePanelDrag()
        onDragFinished: stageSummaryWindowBridge.finishPanelDrag()

        color: "#FFFFFF"
        radius: 20
        border.width: 1
        border.color: panel.panelBorder
        antialiasing: true
        clip: true

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: 8
            anchors.leftMargin: 3
            anchors.rightMargin: -3
            anchors.bottomMargin: -6
            radius: panel.radius + 2
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
                        panel.dragStarted(mouse.x, mouse.y)
                    }
                    onPositionChanged: function(mouse) {
                        if (mouse.buttons & Qt.LeftButton) {
                            panel.dragMoved()
                        }
                    }
                    onReleased: panel.dragFinished()
                    onCanceled: panel.dragFinished()
                }

                Column {
                    anchors.left: parent.left
                    anchors.right: closeButton.left
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 5

                    Text {
                        text: "\u9636\u6bb5\u603b\u7ed3"
                        color: panel.titleText
                        font.family: root.uiFont
                        font.pixelSize: 15
                        font.weight: 700
                    }

                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        text: "\u7cfb\u7edf\u5df2\u5148\u6574\u7406\u51fa\u4e00\u7248\u7ed3\u679c\uff0c\u4f60\u53ef\u4ee5\u76f4\u63a5\u590d\u5236\uff0c\u4e5f\u53ef\u4ee5\u505a\u8f7b\u91cf\u8c03\u6574"
                        color: panel.mutedText
                        font.family: root.uiFont
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
                        text: "\u00d7"
                        color: closeMouse.containsMouse ? "#667085" : panel.mutedText
                        font.family: root.uiFont
                        font.pixelSize: 16
                        font.weight: 400
                    }

                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: panel.closeClicked()
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
                color: panel.sectionFill
                border.width: 1
                border.color: "#EEF2F6"
                visible: panel.busy || panel.hasSummary || panel.errorText.length > 0

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8

                    BusyIndicator {
                        width: 14
                        height: 14
                        running: panel.busy
                        visible: panel.busy
                    }

                    Text {
                        text: panel.busy ? "\u6574\u7406\u4e2d" : (panel.hasSummary ? "\u5df2\u751f\u6210\uff0c\u53ef\u7ee7\u7eed\u5fae\u8c03" : "\u6574\u7406\u7ed3\u679c")
                        color: panel.busy ? panel.statusInk : panel.mutedText
                        font.family: root.uiFont
                        font.pixelSize: 11
                        font.weight: 500
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 8

                Text {
                    text: "\u5185\u5bb9\u533a"
                    color: panel.subtleText
                    font.family: root.uiFont
                    font.pixelSize: 11
                    font.weight: 500
                }

                Rectangle {
                    width: parent.width
                    height: 206
                    radius: 14
                    color: panel.subtleFill
                    border.width: 1
                    border.color: "#EEF2F6"

                    Loader {
                        id: contentLoader
                        anchors.fill: parent
                        anchors.margins: 12
                        sourceComponent: panel.busy && !panel.hasSummary ? loadingComponent : contentComponent
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 8

                Text {
                    text: "\u64cd\u4f5c\u533a"
                    color: panel.subtleText
                    font.family: root.uiFont
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
                        border.color: panel.secondaryBorder
                        opacity: (!panel.busy && panel.hasSummary) ? 1 : 0.58

                        Text {
                            anchors.centerIn: parent
                            text: "\u590d\u5236\u5185\u5bb9"
                            color: panel.secondaryInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 500
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled: !panel.busy && panel.hasSummary
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: panel.copyClicked()
                        }
                    }

                    Rectangle {
                        width: (parent.width - 8) / 2
                        height: 34
                        radius: 11
                        color: panel.primaryFill
                        border.width: 0
                        opacity: panel.busy ? 0.92 : 1

                        Row {
                            anchors.centerIn: parent
                            spacing: 6

                            BusyIndicator {
                                width: 14
                                height: 14
                                running: panel.busy
                                visible: panel.busy
                            }

                            Text {
                                text: panel.busy ? "\u6574\u7406\u4e2d..." : "\u91cd\u65b0\u6574\u7406"
                                color: panel.primaryInk
                                font.family: root.uiFont
                                font.pixelSize: 12
                                font.weight: 600
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled: !panel.busy
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: panel.refreshClicked()
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 8

                Text {
                    text: "\u5feb\u901f\u8c03\u6574"
                    color: panel.subtleText
                    font.family: root.uiFont
                    font.pixelSize: 11
                    font.weight: 500
                }

                Flow {
                    width: parent.width
                    spacing: 6

                    Repeater {
                        model: [
                            { key: "shorter", label: "\u66f4\u7b80\u77ed" },
                            { key: "customer", label: "\u504f\u5ba2\u6237" },
                            { key: "rd", label: "\u504f\u7814\u53d1" },
                            { key: "materials", label: "\u5f3a\u8c03\u5df2\u6536\u96c6\u6750\u6599" }
                        ]

                        delegate: Rectangle {
                            width: chipTextItem.implicitWidth + 20
                            height: 30
                            radius: 15
                            color: chipMouse.containsMouse ? panel.chipHover : "#FFFFFF"
                            border.width: 1
                            border.color: panel.chipBorder
                            opacity: (!panel.busy && panel.hasSummary) ? 1 : 0.58

                            Text {
                                id: chipTextItem
                                anchors.centerIn: parent
                                text: modelData.label
                                color: panel.chipText
                                font.family: root.uiFont
                                font.pixelSize: 12
                                font.weight: 500
                            }

                            MouseArea {
                                id: chipMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: !panel.busy && panel.hasSummary
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: panel.presetRewriteRequested(modelData.key)
                            }
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 8

                Text {
                    text: "\u81ea\u5b9a\u4e49\u8c03\u6574"
                    color: panel.subtleText
                    font.family: root.uiFont
                    font.pixelSize: 11
                    font.weight: 500
                }

                Rectangle {
                    width: parent.width
                    height: 112
                    radius: 14
                    color: panel.subtleFill
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
                        color: panel.bodyText
                        font.family: root.uiFont
                        font.pixelSize: 13
                        font.weight: 400
                        rightPadding: 4
                        bottomPadding: 6

                        Keys.onReturnPressed: function(event) {
                            if (event.modifiers & Qt.ShiftModifier) {
                                return
                            }
                            panel.submitCustomRewrite()
                            event.accepted = true
                        }

                        Keys.onEnterPressed: function(event) {
                            if (event.modifiers & Qt.ShiftModifier) {
                                return
                            }
                            panel.submitCustomRewrite()
                            event.accepted = true
                        }
                    }

                    Text {
                        visible: rewriteEdit.text.length === 0 && !rewriteEdit.activeFocus
                        x: 12
                        y: 11
                        width: parent.width - 24
                        wrapMode: Text.Wrap
                        text: "\u8f93\u5165\u4f60\u7684\u8c03\u6574\u8981\u6c42\uff0c\u4f8b\u5982\uff1a\u66f4\u50cf\u53d1\u7ed9\u5ba2\u6237\u3001\u4fdd\u7559\u5173\u952e\u52a8\u4f5c\u3001\u51cf\u5c11\u80cc\u666f\u8bf4\u660e"
                        color: panel.mutedText
                        font.family: root.uiFont
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
                        border.color: panel.secondaryBorder
                        opacity: (!panel.busy && rewriteEdit.text.trim().length > 0) ? 1 : 0.58

                        Text {
                            id: adjustText
                            anchors.centerIn: parent
                            text: "\u8c03\u6574"
                            color: panel.secondaryInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 500
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled: !panel.busy && rewriteEdit.text.trim().length > 0
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: panel.submitCustomRewrite()
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
                        text: "\u6b63\u5728\u6574\u7406\u5f53\u524d\u9636\u6bb5\u603b\u7ed3..."
                        color: panel.mutedText
                        font.family: root.uiFont
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
                        text: panel.hasSummary ? panel.summaryText : (panel.errorText.length > 0 ? panel.errorText : "\u6682\u65e0\u53ef\u67e5\u770b\u7684\u9636\u6bb5\u603b\u7ed3")
                        color: panel.hasSummary ? panel.bodyText : panel.mutedText
                        font.family: root.uiFont
                        font.pixelSize: 13
                        font.weight: 400
                    }

                    Text {
                        id: errorTextItem
                        y: summaryTextView.contentHeight + 10
                        width: parent.width - (summaryScrollBar.visible ? 10 : 0)
                        visible: panel.errorText.length > 0 && panel.hasSummary
                        wrapMode: Text.Wrap
                        text: panel.errorText
                        color: "#C66A16"
                        font.family: root.uiFont
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
}

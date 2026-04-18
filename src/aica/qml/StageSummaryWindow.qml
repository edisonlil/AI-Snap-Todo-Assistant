import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    width: 443
    height: 632
    color: "transparent"
    readonly property string uiFont: todoDetailBridge ? todoDetailBridge.uiFont : "Microsoft YaHei UI"
    readonly property real preferredHeight: panel.preferredHeight
    onPreferredHeightChanged: stageSummaryWindowBridge.syncPanelSize()

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

        readonly property real panelSidePadding: 24
        readonly property real panelTopPadding: 16
        readonly property real panelBottomPadding: 24
        readonly property real sectionSpacing: 12
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
        readonly property real rewriteBoxMinHeight: 96
        readonly property real chipHeight: 24
        readonly property real chipRadius: 12
        readonly property real chipFontSize: 11
        readonly property real chipHorizontalPadding: 16
        readonly property real contentBoxMinHeight: 96
        readonly property real contentBoxDefaultHeight: 112
        readonly property real contentBoxExpandThreshold: 240
        readonly property real contentBoxAbsoluteMaxHeight: 352
        readonly property real rewriteBoxHeight: Math.max(rewriteBoxMinHeight, rewriteEdit.contentHeight + 18)
        readonly property real contentBoxMeasuredHeight: Math.max(
            92,
            contentLoader.item ? (contentLoader.item.implicitHeight || contentLoader.item.height) + 20 : 92
        )
        readonly property real fixedSectionHeight: (
            panelTopPadding + panelBottomPadding + headerBar.height + chipsFlow.implicitHeight + actionRow.height + rewriteBoxHeight + (sectionSpacing * 4)
        )
        readonly property real preferredContentBoxHeight: (
            contentBoxMeasuredHeight > contentBoxExpandThreshold
            ? Math.min(contentBoxMeasuredHeight, contentBoxAbsoluteMaxHeight)
            : contentBoxDefaultHeight
        )
        readonly property real preferredHeight: fixedSectionHeight + preferredContentBoxHeight
        readonly property real contentBoxAvailableHeight: Math.max(
            contentBoxMinHeight,
            root.height - fixedSectionHeight
        )
        readonly property real contentBoxHeight: Math.max(
            contentBoxMinHeight,
            Math.min(preferredContentBoxHeight, contentBoxAvailableHeight)
        )

        function submitCustomRewrite() {
            var value = rewriteEdit.text.trim()
            if (value.length === 0 || panel.busy) {
                return
            }
            panel.customRewriteRequested(value)
            rewriteEdit.text = ""
        }

        function handlePrimaryAction() {
            if (panel.busy) {
                return
            }
            if (rewriteEdit.text.trim().length > 0) {
                panel.submitCustomRewrite()
                return
            }
            panel.refreshClicked()
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
        radius: 18
        border.width: 1
        border.color: panel.panelBorder
        clip: true

        Column {
            id: panelColumn
            anchors.fill: parent
            anchors.leftMargin: panel.panelSidePadding
            anchors.rightMargin: panel.panelSidePadding
            anchors.topMargin: panel.panelTopPadding
            anchors.bottomMargin: panel.panelBottomPadding
            spacing: panel.sectionSpacing

            Item {
                id: headerBar
                width: parent.width
                height: Math.max(closeButton.height, headerColumn.implicitHeight)

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
                    id: headerColumn
                    anchors.left: parent.left
                    anchors.right: closeButton.left
                    anchors.rightMargin: 10
                    anchors.top: parent.top
                    spacing: 5

                    Text {
                        text: "阶段总结"
                        color: panel.titleText
                        font.family: root.uiFont
                        font.pixelSize: 17
                        font.weight: 600
                    }

                    Text {
                        width: parent.width
                        wrapMode: Text.Wrap
                        text: "系统已先整理出一版结果，你可以直接复制，也可以做轻量调整，不做开放聊天。"
                        color: panel.mutedText
                        font.family: root.uiFont
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
                        color: closeMouse.containsMouse ? "#667085" : panel.mutedText
                        font.family: root.uiFont
                        font.pixelSize: 15
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
                id: contentBox
                width: parent.width
                height: panel.contentBoxHeight
                color: panel.subtleFill
                radius: 12
                border.width: 0

                Loader {
                    id: contentLoader
                    anchors.fill: parent
                    anchors.margins: 10
                    sourceComponent: panel.busy && !panel.hasSummary ? loadingComponent : contentComponent
                }
            }

            Flow {
                id: chipsFlow
                width: parent.width
                spacing: 5

                Repeater {
                    model: [
                        { key: "shorter", label: "更简短" },
                        { key: "customer", label: "偏客户" },
                        { key: "rd", label: "偏研发" },
                        { key: "materials", label: "强调已收集材料" }
                    ]

                    delegate: Rectangle {
                        width: chipTextItem.implicitWidth + panel.chipHorizontalPadding
                        height: panel.chipHeight
                        radius: panel.chipRadius
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: panel.chipBorder
                        opacity: (!panel.busy && panel.hasSummary) ? 1 : 0.58

                        Text {
                            id: chipTextItem
                            anchors.centerIn: parent
                            text: modelData.label
                            color: panel.chipText
                            font.family: root.uiFont
                            font.pixelSize: panel.chipFontSize
                            font.weight: 500
                        }

                        MouseArea {
                            anchors.fill: parent
                            enabled: !panel.busy && panel.hasSummary
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: panel.presetRewriteRequested(modelData.key)
                        }
                    }
                }
            }

            Row {
                id: actionRow
                width: parent.width
                spacing: 8
                layoutDirection: Qt.RightToLeft

                Rectangle {
                    width: refreshContent.implicitWidth + 22
                    height: 32
                    radius: 10
                    color: panel.primaryFill
                    border.width: 0
                    opacity: panel.busy ? 0.92 : 1

                    Row {
                        id: refreshContent
                        anchors.centerIn: parent
                        spacing: 6

                        BusyIndicator {
                            width: 14
                            height: 14
                            running: panel.busy
                            visible: panel.busy
                        }

                        Text {
                            text: panel.busy ? "整理中..." : "重新整理"
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
                        onClicked: panel.handlePrimaryAction()
                    }
                }

                Rectangle {
                    width: copyText.implicitWidth + 22
                    height: 32
                    radius: 10
                    color: "transparent"
                    border.width: 1
                    border.color: panel.secondaryBorder
                    opacity: (!panel.busy && panel.hasSummary) ? 1 : 0.58

                    Text {
                        id: copyText
                        anchors.centerIn: parent
                        text: "复制内容"
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
            }

            Rectangle {
                id: rewriteBox
                width: parent.width
                height: panel.rewriteBoxHeight
                radius: 12
                color: panel.subtleFill
                border.width: 0

                TextEdit {
                    id: rewriteEdit
                    x: 12
                    y: 10
                    width: parent.width - 24
                    height: parent.height - 20
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    textFormat: TextEdit.PlainText
                    color: panel.bodyText
                    font.family: root.uiFont
                    font.pixelSize: 13
                    font.weight: 400
                    rightPadding: 8
                    bottomPadding: 8

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
                    text: "补充你的修改要求（如：偏客户表达）"
                    color: panel.mutedText
                    font.family: root.uiFont
                    font.pixelSize: 12
                    font.weight: 400
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
                implicitHeight: summaryContent.height

                Flickable {
                    id: summaryFlick
                    anchors.fill: parent
                    clip: true
                    contentWidth: width
                    contentHeight: Math.max(height, summaryContent.height)
                    boundsBehavior: Flickable.StopAtBounds

                    Item {
                        id: summaryContent
                        width: summaryFlick.width
                        height: Math.max(markdownView.contentHeight, errorTextItem.visible ? errorTextItem.y + errorTextItem.implicitHeight : 0)

                        TextEdit {
                            id: markdownView
                            width: parent.width
                            readOnly: true
                            selectByMouse: true
                            selectByKeyboard: true
                            wrapMode: TextEdit.Wrap
                            textFormat: TextEdit.MarkdownText
                            text: panel.hasSummary ? panel.summaryText : (panel.errorText.length > 0 ? panel.errorText : "暂无可查看的阶段总结")
                            color: panel.hasSummary ? panel.bodyText : panel.mutedText
                            font.family: root.uiFont
                            font.pixelSize: 13
                            font.weight: 400
                        }

                        Text {
                            id: errorTextItem
                            y: markdownView.contentHeight + 8
                            width: parent.width
                            visible: panel.errorText.length > 0 && panel.hasSummary
                            wrapMode: Text.Wrap
                            text: panel.errorText
                            color: "#C66A16"
                            font.family: root.uiFont
                            font.pixelSize: 11
                            font.weight: 400
                        }
                    }
                }
            }
        }
    }
}

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
        property string noticeText: todoDetailBridge.stageSummaryNotice
        property bool hasSummary: todoDetailBridge.hasStageSummary
        property bool editMode: false
        property bool syncingSummaryEditor: false

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
        readonly property color panelBorder: "#E5E7EB"
        readonly property color titleText: "#18202E"
        readonly property color bodyText: "#4A5565"
        readonly property color mutedText: "#7A8795"
        readonly property color subtleFill: "#F5F5F5"
        readonly property color contentFill: "#FFFFFF"
        readonly property color contentBorder: "#E5E7EB"
        readonly property color primaryFill: "#2A313F"
        readonly property color primaryInk: "#FFFFFF"
        readonly property color secondaryBorder: "#E5E7EB"
        readonly property color secondaryInk: "#4A5565"
        readonly property color chipBorder: "#E5E7EB"
        readonly property color chipText: "#5B6574"
        readonly property real rewriteBoxMinHeight: 96
        readonly property real chipHeight: 28
        readonly property real chipRadius: 14
        readonly property real chipFontSize: 11
        readonly property real chipHorizontalPadding: 16
        readonly property real contentBoxMinHeight: 96
        readonly property real contentBoxDefaultHeight: 236
        readonly property real contentBoxExpandThreshold: 260
        readonly property real contentBoxAbsoluteMaxHeight: 388
        readonly property real preferredRewriteBoxHeight: Math.max(rewriteBoxMinHeight, rewriteEdit.contentHeight + 18)
        readonly property real contentBoxMeasuredHeight: Math.max(
            112,
            contentLoader.item ? (contentLoader.item.implicitHeight || contentLoader.item.height) + 20 : 112
        )
        readonly property real helperHeight: 36
        readonly property real baseFixedSectionHeight: (
            panelTopPadding + panelBottomPadding + headerBar.height + helperHeight + chipsFlow.implicitHeight + actionRow.height + preferredRewriteBoxHeight + (sectionSpacing * 5)
        )
        readonly property real preferredContentBoxHeight: (
            contentBoxMeasuredHeight > contentBoxExpandThreshold
            ? Math.min(contentBoxMeasuredHeight, contentBoxAbsoluteMaxHeight)
            : Math.max(contentBoxDefaultHeight, contentBoxMeasuredHeight)
        )
        readonly property real preferredHeight: baseFixedSectionHeight + preferredContentBoxHeight
        readonly property real extraVerticalSpace: Math.max(0, root.height - preferredHeight)
        readonly property real contentBoxExtraHeight: extraVerticalSpace * 0.65
        readonly property real rewriteBoxExtraHeight: extraVerticalSpace - contentBoxExtraHeight
        readonly property real rewriteBoxHeight: preferredRewriteBoxHeight + rewriteBoxExtraHeight
        readonly property real fixedSectionHeight: (
            panelTopPadding + panelBottomPadding + headerBar.height + helperHeight + chipsFlow.implicitHeight + actionRow.height + rewriteBoxHeight + (sectionSpacing * 5)
        )
        readonly property real contentBoxAvailableHeight: Math.max(contentBoxMinHeight, root.height - fixedSectionHeight)
        readonly property real contentBoxHeight: Math.max(
            contentBoxMinHeight,
            Math.min(preferredContentBoxHeight + contentBoxExtraHeight, contentBoxAvailableHeight)
        )
        readonly property bool summaryActionEnabled: !panel.busy && panel.summaryText.trim().length > 0
        readonly property bool hasCustomRewriteInput: rewriteEdit.text.trim().length > 0
        readonly property string primaryButtonText: panel.busy ? "整理中..." : (panel.hasCustomRewriteInput ? "按要求重写" : "重新整理")

        function submitCustomRewrite() {
            var value = rewriteEdit.text.trim()
            if (value.length === 0 || panel.busy) {
                return
            }
            panel.editMode = false
            panel.customRewriteRequested(value)
            rewriteEdit.text = ""
        }

        function handlePrimaryAction() {
            if (panel.busy) {
                return
            }
            if (panel.hasCustomRewriteInput) {
                panel.submitCustomRewrite()
                return
            }
            panel.editMode = false
            if (panel.hasSummary) {
                todoDetailBridge.rewriteStageSummaryDefault()
                return
            }
            panel.refreshClicked()
        }

        function syncEditorText(value) {
            if (!contentLoader.item || !contentLoader.item.syncFromPanelText) {
                return
            }
            contentLoader.item.syncFromPanelText(value)
        }

        function toggleEditMode() {
            if (panel.busy) {
                return
            }
            if (!panel.editMode && panel.summaryText.trim().length === 0) {
                return
            }
            panel.editMode = !panel.editMode
            if (panel.editMode) {
                panel.syncEditorText(panel.summaryText)
            }
        }

        onSummaryTextChanged: syncEditorText(summaryText)
        onCloseClicked: todoDetailBridge.toggleStageSummary()
        onCopyClicked: todoDetailBridge.copyStageSummary()
        onRefreshClicked: todoDetailBridge.refreshStageSummary()
        onPresetRewriteRequested: function(key) {
            panel.editMode = false
            todoDetailBridge.rewriteStageSummaryWithPreset(key)
        }
        onCustomRewriteRequested: function(text) {
            panel.editMode = false
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
                        text: "保留 Markdown 结构展示，支持直接编辑内容，也可以按下面要求重写整理。"
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
                    color: closeMouse.containsMouse ? "#F3F5F8" : "transparent"

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
                width: parent.width
                height: panel.helperHeight
                radius: 12
                color: panel.editMode ? "#ECEFF3" : "#F5F5F5"
                border.width: 1
                border.color: panel.editMode ? panel.primaryFill : panel.secondaryBorder

                Row {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    Rectangle {
                        width: 7
                        height: 7
                        radius: 3.5
                        anchors.verticalCenter: parent.verticalCenter
                        color: panel.editMode ? panel.primaryFill : panel.secondaryInk
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: panel.editMode ? "编辑中：当前改动会作为复制和重写整理的基础文本" : "阅读态：直接按 Markdown 结构浏览，保留标题和列表层级"
                        color: panel.editMode ? panel.primaryFill : panel.bodyText
                        font.family: root.uiFont
                        font.pixelSize: 11
                        font.weight: 500
                    }
                }
            }

            Rectangle {
                id: contentBox
                width: parent.width
                height: panel.contentBoxHeight
                color: panel.contentFill
                radius: 16
                border.width: 1
                border.color: panel.editMode ? panel.primaryFill : panel.contentBorder

                Loader {
                    id: contentLoader
                    anchors.fill: parent
                    anchors.margins: 12
                    sourceComponent: panel.busy && !panel.hasSummary ? loadingComponent : contentComponent
                }
            }

            Flow {
                id: chipsFlow
                width: parent.width
                spacing: 6

                Repeater {
                    model: [
                        { key: "shorter", label: "更简短" },
                        { key: "customer", label: "偏客户表述" },
                        { key: "rd", label: "偏研发表述" },
                        { key: "materials", label: "强调已收集材料" }
                    ]

                    delegate: Rectangle {
                        width: chipTextItem.implicitWidth + panel.chipHorizontalPadding
                        height: panel.chipHeight
                        radius: panel.chipRadius
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: panel.chipBorder
                        opacity: panel.summaryActionEnabled ? 1 : 0.58

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
                            enabled: panel.summaryActionEnabled
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
                    width: refreshContent.implicitWidth + 24
                    height: 34
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
                            text: panel.primaryButtonText
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
                    width: editText.implicitWidth + 24
                    height: 34
                    radius: 10
                    color: panel.editMode ? "#ECEFF3" : "transparent"
                    border.width: 1
                    border.color: panel.editMode ? panel.primaryFill : panel.secondaryBorder
                    opacity: (!panel.busy && (panel.summaryText.trim().length > 0 || panel.editMode)) ? 1 : 0.58

                    Text {
                        id: editText
                        anchors.centerIn: parent
                        text: panel.editMode ? "完成编辑" : "编辑内容"
                        color: panel.editMode ? panel.primaryFill : panel.secondaryInk
                        font.family: root.uiFont
                        font.pixelSize: 12
                        font.weight: 500
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: !panel.busy && (panel.summaryText.trim().length > 0 || panel.editMode)
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: panel.toggleEditMode()
                    }
                }

                Rectangle {
                    width: copyText.implicitWidth + 24
                    height: 34
                    radius: 10
                    color: "transparent"
                    border.width: 1
                    border.color: panel.secondaryBorder
                    opacity: panel.summaryActionEnabled ? 1 : 0.58

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
                        enabled: panel.summaryActionEnabled
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: panel.copyClicked()
                    }
                }
            }

            Text {
                width: parent.width
                visible: panel.noticeText.length > 0
                wrapMode: Text.Wrap
                text: panel.noticeText
                color: panel.mutedText
                font.family: root.uiFont
                font.pixelSize: 12
                font.weight: 400
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
                    text: "补充你的调整要求，例如：更适合发客户、保留技术细节、把待确认项再压缩一点。"
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
                implicitHeight: 112

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
                implicitHeight: Math.max(
                    112,
                    contentModeLoader.item ? (contentModeLoader.item.implicitHeight || contentModeLoader.item.height) : 112
                )

                function syncFromPanelText(value) {
                    if (!contentModeLoader.item || !contentModeLoader.item.syncFromPanelText) {
                        return
                    }
                    contentModeLoader.item.syncFromPanelText(value)
                }

                Loader {
                    id: contentModeLoader
                    anchors.fill: parent
                    sourceComponent: panel.editMode ? editorComponent : markdownViewComponent
                }
            }
        }

        Component {
            id: editorComponent

            Item {
                implicitHeight: Math.max(112, editorScroll.height)

                function syncFromPanelText(value) {
                    if (summaryEditor.text === value) {
                        return
                    }
                    panel.syncingSummaryEditor = true
                    var nextCursor = Math.min(summaryEditor.cursorPosition, String(value || "").length)
                    summaryEditor.text = value
                    summaryEditor.cursorPosition = nextCursor
                    panel.syncingSummaryEditor = false
                }

                Component.onCompleted: syncFromPanelText(panel.summaryText)

                ScrollView {
                    id: editorScroll
                    anchors.fill: parent
                    clip: true

                    TextArea {
                        id: summaryEditor
                        width: editorScroll.availableWidth
                        height: Math.max(editorScroll.availableHeight, contentHeight + topPadding + bottomPadding)
                        wrapMode: TextEdit.Wrap
                        selectByMouse: true
                        textFormat: TextEdit.PlainText
                        color: panel.bodyText
                        font.family: root.uiFont
                        font.pixelSize: 13
                        font.weight: 400
                        placeholderText: "整理结果会显示在这里，也支持直接编辑。"
                        padding: 4
                        leftPadding: 4
                        rightPadding: 4
                        topPadding: 4
                        bottomPadding: 4
                        background: null

                        onTextChanged: {
                            if (panel.syncingSummaryEditor || text === panel.summaryText) {
                                return
                            }
                            todoDetailBridge.updateStageSummaryText(text)
                        }
                    }
                }
            }
        }

        Component {
            id: markdownViewComponent

            Item {
                implicitHeight: Math.max(112, markdownScroll.height)

                ScrollView {
                    id: markdownScroll
                    anchors.fill: parent
                    clip: true

                    Item {
                        width: markdownScroll.availableWidth
                        height: Math.max(
                            markdownScroll.availableHeight,
                            summaryMarkdown.contentHeight + (errorBox.visible ? errorTextItem.implicitHeight + 20 : 0)
                        )

                        TextEdit {
                            id: summaryMarkdown
                            width: parent.width
                            readOnly: true
                            selectByMouse: true
                            selectByKeyboard: true
                            wrapMode: TextEdit.WrapAtWordBoundaryOrAnywhere
                            textFormat: TextEdit.MarkdownText
                            text: panel.hasSummary ? panel.summaryText : ""
                            color: panel.hasSummary ? panel.bodyText : panel.mutedText
                            font.family: root.uiFont
                            font.pixelSize: 13
                            font.weight: 400
                            leftPadding: 2
                            rightPadding: 2
                            topPadding: 2
                            bottomPadding: 2
                            visible: panel.hasSummary
                        }

                        Text {
                            id: emptyText
                            anchors.centerIn: parent
                            visible: !panel.hasSummary && panel.errorText.length === 0
                            text: "暂无可查看的阶段总结"
                            color: panel.mutedText
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 400
                        }

                        Rectangle {
                            id: errorBox
                            x: 0
                            y: panel.hasSummary ? summaryMarkdown.contentHeight + 10 : 0
                            width: parent.width
                            height: errorTextItem.implicitHeight + 20
                            radius: 12
                            color: "#FFF6F0"
                            border.width: 1
                            border.color: "#F0D7C3"
                            visible: panel.errorText.length > 0

                            Text {
                                id: errorTextItem
                                anchors.fill: parent
                                anchors.margins: 10
                                wrapMode: Text.Wrap
                                text: panel.errorText
                                color: "#8E4F1F"
                                font.family: root.uiFont
                                font.pixelSize: 12
                                font.weight: 400
                            }
                        }

                    }
                }
            }
        }

        Item {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            width: 24
            height: 24
            z: 20

            Rectangle {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                width: 12
                height: 12
                radius: 4
                color: panel.chipBorder
                opacity: 0.95
            }

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.LeftButton
                cursorShape: Qt.SizeFDiagCursor
                onPressed: stageSummaryWindowBridge.startPanelResize("bottom_right")
            }
        }
    }
}

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

    function sectionPalette(title) {
        var normalized = String(title || "")
        if (normalized.indexOf("当前结论") !== -1) {
            return {
                fill: "#FFF7E8",
                border: "#F0D39E",
                tagFill: "#F6E2B8",
                title: "#7A4B00",
                body: "#5C420F",
                bullet: "#C48A22"
            }
        }
        if (normalized.indexOf("已发生进展") !== -1) {
            return {
                fill: "#F2FAF6",
                border: "#CFE8D6",
                tagFill: "#DDF2E4",
                title: "#1F6A44",
                body: "#244B38",
                bullet: "#3AA66B"
            }
        }
        if (normalized.indexOf("待确认事项") !== -1) {
            return {
                fill: "#FFF6F0",
                border: "#F0D7C3",
                tagFill: "#F7E4D6",
                title: "#8E4F1F",
                body: "#65412B",
                bullet: "#D07A3A"
            }
        }
        return {
            fill: "#F3F7FF",
            border: "#D6E3FF",
            tagFill: "#E5EEFF",
            title: "#2E5AAC",
            body: "#24334D",
            bullet: "#4B7CFF"
        }
    }

    function buildSummarySections(text) {
        var normalized = String(text || "").replace(/\r\n/g, "\n").trim()
        if (!normalized.length) {
            return []
        }

        function pushSection(target, title, rawLines) {
            var cleanTitle = String(title || "").trim() || "阶段总结"
            var bodyLines = []
            var bullets = []
            var paragraphBuffer = []
            var sourceText = rawLines.join("\n").trim()

            function flushParagraph() {
                if (!paragraphBuffer.length) {
                    return
                }
                bodyLines.push(paragraphBuffer.join(" "))
                paragraphBuffer = []
            }

            if (sourceText.length) {
                var lines = sourceText.split("\n")
                for (var index = 0; index < lines.length; index += 1) {
                    var rawLine = lines[index]
                    var trimmed = rawLine.trim()
                    if (!trimmed.length) {
                        flushParagraph()
                        continue
                    }

                    var bulletMatch = trimmed.match(/^[-*]\s+(.+)$/)
                    if (!bulletMatch) {
                        bulletMatch = trimmed.match(/^\d+\.\s+(.+)$/)
                    }
                    if (bulletMatch) {
                        flushParagraph()
                        bullets.push(String(bulletMatch[1] || "").trim())
                        continue
                    }
                    paragraphBuffer.push(trimmed)
                }
                flushParagraph()
            }

            target.push({
                title: cleanTitle,
                body: bodyLines.join("\n\n"),
                bullets: bullets,
                palette: root.sectionPalette(cleanTitle)
            })
        }

        var sections = []
        var currentTitle = ""
        var currentLines = []
        var rawLines = normalized.split("\n")
        for (var lineIndex = 0; lineIndex < rawLines.length; lineIndex += 1) {
            var line = rawLines[lineIndex]
            var trimmedLine = line.trim()
            var headingMatch = trimmedLine.match(/^#{1,6}\s*(.+)$/)
            if (headingMatch) {
                if (currentTitle.length || currentLines.length) {
                    pushSection(sections, currentTitle, currentLines)
                }
                currentTitle = String(headingMatch[1] || "").trim()
                currentLines = []
                continue
            }
            if (!currentTitle.length && !sections.length && !currentLines.length) {
                currentTitle = "阶段总结"
            }
            currentLines.push(line)
        }

        if (currentTitle.length || currentLines.length) {
            pushSection(sections, currentTitle, currentLines)
        }
        return sections
    }

    Rectangle {
        id: panel
        anchors.fill: parent
        property bool busy: todoDetailBridge.stageSummaryBusy
        property string summaryText: todoDetailBridge.stageSummaryText
        property string errorText: todoDetailBridge.stageSummaryError
        property bool hasSummary: todoDetailBridge.hasStageSummary
        property bool editMode: false
        property bool syncingSummaryEditor: false
        property var summarySections: root.buildSummarySections(summaryText)

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
        readonly property color panelBorder: "#E7ECF3"
        readonly property color titleText: "#152033"
        readonly property color bodyText: "#223047"
        readonly property color mutedText: "#7B8797"
        readonly property color chipBorder: "#D8DEE8"
        readonly property color chipText: "#5F6C80"
        readonly property color subtleFill: "#F7F9FC"
        readonly property color primaryFill: "#171F2E"
        readonly property color primaryInk: "#FFFFFF"
        readonly property color secondaryBorder: "#D7DDE6"
        readonly property color secondaryInk: "#334155"
        readonly property real rewriteBoxMinHeight: 96
        readonly property real chipHeight: 28
        readonly property real chipRadius: 14
        readonly property real chipFontSize: 11
        readonly property real chipHorizontalPadding: 16
        readonly property real contentBoxMinHeight: 96
        readonly property real contentBoxDefaultHeight: 252
        readonly property real contentBoxExpandThreshold: 280
        readonly property real contentBoxAbsoluteMaxHeight: 392
        readonly property real preferredRewriteBoxHeight: Math.max(rewriteBoxMinHeight, rewriteEdit.contentHeight + 18)
        readonly property real contentBoxMeasuredHeight: Math.max(
            92,
            contentLoader.item ? (contentLoader.item.implicitHeight || contentLoader.item.height) + 20 : 92
        )
        readonly property real baseFixedSectionHeight: (
            panelTopPadding + panelBottomPadding + headerBar.height + helperStrip.height + chipsFlow.implicitHeight + actionRow.height + preferredRewriteBoxHeight + (sectionSpacing * 5)
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
            panelTopPadding + panelBottomPadding + headerBar.height + helperStrip.height + chipsFlow.implicitHeight + actionRow.height + rewriteBoxHeight + (sectionSpacing * 5)
        )
        readonly property real contentBoxAvailableHeight: Math.max(
            contentBoxMinHeight,
            root.height - fixedSectionHeight
        )
        readonly property real contentBoxHeight: Math.max(
            contentBoxMinHeight,
            Math.min(preferredContentBoxHeight + contentBoxExtraHeight, contentBoxAvailableHeight)
        )
        readonly property bool summaryActionEnabled: !panel.busy && panel.summaryText.trim().length > 0

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
        onCopyClicked: todoDetailBridge.copyStageSummary()
        onRefreshClicked: {
            panel.editMode = false
            todoDetailBridge.refreshStageSummary()
        }
        onCloseClicked: todoDetailBridge.toggleStageSummary()
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
                        text: "先按四段结构看重点，需要的话可以直接在内容区修改后再复制或二次整理。"
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
                id: helperStrip
                width: parent.width
                height: 36
                radius: 12
                color: panel.editMode ? "#FFF7E8" : "#F3F7FF"
                border.width: 1
                border.color: panel.editMode ? "#F0D39E" : "#DCE7FF"

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
                        color: panel.editMode ? "#D4942E" : "#5A84FF"
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: panel.editMode ? "编辑中：复制和重新整理都会使用当前文本" : "阅读态：按分段卡片展示，重点更容易扫到"
                        color: panel.editMode ? "#7A4B00" : "#2E5AAC"
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
                color: panel.editMode ? "#FFFDFC" : panel.subtleFill
                radius: 16
                border.width: panel.editMode ? 1 : 0
                border.color: panel.editMode ? "#F0D39E" : "transparent"

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
                    width: editText.implicitWidth + 24
                    height: 34
                    radius: 10
                    color: panel.editMode ? "#FFF7E8" : "transparent"
                    border.width: 1
                    border.color: panel.editMode ? "#F0D39E" : panel.secondaryBorder
                    opacity: (!panel.busy && (panel.summaryText.trim().length > 0 || panel.editMode)) ? 1 : 0.58

                    Text {
                        id: editText
                        anchors.centerIn: parent
                        text: panel.editMode ? "完成编辑" : "编辑内容"
                        color: panel.editMode ? "#7A4B00" : panel.secondaryInk
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
                    108,
                    contentModeLoader.item ? (contentModeLoader.item.implicitHeight || contentModeLoader.item.height) : 108
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
                    sourceComponent: panel.editMode ? editorComponent : summaryViewComponent
                }
            }
        }

        Component {
            id: editorComponent

            Item {
                id: editorView
                implicitHeight: Math.max(108, summaryEditor.contentHeight + 18)

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
                        padding: 2
                        leftPadding: 2
                        rightPadding: 2
                        topPadding: 2
                        bottomPadding: 2
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
            id: summaryViewComponent

            Item {
                id: summaryView
                implicitHeight: Math.max(108, summaryColumn.implicitHeight)

                Flickable {
                    id: summaryFlick
                    anchors.fill: parent
                    clip: true
                    contentWidth: width
                    contentHeight: Math.max(height, summaryColumn.implicitHeight)
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }

                    Column {
                        id: summaryColumn
                        width: summaryFlick.width
                        spacing: 10

                        Repeater {
                            model: panel.summarySections

                            delegate: Rectangle {
                                id: sectionCard
                                property var sectionData: modelData
                                readonly property real contentPadding: 14
                                width: summaryColumn.width
                                height: sectionContent.implicitHeight + contentPadding * 2
                                radius: 14
                                color: sectionData.palette.fill
                                border.width: 1
                                border.color: sectionData.palette.border
                                visible: panel.summarySections.length > 0

                                Column {
                                    id: sectionContent
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.leftMargin: sectionCard.contentPadding
                                    anchors.rightMargin: sectionCard.contentPadding
                                    anchors.topMargin: sectionCard.contentPadding
                                    spacing: 10

                                    Rectangle {
                                        width: titleTextItem.implicitWidth + 16
                                        height: 24
                                        radius: 12
                                        color: sectionCard.sectionData.palette.tagFill

                                        Text {
                                            id: titleTextItem
                                            anchors.centerIn: parent
                                            text: sectionCard.sectionData.title
                                            color: sectionCard.sectionData.palette.title
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            font.weight: 600
                                        }
                                    }

                                    Text {
                                        visible: sectionCard.sectionData.body.length > 0
                                        width: parent.width
                                        wrapMode: Text.Wrap
                                        lineHeightMode: Text.ProportionalHeight
                                        lineHeight: 1.25
                                        text: sectionCard.sectionData.body
                                        color: sectionCard.sectionData.palette.body
                                        font.family: root.uiFont
                                        font.pixelSize: 13
                                        font.weight: 500
                                    }

                                    Column {
                                        width: parent.width
                                        spacing: 8
                                        visible: sectionCard.sectionData.bullets.length > 0

                                        Repeater {
                                            model: sectionCard.sectionData.bullets

                                            delegate: Row {
                                                width: parent.width
                                                spacing: 8

                                                Rectangle {
                                                    width: 6
                                                    height: 6
                                                    radius: 3
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    color: sectionCard.sectionData.palette.bullet
                                                }

                                                Text {
                                                    width: Math.max(0, parent.width - 14)
                                                    wrapMode: Text.Wrap
                                                    lineHeightMode: Text.ProportionalHeight
                                                    lineHeight: 1.25
                                                    text: modelData
                                                    color: "#2A3445"
                                                    font.family: root.uiFont
                                                    font.pixelSize: 13
                                                    font.weight: 400
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            id: errorCardWithSummary
                            width: summaryColumn.width
                            height: errorTextWithSummary.implicitHeight + 28
                            radius: 14
                            color: "#FFF6F0"
                            border.width: 1
                            border.color: "#F0D7C3"
                            visible: panel.errorText.length > 0 && panel.hasSummary

                            Text {
                                id: errorTextWithSummary
                                anchors.fill: parent
                                anchors.margins: 14
                                wrapMode: Text.Wrap
                                text: panel.errorText
                                color: "#8E4F1F"
                                font.family: root.uiFont
                                font.pixelSize: 12
                                font.weight: 400
                            }
                        }

                        Item {
                            width: summaryColumn.width
                            height: emptyText.implicitHeight
                            visible: !panel.hasSummary && panel.errorText.length === 0

                            Text {
                                id: emptyText
                                anchors.centerIn: parent
                                text: "暂无可查看的阶段总结"
                                color: panel.mutedText
                                font.family: root.uiFont
                                font.pixelSize: 12
                                font.weight: 400
                            }
                        }

                        Rectangle {
                            id: errorCardOnly
                            width: summaryColumn.width
                            height: errorTextOnly.implicitHeight + 28
                            radius: 14
                            color: "#FFF6F0"
                            border.width: 1
                            border.color: "#F0D7C3"
                            visible: !panel.hasSummary && panel.errorText.length > 0

                            Text {
                                id: errorTextOnly
                                anchors.fill: parent
                                anchors.margins: 14
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

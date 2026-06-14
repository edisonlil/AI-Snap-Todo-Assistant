import QtQuick
import QtQuick.Controls
import "TimelineCardMapper.js" as TimelineCardMapper

Rectangle {
    id: root
    width: 396
    height: 760
    color: "transparent"
    focus: true
    readonly property int mainPanelWidth: 396
    onTimelineCommandMenuVisibleChanged: {
        if (timelineCommandMenuVisible) {
            updateTimelineCommandMenuGeometry()
        }
    }

    readonly property var themeTokens: typeof theme !== "undefined" ? theme : ({})
    readonly property var detailBridge: typeof todoDetailBridge !== "undefined" ? todoDetailBridge : null
    readonly property var productLineOptions: detailBridge ? detailBridge.productLineOptions : []
    readonly property string productLineValue: detailBridge ? detailBridge.productLine : ""
    readonly property color shellBg: themeTokens.shellBg || "#FFFFFF"
    readonly property color panelBg: themeTokens.panelBg || "#FFFFFF"
    readonly property color panelLine: themeTokens.panelLine || "#E5E7EB"
    readonly property color sectionLine: themeTokens.sectionLine || "#E5E7EB"
    readonly property color titleInk: themeTokens.titleInk || "#18202E"
    readonly property color bodyInk: themeTokens.bodyInk || "#4A5565"
    readonly property color labelInk: themeTokens.labelInk || "#9AA4B3"
    readonly property color mutedInk: themeTokens.mutedInk || "#A9B1BD"
    readonly property color fieldBg: themeTokens.fieldBg || "#F8F9FA"
    readonly property color fieldLine: themeTokens.fieldLine || "#E5E7EB"
    readonly property color timelineBg: themeTokens.timelineBg || "#F8F9FA"
    readonly property color accent: themeTokens.accent || "#2A313F"
    readonly property color accentTint: themeTokens.accentTint || "#ECEFF3"
    readonly property string uiFont: themeTokens.uiFont || (detailBridge ? detailBridge.uiFont : "Microsoft YaHei UI")
    readonly property int outerPadding: 24
    readonly property int contentTopPadding: 16
    readonly property int sectionGap: 16
    readonly property int cardRadius: 24
    readonly property int contentWidth: mainPanelWidth - outerPadding * 2
    readonly property int fieldGap: 12
    readonly property int fieldWidth: (contentWidth - fieldGap) / 2
    readonly property int fieldCardHeight: 64
    readonly property int fieldTextInset: 16
    readonly property int labelGap: 8
    readonly property int titleWeight: 600
    readonly property int sectionWeight: 600
    readonly property int labelWeight: 500
    readonly property int bodyWeight: 400
    readonly property int actionButtonWidth: 62
    property bool syncingFields: false
    property bool syncingTimelineDraft: false
    property string activeAttachmentEventId: ""
    property int syncedTodoSessionRevision: -1
    property string timelineEntryType: "follow_up"
    property bool timelineEntryTypeSelected: false
    property bool timelineCommandMenuVisible: false
    property int timelineCommandSelectedIndex: 0
    property real timelineCommandMenuX: 0
    property real timelineCommandMenuY: 0
    property real timelineCommandMenuWidth: 0
    property string activeTimelineEditingEventId: ""
    property var timelineCardRegistry: ({})
    property var timelineEditorRegistry: ({})
    property var timelineCommandOptions: [
        { "value": "follow_up", "label": "问题反馈", "detail": "写入时间线" },
        { "value": "conclusion", "label": "问题结论", "detail": "写入问题结论并保留结论记录" },
        { "value": "log_analysis", "label": "分析日志", "detail": "后台异步排查当前附件" }
    ]

    function timelineEntryLabel(entryType) {
        return entryType === "conclusion" ? "问题结论" : (entryType === "log_analysis" ? "分析日志" : "问题反馈")
    }

    function timelineEntryPlaceholder() {
        return "输入 / 选择问题反馈、问题结论或分析日志"
    }

    function stripTimelineCommandPrefix(text) {
        var trimmed = text.trim()
        var prefixes = ["/问题反馈", "/问题跟进", "/问题结论", "/分析日志"]
        for (var index = 0; index < prefixes.length; index += 1) {
            var prefix = prefixes[index]
            if (trimmed === prefix) {
                return ""
            }
            if (trimmed.indexOf(prefix + " ") === 0 || trimmed.indexOf(prefix + "\n") === 0) {
                return trimmed.slice(prefix.length).trim()
            }
        }
        if (trimmed === "/") {
            return ""
        }
        return text
    }

    function clearTimelineEntryType() {
        timelineCommandSelectedIndex = 0
        timelineCommandMenuVisible = false
        todoDetailBridge.clearTimelineDraftEntryType()
        addTimelineEdit.forceActiveFocus()
    }

    function selectTimelineEntryType(entryType) {
        timelineCommandMenuVisible = false
        todoDetailBridge.setTimelineDraftEntryType(entryType)
        var nextText = stripTimelineCommandPrefix(addTimelineEdit.text)
        if (nextText !== addTimelineEdit.text) {
            syncingTimelineDraft = true
            addTimelineEdit.text = nextText
            syncingTimelineDraft = false
            todoDetailBridge.updateTimelineDraftText(nextText)
        }
        addTimelineEdit.forceActiveFocus()
    }

    function syncTimelineCommandSelection() {
        for (var index = 0; index < timelineCommandOptions.length; index += 1) {
            if (timelineCommandOptions[index].value === timelineEntryType) {
                timelineCommandSelectedIndex = index
                return
            }
        }
        timelineCommandSelectedIndex = 0
    }

    function moveTimelineCommandSelection(step) {
        if (!timelineCommandMenuVisible) {
            timelineCommandMenuVisible = true
            syncTimelineCommandSelection()
            updateTimelineCommandMenuGeometry()
            return
        }
        var total = timelineCommandOptions.length
        if (total <= 0) {
            return
        }
        timelineCommandSelectedIndex = (timelineCommandSelectedIndex + step + total) % total
    }

    function confirmTimelineCommandSelection() {
        if (!timelineCommandMenuVisible) {
            return false
        }
        if (timelineCommandSelectedIndex < 0 || timelineCommandSelectedIndex >= timelineCommandOptions.length) {
            return false
        }
        selectTimelineEntryType(timelineCommandOptions[timelineCommandSelectedIndex].value)
        return true
    }

    function syncTimelineCommandState() {
        if (syncingTimelineDraft) {
            return
        }
        var trimmed = addTimelineEdit.text.trim()
        if (timelineEntryTypeSelected) {
            timelineCommandMenuVisible = false
            return
        }

        if (trimmed.indexOf("/问题结论") === 0) {
            selectTimelineEntryType("conclusion")
            return
        }
        if (trimmed.indexOf("/问题反馈") === 0 || trimmed.indexOf("/问题跟进") === 0) {
            selectTimelineEntryType("follow_up")
            return
        }
        if (trimmed.indexOf("/分析日志") === 0) {
            selectTimelineEntryType("log_analysis")
            return
        }

        if (trimmed === "/" || trimmed.indexOf("/问题") === 0 || trimmed.indexOf("/分析") === 0) {
            timelineCommandMenuVisible = true
            syncTimelineCommandSelection()
            updateTimelineCommandMenuGeometry()
        } else if (trimmed.length === 0 || trimmed.charAt(0) !== "/") {
            timelineCommandMenuVisible = false
        }
    }

    function submitTimelineEntry() {
        if (addTimelineEdit.text.trim().length === 0 && timelineEntryType !== "log_analysis") {
            return
        }
        todoDetailBridge.addTimelineEntry(addTimelineEdit.text, timelineEntryType)
    }

    function syncTimelineDraft() {
        if (!root.detailBridge) {
            return
        }
        syncingTimelineDraft = true
        timelineEntryType = todoDetailBridge.timelineDraftEntryType
        timelineEntryTypeSelected = todoDetailBridge.timelineDraftEntryTypeSelected
        syncTimelineCommandSelection()
        if (addTimelineEdit.text !== todoDetailBridge.timelineDraftText) {
            addTimelineEdit.text = todoDetailBridge.timelineDraftText
        }
        syncingTimelineDraft = false
    }

    function resetTransientComposerUi() {
        timelineCommandMenuVisible = false
        activeAttachmentEventId = ""
        cancelActiveTimelineEdit()
    }

    function selectProductLine(value) {
        if (!root.detailBridge) {
            return
        }
        todoDetailBridge.selectProductLine(value)
    }

    function optionIndex(options, value) {
        var target = String(value || "")
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index] || "") === target) {
                return index
            }
        }
        return -1
    }

    function updateTimelineCommandMenuGeometry() {
        if (!timelineCommandMenuVisible || !addTimelineEdit || !timelineCommandOverlayLayer) {
            return
        }
        var topLeft = addTimelineEdit.mapToItem(timelineCommandOverlayLayer, 0, 0)
        timelineCommandMenuX = topLeft.x
        timelineCommandMenuY = topLeft.y + addTimelineEdit.height + 6
        timelineCommandMenuWidth = addTimelineEdit.width
    }

    function handleTimelineCommandRemoval() {
        if (!timelineEntryTypeSelected) {
            return false
        }
        if (addTimelineEdit.text.length > 0) {
            return false
        }
        if (addTimelineEdit.selectionStart !== addTimelineEdit.selectionEnd) {
            return false
        }
        if (addTimelineEdit.cursorPosition !== 0) {
            return false
        }
        clearTimelineEntryType()
        return true
    }

    function syncFields() {
        if (!root.detailBridge) {
            return
        }
        syncingFields = true
        titleEdit.text = todoDetailBridge.title
        groupNameEdit.text = todoDetailBridge.groupName
        environmentEdit.text = todoDetailBridge.environment
        productLineFallbackEdit.text = todoDetailBridge.productLine
        productLineEdit.currentIndex = optionIndex(root.productLineOptions, root.productLineValue)
        ticketTypeEdit.text = todoDetailBridge.ticketType
        summaryEdit.text = todoDetailBridge.currentSummary
        syncingFields = false

        var nextRevision = todoDetailBridge.todoSessionRevision
        if (syncedTodoSessionRevision !== nextRevision) {
            syncedTodoSessionRevision = nextRevision
            resetTransientComposerUi()
        }
    }

    function pushField(name, value) {
        if (!syncingFields) {
            todoDetailBridge.updateField(name, value)
        }
    }

    function markAttachmentTarget(eventId) {
        activeAttachmentEventId = eventId || ""
    }

    function formatFileSize(sizeBytes) {
        var value = Number(sizeBytes || 0)
        if (value <= 0) {
            return ""
        }
        if (value < 1024) {
            return value + " B"
        }
        if (value < 1024 * 1024) {
            return (value / 1024).toFixed(1) + " KB"
        }
        return (value / (1024 * 1024)).toFixed(1) + " MB"
    }

    function registerTimelineCard(eventId, item) {
        if (!eventId || !item) {
            return
        }
        var nextRegistry = {}
        for (var key in timelineCardRegistry) {
            nextRegistry[key] = timelineCardRegistry[key]
        }
        nextRegistry[eventId] = item
        timelineCardRegistry = nextRegistry
    }

    function unregisterTimelineCard(eventId, item) {
        if (!eventId) {
            return
        }
        var nextRegistry = {}
        for (var key in timelineCardRegistry) {
            if (key === eventId && timelineCardRegistry[key] === item) {
                continue
            }
            nextRegistry[key] = timelineCardRegistry[key]
        }
        timelineCardRegistry = nextRegistry
    }

    function registerTimelineEditorCard(eventId, item) {
        if (!eventId || !item) {
            return
        }
        var nextRegistry = {}
        for (var key in timelineEditorRegistry) {
            nextRegistry[key] = timelineEditorRegistry[key]
        }
        nextRegistry[eventId] = item
        timelineEditorRegistry = nextRegistry
    }

    function unregisterTimelineEditorCard(eventId, item) {
        if (!eventId) {
            return
        }
        var nextRegistry = {}
        for (var key in timelineEditorRegistry) {
            if (key === eventId && timelineEditorRegistry[key] === item) {
                continue
            }
            nextRegistry[key] = timelineEditorRegistry[key]
        }
        timelineEditorRegistry = nextRegistry
        if (activeTimelineEditingEventId === eventId && !timelineEditorRegistry[eventId]) {
            activeTimelineEditingEventId = ""
        }
    }

    function requestTimelineEdit(eventId) {
        var nextEventId = String(eventId || "").trim()
        if (nextEventId.length === 0) {
            return false
        }
        if (activeTimelineEditingEventId === nextEventId) {
            return true
        }
        var currentEventId = activeTimelineEditingEventId
        if (currentEventId.length > 0) {
            var currentCard = timelineEditorRegistry[currentEventId]
            if (currentCard && currentCard.cancelEditingForSwitch) {
                currentCard.cancelEditingForSwitch()
            } else {
                activeTimelineEditingEventId = ""
            }
        }
        activeTimelineEditingEventId = nextEventId
        return true
    }

    function cancelActiveTimelineEdit() {
        var currentEventId = String(activeTimelineEditingEventId || "").trim()
        if (currentEventId.length === 0) {
            return
        }
        var currentCard = timelineEditorRegistry[currentEventId]
        if (currentCard && currentCard.cancelEditingForSwitch) {
            currentCard.cancelEditingForSwitch()
        } else {
            activeTimelineEditingEventId = ""
        }
    }

    function exitTimelineEdit(eventId) {
        var targetEventId = String(eventId || "").trim()
        if (targetEventId.length === 0) {
            return
        }
        if (activeTimelineEditingEventId === targetEventId) {
            activeTimelineEditingEventId = ""
        }
    }

    function scrollToTimelineEvent(eventId) {
        if (!eventId || !timelineCardRegistry[eventId]) {
            return
        }
        var targetItem = timelineCardRegistry[eventId]
        var point = targetItem.mapToItem(contentColumn, 0, 0)
        var maxContentY = Math.max(0, flick.contentHeight - flick.height)
        flick.contentY = Math.max(0, Math.min(point.y - 12, maxContentY))
    }

    Connections {
        target: root.detailBridge
        function onDataChanged() {
            root.syncFields()
        }
        function onTimelineChanged() {
            if (root.activeAttachmentEventId.length === 0) {
                return
            }
            for (var index = 0; index < todoDetailBridge.timeline.length; index += 1) {
                if (String(todoDetailBridge.timeline[index].id || "") === root.activeAttachmentEventId) {
                    return
                }
            }
            root.activeAttachmentEventId = ""
        }
        function onTimelineDraftChanged() {
            root.syncTimelineDraft()
        }
    }

    Connections {
        target: flick
        function onContentYChanged() {
            root.updateTimelineCommandMenuGeometry()
        }
        function onHeightChanged() {
            root.updateTimelineCommandMenuGeometry()
        }
        function onWidthChanged() {
            root.updateTimelineCommandMenuGeometry()
        }
    }

    Shortcut {
        sequences: [StandardKey.Paste]
        enabled: addTimelineEdit.activeFocus || root.activeAttachmentEventId.length > 0
        onActivated: {
            if (addTimelineEdit.activeFocus) {
                todoDetailBridge.requestDraftTimelineClipboardImagePaste()
                return
            }
            todoDetailBridge.requestClipboardImagePaste(root.activeAttachmentEventId)
        }
    }

    Timer {
        interval: 1000
        running: root.detailBridge ? todoDetailBridge.environmentAccessPopoverOpen : false
        repeat: true
        onTriggered: if (root.detailBridge) todoDetailBridge.refreshEnvironmentOtpState()
    }

    Rectangle {
        id: mainShell
        width: root.mainPanelWidth
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        radius: root.cardRadius
        color: root.panelBg
        border.width: 0
        border.color: root.panelLine
        antialiasing: true

        Rectangle {
            anchors.fill: parent
            anchors.margins: 0
            radius: root.cardRadius
            color: root.shellBg
            opacity: 0.2
        }

        Item {
            anchors.fill: parent

            Item {
                id: header
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 54

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    onPressed: function(mouse) {
                        todoDetailBridge.beginPanelDrag(mouse.x, mouse.y)
                    }
                    onPositionChanged: function(mouse) {
                        if (mouse.buttons & Qt.LeftButton) {
                            todoDetailBridge.updatePanelDrag()
                        }
                    }
                    onReleased: todoDetailBridge.finishPanelDrag()
                    onCanceled: todoDetailBridge.finishPanelDrag()
                }

                Text {
                    x: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    text: "待办详情"
                    color: root.titleInk
                    font.family: root.uiFont
                    font.pixelSize: 17
                    font.weight: root.titleWeight
                }

                Row {
                    z: 1
                    anchors.right: parent.right
                    anchors.rightMargin: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    Rectangle {
                        width: closeText.implicitWidth + 24
                        height: 32
                        radius: 16
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: root.fieldLine

                        Text {
                            id: closeText
                            anchors.centerIn: parent
                            text: "关闭"
                            color: root.bodyInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 700
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: todoDetailBridge.closePanel()
                        }
                    }

                    Rectangle {
                        width: saveText.implicitWidth + 24
                        height: 32
                        radius: 16
                        color: root.accent
                        border.width: 0
                        border.color: "transparent"

                        Text {
                            id: saveText
                            anchors.centerIn: parent
                            text: "保存"
                            color: "#FFFFFF"
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 700
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: todoDetailBridge.saveTodo()
                        }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                height: 1
                color: root.sectionLine
            }

            Flickable {
                id: flick
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                anchors.bottom: parent.bottom
                clip: true
                contentWidth: width
                contentHeight: contentColumn.implicitHeight + 24
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: contentColumn
                    x: root.outerPadding
                    y: root.contentTopPadding
                    width: root.contentWidth
                    spacing: root.sectionGap

                    Item {
                        width: parent.width
                        height: Math.max(42, titleEdit.contentHeight + 6)

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
                        height: Math.max(leftFieldColumn.implicitHeight, rightFieldColumn.implicitHeight)

                        Column {
                            id: leftFieldColumn
                            anchors.left: parent.left
                            anchors.top: parent.top
                            width: root.fieldWidth
                            spacing: root.fieldGap

                            Rectangle {
                                width: parent.width
                                height: root.fieldCardHeight
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: root.fieldTextInset
                                    y: 13
                                    text: "群聊名称"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: groupNameEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
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
                                id: productLineField
                                width: parent.width
                                height: root.fieldCardHeight
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: root.fieldTextInset
                                    y: 13
                                    text: "产品线"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: productLineFallbackEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
                                    height: 22
                                    visible: root.productLineOptions.length <= 1
                                    clip: true
                                    readOnly: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                }

                                ComboBox {
                                    id: productLineEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
                                    height: 22
                                    visible: root.productLineOptions.length > 1
                                    model: root.productLineOptions
                                    currentIndex: root.optionIndex(root.productLineOptions, root.productLineValue)
                                    enabled: root.productLineOptions.length > 1
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    onActivated: if (currentIndex >= 0) root.selectProductLine(root.productLineOptions[currentIndex])

                                    contentItem: Text {
                                        text: productLineEdit.currentIndex >= 0 ? productLineEdit.displayText : productLineFallbackEdit.text
                                        color: root.titleInk
                                        font.family: root.uiFont
                                        font.pixelSize: 13
                                        font.weight: root.bodyWeight
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }

                                    indicator: Text {
                                        x: productLineEdit.width - width
                                        y: 0
                                        width: 14
                                        height: productLineEdit.height
                                        text: productLineEdit.popup.visible ? "⌃" : "⌄"
                                        color: productLineEdit.hovered || productLineEdit.popup.visible ? root.accent : root.labelInk
                                        visible: root.productLineOptions.length > 1
                                        font.family: root.uiFont
                                        font.pixelSize: 14
                                        horizontalAlignment: Text.AlignRight
                                        verticalAlignment: Text.AlignVCenter
                                    }

                                    background: Item {}

                                    delegate: ItemDelegate {
                                        id: productLineOption
                                        width: productLineEdit.width
                                        height: 36
                                        padding: 0
                                        highlighted: productLineEdit.highlightedIndex === index

                                        background: Rectangle {
                                            anchors.fill: parent
                                            anchors.leftMargin: 4
                                            anchors.rightMargin: 4
                                            anchors.topMargin: 2
                                            anchors.bottomMargin: 2
                                            radius: 10
                                            color: productLineEdit.currentIndex === index ? root.accentTint : (productLineOption.hovered || productLineOption.highlighted ? "#F6F8FA" : "transparent")
                                        }

                                        contentItem: Text {
                                            leftPadding: 12
                                            rightPadding: 12
                                            text: modelData
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: productLineEdit.currentIndex === index ? root.labelWeight : root.bodyWeight
                                            verticalAlignment: Text.AlignVCenter
                                            elide: Text.ElideRight
                                        }
                                    }

                                    popup: Popup {
                                        y: productLineEdit.height + 8
                                        width: productLineEdit.width
                                        implicitHeight: Math.min(contentItem.implicitHeight + 8, 148)
                                        padding: 4
                                        modal: false
                                        focus: true
                                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

                                        background: Rectangle {
                                            radius: 14
                                            color: "#FFFFFF"
                                            border.width: 1
                                            border.color: "#DDE3EB"
                                        }

                                        contentItem: ListView {
                                            clip: true
                                            implicitHeight: contentHeight
                                            model: productLineEdit.popup.visible ? productLineEdit.delegateModel : null
                                            currentIndex: productLineEdit.highlightedIndex
                                            boundsBehavior: Flickable.StopAtBounds
                                        }
                                    }
                                }
                            }
                        }

                        Column {
                            id: rightFieldColumn
                            anchors.right: parent.right
                            anchors.top: parent.top
                            width: root.fieldWidth
                            spacing: root.fieldGap

                            Rectangle {
                                width: parent.width
                                height: root.fieldCardHeight
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: root.fieldTextInset
                                    y: 13
                                    text: "环境"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: environmentEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
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
                                height: root.fieldCardHeight
                                radius: 16
                                color: root.fieldBg
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: root.fieldTextInset
                                    y: 13
                                    text: "工单类型"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: ticketTypeEdit
                                    x: root.fieldTextInset
                                    y: 35
                                    width: parent.width - root.fieldTextInset * 2
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

                    Item {
                        width: parent.width
                        height: 32

                        Rectangle {
                            id: envAccessTrigger
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            radius: 15
                            height: 30
                            width: envAccessLabel.implicitWidth + 24
                            color: "#FFFFFF"
                            border.width: 1
                            border.color: root.fieldLine

                            Text {
                                id: envAccessLabel
                                anchors.centerIn: parent
                                text: todoDetailBridge.environmentAccessSummaryText
                                color: root.bodyInk
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.labelWeight
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: todoDetailBridge.toggleEnvironmentAccessPopover()
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: root.labelGap

                        Text {
                            text: "当前描述"
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.sectionWeight
                        }

                        Rectangle {
                            width: parent.width
                            height: 120
                            radius: 18
                            color: root.fieldBg
                            border.width: 0
                            border.color: root.fieldLine

                            Flickable {
                                id: summaryFlick
                                anchors.fill: parent
                                anchors.margins: 14
                                clip: true
                                contentWidth: width
                                contentHeight: Math.max(height, summaryEdit.contentHeight + 4)
                                boundsBehavior: Flickable.StopAtBounds

                                TextEdit {
                                    id: summaryEdit
                                    width: parent.width
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    textFormat: TextEdit.PlainText
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("current_summary", text)
                                }
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.rightMargin: 8
                                y: 10 + (summaryFlick.contentY / Math.max(1, summaryFlick.contentHeight - summaryFlick.height)) * (parent.height - height - 20)
                                width: 4
                                height: Math.max(28, (summaryFlick.height / Math.max(summaryFlick.contentHeight, 1)) * (parent.height - 20))
                                radius: 2
                                color: "#C3CAD6"
                                visible: summaryFlick.contentHeight > summaryFlick.height + 2
                            }
                        }
                    }

                    Item {
                        width: parent.width
                        height: 0
                        visible: false
                    }

                    Column {
                        width: parent.width
                        spacing: 10
                        visible: false

                        Text {
                            text: "关键证据"
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 14
                            font.weight: root.sectionWeight
                        }

                        Repeater {
                            model: []

                            delegate: Rectangle {
                                width: contentColumn.width
                                height: Math.max(72, evidenceValue.contentHeight + 40)
                                radius: 16
                                color: "#FFFFFF"
                                border.width: 0
                                border.color: root.fieldLine

                                Text {
                                    x: 14
                                    y: 12
                                    text: (modelData.label || modelData.type) + " " + modelData.type
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
                                    text: "删除"
                                    color: "#E35B66"
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

                    Item {
                        width: parent.width
                        height: todoMetaColumn.implicitHeight + 12

                        Column {
                            id: todoMetaColumn
                            anchors.fill: parent
                            anchors.margins: 6
                            spacing: 6

                            Item {
                                width: parent.width
                                height: 24

                                Row {
                                    id: syncActionRow
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 12

                                    Item {
                                        width: root.actionButtonWidth
                                        height: 24

                                        Text {
                                            anchors.centerIn: parent
                                            text: todoDetailBridge.hasExternalId ? "重新同步" : "立即同步"
                                            color: root.accent
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            font.weight: root.labelWeight
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: todoDetailBridge.requestManualSync()
                                        }
                                    }

                                    Text {
                                        visible: todoDetailBridge.hasExternalId
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "复制 ID"
                                        color: root.accent
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: todoDetailBridge.copyExternalId()
                                        }
                                    }
                                }

                                Row {
                                    anchors.left: parent.left
                                    anchors.right: syncActionRow.left
                                    anchors.rightMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 8

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "同步状态"
                                        color: root.titleInk
                                        font.family: root.uiFont
                                        font.pixelSize: 12
                                        font.weight: root.sectionWeight
                                    }

                                    Rectangle {
                                        width: compactSyncStatusText.implicitWidth + 14
                                        height: 22
                                        radius: 11
                                        color: todoDetailBridge.hasExternalId ? "#E7F5ED" : "#F4EEE4"

                                        Text {
                                            id: compactSyncStatusText
                                            anchors.centerIn: parent
                                            text: todoDetailBridge.syncStatus
                                            color: todoDetailBridge.hasExternalId ? "#17663A" : root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 10
                                            font.weight: root.labelWeight
                                        }
                                    }

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: Math.max(0, parent.width - x)
                                        elide: Text.ElideRight
                                        text: todoDetailBridge.syncStatusDetail
                                        color: root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.bodyWeight
                                    }
                                }
                            }

                            Text {
                                visible: todoDetailBridge.syncEventLabel.length > 0 || todoDetailBridge.syncUpdatedAtLabel.length > 0
                                width: parent.width
                                text: {
                                    var parts = []
                                    if (todoDetailBridge.syncEventLabel.length > 0) {
                                        parts.push("最近事件: " + todoDetailBridge.syncEventLabel)
                                    }
                                    if (todoDetailBridge.syncUpdatedAtLabel.length > 0) {
                                        parts.push("同步时间: " + todoDetailBridge.syncUpdatedAtLabel)
                                    }
                                    return parts.join("  ")
                                }
                                color: root.mutedInk
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.bodyWeight
                                wrapMode: Text.Wrap
                            }

                            Item {
                                width: parent.width
                                height: 30

                                Row {
                                    id: todoMetaActionRow
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 12

                                    Text {
                                        id: deleteText
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "删除"
                                        color: "#E35B66"
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight

                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: todoDetailBridge.deleteTodo()
                                        }
                                    }

                                    Rectangle {
                                        id: completeButton
                                        width: root.actionButtonWidth
                                        height: 30
                                        enabled: todoDetailBridge.canCompleteTodo
                                        radius: 15
                                        color: enabled ? (completeButtonMouse.pressed ? "#151C28" : root.accent) : "#E1E4E8"
                                        border.width: 0
                                        border.color: "transparent"

                                        Text {
                                            anchors.centerIn: parent
                                            text: "完成"
                                            color: completeButton.enabled ? "#FFFFFF" : root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            font.weight: root.labelWeight
                                        }

                                        MouseArea {
                                            id: completeButtonMouse
                                            anchors.fill: parent
                                            enabled: true
                                            hoverEnabled: true
                                            cursorShape: completeButton.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                            onClicked: todoDetailBridge.completeTodo()
                                        }

                                        Rectangle {
                                            id: completeDisabledTip
                                            visible: completeButtonMouse.containsMouse && !completeButton.enabled
                                            width: completeDisabledTipText.implicitWidth + 22
                                            height: 34
                                            radius: 8
                                            color: "#2A313F"
                                            border.width: 1
                                            border.color: "#3A4352"
                                            anchors.right: parent.right
                                            anchors.bottom: parent.top
                                            anchors.bottomMargin: 8
                                            z: 20

                                            Text {
                                                id: completeDisabledTipText
                                                anchors.centerIn: parent
                                                text: "请先填写问题结论"
                                                color: "#FFFFFF"
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                                font.weight: root.labelWeight
                                            }
                                        }
                                    }
                                }

                                Row {
                                    anchors.left: parent.left
                                    anchors.right: todoMetaActionRow.left
                                    anchors.rightMargin: 12
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 10

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "今天创建: " + todoDetailBridge.createdAtLabel
                                        color: root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.bodyWeight
                                    }

                                    Text {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: Math.max(0, parent.width - x)
                                        elide: Text.ElideRight
                                        text: "更新于: " + todoDetailBridge.updatedAtLabel
                                        color: root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.bodyWeight
                                    }
                                }
                            }

                            Text {
                                visible: todoDetailBridge.hasExternalId
                                width: parent.width
                                text: "external_id: " + todoDetailBridge.externalId
                                color: root.mutedInk
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.bodyWeight
                                wrapMode: Text.WrapAnywhere
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: root.sectionLine
                    }

                    Column {
                        width: parent.width
                        spacing: 12

                        Item {
                            width: parent.width
                            height: 32

                            Text {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                text: "时间线历史"
                                color: root.titleInk
                                font.family: root.uiFont
                                font.pixelSize: 15
                                font.weight: root.sectionWeight
                            }

                            Text {
                                anchors.left: parent.left
                                anchors.leftMargin: 86
                                anchors.verticalCenter: parent.verticalCenter
                                text: todoDetailBridge.timelineCount > 0 ? todoDetailBridge.timelineCount + " 条" : ""
                                color: root.mutedInk
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.bodyWeight
                            }

                            Row {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 6

                                Rectangle {
                                    width: summaryToggleText.implicitWidth + 18
                                    height: 28
                                    radius: 14
                                    color: todoDetailBridge.stageSummaryVisible ? root.accent : "#FFFFFF"
                                    border.width: 1
                                    border.color: todoDetailBridge.stageSummaryVisible ? root.accent : root.fieldLine

                                    Text {
                                        id: summaryToggleText
                                        anchors.centerIn: parent
                                        text: todoDetailBridge.stageSummaryVisible ? "收起阶段总结" : "阶段总结"
                                        color: todoDetailBridge.stageSummaryVisible ? "#FFFFFF" : root.bodyInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: todoDetailBridge.toggleStageSummary()
                                    }
                                }

                                Rectangle {
                                    width: assistToggleText.implicitWidth + 18
                                    height: 28
                                    radius: 14
                                    color: todoDetailBridge.assistTroubleshootingVisible ? root.accent : "#FFFFFF"
                                    border.width: 1
                                    border.color: todoDetailBridge.assistTroubleshootingVisible ? root.accent : root.fieldLine

                                    Text {
                                        id: assistToggleText
                                        anchors.centerIn: parent
                                        text: "辅助排查"
                                        color: todoDetailBridge.assistTroubleshootingVisible ? "#FFFFFF" : root.bodyInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: todoDetailBridge.toggleAssistTroubleshooting()
                                    }
                                }

                                Rectangle {
                                    width: timelineToggleText.implicitWidth + 18
                                    height: 28
                                    radius: 14
                                    color: "#FFFFFF"
                                    border.width: 1
                                    border.color: root.fieldLine

                                    Text {
                                        id: timelineToggleText
                                        anchors.centerIn: parent
                                        text: todoDetailBridge.timelineExpanded ? "收起" : "展开"
                                        color: root.bodyInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: todoDetailBridge.toggleTimeline()
                                    }
                                }
                            }
                        }

                        Column {
                            width: parent.width
                            spacing: 10
                            visible: todoDetailBridge.timelineExpanded

                            Rectangle {
                                id: composerCard
                                width: parent.width
                                height: Math.max(122, addTimelineEdit.contentHeight + 68)
                                radius: 18
                                color: root.fieldBg
                                border.width: 1
                                border.color: composerDropZone.containsDrag ? root.accent : (addTimelineEdit.activeFocus ? root.accent : root.fieldLine)

                                TextEdit {
                                    id: addTimelineEdit
                                    x: root.timelineEntryTypeSelected ? composerTypeTag.x + composerTypeTag.width + 10 : 16
                                    y: 16
                                    width: parent.width - x - 82
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    textFormat: TextEdit.PlainText
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    activeFocusOnPress: true
                                    onTextChanged: {
                                        if (root.syncingTimelineDraft) {
                                            return
                                        }
                                        todoDetailBridge.updateTimelineDraftText(text)
                                        root.syncTimelineCommandState()
                                    }
                                    onActiveFocusChanged: {
                                        if (activeFocus) {
                                            root.markAttachmentTarget("")
                                            root.cancelActiveTimelineEdit()
                                        }
                                    }
                                    onXChanged: root.updateTimelineCommandMenuGeometry()
                                    onYChanged: root.updateTimelineCommandMenuGeometry()
                                    onWidthChanged: root.updateTimelineCommandMenuGeometry()
                                    onHeightChanged: root.updateTimelineCommandMenuGeometry()
                                    Keys.onUpPressed: function(event) {
                                        if (!root.timelineCommandMenuVisible) {
                                            return
                                        }
                                        root.moveTimelineCommandSelection(-1)
                                        event.accepted = true
                                    }
                                    Keys.onDownPressed: function(event) {
                                        if (!root.timelineCommandMenuVisible) {
                                            return
                                        }
                                        root.moveTimelineCommandSelection(1)
                                        event.accepted = true
                                    }
                                    Keys.onReturnPressed: function(event) {
                                        if (root.confirmTimelineCommandSelection()) {
                                            event.accepted = true
                                        }
                                    }
                                    Keys.onEnterPressed: function(event) {
                                        if (root.confirmTimelineCommandSelection()) {
                                            event.accepted = true
                                        }
                                    }
                                    Keys.onPressed: function(event) {
                                        if (event.key !== Qt.Key_Backspace && event.key !== Qt.Key_Delete) {
                                            return
                                        }
                                        if (root.handleTimelineCommandRemoval()) {
                                            event.accepted = true
                                        }
                                    }
                                }

                                Text {
                                    x: addTimelineEdit.x
                                    y: 16
                                    width: addTimelineEdit.width
                                    visible: addTimelineEdit.text.length === 0 && !addTimelineEdit.activeFocus
                                    text: root.timelineEntryPlaceholder()
                                    wrapMode: Text.Wrap
                                    color: root.mutedInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.bodyWeight
                                }

                                Item {
                                    id: composerTypeTag
                                    x: 16
                                    y: 14
                                    width: composerTypeTagText.implicitWidth
                                    height: 24
                                    visible: root.timelineEntryTypeSelected

                                    Text {
                                        id: composerTypeTagText
                                        anchors.left: parent.left
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: root.timelineEntryLabel(root.timelineEntryType)
                                        color: root.accent
                                        font.family: root.uiFont
                                        font.pixelSize: 10
                                        font.weight: root.labelWeight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            root.timelineCommandMenuVisible = !root.timelineCommandMenuVisible
                                            root.syncTimelineCommandSelection()
                                            root.updateTimelineCommandMenuGeometry()
                                        }
                                    }
                                }

                                Rectangle {
                                    width: 64
                                    height: 30
                                    radius: 15
                                    anchors.right: parent.right
                                    anchors.rightMargin: 14
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 14
                                    color: (addTimelineEdit.text.trim().length > 0 || root.timelineEntryType === "log_analysis") ? root.accent : "#E5E7EB"
                                    border.width: 0
                                    border.color: "transparent"

                                    Text {
                                        anchors.centerIn: parent
                                        text: root.timelineEntryType === "log_analysis" ? "提交分析" : "添加"
                                        color: (addTimelineEdit.text.trim().length > 0 || root.timelineEntryType === "log_analysis") ? "#FFFFFF" : root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 12
                                        font.weight: root.labelWeight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: addTimelineEdit.text.trim().length > 0 || root.timelineEntryType === "log_analysis"
                                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: root.submitTimelineEntry()
                                    }
                                }

                                Row {
                                    x: 16
                                    y: parent.height - 30
                                    spacing: 14

                                    Text {
                                        text: "上传附件"
                                        color: root.accent
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: todoDetailBridge.requestDraftTimelineAttachmentSelection()
                                        }
                                    }

                                    Text {
                                        text: "粘贴截图"
                                        color: root.accent
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: todoDetailBridge.requestDraftTimelineClipboardImagePaste()
                                        }
                                    }
                                }

                                DropArea {
                                    id: composerDropZone
                                    anchors.fill: parent

                                    onEntered: function(drag) {
                                        if (drag.hasUrls) {
                                            drag.acceptProposedAction()
                                        }
                                    }

                                    onDropped: function(drop) {
                                        if (!drop.hasUrls) {
                                            return
                                        }
                                        todoDetailBridge.addDraftTimelineAttachmentsFromUrls(drop.urls)
                                        drop.acceptProposedAction()
                                    }
                                }

                                Rectangle {
                                    anchors.fill: parent
                                    radius: parent.radius
                                    color: root.accentTint
                                    opacity: composerDropZone.containsDrag ? 0.88 : 0
                                    visible: composerDropZone.containsDrag
                                    border.width: 1
                                    border.color: root.accent

                                    Text {
                                        anchors.centerIn: parent
                                        text: "释放即可上传附件"
                                        color: root.accent
                                        font.family: root.uiFont
                                        font.pixelSize: 13
                                        font.weight: root.sectionWeight
                                    }
                                }

                            }

                            Column {
                                width: parent.width
                                spacing: 8
                                visible: todoDetailBridge.draftTimelineAttachmentCount > 0

                                Rectangle {
                                    width: parent.width
                                    height: 34
                                    radius: 12
                                    color: root.fieldBg
                                    border.width: 1
                                    border.color: root.fieldLine

                                    Text {
                                        x: 12
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "待添加附件 " + todoDetailBridge.draftTimelineAttachmentCount
                                        color: root.labelInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight
                                    }
                                }

                                Repeater {
                                    model: todoDetailBridge.draftTimelineAttachments

                                    delegate: Rectangle {
                                        width: parent.width
                                        height: modelData.isImage ? 74 : 42
                                        radius: 12
                                        color: root.fieldBg
                                        border.width: 1
                                        border.color: root.fieldLine

                                        Item {
                                            anchors.fill: parent
                                            anchors.margins: 8

                                            Rectangle {
                                                id: draftPreviewThumb
                                                width: modelData.isImage ? 58 : 48
                                                height: modelData.isImage ? 58 : 26
                                                anchors.left: parent.left
                                                anchors.verticalCenter: parent.verticalCenter
                                                radius: modelData.isImage ? 10 : 8
                                                color: modelData.isPreviewable ? root.accentTint : root.fieldBg
                                                visible: modelData.isPreviewable
                                                border.width: 0
                                                border.color: "transparent"

                                                Image {
                                                    anchors.fill: parent
                                                    anchors.margins: 1
                                                    fillMode: Image.PreserveAspectCrop
                                                    visible: modelData.isImage
                                                    source: modelData.isImage ? modelData.fileUrl : ""
                                                    asynchronous: true
                                                    cache: false
                                                    smooth: true
                                                    clip: true
                                                }

                                                Text {
                                                    anchors.centerIn: parent
                                                    visible: modelData.isVideo
                                                    text: "视频"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.labelWeight
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        if (modelData.isPreviewable) {
                                                            todoDetailBridge.previewAttachment(modelData.downloadSource)
                                                        }
                                                    }
                                                }
                                            }

                                            Column {
                                                anchors.left: draftPreviewThumb.visible ? draftPreviewThumb.right : parent.left
                                                anchors.leftMargin: draftPreviewThumb.visible ? 12 : 4
                                                anchors.right: draftActionRow.left
                                                anchors.rightMargin: 8
                                                anchors.verticalCenter: parent.verticalCenter
                                                spacing: 4

                                                Text {
                                                    width: parent.width
                                                    elide: Text.ElideMiddle
                                                    text: modelData.name
                                                    color: root.bodyInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.bodyWeight
                                                }

                                                Text {
                                                    width: parent.width
                                                    elide: Text.ElideRight
                                                    text: {
                                                        var sizeLabel = root.formatFileSize(modelData.sizeBytes)
                                                        if (modelData.isPreviewable) {
                                                            return sizeLabel.length > 0 ? sizeLabel + " · 可预览" : "可预览"
                                                        }
                                                        return sizeLabel
                                                    }
                                                    color: root.mutedInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 10
                                                    font.weight: root.bodyWeight
                                                }
                                            }

                                            Row {
                                                id: draftActionRow
                                                anchors.right: parent.right
                                                anchors.verticalCenter: parent.verticalCenter
                                                spacing: 10

                                                Text {
                                                    visible: modelData.isPreviewable
                                                    text: "预览"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 10
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: todoDetailBridge.previewAttachment(modelData.downloadSource)
                                                    }
                                                }

                                                Text {
                                                    visible: modelData.isPreviewable
                                                    text: "复制"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 10
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: {
                                                            todoDetailBridge.copyAttachment(
                                                                modelData.downloadSource,
                                                                modelData.isImage,
                                                                modelData.isVideo
                                                            )
                                                        }
                                                    }
                                                }

                                                Text {
                                                    visible: !modelData.isPreviewable
                                                    text: "复制名"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 10
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: todoDetailBridge.copyAttachmentName(modelData.name)
                                                    }
                                                }

                                                Text {
                                                    visible: !modelData.isPreviewable
                                                    text: "复制路径"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 10
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: todoDetailBridge.copyAttachmentPath(modelData.downloadSource)
                                                    }
                                                }

                                                Text {
                                                    visible: !modelData.isPreviewable
                                                    text: "打开"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 10
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: todoDetailBridge.openAttachmentFolder(modelData.downloadSource)
                                                    }
                                                }

                                                Text {
                                                    visible: !modelData.isPreviewable
                                                    text: "下载"
                                                    color: root.accent
                                                    font.family: root.uiFont
                                                    font.pixelSize: 10
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: todoDetailBridge.downloadAttachment(modelData.downloadSource, modelData.name)
                                                    }
                                                }

                                                Text {
                                                    text: "移除"
                                                    color: "#E35B66"
                                                    font.family: root.uiFont
                                                    font.pixelSize: 10
                                                    font.weight: root.labelWeight

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: todoDetailBridge.removeDraftTimelineAttachment(modelData.id)
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Repeater {
                                model: todoDetailBridge.timeline

                                delegate: Item {
                                    id: timelineCardHost
                                    width: contentColumn.width
                                    height: cardLoader.item ? (cardLoader.item.implicitHeight || cardLoader.item.height) : 0

                                    Component.onCompleted: root.registerTimelineCard(modelData.id, timelineCardHost)
                                    Component.onDestruction: root.unregisterTimelineCard(modelData.id, timelineCardHost)

                                    Loader {
                                        id: cardLoader
                                        anchors.fill: parent
                                        source: TimelineCardMapper.sourceForType(modelData.type)

                                        onLoaded: {
                                            if (!item) {
                                                return
                                            }
                                            item.rootContext = root
                                            item.todoDetailBridge = todoDetailBridge
                                            item.eventData = modelData
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 78
                                radius: 18
                                color: root.timelineBg
                                border.width: 0
                                border.color: root.fieldLine
                                visible: todoDetailBridge.timelineCount === 0

                                Text {
                                    anchors.centerIn: parent
                                    text: "暂无时间线记录"
                                    color: root.mutedInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.bodyWeight
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    visible: flick.contentHeight > flick.height + 2
                    anchors.right: parent.right
                    anchors.rightMargin: 4
                    y: 8 + (flick.contentY / Math.max(1, flick.contentHeight - flick.height)) * (parent.height - height - 16)
                    width: 4
                    height: Math.max(48, (flick.height / Math.max(flick.contentHeight, 1)) * (parent.height - 16))
                    radius: 2
                    color: "#BEC6D2"
                }

                Item {
                    id: environmentPopoverLayer
                    anchors.fill: parent
                    z: 49
                    visible: todoDetailBridge.environmentAccessPopoverOpen

                    MouseArea {
                        anchors.fill: parent
                        onClicked: todoDetailBridge.closeEnvironmentAccessPopover()
                    }

                    EnvironmentAccessPopover {
                        x: mainShell.width - width - root.outerPadding
                        y: {
                            var point = envAccessTrigger.mapToItem(environmentPopoverLayer, 0, envAccessTrigger.height + 8)
                            return point.y
                        }
                        theme: root.themeTokens
                        groupsModel: todoDetailBridge.environmentAccessGroups
                        z: 1
                    }
                }

                Item {
                    id: timelineCommandOverlayLayer
                    anchors.fill: parent
                    z: 50
                    visible: root.timelineCommandMenuVisible

                    Rectangle {
                        x: root.timelineCommandMenuX
                        y: root.timelineCommandMenuY
                        width: root.timelineCommandMenuWidth
                        height: 108
                        radius: 14
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: root.fieldLine

                        Column {
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Repeater {
                                model: root.timelineCommandOptions

                                delegate: Rectangle {
                                    width: parent.width
                                    height: 24
                                    radius: 10
                                    color: index === root.timelineCommandSelectedIndex ? root.accentTint : "transparent"

                                    Text {
                                        anchors.left: parent.left
                                        anchors.leftMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: "/" + modelData.label
                                        color: root.titleInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.labelWeight
                                    }

                                    Text {
                                        anchors.right: parent.right
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.detail
                                        color: root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 10
                                        font.weight: root.bodyWeight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onEntered: root.timelineCommandSelectedIndex = index
                                        onClicked: root.selectTimelineEntryType(modelData.value)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        syncFields()
        syncTimelineDraft()
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: ticketSection
    required property var theme

    visible: controlPanelBridge.currentSection === "tickets"
    spacing: 0
    readonly property int detailGridColumns: ticketSection.width < 720 ? 1 : ticketSection.width < 1080 ? 2 : ticketSection.width < 1440 ? 3 : 4
    readonly property bool compactDetailLayout: ticketSection.width < 920
    property bool deleteTicketConfirmVisible: false
    property string copyToastMessage: ""
    
    // Per-field editing state map: fieldName -> { editing, saving, draft, original }
    property var fieldStates: ({})
    property string activeActionField: ""
    property string currentTicketId: ""

    property var statusOptions: [
        { value: "open", text: "进行中" },
        { value: "done", text: "已完成" },
        { value: "done_missing_ach", text: "已完成未填ACH" },
        { value: "all", text: "全部状态" }
    ]

    function ticketFieldText(value) {
        if (value === null || value === undefined) {
            return ""
        }
        return String(value)
    }

    function formatProduct(product) {
        var value = ticketFieldText(product)
        if (!value) {
            return ""
        }
        if (value === "WPS\u534f\u4f5c") {
            return "WPS\u534f\u4f5c\uff08\u6cdb\uff09/\u534f\u4f5c-\u79c1\u7f51"
        }
        if (value === "\u6587\u6863\u4e2d\u53f0") {
            return "\u6587\u6863\u4e2d\u53f0/V7"
        }
        if (value === "\u6587\u6863\u4e2d\u5fc3") {
            return "\u6587\u6863\u4e2d\u5fc3/V7"
        }
        return value
    }

    function formatProjectName(projectName) {
        if (projectName === null || projectName === undefined) {
            return ""
        }
        if (Array.isArray(projectName)) {
            return projectName.join(",")
        }
        return String(projectName)
    }

    function formatTicketForTool(ticket) {
        return "\u6807\u9898: " + ticketFieldText(ticket.title) + "\n"
            + "\u4e8c\u7ebf: \u5426\n"
            + "\u7ed3\u8bba: " + ticketFieldText(ticket.conclusionContent) + "\n"
            + "\u5ba2\u6237\u540d\u79f0: " + ticketFieldText(ticket.customerName) + "\n"
            + "\u9879\u76ee\u540d\u79f0: " + formatProjectName(ticket.projectName) + "\n"
            + "\u529f\u80fd\u70b9: " + ticketFieldText(ticket.featurePoint) + "\n"
            + "\u7248\u672c: " + ticketFieldText(ticket.ticketVersion) + "\n"
            + "\u6839\u56e0\u5206\u7c7b: " + ticketFieldText(ticket.rootCause) + "\n"
            + "\u6839\u56e0\u63cf\u8ff0: " + ticketFieldText(ticket.rootCauseDesc) + "\n"
            + "\u4ea7\u54c1: " + formatProduct(ticket.productLine) + "\n"
            + "\u63cf\u8ff0: " + ticketFieldText(ticket.summary)
    }

    function showCopyToast(message) {
        copyToastMessage = message
        copyToast.open()
        copyToastTimer.restart()
    }

    function copyTicketForTool() {
        if (!controlPanelBridge.selectedTicket.id) {
            showCopyToast("\u590d\u5236\u5931\u8d25")
            return
        }
        try {
            ticketClipboardBuffer.text = formatTicketForTool(controlPanelBridge.selectedTicket)
            ticketClipboardBuffer.selectAll()
            ticketClipboardBuffer.copy()
            ticketClipboardBuffer.deselect()
            showCopyToast("\u5df2\u590d\u5236")
        } catch (error) {
            showCopyToast("\u590d\u5236\u5931\u8d25")
        }
    }

    function currentStatusValue() {
        var index = ticketStatusCombo.currentIndex
        if (index < 0 || index >= statusOptions.length) {
            return "open"
        }
        return statusOptions[index].value
    }

    function currentTicketFieldValue(fieldName) {
        if (fieldName === "achNo") {
            return controlPanelBridge.selectedTicket.achNo || ""
        }
        if (fieldName === "ticketVersion") {
            return controlPanelBridge.selectedTicket.ticketVersion || ""
        }
        if (fieldName === "featurePoint") {
            return controlPanelBridge.selectedTicket.featurePoint || ""
        }
        if (fieldName === "rootCause") {
            return controlPanelBridge.selectedTicket.rootCause || ""
        }
        if (fieldName === "rootCauseDesc") {
            return controlPanelBridge.selectedTicket.rootCauseDesc || ""
        }
        return ""
    }

    function getFieldState(fieldName) {
        // Always return a fresh state object, never cache
        if (!fieldStates[fieldName]) {
            return {
                editing: false,
                saving: false,
                draft: "",
                original: ""
            }
        }
        return fieldStates[fieldName]
    }

    function setFieldState(fieldName, updates) {
        // Create a completely new state object to ensure reactivity
        var currentState = fieldStates[fieldName] || {
            editing: false,
            saving: false,
            draft: "",
            original: ""
        }
        
        // Apply updates
        for (var key in updates) {
            currentState[key] = updates[key]
        }
        
        // Force a new object reference to trigger QML reactivity
        var newFieldStates = {}
        for (var existingKey in fieldStates) {
            newFieldStates[existingKey] = fieldStates[existingKey]
        }
        newFieldStates[fieldName] = currentState
        fieldStates = newFieldStates
    }

    function isFieldEditing(fieldName) {
        return getFieldState(fieldName).editing
    }

    function isFieldSaving(fieldName) {
        return getFieldState(fieldName).saving
    }

    function getFieldDraft(fieldName) {
        var state = fieldStates[fieldName]
        if (!state || !state.editing) {
            // If not editing, return current ticket value
            return currentTicketFieldValue(fieldName)
        }
        return state.draft
    }

    function resetAllFieldStates() {
        // Create a completely new empty object to ensure reactivity
        fieldStates = {}
        activeActionField = ""
    }

    function parseRootCausePath(value) {
        var parts = String(value || "").split("/")
        var level1 = parts.length > 0 ? parts[0] : ""
        var level2 = parts.length > 1 ? parts[1] : ""
        var level3 = parts.length > 2 ? parts.slice(2).join("/") : ""
        return {
            level1: level1,
            level2: level2,
            level3: level3
        }
    }

    function rootCauseLevel1Options() {
        var options = controlPanelBridge.rootCauseOptions || []
        var seen = {}
        var result = []
        for (var i = 0; i < options.length; i += 1) {
            var path = parseRootCausePath(options[i])
            var key = path.level1
            if (!key || seen[key]) {
                continue
            }
            seen[key] = true
            result.push({ text: key, value: key })
        }
        return result
    }

    function rootCauseLevel2Options(level1) {
        var selectedLevel1 = String(level1 || "")
        var options = controlPanelBridge.rootCauseOptions || []
        var seen = {}
        var result = []
        for (var i = 0; i < options.length; i += 1) {
            var path = parseRootCausePath(options[i])
            if (path.level1 !== selectedLevel1 || !path.level2 || seen[path.level2]) {
                continue
            }
            seen[path.level2] = true
            result.push({ text: path.level2, value: path.level2 })
        }
        return result
    }

    function rootCauseLevel3Options(level1, level2) {
        var selectedLevel1 = String(level1 || "")
        var selectedLevel2 = String(level2 || "")
        var options = controlPanelBridge.rootCauseOptions || []
        var seen = {}
        var result = []
        for (var i = 0; i < options.length; i += 1) {
            var path = parseRootCausePath(options[i])
            if (path.level1 !== selectedLevel1 || path.level2 !== selectedLevel2 || !path.level3 || seen[path.level3]) {
                continue
            }
            seen[path.level3] = true
            result.push({ text: path.level3, value: path.level3 })
        }
        return result
    }

    function beginTicketFieldEdit(fieldName) {
        // Prevent editing if another field is saving or an action is running
        if (activeActionField.length > 0) {
            return
        }
        for (var key in fieldStates) {
            if (fieldStates[key].saving) {
                return
            }
        }
        
        // CRITICAL: Always get fresh current value from the actual ticket object
        // This ensures we never show stale data from previous tickets
        var currentValue = currentTicketFieldValue(fieldName)
        
        // Force-clear any existing state for this field first
        if (fieldStates[fieldName]) {
            delete fieldStates[fieldName]
        }
        
        // Initialize field state with fresh current value
        setFieldState(fieldName, {
            editing: true,
            saving: false,
            draft: currentValue,
            original: currentValue
        })
    }

    function cancelTicketFieldEdit(fieldName) {
        setFieldState(fieldName, {
            editing: false,
            saving: false,
            draft: getFieldState(fieldName).original,
            original: getFieldState(fieldName).original
        })
    }

    function commitTicketFieldEdit(fieldName, saveAction) {
        var state = getFieldState(fieldName)
        if (!state.editing || state.saving || activeActionField.length > 0) {
            return
        }
        
        var nextValue = (state.draft || "").trim()
        if (nextValue === state.original) {
            // No change, just exit editing mode
            setFieldState(fieldName, {
                editing: false,
                saving: false
            })
            return
        }
        
        // Enter saving state
        setFieldState(fieldName, {
            editing: false,
            saving: true
        })
        
        // Trigger save
        Qt.callLater(function() {
            if (!getFieldState(fieldName).saving) {
                return
            }
            if (saveAction === "ticket_version") {
                controlPanelBridge.saveSelectedTicketVersion(nextValue)
            } else {
                controlPanelBridge.saveSelectedTicketField(saveAction, nextValue)
            }
        })
    }

    function onFieldSaveComplete(fieldName) {
        // Called when backend confirms save is complete
        var currentValue = currentTicketFieldValue(fieldName)
        setFieldState(fieldName, {
            editing: false,
            saving: false,
            draft: currentValue,
            original: currentValue
        })
    }

    function refreshFeaturePointField() {
        if (activeActionField.length > 0 || isFieldEditing("featurePoint")) {
            return
        }
        for (var key in fieldStates) {
            if (fieldStates[key].saving) {
                return
            }
        }
        
        activeActionField = "featurePoint"
        Qt.callLater(function() {
            controlPanelBridge.refreshSelectedTicketFeaturePoint()
            if (activeActionField === "featurePoint") {
                activeActionField = ""
            }
        })
    }

    function requestDeleteSelectedTicket() {
        if (!controlPanelBridge.selectedTicket.id || activeActionField.length > 0) {
            return
        }
        for (var key in fieldStates) {
            if (fieldStates[key].saving) {
                return
            }
        }
        deleteTicketConfirmVisible = true
    }

    function cancelDeleteSelectedTicket() {
        deleteTicketConfirmVisible = false
    }

    function confirmDeleteSelectedTicket() {
        if (!controlPanelBridge.selectedTicket.id) {
            deleteTicketConfirmVisible = false
            return
        }
        deleteTicketConfirmVisible = false
        controlPanelBridge.deleteSelectedTicket()
    }

    ControlPanelSectionCard {
        id: ticketSectionCard
        theme: ticketSection.theme
        Layout.fillWidth: true
        implicitHeight: ticketContent.implicitHeight + 32
        color: "#F6F0E6"

        TextEdit {
            id: ticketClipboardBuffer
            width: 0
            height: 0
            opacity: 0
            visible: true
            textFormat: TextEdit.PlainText
            wrapMode: TextEdit.NoWrap
            selectByMouse: false
            persistentSelection: true
            readOnly: true
        }

        Popup {
            id: copyToast
            parent: ticketSectionCard
            x: Math.round(ticketSectionCard.width - width - 24)
            y: 24
            padding: 0
            margins: 0
            modal: false
            dim: false
            focus: false
            closePolicy: Popup.NoAutoClose
            background: Rectangle {
                radius: 12
                color: "#2F241A"
                opacity: 0.94
            }
            contentItem: Text {
                leftPadding: 14
                rightPadding: 14
                topPadding: 10
                bottomPadding: 10
                text: ticketSection.copyToastMessage
                color: "#FFF9F1"
                font.family: ticketSection.theme.uiFont
                font.pixelSize: 12
            }
        }

        Timer {
            id: copyToastTimer
            interval: 1400
            repeat: false
            onTriggered: copyToast.close()
        }

        ColumnLayout {
            id: ticketContent
            anchors.fill: parent
            anchors.margins: 16
            spacing: 14

            RowLayout {
                visible: controlPanelBridge.selectedTicket.id.length === 0
                Layout.fillWidth: true
                spacing: 10

                ControlPanelSettingsInput {
                    id: ticketSearchInput
                    theme: ticketSection.theme
                    Layout.fillWidth: true
                    text: controlPanelBridge.ticketQuery
                    placeholderText: "搜索标题 / 摘要 / 群名 / 项目名 / 工单类型"
                    onTextEdited: controlPanelBridge.listTickets(text, ticketSection.currentStatusValue())
                }

                ControlPanelSettingsCombo {
                    id: ticketStatusCombo
                    theme: ticketSection.theme
                    Layout.preferredWidth: 160
                    model: ticketSection.statusOptions
                    currentIndex: ticketSection.theme.optionIndex(ticketSection.statusOptions, controlPanelBridge.ticketStatusFilter)
                    onActivated: if (currentIndex >= 0) controlPanelBridge.listTickets(ticketSearchInput.text, ticketSection.statusOptions[currentIndex].value)
                }

            }

            Text {
                visible: controlPanelBridge.selectedTicket.id.length === 0 && controlPanelBridge.tickets.length === 0
                Layout.fillWidth: true
                text: "当前筛选条件下没有工单。"
                color: theme.labelInk
                font.family: theme.uiFont
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }

            Rectangle {
                visible: controlPanelBridge.selectedTicket.id.length === 0 && controlPanelBridge.tickets.length > 0
                Layout.fillWidth: true
                implicitHeight: 560
                radius: 18
                color: "#FFF9F1"
                border.width: 1
                border.color: theme.panelLine

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10

                    Text {
                        text: "工单列表"
                        color: theme.titleInk
                        font.family: theme.uiFont
                        font.pixelSize: 14
                        font.weight: 700
                    }

                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        spacing: 8
                        model: controlPanelBridge.tickets

                        delegate: Rectangle {
                            width: ListView.view.width
                            height: ticketInfoColumn.implicitHeight + 20
                            radius: 14
                            color: "#FFFCF7"
                            border.width: 1
                            border.color: theme.panelLine

                            Column {
                                id: ticketInfoColumn
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 6

                                Row {
                                    width: parent.width
                                    spacing: 8

                                    Text {
                                        width: parent.width - statusBadge.width - projectBadge.width - (parent.spacing * 2)
                                        text: modelData.title
                                        color: theme.titleInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 13
                                        font.weight: 700
                                        elide: Text.ElideRight
                                    }

                                    StatusPill {
                                        id: statusBadge
                                        theme: ticketSection.theme
                                        label: modelData.statusLabel
                                        tone: modelData.statusTone
                                    }

                                    StatusPill {
                                        id: projectBadge
                                        theme: ticketSection.theme
                                        label: modelData.projectStatusLabel
                                        tone: modelData.projectStatusTone
                                    }
                                }

                                Text {
                                    width: parent.width
                                    text: (modelData.summary || "").length > 0 ? modelData.summary : "暂无摘要"
                                    color: theme.bodyInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: "群名: " + (modelData.groupName || "未填写") + " / 环境: " + (modelData.environment || "未填写")
                                    color: theme.bodyInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: "工单类型: " + (modelData.ticketType || "未填写")
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.projectStatusDetail
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                Text {
                                    width: parent.width
                                    text: "最近更新: " + (modelData.updatedAtLabel || "未知") + " / 跟进: " + modelData.timelineCount + " 条"
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: controlPanelBridge.openTicketDetail(modelData.id)
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                visible: controlPanelBridge.selectedTicket.id.length > 0
                Layout.fillWidth: true
                spacing: 18

                // Monitor ticket ID changes to reset field states
                onVisibleChanged: {
                    if (visible) {
                        var newTicketId = controlPanelBridge.selectedTicket.id || ""
                        if (newTicketId !== ticketSection.currentTicketId) {
                            ticketSection.currentTicketId = newTicketId
                            ticketSection.resetAllFieldStates()
                        }
                    }
                }

                Connections {
                    target: controlPanelBridge
                    function onDataChanged() {
                        // Check if ticket ID changed
                        var newTicketId = controlPanelBridge.selectedTicket.id || ""
                        if (newTicketId !== ticketSection.currentTicketId) {
                            ticketSection.currentTicketId = newTicketId
                            ticketSection.resetAllFieldStates()
                            return
                        }
                        
                        // When ticket data changes, sync all field states
                        for (var fieldName in ticketSection.fieldStates) {
                            var state = ticketSection.getFieldState(fieldName)
                            if (state.saving) {
                                // Check if save completed
                                var currentValue = ticketSection.currentTicketFieldValue(fieldName)
                                if (currentValue !== state.original) {
                                    // Save completed, update state
                                    ticketSection.onFieldSaveComplete(fieldName)
                                }
                            }
                        }
                    }
                }

                Component.onCompleted: {
                    // Ensure clean state on mount
                    ticketSection.currentTicketId = controlPanelBridge.selectedTicket.id || ""
                    ticketSection.resetAllFieldStates()
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    ControlPanelPlainButton {
                        theme: ticketSection.theme
                        label: "返回列表"
                        onClicked: {
                            ticketSection.cancelDeleteSelectedTicket()
                            controlPanelBridge.backToTicketList()
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    ControlPanelPlainButton {
                        theme: ticketSection.theme
                        label: "\u590d\u5236\u5de5\u5355"
                        onClicked: ticketSection.copyTicketForTool()
                    }

                    ControlPanelPlainButton {
                        theme: ticketSection.theme
                        label: "\u5220\u9664\u5de5\u5355"
                        fillColor: "#FFF3F1"
                        inkColor: "#8B3A2C"
                        onClicked: ticketSection.requestDeleteSelectedTicket()
                    }
                }

                Rectangle {
                    visible: ticketSection.deleteTicketConfirmVisible
                    Layout.fillWidth: true
                    radius: 18
                    color: "#FFF7F4"
                    border.width: 1
                    border.color: "#E7C8BF"
                    implicitHeight: deleteConfirmColumn.implicitHeight + 24

                    ColumnLayout {
                        id: deleteConfirmColumn
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        Text {
                            Layout.fillWidth: true
                            text: "\u786e\u8ba4\u5220\u9664\u5f53\u524d\u5de5\u5355\u5417\uff1f"
                            color: theme.titleInk
                            font.family: theme.uiFont
                            font.pixelSize: 13
                            font.weight: 700
                            wrapMode: Text.Wrap
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "\u5220\u9664\u540e\u65e0\u6cd5\u6062\u590d\uff0c\u5de5\u5355\u8be6\u60c5\u3001\u8ddf\u8fdb\u8bb0\u5f55\u548c\u9644\u4ef6\u5173\u8054\u90fd\u4f1a\u4e00\u8d77\u79fb\u9664\u3002"
                            color: theme.labelInk
                            font.family: theme.uiFont
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Item {
                                Layout.fillWidth: true
                            }

                            ControlPanelPlainButton {
                                theme: ticketSection.theme
                                label: "\u53d6\u6d88"
                                onClicked: ticketSection.cancelDeleteSelectedTicket()
                            }

                            ControlPanelPlainButton {
                                theme: ticketSection.theme
                                label: "\u786e\u8ba4\u5220\u9664"
                                fillColor: "#C84E3A"
                                inkColor: "#FFFFFF"
                                strokeWidth: 0
                                onClicked: ticketSection.confirmDeleteSelectedTicket()
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: 22
                    color: "#FFFCF8"
                    border.width: 1
                    border.color: "#ECE4D8"
                    implicitHeight: ticketDetailColumn.implicitHeight + 40

                    ColumnLayout {
                        id: ticketDetailColumn
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 28

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            SelectableText {
                                Layout.fillWidth: true
                                text: controlPanelBridge.selectedTicket.title || "未分类任务"
                                color: theme.titleInk
                                font.family: theme.uiFont
                                font.pixelSize: 25
                                font.weight: 700
                                wrapMode: TextEdit.Wrap
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: 8

                                StatusPill {
                                    theme: ticketSection.theme
                                    label: controlPanelBridge.selectedTicket.statusLabel
                                    tone: controlPanelBridge.selectedTicket.statusTone
                                }

                                StatusPill {
                                    theme: ticketSection.theme
                                    label: controlPanelBridge.selectedTicket.projectStatusLabel
                                    tone: controlPanelBridge.selectedTicket.projectStatusTone
                                }

                                StatusPill {
                                    theme: ticketSection.theme
                                    label: controlPanelBridge.selectedTicket.ticketType || "未填写工单类型"
                                    tone: "default"
                                }
                            }

                            SelectableText {
                                Layout.fillWidth: true
                                text: (controlPanelBridge.selectedTicket.currentSummary || "").length > 0 ? controlPanelBridge.selectedTicket.currentSummary : "暂无摘要"
                                color: theme.labelInk
                                font.family: theme.uiFont
                                font.pixelSize: 13
                                wrapMode: TextEdit.Wrap
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 1
                            color: "#E9E0D3"
                        }

                        GridLayout {
                            Layout.fillWidth: true
                            columns: ticketSection.detailGridColumns
                            columnSpacing: 12
                            rowSpacing: 12

                            ColumnLayout {
                                Layout.row: 1
                                Layout.columnSpan: ticketSection.detailGridColumns
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                spacing: 18

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text {
                                        text: "历史跟进"
                                        color: theme.titleInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 14
                                        font.weight: 700
                                    }

                                    Text {
                                        text: controlPanelBridge.selectedTicket.timelineCount + " 条记录，按最近更新排序"
                                        color: theme.labelInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 11
                                    }
                                }

                                Repeater {
                                    model: controlPanelBridge.selectedTicket.timeline

                                    delegate: Item {
                                        Layout.fillWidth: true
                                        implicitHeight: timelineEntryRow.implicitHeight

                                        RowLayout {
                                            id: timelineEntryRow
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            spacing: 16

                                            Item {
                                                Layout.preferredWidth: 16
                                                Layout.alignment: Qt.AlignTop
                                                implicitWidth: 16
                                                implicitHeight: timelineEntryContent.implicitHeight

                                                Rectangle {
                                                    x: 4
                                                    y: 8
                                                    width: 8
                                                    height: 8
                                                    radius: 4
                                                    color: theme.accent
                                                }

                                                Rectangle {
                                                    visible: index < controlPanelBridge.selectedTicket.timeline.length - 1
                                                    x: 7
                                                    y: 24
                                                    width: 2
                                                    height: Math.max(0, parent.height - 24)
                                                    radius: 1
                                                    color: "#E4DCCF"
                                                }
                                            }

                                            ColumnLayout {
                                                id: timelineEntryContent
                                                Layout.fillWidth: true
                                                spacing: 8

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 10

                                                    Text {
                                                        text: modelData.timestampLabel || modelData.timestamp
                                                        color: theme.titleInk
                                                        font.family: theme.uiFont
                                                        font.pixelSize: 12
                                                        font.weight: 700
                                                    }

                                                    Text {
                                                        text: modelData.scenario
                                                        color: theme.labelInk
                                                        font.family: theme.uiFont
                                                        font.pixelSize: 11
                                                    }

                                                    Item {
                                                        Layout.fillWidth: true
                                                    }
                                                }

                                                SelectableText {
                                                    Layout.fillWidth: true
                                                    text: modelData.content
                                                    color: theme.bodyInk
                                                    font.family: theme.uiFont
                                                    font.pixelSize: 12
                                                    wrapMode: TextEdit.Wrap
                                                }

                                                Flow {
                                                    visible: modelData.attachments.length > 0
                                                    Layout.fillWidth: true
                                                    spacing: 8

                                                    Repeater {
                                                        model: modelData.attachments

                                                        delegate: Rectangle {
                                                            radius: 14
                                                            color: "#F6F2EA"
                                                            border.width: 1
                                                            border.color: "#E5DCD0"
                                                            width: attachmentText.implicitWidth + 24
                                                            height: 30

                                                            Text {
                                                                id: attachmentText
                                                                anchors.centerIn: parent
                                                                text: modelData.name + " (" + modelData.sizeLabel + ")"
                                                                color: theme.bodyInk
                                                                font.family: theme.uiFont
                                                                font.pixelSize: 11
                                                            }
                                                        }
                                                    }
                                                }

                                                Rectangle {
                                                    visible: index < controlPanelBridge.selectedTicket.timeline.length - 1
                                                    Layout.fillWidth: true
                                                    implicitHeight: 1
                                                    color: "#EEE5D8"
                                                    Layout.topMargin: 8
                                                }
                                            }
                                        }
                                    }
                                }

                                Text {
                                    visible: controlPanelBridge.selectedTicket.timeline.length === 0
                                    Layout.fillWidth: true
                                    text: "暂无跟进记录"
                                    color: theme.labelInk
                                    font.family: theme.uiFont
                                    font.pixelSize: 12
                                }
                            }

                            Item {
                                Layout.row: 0
                                Layout.columnSpan: ticketSection.detailGridColumns
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                implicitHeight: detailSidebar.implicitHeight + 18

                                ColumnLayout {
                                    id: detailSidebar
                                    anchors.fill: parent
                                    anchors.topMargin: 4
                                    anchors.bottomMargin: 4
                                    spacing: 10

                                    Text {
                                        Layout.fillWidth: true
                                        text: "关键信息"
                                        color: theme.titleInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 14
                                        font.weight: 700
                                    }

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: ticketSection.detailGridColumns
                                        columnSpacing: 10
                                        rowSpacing: 8

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "ach单号"
                                            value: ticketSection.isFieldEditing("achNo") ? ticketSection.getFieldDraft("achNo") : controlPanelBridge.selectedTicket.achNo
                                            placeholderText: "未填写"
                                            editable: true
                                            editing: ticketSection.isFieldEditing("achNo")
                                            saving: ticketSection.isFieldSaving("achNo")
                                            compact: ticketSection.detailGridColumns === 1
                                            draftValue: ticketSection.getFieldDraft("achNo")
                                            onClicked: ticketSection.beginTicketFieldEdit("achNo")
                                            onDraftChanged: function(value) {
                                                ticketSection.setFieldState("achNo", { draft: value })
                                            }
                                            onAccepted: function(value) {
                                                ticketSection.setFieldState("achNo", { draft: value })
                                                ticketSection.commitTicketFieldEdit("achNo", "ach_no")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit("achNo")
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "ach填写时间"
                                            value: controlPanelBridge.selectedTicket.achFilledAtLabel
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            Layout.columnSpan: ticketSection.detailGridColumns
                                            label: "项目关联"
                                            value: controlPanelBridge.selectedTicket.projectStatusDetail
                                            placeholderText: "暂无项目关联信息"
                                            multiline: true
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "群名"
                                            value: controlPanelBridge.selectedTicket.groupName
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "环境"
                                            value: controlPanelBridge.selectedTicket.environment
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "工单类型"
                                            value: controlPanelBridge.selectedTicket.ticketType
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "产品线"
                                            value: controlPanelBridge.selectedTicket.productLine
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "\u7248\u672c\u53f7"
                                            value: ticketSection.isFieldEditing("ticketVersion") ? ticketSection.getFieldDraft("ticketVersion") : controlPanelBridge.selectedTicket.ticketVersion
                                            placeholderText: "\u672a\u586b\u5199"
                                            editable: true
                                            editing: ticketSection.isFieldEditing("ticketVersion")
                                            saving: ticketSection.isFieldSaving("ticketVersion")
                                            compact: ticketSection.detailGridColumns === 1
                                            draftValue: ticketSection.getFieldDraft("ticketVersion")
                                            onClicked: ticketSection.beginTicketFieldEdit("ticketVersion")
                                            onDraftChanged: function(value) {
                                                ticketSection.setFieldState("ticketVersion", { draft: value })
                                            }
                                            onAccepted: function(value) {
                                                ticketSection.setFieldState("ticketVersion", { draft: value })
                                                ticketSection.commitTicketFieldEdit("ticketVersion", "ticket_version")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit("ticketVersion")
                                        }
                                        DetailField {
                                            // Force component recreation when ticket changes by using ticket ID as part of object identity
                                            id: featurePointField
                                            property string ticketId: controlPanelBridge.selectedTicket.id
                                            
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "\u529f\u80fd\u70b9"
                                            value: ticketSection.isFieldEditing("featurePoint") ? ticketSection.getFieldDraft("featurePoint") : controlPanelBridge.selectedTicket.featurePoint
                                            placeholderText: "\u672a\u751f\u6210"
                                            editable: true
                                            editing: ticketSection.isFieldEditing("featurePoint")
                                            saving: ticketSection.isFieldSaving("featurePoint")
                                            compact: ticketSection.detailGridColumns === 1
                                            actionVisible: true
                                            actionBusy: ticketSection.activeActionField === "featurePoint"
                                            actionIconSource: Qt.resolvedUrl("../../../assets/feature-point-refresh.svg")
                                            draftValue: ticketSection.getFieldDraft("featurePoint")
                                            
                                            onClicked: ticketSection.beginTicketFieldEdit("featurePoint")
                                            onActionTriggered: ticketSection.refreshFeaturePointField()
                                            onDraftChanged: function(value) {
                                                ticketSection.setFieldState("featurePoint", { draft: value })
                                            }
                                            onAccepted: function(value) {
                                                ticketSection.setFieldState("featurePoint", { draft: value })
                                                ticketSection.commitTicketFieldEdit("featurePoint", "feature_point")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit("featurePoint")
                                        }

                                        RootCauseCascadeField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "\u95ee\u9898\u6839\u56e0"
                                            value: ticketSection.isFieldEditing("rootCause") ? ticketSection.getFieldDraft("rootCause") : controlPanelBridge.selectedTicket.rootCause
                                            placeholderText: "\u672a\u751f\u6210"
                                            editing: ticketSection.isFieldEditing("rootCause")
                                            saving: ticketSection.isFieldSaving("rootCause")
                                            compact: ticketSection.detailGridColumns === 1
                                            parsePathFn: ticketSection.parseRootCausePath
                                            level1OptionsFn: ticketSection.rootCauseLevel1Options
                                            level2OptionsFn: ticketSection.rootCauseLevel2Options
                                            level3OptionsFn: ticketSection.rootCauseLevel3Options
                                            onClicked: ticketSection.beginTicketFieldEdit("rootCause")
                                            onAccepted: function(value) {
                                                ticketSection.setFieldState("rootCause", { draft: value })
                                                ticketSection.commitTicketFieldEdit("rootCause", "root_cause")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit("rootCause")
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "\u6839\u56e0\u63cf\u8ff0"
                                            value: ticketSection.isFieldEditing("rootCauseDesc") ? ticketSection.getFieldDraft("rootCauseDesc") : controlPanelBridge.selectedTicket.rootCauseDesc
                                            placeholderText: "\u672a\u751f\u6210"
                                            compact: ticketSection.detailGridColumns === 1
                                            multiline: true
                                            editable: true
                                            editing: ticketSection.isFieldEditing("rootCauseDesc")
                                            saving: ticketSection.isFieldSaving("rootCauseDesc")
                                            draftValue: ticketSection.getFieldDraft("rootCauseDesc")
                                            onClicked: ticketSection.beginTicketFieldEdit("rootCauseDesc")
                                            onDraftChanged: function(value) {
                                                ticketSection.setFieldState("rootCauseDesc", { draft: value })
                                            }
                                            onAccepted: function(value) {
                                                ticketSection.setFieldState("rootCauseDesc", { draft: value })
                                                ticketSection.commitTicketFieldEdit("rootCauseDesc", "root_cause_desc")
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit("rootCauseDesc")
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "项目经理"
                                            value: controlPanelBridge.selectedTicket.projectManager
                                            placeholderText: "未填写"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "创建时间"
                                            value: controlPanelBridge.selectedTicket.createdAtLabel
                                            placeholderText: "未知"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "最近更新"
                                            value: controlPanelBridge.selectedTicket.updatedAtLabel
                                            placeholderText: "未知"
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            Layout.columnSpan: ticketSection.detailGridColumns
                                            visible: (controlPanelBridge.selectedTicket.projectSnapshotVersion || "").length > 0
                                                && (controlPanelBridge.selectedTicket.projectSnapshotVersion || "") !== (controlPanelBridge.selectedTicket.ticketVersion || "")
                                            label: "关联项目快照版本"
                                            value: controlPanelBridge.selectedTicket.projectSnapshotVersion
                                            placeholderText: "未填写"
                                            multiline: true
                                        }
                                    }
                                }
                            }
                    }
                }
            }
        }
    }
}
}

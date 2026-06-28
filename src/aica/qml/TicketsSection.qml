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
    property bool unlinkProjectConfirmVisible: false
    
    // Per-field editing state map: fieldName -> { editing, saving, draft, original }
    property var fieldStates: ({})
    property string activeActionField: ""
    property string currentTicketId: ""
    property string selectedProductLine: "all"
    property string selectedTicketType: "all"
    property int ticketPageSize: 10
    property int ticketCurrentPage: 1
    property var filteredTickets: []
    property var pagedTickets: []
    readonly property int ticketTotalCount: filteredTickets.length
    readonly property int ticketTotalPages: Math.max(1, Math.ceil(ticketTotalCount / ticketPageSize))

    property var statusOptions: [
        { value: "open", text: "\u8fdb\u884c\u4e2d" },
        { value: "done", text: "\u5df2\u5b8c\u6210" },
        { value: "today_done", text: "\u4eca\u65e5\u5b8c\u6210" },
        { value: "done_missing_ach", text: "\u5df2\u5b8c\u6210\u672a\u586bACH" },
        { value: "all", text: "\u5168\u90e8\u72b6\u6001" }
    ]
    property var productLineOptions: [
        { value: "all", text: "\u4ea7\u54c1\u7ebf" },
        { value: "\u6587\u6863\u4e2d\u53f0", text: "\u6587\u6863\u4e2d\u53f0" },
        { value: "\u6587\u6863\u4e2d\u5fc3", text: "\u6587\u6863\u4e2d\u5fc3" }
    ]
    property var ticketTypeOptions: [
        { value: "all", text: "\u7c7b\u578b" },
        { value: "\u6392\u67e5\u7c7b", text: "\u6392\u67e5\u7c7b" },
        { value: "\u54a8\u8be2\u7c7b", text: "\u54a8\u8be2\u7c7b" },
        { value: "\u64cd\u4f5c\u7c7b", text: "\u64cd\u4f5c\u7c7b" }
    ]
    property var pageSizeOptions: [
        { value: 10, text: "10 / \u9875" },
        { value: 20, text: "20 / \u9875" },
        { value: 50, text: "50 / \u9875" }
    ]

    function addTicketPageItem(items, page) {
        items.push({
            type: "page",
            label: String(page),
            page: page,
            enabled: true,
            current: page === ticketCurrentPage
        })
    }

    function addTicketPageGap(items) {
        items.push({
            type: "gap",
            label: "...",
            page: -1,
            enabled: false,
            current: false
        })
    }

    function ticketPaginationItems() {
        var items = []
        var totalPages = ticketTotalPages
        var currentPage = ticketCurrentPage
        if (totalPages <= 8) {
            for (var page = 1; page <= totalPages; page += 1) {
                addTicketPageItem(items, page)
            }
            return items
        }

        if (currentPage <= 5) {
            for (var firstPage = 1; firstPage <= 7; firstPage += 1) {
                addTicketPageItem(items, firstPage)
            }
            addTicketPageGap(items)
            addTicketPageItem(items, totalPages)
            return items
        }

        if (currentPage >= totalPages - 4) {
            addTicketPageItem(items, 1)
            addTicketPageGap(items)
            for (var lastPage = totalPages - 6; lastPage <= totalPages; lastPage += 1) {
                addTicketPageItem(items, lastPage)
            }
            return items
        }

        addTicketPageItem(items, 1)
        addTicketPageGap(items)
        for (var nearbyPage = currentPage - 2; nearbyPage <= currentPage + 2; nearbyPage += 1) {
            addTicketPageItem(items, nearbyPage)
        }
        addTicketPageGap(items)
        addTicketPageItem(items, totalPages)
        return items
    }

    function currentStatusValue() {
        var index = ticketStatusCombo.currentIndex
        if (index < 0 || index >= statusOptions.length) {
            return "open"
        }
        return statusOptions[index].value
    }

    function statusTextColor(statusTone) {
        if (statusTone === "done") {
            return "#466B57"
        }
        if (statusTone === "open") {
            return "#2F6A58"
        }
        return theme.bodyInk
    }

    function statusDotColor(statusTone) {
        if (statusTone === "done") {
            return "#7FA68E"
        }
        if (statusTone === "open") {
            return "#4C8A74"
        }
        return "#9AA4AF"
    }

    function displayProductLine(value, index) {
        var text = String(value || "").trim()
        if (text.length > 0) {
            return text
        }
        return index % 2 === 0 ? "\u6587\u6863\u4e2d\u53f0" : "\u6587\u6863\u4e2d\u5fc3"
    }

    function displayTicketType(value, index) {
        var text = String(value || "").trim()
        if (text.length > 0) {
            return text
        }
        var options = ["\u6392\u67e5\u7c7b", "\u54a8\u8be2\u7c7b", "\u64cd\u4f5c\u7c7b"]
        return options[index % options.length]
    }

    function refreshTicketListView(resetPage) {
        var sourceTickets = controlPanelBridge.tickets || []
        var nextTickets = []
        for (var i = 0; i < sourceTickets.length; i += 1) {
            var ticket = sourceTickets[i]
            var productLine = String(ticket.productLine || "").trim()
            var ticketType = String(ticket.ticketType || "").trim()
            if (selectedProductLine !== "all" && productLine !== selectedProductLine) {
                continue
            }
            if (selectedTicketType !== "all" && ticketType !== selectedTicketType) {
                continue
            }
            nextTickets.push(ticket)
        }

        filteredTickets = nextTickets
        if (resetPage) {
            ticketCurrentPage = 1
        }
        if (ticketCurrentPage > ticketTotalPages) {
            ticketCurrentPage = ticketTotalPages
        }
        if (ticketCurrentPage < 1) {
            ticketCurrentPage = 1
        }

        var start = (ticketCurrentPage - 1) * ticketPageSize
        pagedTickets = nextTickets.slice(start, start + ticketPageSize)
    }

    function setTicketPage(page) {
        var nextPage = Math.max(1, Math.min(ticketTotalPages, page))
        if (nextPage === ticketCurrentPage && pagedTickets.length > 0) {
            return
        }
        ticketCurrentPage = nextPage
        refreshTicketListView(false)
    }

    function currentTicketFieldValue(fieldName) {
        if (fieldName === "achNo") {
            return controlPanelBridge.selectedTicket.achNo || ""
        }
        if (fieldName === "ticketVersion") {
            return controlPanelBridge.selectedTicket.ticketVersion || ""
        }
        if (fieldName === "customerEnvironment") {
            return controlPanelBridge.selectedTicket.customerEnvironmentValue || ""
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
        unlinkProjectConfirmVisible = false
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
        unlinkProjectConfirmVisible = false
        deleteTicketConfirmVisible = true
    }

    function requestReopenSelectedTicket() {
        if (!controlPanelBridge.selectedTicket.id || activeActionField.length > 0 || deleteTicketConfirmVisible || unlinkProjectConfirmVisible) {
            return
        }
        for (var key in fieldStates) {
            if (fieldStates[key].saving) {
                return
            }
        }
        controlPanelBridge.reopenSelectedTicket()
    }

    function canUnlinkSelectedTicketProject() {
        var ticket = controlPanelBridge.selectedTicket || {}
        var status = String(ticket.projectStatus || "").trim()
        if (status !== "matched" && status !== "manual" && status !== "expired") {
            return false
        }
        return String(ticket.projectName || ticket.taskOrderNo || ticket.projectStatusDetail || "").trim().length > 0
    }

    function requestUnlinkSelectedTicketProject() {
        if (!controlPanelBridge.selectedTicket.id || activeActionField.length > 0 || deleteTicketConfirmVisible) {
            return
        }
        if (!canUnlinkSelectedTicketProject()) {
            return
        }
        for (var key in fieldStates) {
            if (fieldStates[key].saving) {
                return
            }
        }
        unlinkProjectConfirmVisible = true
    }

    function cancelUnlinkSelectedTicketProject() {
        unlinkProjectConfirmVisible = false
    }

    function confirmUnlinkSelectedTicketProject() {
        if (!controlPanelBridge.selectedTicket.id) {
            unlinkProjectConfirmVisible = false
            return
        }
        unlinkProjectConfirmVisible = false
        controlPanelBridge.unlinkSelectedTicketProject()
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

    Component.onCompleted: refreshTicketListView(true)

    Connections {
        target: controlPanelBridge
        function onDataChanged() {
            ticketSection.refreshTicketListView(true)
        }
    }

    PageRuntime {
        id: ticketListRuntime
        visible: controlPanelBridge.selectedTicket.id.length === 0
        theme: ticketSection.theme
        Layout.fillWidth: true
        Layout.fillHeight: true
        listMinimumHeight: ticketTotalCount > 0 ? 520 : 180

        filterContent: Flow {
            id: searchToolbar
            Layout.fillWidth: true
            spacing: 10

                            ControlPanelSettingsInput {
                                id: ticketSearchInput
                                theme: ticketSection.theme
                                width: Math.max(320, parent.width - 366)
                                text: controlPanelBridge.ticketQuery
                                placeholderText: "\u641c\u7d22\u5de5\u5355\u6807\u9898"
                                onTextEdited: controlPanelBridge.listTickets(text, ticketSection.currentStatusValue())
                            }

                            ControlPanelSettingsCombo {
                                id: ticketStatusCombo
                                theme: ticketSection.theme
                                width: 108
                                model: ticketSection.statusOptions
                                currentIndex: ticketSection.theme.optionIndex(ticketSection.statusOptions, controlPanelBridge.ticketStatusFilter)
                                onActivated: if (currentIndex >= 0) controlPanelBridge.listTickets(ticketSearchInput.text, ticketSection.statusOptions[currentIndex].value)
                            }

                            ControlPanelSettingsCombo {
                                id: ticketProductLineCombo
                                theme: ticketSection.theme
                                width: 112
                                model: ticketSection.productLineOptions
                                currentIndex: ticketSection.theme.optionIndex(ticketSection.productLineOptions, ticketSection.selectedProductLine)
                                onActivated: {
                                    if (currentIndex < 0) {
                                        return
                                    }
                                    ticketSection.selectedProductLine = ticketSection.productLineOptions[currentIndex].value
                                    ticketSection.refreshTicketListView(true)
                                }
                            }

                            ControlPanelSettingsCombo {
                                id: ticketTypeCombo
                                theme: ticketSection.theme
                                width: 96
                                model: ticketSection.ticketTypeOptions
                                currentIndex: ticketSection.theme.optionIndex(ticketSection.ticketTypeOptions, ticketSection.selectedTicketType)
                                onActivated: {
                                    if (currentIndex < 0) {
                                        return
                                    }
                                    ticketSection.selectedTicketType = ticketSection.ticketTypeOptions[currentIndex].value
                                    ticketSection.refreshTicketListView(true)
                                }
                            }

        }

        actionContent: ColumnLayout {
            Layout.fillWidth: true
            spacing: 8

            Flow {
                id: ticketActionToolbar
                Layout.fillWidth: true
                spacing: 10

                ControlPanelPlainButton {
                    theme: ticketSection.theme
                    label: controlPanelBridge.workOrderSyncing ? "\u540c\u6b65\u4e2d" : "\u4e00\u952e\u540c\u6b65"
                    enabled: !controlPanelBridge.workOrderSyncing
                    primary: true
                    strokeWidth: 0
                    onClicked: controlPanelBridge.syncWorkOrdersToServer()
                }

                ControlPanelPlainButton {
                    theme: ticketSection.theme
                    label: controlPanelBridge.workOrderSyncing ? "\u62c9\u53d6\u4e2d" : "\u4e00\u952e\u62c9\u53d6"
                    enabled: !controlPanelBridge.workOrderSyncing
                    onClicked: controlPanelBridge.pullWorkOrdersFromServer()
                }
            }

            Text {
                visible: controlPanelBridge.workOrderSyncMessage.length > 0
                Layout.fillWidth: true
                text: controlPanelBridge.workOrderSyncMessage
                color: theme.mutedInk
                font.family: theme.uiFont
                font.pixelSize: 12
                elide: Text.ElideRight
            }
        }

        listContent: ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

                    Item {
                        visible: ticketTotalCount === 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 132

                        Text {
                            anchors.centerIn: parent
                            text: "\u5f53\u524d\u7b5b\u9009\u6761\u4ef6\u4e0b\u6ca1\u6709\u5de5\u5355"
                            color: theme.bodyInk
                            font.family: theme.uiFont
                            font.pixelSize: 13
                        }
                    }

                    Item {
                        visible: ticketTotalCount > 0
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true

                        Item {
                            id: tableFlickable
                            anchors.fill: parent
                            clip: true
                            property real sidePadding: 18
                            property real columnSpacing: 12
                            property real tableInnerWidth: Math.max(780, width - sidePadding * 2 - columnSpacing * 8)
                            property real tableContentWidth: tableInnerWidth + sidePadding * 2 + columnSpacing * 8
                            property real titleColumnWidth: Math.round(tableInnerWidth * 0.22)
                            property real statusColumnWidth: Math.round(tableInnerWidth * 0.08)
                            property real statusProjectGapWidth: Math.round(tableInnerWidth * 0.06)
                            property real projectColumnWidth: Math.round(tableInnerWidth * 0.15)
                            property real projectProductGapWidth: Math.round(tableInnerWidth * 0.07)
                            property real productColumnWidth: Math.round(tableInnerWidth * 0.10)
                            property real typeColumnWidth: Math.round(tableInnerWidth * 0.08)
                            property real updatedColumnWidth: Math.round(tableInnerWidth * 0.13)
                            property real actionColumnWidth: Math.round(tableInnerWidth * 0.09)

                            Flickable {
                                id: tableHorizontalFlickable
                                anchors.top: parent.top
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                contentWidth: tableColumn.width
                                contentHeight: height
                                flickableDirection: Flickable.HorizontalFlick
                                interactive: contentWidth > width

                                ScrollBar.horizontal: ScrollBar {
                                    policy: ScrollBar.AsNeeded
                                }

                                Column {
                                    id: tableColumn
                                    width: Math.max(tableHorizontalFlickable.width, tableFlickable.tableContentWidth)
                                    spacing: 0

                                    Rectangle {
                                        id: tableHeader
                                        width: parent.width
                                        height: 42
                                        color: "transparent"

                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: tableFlickable.sidePadding
                                            anchors.rightMargin: tableFlickable.sidePadding
                                            spacing: tableFlickable.columnSpacing

                                            Text {
                                                Layout.preferredWidth: tableFlickable.titleColumnWidth
                                                text: "\u5de5\u5355\u6807\u9898"
                                                color: "#7A857F"
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                                horizontalAlignment: Text.AlignLeft
                                                verticalAlignment: Text.AlignVCenter
                                            }

                                            Text {
                                                Layout.preferredWidth: tableFlickable.statusColumnWidth
                                                text: "\u72b6\u6001"
                                                color: "#7A857F"
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }

                                            Item {
                                                Layout.preferredWidth: tableFlickable.statusProjectGapWidth
                                                Layout.fillHeight: true
                                            }

                                            Text {
                                                Layout.preferredWidth: tableFlickable.projectColumnWidth
                                                text: "\u9879\u76ee"
                                                color: "#7A857F"
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                                horizontalAlignment: Text.AlignLeft
                                                verticalAlignment: Text.AlignVCenter
                                            }

                                            Item {
                                                Layout.preferredWidth: tableFlickable.projectProductGapWidth
                                                Layout.fillHeight: true
                                            }

                                            Text {
                                                Layout.preferredWidth: tableFlickable.productColumnWidth
                                                text: "\u4ea7\u54c1\u7ebf"
                                                color: "#7A857F"
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                                horizontalAlignment: Text.AlignLeft
                                                verticalAlignment: Text.AlignVCenter
                                            }

                                            Text {
                                                Layout.preferredWidth: tableFlickable.typeColumnWidth
                                                text: "\u7c7b\u578b"
                                                color: "#7A857F"
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                                horizontalAlignment: Text.AlignLeft
                                                verticalAlignment: Text.AlignVCenter
                                            }

                                            Text {
                                                Layout.preferredWidth: tableFlickable.updatedColumnWidth
                                                text: "\u66f4\u65b0\u65f6\u95f4"
                                                color: "#7A857F"
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }

                                            Text {
                                                Layout.preferredWidth: tableFlickable.actionColumnWidth
                                                text: "\u64cd\u4f5c"
                                                color: "#7A857F"
                                                font.family: theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                        }
                                    }

                                    Rectangle {
                                        width: parent.width
                                        height: 1
                                        color: theme.panelLine
                                    }

                                    ListView {
                                        id: ticketTableView
                                        width: parent.width
                                        height: Math.max(0, tableHorizontalFlickable.height - tableHeader.height - 1)
                                        clip: true
                                        spacing: 0
                                        model: ticketSection.pagedTickets
                                        boundsBehavior: Flickable.StopAtBounds

                                        delegate: Item {
                                            width: ticketTableView.width
                                            height: 54

                                            Rectangle {
                                                anchors.fill: parent
                                                color: "transparent"

                                                MouseArea {
                                                    id: rowDetailMouseArea
                                                    anchors.left: parent.left
                                                    anchors.top: parent.top
                                                    anchors.bottom: parent.bottom
                                                    width: Math.max(0, parent.width - tableFlickable.sidePadding - tableFlickable.actionColumnWidth)
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: function(mouse) {
                                                        mouse.accepted = true
                                                        controlPanelBridge.openTicketDetail(modelData.id)
                                                    }
                                                }

                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: tableFlickable.sidePadding
                                                    anchors.rightMargin: tableFlickable.sidePadding
                                                    spacing: tableFlickable.columnSpacing

                                                    Text {
                                                        Layout.preferredWidth: tableFlickable.titleColumnWidth
                                                        text: modelData.title || "\u672a\u5206\u7c7b\u4efb\u52a1"
                                                        color: theme.titleInk
                                                        font.family: theme.uiFont
                                                        font.pixelSize: 13
                                                        font.weight: 600
                                                        elide: Text.ElideRight
                                                        horizontalAlignment: Text.AlignLeft
                                                        verticalAlignment: Text.AlignVCenter
                                                    }

                                                Item {
                                                    Layout.preferredWidth: tableFlickable.statusColumnWidth
                                                    Layout.fillHeight: true

                                                    Row {
                                                        anchors.centerIn: parent
                                                        spacing: 6

                                                        Rectangle {
                                                            width: 6
                                                            height: 6
                                                            radius: 3
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            color: ticketSection.statusDotColor(modelData.statusTone)
                                                        }

                                                        Text {
                                                            text: modelData.statusLabel || "\u672a\u77e5"
                                                            color: ticketSection.statusTextColor(modelData.statusTone)
                                                            font.family: theme.uiFont
                                                            font.pixelSize: 12
                                                            font.weight: 600
                                                            anchors.verticalCenter: parent.verticalCenter
                                                        }
                                                    }
                                                }

                                                Item {
                                                    Layout.preferredWidth: tableFlickable.statusProjectGapWidth
                                                    Layout.fillHeight: true
                                                }

                                                Text {
                                                    Layout.preferredWidth: tableFlickable.projectColumnWidth
                                                    text: {
                                                        var projectName = modelData.projectName || ""
                                                        if (Array.isArray(projectName)) {
                                                            return projectName.length > 0 ? projectName[0] : "\u672a\u5173\u8054"
                                                        }
                                                        return projectName || "\u672a\u5173\u8054"
                                                    }
                                                    color: theme.bodyInk
                                                    font.family: theme.uiFont
                                                    font.pixelSize: 12
                                                    font.weight: 500
                                                    elide: Text.ElideRight
                                                    horizontalAlignment: Text.AlignLeft
                                                    verticalAlignment: Text.AlignVCenter
                                                }

                                                Item {
                                                    Layout.preferredWidth: tableFlickable.projectProductGapWidth
                                                    Layout.fillHeight: true
                                                }

                                                Text {
                                                    Layout.preferredWidth: tableFlickable.productColumnWidth
                                                    text: ticketSection.displayProductLine(modelData.productLine, index)
                                                    color: theme.bodyInk
                                                    font.family: theme.uiFont
                                                    font.pixelSize: 12
                                                    font.weight: 500
                                                    elide: Text.ElideRight
                                                    horizontalAlignment: Text.AlignLeft
                                                    verticalAlignment: Text.AlignVCenter
                                                }

                                                Text {
                                                    Layout.preferredWidth: tableFlickable.typeColumnWidth
                                                    text: ticketSection.displayTicketType(modelData.ticketType, index)
                                                    color: theme.bodyInk
                                                    font.family: theme.uiFont
                                                    font.pixelSize: 12
                                                    font.weight: 500
                                                    elide: Text.ElideRight
                                                    horizontalAlignment: Text.AlignLeft
                                                    verticalAlignment: Text.AlignVCenter
                                                }

                                                Text {
                                                    Layout.preferredWidth: tableFlickable.updatedColumnWidth
                                                    text: modelData.updatedAtLabel || "\u672a\u77e5"
                                                    color: "#6D7885"
                                                    font.family: theme.uiFont
                                                    font.pixelSize: 12
                                                    horizontalAlignment: Text.AlignHCenter
                                                    verticalAlignment: Text.AlignVCenter
                                                    elide: Text.ElideRight
                                                }

                                                Item {
                                                    Layout.preferredWidth: tableFlickable.actionColumnWidth
                                                    Layout.fillHeight: true

                                                    Row {
                                                        anchors.centerIn: parent
                                                        spacing: 12

                                                        Text {
                                                            text: "\u8be6\u60c5"
                                                            color: detailMouseArea.containsMouse ? theme.accent : "#7D8793"
                                                            font.family: theme.uiFont
                                                            font.pixelSize: 12
                                                            verticalAlignment: Text.AlignVCenter

                                                            Behavior on color {
                                                                ColorAnimation { duration: 100 }
                                                            }

                                                            MouseArea {
                                                                id: detailMouseArea
                                                                anchors.fill: parent
                                                                hoverEnabled: true
                                                                cursorShape: Qt.PointingHandCursor
                                                                onClicked: function(mouse) {
                                                                    mouse.accepted = true
                                                                    controlPanelBridge.openTicketDetail(modelData.id)
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }

                                            Rectangle {
                                                visible: index < ticketSection.pagedTickets.length - 1
                                                anchors.bottom: parent.bottom
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                anchors.leftMargin: tableFlickable.sidePadding
                                                anchors.rightMargin: tableFlickable.sidePadding
                                                height: 1
                                                color: theme.panelLine
                                            }
                                        }
                                    }
                                }
                            }


                        }
                    }
                }
            }

        footerContent: Rectangle {
            id: paginationBar
            visible: ticketTotalCount > 0
            Layout.fillWidth: true
            implicitHeight: 50
            color: "transparent"

            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: theme.panelLine
            }

            Row {
                id: paginationSummary
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 16
                spacing: 6

                Rectangle {
                    id: previousPageButton
                    width: 28
                    height: 28
                    radius: 6
                    color: previousPageMouseArea.containsMouse && ticketSection.ticketCurrentPage > 1 ? (theme.hoverBg || "#F6F8FB") : theme.panelBg
                    border.width: 1
                    border.color: theme.panelLine
                    opacity: ticketSection.ticketCurrentPage > 1 ? 1.0 : 0.55

                    Canvas {
                        anchors.centerIn: parent
                        width: 8
                        height: 12
                        contextType: "2d"
                        onPaint: {
                            context.reset()
                            context.lineWidth = 1.8
                            context.strokeStyle = theme.bodyInk
                            context.lineCap = "round"
                            context.lineJoin = "round"
                            context.beginPath()
                            context.moveTo(width - 2, 2)
                            context.lineTo(2, height / 2)
                            context.lineTo(width - 2, height - 2)
                            context.stroke()
                        }
                    }

                    MouseArea {
                        id: previousPageMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: ticketSection.ticketCurrentPage > 1
                        cursorShape: Qt.PointingHandCursor
                        onClicked: ticketSection.setTicketPage(ticketSection.ticketCurrentPage - 1)
                    }
                }

                Repeater {
                    model: ticketSection.ticketPaginationItems()

                    delegate: Rectangle {
                        property var pageItem: modelData
                        width: pageItem.type === "gap" ? 30 : 28
                        height: 28
                        radius: 6
                        color: pageMouseArea.containsMouse && pageItem.enabled && !pageItem.current ? (theme.hoverBg || "#F6F8FB") : "transparent"
                        border.width: pageItem.current ? 1 : 0
                        border.color: "#111827"

                        Text {
                            anchors.centerIn: parent
                            text: parent.pageItem.label
                            color: parent.pageItem.current ? theme.titleInk : theme.bodyInk
                            font.family: theme.uiFont
                            font.pixelSize: 13
                            font.weight: parent.pageItem.current ? 600 : 500
                        }

                        MouseArea {
                            id: pageMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: parent.pageItem.enabled && !parent.pageItem.current
                            cursorShape: Qt.PointingHandCursor
                            onClicked: ticketSection.setTicketPage(parent.pageItem.page)
                        }
                    }
                }

                Rectangle {
                    id: nextPageButton
                    width: 28
                    height: 28
                    radius: 6
                    color: nextPageMouseArea.containsMouse && ticketSection.ticketCurrentPage < ticketSection.ticketTotalPages ? (theme.hoverBg || "#F6F8FB") : theme.panelBg
                    border.width: 1
                    border.color: theme.panelLine
                    opacity: ticketSection.ticketCurrentPage < ticketSection.ticketTotalPages ? 1.0 : 0.55

                    Canvas {
                        anchors.centerIn: parent
                        width: 8
                        height: 12
                        contextType: "2d"
                        onPaint: {
                            context.reset()
                            context.lineWidth = 1.8
                            context.strokeStyle = theme.bodyInk
                            context.lineCap = "round"
                            context.lineJoin = "round"
                            context.beginPath()
                            context.moveTo(2, 2)
                            context.lineTo(width - 2, height / 2)
                            context.lineTo(2, height - 2)
                            context.stroke()
                        }
                    }

                    MouseArea {
                        id: nextPageMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: ticketSection.ticketCurrentPage < ticketSection.ticketTotalPages
                        cursorShape: Qt.PointingHandCursor
                        onClicked: ticketSection.setTicketPage(ticketSection.ticketCurrentPage + 1)
                    }
                }

                ControlPanelSettingsCombo {
                    id: pageSizeCombo
                    theme: ticketSection.theme
                    width: 86
                    height: 28
                    fieldRadius: 6
                    fieldFontSize: 12
                    leftPadding: 10
                    rightPadding: 28
                    topPadding: 6
                    bottomPadding: 6
                    model: ticketSection.pageSizeOptions
                    currentIndex: ticketSection.theme.optionIndex(ticketSection.pageSizeOptions, ticketSection.ticketPageSize)
                    onActivated: {
                        if (currentIndex < 0) {
                            return
                        }
                        ticketSection.ticketPageSize = ticketSection.pageSizeOptions[currentIndex].value
                        ticketSection.refreshTicketListView(true)
                    }
                }

                Text {
                    height: 28
                    text: "\u5171 " + ticketSection.ticketTotalCount + " \u6761"
                    color: theme.bodyInk
                    font.family: theme.uiFont
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 14
                    rightPadding: 4
                }

                Text {
                    height: 28
                    text: "\u5171 " + ticketSection.ticketTotalPages + " \u9875"
                    color: theme.bodyInk
                    font.family: theme.uiFont
                    font.pixelSize: 13
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 8
                    rightPadding: 0
                }
            }
        }
    }

    DetailRuntime {
        visible: controlPanelBridge.selectedTicket.id.length > 0
        theme: ticketSection.theme
        Layout.fillWidth: true
        onBackRequested: {
            ticketSection.cancelDeleteSelectedTicket()
            ticketSection.cancelUnlinkSelectedTicketProject()
            controlPanelBridge.backToTicketList()
        }

        actionContent: RowLayout {
            ControlPanelPlainButton {
                visible: controlPanelBridge.selectedTicket.status === "done"
                theme: ticketSection.theme
                label: "\u91cd\u65b0\u6253\u5f00"
                onClicked: ticketSection.requestReopenSelectedTicket()
            }

            ControlPanelPlainButton {
                theme: ticketSection.theme
                label: "\u5220\u9664\u5de5\u5355"
                onClicked: ticketSection.requestDeleteSelectedTicket()
            }
        }

        bodyContent: ColumnLayout {
            id: ticketDetailContent
            Layout.fillWidth: true
            spacing: 18

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
                                primary: true
                                strokeWidth: 0
                                onClicked: ticketSection.confirmDeleteSelectedTicket()
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: 12
                    color: theme.panelAltBg
                    border.width: 0
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
                            color: theme.panelLine
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
                                                    color: theme.panelLine
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
                                                            color: theme.inputBg
                                                            border.width: 1
                                                            border.color: theme.panelLine
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
                                                    color: theme.panelLine
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
                                            value: controlPanelBridge.selectedTicket.achNo
                                            placeholderText: "未填写"
                                            editable: false
                                            editing: false
                                            saving: false
                                            compact: ticketSection.detailGridColumns === 1
                                        }

                                        DetailField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "ach填写时间"
                                            value: controlPanelBridge.selectedTicket.achFilledAtLabel
                                            placeholderText: "未填写"
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.columnSpan: ticketSection.detailGridColumns
                                            spacing: 10

                                            DetailField {
                                                theme: ticketSection.theme
                                                Layout.fillWidth: true
                                                label: "项目关联"
                                                value: controlPanelBridge.selectedTicket.projectStatusDetail
                                                placeholderText: "暂无项目关联信息"
                                                multiline: true
                                                actionVisible: ticketSection.canUnlinkSelectedTicketProject()
                                                actionText: "解除"
                                                actionInkColor: "#B75B2B"
                                                onActionTriggered: ticketSection.requestUnlinkSelectedTicketProject()
                                            }

                                            Rectangle {
                                                visible: ticketSection.unlinkProjectConfirmVisible
                                                Layout.fillWidth: true
                                                radius: 16
                                                color: "#FFF7F4"
                                                border.width: 1
                                                border.color: "#E7C8BF"
                                                implicitHeight: unlinkProjectConfirmColumn.implicitHeight + 20

                                                ColumnLayout {
                                                    id: unlinkProjectConfirmColumn
                                                    anchors.fill: parent
                                                    anchors.margins: 10
                                                    spacing: 8

                                                    Text {
                                                        Layout.fillWidth: true
                                                        text: "确认解除当前工单的项目关联吗？"
                                                        color: theme.titleInk
                                                        font.family: theme.uiFont
                                                        font.pixelSize: 13
                                                        font.weight: 700
                                                        wrapMode: Text.Wrap
                                                    }

                                                    Text {
                                                        Layout.fillWidth: true
                                                        text: "解除后会清空项目关联、产品线和版本号；之后自动或批量关联仍可重新匹配。"
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
                                                            label: "取消"
                                                            onClicked: ticketSection.cancelUnlinkSelectedTicketProject()
                                                        }

                                                        ControlPanelPlainButton {
                                                            theme: ticketSection.theme
                                                            label: "确认解除"
                                                            primary: true
                                                            strokeWidth: 0
                                                            onClicked: ticketSection.confirmUnlinkSelectedTicketProject()
                                                        }
                                                    }
                                                }
                                            }
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

                                        SingleSelectCascadeField {
                                            theme: ticketSection.theme
                                            Layout.fillWidth: true
                                            label: "客户环境"
                                            value: controlPanelBridge.selectedTicket.customerEnvironmentValue || ""
                                            selectedCode: controlPanelBridge.selectedTicket.customerEnvironmentCode || ""
                                            placeholderText: "未填写"
                                            editing: !!controlPanelBridge.selectedTicket.customerEnvironmentEditable && ticketSection.isFieldEditing("customerEnvironment")
                                            saving: ticketSection.isFieldSaving("customerEnvironment")
                                            compact: ticketSection.detailGridColumns === 1
                                            options: controlPanelBridge.selectedTicket.customerEnvironmentOptions || []
                                            onClicked: {
                                                if (!controlPanelBridge.selectedTicket.customerEnvironmentEditable || ticketSection.activeActionField.length > 0) {
                                                    return
                                                }
                                                ticketSection.beginTicketFieldEdit("customerEnvironment")
                                            }
                                            onAccepted: function(code, value) {
                                                ticketSection.setFieldState("customerEnvironment", { draft: value, original: currentTicketFieldValue("customerEnvironment"), saving: true, editing: false })
                                                Qt.callLater(function() {
                                                    if (!ticketSection.isFieldSaving("customerEnvironment")) {
                                                        return
                                                    }
                                                    controlPanelBridge.saveSelectedTicketField("customer_environment", code)
                                                })
                                            }
                                            onCanceled: ticketSection.cancelTicketFieldEdit("customerEnvironment")
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
                                            actionIconSource: controlPanelBridge.refreshFeaturePointIconSource
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

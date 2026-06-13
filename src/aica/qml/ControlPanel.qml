import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 1040
    height: 760
    color: "transparent"

    readonly property var themeTokens: typeof theme !== "undefined" ? theme : (controlPanelBridge ? controlPanelBridge.themeTokens : ({}))
    readonly property color shellBg: themeTokens.shellBg || "#FFFFFF"
    readonly property color panelBg: themeTokens.panelBg || "#FFFFFF"
    readonly property color panelAltBg: themeTokens.panelAltBg || "#F8F9FA"
    readonly property color panelLine: themeTokens.panelLine || "#E5E7EB"
    readonly property color titleInk: themeTokens.titleInk || "#2A313F"
    readonly property color bodyInk: themeTokens.bodyInk || "#4A5565"
    readonly property color labelInk: themeTokens.labelInk || "#7C8795"
    readonly property color mutedInk: themeTokens.mutedInk || "#A9B1BD"
    readonly property color accent: themeTokens.accent || "#2A313F"
    readonly property color accentSoft: themeTokens.accentSoft || "#F1F3F6"
    readonly property color accentTint: themeTokens.accentTint || "#ECEFF3"
    readonly property color buttonPrimaryBg: themeTokens.buttonPrimaryBg || accent
    readonly property color buttonPrimaryBgHover: themeTokens.buttonPrimaryBgHover || buttonPrimaryBg
    readonly property color buttonPrimaryBgPressed: themeTokens.buttonPrimaryBgPressed || buttonPrimaryBgHover
    readonly property color buttonPrimaryInk: themeTokens.buttonPrimaryInk || "#FFFFFF"
    readonly property color buttonDefaultBg: themeTokens.buttonDefaultBg || "#FFFFFF"
    readonly property color buttonDefaultBgHover: themeTokens.buttonDefaultBgHover || hoverBg
    readonly property color buttonDefaultBgPressed: themeTokens.buttonDefaultBgPressed || pressedBg
    readonly property color buttonDefaultInk: themeTokens.buttonDefaultInk || bodyInk
    readonly property color buttonDisabledBg: themeTokens.buttonDisabledBg || panelAltBg
    readonly property color buttonDisabledInk: themeTokens.buttonDisabledInk || mutedInk
    readonly property color buttonBorder: themeTokens.buttonBorder || panelLine
    readonly property int buttonRadius: themeTokens.buttonRadius || 6
    readonly property int buttonHeight: themeTokens.buttonHeight || 35
    readonly property int buttonPaddingH: themeTokens.buttonPaddingH || 12
    readonly property int buttonFontSize: themeTokens.buttonFontSize || fontBody
    readonly property int componentRadius: themeTokens.componentRadius || 8
    readonly property int componentHeight: themeTokens.componentHeight || 36
    readonly property color navIdle: themeTokens.navIdle || "#F8F9FA"
    readonly property color inputBg: themeTokens.inputBg || "#FFFFFF"
    readonly property color hoverBg: themeTokens.hoverBg || "#F3F4F6"
    readonly property color pressedBg: themeTokens.pressedBg || "#E5E7EB"
    readonly property color errorBg: themeTokens.errorBg || "#FDECEC"
    readonly property color errorInk: themeTokens.errorInk || "#B42318"
    readonly property color successBg: themeTokens.successBg || "#E7F5ED"
    readonly property color successInk: themeTokens.successInk || "#17663A"
    readonly property int radiusSm: themeTokens.radiusSm || 8
    readonly property int radiusMd: themeTokens.radiusMd || 12
    readonly property int radiusLg: themeTokens.radiusLg || 16
    readonly property int radiusCard: themeTokens.radiusCard || 24
    readonly property int fontCaption: themeTokens.fontCaption || 11
    readonly property int fontBody: themeTokens.fontBody || 12
    readonly property int fontBodyLg: themeTokens.fontBodyLg || 13
    readonly property int fontSection: themeTokens.fontSection || 15
    readonly property int fontTitle: themeTokens.fontTitle || 18
    readonly property int formFieldHeight: themeTokens.formFieldHeight || 36
    readonly property int formFieldCompactHeight: themeTokens.formFieldCompactHeight || 28
    readonly property int formFieldRadius: themeTokens.formFieldRadius || 8
    readonly property int formFieldCompactRadius: themeTokens.formFieldCompactRadius || 8
    readonly property int formFieldPaddingH: themeTokens.formFieldPaddingH || 12
    readonly property int formFieldPaddingV: themeTokens.formFieldPaddingV || 8
    readonly property int formFieldCompactPaddingH: themeTokens.formFieldCompactPaddingH || 8
    readonly property int formFieldFontSize: themeTokens.formFieldFontSize || fontBody
    readonly property int formFieldCompactFontSize: themeTokens.formFieldCompactFontSize || fontBodyLg
    readonly property color formFieldBg: themeTokens.formFieldBg || inputBg
    readonly property color formFieldBorder: themeTokens.formFieldBorder || panelLine
    readonly property color formFieldFocusBorder: themeTokens.formFieldFocusBorder || accent
    readonly property color formFieldPlaceholderInk: themeTokens.formFieldPlaceholderInk || labelInk
    readonly property int formPopupRadius: themeTokens.formPopupRadius || 12
    readonly property int formPopupItemRadius: themeTokens.formPopupItemRadius || 8
    readonly property int formPopupItemHeight: themeTokens.formPopupItemHeight || 38
    readonly property color formPopupBg: themeTokens.formPopupBg || "#FFFFFF"
    readonly property color formPopupHoverBg: themeTokens.formPopupHoverBg || hoverBg
    readonly property int formInlineEditHeight: themeTokens.formInlineEditHeight || formFieldCompactHeight
    readonly property int formChipHeight: themeTokens.formChipHeight || 28
    readonly property int formChipRadius: themeTokens.formChipRadius || 14
    readonly property int formCheckSpacing: themeTokens.formCheckSpacing || 8
    readonly property string uiFont: themeTokens.uiFont || (controlPanelBridge ? controlPanelBridge.uiFont : "Microsoft YaHei UI")
    readonly property string currentSection: controlPanelBridge ? controlPanelBridge.currentSection : ""
    readonly property var currentSectionMeta: controlPanelBridge ? (controlPanelBridge.currentSectionMeta || ({})) : ({})
    readonly property var projectLevelOptions: [
        { value: "normal", text: "常规" },
        { value: "important", text: "重要" }
    ]
    property var projectDraft: emptyProjectDraft()
    property string projectAliasInput: ""
    property string projectViewMode: "list"
    property string selectedProviderId: ""

    function optionIndex(options, value) {
        for (var index = 0; index < options.length; index += 1) {
            if (options[index].value === value) {
                return index
            }
        }
        return options.length > 0 ? 0 : -1
    }

    function optionText(options, value) {
        for (var index = 0; index < options.length; index += 1) {
            if (options[index].value === value) {
                return options[index].text
            }
        }
        return value || ""
    }

    function itemIndexById(items, value) {
        for (var index = 0; index < items.length; index += 1) {
            if (items[index].id === value) {
                return index
            }
        }
        return items.length > 0 ? 0 : -1
    }

    function ensureSelectedProvider() {
        if (!controlPanelBridge || root.currentSection !== "models") {
            return
        }
        var providers = controlPanelBridge.providers || []
        if (!providers.length) {
            selectedProviderId = ""
            return
        }
        for (var index = 0; index < providers.length; index += 1) {
            if (providers[index].id === selectedProviderId) {
                return
            }
        }
        selectedProviderId = providers[0].id
    }

    function selectedProviderPayload() {
        var providers = controlPanelBridge ? (controlPanelBridge.providers || []) : []
        for (var index = 0; index < providers.length; index += 1) {
            if (providers[index].id === selectedProviderId) {
                return providers[index]
            }
        }
        return providers.length ? providers[0] : null
    }

    function fuzzyMatch(text, query) {
        var source = (text || "").toLowerCase()
        var keyword = (query || "").toLowerCase().trim()
        if (!keyword.length) {
            return true
        }
        if (source.indexOf(keyword) >= 0) {
            return true
        }
        var sourceIndex = 0
        for (var queryIndex = 0; queryIndex < keyword.length; queryIndex += 1) {
            var charIndex = source.indexOf(keyword[queryIndex], sourceIndex)
            if (charIndex < 0) {
                return false
            }
            sourceIndex = charIndex + 1
        }
        return true
    }

    function emptyProjectDraft() {
        return {
            id: "",
            projectName: "",
            customerName: "",
            taskOrderNo: "",
            followUpStartedAt: "",
            supportEndedAt: "",
            productLine: "",
            productVersion: "",
            projectManager: "",
            projectLevel: "normal",
            aliases: []
        }
    }

    function projectAliasText(value) {
        if (value === null || value === undefined) {
            return ""
        }
        if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
            return value.toString().trim()
        }
        var keys = ["alias", "aliasName", "alias_name", "name", "text", "label", "groupName", "group_name", "modelData"]
        for (var index = 0; index < keys.length; index += 1) {
            var key = keys[index]
            if (value[key] !== undefined && value[key] !== null) {
                var text = projectAliasText(value[key])
                if (text.length > 0) {
                    return text
                }
            }
        }
        return ""
    }

    function normalizedProjectAliases(values) {
        var source = values || []
        var result = []
        for (var index = 0; index < source.length; index += 1) {
            var alias = projectAliasText(source[index])
            if (alias.length > 0) {
                result.push(alias)
            }
        }
        return result
    }

    function copyProjectDraft(source) {
        return {
            id: source.id || "",
            projectName: source.projectName || "",
            customerName: source.customerName || "",
            taskOrderNo: source.taskOrderNo || "",
            followUpStartedAt: source.followUpStartedAt || "",
            supportEndedAt: source.supportEndedAt || "",
            productLine: source.productLine || "",
            productVersion: source.productVersion || "",
            projectManager: source.projectManager || "",
            projectLevel: source.projectLevel || "normal",
            aliases: normalizedProjectAliases(source.aliases)
        }
    }

    function showProjectList() {
        projectViewMode = "list"
        projectAliasInput = ""
    }

    function startNewProjectDraft() {
        projectDraft = emptyProjectDraft()
        projectAliasInput = ""
        projectViewMode = "detail"
    }

    function loadProjectDraft(projectItem) {
        projectDraft = copyProjectDraft(projectItem || emptyProjectDraft())
        projectAliasInput = ""
        projectViewMode = "detail"
    }

    function updateProjectDraft(fieldName, value) {
        var next = copyProjectDraft(projectDraft)
        next[fieldName] = value || ""
        projectDraft = next
    }

    function findProjectPayload(projectId, taskOrderNo) {
        var normalizedId = (projectId || "").toString().trim()
        var normalizedTaskOrderNo = (taskOrderNo || "").toString().trim()
        for (var index = 0; index < controlPanelBridge.projects.length; index += 1) {
            var item = controlPanelBridge.projects[index]
            if (normalizedId.length && item.id === normalizedId) {
                return item
            }
            if (normalizedTaskOrderNo.length && item.taskOrderNo === normalizedTaskOrderNo) {
                return item
            }
        }
        return null
    }

    function normalizedProjectLevel(value) {
        var text = (value || "").toString().toLowerCase()
        if (text === "important" || value === "重要") {
            return "important"
        }
        return "normal"
    }

    function displayProjectDate(value) {
        var text = (value || "").toString()
        if (!text.length) {
            return ""
        }
        if (text.indexOf("T") >= 0) {
            text = text.split("T")[0]
        } else if (text.indexOf(" ") >= 0) {
            text = text.split(" ")[0]
        }
        return text.replace(/-/g, "/")
    }

    function addProjectAlias() {
        var alias = (projectAliasInput || "").trim()
        if (!alias.length) {
            return
        }
        var next = copyProjectDraft(projectDraft)
        for (var index = 0; index < next.aliases.length; index += 1) {
            if (projectAliasText(next.aliases[index]).toLowerCase() === alias.toLowerCase()) {
                projectAliasInput = ""
                return
            }
        }
        next.aliases.push(alias)
        projectDraft = next
        projectAliasInput = ""
    }

    function removeProjectAlias(alias) {
        var next = copyProjectDraft(projectDraft)
        var updatedAliases = []
        var targetAlias = projectAliasText(alias)
        for (var index = 0; index < next.aliases.length; index += 1) {
            if (projectAliasText(next.aliases[index]) !== targetAlias) {
                updatedAliases.push(next.aliases[index])
            }
        }
        next.aliases = updatedAliases
        projectDraft = next
    }

    function saveCurrentProject() {
        var payload = copyProjectDraft(projectDraft)
        controlPanelBridge.saveProject(payload)
        if (controlPanelBridge.hasError) {
            return
        }
        var refreshed = findProjectPayload(payload.id, payload.taskOrderNo)
        if (refreshed) {
            projectDraft = copyProjectDraft(refreshed)
        }
        projectAliasInput = ""
        projectViewMode = "detail"
    }

    function deleteCurrentProject() {
        if (!projectDraft.id.length) {
            showProjectList()
            return
        }
        controlPanelBridge.deleteProject(projectDraft.id)
        projectDraft = emptyProjectDraft()
        projectAliasInput = ""
        projectViewMode = "list"
    }

    Connections {
        target: controlPanelBridge
        function onProjectDateSelected(fieldName, value) {
            root.updateProjectDraft(fieldName, value)
        }
        function onDataChanged() {
            root.ensureSelectedProvider()
        }
        function onCurrentSectionChanged() {
            root.ensureSelectedProvider()
        }
    }

    Component.onCompleted: ensureSelectedProvider()

    component PlainButton: ControlPanelPlainButton {
        theme: root
    }

    component StatusToggle: Item {
        id: toggleRoot
        property bool checked: false
        signal toggled(bool checked)

        implicitWidth: toggleRow.implicitWidth
        implicitHeight: toggleRow.implicitHeight

        Row {
            id: toggleRow
            anchors.fill: parent
            spacing: 8

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: toggleRoot.checked ? "启用" : "停用"
                color: toggleRoot.checked ? root.successInk : root.labelInk
                font.family: root.uiFont
                font.pixelSize: 12
                font.weight: 700
            }

            Rectangle {
                anchors.verticalCenter: parent.verticalCenter
                width: 48
                height: 26
                radius: 13
                color: toggleRoot.checked ? root.accent : "#D1D5DB"

                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    x: toggleRoot.checked ? parent.width - width - 2 : 2
                    y: 2
                    color: "#FFFFFF"
                    border.width: 1
                    border.color: toggleRoot.checked ? "#D5DBE5" : "#D1D5DB"
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: toggleRoot.toggled(!toggleRoot.checked)
        }
    }

    component WindowButton: Rectangle {
        id: windowButton
        property string label: ""
        property color hoverColor: root.hoverBg
        property color pressedColor: root.pressedBg
        property color inkColor: root.bodyInk
        property int fontPixelSize: 15
        signal clicked

        implicitWidth: 30
        implicitHeight: 30
        radius: 15
        color: buttonArea.pressed ? windowButton.pressedColor : buttonArea.containsMouse ? windowButton.hoverColor : "transparent"

        Text {
            anchors.centerIn: parent
            text: windowButton.label
            color: windowButton.inkColor
            font.family: root.uiFont
            font.pixelSize: windowButton.fontPixelSize
            font.weight: 600
        }

        MouseArea {
            id: buttonArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: windowButton.clicked()
        }
    }

    component SettingsInput: ControlPanelSettingsInput {
        theme: root
    }

    component SettingsCombo: ControlPanelSettingsCombo {
        theme: root
    }

    component PixelInput: ControlPanelPixelInput {
        theme: root
    }

    component MultiLineInput: ControlPanelSettingsArea {
        theme: root
    }

    component StyleTokenRow: Rectangle {
        id: styleRow
        property string title: ""
        property string tokenPath: ""
        property string valueText: ""
        property int minimumValue: 0
        property int maximumValue: 999
        signal valueEdited(int value)

        Layout.fillWidth: true
        implicitHeight: 54
        color: "transparent"

        Column {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Text {
                text: styleRow.title
                color: root.titleInk
                font.family: root.uiFont
                font.pixelSize: root.fontBodyLg
                font.weight: 700
            }

            Text {
                text: styleRow.tokenPath
                color: root.bodyInk
                font.family: root.uiFont
                font.pixelSize: root.fontCaption
            }
        }

        PixelInput {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            minimumValue: styleRow.minimumValue
            maximumValue: styleRow.maximumValue
            text: styleRow.valueText
            onValueEdited: function(value) {
                styleRow.valueEdited(value)
            }
        }
    }

    component SearchableModelCombo: Item {
        id: comboRoot
        property var model: []
        property string value: ""
        property string placeholderText: ""
        signal valueCommitted(string value, string capabilities)

        implicitWidth: 200
        implicitHeight: 32

        function filteredOptions() {
            var keyword = input.text || ""
            if (!keyword.trim().length) {
                return comboRoot.model
            }
            var matches = []
            for (var index = 0; index < comboRoot.model.length; index += 1) {
                var option = comboRoot.model[index]
                if (root.fuzzyMatch(option.text, keyword) || root.fuzzyMatch(option.value, keyword)) {
                    matches.push(option)
                } else if (root.fuzzyMatch(option.details || "", keyword)) {
                    matches.push(option)
                }
            }
            return matches
        }

        function hasMatches() {
            return comboRoot.filteredOptions().length > 0
        }

        function hasExactMatch() {
            var keyword = (input.text || "").trim().toLowerCase()
            if (!keyword.length) {
                return true
            }
            for (var index = 0; index < comboRoot.model.length; index += 1) {
                var option = comboRoot.model[index]
                if ((option.value || "").toLowerCase() === keyword || (option.text || "").toLowerCase() === keyword) {
                    return true
                }
            }
            return false
        }

        function syncInputText() {
            if (input.activeFocus) {
                return
            }
            input.text = root.optionText(comboRoot.model, comboRoot.value)
        }

        function commitValue(nextValue) {
            var normalized = (nextValue || "").trim()
            if (!normalized.length) {
                syncInputText()
                popup.close()
                return
            }
            comboRoot.valueCommitted(normalized, "")
            popup.close()
        }

        function commitCustomValue(capabilities) {
            var normalized = (input.text || "").trim()
            if (!normalized.length) {
                syncInputText()
                popup.close()
                return
            }
            comboRoot.valueCommitted(normalized, capabilities || "")
            popup.close()
        }

        function moveHighlight(step) {
            var options = comboRoot.filteredOptions()
            if (!options.length) {
                optionList.currentIndex = -1
                return
            }
            if (!popup.visible) {
                popup.open()
            }
            if (optionList.currentIndex < 0) {
                optionList.currentIndex = step > 0 ? 0 : options.length - 1
            } else {
                optionList.currentIndex = (optionList.currentIndex + step + options.length) % options.length
            }
            optionList.positionViewAtIndex(optionList.currentIndex, ListView.Contain)
        }

        function commitHighlightedOrInput() {
            var options = comboRoot.filteredOptions()
            if (popup.visible && optionList.currentIndex >= 0 && optionList.currentIndex < options.length) {
                comboRoot.commitValue(options[optionList.currentIndex].value)
                return
            }
            if ((input.text || "").trim().length > 0 && !comboRoot.hasExactMatch()) {
                comboRoot.commitCustomValue("vision_chat,text_chat")
                return
            }
            comboRoot.commitValue(input.text)
        }

        onModelChanged: syncInputText()
        onValueChanged: syncInputText()
        Component.onCompleted: syncInputText()

        Rectangle {
            anchors.fill: parent
            radius: root.formFieldCompactRadius
            color: root.formFieldBg
            border.width: 1
            border.color: input.activeFocus || popup.visible ? root.formFieldFocusBorder : root.formFieldBorder
        }

        TextField {
            id: input
            anchors.fill: parent
            color: root.titleInk
            font.family: root.uiFont
            font.pixelSize: root.formFieldCompactFontSize
            selectByMouse: true
            leftPadding: root.formFieldCompactPaddingH
            rightPadding: 32
            topPadding: 0
            bottomPadding: 0
            placeholderText: comboRoot.placeholderText
            background: Item {}
            onTextEdited: popup.open()
            onActiveFocusChanged: if (activeFocus) popup.open()
            onAccepted: comboRoot.commitHighlightedOrInput()
            onEditingFinished: if (!popup.visible) comboRoot.commitValue(text)
            Keys.onDownPressed: comboRoot.moveHighlight(1)
            Keys.onUpPressed: comboRoot.moveHighlight(-1)
        }

        Canvas {
            x: comboRoot.width - width - 14
            y: (comboRoot.height - height) / 2
            width: 10
            height: 6
            contextType: "2d"
            onPaint: {
                context.reset()
                context.moveTo(0, 0)
                context.lineTo(width, 0)
                context.lineTo(width / 2, height)
                context.closePath()
                context.fillStyle = root.labelInk
                context.fill()
            }
        }

        MouseArea {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 34
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                input.forceActiveFocus()
                if (popup.visible) {
                    popup.close()
                } else {
                    popup.open()
                }
            }
        }

        Popup {
            id: popup
            y: comboRoot.height + 4
            width: comboRoot.width
            padding: 0
            modal: false
            focus: true
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

            background: Rectangle {
                radius: root.formPopupRadius
                color: root.formPopupBg
                border.width: 1
                border.color: root.formFieldBorder
            }

            contentItem: Column {
                width: popup.width - popup.leftPadding - popup.rightPadding
                spacing: 0

                Rectangle {
                    width: parent.width
                    height: addLabel.implicitHeight + 16
                    visible: (input.text || "").trim().length > 0 && !comboRoot.hasExactMatch()
                    color: addMouseArea.pressed ? root.pressedBg : addMouseArea.containsMouse ? root.accentSoft : root.formPopupBg

                    Text {
                        id: addLabel
                        anchors.fill: parent
                        anchors.margins: root.formFieldCompactPaddingH
                        text: "添加并使用: " + (input.text || "").trim()
                        color: root.accent
                        font.family: root.uiFont
                        font.pixelSize: root.formFieldCompactFontSize
                        font.weight: 600
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    MouseArea {
                        id: addMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: comboRoot.commitCustomValue("vision_chat,text_chat")
                    }
                }

                Rectangle {
                    width: parent.width
                    height: textOnlyLabel.implicitHeight + 16
                    visible: (input.text || "").trim().length > 0 && !comboRoot.hasExactMatch()
                    color: textOnlyMouseArea.pressed ? root.pressedBg : textOnlyMouseArea.containsMouse ? root.formPopupHoverBg : root.formPopupBg

                    Text {
                        id: textOnlyLabel
                        anchors.fill: parent
                        anchors.margins: root.formFieldCompactPaddingH
                        text: "添加为仅文本模型"
                        color: root.bodyInk
                        font.family: root.uiFont
                        font.pixelSize: root.formFieldCompactFontSize
                        font.weight: 600
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }

                    MouseArea {
                        id: textOnlyMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: comboRoot.commitCustomValue("text_chat")
                    }
                }

                ListView {
                    id: optionList
                    width: parent.width
                    implicitHeight: Math.min(contentHeight, 240)
                    clip: true
                    model: comboRoot.filteredOptions()

                    delegate: Rectangle {
                        width: optionList.width
                        height: optionText.implicitHeight + 16
                        color: optionMouseArea.pressed ? root.pressedBg : optionMouseArea.containsMouse ? root.formPopupHoverBg : "transparent"

                        Text {
                            id: optionText
                            anchors.fill: parent
                            anchors.margins: root.formFieldCompactPaddingH
                            text: modelData.text
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: root.formFieldCompactFontSize
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        MouseArea {
                            id: optionMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: comboRoot.commitValue(modelData.value)
                        }
                    }
                }
            }
        }
    }

    component ModelFieldInput: ControlPanelSettingsInput {
        theme: root
        implicitHeight: 32
        fieldRadius: root.formFieldCompactRadius
        fieldFontSize: root.formFieldCompactFontSize
        leftPadding: root.formFieldCompactPaddingH
        rightPadding: root.formFieldCompactPaddingH
        topPadding: 0
        bottomPadding: 0
    }

    component ModelFieldCombo: ControlPanelSettingsCombo {
        theme: root
        implicitHeight: 32
        fieldRadius: root.formFieldCompactRadius
        fieldFontSize: root.formFieldCompactFontSize
        leftPadding: root.formFieldCompactPaddingH
        rightPadding: 30
        topPadding: 0
        bottomPadding: 0
        popupMaxHeight: 220
    }

    component SectionCard: Rectangle {
        radius: 12
        color: root.panelAltBg
        border.width: 0
    }

    Rectangle {
        id: shell
        anchors.fill: parent
        radius: controlPanelBridge.windowMaximized ? 0 : 30
        color: root.shellBg
        clip: true

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                radius: 20
                color: root.panelAltBg

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onPressed: controlPanelBridge.startWindowDrag()
                    onDoubleClicked: controlPanelBridge.toggleMaximizedPanel()
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 10
                    spacing: 10

                    Image {
                        Layout.preferredWidth: 18
                        Layout.preferredHeight: 18
                        source: controlPanelBridge.logoSource
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        mipmap: true
                    }

                    Text {
                        text: "Chattodo Hub"
                        color: root.bodyInk
                        font.family: root.uiFont
                        font.pixelSize: 13
                        font.weight: 600
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    WindowButton {
                        label: "−"
                        onClicked: controlPanelBridge.minimizePanel()
                    }

                    WindowButton {
                        label: controlPanelBridge.windowMaximized ? "❐" : "□"
                        fontPixelSize: 13
                        onClicked: controlPanelBridge.toggleMaximizedPanel()
                    }

                    WindowButton {
                        label: "×"
                        hoverColor: "#F4D9D5"
                        pressedColor: "#EDC3BC"
                        inkColor: "#8B3A2C"
                        onClicked: controlPanelBridge.closePanel()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                SectionCard {
                    Layout.preferredWidth: 220
                    Layout.fillHeight: true
                    color: root.panelAltBg
                    radius: 12

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 12

                        Text {
                            visible: false
                            Layout.preferredHeight: 0
                            text: "Chattodo Hub"
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 20
                            font.weight: 700
                        }

                        Text {
                            visible: false
                            Layout.preferredHeight: 0
                            Layout.fillWidth: true
                            text: "统一管理模型、截图热键与本地数据入口。"
                            color: root.bodyInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        Repeater {
                            model: controlPanelBridge.sectionGroups

                            delegate: ColumnLayout {
                                Layout.fillWidth: true
                                Layout.topMargin: index === 0 ? 0 : 6
                                spacing: 8

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Text {
                                        text: modelData.title
                                        color: root.bodyInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        font.weight: 800
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: 1
                                        radius: 1
                                        color: root.panelLine
                                        opacity: 0.9
                                    }
                                }

                                Repeater {
                                    model: modelData.items

                                    delegate: Rectangle {
                                        readonly property bool selected: root.currentSection === modelData.id

                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 40
                                        radius: 6
                                        color: selected || navItemMouse.containsMouse ? root.accentSoft : "transparent"

                                        Text {
                                            anchors.left: parent.left
                                            anchors.leftMargin: 14
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: modelData.title
                                            color: selected || navItemMouse.containsMouse ? root.accent : root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: selected ? 600 : 400
                                        }

                                        MouseArea {
                                            id: navItemMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: if (controlPanelBridge) controlPanelBridge.setCurrentSection(modelData.id)
                                        }
                                    }
                                }
                            }
                        }

                        SectionCard {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            color: root.navIdle

                            Text {
                                anchors.fill: parent
                                anchors.margins: 16
                                text: "提示: 如果功能提示配置缺失，请从托盘图标进入这里完成设置。"
                                color: root.bodyInk
                                font.family: root.uiFont
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }

                SectionCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: root.panelBg
                    radius: 12

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 14

                        RowLayout {
                            Layout.fillWidth: true

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Text {
                                    text: root.currentSectionMeta.title || ""
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 20
                                    font.weight: 700
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.currentSectionMeta.description || ""
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }
                            }

                            PlainButton {
                                label: root.currentSectionMeta.primaryActionLabel || ""
                                primary: true
                                strokeWidth: 0
                                border.color: root.accent
                                onClicked: {
                                    if (!controlPanelBridge) {
                                        return
                                    }
                                    if (root.currentSection === "tickets") {
                                        controlPanelBridge.refreshTickets()
                                    } else {
                                        controlPanelBridge.saveCurrentSection()
                                    }
                                }
                            }
                        }

                        ScrollView {
                            id: scrollArea
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true

                            ColumnLayout {
                                id: contentColumn
                                width: scrollArea.availableWidth
                                spacing: 18

                                ColumnLayout {
                                    visible: root.currentSection === "models"
                                    Layout.fillWidth: true
                                    spacing: 14

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 16

                                        Text {
                                            text: "模型供应商"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 18
                                            font.weight: 600
                                        }

                                        Item {
                                            Layout.fillWidth: true
                                        }

                                        Rectangle {
                                            id: providerSegmentedControl
                                            Layout.preferredWidth: Math.min(600, Math.max(360, segmentCount * 145))
                                            Layout.preferredHeight: 44
                                            radius: root.radiusLg
                                            color: root.hoverBg
                                            clip: true

                                            readonly property var providerItems: controlPanelBridge ? (controlPanelBridge.providers || []) : []
                                            readonly property int selectedIndex: root.itemIndexById(providerItems, root.selectedProviderId)
                                            readonly property int segmentCount: Math.max(1, providerItems.length)

                                            Rectangle {
                                                x: Math.max(0, parent.selectedIndex) * parent.width / parent.segmentCount + 3
                                                y: 3
                                                width: parent.width / parent.segmentCount - 6
                                                height: parent.height - 6
                                                radius: root.radiusMd
                                                color: root.panelBg
                                                border.width: 1
                                                border.color: root.accentTint
                                            }

                                            Repeater {
                                                model: providerSegmentedControl.providerItems

                                                delegate: Item {
                                                    x: index * parent.width / parent.segmentCount
                                                    width: parent.width / parent.segmentCount
                                                    height: parent.height
                                                    readonly property bool selected: root.selectedProviderId === modelData.id

                                                    Text {
                                                        anchors.centerIn: parent
                                                        width: parent.width - 18
                                                        text: modelData.name
                                                        color: selected ? root.titleInk : root.labelInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: root.fontBodyLg
                                                        font.weight: 700
                                                        horizontalAlignment: Text.AlignHCenter
                                                        verticalAlignment: Text.AlignVCenter
                                                        elide: Text.ElideRight
                                                    }

                                                    MouseArea {
                                                        anchors.fill: parent
                                                        cursorShape: Qt.PointingHandCursor
                                                        onClicked: root.selectedProviderId = modelData.id
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: providerForm.implicitHeight + 40
                                        radius: 14
                                        color: root.panelAltBg
                                        border.width: 1
                                        border.color: root.panelLine

                                        ColumnLayout {
                                            id: providerForm
                                            anchors.fill: parent
                                            anchors.margins: 20
                                            spacing: 12

                                            Text {
                                                text: "API Key"
                                                color: "#6B7280"
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                            }

                                            ModelFieldInput {
                                                Layout.fillWidth: true
                                                echoMode: TextInput.Password
                                                text: root.selectedProviderPayload() ? root.selectedProviderPayload().apiKey : ""
                                                placeholderText: root.selectedProviderPayload() ? ("输入 " + root.selectedProviderPayload().name + " 的 API Key") : ""
                                                onTextEdited: if (root.selectedProviderPayload()) controlPanelBridge.updateProviderField(root.selectedProviderPayload().id, "api_key", text)
                                            }

                                            Text {
                                                text: "Base URL"
                                                color: "#6B7280"
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                            }

                                            ModelFieldInput {
                                                Layout.fillWidth: true
                                                enabled: root.selectedProviderPayload() ? root.selectedProviderPayload().baseUrlEnabled : false
                                                text: root.selectedProviderPayload() ? root.selectedProviderPayload().baseUrl : ""
                                                placeholderText: root.selectedProviderPayload() && root.selectedProviderPayload().baseUrlEnabled ? "https://..." : "该供应商无需设置"
                                                onTextEdited: if (root.selectedProviderPayload()) controlPanelBridge.updateProviderField(root.selectedProviderPayload().id, "base_url", text)
                                            }

                                            Text {
                                                text: "超时时间（秒）"
                                                color: "#6B7280"
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                            }

                                            ModelFieldInput {
                                                Layout.fillWidth: true
                                                inputMethodHints: Qt.ImhDigitsOnly
                                                text: root.selectedProviderPayload() ? root.selectedProviderPayload().timeoutSeconds : ""
                                                onTextEdited: if (root.selectedProviderPayload()) controlPanelBridge.updateProviderField(root.selectedProviderPayload().id, "timeout_seconds", text)
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 16

                                        Text {
                                            text: "任务模型绑定"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 18
                                            font.weight: 600
                                        }

                                        Item {
                                            Layout.fillWidth: true
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: taskBindingColumn.implicitHeight + 40
                                        radius: 14
                                        color: root.panelAltBg
                                        border.width: 1
                                        border.color: root.panelLine

                                        ColumnLayout {
                                            id: taskBindingColumn
                                            anchors.fill: parent
                                            anchors.margins: 20
                                            spacing: 8

                                            Repeater {
                                                model: controlPanelBridge.taskBindings

                                                delegate: Rectangle {
                                                    Layout.fillWidth: true
                                                    implicitHeight: bindingMeta.visible ? bindingMeta.implicitHeight + 50 : 52
                                                    radius: 8
                                                    color: bindingMouse.containsMouse ? root.hoverBg : "transparent"

                                                    ColumnLayout {
                                                        anchors.fill: parent
                                                        anchors.leftMargin: 4
                                                        anchors.rightMargin: 4
                                                        anchors.topMargin: 10
                                                        anchors.bottomMargin: 10
                                                        spacing: 6

                                                        RowLayout {
                                                            Layout.fillWidth: true
                                                            spacing: 12

                                                            Text {
                                                                Layout.preferredWidth: 160
                                                                text: modelData.label
                                                                color: root.titleInk
                                                                font.family: root.uiFont
                                                                font.pixelSize: 14
                                                                font.weight: 500
                                                                verticalAlignment: Text.AlignVCenter
                                                            }

                                                            ModelFieldCombo {
                                                                id: providerCombo
                                                                Layout.preferredWidth: 150
                                                                model: modelData.providerOptions
                                                                currentIndex: root.optionIndex(modelData.providerOptions, modelData.providerId)
                                                                onActivated: if (currentIndex >= 0) controlPanelBridge.updateTaskBindingProvider(modelData.id, providerCombo.model[currentIndex].value)
                                                            }

                                                            SearchableModelCombo {
                                                                Layout.fillWidth: true
                                                                model: modelData.modelOptions
                                                                value: modelData.modelId
                                                                placeholderText: "选择或输入模型"
                                                                onValueCommitted: (value, capabilities) => controlPanelBridge.addOrSelectTaskBindingModel(modelData.id, value, capabilities)
                                                            }
                                                        }

                                                        Text {
                                                            id: bindingMeta
                                                            Layout.fillWidth: true
                                                            Layout.leftMargin: 172
                                                            visible: modelData.performanceSummary.length > 0 || modelData.speedHint.length > 0
                                                            text: modelData.speedHint.length > 0 ? (modelData.performanceSummary + " · " + modelData.speedHint) : modelData.performanceSummary
                                                            color: "#6B7280"
                                                            font.family: root.uiFont
                                                            font.pixelSize: 11
                                                            wrapMode: Text.Wrap
                                                        }
                                                    }

                                                    MouseArea {
                                                        id: bindingMouse
                                                        anchors.fill: parent
                                                        hoverEnabled: true
                                                        acceptedButtons: Qt.NoButton
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "theme"
                                    Layout.fillWidth: true
                                    implicitHeight: themeSettingsContent.implicitHeight + 32

                                    ColumnLayout {
                                        id: themeSettingsContent
                                        anchors.fill: parent
                                        anchors.margins: 22
                                        spacing: 0

                                        RowLayout {
                                            Layout.fillWidth: true
                                            Layout.bottomMargin: 18
                                            spacing: 12

                                            Text {
                                                text: "主题设置"
                                                color: root.titleInk
                                                font.family: root.uiFont
                                                font.pixelSize: root.fontSection
                                                font.weight: 800
                                            }

                                            Item { Layout.fillWidth: true }

                                            PlainButton {
                                                label: "恢复默认"
                                                fillColor: root.panelBg
                                                inkColor: root.bodyInk
                                                strokeWidth: 1
                                                onClicked: controlPanelBridge.resetThemeDefaults()
                                            }
                                        }

                                        Rectangle {
                                            Layout.fillWidth: true
                                            implicitHeight: 64
                                            color: "transparent"

                                            Text {
                                                anchors.left: parent.left
                                                anchors.verticalCenter: parent.verticalCenter
                                                text: "主题配色"
                                                color: root.labelInk
                                                font.family: root.uiFont
                                                font.pixelSize: root.fontBodyLg
                                                font.weight: 700
                                            }

                                            Rectangle {
                                                anchors.right: parent.right
                                                anchors.verticalCenter: parent.verticalCenter
                                                width: 430
                                                height: 44
                                                radius: root.radiusLg
                                                color: root.hoverBg
                                                clip: true

                                                readonly property int selectedIndex: root.optionIndex(controlPanelBridge.themePresetOptions, controlPanelBridge.themeConfig.preset_id)
                                                readonly property int segmentCount: Math.max(1, controlPanelBridge.themePresetOptions.length)

                                                Rectangle {
                                                    x: Math.max(0, parent.selectedIndex) * parent.width / parent.segmentCount + 3
                                                    y: 3
                                                    width: parent.width / parent.segmentCount - 6
                                                    height: parent.height - 6
                                                    radius: root.radiusMd
                                                    color: root.panelBg
                                                    border.width: 1
                                                    border.color: root.accentTint
                                                }

                                                Repeater {
                                                    model: controlPanelBridge.themePresetOptions

                                                    delegate: Item {
                                                        x: index * parent.width / parent.segmentCount
                                                        width: parent.width / parent.segmentCount
                                                        height: parent.height
                                                        readonly property bool selected: controlPanelBridge.themeConfig.preset_id === modelData.id

                                                        Row {
                                                            anchors.centerIn: parent
                                                            spacing: 8

                                                            Rectangle {
                                                                anchors.verticalCenter: parent.verticalCenter
                                                                width: 14
                                                                height: 14
                                                                radius: 7
                                                                color: modelData.accentColor
                                                                border.width: 1
                                                                border.color: selected ? root.accentTint : root.panelLine
                                                            }

                                                            Text {
                                                                anchors.verticalCenter: parent.verticalCenter
                                                                text: modelData.label
                                                                color: selected ? root.titleInk : root.labelInk
                                                                font.family: root.uiFont
                                                                font.pixelSize: root.fontBodyLg
                                                                font.weight: 700
                                                            }
                                                        }

                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: controlPanelBridge.selectThemePreset(modelData.id)
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "theme"
                                    Layout.fillWidth: true
                                    implicitHeight: themeParametersContent.implicitHeight + 32

                                    ColumnLayout {
                                        id: themeParametersContent
                                        anchors.fill: parent
                                        anchors.margins: 22
                                        spacing: 0

                                        Text {
                                            Layout.fillWidth: true
                                            Layout.bottomMargin: 10
                                            text: "样式参数"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: root.fontSection
                                            font.weight: 800
                                        }

                                        GridLayout {
                                            Layout.fillWidth: true
                                            columns: 2
                                            rowSpacing: 14
                                            columnSpacing: 22

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 8
                                                Text {
                                                    text: "强调色"
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: root.fontCaption
                                                    font.weight: 700
                                                }
                                                SettingsInput {
                                                    Layout.fillWidth: true
                                                    text: controlPanelBridge.themeConfig.accent_color
                                                    placeholderText: "#2A313F"
                                                    onTextEdited: controlPanelBridge.updateThemeField("accent_color", text)
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 8
                                                Text {
                                                    text: "字体"
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: root.fontCaption
                                                    font.weight: 700
                                                }
                                                SettingsCombo {
                                                    Layout.fillWidth: true
                                                    model: controlPanelBridge.themeFontOptions
                                                    currentIndex: root.optionIndex(controlPanelBridge.themeFontOptions, controlPanelBridge.themeConfig.font_family)
                                                    onActivated: if (currentIndex >= 0) controlPanelBridge.updateThemeField("font_family", model[currentIndex].value)
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 8
                                                Text {
                                                    text: "组件风格"
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: root.fontCaption
                                                    font.weight: 700
                                                }
                                                SettingsCombo {
                                                    Layout.fillWidth: true
                                                    model: controlPanelBridge.themeComponentStyleOptions
                                                    currentIndex: root.optionIndex(controlPanelBridge.themeComponentStyleOptions, controlPanelBridge.themeConfig.component_style)
                                                    onActivated: if (currentIndex >= 0) controlPanelBridge.updateThemeField("component_style", model[currentIndex].value)
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 8
                                                Text {
                                                    text: "界面密度"
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: root.fontCaption
                                                    font.weight: 700
                                                }
                                                SettingsCombo {
                                                    Layout.fillWidth: true
                                                    model: controlPanelBridge.themeDensityOptions
                                                    currentIndex: root.optionIndex(controlPanelBridge.themeDensityOptions, controlPanelBridge.themeConfig.density)
                                                    onActivated: if (currentIndex >= 0) controlPanelBridge.updateThemeField("density", model[currentIndex].value)
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 8
                                                Text {
                                                    text: "圆角比例"
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: root.fontCaption
                                                    font.weight: 700
                                                }
                                                SettingsCombo {
                                                    Layout.fillWidth: true
                                                    model: [
                                                        { value: "0.75", text: "紧凑 75%" },
                                                        { value: "1.0", text: "标准 100%" },
                                                        { value: "1.2", text: "柔和 120%" },
                                                        { value: "1.4", text: "圆润 140%" }
                                                    ]
                                                    currentIndex: {
                                                        var value = Number(controlPanelBridge.themeConfig.radius_scale)
                                                        if (value <= 0.8) return 0
                                                        if (value >= 1.35) return 3
                                                        if (value >= 1.1) return 2
                                                        return 1
                                                    }
                                                    onActivated: if (currentIndex >= 0) controlPanelBridge.updateThemeNumberField("radius_scale", Number(model[currentIndex].value))
                                                }
                                            }

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 8
                                                Text {
                                                    text: "基础字号"
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: root.fontCaption
                                                    font.weight: 700
                                                }
                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    PixelInput {
                                                        id: themeFontSizeInput
                                                        maximumValue: 18
                                                        minimumValue: 11
                                                        text: String(controlPanelBridge.themeConfig.font_size_px || 12)
                                                        onValueEdited: function(value) {
                                                            controlPanelBridge.updateThemeNumberField("font_size_px", value)
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "theme"
                                    Layout.fillWidth: true
                                    implicitHeight: commonStyleContent.implicitHeight + 32

                                    ColumnLayout {
                                        id: commonStyleContent
                                        anchors.fill: parent
                                        anchors.margins: 22
                                        spacing: 0

                                        Text {
                                            Layout.fillWidth: true
                                            Layout.bottomMargin: 10
                                            text: "通用组件样式"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: root.fontSection
                                            font.weight: 800
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 0

                                            StyleTokenRow {
                                                title: "圆角"
                                                tokenPath: "component.Common.radius"
                                                minimumValue: 4
                                                maximumValue: 32
                                                valueText: String(controlPanelBridge.themeConfig.component_radius || 8)
                                                onValueEdited: function(value) {
                                                    controlPanelBridge.updateThemeNumberField("component_radius", value)
                                                }
                                            }

                                            Rectangle {
                                                Layout.fillWidth: true
                                                implicitHeight: 1
                                                color: root.panelLine
                                            }

                                            StyleTokenRow {
                                                title: "高度"
                                                tokenPath: "component.Common.height"
                                                minimumValue: 28
                                                maximumValue: 56
                                                valueText: String(controlPanelBridge.themeConfig.component_height || 36)
                                                onValueEdited: function(value) {
                                                    controlPanelBridge.updateThemeNumberField("component_height", value)
                                                }
                                            }
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "theme"
                                    Layout.fillWidth: true
                                    implicitHeight: buttonStyleContent.implicitHeight + 32

                                    ColumnLayout {
                                        id: buttonStyleContent
                                        anchors.fill: parent
                                        anchors.margins: 22
                                        spacing: 0

                                        Text {
                                            Layout.fillWidth: true
                                            Layout.bottomMargin: 10
                                            text: "按钮样式"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: root.fontSection
                                            font.weight: 800
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 0

                                            StyleTokenRow {
                                                title: "圆角"
                                                tokenPath: "component.Button.radius"
                                                minimumValue: 4
                                                maximumValue: 32
                                                valueText: String(controlPanelBridge.themeConfig.button_radius || 6)
                                                onValueEdited: function(value) {
                                                    controlPanelBridge.updateThemeNumberField("button_radius", value)
                                                }
                                            }

                                            Rectangle {
                                                Layout.fillWidth: true
                                                implicitHeight: 1
                                                color: root.panelLine
                                            }

                                            StyleTokenRow {
                                                title: "高度"
                                                tokenPath: "component.Button.height"
                                                minimumValue: 28
                                                maximumValue: 56
                                                valueText: String(controlPanelBridge.themeConfig.button_height || 35)
                                                onValueEdited: function(value) {
                                                    controlPanelBridge.updateThemeNumberField("button_height", value)
                                                }
                                            }
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "hotkeys"
                                    Layout.fillWidth: true
                                    implicitHeight: hotkeyContent.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: hotkeyContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 12

                                        Text {
                                            text: "全局截图热键"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 15
                                            font.weight: 700
                                        }

                                        Text {
                                            text: controlPanelBridge.hotkeyHelpText
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                            Layout.fillWidth: true
                                        }

                                        SettingsInput {
                                            id: captureHotkeyInput
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.captureHotkey
                                            placeholderText: activeFocus ? "点击后直接按下快捷键组合" : controlPanelBridge.hotkeyPlaceholder
                                            readOnly: true
                                            selectByMouse: false
                                            Keys.onPressed: function(event) {
                                                if (event.key === Qt.Key_Escape) {
                                                    captureHotkeyInput.focus = false
                                                    event.accepted = true
                                                    return
                                                }
                                                if (event.key === Qt.Key_Backspace || event.key === Qt.Key_Delete) {
                                                    controlPanelBridge.updateCaptureHotkey("")
                                                    event.accepted = true
                                                    return
                                                }
                                                if (controlPanelBridge.captureHotkeyFromKeyEvent(event.key, event.modifiers, event.text)) {
                                                    captureHotkeyInput.focus = false
                                                }
                                                event.accepted = true
                                            }
                                        }

                                        Text {
                                            text: "点击输入框后直接按下快捷键组合；按 Esc 取消本次录入。"
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                            Layout.fillWidth: true
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "hotkeys"
                                    Layout.fillWidth: true
                                    implicitHeight: imageContent.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: imageContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 12

                                        Text {
                                            text: "图片压缩阈值"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 15
                                            font.weight: 700
                                        }

                                        Text {
                                            text: "超过该大小的截图会在发送前进行压缩。"
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                            Layout.fillWidth: true
                                        }

                                        SettingsInput {
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.maxImageMegabytes
                                            placeholderText: "4"
                                            onTextEdited: controlPanelBridge.updateMaxImageMegabytes(text)
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "analysis_rules"
                                    Layout.fillWidth: true
                                    implicitHeight: analysisRulesContent.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: analysisRulesContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 12

                                        Text {
                                            text: "用户规则"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 15
                                            font.weight: 700
                                        }

                                        SettingsCombo {
                                            Layout.fillWidth: true
                                            model: controlPanelBridge.analysisRuleScenes
                                            currentIndex: root.optionIndex(controlPanelBridge.analysisRuleScenes, controlPanelBridge.selectedAnalysisRuleScene)
                                            onActivated: if (currentIndex >= 0) controlPanelBridge.setSelectedAnalysisRuleScene(controlPanelBridge.analysisRuleScenes[currentIndex].value)
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "当前场景：" + controlPanelBridge.analysisRuleForm.sceneLabel + "。这些规则会按顺序替换到分析提示词中的 {{RULE}}，用于约束和引导模型输出。"
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 10

                                            Repeater {
                                                model: controlPanelBridge.analysisRuleForm.userRules

                                                delegate: RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 10

                                                    Text {
                                                        text: "规则 " + (index + 1)
                                                        color: root.labelInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: 11
                                                        font.weight: 600
                                                    }

                                                    SettingsInput {
                                                        Layout.fillWidth: true
                                                        text: modelData
                                                        placeholderText: "例如：优先提取客户诉求、当前结论和下一步动作"
                                                        onTextEdited: controlPanelBridge.updateAnalysisUserRule(index, text)
                                                    }

                                                    PlainButton {
                                                        label: "删除"
                                                        visible: controlPanelBridge.analysisRuleForm.userRules.length > 1 || (modelData || "").length > 0
                                                        onClicked: controlPanelBridge.removeAnalysisUserRule(index)
                                                    }
                                                }
                                            }
                                        }

                                        PlainButton {
                                            label: "新增规则"
                                            onClicked: controlPanelBridge.addAnalysisUserRule()
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "当前规则版本: " + controlPanelBridge.analysisRuleForm.promptVersion
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.WrapAnywhere
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "analysis_rules"
                                    Layout.fillWidth: true
                                    implicitHeight: promptDebugContent.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: promptDebugContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 12

                                        Text {
                                            text: "Prompt 调试"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 15
                                            font.weight: 700
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 10

                                            ControlPanelSettingsCheckBox {
                                                theme: root
                                                checked: controlPanelBridge.analysisRuleForm.debugEnabled
                                                text: "开启每次分析的 Prompt 快照记录"
                                                onToggled: controlPanelBridge.updateAnalysisDebugEnabled(checked)
                                            }

                                            SettingsInput {
                                                Layout.preferredWidth: 120
                                                text: controlPanelBridge.analysisRuleForm.debugMaxRecords
                                                placeholderText: "100"
                                                onTextEdited: controlPanelBridge.updateAnalysisDebugMaxRecords(text)
                                            }

                                            PlainButton {
                                                label: "刷新记录"
                                                onClicked: controlPanelBridge.refreshPromptDebugRecords()
                                            }
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "analysis_rules.json: " + controlPanelBridge.analysisRulesPath
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "prompt_debug/: " + controlPanelBridge.promptDebugDirPath
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Repeater {
                                            model: controlPanelBridge.promptDebugRecords

                                            delegate: Rectangle {
                                                Layout.fillWidth: true
                                                implicitHeight: debugItemColumn.implicitHeight + 18
                                                radius: 16
                                                color: controlPanelBridge.selectedPromptDebugRecord.trace_id === modelData.traceId ? root.accentSoft : root.panelBg
                                                border.width: 1
                                                border.color: controlPanelBridge.selectedPromptDebugRecord.trace_id === modelData.traceId ? root.accent : root.panelLine

                                                Column {
                                                    id: debugItemColumn
                                                    anchors.fill: parent
                                                    anchors.margins: 10
                                                    spacing: 4

                                                    Text {
                                                        text: modelData.sceneLabel + " · " + modelData.status
                                                        color: root.titleInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: 12
                                                        font.weight: 700
                                                    }

                                                    Text {
                                                        text: modelData.timestamp + " · " + modelData.model
                                                        color: root.bodyInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: 11
                                                        wrapMode: Text.Wrap
                                                    }

                                                    Text {
                                                        text: (modelData.timingSummary || "") + " · " + modelData.imageCount + " 张图"
                                                        color: root.labelInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: 11
                                                        wrapMode: Text.Wrap
                                                    }
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: controlPanelBridge.selectPromptDebugRecord(modelData.traceId)
                                                }
                                            }
                                        }

                                        Text {
                                            visible: controlPanelBridge.promptDebugRecords.length === 0
                                            Layout.fillWidth: true
                                            text: "还没有调试记录。开启调试后，新的截图分析会落盘保存完整 Prompt 快照。"
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }

                                        Text {
                                            visible: controlPanelBridge.selectedPromptDebugRecord.trace_id.length > 0
                                            text: "当前记录详情"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: 700
                                        }

                                        RowLayout {
                                            visible: controlPanelBridge.selectedPromptDebugRecord.trace_id.length > 0
                                            Layout.fillWidth: true
                                            spacing: 10

                                            PlainButton {
                                                label: "复制 System"
                                                onClicked: controlPanelBridge.copyPromptDebugField("system_prompt")
                                            }

                                            PlainButton {
                                                label: "复制 User"
                                                onClicked: controlPanelBridge.copyPromptDebugField("user_prompt")
                                            }

                                            PlainButton {
                                                label: "复制原始返回"
                                                onClicked: controlPanelBridge.copyPromptDebugField("raw_response")
                                            }
                                        }

                                        MultiLineInput {
                                            visible: controlPanelBridge.selectedPromptDebugRecord.trace_id.length > 0
                                            Layout.fillWidth: true
                                            implicitHeight: 120
                                            readOnly: true
                                            text: controlPanelBridge.selectedPromptDebugRecord.system_prompt
                                        }

                                        MultiLineInput {
                                            visible: controlPanelBridge.selectedPromptDebugRecord.trace_id.length > 0
                                            Layout.fillWidth: true
                                            implicitHeight: 180
                                            readOnly: true
                                            text: controlPanelBridge.selectedPromptDebugRecord.user_prompt
                                        }

                                        MultiLineInput {
                                            visible: controlPanelBridge.selectedPromptDebugRecord.trace_id.length > 0
                                            Layout.fillWidth: true
                                            implicitHeight: 140
                                            readOnly: true
                                            text: controlPanelBridge.selectedPromptDebugRecord.raw_response
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "storage"
                                    Layout.fillWidth: true
                                    implicitHeight: storageContent.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: storageContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 10

                                        Text {
                                            text: "配置文件"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 15
                                            font.weight: 700
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "可将数据和日志切换到非 C 盘目录。保存时会复制已有本地数据，旧目录不会自动删除。"
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "知识库归档会自动保存在数据目录下的 knowledge_base 子目录，修改数据目录后会随本地数据一起迁移。"
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.Wrap
                                        }

                                        Text {
                                            text: "数据目录"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: 700
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 10

                                            SettingsInput {
                                                Layout.fillWidth: true
                                                text: controlPanelBridge.dataDir
                                                placeholderText: "D:/AICA/data"
                                                onTextEdited: controlPanelBridge.updateDataDir(text)
                                            }

                                            PlainButton {
                                                label: "选择目录"
                                                onClicked: controlPanelBridge.chooseStorageDir("data_dir")
                                            }
                                        }

                                        Text {
                                            text: "日志目录"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: 700
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 10

                                            SettingsInput {
                                                Layout.fillWidth: true
                                                text: controlPanelBridge.logDir
                                                placeholderText: "D:/AICA/logs"
                                                onTextEdited: controlPanelBridge.updateLogDir(text)
                                            }

                                            PlainButton {
                                                label: "选择目录"
                                                onClicked: controlPanelBridge.chooseStorageDir("log_dir")
                                            }
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "storage.json: " + controlPanelBridge.storageConfigPath
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "config.json: " + controlPanelBridge.configPath
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "analysis_rules.json: " + controlPanelBridge.analysisRulesPath
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "prompt_debug/: " + controlPanelBridge.promptDebugDirPath
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "todos.json: " + controlPanelBridge.todosPath
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "integrations.json: " + controlPanelBridge.integrationsPath
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.WrapAnywhere
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "server"
                                    Layout.fillWidth: true
                                    implicitHeight: serverContent.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: serverContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 12

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 12

                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 4

                                                Text {
                                                    text: "服务端连接"
                                                    color: root.titleInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 15
                                                    font.weight: 700
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    text: "先保存服务端地址和凭证，具体能力会在后续版本逐步接入。"
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    wrapMode: Text.Wrap
                                                }
                                            }

                                            StatusToggle {
                                                Layout.alignment: Qt.AlignTop | Qt.AlignRight
                                                checked: controlPanelBridge.serverConfig.enabled
                                                onToggled: checked => controlPanelBridge.updateServerField("enabled", checked ? "true" : "false")
                                            }
                                        }

                                        Text {
                                            text: "服务端地址"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: 700
                                        }

                                        SettingsInput {
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.serverConfig.baseUrl
                                            placeholderText: "https://chattodo.example.com"
                                            onTextEdited: controlPanelBridge.updateServerField("base_url", text)
                                        }

                                        Text {
                                            text: "API Key"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: 700
                                        }

                                        SettingsInput {
                                            Layout.fillWidth: true
                                            echoMode: TextInput.Password
                                            text: controlPanelBridge.serverConfig.apiKey
                                            placeholderText: "输入服务端 API Key"
                                            onTextEdited: controlPanelBridge.updateServerField("api_key", text)
                                        }

                                        Text {
                                            text: "请求超时（秒）"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: 700
                                        }

                                        SettingsInput {
                                            Layout.fillWidth: true
                                            inputMethodHints: Qt.ImhDigitsOnly
                                            text: controlPanelBridge.serverConfig.timeoutSeconds
                                            placeholderText: "30"
                                            onTextEdited: controlPanelBridge.updateServerField("timeout_seconds", text)
                                        }

                                        Rectangle {
                                            Layout.fillWidth: true
                                            implicitHeight: serverNotice.implicitHeight + 24
                                            radius: 12
                                            color: "#FFFFFF"
                                            border.width: 1
                                            border.color: root.panelLine

                                            Text {
                                                id: serverNotice
                                                anchors.fill: parent
                                                anchors.margins: 12
                                                text: "当前页面只负责保存连接配置，不会立即请求服务端；后续接入功能点推荐、数据同步等能力时会复用这里的设置。"
                                                color: root.bodyInk
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                                wrapMode: Text.Wrap
                                            }
                                        }
                                    }
                                }

                                ProjectsSection {
                                    theme: root
                                    Layout.fillWidth: true
                                }

                                EnvironmentsSection {
                                    theme: root
                                    Layout.fillWidth: true
                                }

                                TicketsSection {
                                    theme: root
                                    Layout.fillWidth: true
                                }

                                SectionCard {
                                    visible: false && root.currentSection === "projects"
                                    Layout.fillWidth: true
                                    implicitHeight: projectManagerContent.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: projectManagerContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 14

                                        RowLayout {
                                            visible: root.projectViewMode === "list"
                                            Layout.fillWidth: true
                                            spacing: 10

                                            SettingsInput {
                                                id: projectSearchInput
                                                Layout.fillWidth: true
                                                text: controlPanelBridge.projectQuery
                                                placeholderText: "搜索项目名称 / 任务单号 / 群名别名"
                                                onTextEdited: controlPanelBridge.listProjects(text, includeExpiredCheck.checked)
                                            }

                                            ControlPanelSettingsCheckBox {
                                                theme: root
                                                id: includeExpiredCheck
                                                checked: controlPanelBridge.includeExpiredProjects
                                                text: "包含过保项目"
                                                onToggled: controlPanelBridge.listProjects(projectSearchInput.text, checked)
                                            }
                                        }

                                        RowLayout {
                                            visible: root.projectViewMode === "list"
                                            Layout.fillWidth: true
                                            spacing: 10

                                            PlainButton {
                                                label: controlPanelBridge.projectServerSyncing ? "拉取中..." : "从服务端拉取"
                                                enabled: !controlPanelBridge.projectServerSyncing
                                                onClicked: controlPanelBridge.syncProjectsFromServer()
                                            }

                                            PlainButton {
                                                label: "新建项目"
                                                onClicked: root.startNewProjectDraft()
                                            }

                                            PlainButton {
                                                label: "补关联未解决待办"
                                                onClicked: controlPanelBridge.relinkOpenUnresolvedTodos()
                                            }

                                            RowLayout {
                                                visible: controlPanelBridge.projectServerSyncing
                                                spacing: 6

                                                BusyIndicator {
                                                    running: controlPanelBridge.projectServerSyncing
                                                    implicitWidth: 24
                                                    implicitHeight: 24
                                                }

                                                Text {
                                                    text: controlPanelBridge.projectServerSyncMessage
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                }
                                            }
                                        }

                                        Text {
                                            visible: root.projectViewMode === "list" && controlPanelBridge.lastProjectImportSummary.length > 0
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.lastProjectImportSummary
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 14

                                            Rectangle {
                                                visible: root.projectViewMode === "list"
                                                Layout.fillWidth: true
                                                Layout.preferredWidth: 340
                                                implicitHeight: 520
                                                radius: 18
                                                color: root.panelBg
                                                border.width: 1
                                                border.color: root.panelLine

                                                ColumnLayout {
                                                    anchors.fill: parent
                                                    anchors.margins: 12
                                                    spacing: 10

                                                    Text {
                                                        text: "项目列表"
                                                        color: root.titleInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: 14
                                                        font.weight: 700
                                                    }

                                                    ListView {
                                                        Layout.fillWidth: true
                                                        Layout.fillHeight: true
                                                        clip: true
                                                        spacing: 8
                                                        model: controlPanelBridge.projects

                                                        delegate: Rectangle {
                                                            id: projectCard
                                                            property bool currentProject: root.projectDraft.id === modelData.id
                                                            width: ListView.view.width
                                                            height: projectInfoColumn.implicitHeight + 20
                                                            radius: 14
                                                            color: currentProject ? root.accentSoft : root.panelBg
                                                            border.width: 1
                                                            border.color: currentProject ? root.accent : root.panelLine

                                                            Column {
                                                                id: projectInfoColumn
                                                                anchors.fill: parent
                                                                anchors.margins: 10
                                                                spacing: 6

                                                                Row {
                                                                    width: parent.width
                                                                    spacing: 8

                                                                    Text {
                                                                        width: parent.width - expireBadge.width - parent.spacing
                                                                        text: modelData.projectName
                                                                        color: root.titleInk
                                                                        font.family: root.uiFont
                                                                        font.pixelSize: 13
                                                                        font.weight: 700
                                                                        elide: Text.ElideRight
                                                                    }

                                                                    Rectangle {
                                                                        id: expireBadge
                                                                        radius: 10
                                                                        color: modelData.isExpired ? "#FFF1ED" : "#E9F7EF"
                                                                        border.width: 1
                                                                        border.color: modelData.isExpired ? "#F4C7BC" : "#B6DEC5"
                                                                        implicitWidth: expireBadgeText.implicitWidth + 18
                                                                        implicitHeight: 24

                                                                        Text {
                                                                            id: expireBadgeText
                                                                            anchors.centerIn: parent
                                                                            text: modelData.isExpired ? "已过期" : "未过期"
                                                                            color: modelData.isExpired ? "#9A3412" : "#17663A"
                                                                            font.family: root.uiFont
                                                                            font.pixelSize: 11
                                                                            font.weight: 700
                                                                        }
                                                                    }
                                                                }

                                                                Text {
                                                                    width: parent.width
                                                                    text: "任务单号: " + modelData.taskOrderNo
                                                                    color: root.bodyInk
                                                                    font.family: root.uiFont
                                                                    font.pixelSize: 11
                                                                    wrapMode: Text.WrapAnywhere
                                                                }

                                                                Text {
                                                                    width: parent.width
                                                                    text: "过保日期: " + (root.displayProjectDate(modelData.supportEndedAt) || "未填写")
                                                                    color: root.labelInk
                                                                    font.family: root.uiFont
                                                                    font.pixelSize: 11
                                                                }
                                                            }

                                                            MouseArea {
                                                                anchors.fill: parent
                                                                cursorShape: Qt.PointingHandCursor
                                                                onClicked: root.loadProjectDraft(modelData)
                                                            }
                                                        }
                                                    }
                                                }
                                            }

                                            Rectangle {
                                                visible: root.projectViewMode === "detail"
                                                Layout.fillWidth: true
                                                implicitHeight: projectFormColumn.implicitHeight + 24
                                                radius: 18
                                                color: root.panelBg
                                                border.width: 1
                                                border.color: root.panelLine

                                                ColumnLayout {
                                                    id: projectFormColumn
                                                    anchors.left: parent.left
                                                    anchors.right: parent.right
                                                    anchors.top: parent.top
                                                    anchors.margins: 12
                                                    spacing: 8

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        PlainButton {
                                                            label: "返回列表"
                                                            onClicked: root.showProjectList()
                                                        }

                                                        Item {
                                                            Layout.fillWidth: true
                                                        }
                                                    }

                                                    Text {
                                                        text: root.projectDraft.id.length > 0 ? "编辑项目" : "新建项目"
                                                        color: root.titleInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: 14
                                                        font.weight: 700
                                                    }

                                                    Text {
                                                        Layout.fillWidth: true
                                                        text: "保存时会校验群名别名冲突，并只补关联未完成且未解决关联状态的待办。"
                                                        color: root.labelInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: 11
                                                        wrapMode: Text.Wrap
                                                    }

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        SettingsInput {
                                                            Layout.fillWidth: true
                                                            text: root.projectDraft.projectName
                                                            placeholderText: "项目名称"
                                                            onTextEdited: root.updateProjectDraft("projectName", text)
                                                        }

                                                        SettingsInput {
                                                            Layout.fillWidth: true
                                                            text: root.projectDraft.taskOrderNo
                                                            placeholderText: "任务单号"
                                                            onTextEdited: root.updateProjectDraft("taskOrderNo", text)
                                                        }
                                                    }

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        SettingsInput {
                                                            Layout.fillWidth: true
                                                            text: root.projectDraft.customerName
                                                            placeholderText: "客户名称"
                                                            onTextEdited: root.updateProjectDraft("customerName", text)
                                                        }

                                                        SettingsInput {
                                                            Layout.fillWidth: true
                                                            text: root.projectDraft.projectManager
                                                            placeholderText: "项目经理"
                                                            onTextEdited: root.updateProjectDraft("projectManager", text)
                                                        }
                                                    }

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        SettingsInput {
                                                            Layout.fillWidth: true
                                                            text: root.projectDraft.productLine
                                                            placeholderText: "产品线"
                                                            onTextEdited: root.updateProjectDraft("productLine", text)
                                                        }

                                                        SettingsInput {
                                                            Layout.fillWidth: true
                                                            text: root.projectDraft.productVersion
                                                            placeholderText: "产品版本"
                                                            onTextEdited: root.updateProjectDraft("productVersion", text)
                                                        }
                                                    }

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        ControlPanelDateField {
                                                            Layout.fillWidth: true
                                                            theme: root
                                                            text: root.displayProjectDate(root.projectDraft.followUpStartedAt)
                                                            placeholderText: "跟进开始日期"
                                                            onClicked: controlPanelBridge.chooseProjectDate("followUpStartedAt", root.projectDraft.followUpStartedAt)
                                                        }
                                                    }

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        ControlPanelDateField {
                                                            Layout.fillWidth: true
                                                            theme: root
                                                            text: root.displayProjectDate(root.projectDraft.supportEndedAt)
                                                            placeholderText: "过保日期"
                                                            onClicked: controlPanelBridge.chooseProjectDate("supportEndedAt", root.projectDraft.supportEndedAt)
                                                        }
                                                    }

                                                    SettingsCombo {
                                                        Layout.fillWidth: true
                                                        model: root.projectLevelOptions
                                                        currentIndex: root.optionIndex(root.projectLevelOptions, root.normalizedProjectLevel(root.projectDraft.projectLevel))
                                                        onActivated: if (currentIndex >= 0) root.updateProjectDraft("projectLevel", root.projectLevelOptions[currentIndex].value)
                                                    }

                                                    Flow {
                                                        Layout.fillWidth: true
                                                        width: parent.width
                                                        spacing: 8

                                                        Repeater {
                                                            model: root.projectDraft.aliases

                                                            delegate: ControlPanelChip {
                                                                required property var modelData

                                                                theme: root
                                                                label: root.projectAliasText(modelData)
                                                                onRemoveClicked: root.removeProjectAlias(root.projectAliasText(modelData))
                                                            }
                                                        }
                                                    }

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        SettingsInput {
                                                            Layout.fillWidth: true
                                                            text: root.projectAliasInput
                                                            placeholderText: "输入群名别名"
                                                            onTextEdited: root.projectAliasInput = text
                                                            onAccepted: root.addProjectAlias()
                                                        }

                                                        PlainButton {
                                                            label: "添加别名"
                                                            onClicked: root.addProjectAlias()
                                                        }
                                                    }

                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        spacing: 10

                                                        PlainButton {
                                                            label: "重置"
                                                            onClicked: root.startNewProjectDraft()
                                                        }

                                                        Item {
                                                            Layout.fillWidth: true
                                                        }

                                                        PlainButton {
                                                            visible: root.projectDraft.id.length > 0
                                                            label: "删除项目"
                                                            onClicked: root.deleteCurrentProject()
                                                        }

                                                        PlainButton {
                                                            label: "保存项目"
                                                            primary: true
                                                            strokeWidth: 0
                                                            onClicked: root.saveCurrentProject()
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "integrations"
                                    Layout.fillWidth: true
                                    implicitHeight: integrationIntro.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: integrationIntro
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 12

                                        Text {
                                            text: "外部脚本"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 15
                                            font.weight: 700
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.integrationScriptHelpText
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }

                                        PlainButton {
                                            label: "上传脚本"
                                            onClicked: controlPanelBridge.addIntegrationScript()
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: root.currentSection === "integrations" && controlPanelBridge && controlPanelBridge.integrationScripts.length === 0
                                    Layout.fillWidth: true
                                    implicitHeight: emptyIntegrationContent.implicitHeight + 32
                                    color: root.panelAltBg

                                    ColumnLayout {
                                        id: emptyIntegrationContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 8

                                        Text {
                                            text: "还没有导入脚本"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 15
                                            font.weight: 700
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "先上传一个本地脚本，随后可以单独启用、停用或替换脚本路径。"
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                        }
                                    }
                                }

                                Repeater {
                                    model: root.currentSection === "integrations" && controlPanelBridge ? controlPanelBridge.integrationScripts : []

                                    delegate: SectionCard {
                                        Layout.fillWidth: true
                                        implicitHeight: integrationContent.implicitHeight + 32
                                        color: root.panelAltBg

                                        ColumnLayout {
                                            id: integrationContent
                                            anchors.fill: parent
                                            anchors.margins: 16
                                            spacing: 12

                                            RowLayout {
                                                Layout.fillWidth: true
                                                Layout.alignment: Qt.AlignTop
                                                spacing: 12

                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    Layout.alignment: Qt.AlignTop
                                                    spacing: 4

                                                    Text {
                                                        text: modelData.name
                                                        color: root.titleInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: 15
                                                        font.weight: 700
                                                    }

                                                    Text {
                                                text: modelData.supported ? (modelData.enabled ? "已启用" : "已停用") : "当前平台不支持"
                                                color: modelData.supported ? (modelData.enabled ? root.successInk : root.labelInk) : root.errorInk
                                                font.family: root.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                                    }
                                                }

                                                StatusToggle {
                                                    Layout.alignment: Qt.AlignTop | Qt.AlignRight
                                                    Layout.topMargin: 2
                                                    checked: modelData.enabled
                                                    onToggled: checked => controlPanelBridge.setIntegrationEnabled(modelData.id, checked)
                                                }
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "脚本路径: " + modelData.scriptPath
                                                color: root.bodyInk
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                                wrapMode: Text.WrapAnywhere
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: !modelData.supported ? modelData.supportMessage : (modelData.exists ? "脚本文件存在" : "警告：当前脚本路径不存在")
                                                color: modelData.supported && modelData.exists ? root.labelInk : root.errorInk
                                                font.family: root.uiFont
                                                font.pixelSize: 11
                                                wrapMode: Text.Wrap
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 10

                                                Item {
                                                    Layout.fillWidth: true
                                                }

                                                PlainButton {
                                                    label: "重新选择"
                                                    onClicked: controlPanelBridge.chooseIntegrationScript(modelData.id)
                                                }

                                                PlainButton {
                                                    label: "移除"
                                                    onClicked: controlPanelBridge.removeIntegrationScript(modelData.id)
                                                }
                                            }
                                        }
                                    }
                                }

                                Repeater {
                                    model: root.currentSection === "storage" && controlPanelBridge ? controlPanelBridge.locations : []

                                    delegate: SectionCard {
                                        Layout.fillWidth: true
                                        implicitHeight: locationContent.implicitHeight + 32
                                        color: root.panelAltBg

                                        ColumnLayout {
                                            id: locationContent
                                            anchors.fill: parent
                                            anchors.margins: 16
                                            spacing: 10

                                            Text {
                                                text: modelData.title
                                                color: root.titleInk
                                                font.family: root.uiFont
                                                font.pixelSize: 15
                                                font.weight: 700
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: modelData.description
                                                color: root.bodyInk
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                                wrapMode: Text.WrapAnywhere
                                            }

                                            PlainButton {
                                                label: "打开目录"
                                                onClicked: controlPanelBridge.openLocation(modelData.id)
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
    Item {
        anchors.right: shell.right
        anchors.bottom: shell.bottom
        anchors.margins: 10
        width: 24
        height: 24
        visible: !controlPanelBridge.windowMaximized
        z: 20

        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            width: 12
            height: 12
            radius: 4
            color: root.accentSoft
            opacity: 0.95
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.SizeFDiagCursor
            onPressed: controlPanelBridge.startWindowResize("bottom_right")
        }
    }
}

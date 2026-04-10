import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 1040
    height: 760
    color: "transparent"

    readonly property color shellBg: "#F6F2EA"
    readonly property color panelBg: "#FCF9F3"
    readonly property color panelAltBg: "#F3EEE5"
    readonly property color panelLine: "#E7DDCF"
    readonly property color titleInk: "#18202E"
    readonly property color bodyInk: "#4A5565"
    readonly property color labelInk: "#7C8795"
    readonly property color accent: "#3E7B67"
    readonly property color accentSoft: "#D8EAE2"
    readonly property color navIdle: "#F1EBE0"
    readonly property color errorBg: "#FDECEC"
    readonly property color errorInk: "#B42318"
    readonly property color successBg: "#E7F5ED"
    readonly property color successInk: "#17663A"
    readonly property string uiFont: "Microsoft YaHei UI"

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

    component PlainButton: Rectangle {
        id: buttonRoot
        property string label: ""
        property color fillColor: "#FFFDFC"
        property color inkColor: root.titleInk
        property int strokeWidth: 1
        signal clicked

        radius: 16
        color: fillColor
        border.width: strokeWidth
        border.color: root.panelLine
        implicitWidth: buttonText.implicitWidth + 28
        implicitHeight: 38

        Text {
            id: buttonText
            anchors.centerIn: parent
            text: buttonRoot.label
            color: buttonRoot.inkColor
            font.family: root.uiFont
            font.pixelSize: 12
            font.weight: 700
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: buttonRoot.clicked()
        }
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
                color: toggleRoot.checked ? root.accent : "#D7CCBE"

                Rectangle {
                    width: 22
                    height: 22
                    radius: 11
                    x: toggleRoot.checked ? parent.width - width - 2 : 2
                    y: 2
                    color: "#FFFDFC"
                    border.width: 1
                    border.color: toggleRoot.checked ? "#D1E4DA" : "#E0D4C5"
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
        property color hoverColor: "#EEE5D8"
        property color pressedColor: "#E5D9C7"
        property color inkColor: root.bodyInk
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
            font.pixelSize: 15
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

    component SettingsInput: TextField {
        id: input
        color: root.titleInk
        font.family: root.uiFont
        font.pixelSize: 12
        selectByMouse: true
        leftPadding: 14
        rightPadding: 14
        topPadding: 11
        bottomPadding: 11
        background: Rectangle {
            radius: 16
            color: "#FFFEFC"
            border.width: 1
            border.color: input.activeFocus ? root.accent : root.panelLine
        }
    }

    component SettingsCombo: ComboBox {
        id: combo
        textRole: "text"
        font.family: root.uiFont
        font.pixelSize: 12
        leftPadding: 14
        rightPadding: 34
        topPadding: 11
        bottomPadding: 11

        contentItem: Text {
            text: combo.displayText
            color: root.titleInk
            font.family: root.uiFont
            font.pixelSize: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        indicator: Canvas {
            x: combo.width - width - 14
            y: combo.topPadding + (combo.availableHeight - height) / 2
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

        background: Rectangle {
            radius: 16
            color: "#FFFEFC"
            border.width: 1
            border.color: combo.activeFocus ? root.accent : root.panelLine
        }
    }

    component SearchableModelCombo: Item {
        id: comboRoot
        property var model: []
        property string value: ""
        property string placeholderText: ""
        signal valueCommitted(string value, string capabilities)

        implicitWidth: 200
        implicitHeight: 44

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
            radius: 16
            color: "#FFFEFC"
            border.width: 1
            border.color: input.activeFocus || popup.visible ? root.accent : root.panelLine
        }

        TextField {
            id: input
            anchors.fill: parent
            color: root.titleInk
            font.family: root.uiFont
            font.pixelSize: 12
            selectByMouse: true
            leftPadding: 14
            rightPadding: 36
            topPadding: 11
            bottomPadding: 11
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
            y: 19
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
            y: comboRoot.height + 6
            width: comboRoot.width
            padding: 8
            modal: false
            focus: true
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

            background: Rectangle {
                radius: 16
                color: "#FFFEFC"
                border.width: 1
                border.color: root.panelLine
            }

            contentItem: Column {
                width: popup.width - popup.leftPadding - popup.rightPadding
                spacing: 6

                Rectangle {
                    width: parent.width
                    height: addLabel.implicitHeight + 14
                    radius: 12
                    visible: (input.text || "").trim().length > 0 && !comboRoot.hasExactMatch()
                    color: addMouseArea.pressed ? "#E7F5ED" : addMouseArea.containsMouse ? "#F1FAF5" : "#FFFFFF"

                    Text {
                        id: addLabel
                        anchors.fill: parent
                        anchors.margins: 10
                        text: "添加并使用: " + (input.text || "").trim()
                        color: root.accent
                        font.family: root.uiFont
                        font.pixelSize: 12
                        font.weight: 700
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
                    height: textOnlyLabel.implicitHeight + 14
                    radius: 12
                    visible: (input.text || "").trim().length > 0 && !comboRoot.hasExactMatch()
                    color: textOnlyMouseArea.pressed ? "#F6F0E6" : textOnlyMouseArea.containsMouse ? "#FBF6EE" : "#FFFFFF"

                    Text {
                        id: textOnlyLabel
                        anchors.fill: parent
                        anchors.margins: 10
                        text: "添加为仅文本模型"
                        color: root.bodyInk
                        font.family: root.uiFont
                        font.pixelSize: 12
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
                        height: optionText.implicitHeight + 14
                        radius: 12
                        color: optionMouseArea.pressed ? "#EDE6D9" : optionMouseArea.containsMouse ? "#F7F1E7" : "transparent"

                        Text {
                            id: optionText
                            anchors.fill: parent
                            anchors.margins: 10
                            text: modelData.text
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 12
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

    component SectionCard: Rectangle {
        radius: 24
        color: root.panelAltBg
        border.width: 0
    }

    Rectangle {
        id: shell
        anchors.fill: parent
        radius: 30
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
                color: "#FAF5EC"

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onPressed: controlPanelBridge.startWindowDrag()
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 10
                    spacing: 10

                    Rectangle {
                        Layout.preferredWidth: 18
                        Layout.preferredHeight: 18
                        radius: 9
                        color: root.accentSoft

                        Text {
                            anchors.centerIn: parent
                            text: "A"
                            color: root.accent
                            font.family: root.uiFont
                            font.pixelSize: 10
                            font.weight: 700
                        }
                    }

                    Text {
                        text: "AICA 控制面板"
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
                    color: "#F8F2E8"
                    radius: 26

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 14

                        Text {
                            text: "AICA 控制面板"
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 20
                            font.weight: 700
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "统一管理模型、截图热键与本地数据入口。"
                            color: root.bodyInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                        }

                        Repeater {
                            model: controlPanelBridge.sections

                            delegate: SectionCard {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 70
                                color: controlPanelBridge.currentSection === modelData.id ? root.accentSoft : root.panelAltBg

                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 5

                                    Text {
                                        text: modelData.title
                                        color: root.titleInk
                                        font.family: root.uiFont
                                        font.pixelSize: 13
                                        font.weight: 700
                                    }

                                    Text {
                                        width: parent.width
                                        text: modelData.description
                                        color: root.bodyInk
                                        font.family: root.uiFont
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: controlPanelBridge.setCurrentSection(modelData.id)
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
                    radius: 26

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
                                    text: controlPanelBridge.currentSection === "models" ? "模型供应商与任务模型"
                                          : controlPanelBridge.currentSection === "hotkeys" ? "截图热键"
                                          : controlPanelBridge.currentSection === "integrations" ? "脚本集成"
                                          : "存储与日志"
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 20
                                    font.weight: 700
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: controlPanelBridge.currentSection === "models" ? "管理供应商 API Key、请求地址、超时和四类任务模型绑定。"
                                          : controlPanelBridge.currentSection === "hotkeys" ? "截图热键保存后会立即重绑，无需重启应用。"
                                          : controlPanelBridge.currentSection === "integrations" ? "导入本地脚本并控制启用状态，保存后会写入 integrations.json。"
                                          : "快速打开本地数据目录，定位配置、反馈和错误日志。"
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    wrapMode: Text.Wrap
                                }
                            }

                            PlainButton {
                                visible: controlPanelBridge.currentSection !== "storage"
                                label: "保存配置"
                                fillColor: root.accent
                                inkColor: "#FFFFFF"
                                strokeWidth: 0
                                border.color: root.accent
                                onClicked: controlPanelBridge.saveCurrentSection()
                            }
                        }

                        SectionCard {
                            visible: controlPanelBridge.hasError
                            Layout.fillWidth: true
                            color: root.errorBg
                            implicitHeight: errorText.implicitHeight + 24

                            Text {
                                id: errorText
                                anchors.fill: parent
                                anchors.margins: 12
                                text: controlPanelBridge.errorMessage
                                color: root.errorInk
                                font.family: root.uiFont
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                            }
                        }

                        SectionCard {
                            visible: controlPanelBridge.hasStatus
                            Layout.fillWidth: true
                            color: root.successBg
                            implicitHeight: statusText.implicitHeight + 24

                            Text {
                                id: statusText
                                anchors.fill: parent
                                anchors.margins: 12
                                text: controlPanelBridge.statusMessage
                                color: root.successInk
                                font.family: root.uiFont
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
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

                                Repeater {
                                    model: controlPanelBridge.currentSection === "models" ? controlPanelBridge.providers : []

                                    delegate: SectionCard {
                                        Layout.fillWidth: true
                                        implicitHeight: providerContent.implicitHeight + 32
                                        color: "#F6F0E6"

                                        ColumnLayout {
                                            id: providerContent
                                            anchors.fill: parent
                                            anchors.margins: 16
                                            spacing: 12

                                            Text {
                                                text: modelData.name
                                                color: root.titleInk
                                                font.family: root.uiFont
                                                font.pixelSize: 15
                                                font.weight: 700
                                            }

                                            Text {
                                                text: modelData.kind
                                                color: root.labelInk
                                                font.family: root.uiFont
                                                font.pixelSize: 11
                                            }

                                            Text {
                                                text: "API Key"
                                                color: root.labelInk
                                                font.family: root.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                            }

                                            SettingsInput {
                                                Layout.fillWidth: true
                                                echoMode: TextInput.Password
                                                text: modelData.apiKey
                                                placeholderText: "输入 " + modelData.name + " 的 API Key"
                                                onTextEdited: controlPanelBridge.updateProviderField(modelData.id, "api_key", text)
                                            }

                                            Text {
                                                text: "Base URL"
                                                color: root.labelInk
                                                font.family: root.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                            }

                                            SettingsInput {
                                                Layout.fillWidth: true
                                                enabled: modelData.baseUrlEnabled
                                                text: modelData.baseUrl
                                                placeholderText: modelData.baseUrlEnabled ? "https://..." : "该供应商无需设置"
                                                onTextEdited: controlPanelBridge.updateProviderField(modelData.id, "base_url", text)
                                            }

                                            Text {
                                                text: "超时时间 (秒)"
                                                color: root.labelInk
                                                font.family: root.uiFont
                                                font.pixelSize: 11
                                                font.weight: 600
                                            }

                                            SettingsInput {
                                                Layout.fillWidth: true
                                                text: modelData.timeoutSeconds
                                                inputMethodHints: Qt.ImhDigitsOnly
                                                onTextEdited: controlPanelBridge.updateProviderField(modelData.id, "timeout_seconds", text)
                                            }
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: controlPanelBridge.currentSection === "models"
                                    Layout.fillWidth: true
                                    implicitHeight: bindingContent.implicitHeight + 32
                                    color: "#F6F0E6"

                                    ColumnLayout {
                                        id: bindingContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 12

                                        Text {
                                            text: "任务模型绑定"
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 15
                                            font.weight: 700
                                        }

                                        Repeater {
                                            model: controlPanelBridge.currentSection === "models" ? controlPanelBridge.taskBindings : []

                                            delegate: ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 8

                                                Text {
                                                    text: modelData.label
                                                    color: root.bodyInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 12
                                                    font.weight: 600
                                                }

                                                SettingsCombo {
                                                    id: providerCombo
                                                    Layout.fillWidth: true
                                                    model: modelData.providerOptions
                                                    currentIndex: root.optionIndex(modelData.providerOptions, modelData.providerId)
                                                    onActivated: if (currentIndex >= 0) controlPanelBridge.updateTaskBindingProvider(modelData.id, providerCombo.model[currentIndex].value)
                                                }

                                                SearchableModelCombo {
                                                    id: modelCombo
                                                    Layout.fillWidth: true
                                                    model: modelData.modelOptions
                                                    value: modelData.modelId
                                                    placeholderText: "输入或搜索模型名"
                                                    onValueCommitted: (value, capabilities) => controlPanelBridge.addOrSelectTaskBindingModel(modelData.id, value, capabilities)
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    text: modelData.performanceSummary
                                                    color: root.labelInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    wrapMode: Text.Wrap
                                                }

                                                Text {
                                                    Layout.fillWidth: true
                                                    visible: modelData.speedHint.length > 0
                                                    text: modelData.speedHint
                                                    color: "#B7793F"
                                                    font.family: root.uiFont
                                                    font.pixelSize: 11
                                                    wrapMode: Text.Wrap
                                                }
                                            }
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: controlPanelBridge.currentSection === "hotkeys"
                                    Layout.fillWidth: true
                                    implicitHeight: hotkeyContent.implicitHeight + 32
                                    color: "#F6F0E6"

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
                                            text: "支持形如 Alt+A、Ctrl+Shift+A，至少需要一个修饰键。"
                                            color: root.labelInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            wrapMode: Text.Wrap
                                            Layout.fillWidth: true
                                        }

                                        SettingsInput {
                                            Layout.fillWidth: true
                                            text: controlPanelBridge.captureHotkey
                                            placeholderText: "Alt+A"
                                            onTextEdited: controlPanelBridge.updateCaptureHotkey(text)
                                        }
                                    }
                                }

                                SectionCard {
                                    visible: controlPanelBridge.currentSection === "hotkeys"
                                    Layout.fillWidth: true
                                    implicitHeight: imageContent.implicitHeight + 32
                                    color: "#F6F0E6"

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
                                    visible: controlPanelBridge.currentSection === "storage"
                                    Layout.fillWidth: true
                                    implicitHeight: storageContent.implicitHeight + 32
                                    color: "#F6F0E6"

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
                                            text: "config.json: " + controlPanelBridge.configPath
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            wrapMode: Text.WrapAnywhere
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: "prompts.json: " + controlPanelBridge.promptsPath
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
                                    visible: controlPanelBridge.currentSection === "integrations"
                                    Layout.fillWidth: true
                                    implicitHeight: integrationIntro.implicitHeight + 32
                                    color: "#F6F0E6"

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
                                            text: "支持导入 .py、.ps1、.bat、.cmd、.exe。保存后 AICA 会继续按现有 ScriptEventHandler 规则调用脚本。"
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
                                    visible: controlPanelBridge.currentSection === "integrations" && controlPanelBridge.integrationScripts.length === 0
                                    Layout.fillWidth: true
                                    implicitHeight: emptyIntegrationContent.implicitHeight + 32
                                    color: "#F6F0E6"

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
                                    model: controlPanelBridge.currentSection === "integrations" ? controlPanelBridge.integrationScripts : []

                                    delegate: SectionCard {
                                        Layout.fillWidth: true
                                        implicitHeight: integrationContent.implicitHeight + 32
                                        color: "#F6F0E6"

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
                                                        text: modelData.enabled ? "已启用" : "已停用"
                                                        color: modelData.enabled ? root.successInk : root.labelInk
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
                                                text: modelData.exists ? "脚本文件存在" : "警告：当前脚本路径不存在"
                                                color: modelData.exists ? root.labelInk : root.errorInk
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
                                                    fillColor: "#FFF3F1"
                                                    inkColor: "#8B3A2C"
                                                    onClicked: controlPanelBridge.removeIntegrationScript(modelData.id)
                                                }
                                            }
                                        }
                                    }
                                }

                                Repeater {
                                    model: controlPanelBridge.currentSection === "storage" ? controlPanelBridge.locations : []

                                    delegate: SectionCard {
                                        Layout.fillWidth: true
                                        implicitHeight: locationContent.implicitHeight + 32
                                        color: "#F6F0E6"

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
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 1040
    height: 760
    color: "#F6F2EA"

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

    component SectionCard: Rectangle {
        radius: 22
        color: root.panelAltBg
        border.width: 0
        border.color: root.panelLine
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 16
        radius: 28
        color: root.shellBg
        border.width: 0

        RowLayout {
            anchors.fill: parent
            anchors.margins: 14
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
                            border.width: 0

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
                        radius: 24

                        Text {
                            anchors.fill: parent
                            anchors.margins: 16
                            text: "提示：如果功能提示配置缺失，请从托盘图标进入这里完成设置。"
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
                                text: controlPanelBridge.currentSection === "models" ? "模型供应商与任务模型" : controlPanelBridge.currentSection === "hotkeys" ? "截图热键" : "存储与日志"
                                color: root.titleInk
                                font.family: root.uiFont
                                font.pixelSize: 20
                                font.weight: 700
                            }

                            Text {
                                Layout.fillWidth: true
                                text: controlPanelBridge.currentSection === "models" ? "管理供应商 API Key、请求地址、超时和四类任务模型绑定。" : controlPanelBridge.currentSection === "hotkeys" ? "截图热键保存后会立即重绑，无需重启应用。" : "快速打开本地数据目录，定位配置、反馈和错误日志。"
                                color: root.bodyInk
                                font.family: root.uiFont
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                            }
                        }

                        Row {
                            spacing: 10

                            PlainButton {
                                label: "关闭"
                                onClicked: controlPanelBridge.closePanel()
                            }

                            PlainButton {
                                visible: controlPanelBridge.currentSection !== "storage"
                                label: "保存配置"
                                fillColor: root.accent
                                inkColor: "#FFFFFF"
                                strokeWidth: 0
                                border.color: root.accent
                                onClicked: controlPanelBridge.saveConfig()
                            }
                        }
                    }

                    SectionCard {
                        visible: controlPanelBridge.hasError
                        Layout.fillWidth: true
                        color: root.errorBg
                        implicitHeight: errorText.implicitHeight + 24
                        border.width: 0

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
                        border.width: 0

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
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true

                        ColumnLayout {
                            width: parent.width
                            spacing: 18

                            Repeater {
                                model: controlPanelBridge.currentSection === "models" ? controlPanelBridge.providers : []

                                delegate: SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: providerContent.implicitHeight + 32
                                    radius: 24
                                    color: "#F6F0E6"

                                    ColumnLayout {
                                        id: providerContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 12

                                        Text { text: modelData.name; color: root.titleInk; font.family: root.uiFont; font.pixelSize: 15; font.weight: 700 }
                                        Text { text: modelData.kind; color: root.labelInk; font.family: root.uiFont; font.pixelSize: 11 }

                                        Text { text: "API Key"; color: root.labelInk; font.family: root.uiFont; font.pixelSize: 11; font.weight: 600 }
                                        SettingsInput { Layout.fillWidth: true; echoMode: TextInput.Password; text: modelData.apiKey; placeholderText: "输入 " + modelData.name + " 的 API Key"; onTextEdited: controlPanelBridge.updateProviderField(modelData.id, "api_key", text) }

                                        Text { text: "Base URL"; color: root.labelInk; font.family: root.uiFont; font.pixelSize: 11; font.weight: 600 }
                                        SettingsInput { Layout.fillWidth: true; enabled: modelData.baseUrlEnabled; text: modelData.baseUrl; placeholderText: modelData.baseUrlEnabled ? "https://..." : "该供应商无需设置"; onTextEdited: controlPanelBridge.updateProviderField(modelData.id, "base_url", text) }

                                        Text { text: "超时时间（秒）"; color: root.labelInk; font.family: root.uiFont; font.pixelSize: 11; font.weight: 600 }
                                        SettingsInput { Layout.fillWidth: true; text: modelData.timeoutSeconds; inputMethodHints: Qt.ImhDigitsOnly; onTextEdited: controlPanelBridge.updateProviderField(modelData.id, "timeout_seconds", text) }
                                    }
                                }
                            }

                            SectionCard {
                                visible: controlPanelBridge.currentSection === "models"
                                Layout.fillWidth: true
                                implicitHeight: bindingContent.implicitHeight + 32
                                radius: 24
                                color: "#F6F0E6"

                                ColumnLayout {
                                    id: bindingContent
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 12

                                    Text { text: "任务模型绑定"; color: root.titleInk; font.family: root.uiFont; font.pixelSize: 15; font.weight: 700 }

                                    Repeater {
                                        model: controlPanelBridge.currentSection === "models" ? controlPanelBridge.taskBindings : []

                                        delegate: ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 8

                                            Text { text: modelData.label; color: root.bodyInk; font.family: root.uiFont; font.pixelSize: 12; font.weight: 600 }
                                            SettingsCombo { id: providerCombo; Layout.fillWidth: true; model: modelData.providerOptions; currentIndex: root.optionIndex(modelData.providerOptions, modelData.providerId); onActivated: if (currentIndex >= 0) controlPanelBridge.updateTaskBindingProvider(modelData.id, providerCombo.model[currentIndex].value) }
                                            SettingsCombo { id: modelCombo; Layout.fillWidth: true; model: modelData.modelOptions; currentIndex: root.optionIndex(modelData.modelOptions, modelData.modelId); onActivated: if (currentIndex >= 0) controlPanelBridge.updateTaskBindingModel(modelData.id, modelCombo.model[currentIndex].value) }
                                        }
                                    }
                                }
                            }

                            SectionCard {
                                visible: controlPanelBridge.currentSection === "hotkeys"
                                Layout.fillWidth: true
                                implicitHeight: hotkeyContent.implicitHeight + 32
                                radius: 24
                                color: "#F6F0E6"

                                ColumnLayout {
                                    id: hotkeyContent
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 12

                                    Text { text: "全局截图热键"; color: root.titleInk; font.family: root.uiFont; font.pixelSize: 15; font.weight: 700 }
                                    Text { text: "支持形如 Alt+A、Ctrl+Shift+A。至少需要一个修饰键。"; color: root.labelInk; font.family: root.uiFont; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    SettingsInput { Layout.fillWidth: true; text: controlPanelBridge.captureHotkey; placeholderText: "Alt+A"; onTextEdited: controlPanelBridge.updateCaptureHotkey(text) }
                                }
                            }

                            SectionCard {
                                visible: controlPanelBridge.currentSection === "hotkeys"
                                Layout.fillWidth: true
                                implicitHeight: imageContent.implicitHeight + 32
                                radius: 24
                                color: "#F6F0E6"

                                ColumnLayout {
                                    id: imageContent
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 12

                                    Text { text: "图片压缩阈值"; color: root.titleInk; font.family: root.uiFont; font.pixelSize: 15; font.weight: 700 }
                                    Text { text: "超过该大小的截图会在发送前进行压缩。"; color: root.labelInk; font.family: root.uiFont; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    SettingsInput { Layout.fillWidth: true; text: controlPanelBridge.maxImageMegabytes; placeholderText: "4"; onTextEdited: controlPanelBridge.updateMaxImageMegabytes(text) }
                                }
                            }

                            SectionCard {
                                visible: controlPanelBridge.currentSection === "storage"
                                Layout.fillWidth: true
                                implicitHeight: storageContent.implicitHeight + 32
                                radius: 24
                                color: "#F6F0E6"

                                ColumnLayout {
                                    id: storageContent
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    spacing: 10

                                    Text { text: "配置文件"; color: root.titleInk; font.family: root.uiFont; font.pixelSize: 15; font.weight: 700 }
                                    Text { Layout.fillWidth: true; text: "config.json: " + controlPanelBridge.configPath; color: root.bodyInk; font.family: root.uiFont; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                                    Text { Layout.fillWidth: true; text: "prompts.json: " + controlPanelBridge.promptsPath; color: root.bodyInk; font.family: root.uiFont; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                                    Text { Layout.fillWidth: true; text: "todos.json: " + controlPanelBridge.todosPath; color: root.bodyInk; font.family: root.uiFont; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                                }
                            }

                            Repeater {
                                model: controlPanelBridge.currentSection === "storage" ? controlPanelBridge.locations : []

                                delegate: SectionCard {
                                    Layout.fillWidth: true
                                    implicitHeight: locationContent.implicitHeight + 32
                                    radius: 24
                                    color: "#F6F0E6"

                                    ColumnLayout {
                                        id: locationContent
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        spacing: 10

                                        Text { text: modelData.title; color: root.titleInk; font.family: root.uiFont; font.pixelSize: 15; font.weight: 700 }
                                        Text { Layout.fillWidth: true; text: modelData.description; color: root.bodyInk; font.family: root.uiFont; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                                        PlainButton { label: "打开目录"; onClicked: controlPanelBridge.openLocation(modelData.id) }
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

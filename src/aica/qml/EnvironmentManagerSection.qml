import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var theme
    required property string scopeMode
    required property var selectedEnvironment
    property string projectId: ""
    property bool creatingEnvironment: false
    readonly property bool editable: scopeMode === "global" || projectId.length > 0
    property var environmentDraft: emptyEnvironmentDraft()
    property bool accessEditorVisible: false
    property var accessDraft: emptyAccessDraft()
    property string editingEntryEnvironmentId: ""
    property var accessTypeOptions: [
        { value: "web", text: "web" },
        { value: "ssh", text: "ssh" },
        { value: "rdp", text: "rdp" },
        { value: "db", text: "db" },
        { value: "vpn", text: "vpn" }
    ]

    signal backRequested()

    spacing: 12

    function emptyEnvironmentDraft() {
        return {
            id: "",
            name: "",
            type: "",
            note: "",
            sortOrder: 0,
            isActive: true
        }
    }

    function emptyAccessDraft() {
        return {
            id: "",
            name: "",
            type: "web",
            urlOrHost: "",
            username: "",
            password: "",
            otpConfig: "",
            note: "",
            sortOrder: 0,
            isActive: true,
            requiresOtp: true,
            hasPassword: false,
            hasOtpConfig: false
        }
    }

    function loadEnvironmentDraft() {
        if (creatingEnvironment) {
            environmentDraft = emptyEnvironmentDraft()
            accessEditorVisible = false
            accessDraft = emptyAccessDraft()
            editingEntryEnvironmentId = ""
            return
        }
        environmentDraft = {
            id: selectedEnvironment.id || "",
            name: selectedEnvironment.name || "",
            type: selectedEnvironment.type || "",
            note: selectedEnvironment.note || "",
            sortOrder: Number(selectedEnvironment.sortOrder || 0),
            isActive: !!selectedEnvironment.isActive
        }
    }

    function saveEnvironment() {
        if (!editable) {
            return
        }
        var payload = {
            id: environmentDraft.id || "",
            name: (environmentDraft.name || "").trim(),
            type: (environmentDraft.type || "").trim(),
            note: (environmentDraft.note || "").trim(),
            sortOrder: Number(environmentDraft.sortOrder || 0),
            isActive: !!environmentDraft.isActive
        }
        if (scopeMode === "global") {
            controlPanelBridge.saveGlobalEnvironment(payload)
        } else {
            controlPanelBridge.saveProjectEnvironment(projectId, payload)
        }
    }

    function deleteCurrentEnvironment() {
        if (creatingEnvironment || !(selectedEnvironment.id || "").length) {
            backRequested()
            return
        }
        if (scopeMode === "global") {
            controlPanelBridge.deleteGlobalEnvironment(selectedEnvironment.id)
        } else {
            controlPanelBridge.deleteProjectEnvironment(selectedEnvironment.id)
        }
        backRequested()
    }

    function openCreateAccess() {
        if (!editable || !(selectedEnvironment.id || "").length) {
            return
        }
        accessDraft = emptyAccessDraft()
        editingEntryEnvironmentId = selectedEnvironment.id || ""
        accessEditorVisible = true
    }

    function openEditAccess(entryItem) {
        accessDraft = {
            id: entryItem.id || "",
            name: entryItem.name || "",
            type: entryItem.type || "web",
            urlOrHost: entryItem.urlOrHost || "",
            username: entryItem.username || "",
            password: "",
            otpConfig: "",
            note: entryItem.note || "",
            sortOrder: Number(entryItem.sortOrder || 0),
            isActive: !!entryItem.isActive,
            requiresOtp: !!entryItem.requiresOtp,
            hasPassword: !!entryItem.hasPassword,
            hasOtpConfig: !!entryItem.hasOtpConfig
        }
        editingEntryEnvironmentId = selectedEnvironment.id || ""
        accessEditorVisible = true
    }

    function closeAccessEditor() {
        accessEditorVisible = false
        accessDraft = emptyAccessDraft()
        editingEntryEnvironmentId = ""
    }

    function saveAccess() {
        if (!(editingEntryEnvironmentId || "").length) {
            return
        }
        var payload = {
            id: accessDraft.id || "",
            name: (accessDraft.name || "").trim(),
            type: (accessDraft.type || "web").trim(),
            urlOrHost: (accessDraft.urlOrHost || "").trim(),
            username: (accessDraft.username || "").trim(),
            password: accessDraft.password || "",
            otpConfig: accessDraft.otpConfig || "",
            note: (accessDraft.note || "").trim(),
            sortOrder: Number(accessDraft.sortOrder || 0),
            isActive: !!accessDraft.isActive,
            requiresOtp: !!accessDraft.requiresOtp
        }
        if (scopeMode === "global") {
            controlPanelBridge.saveGlobalEnvironmentAccessEntry(editingEntryEnvironmentId, payload)
        } else {
            controlPanelBridge.saveProjectEnvironmentAccessEntry(editingEntryEnvironmentId, payload)
        }
        closeAccessEditor()
    }

    function deleteAccess(entryItem) {
        if (scopeMode === "global") {
            controlPanelBridge.deleteGlobalEnvironmentAccessEntry(entryItem.id)
        } else {
            controlPanelBridge.deleteProjectEnvironmentAccessEntry(entryItem.id)
        }
    }

    function importOtpConfig() {
        var result = controlPanelBridge.importOtpConfigFromQrImage({})
        if (result && result.success) {
            var next = accessDraft
            next.otpConfig = result.otpConfig || result.rawPayload || ""
            accessDraft = next
        }
    }

    onSelectedEnvironmentChanged: loadEnvironmentDraft()
    onCreatingEnvironmentChanged: loadEnvironmentDraft()
    Component.onCompleted: loadEnvironmentDraft()

    Rectangle {
        Layout.fillWidth: true
        radius: 18
        color: theme.panelBg
        border.width: 1
        border.color: theme.panelLine
        implicitHeight: headerContent.implicitHeight + 24

        ColumnLayout {
            id: headerContent
            anchors.fill: parent
            anchors.margins: 12
            spacing: 12

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ControlPanelPlainButton {
                    theme: root.theme
                    label: "返回列表"
                    onClicked: root.backRequested()
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: root.creatingEnvironment ? "新建环境" : ((root.selectedEnvironment.name || "").length > 0 ? root.selectedEnvironment.name : "环境详情")
                        color: theme.titleInk
                        font.family: theme.uiFont
                        font.pixelSize: 15
                        font.weight: 700
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.creatingEnvironment
                            ? "先保存环境基础信息，保存后再维护该环境的访问信息。"
                            : "详情页集中维护环境基础信息和该环境下的访问信息。"
                        color: theme.labelInk
                        font.family: theme.uiFont
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        radius: 18
        color: theme.panelBg
        border.width: 1
        border.color: theme.panelLine
        implicitHeight: environmentForm.implicitHeight + 24

        ColumnLayout {
            id: environmentForm
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Text {
                text: "环境基础信息"
                color: theme.titleInk
                font.family: theme.uiFont
                font.pixelSize: 13
                font.weight: 700
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ControlPanelSettingsInput {
                    theme: root.theme
                    Layout.fillWidth: true
                    text: environmentDraft.name || ""
                    placeholderText: "环境名称"
                    onTextEdited: {
                        var next = environmentDraft
                        next.name = text
                        environmentDraft = next
                    }
                }

                ControlPanelSettingsInput {
                    theme: root.theme
                    Layout.fillWidth: true
                    text: environmentDraft.type || ""
                    placeholderText: "环境类型"
                    onTextEdited: {
                        var next = environmentDraft
                        next.type = text
                        environmentDraft = next
                    }
                }

                Text {
                    text: "排序"
                    color: theme.labelInk
                    font.family: theme.uiFont
                    font.pixelSize: 12
                }

                SpinBox {
                    Layout.preferredWidth: 120
                    from: 0
                    to: 999
                    editable: true
                    value: Number(environmentDraft.sortOrder || 0)
                    onValueModified: {
                        var next = environmentDraft
                        next.sortOrder = value
                        environmentDraft = next
                    }
                }
            }

            TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 72
                text: environmentDraft.note || ""
                placeholderText: "备注"
                wrapMode: TextEdit.Wrap
                font.family: theme.uiFont
                font.pixelSize: 12
                color: theme.titleInk
                onTextChanged: {
                    var next = environmentDraft
                    next.note = text
                    environmentDraft = next
                }
                background: Rectangle {
                    radius: 16
                    color: theme.inputBg
                    border.width: 1
                    border.color: theme.panelLine
                }
            }

            CheckBox {
                checked: !!environmentDraft.isActive
                text: "启用环境"
                font.family: theme.uiFont
                onToggled: {
                    var next = environmentDraft
                    next.isActive = checked
                    environmentDraft = next
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Text {
                    visible: !root.creatingEnvironment && (root.selectedEnvironment.scopeLabel || "").length > 0
                    text: "范围：" + (root.selectedEnvironment.scopeLabel || "")
                    color: theme.labelInk
                    font.family: theme.uiFont
                    font.pixelSize: 11
                }

                Item {
                    Layout.fillWidth: true
                }

                ControlPanelPlainButton {
                    theme: root.theme
                    label: root.creatingEnvironment ? "取消" : "删除环境"
                    onClicked: root.deleteCurrentEnvironment()
                }

                ControlPanelPlainButton {
                    theme: root.theme
                    label: "保存环境"
                    fillColor: theme.accent
                    inkColor: "#FFFFFF"
                    strokeWidth: 0
                    onClicked: root.saveEnvironment()
                }
            }
        }
    }

    Rectangle {
        visible: !root.creatingEnvironment && (root.selectedEnvironment.id || "").length > 0
        Layout.fillWidth: true
        radius: 18
        color: theme.panelBg
        border.width: 1
        border.color: theme.panelLine
        implicitHeight: accessContent.implicitHeight + 24

        ColumnLayout {
            id: accessContent
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            RowLayout {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: "访问信息"
                        color: theme.titleInk
                        font.family: theme.uiFont
                        font.pixelSize: 13
                        font.weight: 700
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "当前环境共 " + Number(root.selectedEnvironment.entryCount || 0) + " 个访问项。"
                        color: theme.labelInk
                        font.family: theme.uiFont
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                    }
                }

                ControlPanelPlainButton {
                    theme: root.theme
                    label: "新增访问项"
                    onClicked: root.openCreateAccess()
                }
            }

            Text {
                visible: (root.selectedEnvironment.entries || []).length === 0
                Layout.fillWidth: true
                text: "当前环境还没有访问信息。"
                color: theme.bodyInk
                font.family: theme.uiFont
                font.pixelSize: 12
            }

            Repeater {
                model: root.selectedEnvironment.entries || []

                delegate: Rectangle {
                    Layout.fillWidth: true
                    radius: 16
                    color: theme.panelAltBg
                    border.width: 1
                    border.color: theme.panelLine
                    implicitHeight: entryColumn.implicitHeight + 20

                    ColumnLayout {
                        id: entryColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 6

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                Layout.fillWidth: true
                                text: (modelData.name || "") + (((modelData.type || "").length > 0) ? (" · " + modelData.type) : "")
                                color: theme.titleInk
                                font.family: theme.uiFont
                                font.pixelSize: 12
                                font.weight: 700
                            }

                            Text {
                                text: (modelData.hasPassword ? "已存密码" : "未存密码")
                                      + " / "
                                      + (modelData.hasOtpConfig ? "已存 OTP" : "未存 OTP")
                                color: theme.labelInk
                                font.family: theme.uiFont
                                font.pixelSize: 10
                            }
                        }

                        Text {
                            visible: (modelData.urlOrHost || "").length > 0
                            Layout.fillWidth: true
                            text: modelData.urlOrHost || ""
                            color: theme.bodyInk
                            font.family: theme.uiFont
                            font.pixelSize: 11
                            wrapMode: Text.WrapAnywhere
                        }

                        Text {
                            visible: (modelData.username || "").length > 0 || (modelData.note || "").length > 0
                            Layout.fillWidth: true
                            text: ((modelData.username || "").length > 0 ? ("账号：" + modelData.username) : "")
                                  + (((modelData.username || "").length > 0 && (modelData.note || "").length > 0) ? " · " : "")
                                  + ((modelData.note || "").length > 0 ? modelData.note : "")
                            color: theme.labelInk
                            font.family: theme.uiFont
                            font.pixelSize: 10
                            wrapMode: Text.Wrap
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                text: !!modelData.isActive ? "已启用" : "已停用"
                                color: !!modelData.isActive ? "#17663A" : theme.labelInk
                                font.family: theme.uiFont
                                font.pixelSize: 10
                                font.weight: 600
                            }

                            Item {
                                Layout.fillWidth: true
                            }

                            ControlPanelPlainButton {
                                theme: root.theme
                                label: "编辑"
                                onClicked: root.openEditAccess(modelData)
                            }

                            ControlPanelPlainButton {
                                theme: root.theme
                                label: "删除"
                                onClicked: root.deleteAccess(modelData)
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        visible: accessEditorVisible
        Layout.fillWidth: true
        radius: 18
        color: theme.panelBg
        border.width: 1
        border.color: theme.panelLine
        implicitHeight: accessForm.implicitHeight + 24

        ColumnLayout {
            id: accessForm
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Text {
                text: (accessDraft.id || "").length > 0 ? "编辑访问项" : "新增访问项"
                color: theme.titleInk
                font.family: theme.uiFont
                font.pixelSize: 13
                font.weight: 700
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ControlPanelSettingsInput {
                    theme: root.theme
                    Layout.fillWidth: true
                    text: accessDraft.name || ""
                    placeholderText: "访问项名称"
                    onTextEdited: {
                        var next = accessDraft
                        next.name = text
                        accessDraft = next
                    }
                }

                ControlPanelSettingsCombo {
                    theme: root.theme
                    Layout.fillWidth: true
                    model: root.accessTypeOptions
                    currentIndex: Math.max(0, theme.optionIndex(root.accessTypeOptions, accessDraft.type || "web"))
                    onActivated: {
                        var next = accessDraft
                        next.type = root.accessTypeOptions[currentIndex].value
                        accessDraft = next
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ControlPanelSettingsInput {
                    theme: root.theme
                    Layout.fillWidth: true
                    text: accessDraft.urlOrHost || ""
                    placeholderText: "URL / Host"
                    onTextEdited: {
                        var next = accessDraft
                        next.urlOrHost = text
                        accessDraft = next
                    }
                }

                ControlPanelSettingsInput {
                    theme: root.theme
                    Layout.fillWidth: true
                    text: accessDraft.username || ""
                    placeholderText: "账号"
                    onTextEdited: {
                        var next = accessDraft
                        next.username = text
                        accessDraft = next
                    }
                }
            }

            ControlPanelSettingsInput {
                theme: root.theme
                Layout.fillWidth: true
                text: accessDraft.password || ""
                placeholderText: accessDraft.hasPassword ? "留空则保持已存密码" : "密码"
                echoMode: TextInput.Password
                onTextEdited: {
                    var next = accessDraft
                    next.password = text
                    accessDraft = next
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                TextArea {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 86
                    text: accessDraft.otpConfig || ""
                    placeholderText: accessDraft.hasOtpConfig
                        ? "留空则保持已存 OTP 配置"
                        : "OTP 配置，支持 tpauth://..."
                    wrapMode: TextEdit.Wrap
                    font.family: theme.uiFont
                    font.pixelSize: 12
                    color: theme.titleInk
                    onTextChanged: {
                        var next = accessDraft
                        next.otpConfig = text
                        accessDraft = next
                    }
                    background: Rectangle {
                        radius: 16
                        color: theme.inputBg
                        border.width: 1
                        border.color: theme.panelLine
                    }
                }

                ColumnLayout {
                    Layout.preferredWidth: 150
                    spacing: 8

                    ControlPanelPlainButton {
                        theme: root.theme
                        label: "从二维码导入"
                        onClicked: root.importOtpConfig()
                    }

                    CheckBox {
                        checked: !!accessDraft.requiresOtp
                        text: "启用 OTP"
                        font.family: theme.uiFont
                        onToggled: {
                            var next = accessDraft
                            next.requiresOtp = checked
                            accessDraft = next
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Text {
                    text: "排序"
                    color: theme.labelInk
                    font.family: theme.uiFont
                    font.pixelSize: 12
                }

                SpinBox {
                    Layout.preferredWidth: 120
                    from: 0
                    to: 999
                    editable: true
                    value: Number(accessDraft.sortOrder || 0)
                    onValueModified: {
                        var next = accessDraft
                        next.sortOrder = value
                        accessDraft = next
                    }
                }
            }

            TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 70
                text: accessDraft.note || ""
                placeholderText: "备注"
                wrapMode: TextEdit.Wrap
                font.family: theme.uiFont
                font.pixelSize: 12
                color: theme.titleInk
                onTextChanged: {
                    var next = accessDraft
                    next.note = text
                    accessDraft = next
                }
                background: Rectangle {
                    radius: 16
                    color: theme.inputBg
                    border.width: 1
                    border.color: theme.panelLine
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 18

                CheckBox {
                    checked: !!accessDraft.isActive
                    text: "启用访问项"
                    font.family: theme.uiFont
                    onToggled: {
                        var next = accessDraft
                        next.isActive = checked
                        accessDraft = next
                    }
                }

                Item {
                    Layout.fillWidth: true
                }

                ControlPanelPlainButton {
                    theme: root.theme
                    label: "取消"
                    onClicked: root.closeAccessEditor()
                }

                ControlPanelPlainButton {
                    theme: root.theme
                    label: "保存访问项"
                    fillColor: theme.accent
                    inkColor: "#FFFFFF"
                    strokeWidth: 0
                    onClicked: root.saveAccess()
                }
            }
        }
    }
}

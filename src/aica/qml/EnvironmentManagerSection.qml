import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var theme
    required property string scopeMode
    required property var groupsModel
    property string projectId: ""
    property string emptyStateText: ""
    readonly property bool editable: scopeMode === "global" || projectId.length > 0
    property bool environmentEditorVisible: false
    property bool accessEditorVisible: false
    property var environmentDraft: ({})
    property var accessDraft: ({})
    property string editingEnvironmentId: ""
    property string editingEntryEnvironmentId: ""
    property var accessTypeOptions: [
        { value: "web", text: "web" },
        { value: "ssh", text: "ssh" },
        { value: "rdp", text: "rdp" },
        { value: "db", text: "db" },
        { value: "vpn", text: "vpn" }
    ]

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

    function syncProjectEnvironmentList() {
        if (scopeMode === "global") {
            controlPanelBridge.listGlobalEnvironments()
            return
        }
        controlPanelBridge.listProjectEnvironments(projectId)
    }

    function openCreateEnvironment() {
        if (!editable) {
            return
        }
        environmentDraft = emptyEnvironmentDraft()
        editingEnvironmentId = ""
        environmentEditorVisible = true
    }

    function openEditEnvironment(groupItem) {
        environmentDraft = {
            id: groupItem.id || "",
            name: groupItem.name || "",
            type: groupItem.type || "",
            note: groupItem.note || "",
            sortOrder: Number(groupItem.sortOrder || 0),
            isActive: !!groupItem.isActive
        }
        editingEnvironmentId = groupItem.id || ""
        environmentEditorVisible = true
    }

    function closeEnvironmentEditor() {
        environmentEditorVisible = false
        environmentDraft = emptyEnvironmentDraft()
        editingEnvironmentId = ""
    }

    function saveEnvironment() {
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
        closeEnvironmentEditor()
    }

    function openCreateAccess(environmentId) {
        if (!editable) {
            return
        }
        accessDraft = emptyAccessDraft()
        editingEntryEnvironmentId = environmentId || ""
        accessEditorVisible = true
    }

    function openEditAccess(environmentId, entryItem) {
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
        editingEntryEnvironmentId = environmentId || ""
        accessEditorVisible = true
    }

    function closeAccessEditor() {
        accessEditorVisible = false
        accessDraft = emptyAccessDraft()
        editingEntryEnvironmentId = ""
    }

    function saveAccess() {
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

    function deleteEnvironment(groupItem) {
        if (scopeMode === "global") {
            controlPanelBridge.deleteGlobalEnvironment(groupItem.id)
        } else {
            controlPanelBridge.deleteProjectEnvironment(groupItem.id)
        }
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

    Component.onCompleted: syncProjectEnvironmentList()

    onProjectIdChanged: {
        if (scopeMode === "project") {
            syncProjectEnvironmentList()
        }
    }

    Rectangle {
        Layout.fillWidth: true
        radius: 18
        color: theme.panelBg
        border.width: 1
        border.color: theme.panelLine
        implicitHeight: summaryColumn.implicitHeight + 24

        ColumnLayout {
            id: summaryColumn
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            RowLayout {
                Layout.fillWidth: true

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Text {
                        text: scopeMode === "global" ? "全局环境模板" : "项目环境维护"
                        color: theme.titleInk
                        font.family: theme.uiFont
                        font.pixelSize: 14
                        font.weight: 700
                    }

                    Text {
                        Layout.fillWidth: true
                        text: editable
                            ? (scopeMode === "global"
                               ? "全局环境对所有项目默认可见；项目级同名环境可以覆盖。"
                               : "维护当前项目的专属环境；保存后待办详情会自动读取全局与项目级合并结果。")
                            : "请先保存项目，再维护项目环境。"
                        color: theme.labelInk
                        font.family: theme.uiFont
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                    }
                }

                ControlPanelPlainButton {
                    theme: root.theme
                    label: "新增环境"
                    visible: editable
                    onClicked: root.openCreateEnvironment()
                }
            }

            Text {
                visible: groupsModel.length === 0
                Layout.fillWidth: true
                text: emptyStateText.length > 0 ? emptyStateText : (editable ? "当前还没有环境分组" : "当前项目尚未保存")
                color: theme.bodyInk
                font.family: theme.uiFont
                font.pixelSize: 12
            }

            Repeater {
                model: groupsModel

                delegate: Rectangle {
                    property string groupId: modelData.id || ""
                    Layout.fillWidth: true
                    radius: 16
                    color: theme.panelAltBg
                    border.width: 1
                    border.color: theme.panelLine
                    implicitHeight: groupColumn.implicitHeight + 20

                    ColumnLayout {
                        id: groupColumn
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name || ""
                                color: theme.titleInk
                                font.family: theme.uiFont
                                font.pixelSize: 13
                                font.weight: 700
                            }

                            Rectangle {
                                radius: 10
                                color: modelData.isGlobal ? "#EEF4FF" : "#EEF7EF"
                                border.width: 1
                                border.color: modelData.isGlobal ? "#C8D8FF" : "#C8E2CD"
                                implicitWidth: scopeText.implicitWidth + 16
                                implicitHeight: 24

                                Text {
                                    id: scopeText
                                    anchors.centerIn: parent
                                    text: modelData.scopeLabel || ""
                                    color: modelData.isGlobal ? "#26418F" : "#17663A"
                                    font.family: theme.uiFont
                                    font.pixelSize: 10
                                    font.weight: 700
                                }
                            }
                        }

                        Text {
                            visible: (modelData.type || "").length > 0 || (modelData.note || "").length > 0
                            Layout.fillWidth: true
                            text: ((modelData.type || "").length > 0 ? ("类型: " + modelData.type) : "")
                                  + (((modelData.type || "").length > 0 && (modelData.note || "").length > 0) ? " · " : "")
                                  + ((modelData.note || "").length > 0 ? modelData.note : "")
                            color: theme.bodyInk
                            font.family: theme.uiFont
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            ControlPanelPlainButton {
                                theme: root.theme
                                label: "新增访问项"
                                onClicked: root.openCreateAccess(modelData.id)
                            }

                            ControlPanelPlainButton {
                                theme: root.theme
                                label: "编辑环境"
                                onClicked: root.openEditEnvironment(modelData)
                            }

                            ControlPanelPlainButton {
                                theme: root.theme
                                label: "删除环境"
                                onClicked: root.deleteEnvironment(modelData)
                            }
                        }

                        Repeater {
                            model: modelData.entries || []

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                radius: 14
                                color: "#FFFFFF"
                                border.width: 1
                                border.color: theme.panelLine
                                implicitHeight: entryColumn.implicitHeight + 18

                                ColumnLayout {
                                    id: entryColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 6

                                    RowLayout {
                                        Layout.fillWidth: true

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.name || ""
                                            color: theme.titleInk
                                            font.family: theme.uiFont
                                            font.pixelSize: 12
                                            font.weight: 700
                                        }

                                        Text {
                                            text: (modelData.hasPassword ? "已保存密码" : "无密码")
                                                  + " / "
                                                  + (modelData.hasOtpConfig ? "已保存 OTP" : "无 OTP")
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
                                        text: ((modelData.username || "").length > 0 ? ("账号: " + modelData.username) : "")
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

                                        ControlPanelPlainButton {
                                            theme: root.theme
                                            label: "编辑"
                                            onClicked: root.openEditAccess(groupId, modelData)
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
            }
        }
    }

    Rectangle {
        visible: environmentEditorVisible
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
                text: editingEnvironmentId.length > 0 ? "编辑环境" : "新增环境"
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
                Layout.preferredHeight: 70
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
                text: "启用该环境"
                font.family: theme.uiFont
                onToggled: {
                    var next = environmentDraft
                    next.isActive = checked
                    environmentDraft = next
                }
            }

            RowLayout {
                Layout.fillWidth: true

                Item { Layout.fillWidth: true }

                ControlPanelPlainButton {
                    theme: root.theme
                    label: "取消"
                    onClicked: root.closeEnvironmentEditor()
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
                text: accessDraft.id && accessDraft.id.length > 0 ? "编辑访问项" : "新增访问项"
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
                    placeholderText: "访问方式名称"
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
                placeholderText: accessDraft.hasPassword ? "留空表示保留当前密码" : "密码"
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
                    placeholderText: accessDraft.hasOtpConfig ? "留空表示保留当前 OTP 配置" : "OTP 配置（otpauth://... 或 secret）"
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
                        label: "导入二维码"
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

                Item { Layout.fillWidth: true }

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

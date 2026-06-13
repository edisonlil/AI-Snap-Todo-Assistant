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
            hasOtpConfig: false,
            otpImportSummary: "",
            otpPreviewUrl: ""
        }
    }

    function copyAccessDraft(overrides) {
        var source = accessDraft || emptyAccessDraft()
        var next = {
            id: source.id || "",
            name: source.name || "",
            type: source.type || "web",
            urlOrHost: source.urlOrHost || "",
            username: source.username || "",
            password: source.password || "",
            otpConfig: source.otpConfig || "",
            note: source.note || "",
            sortOrder: Number(source.sortOrder || 0),
            isActive: !!source.isActive,
            requiresOtp: !!source.requiresOtp,
            hasPassword: !!source.hasPassword,
            hasOtpConfig: !!source.hasOtpConfig,
            otpImportSummary: source.otpImportSummary || "",
            otpPreviewUrl: source.otpPreviewUrl || ""
        }
        for (var key in overrides) {
            next[key] = overrides[key]
        }
        return next
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
        openAccessEditorPopup()
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
            hasOtpConfig: !!entryItem.hasOtpConfig,
            otpImportSummary: entryItem.hasOtpConfig ? "已保存 OTP 配置" : "",
            otpPreviewUrl: ""
        }
        editingEntryEnvironmentId = selectedEnvironment.id || ""
        openAccessEditorPopup()
    }

    function openAccessEditorPopup() {
        accessEditorVisible = true
        accessEditorPopup.open()
        Qt.callLater(function() {
            accessNameInput.forceActiveFocus()
            accessNameInput.selectAll()
        })
    }

    function closeAccessEditor() {
        accessEditorVisible = false
        accessDraft = emptyAccessDraft()
        editingEntryEnvironmentId = ""
        accessEditorPopup.close()
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
        if (controlPanelBridge.hasError) {
            return
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
        applyOtpImportResult(result)
    }

    function pasteOtpConfig() {
        var result = controlPanelBridge.importOtpConfigFromClipboardQr()
        applyOtpImportResult(result)
    }

    function importDroppedOtpConfig(urls) {
        if (!urls || urls.length <= 0) {
            return
        }
        var result = controlPanelBridge.importOtpConfigFromQrImagePath(String(urls[0]))
        applyOtpImportResult(result)
    }

    function applyOtpImportResult(result) {
        if (result && result.success) {
            accessDraft = copyAccessDraft({
                otpConfig: result.otpConfig || result.rawPayload || "",
                requiresOtp: true,
                otpImportSummary: otpImportDisplayText(result),
                otpPreviewUrl: result.previewImageUrl || ""
            })
        }
    }

    function otpImportDisplayText(result) {
        var issuer = result && result.issuer ? String(result.issuer) : ""
        var account = result && result.account ? String(result.account) : ""
        var label = result && result.label ? String(result.label) : ""
        if (issuer.length > 0 && account.length > 0) {
            return issuer + " / " + account
        }
        if (label.length > 0) {
            return label
        }
        return "已解析 OTP 配置"
    }

    function hasOtpDraftDisplay() {
        return (accessDraft.otpConfig || "").length > 0
            || (accessDraft.otpImportSummary || "").length > 0
            || !!accessDraft.hasOtpConfig
    }

    onSelectedEnvironmentChanged: loadEnvironmentDraft()
    onCreatingEnvironmentChanged: loadEnvironmentDraft()
    Component.onCompleted: loadEnvironmentDraft()

    DetailRuntime {
        Layout.fillWidth: true
        theme: root.theme
        title: root.creatingEnvironment ? "新建环境" : ((root.selectedEnvironment.name || "").length > 0 ? root.selectedEnvironment.name : "环境详情")
        description: root.creatingEnvironment
            ? "先保存环境基础信息，保存后再维护该环境的访问信息。"
            : "详情页集中维护环境基础信息和该环境下的访问信息。"
        onBackRequested: root.backRequested()

        bodyContent: ColumnLayout {
            Layout.fillWidth: true
            spacing: 12

    Rectangle {
        Layout.fillWidth: true
        radius: 12
        color: theme.panelAltBg
        border.width: 0
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

                ControlPanelSettingsSpinBox {
                    theme: root.theme
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

            ControlPanelSettingsArea {
                theme: root.theme
                Layout.fillWidth: true
                Layout.preferredHeight: 72
                text: environmentDraft.note || ""
                placeholderText: "备注"
                onTextChanged: {
                    var next = environmentDraft
                    next.note = text
                    environmentDraft = next
                }
            }

            ControlPanelSettingsCheckBox {
                theme: root.theme
                checked: !!environmentDraft.isActive
                text: "启用环境"
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
                    primary: true
                    strokeWidth: 0
                    onClicked: root.saveEnvironment()
                }
            }
        }
    }

    Rectangle {
        visible: !root.creatingEnvironment && (root.selectedEnvironment.id || "").length > 0
        Layout.fillWidth: true
        radius: 12
        color: theme.panelAltBg
        border.width: 0
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
    }
    }

    Item {
        visible: false
        implicitWidth: 0
        implicitHeight: 0

        Popup {
            id: accessEditorPopup
            parent: Overlay.overlay
            x: Math.round((parent.width - width) / 2)
            y: Math.round((parent.height - height) / 2)
            width: Math.max(280, Math.min(860, parent.width - 64))
            height: Math.min(accessEditorScroll.implicitHeight + topPadding + bottomPadding, Math.max(320, parent.height - 80))
            modal: true
            focus: true
            padding: 16
            closePolicy: Popup.CloseOnEscape
            onClosed: {
                if (accessEditorVisible) {
                    root.closeAccessEditor()
                }
            }

            background: Rectangle {
                radius: 18
                color: theme.panelBg
                border.width: 1
                border.color: theme.panelLine
            }

            Overlay.modal: Rectangle {
                color: "#66000000"
            }

            Shortcut {
                sequences: [StandardKey.Paste]
                enabled: accessEditorPopup.visible
                onActivated: root.pasteOtpConfig()
            }

            contentItem: ScrollView {
                id: accessEditorScroll
                implicitHeight: Math.min(accessForm.implicitHeight, 620)
                clip: true

                ColumnLayout {
                    id: accessForm
                    width: accessEditorScroll.availableWidth
                    spacing: 10

                    Text {
                        Layout.fillWidth: true
                        text: (accessDraft.id || "").length > 0 ? "编辑访问项" : "新增访问项"
                        color: theme.titleInk
                        font.family: theme.uiFont
                        font.pixelSize: 15
                        font.weight: 700
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        ControlPanelSettingsInput {
                            id: accessNameInput
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

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 126

                    Rectangle {
                        anchors.fill: parent
                        radius: 8
                        color: otpDropArea.containsDrag ? theme.accentSoft : theme.panelAltBg
                        border.width: 1
                        border.color: otpDropArea.containsDrag ? theme.accent : theme.panelLine
                    }

                    DropArea {
                        id: otpDropArea
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
                            root.importDroppedOtpConfig(drop.urls)
                            drop.acceptProposedAction()
                        }
                    }

                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.importOtpConfig()
                        }

                        Column {
                            anchors.centerIn: parent
                            width: parent.width - 32
                            spacing: 6

                            Text {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: root.hasOtpDraftDisplay()
                                    ? ((accessDraft.otpConfig || "").length > 0 ? "已导入 OTP 配置" : "已保存 OTP 配置")
                                    : (otpDropArea.containsDrag ? "释放即可导入 OTP 二维码" : "将二维码拖到此处，或直接粘贴")
                                color: theme.accent
                                font.family: theme.uiFont
                                font.pixelSize: 14
                                font.weight: 700
                                elide: Text.ElideRight
                            }

                            Text {
                                visible: root.hasOtpDraftDisplay()
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: accessDraft.otpImportSummary || "已解析 OTP 配置"
                                color: theme.labelInk
                                font.family: theme.uiFont
                                font.pixelSize: 11
                                elide: Text.ElideMiddle
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        Layout.fillWidth: true
                        text: "点击上传框选择图片，也可拖拽二维码图片或按 Ctrl+V 粘贴"
                        color: theme.labelInk
                        font.family: theme.uiFont
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }

                    ControlPanelSettingsCheckBox {
                        theme: root.theme
                        checked: !!accessDraft.requiresOtp
                        text: "启用 OTP"
                        onToggled: {
                            var next = accessDraft
                            next.requiresOtp = checked
                            accessDraft = next
                        }
                    }
                }

                Rectangle {
                    visible: (accessDraft.otpConfig || "").length > 0
                    Layout.fillWidth: true
                    implicitHeight: otpPreviewRow.implicitHeight + 20
                    radius: 8
                    color: theme.inputBg
                    border.width: 1
                    border.color: theme.panelLine

                    RowLayout {
                        id: otpPreviewRow
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 10

                        Rectangle {
                            visible: (accessDraft.otpPreviewUrl || "").length > 0
                            Layout.preferredWidth: 72
                            Layout.preferredHeight: 72
                            radius: 6
                            color: theme.panelAltBg
                            border.width: 1
                            border.color: theme.panelLine
                            clip: true

                            Image {
                                anchors.fill: parent
                                anchors.margins: 5
                                source: accessDraft.otpPreviewUrl || ""
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                cache: false
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                Layout.fillWidth: true
                                text: accessDraft.otpImportSummary || "已解析 OTP 配置"
                                color: theme.titleInk
                                font.family: theme.uiFont
                                font.pixelSize: 12
                                font.weight: 700
                                elide: Text.ElideRight
                            }

                            ControlPanelSettingsArea {
                                theme: root.theme
                                Layout.fillWidth: true
                                Layout.preferredHeight: 56
                                readOnly: true
                                selectByMouse: true
                                text: accessDraft.otpConfig || ""
                                wrapMode: TextEdit.WrapAnywhere
                                color: theme.bodyInk
                                background: Rectangle {
                                    radius: theme.radiusSm || 6
                                    color: theme.panelAltBg
                                    border.width: 0
                                }
                            }
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

                ControlPanelSettingsSpinBox {
                    theme: root.theme
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

            ControlPanelSettingsArea {
                theme: root.theme
                Layout.fillWidth: true
                Layout.preferredHeight: 70
                text: accessDraft.note || ""
                placeholderText: "备注"
                onTextChanged: {
                    var next = accessDraft
                    next.note = text
                    accessDraft = next
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 18

                ControlPanelSettingsCheckBox {
                    theme: root.theme
                    checked: !!accessDraft.isActive
                    text: "启用访问项"
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
                    primary: true
                    strokeWidth: 0
                    onClicked: root.saveAccess()
                }
            }
        }
        }
    }
}
}

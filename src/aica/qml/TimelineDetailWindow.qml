import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtWebEngine

Item {
    id: root
    width: 860
    height: 632

    readonly property var themeTokens: typeof theme !== "undefined" ? theme : ({})
    readonly property var detailBridge: typeof todoDetailBridge === "undefined" ? null : todoDetailBridge
    readonly property var windowBridge: typeof timelineDetailWindowBridge === "undefined" ? null : timelineDetailWindowBridge
    readonly property string uiFont: root.themeTokens.uiFont || (root.detailBridge ? root.detailBridge.uiFont : (Qt.platform.os === "osx" ? "PingFang SC" : "Microsoft YaHei UI"))
    readonly property color windowBg: root.themeTokens.panelBg || "#F7F8FA"
    readonly property color toolbarBg: root.themeTokens.panelBg || "#FFFFFF"
    readonly property color toolbarLine: root.themeTokens.panelLine || "#E7EBF0"
    readonly property color editorBg: root.themeTokens.formFieldBg || root.themeTokens.inputBg || "#FFFFFF"
    readonly property color editorInk: root.themeTokens.bodyInk || "#26364B"
    readonly property color titleInk: root.themeTokens.titleInk || "#536173"
    readonly property color labelInk: root.themeTokens.labelInk || "#9AA6B5"
    readonly property color mutedInk: root.themeTokens.mutedInk || root.themeTokens.labelInk || "#9AA6B5"
    readonly property color accent: root.themeTokens.accent || "#26364B"
    readonly property color accentTint: root.themeTokens.accentTint || "#EAF1FF"
    readonly property color hoverBg: root.themeTokens.hoverBg || "#F1F4F8"
    readonly property color fieldLine: root.themeTokens.formFieldBorder || root.themeTokens.fieldLine || "#E7EBF0"
    readonly property color fieldFocusLine: root.themeTokens.formFieldFocusBorder || root.themeTokens.accent || "#B8CDF6"
    readonly property color buttonDefaultBg: root.themeTokens.buttonDefaultBg || "#FFFFFF"
    readonly property color buttonDisabledBg: root.themeTokens.buttonDisabledBg || root.themeTokens.panelAltBg || "#FFFFFF"
    readonly property color buttonDefaultInk: root.themeTokens.buttonDefaultInk || root.editorInk
    readonly property color scrollbarFill: root.themeTokens.mutedInk || "#BEC6D2"
    readonly property color warningFill: root.themeTokens.warningBg || "#FFF4D6"
    readonly property color warningInk: root.themeTokens.warningInk || "#8A5A00"
    readonly property bool detailBusy: root.detailBridge ? root.detailBridge.timelineDetailBusy : false
    readonly property string detailError: root.detailBridge ? root.detailBridge.timelineDetailError : ""
    readonly property string detailEventId: root.detailBridge ? root.detailBridge.timelineDetailEventId : ""
    readonly property bool isMac: Qt.platform.os === "osx"
    readonly property bool hasTimelineSummary: root.detailBridge ? root.detailBridge.timelineDetailSummary.trim().length > 0 : false
    readonly property int pageMargin: 20
    readonly property int editorRadius: 12
    readonly property bool pinned: root.windowBridge ? root.windowBridge.pinned : false
    property bool syncingEditor: false
    property bool previewMode: false
    property bool summaryExpanded: false
    property string previewHtml: ""

    function loadPreviewHtml() {
        if (!root.previewMode || !markdownPreview) {
            return
        }
        markdownPreview.loadHtml(root.previewHtml, "about:blank")
    }

    function refreshPreviewHtml() {
        if (!root.detailBridge) {
            root.previewHtml = ""
            return
        }
        root.previewHtml = root.detailBridge.renderTimelineDetailMarkdown(root.detailBridge.timelineDetailText)
    }

    function syncEditorText() {
        if (!root.detailBridge || markdownEditor.text === root.detailBridge.timelineDetailText) {
            return
        }
        syncingEditor = true
        markdownEditor.text = root.detailBridge.timelineDetailText
        syncingEditor = false
    }

    function persistEditor() {
        if (!root.detailBridge || syncingEditor) {
            return
        }
        root.detailBridge.updateTimelineDetailText(markdownEditor.text)
        root.detailBridge.saveTimelineDetail()
    }

    Shortcut {
        sequences: [ StandardKey.Save ]
        context: Qt.WindowShortcut
        enabled: !!root.detailBridge
        onActivated: root.persistEditor()
    }

    Connections {
        target: root.detailBridge
        function onDataChanged() {
            if (root.previewMode) {
                root.refreshPreviewHtml()
            }
            root.syncEditorText()
        }
    }

    onPreviewHtmlChanged: Qt.callLater(root.loadPreviewHtml)
    onPreviewModeChanged: Qt.callLater(root.loadPreviewHtml)

    Component.onCompleted: {
        syncEditorText()
        markdownEditor.forceActiveFocus()
    }

    component IconButton: Rectangle {
        id: buttonRoot
        property bool active: false
        property bool buttonEnabled: true
        property color iconColor: buttonRoot.active ? root.accent : root.mutedInk
        signal clicked()

        width: 30
        height: 30
        radius: 15
        color: !buttonRoot.buttonEnabled ? root.buttonDisabledBg : (buttonRoot.active ? root.accentTint : (buttonMouse.containsMouse ? root.hoverBg : root.buttonDefaultBg))
        border.width: buttonRoot.active ? 1 : 0
        border.color: buttonRoot.active ? root.fieldFocusLine : "transparent"
        opacity: buttonRoot.buttonEnabled ? 1.0 : 0.45

        MouseArea {
            id: buttonMouse
            anchors.fill: parent
            enabled: buttonRoot.buttonEnabled
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: buttonRoot.clicked()
        }
    }

    Rectangle {
        id: windowShell
        anchors.fill: parent
        radius: 12
        color: root.windowBg
        clip: true
    }

    Item {
        id: titleBar
        anchors.left: windowShell.left
        anchors.right: windowShell.right
        anchors.top: windowShell.top
        height: 42

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
            onPressed: function(mouse) {
                root.windowBridge.beginPanelDrag(mouse.x, mouse.y)
            }
            onPositionChanged: function(mouse) {
                if (mouse.buttons & Qt.LeftButton) {
                    root.windowBridge.updatePanelDrag()
                }
            }
            onReleased: root.windowBridge.finishPanelDrag()
            onCanceled: root.windowBridge.finishPanelDrag()
        }

        Row {
            visible: root.isMac
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            spacing: 9

            Repeater {
                model: [
                    {"fill": "#FF5F57", "action": "close"},
                    {"fill": "#FFBD2E", "action": "minimize"},
                    {"fill": "#28C840", "action": "maximize"}
                ]

                Rectangle {
                    width: 13
                    height: 13
                    radius: 6.5
                    color: modelData.fill

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (modelData.action === "close") {
                                root.detailBridge.closeTimelineDetail()
                            } else if (modelData.action === "minimize") {
                                root.windowBridge.showMinimized()
                            } else {
                                root.windowBridge.toggleMaximized()
                            }
                        }
                    }
                }
            }
        }

        Row {
            visible: !root.isMac
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            spacing: 0

            Repeater {
                model: [
                    {"label": "−", "action": "minimize"},
                    {"label": "□", "action": "maximize"},
                    {"label": "×", "action": "close"}
                ]

                Rectangle {
                    width: 46
                    height: parent.height
                    color: windowButtonMouse.containsMouse ? (modelData.action === "close" ? "#E81123" : "#E8ECF1") : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: windowButtonMouse.containsMouse && modelData.action === "close" ? "#FFFFFF" : "#536173"
                        font.family: root.uiFont
                        font.pixelSize: modelData.action === "maximize" ? 13 : 18
                    }

                    MouseArea {
                        id: windowButtonMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (modelData.action === "close") {
                                root.detailBridge.closeTimelineDetail()
                            } else if (modelData.action === "minimize") {
                                root.windowBridge.showMinimized()
                            } else {
                                root.windowBridge.toggleMaximized()
                            }
                        }
                    }
                }
            }
        }

        Text {
            anchors.left: parent.left
            anchors.leftMargin: root.isMac ? 92 : 18
            anchors.right: parent.right
            anchors.rightMargin: root.isMac ? 68 : 196
            anchors.verticalCenter: parent.verticalCenter
            text: "详细记录.md"
            color: root.titleInk
            font.family: root.uiFont
            font.pixelSize: 13
            font.weight: 600
            elide: Text.ElideRight
        }

        IconButton {
            id: pinButton
            anchors.right: parent.right
            anchors.rightMargin: root.isMac ? 16 : 146
            anchors.verticalCenter: parent.verticalCenter
            active: root.pinned
            onClicked: {
                if (root.windowBridge) {
                    root.windowBridge.togglePinned()
                }
            }

            Shape {
                anchors.centerIn: parent
                width: 15
                height: 15
                scale: 0.9
                layer.enabled: true

                ShapePath {
                    strokeWidth: 0
                    fillColor: pinButton.iconColor
                    startX: 11.214
                    startY: 0.3

                    PathSvg {
                        path: "M11.214 0.3l3.444 3.296c0.449 0.3 0.449 0.899 0.15 1.348-0.449 0.45-1.048 0.45-1.347 0.15l-0.15-0.149-0.3-0.3-3.444 4.944 1.048 1.049c0.299 0.449 0.299 1.048-0.15 1.347-0.299 0.3-0.748 0.3-1.197 0L3 5.989c-0.3-0.449-0.3-0.898 0-1.347 0.299-0.3 0.898-0.3 1.197 0l1.048 1.048 4.944-3.444-0.15-0.15C9.566 1.219 9.566 0.77 9.865 0.3c0.3-0.299 0.898-0.449 1.348 0zM6.148 10.443l-1.198-1.198c-1.048 1.198-2.695 2.995-2.995 3.444-0.449 0.45-0.748 1.048-1.048 1.647 0.749-0.15 1.348-0.449 1.797-0.898 0.45-0.3 2.246-1.947 3.444-2.995z"
                    }
                }
            }
        }
    }

    Rectangle {
        id: toolbar
        anchors.left: windowShell.left
        anchors.right: windowShell.right
        anchors.top: titleBar.bottom
        anchors.leftMargin: root.pageMargin
        anchors.rightMargin: root.pageMargin
        height: 42
        radius: 8
        color: root.toolbarBg

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Text {
                text: root.detailBusy ? "正在润色..." : "Markdown"
                color: root.mutedInk
                font.family: root.uiFont
                font.pixelSize: 12
            }

            Rectangle {
                width: 1
                height: 16
                color: root.toolbarLine
            }

            Text {
                text: root.previewMode ? "编辑" : "预览"
                color: root.titleInk
                font.family: root.uiFont
                font.pixelSize: 12
                font.weight: 500

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.previewMode) {
                            root.syncEditorText()
                            root.previewMode = false
                            markdownEditor.forceActiveFocus()
                        } else {
                            root.refreshPreviewHtml()
                            root.previewMode = true
                        }
                    }
                }
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            IconButton {
                id: polishButton
                active: false
                buttonEnabled: root.detailBridge && !root.detailBusy && markdownEditor.text.trim().length > 0
                iconColor: root.detailBusy ? root.mutedInk : root.accent
                onClicked: {
                    root.detailBridge.requestTimelinePolish(root.detailEventId)
                }

                Shape {
                    visible: !root.detailBusy
                    anchors.centerIn: parent
                    width: 16
                    height: 16
                    scale: 0.95
                    layer.enabled: true

                    ShapePath {
                        strokeWidth: 0
                        fillColor: polishButton.iconColor
                        startX: 12.888
                        startY: 10.75

                        PathSvg {
                            path: "M12.888 10.75l0.007 0.117c0.056 0.499 0.465 0.897 0.984 0.952l0.121 0.006c0.4 0 0.4 0.6 0 0.6-0.616 0-1.112 0.483-1.112 1.075 0 0.4-0.6 0.4-0.6 0l-0.006-0.117c-0.06-0.537-0.53-0.958-1.106-0.958l-0.08-0.009c-0.317-0.074-0.291-0.591 0.08-0.591l0.122-0.006c0.558-0.059 0.99-0.517 0.99-1.069l0.009-0.08c0.074-0.318 0.591-0.291 0.591 0.08zM6.735 3.875l0.005 0.192c0.1 1.847 1.625 3.331 3.532 3.428l0.199 0.005c0.666 0 0.666 1 0 1-2.066 0-3.736 1.626-3.736 3.625 0 0.667-1 0.667-1 0l-0.005-0.192C5.627 9.773 4 8.25 2 8.25l-0.105-0.009c-0.56-0.099-0.525-0.991 0.105-0.991l0.199-0.005c1.973-0.1 3.536-1.685 3.536-3.62l0.01-0.105c0.098-0.56 0.99-0.525 0.99 0.105z m5.852 7.82l-0.063 0.087a1.704 1.704 0 0 1-0.293 0.287l-0.08 0.055 0.08 0.055c0.109 0.084 0.207 0.18 0.293 0.287l0.063 0.086 0.066-0.086a1.704 1.704 0 0 1 0.293-0.287l0.078-0.055-0.078-0.055a1.704 1.704 0 0 1-0.293-0.287l-0.066-0.087zM6.235 5.943l-0.048 0.094a4.703 4.703 0 0 1-1.976 1.929l-0.071 0.034 0.071 0.034a4.703 4.703 0 0 1 1.976 1.929l0.048 0.093 0.048-0.093A4.703 4.703 0 0 1 8.259 8.034l0.069-0.034-0.07-0.034a4.703 4.703 0 0 1-1.975-1.929l-0.048-0.094zM12.888 2.5l0.007 0.117c0.056 0.499 0.465 0.897 0.984 0.952l0.121 0.006c0.4 0 0.4 0.6 0 0.6-0.616 0-1.112 0.483-1.112 1.075 0 0.4-0.6 0.4-0.6 0l-0.006-0.117c-0.06-0.537-0.53-0.958-1.106-0.958l-0.08-0.009c-0.317-0.074-0.291-0.591 0.08-0.591l0.122-0.006c0.558-0.059 0.99-0.517 0.99-1.069l0.009-0.08c0.074-0.318 0.591-0.291 0.591 0.08z m-0.3 0.946l-0.064 0.087a1.704 1.704 0 0 1-0.293 0.287l-0.08 0.055 0.08 0.055c0.109 0.084 0.207 0.18 0.293 0.287l0.063 0.086 0.066-0.086a1.704 1.704 0 0 1 0.293-0.287l0.078-0.055-0.078-0.055a1.704 1.704 0 0 1-0.293-0.287l-0.066-0.087z"
                        }
                    }
                }

                Text {
                    visible: root.detailBusy
                    anchors.centerIn: parent
                    text: "..."
                    color: root.mutedInk
                    font.family: root.uiFont
                    font.pixelSize: 12
                    font.weight: 700
                }
            }
        }
    }

    Rectangle {
        id: editorFrame
        anchors.left: windowShell.left
        anchors.right: windowShell.right
        anchors.top: toolbar.bottom
        anchors.bottom: windowShell.bottom
        anchors.leftMargin: root.pageMargin
        anchors.rightMargin: root.pageMargin
        anchors.topMargin: 14
        anchors.bottomMargin: 18
        radius: root.editorRadius
        color: root.editorBg
        clip: true

        Rectangle {
            anchors.fill: parent
            radius: root.editorRadius
            color: root.editorBg
        }

        Rectangle {
            id: summaryPanel
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 46
            anchors.rightMargin: 46
            anchors.topMargin: 20
            readonly property real collapsedHeight: 28
            readonly property real expandedBodyHeight: Math.min(156, summaryExpandedText.implicitHeight + 8)
            readonly property real expandedHeight: 28 + 18 + expandedBodyHeight
            height: root.hasTimelineSummary ? (root.summaryExpanded ? expandedHeight : collapsedHeight) : 0
            color: "transparent"
            opacity: root.hasTimelineSummary ? 1 : 0
            visible: root.hasTimelineSummary
            clip: false

            Item {
                id: summaryToggleRow
                anchors.left: parent.left
                anchors.top: parent.top
                width: 180
                height: 24

                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.summaryExpanded ? "⌄" : "›"
                    color: root.titleInk
                    font.family: root.uiFont
                    font.pixelSize: 16
                    font.weight: 600
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 28
                    anchors.verticalCenter: parent.verticalCenter
                    text: "已生成摘要"
                    color: root.titleInk
                    font.family: root.uiFont
                    font.pixelSize: 14
                    font.weight: 600
                }

                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.summaryExpanded = !root.summaryExpanded
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.top: summaryToggleRow.bottom
                anchors.topMargin: 12
                width: 3
                height: summaryPanel.expandedBodyHeight
                radius: 1.5
                color: root.fieldLine
                visible: root.summaryExpanded
            }

            Item {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: summaryToggleRow.bottom
                anchors.topMargin: 12
                anchors.leftMargin: 22
                height: summaryPanel.expandedBodyHeight
                clip: true
                visible: root.summaryExpanded

                Text {
                    id: summaryExpandedText
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    text: root.detailBridge ? root.detailBridge.timelineDetailSummary : ""
                    color: root.mutedInk
                    font.family: root.uiFont
                    font.pixelSize: 14
                    lineHeight: 1.5
                    lineHeightMode: Text.ProportionalHeight
                    wrapMode: Text.WordWrap
                }
            }
        }

        ScrollView {
            id: editorScroll
            anchors.fill: parent
            anchors.leftMargin: 46
            anchors.rightMargin: 46
            anchors.topMargin: root.hasTimelineSummary ? summaryPanel.height + 22 : 38
            anchors.bottomMargin: 38
            clip: true
            enabled: !root.previewMode
            opacity: root.previewMode ? 0 : 1
            z: root.previewMode ? 0 : 1

            TextArea {
                id: markdownEditor
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                clip: true
                textFormat: TextEdit.PlainText
                color: root.editorInk
                selectedTextColor: root.themeTokens.buttonPrimaryInk || "#FFFFFF"
                selectionColor: root.accentTint
                font.family: root.uiFont
                font.pixelSize: 16
                font.weight: 400
                leftPadding: 0
                rightPadding: 0
                topPadding: 0
                bottomPadding: 0
                background: null
                cursorVisible: activeFocus
                cursorDelegate: Rectangle {
                    width: 1.5
                    color: root.accent
                    visible: markdownEditor.activeFocus
                }
                onTextChanged: {
                    if (!root.syncingEditor) {
                        root.detailBridge.updateTimelineDetailText(text)
                    }
                }
            }
        }

        Item {
            id: previewScroll
            anchors.fill: parent
            anchors.leftMargin: 46
            anchors.rightMargin: 46
            anchors.topMargin: root.hasTimelineSummary ? summaryPanel.height + 22 : 38
            anchors.bottomMargin: 38
            clip: true
            enabled: root.previewMode
            opacity: root.previewMode ? 1 : 0
            z: root.previewMode ? 1 : 0

            WebEngineView {
                id: markdownPreview
                anchors.fill: parent
                focus: false
                backgroundColor: root.editorBg
            }
        }

        Rectangle {
            id: errorBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 30
            color: root.warningFill
            visible: root.detailError.length > 0

            Text {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                verticalAlignment: Text.AlignVCenter
                text: root.detailError
                color: root.warningInk
                elide: Text.ElideRight
                font.family: root.uiFont
                font.pixelSize: 12
            }
        }
    }
}

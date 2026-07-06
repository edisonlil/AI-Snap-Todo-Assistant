import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: rootField
    required property var theme
    property string label: ""
    property string value: ""
    property string placeholderText: "未填写"
    property bool editable: false
    property bool editing: false
    property bool saving: false
    property bool loading: false
    property bool hasMore: false
    property bool compact: false
    property var options: []
    property string errorText: ""
    property string filterText: ""
    property bool actionVisible: false
    property bool actionBusy: false
    property string actionIconSource: ""
    property bool committingSelection: false
    readonly property bool loadingMore: rootField.loading && rootField.options.length > 0

    readonly property color titleInk: resolveThemeColor("titleInk", "#18202E")
    readonly property color labelInk: resolveThemeColor("labelInk", "#7C8795")
    readonly property color accent: resolveThemeColor("accent", "#2A313F")
    readonly property color accentTint: resolveThemeColor("accentTint", "#ECEFF3")
    readonly property color hoverBg: resolveThemeColor("hoverBg", "#F3F4F6")
    readonly property color panelBg: resolveThemeColor("panelBg", "#FFFFFF")
    readonly property color panelAltBg: resolveThemeColor("panelAltBg", "#F5F5F5")
    readonly property color fieldBg: resolveThemeColor("panelAltBg", resolveThemeColor("fieldBg", "#F5F5F5"))
    readonly property color fieldLine: resolveThemeColor("formFieldBorder", resolveThemeColor("fieldLine", resolveThemeColor("panelLine", "#E5E7EB")))
    readonly property color fieldFocusLine: resolveThemeColor("formFieldFocusBorder", resolveThemeColor("accent", "#2A313F"))
    readonly property color popupBg: resolveThemeColor("panelAltBg", resolveThemeColor("fieldBg", "#F5F5F5"))
    readonly property string uiFont: theme && theme.uiFont ? theme.uiFont : "Microsoft YaHei UI"
    readonly property int formInlineEditHeight: theme && theme.formInlineEditHeight ? theme.formInlineEditHeight : 32
    readonly property int formPopupRadius: theme && theme.formPopupRadius ? theme.formPopupRadius : 8
    readonly property int formPopupItemRadius: theme && theme.formPopupItemRadius ? theme.formPopupItemRadius : 6
    readonly property int formPopupItemHeight: theme && theme.formPopupItemHeight ? theme.formPopupItemHeight : 30
    readonly property int popupOuterMargin: 12
    readonly property int popupPreferredHeight: 280
    readonly property int popupPreferredWidth: 460

    signal clicked
    signal accepted(string value)
    signal canceled
    signal actionTriggered
    signal searchRequested(string query)
    signal loadMoreRequested

    function resolveThemeColor(name, fallback) {
        return theme && theme[name] !== undefined ? theme[name] : fallback
    }

    function popupAnchorPoint() {
        if (!editorColumn) {
            return Qt.point(0, formInlineEditHeight + 8)
        }
        return editorColumn.mapToItem(rootField, 0, editorColumn.height + 8)
    }

    function popupParentItem() {
        return rootField
    }

    function popupOpenPoint() {
        return rootField.popupAnchorPoint()
    }

    function popupSceneOpenPoint() {
        if (!editorColumn) {
            return rootField.mapToItem(null, 0, formInlineEditHeight + 8)
        }
        return editorColumn.mapToItem(null, 0, editorColumn.height + 8)
    }

    function popupContentHeight() {
        return Math.min(popupColumn.implicitHeight + 8, popupPreferredHeight)
    }

    function popupWidthValue() {
        var preferred = Math.max(320, Math.min(rootField.width - 12, popupPreferredWidth))
        return preferred
    }

    function popupXPosition() {
        return popupOpenPoint().x
    }

    function popupViewportHeight() {
        if (Overlay.overlay && Overlay.overlay.height) {
            return Overlay.overlay.height
        }
        if (rootField.parent && rootField.parent.height) {
            return rootField.parent.height
        }
        return popupPreferredHeight
    }

    function popupSpaceBelow() {
        return Math.max(0, popupViewportHeight() - popupSceneOpenPoint().y - popupOuterMargin)
    }

    function popupHeightValue() {
        var desiredHeight = popupContentHeight()
        var availableHeight = popupSpaceBelow()
        if (availableHeight <= 0) {
            return desiredHeight
        }
        return Math.min(desiredHeight, availableHeight)
    }

    function popupYPosition() {
        return popupOpenPoint().y
    }

    function optionText(option) {
        return String(option && (option.text || option.value) || "")
    }

    function optionValue(option) {
        return String(option && option.value || "")
    }

    function normalizedFilterText() {
        return String(rootField.filterText || "").trim()
    }

    function hasExactOptionMatch(rawValue) {
        var normalized = String(rawValue || "").trim()
        if (!normalized.length) {
            return false
        }
        for (var index = 0; index < rootField.options.length; index += 1) {
            var option = rootField.options[index]
            if (rootField.optionValue(option) === normalized || rootField.optionText(option) === normalized) {
                return true
            }
        }
        return false
    }

    function shouldShowManualSubmit() {
        return rootField.normalizedFilterText().length > 0 && !rootField.hasExactOptionMatch(rootField.filterText)
    }

    function commitOption(option) {
        if (!option) {
            return
        }
        committingSelection = true
        popup.close()
        rootField.accepted(String(option.value || ""))
    }

    function commitManualValue(rawValue) {
        var normalized = String(rawValue || "").trim()
        if (!normalized.length) {
            return
        }
        committingSelection = true
        popup.close()
        rootField.accepted(normalized)
    }

    function submitSearchInput() {
        if (rootField.shouldShowManualSubmit()) {
            rootField.commitManualValue(rootField.filterText)
            return
        }
        for (var index = 0; index < rootField.options.length; index += 1) {
            var option = rootField.options[index]
            if (
                rootField.optionValue(option) === rootField.normalizedFilterText()
                || rootField.optionText(option) === rootField.normalizedFilterText()
            ) {
                rootField.commitOption(option)
                return
            }
        }
    }

    onEditingChanged: {
        if (!editing) {
            committingSelection = false
            filterText = ""
            searchDebounce.stop()
            popup.close()
            return
        }
        Qt.callLater(function() {
            if (!rootField.editing) {
                return
            }
            filterText = ""
            popup.open()
            rootField.searchRequested("")
            searchInput.forceActiveFocus()
        })
    }

    radius: 0
    color: "transparent"
    border.width: 0
    implicitHeight: fieldColumn.implicitHeight + 14

    Timer {
        id: searchDebounce
        interval: 250
        repeat: false
        onTriggered: rootField.searchRequested(rootField.filterText)
    }

    ColumnLayout {
        id: fieldColumn
        anchors.fill: parent
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        anchors.topMargin: 4
        anchors.bottomMargin: 10
        spacing: 5

        Text {
            Layout.fillWidth: true
            text: rootField.label
            color: rootField.labelInk
            font.family: rootField.uiFont
            font.pixelSize: 10
            font.weight: 500
            elide: Text.ElideRight
            opacity: 0.72
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: rootField.editing ? editorColumn.implicitHeight : valueRow.implicitHeight

            RowLayout {
                id: valueRow
                anchors.left: parent.left
                anchors.right: parent.right
                visible: !rootField.editing
                spacing: 8

                BusyIndicator {
                    visible: rootField.saving || rootField.actionBusy
                    running: rootField.saving || rootField.actionBusy
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                }

                Item {
                    Layout.fillWidth: true
                    implicitHeight: valueText.implicitHeight

                    Text {
                        id: valueText
                        anchors.left: parent.left
                        anchors.right: actionRow.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: actionRow.width > 0 ? 10 : 0
                        text: rootField.value.length > 0 ? rootField.value : rootField.placeholderText
                        color: rootField.value.length > 0 ? rootField.titleInk : rootField.labelInk
                        font.family: rootField.uiFont
                        font.pixelSize: rootField.compact ? 12 : 13
                        font.weight: rootField.value.length > 0 ? 500 : 400
                        elide: Text.ElideRight
                    }

                    MouseArea {
                        id: hoverArea
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: rootField.editable && !rootField.saving && !rootField.actionBusy
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: rootField.clicked()
                    }

                    Row {
                        id: actionRow
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        visible: rootField.actionVisible || (rootField.editable && hoverArea.containsMouse && !rootField.saving && !rootField.actionBusy)
                        width: visible ? implicitWidth : 0

                        Rectangle {
                            visible: rootField.actionVisible
                            implicitWidth: rootField.compact ? 18 : 20
                            implicitHeight: implicitWidth
                            radius: implicitWidth / 2
                            color: actionHover.containsMouse ? rootField.hoverBg : "#FFFFFF"
                            border.width: 1
                            border.color: rootField.fieldLine

                            BusyIndicator {
                                anchors.centerIn: parent
                                width: 12
                                height: 12
                                visible: rootField.actionBusy
                                running: rootField.actionBusy
                            }

                            Image {
                                anchors.centerIn: parent
                                width: 12
                                height: 12
                                visible: !rootField.actionBusy
                                source: rootField.actionIconSource
                                fillMode: Image.PreserveAspectFit
                            }

                            MouseArea {
                                id: actionHover
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: !rootField.actionBusy
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: rootField.actionTriggered()
                            }
                        }

                        Text {
                            visible: rootField.editable && hoverArea.containsMouse && !rootField.actionBusy && !rootField.saving
                            text: "\u270e"
                            color: rootField.accent
                            font.family: rootField.uiFont
                            font.pixelSize: 11
                            opacity: 0.75
                        }
                    }
                }
            }

            ColumnLayout {
                id: editorColumn
                anchors.left: parent.left
                anchors.right: parent.right
                visible: rootField.editing
                spacing: 6

                Control {
                    Layout.fillWidth: true
                    Layout.preferredHeight: rootField.formInlineEditHeight
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 0

                    background: Rectangle {
                        color: "transparent"
                        border.width: 0
                    }

                    Text {
                        anchors.left: parent.left
                        anchors.right: arrow.left
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: rootField.value.length > 0 ? rootField.value : rootField.placeholderText
                        color: rootField.value.length > 0 ? rootField.titleInk : rootField.labelInk
                        font.family: rootField.uiFont
                        font.pixelSize: rootField.compact ? 11 : 12
                        elide: Text.ElideRight
                    }

                    Canvas {
                        id: arrow
                        anchors.right: parent.right
                        anchors.rightMargin: 2
                        anchors.verticalCenter: parent.verticalCenter
                        width: 8
                        height: 5
                        contextType: "2d"
                        onPaint: {
                            context.reset()
                            context.moveTo(0, 0)
                            context.lineTo(width, 0)
                            context.lineTo(width / 2, height)
                            context.closePath()
                            context.fillStyle = rootField.labelInk
                            context.fill()
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: popup.opened ? rootField.fieldFocusLine : rootField.fieldLine
                        opacity: 0.95
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: popup.open()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignLeft
                    spacing: 10

                    Text {
                        text: "取消"
                        color: rootField.labelInk
                        font.family: rootField.uiFont
                        font.pixelSize: 11
                        font.weight: 500
                        opacity: 0.88

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                rootField.committingSelection = true
                                popup.close()
                                rootField.canceled()
                            }
                        }
                    }
                }

                Popup {
                    id: popup
                    parent: rootField.popupParentItem()
                    x: rootField.popupXPosition()
                    y: rootField.popupYPosition()
                    width: rootField.popupWidthValue()
                    height: rootField.popupHeightValue()
                    modal: false
                    focus: true
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                    padding: 0

                    background: Rectangle {
                        radius: rootField.formPopupRadius
                        color: rootField.popupBg
                        border.width: 1
                        border.color: rootField.fieldLine
                    }

                    contentItem: Rectangle {
                        clip: true
                        color: rootField.fieldBg
                        border.width: 1
                        border.color: rootField.fieldLine
                        radius: rootField.formPopupItemRadius

                        ColumnLayout {
                            id: popupColumn
                            anchors.fill: parent
                            anchors.margins: 4
                            spacing: 4

                            TextField {
                                id: searchInput
                                Layout.fillWidth: true
                                Layout.preferredHeight: rootField.formInlineEditHeight
                                placeholderText: "输入关键字搜索功能点"
                                text: rootField.filterText
                                color: rootField.titleInk
                                font.family: rootField.uiFont
                                font.pixelSize: rootField.compact ? 11 : 12
                                selectByMouse: true

                                background: Rectangle {
                                    radius: rootField.formPopupItemRadius
                                    color: rootField.panelBg
                                    border.width: 1
                                    border.color: rootField.fieldLine
                                }

                                onTextEdited: {
                                    rootField.filterText = text
                                    searchDebounce.restart()
                                }
                                onAccepted: rootField.submitSearchInput()
                                Keys.onEscapePressed: {
                                    rootField.committingSelection = true
                                    popup.close()
                                    rootField.canceled()
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                visible: rootField.loading && rootField.options.length === 0
                                spacing: 8

                                BusyIndicator {
                                    running: true
                                    Layout.preferredWidth: 16
                                    Layout.preferredHeight: 16
                                }

                                Text {
                                    text: rootField.options.length > 0 ? "正在加载更多功能点..." : "正在搜索功能点..."
                                    color: rootField.labelInk
                                    font.family: rootField.uiFont
                                    font.pixelSize: 11
                                }
                            }

                            Rectangle {
                                Layout.fillWidth: true
                                visible: rootField.shouldShowManualSubmit()
                                implicitHeight: manualLabel.implicitHeight + 16
                                radius: rootField.formPopupItemRadius
                                color: manualMouseArea.containsMouse ? rootField.hoverBg : rootField.panelBg
                                border.width: 1
                                border.color: rootField.fieldLine

                                Text {
                                    id: manualLabel
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "直接填写：" + rootField.normalizedFilterText()
                                    color: rootField.accent
                                    font.family: rootField.uiFont
                                    font.pixelSize: rootField.compact ? 11 : 12
                                    font.weight: 600
                                    elide: Text.ElideRight
                                }

                                MouseArea {
                                    id: manualMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: rootField.commitManualValue(rootField.filterText)
                                }
                            }

                            ListView {
                                id: optionList
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.minimumHeight: rootField.formPopupItemHeight * 3
                                Layout.preferredHeight: Math.min(contentHeight, 212)
                                visible: rootField.normalizedFilterText().length > 0 && options.length > 0
                                clip: true
                                interactive: true
                                boundsBehavior: Flickable.StopAtBounds
                                flickableDirection: Flickable.VerticalFlick
                                reuseItems: true
                                cacheBuffer: rootField.formPopupItemHeight * 10
                                model: rootField.options
                                spacing: 2
                                function loadMoreTriggerDistance() {
                                    return Math.max(rootField.formPopupItemHeight * 6, height * 0.5)
                                }

                                function isNearLoadMoreEdge() {
                                    if (contentHeight <= height) {
                                        return true
                                    }
                                    return contentY + height + loadMoreTriggerDistance() >= contentHeight
                                }

                                function requestLoadMoreIfNeeded() {
                                    if (
                                        visible
                                        && rootField.hasMore
                                        && !rootField.loading
                                        && isNearLoadMoreEdge()
                                    ) {
                                        rootField.loadMoreRequested()
                                    }
                                }

                                onContentYChanged: requestLoadMoreIfNeeded()
                                onHeightChanged: requestLoadMoreIfNeeded()
                                onContentHeightChanged: requestLoadMoreIfNeeded()
                                onMovementEnded: {
                                    requestLoadMoreIfNeeded()
                                }

                                delegate: Rectangle {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: rootField.formPopupItemHeight
                                    radius: rootField.formPopupItemRadius
                                    color: String(modelData.value || "") === String(rootField.value || "")
                                           ? rootField.accentTint
                                           : itemMouseArea.containsMouse
                                             ? rootField.hoverBg
                                             : "transparent"

                                    Text {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.text || modelData.value || ""
                                        color: String(modelData.value || "") === String(rootField.value || "")
                                               ? rootField.accent
                                               : rootField.titleInk
                                        font.family: rootField.uiFont
                                        font.pixelSize: rootField.compact ? 11 : 12
                                        font.weight: String(modelData.value || "") === String(rootField.value || "") ? 600 : 400
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        id: itemMouseArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: rootField.commitOption(modelData)
                                    }
                                }

                                ScrollBar.vertical: ScrollBar {
                                    policy: optionList.contentHeight > optionList.height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                                }

                                footer: Item {
                                    width: optionList.width
                                    height: rootField.loadingMore ? rootField.formPopupItemHeight : 0
                                    visible: rootField.loadingMore

                                    Row {
                                        anchors.centerIn: parent
                                        spacing: 8

                                        BusyIndicator {
                                            running: rootField.loadingMore
                                            width: 16
                                            height: 16
                                        }

                                        Text {
                                            text: "正在加载更多功能点..."
                                            color: rootField.labelInk
                                            font.family: rootField.uiFont
                                            font.pixelSize: 11
                                        }
                                    }
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: rootField.errorText.length > 0
                                text: rootField.errorText
                                color: "#B42318"
                                font.family: rootField.uiFont
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: rootField.normalizedFilterText().length > 0
                                         && !rootField.loading
                                         && rootField.errorText.length === 0
                                         && rootField.options.length === 0
                                text: "未找到匹配项"
                                color: rootField.labelInk
                                font.family: rootField.uiFont
                                font.pixelSize: 11
                                horizontalAlignment: Text.AlignHCenter
                                topPadding: 8
                                bottomPadding: 8
                            }
                        }
                    }

                    onOpened: {
                        Qt.callLater(function() {
                            searchInput.forceActiveFocus()
                        })
                    }

                    onClosed: {
                        if (rootField.editing && !rootField.committingSelection) {
                            rootField.canceled()
                        }
                        rootField.committingSelection = false
                    }
                }
            }
        }

        Rectangle {
            visible: !rootField.editing
            Layout.fillWidth: true
            implicitHeight: 1
            color: rootField.fieldLine
            opacity: 0.85
        }
    }
}

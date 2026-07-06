import QtQuick
import QtQuick.Controls

ComboBox {
    id: combo
    required property var theme
    property int popupMaxHeight: 280
    property int popupItemMinHeight: theme.formPopupItemHeight || 38
    property int popupTextMaximumLineCount: 1
    property int fieldRadius: theme.componentRadius || theme.formFieldRadius || 8
    property int fieldFontSize: theme.formFieldFontSize || theme.fontBody || 12
    property color fieldBg: theme.formFieldBg || theme.inputBg || "#FFFFFF"
    property color fieldBorder: theme.formFieldBorder || theme.panelLine || "#E5E7EB"
    property color fieldFocusBorder: theme.formFieldFocusBorder || theme.accent || "#2A313F"
    property string filterText: ""

    function optionLabel(option) {
        if (option === null || option === undefined) {
            return ""
        }
        if (typeof option === "object") {
            return option.text || option.label || option.value || ""
        }
        return String(option)
    }

    function optionValue(option) {
        if (option === null || option === undefined) {
            return ""
        }
        if (typeof option === "object") {
            return option.value || option.text || option.label || ""
        }
        return String(option)
    }

    function optionDetails(option) {
        if (option === null || option === undefined || typeof option !== "object") {
            return ""
        }
        return option.details || ""
    }

    function sourceOptionAt(index) {
        var sourceModel = combo.model || []
        if (index < 0 || index >= sourceModel.length) {
            return null
        }
        return sourceModel[index]
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

    function filteredOptions() {
        var keyword = (combo.filterText || "").trim()
        var sourceModel = combo.model || []
        var matches = []
        for (var index = 0; index < sourceModel.length; index += 1) {
            var option = sourceModel[index]
            var label = combo.optionLabel(option)
            var value = combo.optionValue(option)
            var details = combo.optionDetails(option)
            if (
                !keyword.length
                || combo.fuzzyMatch(label, keyword)
                || combo.fuzzyMatch(value, keyword)
                || combo.fuzzyMatch(details, keyword)
            ) {
                matches.push({
                    sourceIndex: index,
                    label: label,
                    value: value,
                    details: details,
                })
            }
        }
        return matches
    }

    function filteredIndexForSourceIndex(sourceIndex) {
        var options = combo.filteredOptions()
        for (var index = 0; index < options.length; index += 1) {
            if (options[index].sourceIndex === sourceIndex) {
                return index
            }
        }
        return options.length > 0 ? 0 : -1
    }

    function exactSourceIndex(keyword) {
        var normalized = (keyword || "").trim().toLowerCase()
        var sourceModel = combo.model || []
        if (!normalized.length) {
            return combo.currentIndex
        }
        for (var index = 0; index < sourceModel.length; index += 1) {
            var option = sourceModel[index]
            if (
                combo.optionLabel(option).toLowerCase() === normalized
                || combo.optionValue(option).toLowerCase() === normalized
            ) {
                return index
            }
        }
        return -1
    }

    function syncInputText() {
        if (input.activeFocus && popup.visible) {
            return
        }
        combo.filterText = ""
        input.text = combo.optionLabel(combo.sourceOptionAt(combo.currentIndex))
    }

    function syncHighlightedIndex() {
        popupList.currentIndex = combo.filteredIndexForSourceIndex(combo.currentIndex)
        if (popupList.currentIndex >= 0) {
            popupList.positionViewAtIndex(popupList.currentIndex, ListView.Contain)
        }
    }

    function openPopup() {
        if (!popup.visible) {
            popup.open()
        }
        combo.syncHighlightedIndex()
    }

    function commitOptionAt(filteredIndex) {
        var options = combo.filteredOptions()
        if (filteredIndex < 0 || filteredIndex >= options.length) {
            return
        }
        var sourceIndex = options[filteredIndex].sourceIndex
        combo.currentIndex = sourceIndex
        combo.activated(sourceIndex)
        popup.close()
        combo.syncInputText()
    }

    function commitHighlightedOrExact() {
        var options = combo.filteredOptions()
        if (popup.visible && popupList.currentIndex >= 0 && popupList.currentIndex < options.length) {
            combo.commitOptionAt(popupList.currentIndex)
            return
        }
        var sourceIndex = combo.exactSourceIndex(input.text)
        if (sourceIndex >= 0) {
            combo.currentIndex = sourceIndex
            combo.activated(sourceIndex)
        }
        popup.close()
        combo.syncInputText()
    }

    function moveHighlight(step) {
        var options = combo.filteredOptions()
        if (!options.length) {
            popupList.currentIndex = -1
            combo.openPopup()
            return
        }
        combo.openPopup()
        if (popupList.currentIndex < 0) {
            popupList.currentIndex = step > 0 ? 0 : options.length - 1
        } else {
            popupList.currentIndex = (popupList.currentIndex + step + options.length) % options.length
        }
        popupList.positionViewAtIndex(popupList.currentIndex, ListView.Contain)
    }

    function dismissPopup() {
        popup.close()
        filterText = ""
        input.focus = false
    }

    textRole: "text"
    editable: true
    font.family: theme.uiFont
    font.pixelSize: fieldFontSize
    implicitHeight: theme.componentHeight || theme.formFieldHeight || 36
    leftPadding: theme.formFieldPaddingH || 14
    rightPadding: Math.max(34, (theme.formFieldPaddingH || 14) + 20)
    topPadding: theme.formFieldPaddingV || 11
    bottomPadding: theme.formFieldPaddingV || 11

    onCurrentIndexChanged: syncInputText()
    onModelChanged: syncInputText()
    Component.onCompleted: syncInputText()

    contentItem: TextField {
        id: input
        text: combo.optionLabel(combo.sourceOptionAt(combo.currentIndex))
        color: theme.titleInk
        font.family: theme.uiFont
        font.pixelSize: combo.fieldFontSize
        verticalAlignment: TextInput.AlignVCenter
        readOnly: !combo.editable
        selectByMouse: combo.editable
        cursorVisible: combo.editable && activeFocus
        leftPadding: 0
        rightPadding: 0
        topPadding: 0
        bottomPadding: 0
        background: Item {}

        onTextEdited: {
            combo.filterText = text
            combo.openPopup()
        }

        onActiveFocusChanged: {
            if (activeFocus) {
                combo.filterText = ""
                combo.openPopup()
                if (combo.editable) {
                    Qt.callLater(function() {
                        if (input.activeFocus) {
                            input.selectAll()
                        }
                    })
                }
                return
            }
            if (!popup.visible) {
                combo.syncInputText()
            }
        }

        onAccepted: combo.commitHighlightedOrExact()
        onEditingFinished: if (!popup.visible) combo.syncInputText()
        Keys.onEscapePressed: popup.close()
        Keys.onDownPressed: combo.moveHighlight(1)
        Keys.onUpPressed: combo.moveHighlight(-1)
    }

    MouseArea {
        anchors.fill: parent
        enabled: !combo.editable
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            input.forceActiveFocus()
            combo.filterText = ""
            if (popup.visible) {
                popup.close()
            } else {
                combo.openPopup()
            }
        }
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
            context.fillStyle = theme.labelInk
            context.fill()
        }
    }

    background: Rectangle {
        radius: combo.fieldRadius
        color: combo.fieldBg
        border.width: 1
        border.color: combo.activeFocus || combo.popup.visible ? combo.fieldFocusBorder : combo.fieldBorder
    }

    popup: Popup {
        id: popup
        y: combo.height + 6
        width: combo.width
        padding: 6
        modal: false
        focus: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        implicitHeight: Math.min(popupList.implicitHeight + topPadding + bottomPadding,
                                 combo.popupMaxHeight + topPadding + bottomPadding)
        onOpened: combo.syncHighlightedIndex()
        onClosed: {
            popupList.currentIndex = -1
            if (!input.activeFocus) {
                combo.syncInputText()
            }
        }

        background: Rectangle {
            radius: theme.formPopupRadius || 12
            color: theme.formPopupBg || "#FFFFFF"
            border.width: 1
            border.color: combo.fieldBorder
        }

        contentItem: ListView {
            id: popupList
            clip: true
            implicitHeight: Math.min(contentHeight, combo.popupMaxHeight)
            boundsBehavior: Flickable.StopAtBounds
            model: combo.popup.visible ? combo.filteredOptions() : null
            delegate: ItemDelegate {
                width: combo.width - combo.popup.leftPadding - combo.popup.rightPadding
                height: Math.max(combo.popupItemMinHeight, optionText.implicitHeight + 18)
                padding: 0
                highlighted: popupList.currentIndex === index

                background: Rectangle {
                    radius: theme.formPopupItemRadius || 8
                    color: highlighted ? theme.accentSoft : hovered ? (theme.formPopupHoverBg || theme.hoverBg || "#F6F8FB") : "transparent"
                }

                contentItem: Text {
                    id: optionText
                    leftPadding: 10
                    rightPadding: 10
                    text: modelData.label
                    color: theme.titleInk
                    font.family: theme.uiFont
                    font.pixelSize: combo.fieldFontSize
                    verticalAlignment: Text.AlignVCenter
                    wrapMode: Text.Wrap
                    maximumLineCount: combo.popupTextMaximumLineCount
                    elide: Text.ElideRight
                }

                onClicked: combo.commitOptionAt(index)
            }

            ScrollBar.vertical: ScrollBar {
                policy: popupList.contentHeight > popupList.height ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
            }
        }
    }
}

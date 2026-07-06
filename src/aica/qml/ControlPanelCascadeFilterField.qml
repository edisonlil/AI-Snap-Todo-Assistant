import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: rootField
    required property var theme
    property string value: ""
    property string placeholderText: "未填写"
    property var parsePathFn
    property var level1OptionsFn
    property var level2OptionsFn
    property var level3OptionsFn
    property string level1: ""
    property string level2: ""
    property string level3: ""
    property var level1Options: []
    property var level2Options: []
    property var level3Options: []
    property string filterText: ""

    readonly property color titleInk: resolveThemeColor("titleInk", "#18202E")
    readonly property color labelInk: resolveThemeColor("labelInk", "#7C8795")
    readonly property color mutedInk: resolveThemeColor("mutedInk", "#A9B1BD")
    readonly property color accent: resolveThemeColor("accent", "#2A313F")
    readonly property color accentTint: resolveThemeColor("accentTint", "#ECEFF3")
    readonly property color hoverBg: resolveThemeColor("hoverBg", "#F3F4F6")
    readonly property color fieldBg: resolveThemeColor("formFieldBg", resolveThemeColor("inputBg", "#FFFFFF"))
    readonly property color fieldLine: resolveThemeColor("formFieldBorder", resolveThemeColor("panelLine", "#E5E7EB"))
    readonly property color fieldFocusLine: resolveThemeColor("formFieldFocusBorder", resolveThemeColor("accent", "#2A313F"))
    readonly property color popupBg: resolveThemeColor("panelAltBg", "#F5F5F5")
    readonly property string uiFont: theme && theme.uiFont ? theme.uiFont : "Microsoft YaHei UI"
    readonly property int fieldRadius: theme && theme.componentRadius ? theme.componentRadius : 8
    readonly property int fieldHeight: theme && theme.componentHeight ? theme.componentHeight : 36
    readonly property int fieldFontSize: theme && theme.formFieldFontSize ? theme.formFieldFontSize : (theme && theme.fontBody ? theme.fontBody : 12)
    readonly property int popupRadius: theme && theme.formPopupRadius ? theme.formPopupRadius : 12
    readonly property int popupItemRadius: theme && theme.formPopupItemRadius ? theme.formPopupItemRadius : 8
    readonly property int popupItemHeight: theme && theme.formPopupItemHeight ? theme.formPopupItemHeight : 38
    readonly property int popupPadding: 0
    readonly property int popupMinWidth: 360
    readonly property int popupMaxWidth: 432
    readonly property int popupMaxHeight: 280

    signal accepted(string value)

    function resolveThemeColor(name, fallback) {
        return theme && theme[name] !== undefined ? theme[name] : fallback
    }

    function displayPath(rawValue) {
        var text = String(rawValue || "")
        if (!text) {
            return ""
        }
        return text.split("/").join(" / ")
    }

    function optionLabel(option) {
        return String(option && (option.text || option.value) || "")
    }

    function optionValue(option) {
        return String(option && option.value || "")
    }

    function fuzzyMatch(text, query) {
        var source = String(text || "").toLowerCase()
        var keyword = String(query || "").toLowerCase().trim()
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

    function searchablePaths() {
        var results = []
        var topOptions = level1OptionsFn ? level1OptionsFn() : level1Options
        for (var level1Index = 0; level1Index < topOptions.length; level1Index += 1) {
            var item1 = topOptions[level1Index]
            var value1 = optionValue(item1)
            var text1 = optionLabel(item1)
            var secondOptions = level2OptionsFn ? level2OptionsFn(value1) : []
            if (!secondOptions.length) {
                results.push({
                    level1: value1,
                    level2: "",
                    level3: "",
                    value: value1,
                    displayText: text1,
                })
                continue
            }
            for (var level2Index = 0; level2Index < secondOptions.length; level2Index += 1) {
                var item2 = secondOptions[level2Index]
                var value2 = optionValue(item2)
                var text2 = optionLabel(item2)
                var thirdOptions = level3OptionsFn ? level3OptionsFn(value1, value2) : []
                if (!thirdOptions.length) {
                    results.push({
                        level1: value1,
                        level2: value2,
                        level3: "",
                        value: value1 + "/" + value2,
                        displayText: text1 + " / " + text2,
                    })
                    continue
                }
                for (var level3Index = 0; level3Index < thirdOptions.length; level3Index += 1) {
                    var item3 = thirdOptions[level3Index]
                    var value3 = optionValue(item3)
                    var text3 = optionLabel(item3)
                    results.push({
                        level1: value1,
                        level2: value2,
                        level3: value3,
                        value: value1 + "/" + value2 + "/" + value3,
                        displayText: text1 + " / " + text2 + " / " + text3,
                    })
                }
            }
        }
        return results
    }

    function filteredSearchPaths() {
        var keyword = String(filterText || "").trim()
        if (!keyword.length) {
            return []
        }
        var source = searchablePaths()
        var result = []
        for (var index = 0; index < source.length; index += 1) {
            var item = source[index]
            if (fuzzyMatch(item.displayText, keyword) || fuzzyMatch(item.value, keyword)) {
                result.push(item)
            }
        }
        return result
    }

    function popupColumnCount() {
        var count = 1
        if (rootField.level2Options.length > 0) {
            count += 1
        }
        if (rootField.level3Options.length > 0) {
            count += 1
        }
        return count
    }

    function popupContentWidth() {
        var columns = popupColumnCount()
        var preferredWidth = popupMinWidth + Math.max(0, columns - 2) * 56
        return Math.min(popupMaxWidth, Math.max(popupMinWidth, preferredWidth))
    }

    function popupOffsetX(popupWidth) {
        var containerWidth = rootField.parent && rootField.parent.width ? Number(rootField.parent.width) : Number(rootField.width)
        var selfX = Number(rootField.x || 0)
        var desiredWidth = Number(popupWidth || 0)
        var minOffset = -selfX
        var maxOffset = Math.min(0, containerWidth - selfX - desiredWidth)
        return Math.max(minOffset, maxOffset)
    }

    function ensureSelection(options, preferred, fallbackToFirst) {
        var next = String(preferred || "")
        if (!options || options.length === 0) {
            return ""
        }
        if (next.length > 0) {
            for (var i = 0; i < options.length; i += 1) {
                if (options[i].value === next) {
                    return next
                }
            }
        }
        return fallbackToFirst === true ? options[0].value : ""
    }

    function syncCascadeFromValue(rawValue) {
        var parsed = parsePathFn ? parsePathFn(rawValue) : { level1: "", level2: "", level3: "" }
        level1Options = level1OptionsFn ? level1OptionsFn() : []
        level1 = ensureSelection(level1Options, parsed.level1, false)
        level2Options = level1 && level2OptionsFn ? level2OptionsFn(level1) : []
        level2 = ensureSelection(level2Options, parsed.level2, false)
        level3Options = level1 && level2 && level3OptionsFn ? level3OptionsFn(level1, level2) : []
        level3 = ensureSelection(level3Options, parsed.level3, false)
    }

    function applySearchPath(path) {
        if (!path) {
            return
        }
        syncCascadeFromValue(path.value)
    }

    function composeValue() {
        if (!level1) {
            return ""
        }
        if (!level2) {
            return level1
        }
        if (!level3) {
            return level1 + "/" + level2
        }
        return level1 + "/" + level2 + "/" + level3
    }

    function acceptCurrentSelection() {
        var nextValue = composeValue()
        popup.close()
        rootField.accepted(nextValue)
    }

    function clearSelection() {
        filterText = ""
        if (searchInput) {
            searchInput.text = ""
        }
        popup.close()
        rootField.accepted("")
    }

    function acceptSearchPath(path) {
        applySearchPath(path)
        filterText = ""
        searchInput.text = ""
        acceptCurrentSelection()
    }

    function commitFirstSearchMatch() {
        var source = filteredSearchPaths()
        if (!source.length) {
            return
        }
        acceptSearchPath(source[0])
    }

    function openPopup() {
        syncCascadeFromValue(value)
        filterText = ""
        popup.open()
        Qt.callLater(function() {
            searchInput.forceActiveFocus()
            searchInput.selectAll()
        })
    }

    function closePopup() {
        popup.close()
        filterText = ""
        if (searchInput) {
            searchInput.focus = false
        }
    }

    radius: fieldRadius
    color: fieldBg
    border.width: 1
    border.color: popup.opened ? fieldFocusLine : fieldLine
    implicitHeight: fieldHeight

    Text {
        anchors.left: parent.left
        anchors.right: indicator.left
        anchors.leftMargin: theme.formFieldPaddingH || 14
        anchors.rightMargin: 8
        anchors.verticalCenter: parent.verticalCenter
        text: rootField.value.length > 0 ? rootField.displayPath(rootField.value) : rootField.placeholderText
        color: rootField.value.length > 0 ? rootField.titleInk : rootField.labelInk
        font.family: rootField.uiFont
        font.pixelSize: rootField.fieldFontSize
        elide: Text.ElideRight
    }

    Canvas {
        id: indicator
        anchors.right: parent.right
        anchors.rightMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        width: 10
        height: 6
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

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: rootField.openPopup()
    }

    Popup {
        id: popup
        parent: rootField
        x: rootField.popupOffsetX(width)
        y: rootField.height + 8
        width: Math.max(rootField.width, rootField.popupContentWidth())
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        padding: rootField.popupPadding

        background: Rectangle {
            radius: rootField.popupRadius
            color: rootField.popupBg
            border.width: 1
            border.color: rootField.fieldLine
        }

        contentItem: Rectangle {
            color: "transparent"
            implicitHeight: searchColumn.implicitHeight

            ColumnLayout {
                id: searchColumn
                anchors.fill: parent
                spacing: 6

                TextField {
                    id: searchInput
                    Layout.fillWidth: true
                    Layout.preferredHeight: rootField.fieldHeight
                    placeholderText: "输入关键字筛选"
                    color: rootField.titleInk
                    font.family: rootField.uiFont
                    font.pixelSize: rootField.fieldFontSize
                    selectByMouse: true
                    rightPadding: clearAction.visible ? 56 : 12

                    background: Rectangle {
                        radius: rootField.popupItemRadius
                        color: rootField.popupBg
                        border.width: 1
                        border.color: rootField.fieldLine
                    }

                    onTextEdited: rootField.filterText = text
                    onAccepted: rootField.commitFirstSearchMatch()
                    Keys.onEscapePressed: popup.close()
                    Text {
                        id: clearAction
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        visible: rootField.value.length > 0 || searchInput.text.length > 0
                        text: "清空"
                        color: clearMouseArea.containsMouse ? rootField.accent : rootField.labelInk
                        font.family: rootField.uiFont
                        font.pixelSize: 11
                        font.weight: 500
                        opacity: 0.9
                    }

                    MouseArea {
                        id: clearMouseArea
                        anchors.fill: clearAction
                        visible: clearAction.visible
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: rootField.clearSelection()
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    visible: rootField.filterText.trim().length > 0
                    implicitHeight: Math.min(searchResultList.contentHeight + 8, 220)
                    radius: rootField.popupItemRadius
                    color: rootField.popupBg
                    border.width: 1
                    border.color: rootField.fieldLine

                    ListView {
                        id: searchResultList
                        anchors.fill: parent
                        anchors.margins: 4
                        clip: true
                        model: rootField.filteredSearchPaths()
                        spacing: 2

                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: rootField.popupItemHeight
                            radius: rootField.popupItemRadius
                            color: resultMouseArea.containsMouse ? rootField.hoverBg : "transparent"

                            Text {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.displayText
                                color: rootField.titleInk
                                font.family: rootField.uiFont
                                font.pixelSize: rootField.fieldFontSize
                                elide: Text.ElideRight
                            }

                            MouseArea {
                                id: resultMouseArea
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: rootField.acceptSearchPath(modelData)
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: searchResultList.count === 0
                        text: "未找到匹配项"
                        color: rootField.labelInk
                        font.family: rootField.uiFont
                        font.pixelSize: 11
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: rootField.filterText.trim().length === 0
                    spacing: 6

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 180
                        implicitHeight: 220
                        radius: rootField.popupItemRadius
                        color: rootField.popupBg
                        border.width: 1
                        border.color: rootField.fieldLine

                        ListView {
                            anchors.fill: parent
                            anchors.margins: 4
                            clip: true
                            model: rootField.level1Options
                            spacing: 2

                            delegate: Rectangle {
                                required property var modelData
                                width: ListView.view.width
                                height: rootField.popupItemHeight
                                radius: rootField.popupItemRadius
                                color: resultMouseArea.containsMouse
                                       ? rootField.hoverBg
                                       : (modelData.value === rootField.level1 ? rootField.accentTint : "transparent")

                                Text {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.text
                                    color: modelData.value === rootField.level1 ? rootField.accent : rootField.titleInk
                                    font.family: rootField.uiFont
                                    font.pixelSize: rootField.fieldFontSize
                                    font.weight: modelData.value === rootField.level1 ? 600 : 400
                                    elide: Text.ElideRight
                                }

                                MouseArea {
                                    id: resultMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        rootField.level1 = modelData.value
                                        rootField.level2Options = level2OptionsFn ? level2OptionsFn(rootField.level1) : []
                                        rootField.level2 = ""
                                        rootField.level3Options = []
                                        rootField.level3 = ""
                                        if (rootField.level2Options.length === 0) {
                                            rootField.acceptCurrentSelection()
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        visible: rootField.level2Options.length > 0
                        Layout.fillWidth: true
                        Layout.preferredWidth: 180
                        implicitHeight: 220
                        radius: rootField.popupItemRadius
                        color: rootField.popupBg
                        border.width: 1
                        border.color: rootField.fieldLine

                        ListView {
                            anchors.fill: parent
                            anchors.margins: 4
                            clip: true
                            model: rootField.level2Options
                            spacing: 2

                            delegate: Rectangle {
                                required property var modelData
                                width: ListView.view.width
                                height: rootField.popupItemHeight
                                radius: rootField.popupItemRadius
                                color: resultMouseArea.containsMouse
                                       ? rootField.hoverBg
                                       : (modelData.value === rootField.level2 ? rootField.accentTint : "transparent")

                                Text {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.text
                                    color: modelData.value === rootField.level2 ? rootField.accent : rootField.titleInk
                                    font.family: rootField.uiFont
                                    font.pixelSize: rootField.fieldFontSize
                                    font.weight: modelData.value === rootField.level2 ? 600 : 400
                                    elide: Text.ElideRight
                                }

                                MouseArea {
                                    id: resultMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        rootField.level2 = modelData.value
                                        rootField.level3Options = level3OptionsFn ? level3OptionsFn(rootField.level1, rootField.level2) : []
                                        rootField.level3 = ""
                                        if (rootField.level3Options.length === 0) {
                                            rootField.acceptCurrentSelection()
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        visible: rootField.level3Options.length > 0
                        Layout.fillWidth: true
                        Layout.preferredWidth: 180
                        implicitHeight: 220
                        radius: rootField.popupItemRadius
                        color: rootField.popupBg
                        border.width: 1
                        border.color: rootField.fieldLine

                        ListView {
                            anchors.fill: parent
                            anchors.margins: 4
                            clip: true
                            model: rootField.level3Options
                            spacing: 2

                            delegate: Rectangle {
                                required property var modelData
                                width: ListView.view.width
                                height: rootField.popupItemHeight
                                radius: rootField.popupItemRadius
                                color: resultMouseArea.containsMouse
                                       ? rootField.hoverBg
                                       : (modelData.value === rootField.level3 ? rootField.accentTint : "transparent")

                                Text {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.text
                                    color: modelData.value === rootField.level3 ? rootField.accent : rootField.titleInk
                                    font.family: rootField.uiFont
                                    font.pixelSize: rootField.fieldFontSize
                                    font.weight: modelData.value === rootField.level3 ? 600 : 400
                                    elide: Text.ElideRight
                                }

                                MouseArea {
                                    id: resultMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        rootField.level3 = modelData.value
                                        rootField.acceptCurrentSelection()
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

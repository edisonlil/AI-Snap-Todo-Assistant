import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: rootField
    required property var theme
    property string label: ""
    property string value: ""
    property string selectedCode: ""
    property string placeholderText: "未填写"
    property bool editing: false
    property bool saving: false
    property bool compact: false
    property var options: []

    readonly property color titleInk: resolveThemeColor("titleInk", "#18202E")
    readonly property color labelInk: resolveThemeColor("labelInk", "#7C8795")
    readonly property color accent: resolveThemeColor("accent", "#2A313F")
    readonly property color accentTint: resolveThemeColor("accentTint", "#ECEFF3")
    readonly property color hoverBg: resolveThemeColor("hoverBg", "#F3F4F6")
    readonly property color fieldBg: resolveThemeColor("fieldBg", "#F5F5F5")
    readonly property color fieldLine: resolveThemeColor("formFieldBorder", resolveThemeColor("fieldLine", resolveThemeColor("panelLine", "#E5E7EB")))
    readonly property color fieldFocusLine: resolveThemeColor("formFieldFocusBorder", resolveThemeColor("accent", "#2A313F"))
    readonly property color inputBg: resolveThemeColor("formFieldBg", resolveThemeColor("inputBg", "#FFFFFF"))
    readonly property string uiFont: theme && theme.uiFont ? theme.uiFont : "Microsoft YaHei UI"
    readonly property int formInlineEditHeight: theme && theme.formInlineEditHeight ? theme.formInlineEditHeight : 32
    readonly property int formPopupRadius: theme && theme.formPopupRadius ? theme.formPopupRadius : 8
    readonly property int formPopupItemRadius: theme && theme.formPopupItemRadius ? theme.formPopupItemRadius : 6
    readonly property int formPopupItemHeight: theme && theme.formPopupItemHeight ? theme.formPopupItemHeight : 30
    readonly property string selectedText: optionTextByCode(selectedCode) || value

    signal clicked
    signal accepted(string code, string value)
    signal canceled

    function resolveThemeColor(name, fallback) {
        return theme && theme[name] !== undefined ? theme[name] : fallback
    }

    function optionTextByCode(code) {
        var normalized = String(code || "")
        for (var index = 0; index < options.length; index += 1) {
            var option = options[index]
            if (String(option.code || "") === normalized) {
                return String(option.text || option.value || "")
            }
        }
        return ""
    }

    function currentOptionIndex() {
        var normalized = String(selectedCode || "")
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].code || "") === normalized) {
                return index
            }
        }
        return -1
    }

    onEditingChanged: {
        if (!editing) {
            popup.close()
            return
        }
        Qt.callLater(function() {
            if (rootField.editing) {
                popup.open()
            }
        })
    }

    radius: 0
    color: "transparent"
    border.width: 0
    implicitHeight: fieldColumn.implicitHeight + 14

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
                    visible: rootField.saving
                    running: rootField.saving
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                }

                Item {
                    Layout.fillWidth: true
                    implicitHeight: valueText.implicitHeight

                    Text {
                        id: valueText
                        anchors.left: parent.left
                        anchors.right: valueAction.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: 10
                        text: rootField.selectedText.length > 0 ? rootField.selectedText : rootField.placeholderText
                        color: rootField.selectedText.length > 0 ? rootField.titleInk : rootField.labelInk
                        font.family: rootField.uiFont
                        font.pixelSize: rootField.compact ? 12 : 13
                        font.weight: rootField.selectedText.length > 0 ? 500 : 400
                        elide: Text.ElideRight
                    }

                    Text {
                        id: valueAction
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        visible: hoverArea.containsMouse && !rootField.saving
                        text: "\u270e"
                        color: rootField.accent
                        font.family: rootField.uiFont
                        font.pixelSize: 11
                        opacity: 0.75
                    }

                    MouseArea {
                        id: hoverArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: !rootField.saving ? Qt.PointingHandCursor : Qt.ArrowCursor
                        enabled: !rootField.saving
                        onClicked: rootField.clicked()
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
                    id: trigger
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
                        text: rootField.selectedText
                        color: rootField.titleInk
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
                                popup.close()
                                rootField.canceled()
                            }
                        }
                    }
                }

                Popup {
                    id: popup
                    parent: rootField
                    x: 0
                    y: rootField.formInlineEditHeight + 12
                    width: Math.max(320, Math.min(rootField.width - 12, 420))
                    modal: false
                    focus: true
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                    padding: 0

                    background: Rectangle {
                        radius: rootField.formPopupRadius
                        color: rootField.inputBg
                        border.width: 1
                        border.color: rootField.fieldLine
                    }

                    contentItem: Rectangle {
                        color: rootField.fieldBg
                        border.width: 1
                        border.color: rootField.fieldLine
                        radius: rootField.formPopupItemRadius
                        implicitHeight: Math.min(optionList.contentHeight + 8, 220)

                        ListView {
                            id: optionList
                            anchors.fill: parent
                            anchors.margins: 4
                            clip: true
                            model: rootField.options
                            spacing: 2
                            currentIndex: rootField.currentOptionIndex()

                            delegate: Rectangle {
                                required property var modelData
                                width: ListView.view.width
                                height: rootField.formPopupItemHeight
                                radius: rootField.formPopupItemRadius
                                color: itemMouseArea.containsMouse
                                       ? rootField.hoverBg
                                       : (String(modelData.code || "") === String(rootField.selectedCode || "") ? rootField.accentTint : "transparent")

                                Text {
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.text || modelData.value || ""
                                    color: String(modelData.code || "") === String(rootField.selectedCode || "") ? rootField.accent : rootField.titleInk
                                    font.family: rootField.uiFont
                                    font.pixelSize: rootField.compact ? 11 : 12
                                    font.weight: String(modelData.code || "") === String(rootField.selectedCode || "") ? 600 : 400
                                    elide: Text.ElideRight
                                }

                                MouseArea {
                                    id: itemMouseArea
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        popup.close()
                                        rootField.accepted(String(modelData.code || ""), String(modelData.value || ""))
                                    }
                                }
                            }
                        }
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

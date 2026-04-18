import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: rootField
    required property var theme
    property string label: ""
    property string value: ""
    property string placeholderText: "未生成"
    property bool editing: false
    property bool saving: false
    property bool compact: false
    property string level1: ""
    property string level2: ""
    property string level3: ""
    property var level1Options: []
    property var level2Options: []
    property var level3Options: []
    property var parsePathFn
    property var level1OptionsFn
    property var level2OptionsFn
    property var level3OptionsFn
    signal clicked
    signal accepted(string value)
    signal canceled

    function displayPath(rawValue) {
        var text = String(rawValue || "")
        if (!text) {
            return ""
        }
        var parts = text.split("/")
        return parts.join(" / ")
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

    function ensureSelection(options, preferred) {
        var next = String(preferred || "")
        if (!options || options.length === 0) {
            return ""
        }
        for (var i = 0; i < options.length; i += 1) {
            if (options[i].value === next) {
                return next
            }
        }
        return options[0].value
    }

    function syncCascadeFromValue(rawValue) {
        var parsed = parsePathFn ? parsePathFn(rawValue) : { level1: "", level2: "", level3: "" }
        level1Options = level1OptionsFn ? level1OptionsFn() : []
        level1 = ensureSelection(level1Options, parsed.level1)
        level2Options = level2OptionsFn ? level2OptionsFn(level1) : []
        level2 = ensureSelection(level2Options, parsed.level2)
        level3Options = level3OptionsFn ? level3OptionsFn(level1, level2) : []
        level3 = ensureSelection(level3Options, parsed.level3)
    }

    onEditingChanged: {
        if (editing) {
            syncCascadeFromValue(value)
        }
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
            color: theme.labelInk
            font.family: theme.uiFont
            font.pixelSize: 10
            font.weight: 500
            elide: Text.ElideRight
            opacity: 0.72
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: rootField.editing ? cascadeEditor.implicitHeight : valueRow.implicitHeight

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
                        text: rootField.value.length > 0 ? rootField.displayPath(rootField.value) : rootField.placeholderText
                        color: rootField.value.length > 0 ? theme.titleInk : "#A2907A"
                        font.family: theme.uiFont
                        font.pixelSize: rootField.compact ? 12 : 13
                        font.weight: rootField.value.length > 0 ? 500 : 400
                        elide: Text.ElideRight
                    }

                    Text {
                        id: valueAction
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        visible: hoverArea.containsMouse && !rootField.saving
                        text: "\u270e"
                        color: theme.accent
                        font.family: theme.uiFont
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
                id: cascadeEditor
                anchors.left: parent.left
                anchors.right: parent.right
                visible: rootField.editing
                spacing: 6

                Control {
                    id: cascadeTrigger
                    Layout.fillWidth: true
                    Layout.preferredHeight: 32
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
                        anchors.right: triggerArrow.left
                        anchors.leftMargin: 0
                        anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: rootField.displayPath(rootField.composeValue())
                        color: rootField.theme.titleInk
                        font.family: rootField.theme.uiFont
                        font.pixelSize: rootField.compact ? 11 : 12
                        elide: Text.ElideRight
                    }

                    Canvas {
                        id: triggerArrow
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
                            context.fillStyle = rootField.theme.labelInk
                            context.fill()
                        }
                    }

                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: "#E0D5C8"
                        opacity: 0.9
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: cascadePopup.open()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignLeft
                    spacing: 10

                    Text {
                        text: "保存"
                        color: rootField.theme.accent
                        font.family: rootField.theme.uiFont
                        font.pixelSize: 11
                        font.weight: 600

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                cascadePopup.close()
                                rootField.accepted(rootField.composeValue())
                            }
                        }
                    }

                    Text {
                        text: "取消"
                        color: rootField.theme.labelInk
                        font.family: rootField.theme.uiFont
                        font.pixelSize: 11
                        font.weight: 500
                        opacity: 0.88

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                cascadePopup.close()
                                rootField.canceled()
                            }
                        }
                    }
                }

                Popup {
                    id: cascadePopup
                    parent: rootField
                    x: 0
                    y: 44
                    width: Math.max(320, Math.min(rootField.width - 12, 760))
                    modal: false
                    focus: true
                    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                    padding: 0

                    background: Rectangle {
                        radius: 8
                        color: "#FFFEFC"
                        border.width: 1
                        border.color: "#E0D5C8"
                    }

                    contentItem: RowLayout {
                        spacing: 6

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 180
                            implicitHeight: 220
                            radius: 7
                            color: "#FFF9F2"
                            border.width: 1
                            border.color: "#E7DCCF"

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 4
                                clip: true
                                model: rootField.level1Options
                                spacing: 2

                                delegate: Rectangle {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 30
                                    radius: 6
                                    color: modelData.value === rootField.level1 ? "#F0E3D3" : "transparent"

                                    Text {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.text
                                        color: rootField.theme.titleInk
                                        font.family: rootField.theme.uiFont
                                        font.pixelSize: rootField.compact ? 11 : 12
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            rootField.level1 = modelData.value
                                            rootField.level2Options = level2OptionsFn ? level2OptionsFn(rootField.level1) : []
                                            rootField.level2 = rootField.ensureSelection(rootField.level2Options, "")
                                            rootField.level3Options = level3OptionsFn ? level3OptionsFn(rootField.level1, rootField.level2) : []
                                            rootField.level3 = rootField.ensureSelection(rootField.level3Options, "")
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
                            radius: 7
                            color: "#FFF9F2"
                            border.width: 1
                            border.color: "#E7DCCF"

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 4
                                clip: true
                                model: rootField.level2Options
                                spacing: 2

                                delegate: Rectangle {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 30
                                    radius: 6
                                    color: modelData.value === rootField.level2 ? "#F0E3D3" : "transparent"

                                    Text {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.text
                                        color: rootField.theme.titleInk
                                        font.family: rootField.theme.uiFont
                                        font.pixelSize: rootField.compact ? 11 : 12
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            rootField.level2 = modelData.value
                                            rootField.level3Options = level3OptionsFn ? level3OptionsFn(rootField.level1, rootField.level2) : []
                                            rootField.level3 = rootField.ensureSelection(rootField.level3Options, "")
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
                            radius: 7
                            color: "#FFF9F2"
                            border.width: 1
                            border.color: "#E7DCCF"

                            ListView {
                                anchors.fill: parent
                                anchors.margins: 4
                                clip: true
                                model: rootField.level3Options
                                spacing: 2

                                delegate: Rectangle {
                                    required property var modelData
                                    width: ListView.view.width
                                    height: 30
                                    radius: 6
                                    color: modelData.value === rootField.level3 ? "#F0E3D3" : "transparent"

                                    Text {
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.text
                                        color: rootField.theme.titleInk
                                        font.family: rootField.theme.uiFont
                                        font.pixelSize: rootField.compact ? 11 : 12
                                        elide: Text.ElideRight
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: rootField.level3 = modelData.value
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
            color: "#E8DFD2"
            opacity: 0.85
        }
    }
}

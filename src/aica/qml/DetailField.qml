import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: fieldRoot
    required property var theme
    property string label: ""
    property string value: ""
    property string placeholderText: "未填写"
    property string draftValue: ""
    property bool editable: false
    property bool editing: false
    property bool saving: false
    property bool multiline: false
    property bool compact: false
    property bool actionVisible: false
    property bool actionBusy: false
    property string actionIconSource: ""
    property string actionText: ""
    property color actionInkColor: theme.accent
    readonly property color formFieldBorder: theme.formFieldBorder || theme.panelLine
    readonly property color formFieldFocusBorder: theme.formFieldFocusBorder || theme.accent
    signal clicked
    signal actionTriggered
    signal accepted(string value)
    signal canceled
    signal draftChanged(string value)  // New signal for draft changes

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
            text: fieldRoot.label
            color: theme.labelInk
            font.family: theme.uiFont
            font.pixelSize: 10
            font.weight: 500
            elide: Text.ElideRight
            opacity: 0.72
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: fieldValueRow.implicitHeight

            RowLayout {
                id: fieldValueRow
                anchors.left: parent.left
                anchors.right: parent.right
                spacing: 8

                BusyIndicator {
                    visible: fieldRoot.saving || fieldRoot.actionBusy
                    running: fieldRoot.saving || fieldRoot.actionBusy
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                }

                ControlPanelSettingsInput {
                    id: inlineEditor
                    visible: fieldRoot.editable && fieldRoot.editing
                    theme: fieldRoot.theme
                    Layout.fillWidth: true
                    placeholderText: fieldRoot.placeholderText
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 8
                    
                    // Internal state to track current text
                    property string internalText: ""
                    
                    background: Rectangle {
                        color: "transparent"
                        border.width: 0

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: inlineEditor.activeFocus ? fieldRoot.formFieldFocusBorder : fieldRoot.formFieldBorder
                            opacity: inlineEditor.activeFocus ? 1 : 0.9
                        }
                    }
                    
                    Connections {
                        target: fieldRoot
                        function onEditingChanged() {
                            if (fieldRoot.editing) {
                                // CRITICAL: When entering edit mode, reset text to draftValue
                                // This ensures we always start with the correct current value
                                inlineEditor.internalText = fieldRoot.draftValue
                                inlineEditor.text = fieldRoot.draftValue
                                Qt.callLater(function() {
                                    inlineEditor.forceActiveFocus()
                                })
                            } else {
                                // When exiting edit mode, clear internal state
                                inlineEditor.internalText = ""
                                inlineEditor.text = ""
                            }
                        }
                    }

                    onTextChanged: {
                        // Track text changes internally
                        if (fieldRoot.editing && text !== internalText) {
                            internalText = text
                            fieldRoot.draftChanged(text)
                        }
                    }
                    
                    onAccepted: fieldRoot.accepted(inlineEditor.text)
                    Keys.onEscapePressed: fieldRoot.canceled()
                }

                Item {
                    visible: !fieldRoot.editing
                    Layout.fillWidth: true
                    implicitHeight: Math.max(fieldTextLoader.implicitHeight + (fieldRoot.multiline ? 4 : 0), actionRow.implicitHeight)

                    // 只读字段使用 SelectableText 支持选中复制
                    Loader {
                        id: fieldTextLoader
                        anchors.left: parent.left
                        anchors.right: actionRow.left
                        anchors.verticalCenter: fieldRoot.multiline ? undefined : parent.verticalCenter
                        anchors.top: fieldRoot.multiline ? parent.top : undefined
                        anchors.rightMargin: actionRow.width > 0 ? 10 : 0
                        
                        // 展示态始终使用可选中文本；进入编辑只通过独立操作按钮触发。
                        sourceComponent: selectableTextComponent
                        
                        property int maxHeight: fieldRoot.multiline ? 120 : 9999
                    }
                    
                    Component {
                        id: selectableTextComponent
                        SelectableText {
                            id: fieldTextSelectable
                            width: fieldTextLoader.width
                            height: fieldRoot.multiline ? Math.min(implicitHeight, fieldTextLoader.maxHeight) : implicitHeight
                            clip: fieldRoot.multiline
                            text: fieldRoot.value.length > 0 ? fieldRoot.value : fieldRoot.placeholderText
                            color: fieldRoot.value.length > 0 ? theme.titleInk : theme.labelInk
                            font.family: theme.uiFont
                            font.pixelSize: fieldRoot.compact ? 12 : 13
                            font.weight: fieldRoot.value.length > 0 ? 500 : 400
                            wrapMode: fieldRoot.multiline ? TextEdit.Wrap : TextEdit.NoWrap
                        }
                    }
                    
                    // Hover 检测层，只在可编辑字段时启用
                    HoverHandler {
                        id: fieldHover
                        enabled: fieldRoot.editable
                    }

                    Row {
                        id: actionRow
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        visible: fieldRoot.actionVisible || (fieldRoot.editable && fieldHover.hovered && !fieldRoot.actionBusy && !fieldRoot.saving)
                        width: visible ? implicitWidth : 0
                        z: 2

                        Rectangle {
                            readonly property bool textAction: fieldRoot.actionText.length > 0
                            visible: fieldRoot.actionVisible
                            implicitWidth: textAction ? actionTextLabel.implicitWidth + 2 : (fieldRoot.compact ? 18 : 20)
                            implicitHeight: textAction ? 20 : implicitWidth
                            radius: textAction ? 0 : implicitWidth / 2
                            color: textAction ? "transparent" : (actionButtonHover.containsMouse ? theme.hoverBg : "#FFFFFF")
                            border.width: textAction ? 0 : 1
                            border.color: textAction ? "transparent" : theme.panelLine

                            BusyIndicator {
                                anchors.centerIn: parent
                                width: 12
                                height: 12
                                visible: fieldRoot.actionBusy
                                running: fieldRoot.actionBusy
                            }

                            Image {
                                anchors.centerIn: parent
                                width: 12
                                height: 12
                                visible: !fieldRoot.actionBusy && !parent.textAction
                                source: fieldRoot.actionIconSource
                                fillMode: Image.PreserveAspectFit
                            }

                            Text {
                                id: actionTextLabel
                                anchors.centerIn: parent
                                visible: !fieldRoot.actionBusy && parent.textAction
                                text: fieldRoot.actionText
                                color: fieldRoot.actionInkColor
                                font.family: theme.uiFont
                                font.pixelSize: 11
                                font.weight: 600
                                opacity: actionButtonHover.containsMouse ? 1 : 0.72
                            }

                            MouseArea {
                                id: actionButtonHover
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: !fieldRoot.actionBusy
                                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: fieldRoot.actionTriggered()
                            }
                        }

                        Text {
                            id: editAction
                            visible: fieldRoot.editable && fieldHover.hovered && !fieldRoot.actionBusy && !fieldRoot.saving
                            text: "\u270e"
                            color: theme.accent
                            font.family: theme.uiFont
                            font.pixelSize: 11
                            opacity: 0.75

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: fieldRoot.clicked()
                            }
                        }
                    }
                }

                RowLayout {
                    visible: fieldRoot.editable && fieldRoot.editing
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    spacing: 10

                    Text {
                        text: "保存"
                        color: fieldRoot.theme.accent
                        font.family: fieldRoot.theme.uiFont
                        font.pixelSize: 11
                        font.weight: 600

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: fieldRoot.accepted(inlineEditor.text)
                        }
                    }

                    Text {
                        text: "取消"
                        color: fieldRoot.theme.labelInk
                        font.family: fieldRoot.theme.uiFont
                        font.pixelSize: 11
                        font.weight: 500
                        opacity: 0.88

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: fieldRoot.canceled()
                        }
                    }
                }
            }

            Rectangle {
                visible: !fieldRoot.editing
                Layout.fillWidth: true
                implicitHeight: 1
                color: fieldRoot.formFieldBorder
                opacity: 0.85
            }
        }
    }
}

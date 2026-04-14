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
    signal clicked
    signal actionTriggered
    signal accepted(string value)
    signal canceled

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
                    text: fieldRoot.draftValue
                    placeholderText: fieldRoot.placeholderText
                    leftPadding: 0
                    rightPadding: 0
                    topPadding: 0
                    bottomPadding: 8
                    background: Rectangle {
                        color: "transparent"
                        border.width: 0

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: inlineEditor.activeFocus ? fieldRoot.theme.accent : "#D8CCBE"
                            opacity: inlineEditor.activeFocus ? 1 : 0.9
                        }
                    }

                    onTextEdited: fieldRoot.draftValue = text
                    onAccepted: fieldRoot.accepted(fieldRoot.draftValue)
                    Keys.onEscapePressed: fieldRoot.canceled()
                }

                Item {
                    visible: !fieldRoot.editing
                    Layout.fillWidth: true
                    implicitHeight: Math.max(fieldText.implicitHeight + (fieldRoot.multiline ? 4 : 0), actionRow.implicitHeight)

                    MouseArea {
                        id: fieldHover
                        anchors.fill: parent
                        acceptedButtons: Qt.NoButton
                        hoverEnabled: true
                    }

                    Text {
                        id: fieldText
                        anchors.left: parent.left
                        anchors.right: actionRow.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: actionRow.width > 0 ? 10 : 0
                        text: fieldRoot.value.length > 0 ? fieldRoot.value : fieldRoot.placeholderText
                        color: fieldRoot.value.length > 0 ? theme.titleInk : "#A2907A"
                        font.family: theme.uiFont
                        font.pixelSize: fieldRoot.compact ? 12 : 13
                        font.weight: fieldRoot.value.length > 0 ? 500 : 400
                        wrapMode: fieldRoot.multiline ? Text.Wrap : Text.NoWrap
                        elide: fieldRoot.multiline ? Text.ElideNone : Text.ElideRight
                    }

                    Row {
                        id: actionRow
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        visible: fieldRoot.actionVisible || (fieldRoot.editable && fieldHover.containsMouse && !fieldRoot.actionBusy && !fieldRoot.saving)
                        width: visible ? implicitWidth : 0

                        Rectangle {
                            visible: fieldRoot.actionVisible
                            implicitWidth: fieldRoot.compact ? 18 : 20
                            implicitHeight: implicitWidth
                            radius: implicitWidth / 2
                            color: actionButtonHover.containsMouse ? "#F3E6D6" : "#FFF8EF"
                            border.width: 1
                            border.color: theme.panelLine

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
                                visible: !fieldRoot.actionBusy
                                source: fieldRoot.actionIconSource
                                fillMode: Image.PreserveAspectFit
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
                            visible: fieldRoot.editable && fieldHover.containsMouse && !fieldRoot.actionBusy && !fieldRoot.saving
                            text: "\u270e"
                            color: theme.accent
                            font.family: theme.uiFont
                            font.pixelSize: 11
                            opacity: 0.75
                        }
                    }

                    MouseArea {
                        anchors.left: parent.left
                        anchors.right: actionRow.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        enabled: fieldRoot.editable && !fieldRoot.saving && !fieldRoot.actionBusy
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: fieldRoot.clicked()
                    }
                }

                RowLayout {
                    visible: fieldRoot.editable && fieldRoot.editing
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
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
                            onClicked: fieldRoot.accepted(fieldRoot.draftValue)
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
                color: "#E8DFD2"
                opacity: 0.85
            }
        }
    }
}

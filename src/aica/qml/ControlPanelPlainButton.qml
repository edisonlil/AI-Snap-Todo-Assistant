import QtQuick

Rectangle {
    id: buttonRoot
    required property var theme
    property string label: ""
    property color fillColor: "#FFFDFC"
    property color inkColor: theme.titleInk
    property int strokeWidth: 1
    signal clicked

    radius: 16
    color: fillColor
    border.width: strokeWidth
    border.color: theme.panelLine
    implicitWidth: buttonText.implicitWidth + 28
    implicitHeight: 38

    Text {
        id: buttonText
        anchors.centerIn: parent
        text: buttonRoot.label
        color: buttonRoot.inkColor
        font.family: theme.uiFont
        font.pixelSize: 12
        font.weight: 700
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: buttonRoot.clicked()
    }
}

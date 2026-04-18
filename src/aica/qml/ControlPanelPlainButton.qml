import QtQuick

Rectangle {
    id: buttonRoot
    required property var theme
    property string label: ""
    property color fillColor: "#FFFFFF"
    property color inkColor: theme.accent
    property int strokeWidth: 1
    signal clicked

    radius: 16
    color: fillColor
    border.width: strokeWidth
    border.color: buttonRoot.strokeWidth > 0 ? theme.accent : buttonRoot.fillColor
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

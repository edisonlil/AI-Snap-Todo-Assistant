import QtQuick

Rectangle {
    id: button
    required property var theme
    property string label: ""
    property bool selected: false
    signal clicked

    radius: theme.componentRadius || theme.formFieldRadius || 8
    implicitWidth: segmentLabel.implicitWidth + 28
    implicitHeight: theme.componentHeight || theme.formFieldHeight || 36
    color: selected ? theme.accentSoft : (theme.formFieldBg || theme.inputBg || "#FFFFFF")
    border.width: 1
    border.color: selected ? theme.accent : (theme.formFieldBorder || theme.panelLine || "#E5E7EB")

    Text {
        id: segmentLabel
        anchors.centerIn: parent
        text: button.label
        color: button.selected ? theme.accent : theme.titleInk
        font.family: theme.uiFont
        font.pixelSize: theme.formFieldFontSize || theme.fontBody || 12
        font.weight: button.selected ? 700 : 500
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: button.clicked()
    }
}

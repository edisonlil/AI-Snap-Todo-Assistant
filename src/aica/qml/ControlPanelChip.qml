import QtQuick

Rectangle {
    id: chip
    required property var theme
    property string label: ""
    property bool removable: true
    signal removeClicked

    radius: theme.formChipRadius || 14
    width: chipText.implicitWidth + (removable ? 28 : 20)
    height: theme.formChipHeight || 28
    color: theme.accentSoft
    border.width: 1
    border.color: theme.formFieldBorder || theme.panelLine || "#E5E7EB"

    Text {
        id: chipText
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 10
        text: chip.label
        color: theme.titleInk
        font.family: theme.uiFont
        font.pixelSize: Math.max(10, (theme.formFieldFontSize || theme.fontBody || 12) - 1)
        font.weight: 600
        elide: Text.ElideRight
    }

    Text {
        visible: chip.removable
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: 10
        text: "×"
        color: theme.labelInk
        font.family: theme.uiFont
        font.pixelSize: theme.formFieldFontSize || theme.fontBody || 12

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: chip.removeClicked()
        }
    }
}

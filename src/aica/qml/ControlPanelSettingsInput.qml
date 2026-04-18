import QtQuick
import QtQuick.Controls

TextField {
    id: input
    required property var theme

    color: theme.titleInk
    font.family: theme.uiFont
    font.pixelSize: 12
    selectByMouse: true
    leftPadding: 14
    rightPadding: 14
    topPadding: 11
    bottomPadding: 11

    background: Rectangle {
        radius: 16
        color: "#FFFEFC"
        border.width: 1
        border.color: input.activeFocus ? theme.accent : theme.panelLine
    }
}

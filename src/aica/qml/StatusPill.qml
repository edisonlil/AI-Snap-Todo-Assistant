import QtQuick

Rectangle {
    required property var theme
    property string label: ""
    property string tone: "default"

    radius: 11
    implicitWidth: pillText.implicitWidth + 18
    implicitHeight: 24
    border.width: 1
    color: tone === "matched" ? "#E7F5ED"
         : tone === "warning" ? "#FFF4E8"
         : tone === "done" ? "#ECEFF3"
         : tone === "open" ? "#EAF7F1"
         : theme.panelAltBg
    border.color: tone === "matched" ? "#B6DEC5"
                : tone === "warning" ? "#F2C998"
                : tone === "done" ? theme.panelLine
                : tone === "open" ? "#B9DCCB"
                : theme.panelLine

    Text {
        id: pillText
        anchors.centerIn: parent
        text: parent.label
        color: tone === "warning" ? "#9A4B00"
             : tone === "done" ? theme.accent
             : tone === "matched" || tone === "open" ? "#17663A"
             : theme.bodyInk
        font.family: theme.uiFont
        font.pixelSize: 11
        font.weight: 700
    }
}

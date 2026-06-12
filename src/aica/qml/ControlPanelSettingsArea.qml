import QtQuick
import QtQuick.Controls

TextArea {
    id: area
    required property var theme
    property int fieldRadius: theme.componentRadius || theme.formFieldRadius || 8
    property int fieldFontSize: theme.formFieldFontSize || theme.fontBody || 12
    property color fieldBg: theme.formFieldBg || theme.inputBg || "#FFFFFF"
    property color fieldBorder: theme.formFieldBorder || theme.panelLine || "#E5E7EB"
    property color fieldFocusBorder: theme.formFieldFocusBorder || theme.accent || "#2A313F"

    color: theme.titleInk
    font.family: theme.uiFont
    font.pixelSize: fieldFontSize
    selectByMouse: true
    wrapMode: TextEdit.Wrap
    padding: theme.formFieldPaddingH || 14
    implicitHeight: 96

    background: Rectangle {
        radius: area.fieldRadius
        color: area.fieldBg
        border.width: 1
        border.color: area.activeFocus ? area.fieldFocusBorder : area.fieldBorder
    }
}

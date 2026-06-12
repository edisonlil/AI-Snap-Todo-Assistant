import QtQuick
import QtQuick.Controls

TextField {
    id: input
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
    implicitHeight: theme.componentHeight || theme.formFieldHeight || 36
    leftPadding: theme.formFieldPaddingH || 14
    rightPadding: theme.formFieldPaddingH || 14
    topPadding: theme.formFieldPaddingV || 11
    bottomPadding: theme.formFieldPaddingV || 11

    background: Rectangle {
        radius: input.fieldRadius
        color: input.fieldBg
        border.width: 1
        border.color: input.activeFocus ? input.fieldFocusBorder : input.fieldBorder
    }
}

import QtQuick
import QtQuick.Controls

SpinBox {
    id: spin
    required property var theme
    property int fieldRadius: theme.componentRadius || theme.formFieldRadius || 8
    property int fieldFontSize: theme.formFieldFontSize || theme.fontBody || 12
    property color fieldBg: theme.formFieldBg || theme.inputBg || "#FFFFFF"
    property color fieldBorder: theme.formFieldBorder || theme.panelLine || "#E5E7EB"
    property color fieldFocusBorder: theme.formFieldFocusBorder || theme.accent || "#2A313F"

    implicitHeight: theme.componentHeight || theme.formFieldHeight || 36
    font.family: theme.uiFont
    font.pixelSize: fieldFontSize

    background: Rectangle {
        radius: spin.fieldRadius
        color: spin.fieldBg
        border.width: 1
        border.color: spin.activeFocus ? spin.fieldFocusBorder : spin.fieldBorder
    }
}

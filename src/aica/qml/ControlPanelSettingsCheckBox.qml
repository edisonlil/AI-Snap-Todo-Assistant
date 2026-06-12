import QtQuick
import QtQuick.Controls

CheckBox {
    id: check
    required property var theme
    readonly property int fieldFontSize: theme.formFieldFontSize || theme.fontBody || 12
    readonly property int checkSpacing: theme.formCheckSpacing || 8

    spacing: checkSpacing
    font.family: theme.uiFont
    font.pixelSize: fieldFontSize
    palette.text: theme.titleInk
}

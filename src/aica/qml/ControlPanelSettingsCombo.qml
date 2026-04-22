import QtQuick
import QtQuick.Controls

ComboBox {
    id: combo
    required property var theme

    textRole: "text"
    font.family: theme.uiFont
    font.pixelSize: 12
    leftPadding: 14
    rightPadding: 34
    topPadding: 11
    bottomPadding: 11

    contentItem: Text {
        text: combo.displayText
        color: theme.titleInk
        font.family: theme.uiFont
        font.pixelSize: 12
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Canvas {
        x: combo.width - width - 14
        y: combo.topPadding + (combo.availableHeight - height) / 2
        width: 10
        height: 6
        contextType: "2d"
        onPaint: {
            context.reset()
            context.moveTo(0, 0)
            context.lineTo(width, 0)
            context.lineTo(width / 2, height)
            context.closePath()
            context.fillStyle = theme.labelInk
            context.fill()
        }
    }

    background: Rectangle {
        radius: 16
        color: theme.inputBg
        border.width: 1
        border.color: combo.activeFocus ? theme.accent : theme.panelLine
    }
}

import QtQuick
import QtQuick.Controls

CheckBox {
    id: check
    required property var theme
    readonly property int fieldFontSize: theme.formFieldFontSize || theme.fontBody || 12
    readonly property int checkSpacing: theme.formCheckSpacing || 8
    readonly property int checkIndicatorSize: 22
    readonly property int checkIndicatorRadius: 6
    readonly property color checkedFill: theme.accent || "#2A313F"
    readonly property color uncheckedFill: theme.formFieldBg || theme.inputBg || "#FFFFFF"
    readonly property color uncheckedBorder: theme.formFieldBorder || theme.panelLine || "#E5E7EB"
    readonly property color focusBorder: theme.formFieldFocusBorder || checkedFill
    readonly property color disabledInk: theme.mutedInk || "#A9B1BD"

    spacing: checkSpacing
    font.family: theme.uiFont
    font.pixelSize: fieldFontSize
    palette.text: theme.titleInk
    hoverEnabled: true
    implicitHeight: Math.max(theme.componentHeight || theme.formFieldHeight || 36, checkIndicatorSize)

    indicator: Rectangle {
        implicitWidth: check.checkIndicatorSize
        implicitHeight: check.checkIndicatorSize
        x: check.leftPadding
        y: (check.height - height) / 2
        radius: check.checkIndicatorRadius
        color: check.checked
               ? check.checkedFill
               : check.down
                 ? (check.theme.pressedBg || "#E5E7EB")
                 : check.hovered
                   ? (check.theme.hoverBg || "#F3F4F6")
                   : check.uncheckedFill
        border.width: check.activeFocus ? 2 : 1
        border.color: check.activeFocus
                      ? check.focusBorder
                      : check.checked
                        ? check.checkedFill
                        : check.uncheckedBorder
        opacity: check.enabled ? 1 : 0.55

        Canvas {
            id: checkMark
            anchors.fill: parent
            visible: check.checked
            opacity: check.enabled ? 1 : 0.65

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.lineWidth = 2.2
                ctx.lineCap = "round"
                ctx.lineJoin = "round"
                ctx.strokeStyle = "#FFFFFF"
                ctx.beginPath()
                ctx.moveTo(width * 0.28, height * 0.52)
                ctx.lineTo(width * 0.43, height * 0.67)
                ctx.lineTo(width * 0.73, height * 0.34)
                ctx.stroke()
            }

            Connections {
                target: check
                function onCheckedChanged() {
                    checkMark.requestPaint()
                }
            }
        }
    }

    contentItem: Text {
        text: check.text
        font: check.font
        color: check.enabled ? check.theme.titleInk : check.disabledInk
        verticalAlignment: Text.AlignVCenter
        leftPadding: check.indicator.width + check.spacing
    }
}

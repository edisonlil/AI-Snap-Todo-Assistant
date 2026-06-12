import QtQuick

Rectangle {
    id: buttonRoot
    required property var theme
    property string label: ""
    property bool primary: false
    property color fillColor: primary ? (theme.buttonPrimaryBg || theme.accent || "#2A313F") : (theme.buttonDefaultBg || "#FFFFFF")
    property color hoverColor: primary ? (theme.buttonPrimaryBgHover || fillColor) : (theme.buttonDefaultBgHover || theme.hoverBg || fillColor)
    property color pressedColor: primary ? (theme.buttonPrimaryBgPressed || hoverColor) : (theme.buttonDefaultBgPressed || theme.pressedBg || hoverColor)
    property color inkColor: primary ? (theme.buttonPrimaryInk || "#FFFFFF") : (theme.buttonDefaultInk || theme.bodyInk || "#4A5565")
    property color disabledFillColor: theme.buttonDisabledBg || theme.panelAltBg || "#F2F4F7"
    property color disabledInkColor: theme.buttonDisabledInk || theme.mutedInk || "#98A2B3"
    property int strokeWidth: 1
    property color strokeColor: primary ? fillColor : (theme.buttonBorder || theme.panelLine || "#E5E7EB")
    signal clicked

    radius: theme.buttonRadius || 6
    color: !enabled ? disabledFillColor : buttonMouse.pressed ? pressedColor : buttonMouse.containsMouse ? hoverColor : fillColor
    border.width: strokeWidth
    border.color: buttonRoot.strokeWidth > 0 ? buttonRoot.strokeColor : buttonRoot.color
    implicitWidth: buttonText.implicitWidth + (theme.buttonPaddingH || 14) * 2
    implicitHeight: theme.buttonHeight || 35

    Text {
        id: buttonText
        anchors.centerIn: parent
        text: buttonRoot.label
        color: buttonRoot.enabled ? buttonRoot.inkColor : buttonRoot.disabledInkColor
        font.family: theme.uiFont
        font.pixelSize: theme.buttonFontSize || theme.fontBody || 12
        font.weight: 700
    }

    MouseArea {
        id: buttonMouse
        anchors.fill: parent
        enabled: buttonRoot.enabled
        hoverEnabled: true
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: buttonRoot.clicked()
    }
}

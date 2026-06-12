import QtQuick
import QtQuick.Controls

TextField {
    id: input
    required property var theme
    property int minimumValue: 0
    property int maximumValue: 999
    property int stepSize: 1
    property bool compact: false
    property int fieldRadius: compact ? (theme.formFieldCompactRadius || 6) : (theme.componentRadius || theme.formFieldRadius || 8)
    property int fieldHeight: compact ? (theme.formFieldCompactHeight || 28) : (theme.componentHeight || theme.formFieldHeight || 36)
    property int fieldFontSize: theme.formFieldCompactFontSize || theme.fontBody || 12
    property color fieldBg: theme.formFieldBg || theme.inputBg || "#FFFFFF"
    property color fieldBorder: theme.formFieldBorder || theme.panelLine || "#E5E7EB"
    property color fieldFocusBorder: theme.formFieldFocusBorder || theme.accent || "#2A313F"
    signal valueEdited(int value)

    function normalizedValue(value) {
        var parsed = Number(value)
        if (!isFinite(parsed)) {
            parsed = input.minimumValue
        }
        return Math.max(input.minimumValue, Math.min(input.maximumValue, Math.round(parsed)))
    }

    function commitValue(value) {
        var nextValue = normalizedValue(value)
        text = String(nextValue)
        valueEdited(nextValue)
    }

    implicitWidth: 140
    implicitHeight: fieldHeight
    color: theme.titleInk
    font.family: theme.uiFont
    font.pixelSize: fieldFontSize
    selectByMouse: true
    inputMethodHints: Qt.ImhDigitsOnly
    leftPadding: 12
    rightPadding: 34
    topPadding: Math.max(4, Math.round((fieldHeight - fieldFontSize - 4) / 2))
    bottomPadding: topPadding
    verticalAlignment: TextInput.AlignVCenter
    onTextEdited: valueEdited(normalizedValue(text))
    onEditingFinished: commitValue(text)

    Keys.onUpPressed: function(event) {
        commitValue(normalizedValue(text) + stepSize)
        event.accepted = true
    }

    Keys.onDownPressed: function(event) {
        commitValue(normalizedValue(text) - stepSize)
        event.accepted = true
    }

    background: Rectangle {
        radius: input.fieldRadius
        color: input.fieldBg
        border.width: 1
        border.color: input.activeFocus ? input.fieldFocusBorder : input.fieldBorder
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        text: "px"
        color: input.theme.bodyInk
        font.family: input.theme.uiFont
        font.pixelSize: input.fieldFontSize
        font.weight: 700
    }
}

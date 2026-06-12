import QtQuick

Rectangle {
    id: spin
    required property var theme
    property int from: 0
    property int to: 99
    property int stepSize: 1
    property bool editable: true
    property int value: 0
    property int fieldRadius: theme.componentRadius || theme.formFieldRadius || 8
    property int fieldFontSize: theme.formFieldFontSize || theme.fontBody || 12
    property color fieldBg: theme.formFieldBg || theme.inputBg || "#FFFFFF"
    property color fieldBorder: theme.formFieldBorder || theme.panelLine || "#E5E7EB"
    property color fieldFocusBorder: theme.formFieldFocusBorder || theme.accent || "#2A313F"
    readonly property int stepButtonWidth: Math.max(36, implicitHeight)
    readonly property color stepInk: theme.labelInk || "#667085"
    readonly property color stepDisabledInk: theme.mutedInk || "#A9B1BD"
    readonly property color stepHoverBg: theme.hoverBg || "#F3F4F6"
    readonly property color stepPressedBg: theme.pressedBg || "#E5E7EB"
    readonly property bool canDecrease: enabled && value > from
    readonly property bool canIncrease: enabled && value < to
    signal valueModified

    function clampValue(source) {
        var parsed = Number(source)
        if (!isFinite(parsed)) {
            parsed = spin.from
        }
        return Math.max(spin.from, Math.min(spin.to, Math.round(parsed)))
    }

    function commitValue(source) {
        var nextValue = clampValue(source)
        if (spin.value !== nextValue) {
            spin.value = nextValue
            valueModified()
        } else {
            valueInput.text = String(nextValue)
        }
    }

    function stepBy(delta) {
        commitValue(spin.value + delta * spin.stepSize)
    }

    implicitWidth: 120
    implicitHeight: theme.componentHeight || theme.formFieldHeight || 36
    radius: fieldRadius
    color: "transparent"
    clip: true

    onValueChanged: {
        var nextText = String(clampValue(value))
        if (valueInput.text !== nextText) {
            valueInput.text = nextText
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: spin.fieldRadius
        color: spin.fieldBg
        border.width: 1
        border.color: valueInput.activeFocus ? spin.fieldFocusBorder : spin.fieldBorder
    }

    Rectangle {
        id: decreaseButton
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: 1
        width: spin.stepButtonWidth
        radius: Math.max(0, spin.fieldRadius - 1)
        color: "transparent"
        clip: true

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: parent.width + spin.fieldRadius
            radius: parent.radius
            color: !spin.canDecrease ? "transparent" : decreaseMouse.pressed ? spin.stepPressedBg : decreaseMouse.containsMouse ? spin.stepHoverBg : "transparent"
        }

        Text {
            anchors.centerIn: parent
            text: "-"
            color: spin.canDecrease ? spin.stepInk : spin.stepDisabledInk
            font.family: spin.theme.uiFont
            font.pixelSize: spin.fieldFontSize + 6
            font.weight: 400
        }

        MouseArea {
            id: decreaseMouse
            anchors.fill: parent
            enabled: spin.canDecrease
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: spin.stepBy(-1)
        }
    }

    Rectangle {
        anchors.left: decreaseButton.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: 1
        anchors.bottomMargin: 1
        width: 1
        color: spin.fieldBorder
    }

    TextInput {
        id: valueInput
        anchors.left: decreaseButton.right
        anchors.right: increaseButton.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        text: String(spin.clampValue(spin.value))
        clip: true
        color: spin.enabled ? spin.theme.titleInk : spin.stepDisabledInk
        selectionColor: spin.theme.accentSoft || "#F1F3F6"
        selectedTextColor: spin.theme.titleInk
        font.family: spin.theme.uiFont
        font.pixelSize: spin.fieldFontSize
        horizontalAlignment: TextInput.AlignHCenter
        verticalAlignment: TextInput.AlignVCenter
        readOnly: !spin.editable || !spin.enabled
        selectByMouse: spin.editable && spin.enabled
        inputMethodHints: Qt.ImhDigitsOnly
        validator: IntValidator {
            bottom: spin.from
            top: spin.to
        }
        onTextEdited: spin.commitValue(text)
        onEditingFinished: spin.commitValue(text)

        Keys.onUpPressed: function(event) {
            spin.stepBy(1)
            event.accepted = true
        }

        Keys.onDownPressed: function(event) {
            spin.stepBy(-1)
            event.accepted = true
        }
    }

    Rectangle {
        anchors.right: increaseButton.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.topMargin: 1
        anchors.bottomMargin: 1
        width: 1
        color: spin.fieldBorder
    }

    Rectangle {
        id: increaseButton
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.margins: 1
        width: spin.stepButtonWidth
        radius: Math.max(0, spin.fieldRadius - 1)
        color: "transparent"
        clip: true

        Rectangle {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: parent.width + spin.fieldRadius
            radius: parent.radius
            color: !spin.canIncrease ? "transparent" : increaseMouse.pressed ? spin.stepPressedBg : increaseMouse.containsMouse ? spin.stepHoverBg : "transparent"
        }

        Text {
            anchors.centerIn: parent
            text: "+"
            color: spin.canIncrease ? spin.stepInk : spin.stepDisabledInk
            font.family: spin.theme.uiFont
            font.pixelSize: spin.fieldFontSize + 8
            font.weight: 300
        }

        MouseArea {
            id: increaseMouse
            anchors.fill: parent
            enabled: spin.canIncrease
            hoverEnabled: true
            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
            onClicked: spin.stepBy(1)
        }
    }
}

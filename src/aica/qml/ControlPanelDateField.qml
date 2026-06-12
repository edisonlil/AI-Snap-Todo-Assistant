import QtQuick

Rectangle {
    id: field
    required property var theme
    property string text: ""
    property string placeholderText: ""
    readonly property bool hasValue: text.length > 0
    signal clicked

    implicitHeight: theme.componentHeight || theme.formFieldHeight || 36
    radius: theme.componentRadius || theme.formFieldRadius || 8
    color: theme.formFieldBg || theme.inputBg || "#FFFFFF"
    border.width: 1
    border.color: theme.formFieldBorder || theme.panelLine || "#E5E7EB"

    Text {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: theme.formFieldPaddingH || 14
        anchors.right: arrow.left
        anchors.rightMargin: 10
        text: field.hasValue ? field.text : field.placeholderText
        color: field.hasValue ? theme.titleInk : (theme.formFieldPlaceholderInk || theme.labelInk)
        font.family: theme.uiFont
        font.pixelSize: theme.formFieldFontSize || theme.fontBody || 12
        elide: Text.ElideRight
    }

    Text {
        id: arrow
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.rightMargin: theme.formFieldPaddingH || 14
        text: "▼"
        color: theme.labelInk
        font.family: theme.uiFont
        font.pixelSize: theme.formFieldFontSize || theme.fontBody || 12
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: field.clicked()
    }
}

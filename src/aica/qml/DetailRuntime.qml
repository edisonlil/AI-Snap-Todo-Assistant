import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var theme
    property string backLabel: "返回列表"
    property string title: ""
    property string description: ""
    property bool showBackButton: true
    property int contentSpacing: 12
    readonly property color surfaceColor: theme.panelAltBg
    readonly property color lineColor: theme.panelLine
    readonly property color titleColor: theme.titleInk
    readonly property color bodyColor: theme.bodyInk
    readonly property color buttonDefaultBg: theme.buttonDefaultBg
    readonly property color buttonPrimaryBg: theme.buttonPrimaryBg
    property alias actionContent: actionSlot.data
    property alias bodyContent: bodySlot.data
    property alias footerContent: footerSlot.data
    signal backRequested()

    spacing: contentSpacing

    Rectangle {
        visible: root.showBackButton
            || root.title.length > 0
            || root.description.length > 0
            || actionSlot.children.length > 0
        Layout.fillWidth: true
        implicitHeight: detailHeaderRow.implicitHeight + 24
        radius: 12
        color: root.surfaceColor
        border.width: 0

        RowLayout {
            id: detailHeaderRow
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            ControlPanelPlainButton {
                visible: root.showBackButton
                theme: root.theme
                label: root.backLabel
                onClicked: root.backRequested()
            }

            ColumnLayout {
                visible: root.title.length > 0 || root.description.length > 0
                Layout.fillWidth: true
                spacing: 4

                Text {
                    visible: root.title.length > 0
                    Layout.fillWidth: true
                    text: root.title
                    color: root.titleColor
                    font.family: theme.uiFont
                    font.pixelSize: 15
                    font.weight: 700
                    elide: Text.ElideRight
                }

                Text {
                    visible: root.description.length > 0
                    Layout.fillWidth: true
                    text: root.description
                    color: root.bodyColor
                    font.family: theme.uiFont
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
            }

            Item {
                visible: root.title.length === 0 && root.description.length === 0
                Layout.fillWidth: true
            }

            RowLayout {
                id: actionSlot
                visible: children.length > 0
                spacing: 10
            }
        }
    }

    ColumnLayout {
        id: bodySlot
        Layout.fillWidth: true
        spacing: root.contentSpacing
    }

    ColumnLayout {
        id: footerSlot
        visible: children.length > 0
        Layout.fillWidth: true
        spacing: root.contentSpacing
    }
}

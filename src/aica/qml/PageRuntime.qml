import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var theme
    property bool showHeader: false
    property string title: ""
    property string description: ""
    property int pageGap: 12
    property int sectionPadding: 16
    property int sectionRadius: 12
    property int compactBreakpoint: 760
    property int listMinimumHeight: 520
    property bool listFramed: true
    readonly property color surfaceColor: theme.panelAltBg
    readonly property color lineColor: theme.panelLine
    readonly property color titleColor: theme.titleInk
    readonly property color bodyColor: theme.bodyInk
    readonly property color accentColor: theme.accent
    property alias filterContent: filterSlot.data
    property alias actionContent: actionSlot.data
    property alias listContent: listSlot.data
    property alias footerContent: footerSlot.data

    spacing: pageGap

    ColumnLayout {
        visible: root.showHeader && (root.title.length > 0 || root.description.length > 0)
        Layout.fillWidth: true
        spacing: 6

        Text {
            visible: root.title.length > 0
            Layout.fillWidth: true
            text: root.title
            color: root.titleColor
            font.family: theme.uiFont
            font.pixelSize: 20
            font.weight: 700
            elide: Text.ElideRight
        }

        Text {
            visible: root.description.length > 0
            Layout.fillWidth: true
            text: root.description
            color: root.bodyColor
            font.family: theme.uiFont
            font.pixelSize: 12
            wrapMode: Text.Wrap
        }
    }

    Rectangle {
        visible: filterSlot.children.length > 0
        Layout.fillWidth: true
        implicitHeight: filterSlot.implicitHeight + root.sectionPadding * 2
        radius: root.sectionRadius
        color: root.surfaceColor
        border.width: 0

        ColumnLayout {
            id: filterSlot
            anchors.fill: parent
            anchors.margins: root.sectionPadding
            spacing: 10
        }
    }

    Rectangle {
        visible: actionSlot.children.length > 0
        Layout.fillWidth: true
        implicitHeight: actionSlot.implicitHeight + root.sectionPadding * 2
        radius: root.sectionRadius
        color: root.surfaceColor
        border.width: 0

        ColumnLayout {
            id: actionSlot
            anchors.fill: parent
            anchors.margins: root.sectionPadding
            spacing: 10
        }
    }

    Rectangle {
        visible: listSlot.children.length > 0 || footerSlot.children.length > 0
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: root.listMinimumHeight
        implicitHeight: Math.max(root.listMinimumHeight, listBody.implicitHeight)
        radius: root.listFramed ? root.sectionRadius : 0
        color: root.listFramed ? root.surfaceColor : "transparent"
        border.width: 0
        clip: true

        ColumnLayout {
            id: listBody
            anchors.fill: parent
            spacing: 0

            ColumnLayout {
                id: listSlot
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0
            }

            ColumnLayout {
                id: footerSlot
                visible: children.length > 0
                Layout.fillWidth: true
                spacing: 0
            }
        }
    }
}

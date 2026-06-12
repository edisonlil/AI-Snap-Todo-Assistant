import QtQuick
import QtQml

Rectangle {
    id: root
    width: 286
    height: 194
    color: "transparent"

    readonly property var bridge: (typeof todoPanelBridge !== "undefined" && todoPanelBridge) ? todoPanelBridge : fallbackBridge
    readonly property var themeTokens: typeof theme !== "undefined" ? theme : ({})
    readonly property color panelBg: themeTokens.panelBg || "#FFFFFF"
    readonly property color panelAltBg: themeTokens.panelAltBg || "#F8F9FA"
    readonly property color panelLine: themeTokens.panelLine || "#E5E7EB"
    readonly property color titleInk: themeTokens.titleInk || "#2A313F"
    readonly property color bodyInk: themeTokens.bodyInk || "#4A5565"
    readonly property color labelInk: themeTokens.labelInk || "#7C8795"
    readonly property color accent: themeTokens.accent || "#2A313F"
    readonly property color accentSoft: themeTokens.accentSoft || "#ECEFF3"
    readonly property color hoverBg: themeTokens.hoverBg || "#F3F4F6"
    readonly property string uiFont: themeTokens.uiFont || "Microsoft YaHei UI"
    readonly property int radiusLg: themeTokens.radiusLg || 16
    readonly property int radiusCard: themeTokens.radiusCard || 20
    readonly property int fontTiny: themeTokens.fontTiny || 10
    readonly property int fontCaption: themeTokens.fontCaption || 11
    readonly property int fontBody: themeTokens.fontBody || 12
    readonly property int outerPadding: 12
    readonly property int headerHeight: 26
    readonly property int sectionGap: 6
    readonly property int rowHeight: 30
    readonly property int rowSpacing: 2
    readonly property int listBottomInset: 2
    readonly property int listViewportHeight: Math.max(
        0,
        height - outerPadding * 2 - headerHeight - (root.bridge.minimized ? 0 : sectionGap) - listBottomInset
    )

    QtObject {
        id: fallbackBridge

        readonly property var todos: []
        readonly property int todoCount: 0
        readonly property bool minimized: false
        readonly property bool pinned: true
        readonly property bool canExpand: false
        readonly property bool hasSelected: false
        readonly property string expandLabel: ""
        readonly property string logoSource: ""
        readonly property string headerStatusText: todoCount + " 进行中"

        function startDrag() {}
        function moveDrag() {}
        function endDrag() {}
        function toggleExpanded() {}
        function toggleMinimized() {}
        function togglePinned() {}
        function clearSelection() {}
        function selectTodo(todoId) {}
        function requestDetail(todoId) {}
    }

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: root.bridge.minimized ? height / 2 : root.radiusCard
        color: root.panelBg
        opacity: 1
        border.width: 0
        border.color: "transparent"
        antialiasing: true

        Column {
            anchors.fill: parent
            anchors.margins: root.outerPadding
            spacing: root.bridge.minimized ? 0 : root.sectionGap

            Item {
                width: parent.width
                height: root.headerHeight

                MouseArea {
                    anchors.fill: parent
                    onPressed: root.bridge.startDrag()
                    onPositionChanged: root.bridge.moveDrag()
                    onReleased: root.bridge.endDrag()
                }

                Row {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8

                    Image {
                        width: 24
                        height: 24
                        source: root.bridge.logoSource
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        mipmap: true
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.verticalCenterOffset: 1
                        text: root.bridge.headerStatusText
                        font.family: root.uiFont
                        font.pixelSize: root.fontCaption
                        color: root.labelInk
                    }
                }

                Text {
                    id: expandLabel
                    anchors.right: minimizeButton.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.bridge.canExpand && !root.bridge.minimized
                    text: root.bridge.expandLabel
                    font.family: root.uiFont
                    font.pixelSize: root.fontTiny
                    color: root.labelInk

                    MouseArea {
                        anchors.fill: parent
                        onClicked: function(mouse) {
                            mouse.accepted = true
                            root.bridge.toggleExpanded()
                        }
                    }
                }

                Rectangle {
                    id: minimizeButton
                    anchors.right: clearButton.visible ? clearButton.left : pinButton.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    radius: 999
                    color: root.panelBg
                    border.width: 1
                    border.color: root.panelLine
                    width: 24
                    height: 24

                    Text {
                        anchors.centerIn: parent
                        text: root.bridge.minimized ? "+" : "−"
                        font.family: root.uiFont
                        font.pixelSize: 14
                        color: root.bodyInk
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: function(mouse) {
                            mouse.accepted = true
                            root.bridge.toggleMinimized()
                        }
                    }
                }

                Rectangle {
                    id: clearButton
                    anchors.right: pinButton.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.bridge.hasSelected
                    radius: 999
                    color: root.panelBg
                    border.width: 1
                    border.color: root.panelLine
                    width: clearLabel.width + 14
                    height: 24

                    Text {
                        id: clearLabel
                        anchors.centerIn: parent
                        text: "清除选中"
                        font.family: root.uiFont
                        font.pixelSize: root.fontTiny
                        color: root.bodyInk
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: function(mouse) {
                            mouse.accepted = true
                            root.bridge.clearSelection()
                        }
                    }
                }

                Rectangle {
                    id: pinButton
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    radius: 999
                    width: 24
                    height: 24
                    color: root.bridge.pinned ? "#ECEFF3" : "#FFFFFF"
                    border.width: 1
                    border.color: root.bridge.pinned ? "#2A313F" : "#E5E7EB"

                    Item {
                        anchors.centerIn: parent
                        width: 12
                        height: 12
                        rotation: root.bridge.pinned ? 0 : 32

                        readonly property color pinColor: root.bridge.pinned ? "#2A313F" : "#6E6E6E"

                        Rectangle {
                            x: 1
                            y: 1
                            width: 10
                            height: 3
                            radius: 1.5
                            color: parent.pinColor
                        }

                        Rectangle {
                            x: 5
                            y: 3
                            width: 2
                            height: 5
                            radius: 1
                            color: parent.pinColor
                        }

                        Rectangle {
                            x: 4
                            y: 7
                            width: 4
                            height: 2
                            radius: 1
                            color: parent.pinColor
                            rotation: 45
                            transformOrigin: Item.Left
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: function(mouse) {
                            mouse.accepted = true
                            root.bridge.togglePinned()
                        }
                    }
                }
            }

            Item {
                id: listViewport
                width: parent.width
                height: root.bridge.minimized ? 0 : root.listViewportHeight
                clip: true
                visible: !root.bridge.minimized

                Flickable {
                    id: listFlick
                    anchors.fill: parent
                    clip: true
                    contentWidth: width
                    contentHeight: listColumn.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds

                    Column {
                        id: listColumn
                        width: Math.max(0, listFlick.width - 6)
                        spacing: root.rowSpacing

                        Repeater {
                            model: root.bridge.todos

                            delegate: Rectangle {
                                width: listColumn.width
                                height: root.rowHeight
                                radius: 15
                                color: modelData.selected ? "#F5F5F5" : "transparent"
                                border.width: 0
                                border.color: "transparent"
                                antialiasing: true

                                Rectangle {
                                    id: radioButton
                                    x: 10
                                    width: 18
                                    height: 18
                                    radius: 9
                                    anchors.verticalCenter: parent.verticalCenter
                                    color: "#FFFFFF"
                                    border.width: 1.5
                                    border.color: modelData.selected ? "#2A313F" : "#C8C8C8"

                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: modelData.selected ? 8 : 0
                                        height: modelData.selected ? 8 : 0
                                        radius: 4
                                        color: "#2A313F"
                                        visible: modelData.selected
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: function(mouse) {
                                            mouse.accepted = true
                                            root.bridge.selectTodo(modelData.id)
                                        }
                                    }
                                }

                                Text {
                                    id: titleText
                                    x: 38
                                    width: parent.width - x - 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: modelData.title
                                    elide: Text.ElideRight
                                    wrapMode: Text.NoWrap
                                    maximumLineCount: 1
                                    font.pixelSize: 10
                                    font.weight: modelData.selected ? 600 : 500
                                    color: "#141414"
                                }

                                MouseArea {
                                    anchors.verticalCenter: titleText.verticalCenter
                                    x: titleText.x
                                    width: titleText.width
                                    height: parent.height
                                    onClicked: function(mouse) {
                                        mouse.accepted = true
                                        root.bridge.requestDetail(modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.rightMargin: 0
                    y: 4 + (listFlick.contentY / Math.max(1, listFlick.contentHeight - listFlick.height)) * (parent.height - height - 8)
                    width: 3
                    height: Math.max(24, (listFlick.height / Math.max(listFlick.contentHeight, 1)) * (parent.height - 8))
                    radius: 1.5
                    color: "#D1D5DB"
                    visible: listFlick.contentHeight > listFlick.height + 2
                }
            }
        }
    }
}

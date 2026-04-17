import QtQuick

Rectangle {
    id: root
    width: 286
    height: 194
    color: "transparent"

    readonly property int outerPadding: 12
    readonly property int headerHeight: 26
    readonly property int sectionGap: 6
    readonly property int rowHeight: 30
    readonly property int rowSpacing: 2
    readonly property int listBottomInset: 2
    readonly property int listViewportHeight: Math.max(
        0,
        height - outerPadding * 2 - headerHeight - (todoPanelBridge.minimized ? 0 : sectionGap) - listBottomInset
    )

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: 30
        color: "#FFFFFF"
        opacity: 1
        border.width: 0
        border.color: "transparent"
        antialiasing: true

        Column {
            anchors.fill: parent
            anchors.margins: root.outerPadding
            spacing: todoPanelBridge.minimized ? 0 : root.sectionGap

            Item {
                width: parent.width
                height: root.headerHeight

                MouseArea {
                    anchors.fill: parent
                    onPressed: todoPanelBridge.startDrag()
                    onPositionChanged: todoPanelBridge.moveDrag()
                    onReleased: todoPanelBridge.endDrag()
                }

                Text {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: "待办"
                    font.pixelSize: 14
                    font.weight: 600
                    color: "#121212"
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 40
                    anchors.verticalCenter: parent.verticalCenter
                    text: todoPanelBridge.todoCount + " 进行中"
                    font.pixelSize: 11
                    color: "#7B7B7B"
                }

                Text {
                    id: expandLabel
                    anchors.right: minimizeButton.left
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    visible: todoPanelBridge.canExpand && !todoPanelBridge.minimized
                    text: todoPanelBridge.expandLabel
                    font.pixelSize: 10
                    color: "#9B9B9B"

                    MouseArea {
                        anchors.fill: parent
                        onClicked: function(mouse) {
                            mouse.accepted = true
                            todoPanelBridge.toggleExpanded()
                        }
                    }
                }

                Rectangle {
                    id: minimizeButton
                    anchors.right: clearButton.visible ? clearButton.left : parent.right
                    anchors.rightMargin: clearButton.visible ? 8 : 0
                    anchors.verticalCenter: parent.verticalCenter
                    radius: 999
                    color: "#FFFDFC"
                    border.width: 1
                    border.color: "#ECE7DE"
                    width: 24
                    height: 24

                    Text {
                        anchors.centerIn: parent
                        text: todoPanelBridge.minimized ? "+" : "−"
                        font.pixelSize: 14
                        color: "#5D5D5D"
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: function(mouse) {
                            mouse.accepted = true
                            todoPanelBridge.toggleMinimized()
                        }
                    }
                }

                Rectangle {
                    id: clearButton
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    visible: todoPanelBridge.hasSelected
                    radius: 999
                    color: "#FFFDFC"
                    border.width: 1
                    border.color: "#ECE7DE"
                    width: clearLabel.width + 14
                    height: 24

                    Text {
                        id: clearLabel
                        anchors.centerIn: parent
                        text: "清除选中"
                        font.pixelSize: 10
                        color: "#5D5D5D"
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: function(mouse) {
                            mouse.accepted = true
                            todoPanelBridge.clearSelection()
                        }
                    }
                }
            }

            Item {
                id: listViewport
                width: parent.width
                height: todoPanelBridge.minimized ? 0 : root.listViewportHeight
                clip: true
                visible: !todoPanelBridge.minimized

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
                            model: todoPanelBridge.todos

                            delegate: Rectangle {
                                width: listColumn.width
                                height: root.rowHeight
                                radius: 15
                                color: modelData.selected ? "#FFFEFC" : "transparent"
                                border.width: 0
                                border.color: "transparent"
                                antialiasing: true

                                Rectangle {
                                    id: radioButton
                                    x: 4
                                    width: 18
                                    height: 18
                                    radius: 9
                                    anchors.verticalCenter: parent.verticalCenter
                                    color: "#FFFFFF"
                                    border.width: 1.5
                                    border.color: modelData.selected ? "#5E8CFF" : "#C8C8C8"

                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: modelData.selected ? 8 : 0
                                        height: modelData.selected ? 8 : 0
                                        radius: 4
                                        color: "#5E8CFF"
                                        visible: modelData.selected
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: function(mouse) {
                                            mouse.accepted = true
                                            todoPanelBridge.selectTodo(modelData.id)
                                        }
                                    }
                                }

                                Text {
                                    id: titleText
                                    x: 32
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
                                        todoPanelBridge.requestDetail(modelData.id)
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
                    color: "#D4D0C8"
                    visible: listFlick.contentHeight > listFlick.height + 2
                }
            }
        }
    }
}

import QtQuick

Rectangle {
    id: root
    width: 286
    height: 194
    color: "transparent"

    Rectangle {
        id: surface
        anchors.fill: parent
        radius: 30
        color: "#F7F6F2"
        opacity: 0.972
        border.width: 0
        border.color: "transparent"
        antialiasing: true

        MouseArea {
            anchors.fill: parent
            onClicked: todoPanelBridge.toggleExpanded()
        }

        Column {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 4

            Item {
                width: parent.width
                height: 26

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
                    anchors.right: clearButton.visible ? clearButton.left : parent.right
                    anchors.rightMargin: clearButton.visible ? 8 : 0
                    anchors.verticalCenter: parent.verticalCenter
                    visible: todoPanelBridge.canExpand
                    text: todoPanelBridge.expandLabel
                    font.pixelSize: 10
                    color: "#9B9B9B"
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
                        onClicked: {
                            mouse.accepted = true
                            todoPanelBridge.clearSelection()
                        }
                    }
                }
            }

            Repeater {
                model: todoPanelBridge.todos

                delegate: Rectangle {
                    id: rowItem
                    width: surface.width - 24
                    height: 30
                    radius: 15
                    color: modelData.selected ? "#FFFEFC" : "transparent"
                    border.width: 0
                    border.color: "transparent"
                    antialiasing: true
                    property real contentOffset: 0
                    property real actionWidth: 72
                    property real pressX: 0
                    property bool dragging: false

                        Rectangle {
                            id: completeReveal
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.right: parent.right
                            width: rowItem.actionWidth
                            radius: 15
                        color: "#EEF4FF"
                        border.width: 1
                        border.color: "#D6E4FB"
                        visible: rowItem.contentOffset < 0

                        Text {
                            anchors.centerIn: parent
                            text: "完成"
                            font.pixelSize: 10
                            color: "#275ED8"
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                mouse.accepted = true
                                todoPanelBridge.completeTodo(modelData.id)
                                rowItem.contentOffset = 0
                            }
                        }
                    }

                    Item {
                        id: contentLayer
                        anchors.fill: parent
                        x: rowItem.contentOffset

                        Rectangle {
                            id: radioButton
                            x: 4
                            width: 18
                            height: 18
                            radius: 9
                            anchors.verticalCenter: parent.verticalCenter
                            color: "#FFFFFF"
                            border.width: modelData.selected ? 1.5 : 1.5
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
                                onClicked: {
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
                            onClicked: {
                                mouse.accepted = true
                                todoPanelBridge.requestDetail(modelData.id)
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            propagateComposedEvents: true
                            onPressed: mouse => {
                                rowItem.pressX = mouse.x
                                rowItem.dragging = false
                            }
                            onPositionChanged: mouse => {
                                var delta = mouse.x - rowItem.pressX
                                if (delta < -6 || rowItem.contentOffset < 0) {
                                    rowItem.dragging = true
                                    rowItem.contentOffset = Math.max(-rowItem.actionWidth, Math.min(0, delta))
                                }
                            }
                            onReleased: {
                                if (rowItem.dragging) {
                                    rowItem.contentOffset = rowItem.contentOffset < -(rowItem.actionWidth / 2) ? -rowItem.actionWidth : 0
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

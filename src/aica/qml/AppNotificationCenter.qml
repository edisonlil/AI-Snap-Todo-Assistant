import QtQuick

Item {
    id: root
    property var bridge: null
    property string uiFont: "Microsoft YaHei UI"
    property real maxCardWidth: 336
    property real cardSpacing: 10

    implicitWidth: maxCardWidth
    implicitHeight: stackView.contentHeight
    width: implicitWidth
    height: implicitHeight

    ListView {
        id: stackView
        anchors.fill: parent
        anchors.rightMargin: 0
        anchors.bottomMargin: 0
        width: root.maxCardWidth
        height: contentHeight
        model: root.bridge ? root.bridge.notifications : []
        interactive: false
        clip: false
        spacing: root.cardSpacing
        verticalLayoutDirection: ListView.BottomToTop
        boundsBehavior: Flickable.StopAtBounds

        add: Transition {
            ParallelAnimation {
                NumberAnimation {
                    properties: "opacity,y"
                    from: 0
                    to: 1
                    duration: 180
                    easing.type: Easing.OutCubic
                }
            }
        }

        displaced: Transition {
            NumberAnimation {
                properties: "y"
                duration: 180
                easing.type: Easing.OutCubic
            }
        }

        move: Transition {
            NumberAnimation {
                properties: "y"
                duration: 180
                easing.type: Easing.OutCubic
            }
        }

        remove: Transition {
            ParallelAnimation {
                NumberAnimation {
                    properties: "opacity"
                    to: 0
                    duration: 220
                    easing.type: Easing.OutCubic
                }
                NumberAnimation {
                    properties: "y"
                    to: -8
                    duration: 220
                    easing.type: Easing.OutCubic
                }
            }
        }

        delegate: Item {
            id: notificationItem
            required property var modelData
            width: stackView.width
            implicitHeight: cardShell.implicitHeight
            height: implicitHeight

            Rectangle {
                id: cardShell
                width: parent.width
                implicitHeight: Math.max(70, contentColumn.implicitHeight + 22)
                radius: 18
                color: "#FFFFFF"
                border.width: 1
                border.color: "#E5E7EB"

                Rectangle {
                    width: 1
                    color: "#F3F4F6"
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    visible: false
                }

                Column {
                    id: contentColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 14
                    spacing: 6

                    Row {
                        spacing: 8

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 4
                            anchors.verticalCenter: parent.verticalCenter
                            color: {
                                if (modelData.level === "error") {
                                    return "#B42318"
                                }
                                if (modelData.level === "warning") {
                                    return "#B7791F"
                                }
                                if (modelData.level === "success") {
                                    return "#17663A"
                                }
                                return "#4A5565"
                            }
                        }

                        Text {
                            text: {
                                if (modelData.level === "error") {
                                    return "错误"
                                }
                                if (modelData.level === "warning") {
                                    return "提醒"
                                }
                                if (modelData.level === "success") {
                                    return "完成"
                                }
                                return "通知"
                            }
                            color: "#18202E"
                            font.family: root.uiFont
                            font.pixelSize: 11
                            font.weight: 600
                        }
                    }

                    Text {
                        width: parent.width
                        text: String(modelData.message || "")
                        color: "#4A5565"
                        font.family: root.uiFont
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        lineHeight: 1.15
                    }
                }
            }
        }
    }
}

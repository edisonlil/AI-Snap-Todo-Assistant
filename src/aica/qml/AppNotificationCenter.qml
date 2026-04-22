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

    function _indexOfNotification(notificationId) {
        for (var index = 0; index < displayModel.count; index += 1) {
            if (displayModel.get(index).id === notificationId) {
                return index
            }
        }
        return -1
    }

    function syncNotifications() {
        var source = bridge ? (bridge.notifications || []) : []

        for (var removeIndex = displayModel.count - 1; removeIndex >= 0; removeIndex -= 1) {
            var existingId = displayModel.get(removeIndex).id
            var stillExists = false
            for (var sourceIndex = 0; sourceIndex < source.length; sourceIndex += 1) {
                if (source[sourceIndex].id === existingId) {
                    stillExists = true
                    break
                }
            }
            if (!stillExists) {
                displayModel.remove(removeIndex)
            }
        }

        for (var updateIndex = 0; updateIndex < displayModel.count && updateIndex < source.length; updateIndex += 1) {
            displayModel.set(updateIndex, source[updateIndex])
        }

        for (var appendIndex = displayModel.count; appendIndex < source.length; appendIndex += 1) {
            displayModel.append(source[appendIndex])
        }
    }

    ListModel {
        id: displayModel
    }

    Connections {
        target: bridge

        function onNotificationsChanged() {
            root.syncNotifications()
        }
    }

    Component.onCompleted: syncNotifications()

    ListView {
        id: stackView
        anchors.fill: parent
        width: root.maxCardWidth
        height: contentHeight
        model: displayModel
        interactive: false
        clip: false
        spacing: root.cardSpacing
        verticalLayoutDirection: ListView.TopToBottom
        boundsBehavior: Flickable.StopAtBounds

        add: Transition {
            NumberAnimation {
                properties: "opacity"
                from: 0
                to: 1
                duration: 180
                easing.type: Easing.OutCubic
            }
        }

        addDisplaced: Transition {
            NumberAnimation {
                properties: "y"
                duration: 220
                easing.type: Easing.OutCubic
            }
        }

        displaced: Transition {
            NumberAnimation {
                properties: "y"
                duration: 220
                easing.type: Easing.OutCubic
            }
        }

        move: Transition {
            NumberAnimation {
                properties: "y"
                duration: 0
                easing.type: Easing.OutCubic
            }
        }

        removeDisplaced: Transition {
            NumberAnimation {
                properties: "y"
                duration: 220
                easing.type: Easing.OutCubic
            }
        }

        remove: Transition {
            NumberAnimation {
                properties: "opacity"
                to: 0
                duration: 260
                easing.type: Easing.OutCubic
            }
        }

        delegate: Item {
            width: stackView.width
            implicitHeight: cardShell.implicitHeight
            height: implicitHeight

            Rectangle {
                id: cardShell
                width: parent.width
                implicitHeight: Math.max(70, contentColumn.implicitHeight + 24)
                radius: 18
                color: "#FFFFFF"
                border.width: 1
                border.color: "#E5E7EB"

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
                                if (level === "error") {
                                    return "#B42318"
                                }
                                if (level === "warning") {
                                    return "#B7791F"
                                }
                                if (level === "success") {
                                    return "#17663A"
                                }
                                return "#4A5565"
                            }
                        }

                        Text {
                            text: {
                                if (level === "error") {
                                    return "错误"
                                }
                                if (level === "warning") {
                                    return "提醒"
                                }
                                if (level === "success") {
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
                        text: String(message || "")
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

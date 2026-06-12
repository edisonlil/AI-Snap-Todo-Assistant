import QtQuick

Item {
    id: root
    property var bridge: null
    property string uiFont: "Microsoft YaHei UI"
    property var theme: ({})
    readonly property color panelBg: theme.panelBg || "#FFFFFF"
    readonly property color panelLine: theme.panelLine || "#E5E7EB"
    readonly property color titleInk: theme.titleInk || "#18202E"
    readonly property color bodyInk: theme.bodyInk || "#4A5565"
    readonly property color errorInk: theme.errorInk || "#B42318"
    readonly property color warningInk: theme.warningInk || "#B7791F"
    readonly property color successInk: theme.successInk || "#17663A"
    readonly property int radiusLg: theme.radiusLg || 18
    readonly property int fontCaption: theme.fontCaption || 11
    readonly property int fontBodyLg: theme.fontBodyLg || 13
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
                radius: root.radiusLg
                color: root.panelBg
                border.width: 1
                border.color: root.panelLine

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
                                    return root.errorInk
                                }
                                if (level === "warning") {
                                    return root.warningInk
                                }
                                if (level === "success") {
                                    return root.successInk
                                }
                                return root.bodyInk
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
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: root.fontCaption
                            font.weight: 600
                        }
                    }

                    Text {
                        width: parent.width
                        text: String(message || "")
                        color: root.bodyInk
                        font.family: root.uiFont
                        font.pixelSize: root.fontBodyLg
                        wrapMode: Text.Wrap
                        lineHeight: 1.15
                    }
                }
            }
        }
    }
}

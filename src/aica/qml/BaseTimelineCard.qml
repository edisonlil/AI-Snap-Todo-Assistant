import QtQuick

Rectangle {
    id: baseCard
    width: parent ? parent.width : 0
    radius: 18
    color: rootContext ? rootContext.timelineBg : "#F7F7F4"
    border.width: 1
    border.color: rootContext ? rootContext.fieldLine : "#E7EDF5"
    implicitHeight: Math.max(124, contentColumn.implicitHeight + 28)

    property var rootContext
    property var todoDetailBridge
    property var eventData
    property string typeLabel: ""
    property string titleText: ""
    property string summaryText: ""
    property string status: ""
    property string statusLabel: ""
    property bool showDeleteAction: true
    property string expandActionLabel: ""
    property bool expanded: false
    property Component bodyComponent
    property Component actionsComponent
    property Component expandComponent
    property color bulletColor: status === "success"
                                 ? "#4B9A62"
                                 : (status === "failed" ? "#C9414B" : (rootContext ? rootContext.accent : "#3D7CFF"))

    readonly property color runningFill: "#EEF4FF"
    readonly property color runningInk: rootContext ? rootContext.accent : "#3D7CFF"
    readonly property color successFill: "#EAF7EE"
    readonly property color successInk: "#287D4E"
    readonly property color failedFill: "#FDECEC"
    readonly property color failedInk: "#C9414B"

    function statusFillColor() {
        if (status === "success") {
            return successFill
        }
        if (status === "failed") {
            return failedFill
        }
        return runningFill
    }

    function statusInkColor() {
        if (status === "success") {
            return successInk
        }
        if (status === "failed") {
            return failedInk
        }
        return runningInk
    }

    Column {
        id: contentColumn
        x: 16
        y: 14
        width: parent.width - 32
        spacing: 10

        Item {
            width: parent.width
            height: Math.max(metaColumn.implicitHeight, headerActionRow.height)

            Rectangle {
                x: 0
                y: 4
                width: 8
                height: 8
                radius: 4
                color: baseCard.bulletColor
            }

            Column {
                id: metaColumn
                x: 16
                y: 0
                spacing: 4

                Text {
                    text: eventData ? eventData.timeLabel : ""
                    color: rootContext ? rootContext.mutedInk : "#B3BBC8"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.bodyWeight : 400
                }

                Text {
                    text: typeLabel
                    color: rootContext ? rootContext.labelInk : "#9AA4B3"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500
                }
            }

            Row {
                id: headerActionRow
                anchors.right: parent.right
                anchors.top: parent.top
                spacing: 12
                height: 22

                Rectangle {
                    id: statusPill
                    visible: statusLabel.length > 0
                    width: statusText.implicitWidth + 16
                    height: 22
                    radius: 11
                    color: baseCard.statusFillColor()

                    Text {
                        id: statusText
                        anchors.centerIn: parent
                        text: statusLabel
                        color: baseCard.statusInkColor()
                        font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                        font.pixelSize: 10
                        font.weight: rootContext ? rootContext.labelWeight : 500
                    }
                }

                Item {
                    visible: showDeleteAction && eventData
                    width: deleteText.implicitWidth
                    height: parent.height

                    Text {
                        id: deleteText
                        anchors.verticalCenter: parent.verticalCenter
                        text: "删除"
                        color: "#E35B66"
                        font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                        font.pixelSize: 11
                        font.weight: rootContext ? rootContext.labelWeight : 500
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (todoDetailBridge && eventData && eventData.id) {
                                todoDetailBridge.deleteTimelineCard(eventData.id)
                            }
                        }
                    }
                }
            }
        }

        Column {
            width: parent.width
            spacing: 4
            visible: titleText.length > 0 || summaryText.length > 0

            Text {
                visible: titleText.length > 0
                width: parent.width
                text: titleText
                wrapMode: Text.Wrap
                color: rootContext ? rootContext.titleInk : "#18202E"
                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                font.pixelSize: 15
                font.weight: rootContext ? rootContext.sectionWeight : 600
            }

            Text {
                visible: summaryText.length > 0
                width: parent.width
                text: summaryText
                wrapMode: Text.Wrap
                color: rootContext ? rootContext.bodyInk : "#4A5565"
                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                font.pixelSize: 12
                font.weight: rootContext ? rootContext.bodyWeight : 400
                lineHeight: 18
                lineHeightMode: Text.FixedHeight
            }
        }

        Loader {
            id: bodyLoader
            width: parent.width
            sourceComponent: bodyComponent
            visible: bodyComponent !== undefined && bodyComponent !== null
        }

        Loader {
            id: actionsLoader
            width: parent.width
            sourceComponent: actionsComponent
            visible: actionsComponent !== undefined && actionsComponent !== null
        }

        Column {
            width: parent.width
            spacing: 8
            visible: (expandActionLabel.length > 0 || baseCard.expanded)
                     && expandComponent !== undefined
                     && expandComponent !== null

            Text {
                visible: expandActionLabel.length > 0
                text: expandActionLabel
                color: rootContext ? rootContext.accent : "#3D7CFF"
                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                font.pixelSize: 11
                font.weight: rootContext ? rootContext.labelWeight : 500

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: baseCard.expanded = !baseCard.expanded
                }
            }

            Rectangle {
                width: parent.width
                radius: 14
                color: "#FFFFFF"
                border.width: 1
                border.color: rootContext ? rootContext.fieldLine : "#E7EDF5"
                visible: baseCard.expanded
                implicitHeight: expandLoader.implicitHeight + 24

                Loader {
                    id: expandLoader
                    x: 12
                    y: 12
                    width: parent.width - 24
                    sourceComponent: expandComponent
                }
            }
        }
    }
}

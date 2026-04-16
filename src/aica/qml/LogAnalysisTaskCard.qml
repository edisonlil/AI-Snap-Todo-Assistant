import QtQuick

BaseTimelineCard {
    id: taskCard
    typeLabel: eventData && eventData.cardLabel ? eventData.cardLabel : "日志分析任务"
    titleText: "日志分析任务"
    summaryText: ""
    status: eventData ? eventData.status : ""
    statusLabel: eventData && eventData.statusLabel ? eventData.statusLabel : ""
    expandActionLabel: status === "running" ? "查看分析过程" : (status === "failed" ? "查看原因" : "")
    bodyComponent: bodySection
    actionsComponent: successActions
    expandComponent: expandSection

    function payloadValue() {
        return eventData && eventData.payload ? eventData.payload : {}
    }

    function commandText() {
        var payload = payloadValue()
        return String(payload.command_text || payload.raw_command || (eventData ? eventData.content : "") || "")
    }

    function currentStep() {
        var payload = payloadValue()
        return String(payload.current_step || "")
    }

    function failureReason() {
        var payload = payloadValue()
        return String(payload.failure_reason || "")
    }

    function failureDetails() {
        var payload = payloadValue()
        var details = payload.failure_details
        return Array.isArray(details) ? details : []
    }

    function processSteps() {
        var payload = payloadValue()
        var steps = payload.process_steps
        return Array.isArray(steps) ? steps : []
    }

    function resultEventId() {
        var payload = payloadValue()
        return String(payload.result_event_id || "")
    }

    Component {
        id: bodySection

        Item {
            width: taskCard.width ? taskCard.width - 32 : 0
            implicitHeight: bodyColumn.implicitHeight

            Column {
                id: bodyColumn
                width: parent.width
                spacing: 10

                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: taskCard.commandText()
                    color: rootContext ? rootContext.bodyInk : "#4A5565"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 13
                    font.weight: rootContext ? rootContext.bodyWeight : 400
                }

                Row {
                    visible: taskCard.status === "running"
                    spacing: 8

                    Item {
                        width: 34
                        height: 14

                        Repeater {
                            model: 3

                            delegate: Rectangle {
                                width: 6
                                height: 6
                                radius: 3
                                x: index * 10
                                y: 4
                                color: rootContext ? rootContext.accent : "#3D7CFF"
                                opacity: 0.28

                                SequentialAnimation on opacity {
                                    running: taskCard.status === "running"
                                    loops: Animation.Infinite
                                    NumberAnimation { to: 1.0; duration: 260 }
                                    NumberAnimation { to: 0.28; duration: 260 }
                                    PauseAnimation { duration: index * 140 }
                                }
                            }
                        }
                    }

                    Text {
                        text: taskCard.currentStep()
                        color: rootContext ? rootContext.accent : "#3D7CFF"
                        font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                        font.pixelSize: 12
                        font.weight: rootContext ? rootContext.labelWeight : 500
                    }
                }

                Text {
                    visible: taskCard.status === "running"
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "后台分析中，你可以继续补充跟进内容。"
                    color: rootContext ? rootContext.mutedInk : "#B3BBC8"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.bodyWeight : 400
                }

                Text {
                    visible: taskCard.status === "success"
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: "已生成分析结果"
                    color: "#287D4E"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 12
                    font.weight: rootContext ? rootContext.labelWeight : 500
                }

                Text {
                    visible: taskCard.status === "failed" && taskCard.failureReason().length > 0
                    width: parent.width
                    wrapMode: Text.Wrap
                    text: taskCard.failureReason()
                    color: "#C9414B"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 12
                    font.weight: rootContext ? rootContext.bodyWeight : 400
                }
            }
        }
    }

    Component {
        id: successActions

        Row {
            visible: taskCard.status === "success" && taskCard.resultEventId().length > 0
            spacing: 12

            Text {
                text: "查看结果"
                color: rootContext ? rootContext.accent : "#3D7CFF"
                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                font.pixelSize: 11
                font.weight: rootContext ? rootContext.labelWeight : 500

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (rootContext && taskCard.resultEventId().length > 0) {
                            rootContext.scrollToTimelineEvent(taskCard.resultEventId())
                        }
                    }
                }
            }
        }
    }

    Component {
        id: expandSection

        Item {
            width: taskCard.width ? taskCard.width - 56 : 0
            implicitHeight: expandColumn.implicitHeight

            Column {
                id: expandColumn
                width: parent.width
                spacing: 8

                Repeater {
                    visible: taskCard.status === "running"
                    model: taskCard.processSteps()

                    delegate: Row {
                        spacing: 10

                        Rectangle {
                            width: 10
                            height: 10
                            radius: 5
                            anchors.verticalCenter: parent.verticalCenter
                            border.width: 2
                            border.color: modelData.state === "done"
                                          ? (rootContext ? rootContext.accent : "#3D7CFF")
                                          : (modelData.state === "active" ? (rootContext ? rootContext.accent : "#3D7CFF") : "#D3DAE5")
                            color: modelData.state === "done" || modelData.state === "active"
                                   ? (rootContext ? rootContext.accent : "#3D7CFF")
                                   : "#FFFFFF"
                        }

                        Text {
                            text: modelData.label
                            color: modelData.state === "active"
                                   ? (rootContext ? rootContext.accent : "#3D7CFF")
                                   : (rootContext ? rootContext.bodyInk : "#4A5565")
                            font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                            font.pixelSize: 12
                            font.weight: modelData.state === "active"
                                         ? (rootContext ? rootContext.labelWeight : 500)
                                         : (rootContext ? rootContext.bodyWeight : 400)
                        }
                    }
                }

                Repeater {
                    visible: taskCard.status === "failed"
                    model: taskCard.failureDetails()

                    delegate: Row {
                        spacing: 8

                        Rectangle {
                            width: 6
                            height: 6
                            radius: 3
                            y: 7
                            color: "#E35B66"
                        }

                        Text {
                            width: parent.width - 16
                            wrapMode: Text.Wrap
                            text: String(modelData)
                            color: rootContext ? rootContext.bodyInk : "#4A5565"
                            font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                            font.pixelSize: 12
                            font.weight: rootContext ? rootContext.bodyWeight : 400
                        }
                    }
                }
            }
        }
    }
}

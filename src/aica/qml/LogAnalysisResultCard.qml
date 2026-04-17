import QtQuick

BaseTimelineCard {
    id: resultCard
    typeLabel: eventData && eventData.cardLabel ? eventData.cardLabel : "日志分析结果"
    titleText: "日志分析结果"
    status: "success"
    statusLabel: eventData && eventData.statusLabel ? eventData.statusLabel : "已生成"
    bodyComponent: bodySection
    actionsComponent: actionsSection

    function payloadValue() {
        return eventData && eventData.payload ? eventData.payload : {}
    }

    function materials() {
        var items = payloadValue().analyzed_materials
        return Array.isArray(items) ? items : []
    }

    function materialText() {
        var values = []
        var items = materials()
        for (var index = 0; index < items.length; index += 1) {
            var item = items[index]
            if (!item) {
                continue
            }
            var name = String(item.name || item.summary || "分析材料")
            values.push(name)
        }
        return values.length > 0 ? values.join("\n") : "未提供分析材料"
    }

    function findingsText() {
        return String(payloadValue().findings || "暂无关键发现")
    }

    function conclusionText() {
        return String(payloadValue().conclusion || payloadValue().judgment || "暂无分析结论")
    }

    function judgmentText() {
        return String(payloadValue().judgment || "暂无初步判断")
    }

    function nextStepsText() {
        return String(payloadValue().next_steps || "暂无建议下一步")
    }

    function sections() {
        return [
            { "title": "分析结论", "text": conclusionText() },
            { "title": "关键发现", "text": findingsText() },
            { "title": "建议下一步", "text": nextStepsText() },
            { "title": "已分析材料", "text": materialText() }
        ]
    }

    function fullCopyText() {
        var items = sections()
        var lines = []
        for (var index = 0; index < items.length; index += 1) {
            lines.push(items[index].title)
            lines.push(items[index].text)
            if (index < items.length - 1) {
                lines.push("")
            }
        }
        return lines.join("\n")
    }

    Component {
        id: actionsSection

        Row {
            spacing: 12

            Text {
                text: "复制结果"
                color: rootContext ? rootContext.accent : "#3D7CFF"
                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                font.pixelSize: 11
                font.weight: rootContext ? rootContext.labelWeight : 500

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (todoDetailBridge) {
                            todoDetailBridge.copyPlainText(resultCard.fullCopyText())
                        }
                    }
                }
            }
        }
    }

    Component {
        id: bodySection

        Item {
            width: resultCard.width ? resultCard.width - 32 : 0
            implicitHeight: sectionColumn.implicitHeight

            Column {
                id: sectionColumn
                width: parent.width
                spacing: 8

                Repeater {
                    model: resultCard.sections()

                    delegate: Rectangle {
                        width: sectionColumn.width
                        radius: 14
                        color: "#FFFFFF"
                        border.width: 0
                        implicitHeight: sectionContent.implicitHeight + 20

                        Column {
                            id: sectionContent
                            x: 12
                            y: 10
                            width: parent.width - 24
                            spacing: 6

                            Row {
                                width: parent.width
                                spacing: 10

                                Text {
                                    text: modelData.title
                                    color: rootContext ? rootContext.labelInk : "#9AA4B3"
                                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                    font.pixelSize: 11
                                    font.weight: rootContext ? rootContext.labelWeight : 500
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "复制"
                                    color: rootContext ? rootContext.accent : "#3D7CFF"
                                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                    font.pixelSize: 10
                                    font.weight: rootContext ? rootContext.labelWeight : 500

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (todoDetailBridge) {
                                                todoDetailBridge.copyPlainText(String(modelData.text || ""))
                                            }
                                        }
                                    }
                                }
                            }

                            Text {
                                width: parent.width
                                wrapMode: Text.Wrap
                                text: modelData.text
                                color: rootContext ? rootContext.bodyInk : "#4A5565"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 12
                                font.weight: rootContext ? rootContext.bodyWeight : 400
                                lineHeight: 18
                                lineHeightMode: Text.FixedHeight
                            }
                        }
                    }
                }
            }
        }
    }
}

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

    function splitTextLines(text) {
        var content = String(text || "").trim()
        if (content.length === 0) {
            return []
        }
        var parts = content.split("\n")
        var values = []
        for (var index = 0; index < parts.length; index += 1) {
            var line = String(parts[index] || "").trim()
            if (line.length > 0) {
                values.push(line)
            }
        }
        return values
    }

    function stringList(key) {
        var items = payloadValue()[key]
        var values = []
        if (items === undefined || items === null) {
            return values
        }
        if (typeof items === "string") {
            return splitTextLines(items)
        }
        if (Array.isArray(items) || typeof items.length === "number") {
            for (var index = 0; index < items.length; index += 1) {
                var text = String(items[index] || "").trim()
                if (text.length > 0) {
                    values.push(text)
                }
            }
        }
        return values
    }

    function conclusionText() {
        return String(payloadValue().conclusion || payloadValue().judgment || "暂无分析结论")
    }

    function sections() {
        var items = []
        items.push({ "title": "分析结论", "type": "paragraph", "text": conclusionText() })

        var findingLines = stringList("finding_lines")
        if (findingLines.length === 0) {
            findingLines = splitTextLines(payloadValue().findings || "")
        }
        if (findingLines.length > 0) {
            items.push({ "title": "关键依据", "type": "list", "lines": findingLines })
        }

        var nextStepLines = stringList("next_step_lines")
        if (nextStepLines.length === 0) {
            nextStepLines = splitTextLines(payloadValue().next_steps || "")
        }
        if (nextStepLines.length > 0) {
            items.push({ "title": "建议动作", "type": "list", "lines": nextStepLines })
        }

        var missingLines = stringList("missing_information_lines")
        if (missingLines.length === 0) {
            missingLines = stringList("missing_information")
        }
        if (missingLines.length > 0) {
            items.push({ "title": "待补充信息", "type": "list", "lines": missingLines })
        }

        var materialLines = stringList("material_lines")
        if (materialLines.length === 0) {
            materialLines = splitTextLines(payloadValue().materials || "")
        }
        if (materialLines.length === 0) {
            var materials = payloadValue().analyzed_materials
            if (Array.isArray(materials) || (materials && typeof materials.length === "number")) {
                for (var materialIndex = 0; materialIndex < materials.length; materialIndex += 1) {
                    var item = materials[materialIndex]
                    if (!item) {
                        continue
                    }
                    var summary = String(item.summary || item.name || "").trim()
                    if (summary.length > 0) {
                        materialLines.push(summary)
                    }
                }
            }
        }
        if (materialLines.length > 0) {
            items.push({ "title": "已分析材料", "type": "list", "lines": materialLines })
        }

        return items
    }

    function fullCopyText() {
        var items = sections()
        var lines = []
        for (var index = 0; index < items.length; index += 1) {
            var section = items[index]
            lines.push(section.title)
            if (section.type === "list") {
                for (var itemIndex = 0; itemIndex < section.lines.length; itemIndex += 1) {
                    lines.push("- " + section.lines[itemIndex])
                }
            } else {
                lines.push(section.text)
            }
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
                                            if (!todoDetailBridge) {
                                                return
                                            }
                                            if (modelData.type === "list") {
                                                todoDetailBridge.copyPlainText(modelData.lines.join("\n"))
                                            } else {
                                                todoDetailBridge.copyPlainText(String(modelData.text || ""))
                                            }
                                        }
                                    }
                                }
                            }

                            Text {
                                visible: modelData.type !== "list"
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

                            Column {
                                visible: modelData.type === "list"
                                width: parent.width
                                spacing: 6

                                Repeater {
                                    model: modelData.type === "list" ? modelData.lines : []

                                    delegate: Row {
                                        width: sectionContent.width
                                        spacing: 6

                                        Text {
                                            text: "•"
                                            color: rootContext ? rootContext.bodyInk : "#4A5565"
                                            font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                            font.pixelSize: 12
                                            font.weight: rootContext ? rootContext.bodyWeight : 400
                                        }

                                        Text {
                                            width: parent.width - 12
                                            wrapMode: Text.Wrap
                                            text: modelData
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
        }
    }
}

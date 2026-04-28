import QtQuick

Rectangle {
    id: root
    width: 443
    height: 632
    color: "transparent"
    readonly property string uiFont: todoDetailBridge ? todoDetailBridge.uiFont : "Microsoft YaHei UI"
    readonly property real preferredHeight: 632

    Rectangle {
        id: panel
        anchors.fill: parent

        property string selectedKey: "case"
        property string toastText: ""

        readonly property real panelSidePadding: 24
        readonly property real panelTopPadding: 16
        readonly property real panelBottomPadding: 24
        readonly property real sectionSpacing: 12
        readonly property color panelBorder: "#E5E7EB"
        readonly property color titleText: "#18202E"
        readonly property color bodyText: "#4A5565"
        readonly property color mutedText: "#7A8795"
        readonly property color subtleFill: "#F5F5F5"
        readonly property color contentBorder: "#E5E7EB"
        readonly property color primaryFill: "#2A313F"
        readonly property color secondaryInk: "#4A5565"
        readonly property color chipBorder: "#E5E7EB"
        readonly property color chipText: "#5B6574"
        readonly property real chipHeight: 28
        readonly property real chipRadius: 14
        readonly property real chipFontSize: 11
        readonly property real headerHeight: 28
        readonly property real helperHeight: 64
        readonly property real bodyHeight: root.height
            - panel.panelTopPadding
            - panel.panelBottomPadding
            - headerHeight
            - helperHeight
            - panel.sectionSpacing * 2

        readonly property var toolTabs: [
            { "key": "case", "label": "案例" },
            { "key": "doc", "label": "文档" },
            { "key": "err", "label": "错误码" },
            { "key": "step", "label": "步骤" }
        ]

        readonly property var tabData: ({
            "case": {
                "recognized": "已从时间线识别",
                "known": "已存在 demo 验证结论",
                "knownReason": "来自历史跟进：demo 正常，生产异常",
                "missing": [
                    { "title": "生产环境请求参数", "reason": "用于确认是否存在参数差异" },
                    { "title": "日志分析结论", "reason": "需要明确是否存在异常或 warning" },
                    { "title": "问题文件与截图", "reason": "用于复现与一线分析" }
                ]
            },
            "doc": {
                "recognized": "已识别预览 / 导出链路问题",
                "known": "可参考预览链路参数核对清单",
                "knownReason": "重点核对 preview_mode、scale、dpi、印章坐标和文档格式",
                "missing": [
                    { "title": "文档格式与版本", "reason": "用于判断是否触发格式兼容问题" },
                    { "title": "导出参数截图", "reason": "用于对齐客户侧与 demo 环境配置" },
                    { "title": "相关接口返回体", "reason": "用于确认服务端是否返回异常状态" }
                ]
            },
            "err": {
                "recognized": "暂未发现稳定错误码",
                "known": "错误码证据不足",
                "knownReason": "当前描述偏现象类，需要补充接口返回、日志或任务失败码",
                "missing": [
                    { "title": "完整错误码", "reason": "用于匹配已有错误码说明" },
                    { "title": "请求 ID / trace ID", "reason": "用于串联服务端日志" },
                    { "title": "失败发生时间", "reason": "用于缩小日志检索范围" }
                ]
            },
            "step": {
                "recognized": "可先按最小复现路径推进",
                "known": "demo 与生产环境对比是关键线索",
                "knownReason": "当前已知 demo 正常、生产异常，优先排查环境和参数差异",
                "missing": [
                    { "title": "固定同一份问题文件", "reason": "避免素材差异干扰定位" },
                    { "title": "逐项对比渲染参数", "reason": "确认 preview_mode、印章坐标、文档格式是否一致" },
                    { "title": "补充复现结论", "reason": "用于决定是否升级研发排查" }
                ]
            }
        })

        readonly property var resultData: ({
            "case": {
                "title": "相似案例",
                "count": "模拟 2 条结果",
                "items": [
                    {
                        "title": "电子签章在线预览坐标偏移",
                        "desc": "历史结论：生产与测试环境 preview_mode、缩放参数不一致，导致坐标换算结果不同。",
                        "text": "【相似案例】preview_mode 与缩放参数不一致可能导致坐标偏移，建议优先比对请求参数。"
                    },
                    {
                        "title": "PDF 转图片后签章错位",
                        "desc": "与 DPI/缩放设置相关，服务端渲染参数不同导致偏移。",
                        "text": "【相似案例】与 DPI/缩放设置相关，建议核对服务端渲染参数。"
                    }
                ]
            },
            "doc": {
                "title": "官方文档",
                "count": "模拟 2 条结果",
                "items": [
                    {
                        "title": "签章预览坐标与缩放说明",
                        "desc": "页码、坐标原点、缩放比、旋转与预览模式共同影响展示。",
                        "text": "【官方文档】签章位置与页码/坐标系/缩放/预览模式相关，建议对照核查。"
                    },
                    {
                        "title": "预览服务参数列表",
                        "desc": "包含 preview_mode、scale、dpi 等关键字段说明。",
                        "text": "【官方文档】建议核对 preview_mode/scale/dpi 等字段。"
                    }
                ]
            },
            "err": {
                "title": "错误码说明",
                "count": "模拟 2 条结果",
                "items": [
                    {
                        "title": "400000007",
                        "desc": "参数校验失败，检查必填字段与格式。",
                        "text": "【错误码】400000007 参数校验失败，需检查必填字段与格式。"
                    },
                    {
                        "title": "15041",
                        "desc": "文档创建失败，可能与权限或模板异常相关。",
                        "text": "【错误码】15041 文档创建失败，需检查权限与模板。"
                    }
                ]
            },
            "step": {
                "title": "验证步骤",
                "count": "模拟 1 条结果",
                "items": [
                    {
                        "title": "生产与 demo 对比验证",
                        "desc": "1. 使用同一文件；2. 使用同一请求参数；3. 对比 preview_mode、scale、dpi、页码和坐标；4. 记录是否复现。",
                        "text": "【验证步骤】\n1. 使用同一文件\n2. 使用同一请求参数\n3. 对比 preview_mode、scale、dpi、页码和坐标\n4. 记录生产与 demo 是否复现"
                    }
                ]
            }
        })

        function currentData() {
            return tabData[selectedKey] || tabData["case"]
        }

        function currentResults() {
            return resultData[selectedKey] || resultData["case"]
        }

        function appendTimelineDraft(text) {
            var value = String(text || "").trim()
            if (value.length === 0 || !todoDetailBridge) {
                return
            }
            var current = String(todoDetailBridge.timelineDraftText || "").trim()
            todoDetailBridge.setTimelineDraftEntryType("follow_up")
            todoDetailBridge.updateTimelineDraftText(current.length > 0 ? current + "\n\n" + value : value)
            panel.showToast("已引用到跟进")
        }

        function showToast(text) {
            toastText = text
            toastTimer.restart()
        }

        Timer {
            id: toastTimer
            interval: 1500
            onTriggered: panel.toastText = ""
        }

        color: "#FFFFFF"
        radius: 18
        border.width: 1
        border.color: panel.panelBorder
        clip: true

        Column {
            id: panelColumn
            anchors.fill: parent
            anchors.leftMargin: panel.panelSidePadding
            anchors.rightMargin: panel.panelSidePadding
            anchors.topMargin: panel.panelTopPadding
            anchors.bottomMargin: panel.panelBottomPadding
            spacing: panel.sectionSpacing

            Item {
                id: headerBar
                width: parent.width
                height: panel.headerHeight

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                    onPressed: function(mouse) {
                        assistTroubleshootingWindowBridge.beginPanelDrag(mouse.x, mouse.y)
                    }
                    onPositionChanged: function(mouse) {
                        if (mouse.buttons & Qt.LeftButton) {
                            assistTroubleshootingWindowBridge.updatePanelDrag()
                        }
                    }
                    onReleased: assistTroubleshootingWindowBridge.finishPanelDrag()
                    onCanceled: assistTroubleshootingWindowBridge.finishPanelDrag()
                }

                Row {
                    anchors.left: parent.left
                    anchors.right: closeButton.left
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8

                    Rectangle {
                        width: 26
                        height: 26
                        radius: 9
                        color: "#EEF2FF"

                        Text {
                            anchors.centerIn: parent
                            text: "✦"
                            color: "#4F73FF"
                            font.family: root.uiFont
                            font.pixelSize: 14
                            font.weight: 700
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "辅助排查"
                        color: panel.titleText
                        font.family: root.uiFont
                        font.pixelSize: 17
                        font.weight: 600
                    }
                }

                Rectangle {
                    id: closeButton
                    width: 20
                    height: 20
                    radius: 6
                    anchors.right: parent.right
                    anchors.top: parent.top
                    color: closeMouse.containsMouse ? "#F3F5F8" : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "×"
                        color: closeMouse.containsMouse ? "#667085" : panel.mutedText
                        font.family: root.uiFont
                        font.pixelSize: 15
                        font.weight: 400
                    }

                    MouseArea {
                        id: closeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: todoDetailBridge.closeAssistTroubleshooting()
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: panel.helperHeight
                radius: 12
                color: panel.subtleFill
                border.width: 1
                border.color: panel.contentBorder

                Text {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    anchors.topMargin: 10
                    anchors.bottomMargin: 10
                    text: "更像环境或参数差异问题，建议先补齐参数和日志，再决定是否升级。"
                    wrapMode: Text.Wrap
                    color: panel.bodyText
                    font.family: root.uiFont
                    font.pixelSize: 13
                    font.weight: 400
                    lineHeight: 1.22
                }
            }

            Flickable {
                id: bodyFlick
                width: parent.width
                height: panel.bodyHeight
                clip: true
                contentWidth: width
                contentHeight: bodyColumn.implicitHeight
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: bodyColumn
                    width: bodyFlick.width
                    spacing: panel.sectionSpacing

                    Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: "操作"
                            color: panel.mutedText
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 400
                        }

                        Row {
                            width: parent.width
                            height: panel.chipHeight
                            spacing: 6

                            Repeater {
                                model: panel.toolTabs

                                delegate: Rectangle {
                                    width: tabText.implicitWidth + 20
                                    height: panel.chipHeight
                                    radius: 8
                                    color: panel.selectedKey === modelData.key ? "#EEF2FF" : "transparent"
                                    border.width: 1
                                    border.color: "transparent"

                                    Text {
                                        id: tabText
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        color: panel.selectedKey === modelData.key ? "#4F73FF" : "#667085"
                                        font.family: root.uiFont
                                        font.pixelSize: panel.chipFontSize
                                        font.weight: 500
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: panel.selectedKey = modelData.key
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: resultColumn.implicitHeight + 24
                        radius: 14
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: panel.contentBorder

                        Column {
                            id: resultColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 14
                            spacing: 10

                            Item {
                                width: parent.width
                                height: 18

                                Text {
                                    anchors.left: parent.left
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: panel.currentResults().title
                                    color: panel.titleText
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: 600
                                }

                                Text {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: panel.currentResults().count
                                    color: panel.mutedText
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: 400
                                }
                            }

                            Repeater {
                                model: panel.currentResults().items

                                delegate: Rectangle {
                                    width: parent.width
                                    height: resultCardColumn.implicitHeight + 20
                                    radius: 12
                                    color: "#FFFFFF"
                                    border.width: 1
                                    border.color: panel.contentBorder

                                    Column {
                                        id: resultCardColumn
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.top: parent.top
                                        anchors.margins: 12
                                        spacing: 7

                                        Text {
                                            width: parent.width
                                            text: modelData.title
                                            wrapMode: Text.Wrap
                                            color: panel.titleText
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: 600
                                            lineHeight: 1.2
                                        }

                                        Text {
                                            width: parent.width
                                            text: modelData.desc
                                            wrapMode: Text.Wrap
                                            color: panel.bodyText
                                            font.family: root.uiFont
                                            font.pixelSize: 12
                                            font.weight: 400
                                            lineHeight: 1.25
                                        }

                                        Row {
                                            spacing: 14
                                            height: 18

                                            Text {
                                                text: "引用到跟进"
                                                color: "#4F73FF"
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                                font.weight: 500

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: panel.appendTimelineDraft(modelData.text)
                                                }
                                            }

                                            Text {
                                                text: "查看详情"
                                                color: "#4F73FF"
                                                font.family: root.uiFont
                                                font.pixelSize: 12
                                                font.weight: 500

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: panel.showToast("暂无更多详情")
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: "信息状态"
                            color: panel.mutedText
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 400
                        }

                        Text {
                            width: parent.width
                            text: panel.currentData().recognized
                            wrapMode: Text.Wrap
                            color: panel.bodyText
                            font.family: root.uiFont
                            font.pixelSize: 13
                            font.weight: 400
                            lineHeight: 1.2
                        }

                        Column {
                            width: parent.width
                            spacing: 3

                            Text {
                                width: parent.width
                                text: "✓ " + panel.currentData().known
                                wrapMode: Text.Wrap
                                color: panel.bodyText
                                font.family: root.uiFont
                                font.pixelSize: 13
                                font.weight: 400
                                lineHeight: 1.2
                            }

                            Text {
                                width: parent.width
                                text: panel.currentData().knownReason
                                wrapMode: Text.Wrap
                                color: panel.mutedText
                                font.family: root.uiFont
                                font.pixelSize: 12
                                font.weight: 400
                                lineHeight: 1.2
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 8

                        Text {
                            text: "仍需补充"
                            color: panel.mutedText
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 400
                        }

                        Repeater {
                            model: panel.currentData().missing

                            delegate: Column {
                                width: parent.width
                                spacing: 3

                                Text {
                                    width: parent.width
                                    text: modelData.title
                                    wrapMode: Text.Wrap
                                    color: panel.titleText
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: 500
                                    lineHeight: 1.2
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.reason
                                    wrapMode: Text.Wrap
                                    color: panel.mutedText
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: 400
                                    lineHeight: 1.2
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: panel.contentBorder
                    }

                    Column {
                        width: parent.width
                        spacing: 8

                        Item {
                            width: parent.width
                            height: 24

                            Text {
                                anchors.left: parent.left
                                anchors.verticalCenter: parent.verticalCenter
                                text: "暂不建议升级"
                                color: panel.titleText
                                font.family: root.uiFont
                                font.pixelSize: 14
                                font.weight: 600
                            }

                            Rectangle {
                                width: riskText.implicitWidth + 16
                                height: 24
                                radius: 12
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                color: "#FFF4EC"

                                Text {
                                    id: riskText
                                    anchors.centerIn: parent
                                    text: "证据不足"
                                    color: "#D65A19"
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: 500
                                }
                            }
                        }

                        Text {
                            width: parent.width
                            text: "当前缺少参数、日志、demo 对比等关键证据。建议先补齐信息，再判断是否需要升级。"
                            wrapMode: Text.Wrap
                            color: panel.bodyText
                            font.family: root.uiFont
                            font.pixelSize: 13
                            font.weight: 400
                            lineHeight: 1.25
                        }
                    }
                }

                Rectangle {
                    visible: bodyFlick.contentHeight > bodyFlick.height + 2
                    anchors.right: parent.right
                    anchors.rightMargin: 4
                    y: 8 + (bodyFlick.contentY / Math.max(1, bodyFlick.contentHeight - bodyFlick.height)) * (parent.height - height - 16)
                    width: 4
                    height: Math.max(48, (bodyFlick.height / Math.max(bodyFlick.contentHeight, 1)) * (parent.height - 16))
                    radius: 2
                    color: "#BEC6D2"
                }
            }
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 14
            width: toastTextItem.implicitWidth + 24
            height: 32
            radius: 16
            color: "#111827"
            opacity: panel.toastText.length > 0 ? 0.94 : 0
            visible: opacity > 0

            Text {
                id: toastTextItem
                anchors.centerIn: parent
                text: panel.toastText
                color: "#FFFFFF"
                font.family: root.uiFont
                font.pixelSize: 12
                font.weight: 500
            }
        }

        Item {
            width: 18
            height: 18
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            Canvas {
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.strokeStyle = "rgba(17, 24, 39, 0.18)"
                    ctx.lineWidth = 2
                    ctx.beginPath()
                    ctx.moveTo(width - 10, height - 5)
                    ctx.lineTo(width - 5, height - 5)
                    ctx.lineTo(width - 5, height - 10)
                    ctx.stroke()
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.SizeFDiagCursor
                onPressed: assistTroubleshootingWindowBridge.startPanelResize("bottom_right")
            }
        }
    }
}

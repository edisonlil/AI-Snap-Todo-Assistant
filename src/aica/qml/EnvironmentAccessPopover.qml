import QtQuick

Rectangle {
    id: root
    required property var theme
    required property var groupsModel
    readonly property color panelBg: theme.panelBg || "#FFFFFF"
    readonly property color panelAltBg: theme.panelAltBg || theme.fieldBg || "#F8F9FA"
    readonly property color panelLine: theme.panelLine || "#E5E7EB"
    readonly property color fieldLine: theme.fieldLine || theme.panelLine || "#E5E7EB"
    readonly property color titleInk: theme.titleInk || "#18202E"
    readonly property color bodyInk: theme.bodyInk || "#4A5565"
    readonly property color labelInk: theme.labelInk || "#7C8795"
    readonly property color mutedInk: theme.mutedInk || "#A9B1BD"
    readonly property color accent: theme.accent || "#2A313F"
    readonly property int fontTiny: theme.fontTiny || 10
    readonly property int fontCaption: theme.fontCaption || 11
    readonly property int fontBody: theme.fontBody || 12
    readonly property int fontBodyLg: theme.fontBodyLg || 13
    readonly property int fontSection: theme.fontSection || 14
    readonly property string uiFont: theme.uiFont || "Microsoft YaHei UI"
    readonly property int sectionWeight: theme.sectionWeight || 600
    readonly property int labelWeight: theme.labelWeight || 500
    readonly property int bodyWeight: theme.bodyWeight || 400
    readonly property int cardRadius: 20
    readonly property int groupRadius: 16
    readonly property int entryRadius: 16
    readonly property int badgeRadius: 11
    readonly property int buttonRadius: 12
    readonly property int otpRadius: 10
    width: 336
    radius: root.cardRadius
    color: root.panelBg
    border.width: 1
    border.color: root.panelLine

    implicitHeight: contentColumn.implicitHeight + 24

    function flowMessage(entry) {
        var accessName = (entry && entry.name) ? entry.name : "当前入口"
        if (entry && entry.detailMode === "link") {
            if ((entry.username || "").length === 0 && !entry.canCopyPassword && !entry.canCopyOtp) {
                return "已复制" + accessName + "链接。当前访问方式暂无账号、密码或验证码。"
            }
            return "已复制" + accessName + "链接。继续复制账号、密码或验证码："
        }
        if (entry && entry.hasTarget) {
            return "已用新窗口打开" + accessName + "，并自动复制账号。继续完成登录："
        }
        return "已准备连接" + accessName + "，并自动复制账号。继续复制密码："
    }

    function otpDisplay(code) {
        var value = (code || "").replace(/\s+/g, "")
        if (value.length === 6) {
            return value.slice(0, 3) + " " + value.slice(3)
        }
        return value
    }

    Column {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 10

        Column {
            width: parent.width
            spacing: 4

            Text {
                text: "环境访问"
                color: root.titleInk
                font.family: root.uiFont
                font.pixelSize: root.fontSection
                font.weight: root.sectionWeight
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "点击开始登录后，会尝试打开入口并自动复制账号，再按需复制密码或验证码。"
                color: root.labelInk
                font.family: root.uiFont
                font.pixelSize: root.fontCaption
                font.weight: root.bodyWeight
                lineHeight: 1.35
            }
        }

        Repeater {
            model: root.groupsModel

            delegate: Rectangle {
                width: parent.width
                radius: root.groupRadius
                color: root.panelBg
                border.width: 0
                border.color: "transparent"
                height: groupColumn.implicitHeight + 16

                Column {
                    id: groupColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 8
                    spacing: 8

                    Rectangle {
                        width: parent.width
                        height: 42
                        radius: root.groupRadius
                        color: "transparent"

                        Row {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.leftMargin: 10
                            anchors.rightMargin: 10
                            spacing: 8

                            Column {
                                width: parent.width - groupArrow.width - parent.spacing
                                spacing: 2

                                Text {
                                    width: parent.width
                                    text: modelData.name || ""
                                    elide: Text.ElideRight
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: root.fontBody
                                    font.weight: root.sectionWeight
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.summary || ""
                                    elide: Text.ElideRight
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: root.fontTiny
                                    font.weight: root.bodyWeight
                                }
                            }

                            Text {
                                id: groupArrow
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.expanded ? "▾" : "▸"
                                color: root.labelInk
                                font.family: root.uiFont
                                font.pixelSize: root.fontBody
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: todoDetailBridge.toggleEnvironmentGroup(modelData.id)
                        }
                    }

                    Column {
                        visible: modelData.expanded
                        width: parent.width
                        spacing: 8

                        Repeater {
                            model: modelData.entries || []

                            delegate: Rectangle {
                                width: parent.width
                                radius: root.entryRadius
                                color: root.panelAltBg
                                border.width: 1
                                border.color: modelData.loginActivated ? root.accent : root.fieldLine
                                height: entryColumn.implicitHeight + 16

                                Column {
                                    id: entryColumn
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 10
                                    spacing: 8

                                    Row {
                                        width: parent.width
                                        spacing: 8

                                        Text {
                                            width: parent.width - (entryBadge.visible ? entryBadge.width + parent.spacing : 0)
                                            text: modelData.name || ""
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: root.fontBody
                                            font.weight: root.sectionWeight
                                            elide: Text.ElideRight
                                        }

                                        Rectangle {
                                            id: entryBadge
                                            visible: modelData.requiresOtp
                                            radius: root.badgeRadius
                                            height: 24
                                            width: badgeText.implicitWidth + 16
                                            color: root.panelBg
                                            border.width: 1
                                            border.color: root.fieldLine

                                            Text {
                                                id: badgeText
                                                anchors.centerIn: parent
                                                text: "需要 OTP"
                                                color: root.labelInk
                                                font.family: root.uiFont
                                                font.pixelSize: root.fontTiny
                                                font.weight: root.labelWeight
                                            }
                                        }
                                    }

                                    Text {
                                        visible: (modelData.urlOrHost || "").length > 0
                                        width: parent.width
                                        text: modelData.urlOrHost || ""
                                        color: root.labelInk
                                        font.family: root.uiFont
                                        font.pixelSize: root.fontTiny
                                        font.weight: root.bodyWeight
                                        wrapMode: Text.WrapAnywhere
                                    }

                                    Text {
                                        visible: (modelData.note || "").length > 0 && !modelData.loginActivated
                                        width: parent.width
                                        text: modelData.note || ""
                                        color: root.bodyInk
                                        font.family: root.uiFont
                                        font.pixelSize: root.fontCaption
                                        font.weight: root.bodyWeight
                                        wrapMode: Text.Wrap
                                        lineHeight: 1.35
                                    }

                                    Flow {
                                        width: parent.width
                                        spacing: 8

                                        Row {
                                            visible: modelData.hasTarget
                                                || (modelData.username || "").length > 0
                                                || modelData.hasPassword
                                            spacing: 10
                                            width: loginButton.width
                                                   + (copyLinkText.visible ? copyLinkText.implicitWidth + spacing : 0)
                                            height: 30

                                            Rectangle {
                                                id: loginButton
                                                radius: root.buttonRadius
                                                width: loginLabel.implicitWidth + 22
                                                height: parent.height
                                                color: root.accent

                                                Text {
                                                    id: loginLabel
                                                    anchors.centerIn: parent
                                                    text: "开始登录"
                                                    color: root.panelBg
                                                    font.family: root.uiFont
                                                    font.pixelSize: root.fontCaption
                                                    font.weight: root.labelWeight
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: todoDetailBridge.startEnvironmentLogin(modelData.id)
                                                }
                                            }

                                            Text {
                                                id: copyLinkText
                                                visible: modelData.hasTarget
                                                width: implicitWidth
                                                height: parent.height
                                                text: "复制链接"
                                                color: root.titleInk
                                                font.family: root.uiFont
                                                font.pixelSize: root.fontCaption
                                                font.weight: root.labelWeight
                                                verticalAlignment: Text.AlignVCenter

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: todoDetailBridge.copyEnvironmentAddressAndShowDetails(modelData.id)
                                                }
                                            }

                                        }
                                    }

                                    Item {
                                        visible: modelData.loginActivated
                                        width: parent.width
                                        height: loginFlowCard.implicitHeight

                                            Rectangle {
                                                id: loginFlowCard
                                                width: parent.width
                                                implicitHeight: flowColumn.implicitHeight + 24
                                                radius: root.entryRadius
                                                color: root.panelBg
                                                border.width: 1
                                                border.color: root.fieldLine

                                            Canvas {
                                                id: dashOutline
                                                anchors.fill: parent
                                                anchors.margins: 1
                                                onWidthChanged: requestPaint()
                                                onHeightChanged: requestPaint()
                                                onPaint: {
                                                    var ctx = getContext("2d")
                                                    ctx.clearRect(0, 0, width, height)
                                                    ctx.strokeStyle = root.fieldLine
                                                    ctx.lineWidth = 1
                                                    ctx.setLineDash([3, 4])
                                                    var inset = 8
                                                    var radius = 13
                                                    var left = inset
                                                    var top = inset
                                                    var right = width - inset
                                                    var bottom = height - inset
                                                    ctx.beginPath()
                                                    ctx.moveTo(left + radius, top)
                                                    ctx.lineTo(right - radius, top)
                                                    ctx.quadraticCurveTo(right, top, right, top + radius)
                                                    ctx.lineTo(right, bottom - radius)
                                                    ctx.quadraticCurveTo(right, bottom, right - radius, bottom)
                                                    ctx.lineTo(left + radius, bottom)
                                                    ctx.quadraticCurveTo(left, bottom, left, bottom - radius)
                                                    ctx.lineTo(left, top + radius)
                                                    ctx.quadraticCurveTo(left, top, left + radius, top)
                                                    ctx.stroke()
                                                }
                                            }

                                            Column {
                                                id: flowColumn
                                                anchors.left: parent.left
                                                anchors.right: parent.right
                                                anchors.top: parent.top
                                                anchors.margins: 16
                                                spacing: 12

                                                    Text {
                                                        width: parent.width
                                                        text: root.flowMessage(modelData)
                                                        color: root.bodyInk
                                                        font.family: root.uiFont
                                                        font.pixelSize: root.fontBody
                                                        font.weight: root.bodyWeight
                                                        wrapMode: Text.Wrap
                                                        lineHeight: 1.5
                                                    }

                                                Row {
                                                    width: parent.width
                                                    spacing: 8

                                                    Rectangle {
                                                        visible: (modelData.username || "").length > 0
                                                        radius: root.buttonRadius
                                                        width: 60
                                                        height: 29
                                                        color: root.panelBg
                                                        border.width: 1
                                                        border.color: root.fieldLine

                                                        Text {
                                                            id: usernameLabel
                                                            anchors.centerIn: parent
                                                            text: "复制账号"
                                                            color: root.bodyInk
                                                            font.family: root.uiFont
                                                            font.pixelSize: root.fontCaption
                                                            font.weight: root.labelWeight
                                                        }

                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: todoDetailBridge.copyEnvironmentUsername(modelData.id)
                                                        }
                                                    }

                                                    Rectangle {
                                                        visible: modelData.canCopyPassword
                                                        radius: root.buttonRadius
                                                        width: 60
                                                        height: 29
                                                        color: root.panelBg
                                                        border.width: 1
                                                        border.color: root.fieldLine

                                                        Text {
                                                            id: passwordLabel
                                                            anchors.centerIn: parent
                                                            text: "复制密码"
                                                            color: root.bodyInk
                                                            font.family: root.uiFont
                                                            font.pixelSize: root.fontCaption
                                                            font.weight: root.labelWeight
                                                        }

                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: todoDetailBridge.copyEnvironmentPassword(modelData.id)
                                                        }
                                                    }

                                                    Rectangle {
                                                        visible: modelData.canCopyOtp
                                                        radius: root.otpRadius
                                                        width: 92
                                                        height: 29
                                                        color: root.panelBg
                                                        border.width: 1
                                                        border.color: root.fieldLine

                                                        Row {
                                                            id: otpRow
                                                            anchors.fill: parent
                                                            spacing: 0

                                                            Text {
                                                                width: 58
                                                                height: parent.height
                                                                text: root.otpDisplay(modelData.otpCode || "")
                                                                color: root.titleInk
                                                                font.family: root.uiFont
                                                                font.pixelSize: root.fontBody
                                                                font.weight: root.sectionWeight
                                                                horizontalAlignment: Text.AlignHCenter
                                                                verticalAlignment: Text.AlignVCenter
                                                            }

                                                            Rectangle {
                                                                width: 1
                                                                height: parent.height
                                                                color: root.fieldLine
                                                            }

                                                            Text {
                                                                width: 33
                                                                height: parent.height
                                                                text: (modelData.otpRemainingSeconds || 0) + "s"
                                                                color: root.labelInk
                                                                font.family: root.uiFont
                                                                font.pixelSize: root.fontTiny
                                                                font.weight: root.labelWeight
                                                                horizontalAlignment: Text.AlignHCenter
                                                                verticalAlignment: Text.AlignVCenter
                                                            }
                                                        }

                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: todoDetailBridge.copyEnvironmentOtp(modelData.id)
                                                        }
                                                    }
                                                }

                                                Text {
                                                    visible: modelData.canCopyOtp
                                                    width: parent.width
                                                    text: "验证码直接显示，点击数字可复制；倒计时与验证码同区，不再挤在底部。"
                                                    color: root.mutedInk
                                                    font.family: root.uiFont
                                                    font.pixelSize: root.fontCaption
                                                    font.weight: root.bodyWeight
                                                    wrapMode: Text.Wrap
                                                    lineHeight: 1.45
                                                }

                                                Item {
                                                    width: 1
                                                    height: 6
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            visible: (modelData.entries || []).length === 0
                            width: parent.width
                            height: emptyText.implicitHeight + 16
                            radius: root.entryRadius
                            color: root.panelBg
                            border.width: 1
                            border.color: root.fieldLine

                            Text {
                                id: emptyText
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                text: modelData.note || "当前环境组暂无可直接访问入口"
                                color: root.labelInk
                                font.family: root.uiFont
                                font.pixelSize: root.fontCaption
                                font.weight: root.bodyWeight
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            visible: (root.groupsModel || []).length === 0
            width: parent.width
            height: 44
            radius: root.groupRadius
            color: root.panelAltBg
            border.width: 1
            border.color: root.fieldLine

            Text {
                anchors.centerIn: parent
                text: "当前项目暂无可用环境配置"
                color: root.labelInk
                font.family: root.uiFont
                font.pixelSize: root.fontCaption
                font.weight: root.bodyWeight
            }
        }
    }
}

import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    required property var theme
    required property var groupsModel
    width: 336
    radius: 20
    color: "#FFFFFF"
    border.width: 1
    border.color: "#ECEFF3"

    implicitHeight: contentColumn.implicitHeight + 24

    function flowMessage(entry) {
        var accessName = (entry && entry.name) ? entry.name : "当前入口"
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
                color: root.theme.titleInk
                font.family: root.theme.uiFont
                font.pixelSize: 14
                font.weight: root.theme.sectionWeight
            }

            Text {
                width: parent.width
                wrapMode: Text.Wrap
                text: "点击开始登录后，会尝试打开入口并自动复制账号，再按需复制密码或验证码。"
                color: root.theme.labelInk
                font.family: root.theme.uiFont
                font.pixelSize: 11
                font.weight: root.theme.bodyWeight
                lineHeight: 1.35
            }
        }

        Repeater {
            model: root.groupsModel

            delegate: Rectangle {
                width: parent.width
                radius: 16
                color: "#FFFFFF"
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
                        radius: 12
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
                                    color: root.theme.titleInk
                                    font.family: root.theme.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.theme.sectionWeight
                                }

                                Text {
                                    width: parent.width
                                    text: modelData.summary || ""
                                    elide: Text.ElideRight
                                    color: root.theme.labelInk
                                    font.family: root.theme.uiFont
                                    font.pixelSize: 10
                                    font.weight: root.theme.bodyWeight
                                }
                            }

                            Text {
                                id: groupArrow
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.expanded ? "▾" : "▸"
                                color: root.theme.labelInk
                                font.family: root.theme.uiFont
                                font.pixelSize: 12
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
                                radius: 16
                                color: "#FAFAF9"
                                border.width: 1
                                border.color: modelData.loginActivated ? "#D9E2EC" : "#EDF1F5"
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
                                            color: root.theme.titleInk
                                            font.family: root.theme.uiFont
                                            font.pixelSize: 12
                                            font.weight: root.theme.sectionWeight
                                            elide: Text.ElideRight
                                        }

                                        Rectangle {
                                            id: entryBadge
                                            visible: modelData.requiresOtp
                                            radius: 11
                                            height: 24
                                            width: badgeText.implicitWidth + 16
                                            color: "#FFFFFF"
                                            border.width: 1
                                            border.color: "#E2E8F0"

                                            Text {
                                                id: badgeText
                                                anchors.centerIn: parent
                                                text: "需要 OTP"
                                                color: "#7B8797"
                                                font.family: root.theme.uiFont
                                                font.pixelSize: 10
                                                font.weight: root.theme.labelWeight
                                            }
                                        }
                                    }

                                    Text {
                                        visible: (modelData.urlOrHost || "").length > 0
                                        width: parent.width
                                        text: modelData.urlOrHost || ""
                                        color: "#7C8798"
                                        font.family: root.theme.uiFont
                                        font.pixelSize: 10
                                        font.weight: root.theme.bodyWeight
                                        wrapMode: Text.WrapAnywhere
                                    }

                                    Text {
                                        visible: (modelData.note || "").length > 0 && !modelData.loginActivated
                                        width: parent.width
                                        text: modelData.note || ""
                                        color: root.theme.bodyInk
                                        font.family: root.theme.uiFont
                                        font.pixelSize: 11
                                        font.weight: root.theme.bodyWeight
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
                                            spacing: 1
                                            width: loginButton.width + copyMenuButton.width + spacing
                                            height: 30

                                            Rectangle {
                                                id: loginButton
                                                radius: 12
                                                width: loginLabel.implicitWidth + 22
                                                height: parent.height
                                                color: "#111827"

                                                Text {
                                                    id: loginLabel
                                                    anchors.centerIn: parent
                                                    text: "开始登录"
                                                    color: "#FFFFFF"
                                                    font.family: root.theme.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.theme.labelWeight
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: todoDetailBridge.startEnvironmentLogin(modelData.id)
                                                }
                                            }

                                            Rectangle {
                                                id: copyMenuButton
                                                radius: 12
                                                width: 30
                                                height: parent.height
                                                color: copyMenu.opened ? "#1F2937" : "#111827"

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "▾"
                                                    color: "#FFFFFF"
                                                    font.family: root.theme.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.theme.labelWeight
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: {
                                                        copyMenu.x = copyMenuButton.x
                                                        copyMenu.y = copyMenuButton.y + copyMenuButton.height + 4
                                                        copyMenu.open()
                                                    }
                                                }
                                            }

                                            Menu {
                                                id: copyMenu

                                                MenuItem {
                                                    text: "复制地址"
                                                    enabled: (modelData.urlOrHost || "").length > 0
                                                    onTriggered: todoDetailBridge.copyEnvironmentAddress(modelData.id)
                                                }

                                                MenuItem {
                                                    text: "复制账号"
                                                    enabled: (modelData.username || "").length > 0
                                                    onTriggered: todoDetailBridge.copyEnvironmentUsername(modelData.id)
                                                }

                                                MenuItem {
                                                    text: "复制密码"
                                                    enabled: modelData.hasPassword
                                                    onTriggered: todoDetailBridge.copyEnvironmentPassword(modelData.id)
                                                }

                                                MenuItem {
                                                    text: "复制地址/账号/密码"
                                                    enabled: (
                                                        (modelData.urlOrHost || "").length > 0
                                                        || (modelData.username || "").length > 0
                                                        || modelData.hasPassword
                                                    )
                                                    onTriggered: todoDetailBridge.copyEnvironmentLoginInfo(modelData.id)
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
                                                radius: 18
                                                color: "#FCFCFB"
                                                border.width: 1
                                                border.color: "#E3EAF4"

                                            Canvas {
                                                id: dashOutline
                                                anchors.fill: parent
                                                anchors.margins: 1
                                                onWidthChanged: requestPaint()
                                                onHeightChanged: requestPaint()
                                                onPaint: {
                                                    var ctx = getContext("2d")
                                                    ctx.clearRect(0, 0, width, height)
                                                    ctx.strokeStyle = "#D7E2F0"
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
                                                        color: "#465466"
                                                        font.family: root.theme.uiFont
                                                        font.pixelSize: 12
                                                        font.weight: root.theme.bodyWeight
                                                        wrapMode: Text.Wrap
                                                        lineHeight: 1.5
                                                    }

                                                Row {
                                                    width: parent.width
                                                    spacing: 8

                                                    Rectangle {
                                                        visible: (modelData.username || "").length > 0
                                                        radius: 12
                                                        width: 60
                                                        height: 29
                                                        color: "#FFFFFF"
                                                        border.width: 1
                                                        border.color: "#D4DBE6"

                                                        Text {
                                                            id: usernameLabel
                                                            anchors.centerIn: parent
                                                            text: "复制账号"
                                                            color: root.theme.bodyInk
                                                            font.family: root.theme.uiFont
                                                            font.pixelSize: 11
                                                            font.weight: root.theme.labelWeight
                                                        }

                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: todoDetailBridge.copyEnvironmentUsername(modelData.id)
                                                        }
                                                    }

                                                    Rectangle {
                                                        visible: modelData.canCopyPassword
                                                        radius: 12
                                                        width: 60
                                                        height: 29
                                                        color: "#FFFFFF"
                                                        border.width: 1
                                                        border.color: "#D4DBE6"

                                                        Text {
                                                            id: passwordLabel
                                                            anchors.centerIn: parent
                                                            text: "复制密码"
                                                            color: root.theme.bodyInk
                                                            font.family: root.theme.uiFont
                                                            font.pixelSize: 11
                                                            font.weight: root.theme.labelWeight
                                                        }

                                                        MouseArea {
                                                            anchors.fill: parent
                                                            cursorShape: Qt.PointingHandCursor
                                                            onClicked: todoDetailBridge.copyEnvironmentPassword(modelData.id)
                                                        }
                                                    }

                                                    Rectangle {
                                                        visible: modelData.canCopyOtp
                                                        radius: 10
                                                        width: 92
                                                        height: 29
                                                        color: "#FFFFFF"
                                                        border.width: 1
                                                        border.color: "#D4DBE6"

                                                        Row {
                                                            id: otpRow
                                                            anchors.fill: parent
                                                            spacing: 0

                                                            Text {
                                                                width: 58
                                                                height: parent.height
                                                                text: root.otpDisplay(modelData.otpCode || "")
                                                                color: "#111827"
                                                                font.family: root.theme.uiFont
                                                                font.pixelSize: 12
                                                                font.weight: root.theme.sectionWeight
                                                                horizontalAlignment: Text.AlignHCenter
                                                                verticalAlignment: Text.AlignVCenter
                                                            }

                                                            Rectangle {
                                                                width: 1
                                                                height: parent.height
                                                                color: "#E5E7EB"
                                                            }

                                                            Text {
                                                                width: 33
                                                                height: parent.height
                                                                text: (modelData.otpRemainingSeconds || 0) + "s"
                                                                color: "#64748B"
                                                                font.family: root.theme.uiFont
                                                                font.pixelSize: 10
                                                                font.weight: root.theme.labelWeight
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
                                                    color: "#94A3B8"
                                                    font.family: root.theme.uiFont
                                                    font.pixelSize: 11
                                                    font.weight: root.theme.bodyWeight
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
                            radius: 12
                            color: "#FFFFFF"
                            border.width: 1
                            border.color: "#EEF2F6"

                            Text {
                                id: emptyText
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                text: modelData.note || "当前环境组暂无可直接访问入口"
                                color: root.theme.labelInk
                                font.family: root.theme.uiFont
                                font.pixelSize: 11
                                font.weight: root.theme.bodyWeight
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
            radius: 12
            color: "#FAFBFD"
            border.width: 1
            border.color: "#EEF2F6"

            Text {
                anchors.centerIn: parent
                text: "当前项目暂无可用环境配置"
                color: root.theme.labelInk
                font.family: root.theme.uiFont
                font.pixelSize: 11
                font.weight: root.theme.bodyWeight
            }
        }
    }
}

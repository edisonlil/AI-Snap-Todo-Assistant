import QtQuick

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
                text: "点击开始登录后，会尝试打开入口并复制账号，再按需复制密码或验证码。"
                color: root.theme.labelInk
                font.family: root.theme.uiFont
                font.pixelSize: 11
                font.weight: root.theme.bodyWeight
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
                                text: modelData.expanded ? "▴" : "▾"
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
                                border.color: "#EDF1F5"
                                height: entryColumn.implicitHeight + 14

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
                                            radius: 10
                                            height: 20
                                            width: badgeText.implicitWidth + 12
                                            color: "#FFFFFF"
                                            border.width: 1
                                            border.color: "#E5E7EB"

                                            Text {
                                                id: badgeText
                                                anchors.centerIn: parent
                                                text: "需要OTP"
                                                color: "#6B7280"
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
                                        color: root.theme.labelInk
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
                                    }

                                    Flow {
                                        width: parent.width
                                        spacing: 8

                                        Rectangle {
                                            visible: modelData.hasTarget
                                            radius: 12
                                            width: loginLabel.implicitWidth + 20
                                            height: 28
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
                                    }

                                    Rectangle {
                                        visible: modelData.loginActivated
                                        width: parent.width
                                        radius: 14
                                        color: "#FFFFFF"
                                        border.width: 1
                                        border.color: "#DCE3EC"
                                        height: flowColumn.implicitHeight + 12

                                        Column {
                                            id: flowColumn
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.margins: 10
                                            spacing: 6

                                            Text {
                                                width: parent.width
                                                text: "已用新窗口打开当前入口，并自动复制账号。继续完成登录。"
                                                color: root.theme.bodyInk
                                                font.family: root.theme.uiFont
                                                font.pixelSize: 11
                                                font.weight: root.theme.bodyWeight
                                                wrapMode: Text.Wrap
                                            }

                                            Flow {
                                                width: parent.width
                                                spacing: 8

                                                Rectangle {
                                                    visible: modelData.canCopyPassword
                                                    radius: 10
                                                    width: passwordLabel.implicitWidth + 18
                                                    height: 26
                                                    color: "#FFFFFF"
                                                    border.width: 1
                                                    border.color: "#D9E0EA"

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
                                                    width: otpLabel.implicitWidth + 18
                                                    height: 26
                                                    color: "#FFFFFF"
                                                    border.width: 1
                                                    border.color: "#D9E0EA"

                                                    Text {
                                                        id: otpLabel
                                                        anchors.centerIn: parent
                                                        text: "复制验证码"
                                                        color: root.theme.bodyInk
                                                        font.family: root.theme.uiFont
                                                        font.pixelSize: 11
                                                        font.weight: root.theme.labelWeight
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
                                                text: "当前验证码剩余 " + (modelData.otpRemainingSeconds || 0) + "s"
                                                color: "#94A3B8"
                                                font.family: root.theme.uiFont
                                                font.pixelSize: 10
                                                font.weight: root.theme.labelWeight
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

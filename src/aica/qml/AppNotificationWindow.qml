import QtQuick

Item {
    id: root
    width: 360
    height: 420
    implicitWidth: width
    implicitHeight: height
    readonly property var themeTokens: typeof theme !== "undefined" ? theme : ({})

    AppNotificationCenter {
        id: notificationCenter
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 12
        anchors.bottomMargin: 12
        bridge: notificationBridge
        uiFont: notificationUiFont
        theme: root.themeTokens
    }
}

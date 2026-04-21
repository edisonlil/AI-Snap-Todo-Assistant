import QtQuick

Item {
    id: root
    width: notificationCenter.implicitWidth + 24
    height: notificationCenter.implicitHeight + 24
    implicitWidth: width
    implicitHeight: height

    AppNotificationCenter {
        id: notificationCenter
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 12
        anchors.bottomMargin: 12
        bridge: notificationBridge
        uiFont: notificationUiFont
    }
}

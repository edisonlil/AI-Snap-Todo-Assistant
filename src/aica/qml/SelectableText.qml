import QtQuick
import QtQuick.Controls

// 可选中复制的只读文本组件
// 仅用于展示字段，不支持点击编辑
FocusScope {
    id: root
    
    // 对外属性
    property alias text: textEdit.text
    property alias color: textEdit.color
    property alias font: textEdit.font
    property alias wrapMode: textEdit.wrapMode
    property alias selectedText: textEdit.selectedText
    
    implicitWidth: textEdit.implicitWidth
    implicitHeight: textEdit.implicitHeight
    
    TextEdit {
        id: textEdit
        anchors.fill: parent
        
        // 只读模式，支持选中和复制
        readOnly: true
        selectByMouse: true
        selectByKeyboard: true
        
        // 允许获取焦点以接收键盘事件
        activeFocusOnPress: true
        focus: true
        
        // 文本格式
        textFormat: TextEdit.PlainText
        
        // 选中文本的颜色
        selectionColor: "#B8A890"
        selectedTextColor: "#2F241A"
        
        // 支持 Ctrl+C 复制
        Keys.onPressed: function(event) {
            if ((event.key === Qt.Key_C) && (event.modifiers & Qt.ControlModifier)) {
                if (selectedText.length > 0) {
                    textEdit.copy()
                    event.accepted = true
                }
            }
        }
    }
    
    // 右键菜单支持复制
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        propagateComposedEvents: true
        onClicked: function(mouse) {
            if (textEdit.selectedText.length > 0) {
                contextMenu.popup()
                mouse.accepted = true
            } else {
                mouse.accepted = false
            }
        }
    }
    
    Menu {
        id: contextMenu
        
        MenuItem {
            text: "复制"
            enabled: textEdit.selectedText.length > 0
            onTriggered: textEdit.copy()
        }
    }
}

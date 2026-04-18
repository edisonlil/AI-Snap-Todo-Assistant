import QtQuick

Flow {
    id: root
    required property var theme
    property var itemsModel: []
    width: parent ? parent.width : implicitWidth
    spacing: 8

    Repeater {
        model: root.itemsModel

        delegate: Rectangle {
            visible: !!modelData
            radius: 15
            height: 30
            color: root.theme.fieldBg
            border.width: 0
            border.color: root.theme.fieldLine
            width: itemRow.implicitWidth + 18

            Row {
                id: itemRow
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: modelData.label || ""
                    color: root.theme.labelInk
                    font.family: root.theme.uiFont
                    font.pixelSize: 11
                    font.weight: root.theme.labelWeight
                }

                Text {
                    text: modelData.value || ""
                    color: root.theme.titleInk
                    font.family: root.theme.uiFont
                    font.pixelSize: 11
                    font.weight: root.theme.sectionWeight
                }
            }
        }
    }
}

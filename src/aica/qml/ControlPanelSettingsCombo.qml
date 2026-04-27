import QtQuick
import QtQuick.Controls

ComboBox {
    id: combo
    required property var theme
    property int popupMaxHeight: 280
    property int popupItemMinHeight: 38
    property int popupTextMaximumLineCount: 1

    function optionLabel(option) {
        if (option === null || option === undefined) {
            return ""
        }
        if (typeof option === "object") {
            return option.text || option.label || option.value || ""
        }
        return String(option)
    }

    textRole: "text"
    font.family: theme.uiFont
    font.pixelSize: 12
    leftPadding: 14
    rightPadding: 34
    topPadding: 11
    bottomPadding: 11

    contentItem: Text {
        text: combo.displayText
        color: theme.titleInk
        font.family: theme.uiFont
        font.pixelSize: 12
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Canvas {
        x: combo.width - width - 14
        y: combo.topPadding + (combo.availableHeight - height) / 2
        width: 10
        height: 6
        contextType: "2d"
        onPaint: {
            context.reset()
            context.moveTo(0, 0)
            context.lineTo(width, 0)
            context.lineTo(width / 2, height)
            context.closePath()
            context.fillStyle = theme.labelInk
            context.fill()
        }
    }

    background: Rectangle {
        radius: 16
        color: theme.inputBg
        border.width: 1
        border.color: combo.activeFocus || combo.popup.visible ? theme.accent : theme.panelLine
    }

    popup: Popup {
        id: popup
        y: combo.height + 6
        width: combo.width
        padding: 6
        modal: false
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        implicitHeight: Math.min(popupList.implicitHeight + topPadding + bottomPadding,
                                 combo.popupMaxHeight + topPadding + bottomPadding)
        onOpened: {
            if (combo.currentIndex >= 0) {
                popupList.positionViewAtIndex(combo.currentIndex, ListView.Contain)
            }
        }

        background: Rectangle {
            radius: 12
            color: "#FFFFFF"
            border.width: 1
            border.color: theme.panelLine
        }

        contentItem: ListView {
            id: popupList
            clip: true
            implicitHeight: Math.min(contentHeight, combo.popupMaxHeight)
            boundsBehavior: Flickable.StopAtBounds
            model: combo.popup.visible ? combo.delegateModel : null
            currentIndex: combo.highlightedIndex

            ScrollBar.vertical: ScrollBar {
                policy: popupList.contentHeight > popupList.height ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
            }
        }
    }

    delegate: ItemDelegate {
        width: combo.width - combo.popup.leftPadding - combo.popup.rightPadding
        height: Math.max(combo.popupItemMinHeight, optionText.implicitHeight + 18)
        padding: 0
        highlighted: combo.highlightedIndex === index

        background: Rectangle {
            radius: 8
            color: highlighted ? theme.accentSoft : hovered ? "#F6F8FB" : "transparent"
        }

        contentItem: Text {
            id: optionText
            leftPadding: 10
            rightPadding: 10
            text: combo.optionLabel(modelData)
            color: theme.titleInk
            font.family: theme.uiFont
            font.pixelSize: 12
            verticalAlignment: Text.AlignVCenter
            wrapMode: Text.Wrap
            maximumLineCount: combo.popupTextMaximumLineCount
            elide: Text.ElideRight
        }
    }
}

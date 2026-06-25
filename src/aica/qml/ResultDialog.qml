import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    width: 760
    height: 560
    color: "transparent"

    readonly property var themeTokens: typeof theme !== "undefined" ? theme : ({})
    readonly property color shellBg: themeTokens.shellBg || "#FFFFFF"
    readonly property color panelBg: themeTokens.panelBg || "#FFFFFF"
    readonly property color titleInk: themeTokens.titleInk || "#18202E"
    readonly property color bodyInk: themeTokens.bodyInk || "#4A5565"
    readonly property color labelInk: themeTokens.labelInk || "#9AA4B3"
    readonly property color mutedInk: themeTokens.mutedInk || "#A9B1BD"
    readonly property color accent: themeTokens.accent || "#2A313F"
    readonly property color fieldBg: themeTokens.fieldBg || "#F8F9FA"
    readonly property color fieldLine: themeTokens.fieldLine || "#E5E7EB"
    readonly property string uiFont: themeTokens.uiFont || (resultDialogBridge ? resultDialogBridge.uiFont : "Microsoft YaHei UI")
    readonly property int radiusCard: themeTokens.radiusCard || 28
    readonly property int fontCaption: themeTokens.fontCaption || 11
    readonly property int fontBody: themeTokens.fontBody || 12
    readonly property int fontBodyLg: themeTokens.fontBodyLg || 13
    readonly property int fontTitle: themeTokens.fontTitle || 18
    readonly property int outerPadding: 22
    readonly property int cardRadius: root.radiusCard
    readonly property int sectionGap: 10
    readonly property int contentWidth: width - outerPadding * 2
    readonly property int fieldGap: 14
    readonly property int fieldWidth: (contentWidth - fieldGap) / 2
    readonly property int titleWeight: 600
    readonly property int sectionWeight: 600
    readonly property int labelWeight: 500
    readonly property int bodyWeight: 400
    property bool syncingFields: false

    function syncFields() {
        syncingFields = true
        if (titleEdit.text !== resultDialogBridge.title) {
            titleEdit.text = resultDialogBridge.title
        }
        if (groupNameEdit.text !== resultDialogBridge.groupName) {
            groupNameEdit.text = resultDialogBridge.groupName
        }
        if (environmentEdit.text !== resultDialogBridge.environment) {
            environmentEdit.text = resultDialogBridge.environment
        }
        productLineEdit.currentIndex = root.optionIndex(resultDialogBridge.productLineOptions, resultDialogBridge.productLine)
        if (ticketTypeEdit.text !== resultDialogBridge.ticketType) {
            ticketTypeEdit.text = resultDialogBridge.ticketType
        }
        if (summaryEdit.text !== resultDialogBridge.recognitionConclusion) {
            summaryEdit.text = resultDialogBridge.recognitionConclusion
        }
        syncingFields = false
    }

    function pushField(name, value) {
        if (!syncingFields) {
            resultDialogBridge.updateField(name, value)
        }
    }

    function optionIndex(options, value) {
        var target = String(value || "")
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index] || "") === target) {
                return index
            }
        }
        return -1
    }

    function projectCandidateTitle(candidate) {
        if (!candidate) {
            return ""
        }
        var title = String(candidate.projectName || "")
        var taskOrderNo = String(candidate.taskOrderNo || "")
        if (title.length > 0 && taskOrderNo.length > 0) {
            return title + " / " + taskOrderNo
        }
        return title.length > 0 ? title : taskOrderNo
    }

    function projectCandidateReason(candidate) {
        if (!candidate) {
            return ""
        }
        var reason = String(candidate.matchReason || "")
        if (reason === "alias_exact") {
            return "群名别名命中"
        }
        if (reason === "project_name_match") {
            return "项目名匹配"
        }
        if (reason === "task_order_match") {
            return "任务单号匹配"
        }
        if (reason === "alias_match") {
            return "别名匹配"
        }
        if (reason === "customer_match") {
            return "客户名匹配"
        }
        return reason
    }

    Connections {
        target: resultDialogBridge
        function onDataChanged() {
            root.syncFields()
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: root.cardRadius
        color: root.panelBg
        antialiasing: true

        Rectangle {
            anchors.fill: parent
            radius: root.cardRadius
            color: root.shellBg
            opacity: 0.18
        }

        Item {
            anchors.fill: parent

            Item {
                id: header
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                height: 52

                MouseArea {
                    anchors.left: parent.left
                    anchors.right: headerActions.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    acceptedButtons: Qt.LeftButton
                    onPressed: resultDialogBridge.startWindowDrag()
                }

                Text {
                    x: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    text: "\u5de5\u5355\u5f85\u529e\u786e\u8ba4"
                    color: root.titleInk
                    font.family: root.uiFont
                    font.pixelSize: 18
                    font.weight: root.titleWeight
                }

                Row {
                    id: headerActions
                    anchors.right: parent.right
                    anchors.rightMargin: root.outerPadding
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    Rectangle {
                        width: closeText.implicitWidth + 24
                        height: 32
                        radius: 16
                        color: "#FFFFFF"
                        border.width: 1
                        border.color: root.fieldLine

                        Text {
                            id: closeText
                            anchors.centerIn: parent
                            text: "\u5173\u95ed"
                            color: root.bodyInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 700
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: resultDialogBridge.closeDialog()
                        }
                    }

                    Rectangle {
                        width: saveText.implicitWidth + 24
                        height: 32
                        radius: 16
                        color: root.accent
                        border.width: 0
                        border.color: "transparent"

                        Text {
                            id: saveText
                            anchors.centerIn: parent
                            text: "\u4fdd\u5b58"
                            color: "#FFFFFF"
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: 700
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: resultDialogBridge.saveDialog()
                        }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                height: 1
                color: root.fieldLine
            }

            Rectangle {
                id: footerBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.leftMargin: root.outerPadding
                anchors.rightMargin: root.outerPadding
                anchors.bottomMargin: 16
                height: 46
                radius: 18
                color: root.fieldBg

                Text {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    anchors.verticalCenter: parent.verticalCenter
                    elide: Text.ElideRight
                    text: resultDialogBridge.productLineError.length > 0 ? resultDialogBridge.productLineError : resultDialogBridge.saveHint
                    color: resultDialogBridge.productLineError.length > 0 ? "#D93025" : root.mutedInk
                    font.family: root.uiFont
                    font.pixelSize: 11
                    font.weight: root.bodyWeight
                }
            }

            Flickable {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: header.bottom
                anchors.bottom: footerBar.top
                anchors.bottomMargin: 10
                clip: true
                contentWidth: width
                contentHeight: contentColumn.implicitHeight + 12
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: contentColumn
                    x: root.outerPadding
                    y: 12
                    width: root.contentWidth
                    spacing: root.sectionGap

                    Row {
                        spacing: 6

                        Rectangle {
                            height: 24
                            width: scenarioText.implicitWidth + 16
                            radius: 13
                            color: root.fieldBg

                            Text {
                                id: scenarioText
                                anchors.centerIn: parent
                                text: resultDialogBridge.scenario
                                color: "#5B6574"
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.labelWeight
                            }
                        }

                        Rectangle {
                            height: 24
                            width: Math.min(contentColumn.width - 110, modelText.implicitWidth + 16)
                            radius: 13
                            color: root.fieldBg

                            Text {
                                id: modelText
                                anchors.centerIn: parent
                                width: parent.width - 14
                                elide: Text.ElideMiddle
                                horizontalAlignment: Text.AlignHCenter
                                text: resultDialogBridge.model
                                color: "#5B6574"
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.labelWeight
                            }
                        }

                        Rectangle {
                            height: 24
                            width: timingText.implicitWidth + 16
                            radius: 13
                            color: root.fieldBg
                            visible: resultDialogBridge.timingSummary.length > 0

                            Text {
                                id: timingText
                                anchors.centerIn: parent
                                text: resultDialogBridge.timingSummary
                                color: "#5B6574"
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.labelWeight
                            }
                        }
                    }

                    Item {
                        width: parent.width
                        height: Math.max(38, titleEdit.contentHeight + 4)

                        TextEdit {
                            id: titleEdit
                            anchors.fill: parent
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                            textFormat: TextEdit.PlainText
                            color: root.titleInk
                            font.family: root.uiFont
                            font.pixelSize: 16
                            font.weight: root.titleWeight
                            verticalAlignment: TextEdit.AlignTop
                            onTextChanged: root.pushField("title", text)
                        }
                    }

                    Item {
                        width: parent.width
                        height: 120

                        Column {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            width: root.fieldWidth
                            spacing: root.fieldGap

                            Rectangle {
                                width: parent.width
                                height: 52
                                radius: 16
                                color: root.fieldBg

                                Text {
                                    x: 14
                                    y: 12
                                    text: "\u7fa4\u804a\u540d\u79f0"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: groupNameEdit
                                    x: 14
                                    y: 27
                                    width: parent.width - 28
                                    height: 22
                                    clip: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("group_name", text)
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 52
                                radius: 16
                                color: root.fieldBg
                                border.width: resultDialogBridge.productLineError.length > 0 ? 1 : 0
                                border.color: resultDialogBridge.productLineError.length > 0 ? "#D93025" : root.fieldLine

                                Text {
                                    x: 14
                                    y: 12
                                    text: resultDialogBridge.productLineRequired ? "\u4ea7\u54c1\u7ebf *" : "\u4ea7\u54c1\u7ebf"
                                    color: resultDialogBridge.productLineError.length > 0 ? "#D93025" : root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                ComboBox {
                                    id: productLineEdit
                                    x: 14
                                    y: 24
                                    width: parent.width - 28
                                    height: 24
                                    model: resultDialogBridge.productLineOptions
                                    currentIndex: root.optionIndex(resultDialogBridge.productLineOptions, resultDialogBridge.productLine)
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    enabled: resultDialogBridge.productLineOptions.length > 1
                                    onActivated: if (currentIndex >= 0) root.pushField("product_line", resultDialogBridge.productLineOptions[currentIndex])

                                    contentItem: Text {
                                        text: productLineEdit.currentIndex >= 0 ? productLineEdit.displayText : (resultDialogBridge.productLineOptions.length > 0 ? "请选择产品线" : "未匹配项目")
                                        color: productLineEdit.currentIndex >= 0 ? root.titleInk : root.mutedInk
                                        font.family: root.uiFont
                                        font.pixelSize: 13
                                        font.weight: root.bodyWeight
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }

                                    indicator: Text {
                                        x: productLineEdit.width - width
                                        y: 0
                                        width: 14
                                        height: productLineEdit.height
                                        text: productLineEdit.popup.visible ? "⌃" : "⌄"
                                        color: productLineEdit.hovered || productLineEdit.popup.visible ? root.accent : root.labelInk
                                        visible: resultDialogBridge.productLineOptions.length > 1
                                        font.family: root.uiFont
                                        font.pixelSize: 14
                                        horizontalAlignment: Text.AlignRight
                                        verticalAlignment: Text.AlignVCenter
                                    }

                                    background: Item {}

                                    delegate: ItemDelegate {
                                        id: productLineOption
                                        width: productLineEdit.width
                                        height: 38
                                        padding: 0
                                        highlighted: productLineEdit.highlightedIndex === index

                                        background: Rectangle {
                                            anchors.fill: parent
                                            anchors.leftMargin: 4
                                            anchors.rightMargin: 4
                                            anchors.topMargin: 2
                                            anchors.bottomMargin: 2
                                            radius: 8
                                            color: productLineEdit.currentIndex === index ? "#EDF1F6" : (productLineOption.hovered || productLineOption.highlighted ? "#F6F8FA" : "transparent")
                                        }

                                        contentItem: Text {
                                            leftPadding: 12
                                            rightPadding: 12
                                            text: modelData
                                            color: root.titleInk
                                            font.family: root.uiFont
                                            font.pixelSize: 13
                                            font.weight: productLineEdit.currentIndex === index ? 700 : root.bodyWeight
                                            verticalAlignment: Text.AlignVCenter
                                            elide: Text.ElideRight
                                        }
                                    }

                                    popup: Popup {
                                        y: productLineEdit.height + 6
                                        width: productLineEdit.width
                                        implicitHeight: Math.min(contentItem.implicitHeight + 8, 156)
                                        padding: 4
                                        modal: false
                                        focus: true
                                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent

                                        background: Rectangle {
                                            radius: 12
                                            color: "#FFFFFF"
                                            border.width: 1
                                            border.color: "#DDE3EB"
                                            layer.enabled: true
                                            layer.samples: 4
                                        }

                                        contentItem: ListView {
                                            clip: true
                                            implicitHeight: contentHeight
                                            model: productLineEdit.popup.visible ? productLineEdit.delegateModel : null
                                            currentIndex: productLineEdit.highlightedIndex
                                            boundsBehavior: Flickable.StopAtBounds
                                        }
                                    }
                                }
                            }
                        }

                        Column {
                            anchors.right: parent.right
                            anchors.top: parent.top
                            width: root.fieldWidth
                            spacing: root.fieldGap

                            Rectangle {
                                width: parent.width
                                height: 52
                                radius: 16
                                color: root.fieldBg

                                Text {
                                    x: 14
                                    y: 12
                                    text: "\u73af\u5883"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: environmentEdit
                                    x: 14
                                    y: 27
                                    width: parent.width - 28
                                    height: 22
                                    clip: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("environment", text)
                                }
                            }

                            Rectangle {
                                width: parent.width
                                height: 52
                                radius: 16
                                color: root.fieldBg

                                Text {
                                    x: 14
                                    y: 12
                                    text: "\u5de5\u5355\u7c7b\u578b"
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                TextInput {
                                    id: ticketTypeEdit
                                    x: 14
                                    y: 27
                                    width: parent.width - 28
                                    height: 22
                                    clip: true
                                    readOnly: true
                                    selectByMouse: true
                                    color: root.titleInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                }
                            }
                        }
                    }

                    Rectangle {
                        width: parent.width
                        radius: 16
                        color: root.fieldBg
                        visible: (resultDialogBridge.projectCandidates || []).length > 0
                                 && !resultDialogBridge.hasProjectCandidateSelection
                        implicitHeight: candidatePanel.implicitHeight + 16

                        Column {
                            id: candidatePanel
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 8

                            Text {
                                text: resultDialogBridge.hasProjectCandidateSelection ? "已选中候选项目" : "候选项目"
                                color: root.labelInk
                                font.family: root.uiFont
                                font.pixelSize: 11
                                font.weight: root.labelWeight
                            }

                            Text {
                                text: resultDialogBridge.hasProjectCandidateSelection
                                    ? projectCandidateTitle(resultDialogBridge.selectedProjectCandidate)
                                    : "输入群聊名称后将自动给出项目候选，点选后再保存。"
                                color: root.titleInk
                                font.family: root.uiFont
                                font.pixelSize: 13
                                font.weight: root.bodyWeight
                                wrapMode: Text.Wrap
                            }

                            ListView {
                                width: parent.width
                                implicitHeight: Math.min(contentHeight, 180)
                                clip: true
                                spacing: 8
                                model: resultDialogBridge.projectCandidates

                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: candidateItem.implicitHeight + 18
                                    radius: 12
                                    color: candidateMouseArea.containsMouse ? "#F6F8FA" : "#FFFFFF"
                                    border.width: resultDialogBridge.selectedProjectCandidate.projectId === modelData.projectId ? 1 : 0
                                    border.color: resultDialogBridge.selectedProjectCandidate.projectId === modelData.projectId ? root.accent : "transparent"

                                    Column {
                                        id: candidateItem
                                        anchors.fill: parent
                                        anchors.margins: 10
                                        spacing: 4

                                        Row {
                                            width: parent.width
                                            spacing: 8

                                            Text {
                                                width: parent.width - candidateReason.implicitWidth - parent.spacing
                                                text: projectCandidateTitle(modelData)
                                                color: root.titleInk
                                                font.family: root.uiFont
                                                font.pixelSize: 13
                                                font.weight: 700
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                id: candidateReason
                                                text: projectCandidateReason(modelData)
                                                color: root.labelInk
                                                font.family: root.uiFont
                                                font.pixelSize: 11
                                            }
                                        }

                                        Text {
                                            width: parent.width
                                            text: "客户: " + (modelData.customerName || "未知") + "  别名: " + (modelData.matchedAlias || "无")
                                            color: root.bodyInk
                                            font.family: root.uiFont
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }

                                    MouseArea {
                                        id: candidateMouseArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: resultDialogBridge.chooseProjectCandidate(modelData)
                                    }
                                }
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 6

                        Text {
                            text: "\u672c\u6b21\u8bc6\u522b\u7ed3\u8bba"
                            color: root.labelInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.sectionWeight
                        }

                        Rectangle {
                            width: parent.width
                            height: 176
                            radius: 20
                            color: root.fieldBg

                            Flickable {
                                id: summaryFlick
                                anchors.fill: parent
                                anchors.margins: 12
                                clip: true
                                contentWidth: width
                                contentHeight: Math.max(height, summaryEdit.contentHeight + 2)
                                boundsBehavior: Flickable.StopAtBounds

                                TextEdit {
                                    id: summaryEdit
                                    width: parent.width
                                    wrapMode: TextEdit.Wrap
                                    selectByMouse: true
                                    textFormat: TextEdit.PlainText
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 13
                                    font.weight: root.bodyWeight
                                    onTextChanged: root.pushField("timeline_entry", text)
                                }
                            }

                            Rectangle {
                                anchors.right: parent.right
                                anchors.rightMargin: 6
                                y: 8 + (summaryFlick.contentY / Math.max(1, summaryFlick.contentHeight - summaryFlick.height)) * (parent.height - height - 16)
                                width: 4
                                height: Math.max(30, (summaryFlick.height / Math.max(summaryFlick.contentHeight, 1)) * (parent.height - 16))
                                radius: 2
                                color: "#C7CDD7"
                                visible: summaryFlick.contentHeight > summaryFlick.height + 2
                            }
                        }
                    }

                    Column {
                        width: parent.width
                        spacing: 8
                        visible: false

                        Text {
                            text: "关键证据"
                            color: root.labelInk
                            font.family: root.uiFont
                            font.pixelSize: 12
                            font.weight: root.sectionWeight
                        }

                        Repeater {
                            model: []

                            delegate: Rectangle {
                                width: contentColumn.width
                                height: Math.max(64, evidenceValue.contentHeight + 36)
                                radius: 16
                                color: root.fieldBg

                                Text {
                                    x: 14
                                    y: 12
                                    text: (modelData.label || modelData.type) + " · " + modelData.type
                                    color: root.labelInk
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight
                                }

                                Text {
                                    id: evidenceValue
                                    x: 14
                                    y: 30
                                    width: parent.width - 84
                                    wrapMode: Text.Wrap
                                    text: modelData.value
                                    color: root.bodyInk
                                    font.family: root.uiFont
                                    font.pixelSize: 12
                                    font.weight: root.bodyWeight
                                }

                                Text {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 14
                                    y: 12
                                    text: "移除"
                                    color: "#6B7280"
                                    font.family: root.uiFont
                                    font.pixelSize: 11
                                    font.weight: root.labelWeight

                                    MouseArea {
                                        anchors.fill: parent
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {}
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    visible: parent.contentHeight > parent.height + 2
                    anchors.right: parent.right
                    anchors.rightMargin: 4
                    y: 8 + (parent.contentY / Math.max(1, parent.contentHeight - parent.height)) * (parent.height - height - 16)
                    width: 4
                    height: Math.max(56, (parent.height / Math.max(parent.contentHeight, 1)) * (parent.height - 16))
                    radius: 2
                    color: "#BEC6D2"
                }
            }
        }
    }

    Component.onCompleted: syncFields()
}

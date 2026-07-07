import QtQuick
import QtQuick.Controls

Rectangle {
    id: timelineCard
    width: parent ? parent.width : 0
    radius: 18
    color: rootContext ? rootContext.timelineBg : "#F5F5F5"
    border.width: editing || dropActive || attachmentTarget ? 1 : 0
    border.color: dropActive
                  ? (rootContext ? rootContext.accent : "#2A313F")
                  : ((editing || attachmentTarget) ? (rootContext ? rootContext.accent : "#2A313F") : (rootContext ? rootContext.fieldLine : "#E5E7EB"))
    implicitHeight: Math.max(124, entryColumn.implicitHeight + 28)

    property var rootContext
    property var todoDetailBridge
    property var eventData
    property string eventId: eventData && eventData.id ? eventData.id : ""
    property string originalContent: eventData && eventData.content ? eventData.content : ""
    property string registeredEditorEventId: ""
    readonly property bool editing: rootContext ? rootContext.activeTimelineEditingEventId === eventId : false
    readonly property bool detailLocked: rootContext ? rootContext.timelineDetailVisible : false
    readonly property bool bodyEditingLocked: detailLocked
    property bool dropActive: dropZone.containsDrag
    property bool attachmentTarget: rootContext && rootContext.activeAttachmentEventId === eventId
    property bool attachmentsExpanded: false
    readonly property int previewMaxHeight: 118
    readonly property int editorMaxHeight: 160
    readonly property string previewText: eventData ? (eventData.summary || eventData.content || "") : ""

    function syncEditorRegistration() {
        var nextEventId = rootContext && eventId.length > 0 ? eventId : ""
        if (registeredEditorEventId === nextEventId) {
            return
        }
        if (registeredEditorEventId.length > 0 && rootContext) {
            rootContext.unregisterTimelineEditorCard(registeredEditorEventId, timelineCard)
        }
        registeredEditorEventId = ""
        if (nextEventId.length > 0 && rootContext) {
            rootContext.registerTimelineEditorCard(nextEventId, timelineCard)
            registeredEditorEventId = nextEventId
        }
    }

    function beginEditing() {
        if (bodyEditingLocked) {
            return false
        }
        timelineCard.originalContent = eventData ? (eventData.rawContent || eventData.content || "") : ""
        if (rootContext) {
            rootContext.markAttachmentTarget(timelineCard.eventId)
            return rootContext.requestTimelineEdit(timelineCard.eventId)
        }
        return false
    }

    function exitEditing() {
        if (rootContext) {
            rootContext.exitTimelineEdit(eventId)
        }
    }

    function cancelEditingForSwitch() {
        timelineEditor.text = timelineCard.originalContent
        if (todoDetailBridge) {
            todoDetailBridge.updateTimelineContent(timelineCard.eventId, timelineCard.originalContent)
        }
        exitEditing()
    }

    onRootContextChanged: syncEditorRegistration()
    onEventIdChanged: syncEditorRegistration()
    onDetailLockedChanged: {
        if (bodyEditingLocked && editing) {
            exitEditing()
        }
    }
    Component.onDestruction: {
        if (registeredEditorEventId.length > 0 && rootContext) {
            rootContext.unregisterTimelineEditorCard(registeredEditorEventId, timelineCard)
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: !editing && !bodyEditingLocked
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton
        onClicked: timelineCard.beginEditing()
    }

    Column {
        id: entryColumn
        x: 16
        y: 14
        width: parent.width - 32
        spacing: 10

        Item {
            width: parent.width
            height: 40

            Rectangle {
                x: 0
                y: 4
                width: 8
                height: 8
                radius: 4
                color: eventData && eventData.kind === "manual"
                       ? (rootContext ? rootContext.accent : "#2A313F")
                       : "#D7DDE8"
            }

            Column {
                x: 16
                y: 0
                spacing: 4

                Text {
                    text: eventData ? eventData.timeLabel : ""
                    color: rootContext ? rootContext.mutedInk : "#B3BBC8"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.bodyWeight : 400
                }

                Text {
                    text: eventData ? eventData.scenario : ""
                    color: rootContext ? rootContext.labelInk : "#9AA4B3"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500
                }

                Rectangle {
                    visible: !!(eventData && eventData.taskStatusLabel)
                    width: statusLabel.implicitWidth + 16
                    height: 22
                    radius: 11
                    color: eventData && eventData.taskStatus === "failed"
                           ? "#FDECEC"
                           : ((eventData && eventData.taskStatus === "completed") ? "#E7F5ED" : "#ECEFF3")

                    Text {
                        id: statusLabel
                        anchors.centerIn: parent
                        text: eventData && eventData.taskStatusLabel ? eventData.taskStatusLabel : ""
                        color: eventData && eventData.taskStatus === "failed"
                               ? "#B42318"
                               : ((eventData && eventData.taskStatus === "completed")
                                  ? "#17663A"
                                  : (rootContext ? rootContext.accent : "#2A313F"))
                        font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                        font.pixelSize: 10
                        font.weight: rootContext ? rootContext.labelWeight : 500
                    }
                }

                Text {
                    visible: !!(eventData && eventData.taskStatusDetail)
                    text: eventData && eventData.taskStatusDetail ? eventData.taskStatusDetail : ""
                    color: eventData && eventData.taskStatus === "failed"
                           ? "#C9414B"
                           : (rootContext ? rootContext.mutedInk : "#B3BBC8")
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 10
                    font.weight: rootContext ? rootContext.bodyWeight : 400
                    wrapMode: Text.Wrap
                    width: Math.min(240, entryColumn.width - 20)
                }
            }

            Row {
                anchors.right: parent.right
                anchors.top: parent.top
                spacing: 12

                Text {
                    visible: editing && !bodyEditingLocked
                    text: "保存"
                    color: rootContext ? rootContext.accent : "#2A313F"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            todoDetailBridge.commitTimelineContent(timelineCard.eventId, timelineEditor.text)
                            timelineCard.originalContent = timelineEditor.text
                            timelineCard.exitEditing()
                        }
                    }
                }

                Text {
                    visible: editing && !bodyEditingLocked
                    text: "取消"
                    color: rootContext ? rootContext.mutedInk : "#B3BBC8"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: timelineCard.cancelEditingForSwitch()
                    }
                }

                Text {
                    text: "详情"
                    color: rootContext ? rootContext.accent : "#2A313F"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (todoDetailBridge) {
                                todoDetailBridge.openTimelineDetail(timelineCard.eventId)
                            }
                        }
                    }
                }

                Text {
                    text: "上传附件"
                    color: rootContext ? rootContext.accent : "#2A313F"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (rootContext) {
                                rootContext.markAttachmentTarget(timelineCard.eventId)
                            }
                            todoDetailBridge.requestAttachmentSelection(timelineCard.eventId)
                        }
                    }
                }

                Text {
                    text: "粘贴截图"
                    color: rootContext ? rootContext.accent : "#2A313F"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (rootContext) {
                                rootContext.markAttachmentTarget(timelineCard.eventId)
                            }
                            todoDetailBridge.requestClipboardImagePaste(timelineCard.eventId)
                        }
                    }
                }

                Text {
                    text: "删除"
                    color: "#E35B66"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        enabled: !bodyEditingLocked
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: todoDetailBridge.deleteTimelineCard(timelineCard.eventId)
                    }
                }
            }
        }

        ScrollView {
            id: timelinePreviewScroll
            visible: !editing
            width: parent.width
            height: Math.min(timelinePreview.contentHeight, timelineCard.previewMaxHeight)
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: timelinePreview.contentHeight > height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

                TextArea {
                    id: timelinePreview
                    readOnly: true
                    width: timelinePreviewScroll.availableWidth
                    wrapMode: TextEdit.Wrap
                    textFormat: TextEdit.PlainText
                color: rootContext ? rootContext.bodyInk : "#4A5565"
                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                font.pixelSize: 13
                font.weight: rootContext ? rootContext.bodyWeight : 400
                text: timelineCard.previewText
                selectByMouse: false
                leftPadding: 0
                rightPadding: 0
                topPadding: 0
                bottomPadding: 0
                background: null
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                acceptedButtons: Qt.LeftButton
                onClicked: timelineCard.beginEditing()
                onDoubleClicked: {
                    if (todoDetailBridge) {
                        todoDetailBridge.openTimelineDetail(timelineCard.eventId)
                    }
                }
            }
        }

        Text {
            visible: !editing && timelinePreview.contentHeight > timelineCard.previewMaxHeight
            text: "内容较长，可滚动查看，双击或点详情查看完整记录"
            color: rootContext ? rootContext.accent : "#2A313F"
            font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
            font.pixelSize: 11
            font.weight: rootContext ? rootContext.labelWeight : 500

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (todoDetailBridge) {
                        todoDetailBridge.openTimelineDetail(timelineCard.eventId)
                    }
                }
            }
        }

        ScrollView {
            id: timelineEditorScroll
            visible: editing
            width: parent.width
            height: Math.min(timelineCard.editorMaxHeight, Math.max(60, timelineEditor.contentHeight + 4))
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: timelineEditor.contentHeight > height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

            TextArea {
                id: timelineEditor
                width: timelineEditorScroll.availableWidth
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                textFormat: TextEdit.PlainText
                color: rootContext ? rootContext.bodyInk : "#4A5565"
                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                font.pixelSize: 13
                font.weight: rootContext ? rootContext.bodyWeight : 400
                text: eventData ? (eventData.rawContent || eventData.content || "") : ""
                leftPadding: 0
                rightPadding: 0
                topPadding: 0
                bottomPadding: 0
                background: null

                onVisibleChanged: {
                    if (visible) {
                        if (rootContext) {
                            rootContext.markAttachmentTarget(timelineCard.eventId)
                        }
                        timelineCard.originalContent = eventData ? (eventData.rawContent || eventData.content || "") : ""
                        forceActiveFocus()
                        cursorPosition = length
                    }
                }

                onTextChanged: todoDetailBridge.updateTimelineContent(timelineCard.eventId, text)
            }
        }

        Column {
            width: parent.width
            spacing: 8
            visible: eventData && eventData.attachmentCount > 0

            Rectangle {
                width: parent.width
                height: 34
                radius: 12
                color: rootContext ? rootContext.fieldBg : "#F5F5F5"
                border.width: 1
                border.color: rootContext ? rootContext.fieldLine : "#E5E7EB"

                Text {
                    x: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: "附件 " + (eventData ? eventData.attachmentCount : 0)
                    color: rootContext ? rootContext.labelInk : "#9AA4B3"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500
                }

                Text {
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: timelineCard.attachmentsExpanded ? "收起" : "展开"
                    color: rootContext ? rootContext.accent : "#2A313F"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (rootContext) {
                                rootContext.markAttachmentTarget(timelineCard.eventId)
                            }
                            timelineCard.attachmentsExpanded = !timelineCard.attachmentsExpanded
                        }
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 8
                visible: timelineCard.attachmentsExpanded

                Repeater {
                    model: eventData ? eventData.attachments : []

                    delegate: Rectangle {
                        width: entryColumn.width
                        height: modelData.isImage ? 74 : 42
                        radius: 12
                        color: rootContext ? rootContext.fieldBg : "#F5F5F5"
                        border.width: 1
                        border.color: rootContext ? rootContext.fieldLine : "#E5E7EB"

                        Rectangle {
                            id: previewThumb
                            width: modelData.isImage ? 58 : 48
                            height: modelData.isImage ? 58 : 26
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            radius: modelData.isImage ? 10 : 8
                            color: modelData.isPreviewable
                                   ? (rootContext ? rootContext.accentTint : "#ECEFF3")
                                   : (rootContext ? rootContext.fieldBg : "#F5F5F5")
                            visible: modelData.isPreviewable
                            border.width: 0

                            Image {
                                anchors.fill: parent
                                anchors.margins: 1
                                fillMode: Image.PreserveAspectCrop
                                visible: modelData.isImage
                                source: modelData.isImage ? modelData.fileUrl : ""
                                asynchronous: true
                                cache: false
                                smooth: true
                                clip: true
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: modelData.isVideo
                                text: "视频"
                                color: rootContext ? rootContext.accent : "#2A313F"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 11
                                font.weight: rootContext ? rootContext.labelWeight : 500
                            }

                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (rootContext) {
                                        rootContext.markAttachmentTarget(timelineCard.eventId)
                                    }
                                    if (modelData.isPreviewable) {
                                        todoDetailBridge.previewAttachment(modelData.path)
                                    } else {
                                        todoDetailBridge.activateAttachment(
                                            modelData.path,
                                            modelData.isImage,
                                            modelData.isVideo,
                                            modelData.name
                                        )
                                    }
                                }
                            }
                        }

                        Column {
                            anchors.left: previewThumb.visible ? previewThumb.right : parent.left
                            anchors.leftMargin: previewThumb.visible ? 12 : 12
                            anchors.right: actionRow.left
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 4

                            Text {
                                width: parent.width
                                elide: Text.ElideMiddle
                                text: modelData.name
                                color: rootContext ? rootContext.bodyInk : "#4A5565"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 11
                                font.weight: rootContext ? rootContext.bodyWeight : 400
                            }

                            Text {
                                width: parent.width
                                elide: Text.ElideRight
                                text: {
                                    var sizeLabel = rootContext ? rootContext.formatFileSize(modelData.sizeBytes) : ""
                                    if (modelData.isPreviewable) {
                                        return sizeLabel.length > 0 ? sizeLabel + " · 可预览" : "可预览"
                                    }
                                    return sizeLabel
                                }
                                color: rootContext ? rootContext.mutedInk : "#B3BBC8"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 10
                                font.weight: rootContext ? rootContext.bodyWeight : 400
                            }
                        }

                        Row {
                            id: actionRow
                            anchors.right: parent.right
                            anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 10

                            Text {
                                visible: modelData.isPreviewable
                                text: "预览"
                                color: rootContext ? rootContext.accent : "#2A313F"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 10
                                font.weight: rootContext ? rootContext.labelWeight : 500

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (rootContext) {
                                            rootContext.markAttachmentTarget(timelineCard.eventId)
                                        }
                                        todoDetailBridge.previewAttachment(modelData.path)
                                    }
                                }
                            }

                            Text {
                                visible: modelData.isPreviewable
                                text: "复制"
                                color: rootContext ? rootContext.accent : "#2A313F"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 10
                                font.weight: rootContext ? rootContext.labelWeight : 500

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (rootContext) {
                                            rootContext.markAttachmentTarget(timelineCard.eventId)
                                        }
                                        todoDetailBridge.copyAttachment(
                                            modelData.path,
                                            modelData.isImage,
                                            modelData.isVideo
                                        )
                                    }
                                }
                            }

                            Text {
                                visible: !modelData.isPreviewable
                                text: "复制名"
                                color: rootContext ? rootContext.accent : "#2A313F"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 10
                                font.weight: rootContext ? rootContext.labelWeight : 500

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (rootContext) {
                                            rootContext.markAttachmentTarget(timelineCard.eventId)
                                        }
                                        todoDetailBridge.copyAttachmentName(modelData.name)
                                    }
                                }
                            }

                            Text {
                                visible: !modelData.isPreviewable
                                text: "复制路径"
                                color: rootContext ? rootContext.accent : "#2A313F"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 10
                                font.weight: rootContext ? rootContext.labelWeight : 500

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (rootContext) {
                                            rootContext.markAttachmentTarget(timelineCard.eventId)
                                        }
                                        todoDetailBridge.copyAttachmentPath(modelData.path)
                                    }
                                }
                            }

                            Text {
                                visible: !modelData.isPreviewable
                                text: "打开"
                                color: rootContext ? rootContext.accent : "#2A313F"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 10
                                font.weight: rootContext ? rootContext.labelWeight : 500

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (rootContext) {
                                            rootContext.markAttachmentTarget(timelineCard.eventId)
                                        }
                                        todoDetailBridge.openAttachmentFolder(modelData.path)
                                    }
                                }
                            }

                            Text {
                                visible: !modelData.isPreviewable
                                text: "下载"
                                color: rootContext ? rootContext.accent : "#2A313F"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 10
                                font.weight: rootContext ? rootContext.labelWeight : 500

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (rootContext) {
                                            rootContext.markAttachmentTarget(timelineCard.eventId)
                                        }
                                        todoDetailBridge.downloadAttachment(modelData.path, modelData.name)
                                    }
                                }
                            }

                            Text {
                                text: "移除"
                                color: "#E35B66"
                                font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                                font.pixelSize: 10
                                font.weight: rootContext ? rootContext.labelWeight : 500

                                MouseArea {
                                    anchors.fill: parent
                                    enabled: !bodyEditingLocked
                                    cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: {
                                        if (rootContext) {
                                            rootContext.markAttachmentTarget(timelineCard.eventId)
                                        }
                                        todoDetailBridge.removeTimelineAttachment(timelineCard.eventId, modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    DropArea {
        id: dropZone
        anchors.fill: parent
        enabled: !timelineCard.editing

        onEntered: function(drag) {
            if (drag.hasUrls) {
                drag.acceptProposedAction()
            }
        }

        onDropped: function(drop) {
            if (!drop.hasUrls) {
                return
            }
            if (rootContext) {
                rootContext.markAttachmentTarget(timelineCard.eventId)
            }
            todoDetailBridge.addTimelineAttachmentsFromUrls(timelineCard.eventId, drop.urls)
            drop.acceptProposedAction()
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: rootContext ? rootContext.accentTint : "#ECEFF3"
        opacity: dropActive ? 0.88 : 0
        visible: dropActive
        border.width: 1
        border.color: rootContext ? rootContext.accent : "#2A313F"

        Text {
            anchors.centerIn: parent
            text: "释放即可上传附件"
            color: rootContext ? rootContext.accent : "#2A313F"
            font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
            font.pixelSize: 13
            font.weight: rootContext ? rootContext.sectionWeight : 600
        }
    }
}

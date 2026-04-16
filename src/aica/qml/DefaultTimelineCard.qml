import QtQuick

Rectangle {
    id: timelineCard
    width: parent ? parent.width : 0
    radius: 18
    color: rootContext ? rootContext.timelineBg : "#F7F7F4"
    border.width: editing || dropActive || attachmentTarget ? 1 : 0
    border.color: dropActive
                  ? (rootContext ? rootContext.accent : "#3D7CFF")
                  : ((editing || attachmentTarget) ? "#D7E5FF" : (rootContext ? rootContext.fieldLine : "#E7EDF5"))
    implicitHeight: Math.max(124, entryColumn.implicitHeight + 28)

    property var rootContext
    property var todoDetailBridge
    property var eventData
    property bool editing: false
    property string eventId: eventData && eventData.id ? eventData.id : ""
    property string originalContent: eventData && eventData.content ? eventData.content : ""
    property bool dropActive: dropZone.containsDrag
    property bool attachmentTarget: rootContext && rootContext.activeAttachmentEventId === eventId
    property bool attachmentsExpanded: false

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
                       ? (rootContext ? rootContext.accent : "#3D7CFF")
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
                           : ((eventData && eventData.taskStatus === "completed") ? "#EAF7EE" : "#EEF4FF")

                    Text {
                        id: statusLabel
                        anchors.centerIn: parent
                        text: eventData ? eventData.taskStatusLabel : ""
                        color: eventData && eventData.taskStatus === "failed"
                               ? "#C9414B"
                               : ((eventData && eventData.taskStatus === "completed")
                                  ? "#287D4E"
                                  : (rootContext ? rootContext.accent : "#3D7CFF"))
                        font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                        font.pixelSize: 10
                        font.weight: rootContext ? rootContext.labelWeight : 500
                    }
                }

                Text {
                    visible: !!(eventData && eventData.taskStatusDetail)
                    text: eventData ? eventData.taskStatusDetail : ""
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
                    text: editing ? "编辑中" : "点击编辑"
                    color: editing
                           ? (rootContext ? rootContext.accent : "#3D7CFF")
                           : (rootContext ? rootContext.mutedInk : "#B3BBC8")
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500
                }

                Text {
                    visible: editing
                    text: "保存"
                    color: rootContext ? rootContext.accent : "#3D7CFF"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            todoDetailBridge.commitTimelineContent(timelineCard.eventId, timelineEditor.text)
                            timelineCard.originalContent = timelineEditor.text
                            timelineCard.editing = false
                        }
                    }
                }

                Text {
                    visible: editing
                    text: "取消"
                    color: rootContext ? rootContext.mutedInk : "#B3BBC8"
                    font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
                    font.pixelSize: 11
                    font.weight: rootContext ? rootContext.labelWeight : 500

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            timelineEditor.text = timelineCard.originalContent
                            todoDetailBridge.updateTimelineContent(timelineCard.eventId, timelineCard.originalContent)
                            timelineCard.editing = false
                        }
                    }
                }

                Text {
                    text: "上传附件"
                    color: rootContext ? rootContext.accent : "#3D7CFF"
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
                    color: rootContext ? rootContext.accent : "#3D7CFF"
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
                        cursorShape: Qt.PointingHandCursor
                        onClicked: todoDetailBridge.deleteTimelineEntry(timelineCard.eventId)
                    }
                }
            }
        }

        Text {
            id: timelinePreview
            visible: !editing
            width: parent.width
            wrapMode: Text.Wrap
            text: eventData ? eventData.content : ""
            color: rootContext ? rootContext.bodyInk : "#4A5565"
            font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
            font.pixelSize: 13
            font.weight: rootContext ? rootContext.bodyWeight : 400

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (rootContext) {
                        rootContext.markAttachmentTarget(timelineCard.eventId)
                    }
                    timelineCard.originalContent = eventData ? eventData.content : ""
                    timelineCard.editing = true
                }
            }
        }

        TextEdit {
            id: timelineEditor
            visible: editing
            width: parent.width
            height: Math.max(60, contentHeight + 4)
            wrapMode: TextEdit.Wrap
            selectByMouse: true
            textFormat: TextEdit.PlainText
            color: rootContext ? rootContext.bodyInk : "#4A5565"
            font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
            font.pixelSize: 13
            font.weight: rootContext ? rootContext.bodyWeight : 400
            text: eventData ? eventData.content : ""

            onVisibleChanged: {
                if (visible) {
                    if (rootContext) {
                        rootContext.markAttachmentTarget(timelineCard.eventId)
                    }
                    timelineCard.originalContent = eventData ? eventData.content : ""
                    forceActiveFocus()
                    cursorPosition = length
                }
            }

            onTextChanged: todoDetailBridge.updateTimelineContent(timelineCard.eventId, text)
        }

        Column {
            width: parent.width
            spacing: 8
            visible: eventData && eventData.attachmentCount > 0

            Rectangle {
                width: parent.width
                height: 34
                radius: 12
                color: "#FFFFFF"
                border.width: 0

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
                    color: rootContext ? rootContext.accent : "#3D7CFF"
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
                        color: "#FFFFFF"
                        border.width: 0

                        Rectangle {
                            id: previewThumb
                            width: modelData.isImage ? 58 : 48
                            height: modelData.isImage ? 58 : 26
                            anchors.left: parent.left
                            anchors.leftMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                            radius: modelData.isImage ? 10 : 8
                            color: modelData.isPreviewable
                                   ? (rootContext ? rootContext.accentTint : "#EEF4FF")
                                   : (rootContext ? rootContext.fieldBg : "#F7F7F4")
                            visible: modelData.isPreviewable
                            border.width: 0

                            Image {
                                anchors.fill: parent
                                anchors.margins: 1
                                fillMode: Image.PreserveAspectCrop
                                visible: modelData.isImage
                                source: modelData.fileUrl
                                asynchronous: true
                                cache: false
                                smooth: true
                                clip: true
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: modelData.isVideo
                                text: "视频"
                                color: rootContext ? rootContext.accent : "#3D7CFF"
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
                                color: rootContext ? rootContext.accent : "#3D7CFF"
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
                                color: rootContext ? rootContext.accent : "#3D7CFF"
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
                                color: rootContext ? rootContext.accent : "#3D7CFF"
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
                                color: rootContext ? rootContext.accent : "#3D7CFF"
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
                                color: rootContext ? rootContext.accent : "#3D7CFF"
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
                                color: rootContext ? rootContext.accent : "#3D7CFF"
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
                                    cursorShape: Qt.PointingHandCursor
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
        color: rootContext ? rootContext.accentTint : "#EEF4FF"
        opacity: dropActive ? 0.88 : 0
        visible: dropActive
        border.width: 1
        border.color: rootContext ? rootContext.accent : "#3D7CFF"

        Text {
            anchors.centerIn: parent
            text: "释放即可上传附件"
            color: rootContext ? rootContext.accent : "#3D7CFF"
            font.family: rootContext ? rootContext.uiFont : "Microsoft YaHei UI"
            font.pixelSize: 13
            font.weight: rootContext ? rootContext.sectionWeight : 600
        }
    }
}

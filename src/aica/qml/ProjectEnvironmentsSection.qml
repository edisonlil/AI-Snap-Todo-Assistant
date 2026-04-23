import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: projectEnvSection
    required property var theme

    visible: controlPanelBridge.currentSection === "project_environments"
    spacing: 0
    property string selectedProjectId: controlPanelBridge.projectEnvironmentProjectId || ""

    function ensureProjectSelection() {
        var projects = controlPanelBridge.projects || []
        if (!projects.length) {
            selectedProjectId = ""
            controlPanelBridge.listProjectEnvironments("")
            return
        }
        for (var i = 0; i < projects.length; i += 1) {
            if (projects[i].id === selectedProjectId) {
                return
            }
        }
        selectedProjectId = projects[0].id
        controlPanelBridge.listProjectEnvironments(selectedProjectId)
    }

    onVisibleChanged: {
        if (visible) {
            ensureProjectSelection()
        }
    }

    Component.onCompleted: {
        if (visible) {
            ensureProjectSelection()
        }
    }

    Connections {
        target: controlPanelBridge
        function onDataChanged() {
            if (projectEnvSection.visible) {
                projectEnvSection.ensureProjectSelection()
            }
        }
    }

    ControlPanelSectionCard {
        theme: projectEnvSection.theme
        Layout.fillWidth: true
        implicitHeight: sectionContent.implicitHeight + 32
        color: theme.panelBg

        ColumnLayout {
            id: sectionContent
            anchors.fill: parent
            anchors.margins: 16
            spacing: 14

            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Rectangle {
                    Layout.preferredWidth: 320
                    Layout.fillHeight: true
                    implicitHeight: 520
                    radius: 18
                    color: theme.panelBg
                    border.width: 1
                    border.color: theme.panelLine

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 10

                        Text {
                            text: "项目列表"
                            color: theme.titleInk
                            font.family: theme.uiFont
                            font.pixelSize: 14
                            font.weight: 700
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "选择一个项目后，在右侧维护项目级环境。"
                            color: theme.labelInk
                            font.family: theme.uiFont
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }

                        ListView {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 8
                            model: controlPanelBridge.projects

                            delegate: Rectangle {
                                property bool selected: projectEnvSection.selectedProjectId === modelData.id
                                width: ListView.view.width
                                height: projectColumn.implicitHeight + 18
                                radius: 14
                                color: selected ? theme.accentSoft : theme.panelBg
                                border.width: 1
                                border.color: selected ? theme.accent : theme.panelLine

                                Column {
                                    id: projectColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 6

                                    Text {
                                        width: parent.width
                                        text: modelData.projectName || ""
                                        color: theme.titleInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 13
                                        font.weight: 700
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        width: parent.width
                                        text: "任务单号: " + (modelData.taskOrderNo || "")
                                        color: theme.bodyInk
                                        font.family: theme.uiFont
                                        font.pixelSize: 11
                                        wrapMode: Text.WrapAnywhere
                                    }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        projectEnvSection.selectedProjectId = modelData.id
                                        controlPanelBridge.listProjectEnvironments(modelData.id)
                                    }
                                }
                            }
                        }
                    }
                }

                EnvironmentManagerSection {
                    theme: projectEnvSection.theme
                    scopeMode: "project"
                    projectId: projectEnvSection.selectedProjectId
                    groupsModel: controlPanelBridge.projectEnvironmentGroups
                    Layout.fillWidth: true
                }
            }
        }
    }
}

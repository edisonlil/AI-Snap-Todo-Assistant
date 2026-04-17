import QtQuick

Rectangle {
    id: root
    width: 332
    height: 632
    color: "transparent"
    readonly property string uiFont: "Microsoft YaHei UI"

    StageSummaryPanel {
        anchors.fill: parent
        theme: root
        busy: todoDetailBridge.stageSummaryBusy
        summaryText: todoDetailBridge.stageSummaryText
        errorText: todoDetailBridge.stageSummaryError
        hasSummary: todoDetailBridge.hasStageSummary
        onCloseClicked: todoDetailBridge.toggleStageSummary()
        onCopyClicked: todoDetailBridge.copyStageSummary()
        onRefreshClicked: todoDetailBridge.refreshStageSummary()
        onPresetRewriteRequested: function(key) {
            todoDetailBridge.rewriteStageSummaryWithPreset(key)
        }
        onCustomRewriteRequested: function(text) {
            todoDetailBridge.rewriteStageSummary(text)
        }
        onDragStarted: function(offsetX, offsetY) {
            stageSummaryWindowBridge.beginPanelDrag(offsetX, offsetY)
        }
        onDragMoved: stageSummaryWindowBridge.updatePanelDrag()
        onDragFinished: stageSummaryWindowBridge.finishPanelDrag()
    }
}

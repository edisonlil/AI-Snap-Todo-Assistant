.pragma library

var registry = {
    "default": "DefaultTimelineCard.qml",
    "log_analysis_command": "LogAnalysisTaskCard.qml",
    "log_analysis_result": "LogAnalysisResultCard.qml"
}

function sourceForType(eventType) {
    var key = String(eventType || "")
    if (registry[key]) {
        return registry[key]
    }
    return registry["default"]
}

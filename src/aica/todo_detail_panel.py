"""QML-backed detail panel for a todo item and its timeline."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import uuid

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtQuick import QQuickView
from PyQt6.QtWidgets import QApplication

from .models import TicketSummaryFields
from .ticket_field_resolver import (
    TICKET_TYPE_OPTIONS,
    normalize_ticket_type,
    resolve_product_line,
)
from .todo_store import TimelineEvent, TodoItem

_EMPTY_TEXT = "未填写"


def _format_ts(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%m-%d %H:%M")
    except ValueError:
        return value


def _clean_text(value: str, fallback: str = _EMPTY_TEXT) -> str:
    text = str(value or "").strip()
    return text or fallback


def _normalize_timeline_scenario(kind: str, scenario: str) -> str:
    if kind == "manual":
        return "手动跟进"
    return str(scenario or "系统记录").strip() or "系统记录"


class _TodoDetailBridge(QObject):
    dataChanged = pyqtSignal()
    timelineChanged = pyqtSignal()
    timelineExpandedChanged = pyqtSignal()

    saveRequested = pyqtSignal(str, object)
    closeRequested = pyqtSignal()
    completeRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)
    exportPlanRequested = pyqtSignal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._todo_id: str | None = None
        self._title = ""
        self._group_name = _EMPTY_TEXT
        self._environment = _EMPTY_TEXT
        self._product_line = _EMPTY_TEXT
        self._ticket_type = _EMPTY_TEXT
        self._current_summary = ""
        self._overview = ""
        self._created_at = ""
        self._updated_at = ""
        self._timeline: list[dict[str, str]] = []
        self._timeline_expanded = True

    @pyqtProperty(str, notify=dataChanged)
    def title(self) -> str:
        return self._title

    @pyqtProperty(str, notify=dataChanged)
    def overview(self) -> str:
        return self._overview

    @pyqtProperty(str, notify=dataChanged)
    def groupName(self) -> str:
        return self._group_name

    @pyqtProperty(str, notify=dataChanged)
    def environment(self) -> str:
        return self._environment

    @pyqtProperty(str, notify=dataChanged)
    def productLine(self) -> str:
        return self._product_line

    @pyqtProperty(str, notify=dataChanged)
    def ticketType(self) -> str:
        return self._ticket_type

    @pyqtProperty("QVariantList", constant=True)
    def ticketTypeOptions(self):  # noqa: ANN201
        return list(TICKET_TYPE_OPTIONS)

    @pyqtProperty(str, notify=dataChanged)
    def currentSummary(self) -> str:
        return self._current_summary

    @pyqtProperty(str, notify=dataChanged)
    def createdAtLabel(self) -> str:
        return self._created_at

    @pyqtProperty(str, notify=dataChanged)
    def updatedAtLabel(self) -> str:
        return self._updated_at

    @pyqtProperty(int, notify=timelineChanged)
    def timelineCount(self) -> int:
        return len(self._timeline)

    @pyqtProperty("QVariantList", notify=timelineChanged)
    def timeline(self):  # noqa: ANN201
        return self._timeline

    @pyqtProperty(bool, notify=timelineExpandedChanged)
    def timelineExpanded(self) -> bool:
        return self._timeline_expanded

    def set_todo(self, todo: TodoItem) -> None:
        self._todo_id = todo.id
        self._group_name = _clean_text(todo.summary_fields.group_name)
        self._environment = _clean_text(todo.summary_fields.environment)
        self._product_line = resolve_product_line(raw_value=todo.summary_fields.product_line)
        self._ticket_type = normalize_ticket_type(
            todo.summary_fields.ticket_type,
            summary_text=todo.current_summary,
        )
        self._current_summary = todo.current_summary.strip()
        self._title = todo.title.strip() or "未分类任务"
        self._overview = self._title
        self._created_at = _format_ts(todo.created_at)
        self._updated_at = _format_ts(todo.updated_at)
        self._timeline = [
            {
                "id": event.id,
                "timestamp": event.timestamp,
                "timeLabel": _format_ts(event.timestamp),
                "scenario": _normalize_timeline_scenario(event.kind, event.scenario),
                "content": event.content.strip(),
                "kind": event.kind,
            }
            for event in reversed(todo.timeline)
        ]
        if not self._current_summary and self._timeline:
            self._current_summary = self._timeline[0]["content"]
            self._title = todo.title.strip() or "未分类任务"
            self._overview = self._title
        self._timeline_expanded = bool(self._timeline)
        self.dataChanged.emit()
        self.timelineChanged.emit()
        self.timelineExpandedChanged.emit()

    @pyqtSlot(str, str)
    def updateField(self, name: str, value: str) -> None:
        text = str(value)
        if name == "title":
            self._title = text.strip()
            self._overview = self._title
        elif name == "group_name":
            self._group_name = text
        elif name == "environment":
            self._environment = text
        elif name == "product_line":
            self._product_line = resolve_product_line(raw_value=text)
        elif name == "ticket_type":
            self._ticket_type = normalize_ticket_type(text, summary_text=self._current_summary)
        elif name == "current_summary":
            self._current_summary = text
        else:
            return
        self.dataChanged.emit()

    @pyqtSlot(str, str)
    def updateTimelineContent(self, event_id: str, value: str) -> None:
        for item in self._timeline:
            if item["id"] == event_id:
                item["content"] = str(value)
                return

    @pyqtSlot(str, str)
    def commitTimelineContent(self, event_id: str, value: str) -> None:
        self.updateTimelineContent(event_id, value)
        self._emit_save_request()

    @pyqtSlot(str)
    def addTimelineEntry(self, value: str) -> None:
        content = str(value or "").strip()
        if not content:
            return
        timestamp = datetime.now().isoformat()
        self._timeline.insert(
            0,
            {
                "id": str(uuid.uuid4()),
                "timestamp": timestamp,
                "timeLabel": _format_ts(timestamp),
                "scenario": "鎵嬪姩璺熻繘",
                "content": content,
                "kind": "manual",
            },
        )
        if not self._timeline_expanded:
            self._timeline_expanded = True
            self.timelineExpandedChanged.emit()
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot(str)
    def deleteTimelineEntry(self, event_id: str) -> None:
        remaining = [item for item in self._timeline if item["id"] != event_id]
        if len(remaining) == len(self._timeline):
            return
        self._timeline = remaining
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot()
    def toggleTimeline(self) -> None:
        self._timeline_expanded = not self._timeline_expanded
        self.timelineExpandedChanged.emit()

    @pyqtSlot()
    def saveTodo(self) -> None:
        self._emit_save_request()

    def _build_payload(self) -> dict[str, object] | None:
        if self._todo_id is None:
            return None
        normalized_summary = self._current_summary.strip()
        normalized_title = self._title.strip() or "未分类任务"
        return {
            "title": normalized_title,
            "current_summary": normalized_summary,
            "summary_fields": TicketSummaryFields(
                group_name=_clean_text(self._group_name),
                environment=_clean_text(self._environment),
                product_line=resolve_product_line(raw_value=self._product_line),
                ticket_type=normalize_ticket_type(
                    self._ticket_type,
                    summary_text="\n".join(
                        part
                        for part in (
                            normalized_title,
                            normalized_summary,
                            *(item.get("content", "").strip() for item in self._timeline),
                        )
                        if part
                    ),
                ),
            ).to_dict(),
            "timeline": [
                TimelineEvent(
                    id=item["id"],
                    timestamp=item["timestamp"],
                    kind=item.get("kind", "analysis"),
                    scenario=item.get("scenario", ""),
                    content=item.get("content", "").strip(),
                )
                for item in reversed(self._timeline)
            ],
        }

    def _emit_save_request(self) -> None:
        payload = self._build_payload()
        if self._todo_id is None or payload is None:
            return
        self.saveRequested.emit(self._todo_id, payload)

    @pyqtSlot()
    def closePanel(self) -> None:
        self.closeRequested.emit()

    @pyqtSlot()
    def completeTodo(self) -> None:
        if self._todo_id is None:
            return
        self.completeRequested.emit(self._todo_id)

    @pyqtSlot()
    def deleteTodo(self) -> None:
        if self._todo_id is None:
            return
        self.deleteRequested.emit(self._todo_id)

    @pyqtSlot()
    def exportPlan(self) -> None:
        if self._todo_id is None:
            return
        payload = {
            "title": self._title.strip(),
            "current_summary": self._current_summary.strip(),
            "summary_fields": TicketSummaryFields(
                group_name=_clean_text(self._group_name),
                environment=_clean_text(self._environment),
                product_line=resolve_product_line(raw_value=self._product_line),
                ticket_type=normalize_ticket_type(
                    self._ticket_type,
                    summary_text="\n".join(
                        part
                        for part in (
                            self._title.strip(),
                            self._current_summary.strip(),
                            *(item.get("content", "").strip() for item in self._timeline),
                        )
                        if part
                    ),
                ),
            ).to_dict(),
            "timeline": [
                {
                    "id": item["id"],
                    "timestamp": item["timestamp"],
                    "kind": item.get("kind", "analysis"),
                    "scenario": item.get("scenario", ""),
                    "content": item.get("content", "").strip(),
                }
                for item in reversed(self._timeline)
            ],
        }
        self.exportPlanRequested.emit(self._todo_id, payload)


class TodoDetailPanel(QQuickView):
    save_requested = pyqtSignal(str, object)
    closed = pyqtSignal()
    complete_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    export_plan_requested = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bridge = _TodoDetailBridge()
        self._panel_width = 396
        self._panel_height = 724
        self._screen_margin = 20
        self._anchor_gap = 16

        self.setFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setColor(QColor(0, 0, 0, 0))
        self.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.rootContext().setContextProperty("todoDetailBridge", self._bridge)
        self.setSource(
            QUrl.fromLocalFile(
                str(Path(__file__).with_name("qml").joinpath("TodoDetailPanel.qml"))
            )
        )
        self._ensure_qml_loaded()

        self._bridge.saveRequested.connect(self.save_requested)
        self._bridge.closeRequested.connect(self._close_panel)
        self._bridge.completeRequested.connect(self.complete_requested)
        self._bridge.deleteRequested.connect(self.delete_requested)
        self._bridge.exportPlanRequested.connect(self.export_plan_requested)

        self.resize(self._panel_width, self._panel_height)
        self.hide()

    def _ensure_qml_loaded(self) -> None:
        if self.status() != QQuickView.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self.errors())
        raise RuntimeError(f"Failed to load TodoDetailPanel.qml:\n{errors}")

    def show_todo(self, todo: TodoItem, anchor_rect=None) -> None:
        self._bridge.set_todo(todo)
        self.resize(self._panel_width, self._panel_height)
        self._reposition(anchor_rect)
        self.show()
        self.raise_()
        self.requestActivate()

    def _reposition(self, anchor_rect=None) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        if anchor_rect is None:
            x = available.right() - self.width() - self._screen_margin
            y = available.top() + self._screen_margin
        else:
            x = anchor_rect.left() - self.width() - self._anchor_gap
            if x < available.left() + self._screen_margin:
                x = anchor_rect.right() + self._anchor_gap
            x = max(
                available.left() + self._screen_margin,
                min(x, available.right() - self.width() - self._screen_margin),
            )
            y = max(
                available.top() + self._screen_margin,
                min(
                    anchor_rect.top(),
                    available.bottom() - self.height() - self._screen_margin,
                ),
            )
        self.setPosition(x, y)

    def _close_panel(self) -> None:
        self.hide()
        self.closed.emit()

"""QML-backed detail panel for a todo item and its timeline."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import unquote, urlparse
import uuid

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QObject, QPoint, Qt, QMimeData, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
    from PyQt6.QtGui import QColor, QCursor, QDesktopServices, QGuiApplication, QImage
    from PyQt6.QtQuick import QQuickView
    from PyQt6.QtWidgets import QApplication, QFileDialog
except Exception:  # pragma: no cover - fallback for test environments without Qt runtime
    class QObject:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass

    class _Signal:
        def __init__(self):
            self._callbacks = []

        def connect(self, callback):
            self._callbacks.append(callback)

        def emit(self, *args, **kwargs):
            for callback in list(self._callbacks):
                callback(*args, **kwargs)

    class _SignalDescriptor:
        def __init__(self):
            self._name = ""

        def __set_name__(self, owner, name):
            self._name = f"__signal_{name}"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            signal = getattr(instance, self._name, None)
            if signal is None:
                signal = _Signal()
                setattr(instance, self._name, signal)
            return signal

    def pyqtSignal(*_args, **_kwargs):  # type: ignore[no-redef]
        return _SignalDescriptor()

    def pyqtSlot(*_args, **_kwargs):  # type: ignore[no-redef]
        def _decorator(func):
            return func
        return _decorator

    def pyqtProperty(*_args, **_kwargs):  # type: ignore[no-redef]
        def _decorator(func):
            return property(func)
        return _decorator

    class Qt:  # type: ignore[no-redef]
        class WindowType:
            FramelessWindowHint = 0
            WindowStaysOnTopHint = 0
            Tool = 0

    class QUrl:  # type: ignore[no-redef]
        def __init__(self, path=""):
            self._path = path

        @staticmethod
        def fromLocalFile(path):
            return QUrl(path)

        def toString(self):
            return self._path

    class QMimeData:  # type: ignore[no-redef]
        def __init__(self):
            self._urls = []

        def setUrls(self, urls):
            self._urls = list(urls)

    class QPoint:  # type: ignore[no-redef]
        def __init__(self, x=0, y=0):
            self._x = x
            self._y = y

        def x(self):
            return self._x

        def y(self):
            return self._y

    class QColor:  # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            pass

    class QImage:  # type: ignore[no-redef]
        def isNull(self):
            return True

        def save(self, *_args, **_kwargs):
            return False

    class QDesktopServices:  # type: ignore[no-redef]
        @staticmethod
        def openUrl(*_args, **_kwargs):
            return False

    class QCursor:  # type: ignore[no-redef]
        @staticmethod
        def pos():
            return QPoint()

    class _Clipboard:  # type: ignore[no-redef]
        def image(self):
            return QImage()

        def setImage(self, *_args, **_kwargs):
            return None

        def setMimeData(self, *_args, **_kwargs):
            return None

    class QGuiApplication:  # type: ignore[no-redef]
        @staticmethod
        def clipboard():
            return _Clipboard()

    class _Context:  # type: ignore[no-redef]
        def setContextProperty(self, *_args, **_kwargs):
            return None

    class QQuickView:  # type: ignore[no-redef]
        class ResizeMode:
            SizeRootObjectToView = 0

        class Status:
            Error = "error"

        def __init__(self, *args, **kwargs):
            self._context = _Context()

        def setFlags(self, *_args, **_kwargs):
            return None

        def setColor(self, *_args, **_kwargs):
            return None

        def setResizeMode(self, *_args, **_kwargs):
            return None

        def rootContext(self):
            return self._context

        def setSource(self, *_args, **_kwargs):
            return None

        def status(self):
            return None

        def errors(self):
            return []

        def resize(self, *_args, **_kwargs):
            return None

        def hide(self):
            return None

        def show(self):
            return None

        def raise_(self):
            return None

        def requestActivate(self):
            return None

        def setPosition(self, *_args, **_kwargs):
            return None

    class QApplication:  # type: ignore[no-redef]
        @staticmethod
        def primaryScreen():
            return None

    class QFileDialog:  # type: ignore[no-redef]
        @staticmethod
        def getOpenFileNames(*_args, **_kwargs):
            return [], ""

        @staticmethod
        def getSaveFileName(*_args, **_kwargs):
            return "", ""

from .models import TicketSummaryFields
from .paths import todo_attachments_dir
from .ticket_field_resolver import (
    TICKET_TYPE_OPTIONS,
    normalize_ticket_type,
    resolve_product_line,
)
from .todo_store import TimelineAttachment, TimelineEvent, TodoItem

_EMPTY_TEXT = "未填写"
_DEFAULT_TODO_TITLE = "\u672a\u5206\u7c7b\u4efb\u52a1"
_MANUAL_SCENARIO = "\u624b\u52a8\u8ddf\u8fdb"
_SYSTEM_SCENARIO = "\u7cfb\u7edf\u8bb0\u5f55"
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


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
        return _MANUAL_SCENARIO
    return str(scenario or _SYSTEM_SCENARIO).strip() or _SYSTEM_SCENARIO


def _coerce_dropped_file_paths(urls: object) -> list[str]:
    if not isinstance(urls, (list, tuple)):
        return []

    resolved_paths: list[str] = []
    seen: set[str] = set()
    for item in urls:
        candidate = ""
        if hasattr(item, "toLocalFile"):
            try:
                candidate = str(item.toLocalFile() or "")
            except Exception:
                candidate = ""
        if not candidate:
            raw = str(item or "").strip()
            if raw.startswith("file://"):
                parsed = urlparse(raw)
                candidate = unquote(parsed.path or "")
                if os.name == "nt" and candidate.startswith("/") and len(candidate) > 2 and candidate[2] == ":":
                    candidate = candidate[1:]
            else:
                candidate = raw

        normalized = os.path.normcase(os.path.normpath(candidate.strip()))
        if not candidate or normalized in seen:
            continue
        seen.add(normalized)
        resolved_paths.append(candidate)
    return resolved_paths


def _attachment_kind(path: str, name: str = "") -> str:
    suffix = Path(name or path).suffix.lower()
    if suffix in _IMAGE_EXTENSIONS:
        return "image"
    if suffix in _VIDEO_EXTENSIONS:
        return "video"
    return "file"


def _clamp_panel_position(
    x: int,
    y: int,
    *,
    panel_width: int,
    panel_height: int,
    available_left: int,
    available_top: int,
    available_right: int,
    available_bottom: int,
    margin: int,
) -> tuple[int, int]:
    max_x = available_right - panel_width - margin
    max_y = available_bottom - panel_height - margin
    clamped_x = max(available_left + margin, min(x, max_x))
    clamped_y = max(available_top + margin, min(y, max_y))
    return clamped_x, clamped_y


def _resolve_available_geometry(screen_or_geometry):
    if screen_or_geometry is None:
        return None
    geometry_getter = getattr(screen_or_geometry, "availableGeometry", None)
    if callable(geometry_getter):
        return geometry_getter()
    return screen_or_geometry


class _TodoDetailBridge(QObject):
    dataChanged = pyqtSignal()
    timelineChanged = pyqtSignal()
    timelineExpandedChanged = pyqtSignal()
    panelDragStarted = pyqtSignal(float, float)
    panelDragMoved = pyqtSignal()
    panelDragFinished = pyqtSignal()

    saveRequested = pyqtSignal(str, object)
    attachmentSelectionRequested = pyqtSignal(str)
    clipboardImagePasteRequested = pyqtSignal(str)
    closeRequested = pyqtSignal()
    completeRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)
    exportPlanRequested = pyqtSignal(str, object)

    def __init__(self, attachment_root: Path | None = None) -> None:
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
        self._timeline: list[dict[str, object]] = []
        self._timeline_expanded = True
        self._attachment_root = Path(attachment_root) if attachment_root is not None else todo_attachments_dir()

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
        self._title = todo.title.strip() or _DEFAULT_TODO_TITLE
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
                "attachments": [self._attachment_to_dict(item) for item in event.attachments],
                "attachmentCount": len(event.attachments),
            }
            for event in reversed(todo.timeline)
        ]
        if not self._current_summary and self._timeline:
            self._current_summary = self._timeline[0]["content"]
            self._title = todo.title.strip() or _DEFAULT_TODO_TITLE
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
        item = self._find_timeline_item(event_id)
        if item is not None:
            item["content"] = str(value)

    @pyqtSlot(str, str)
    def commitTimelineContent(self, event_id: str, value: str) -> None:
        self.updateTimelineContent(event_id, value)
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot(str)
    def requestAttachmentSelection(self, event_id: str) -> None:
        if self._find_timeline_item(event_id) is None:
            return
        self.attachmentSelectionRequested.emit(event_id)

    @pyqtSlot(str)
    def requestClipboardImagePaste(self, event_id: str) -> None:
        if self._find_timeline_item(event_id) is None:
            return
        self.clipboardImagePasteRequested.emit(event_id)

    @pyqtSlot(str, "QVariantList")
    def addTimelineAttachmentsFromUrls(self, event_id: str, urls: object) -> None:
        file_paths = _coerce_dropped_file_paths(urls)
        if not file_paths:
            return
        self.attach_files_to_event(event_id, file_paths)

    @pyqtSlot(str)
    def previewAttachment(self, file_path: str) -> None:
        path = str(file_path or "").strip()
        if not path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @pyqtSlot(str, bool, bool, str)
    def activateAttachment(self, file_path: str, is_image: bool, is_video: bool, file_name: str) -> None:
        path = Path(str(file_path or "").strip()).expanduser()
        if not path.is_file():
            return
        if bool(is_image):
            self._copy_image_attachment(path)
            return
        if bool(is_video):
            self._copy_file_to_clipboard(path)
            return
        self._download_attachment(path, str(file_name or path.name).strip() or path.name)

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
                "scenario": _MANUAL_SCENARIO,
                "content": content,
                "kind": "manual",
                "attachments": [],
                "attachmentCount": 0,
            },
        )
        if not self._timeline_expanded:
            self._timeline_expanded = True
            self.timelineExpandedChanged.emit()
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot(str)
    def deleteTimelineEntry(self, event_id: str) -> None:
        removed = [item for item in self._timeline if item["id"] == event_id]
        remaining = [item for item in self._timeline if item["id"] != event_id]
        if len(remaining) == len(self._timeline):
            return
        for item in removed:
            self._delete_attachments_for_item(item)
        self._timeline = remaining
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot(str, str)
    def removeTimelineAttachment(self, event_id: str, attachment_id: str) -> None:
        item = self._find_timeline_item(event_id)
        if item is None:
            return
        attachments = item.get("attachments", [])
        if not isinstance(attachments, list):
            return
        remaining: list[dict[str, object]] = []
        removed_path = ""
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            if attachment.get("id") == attachment_id:
                removed_path = str(attachment.get("path", ""))
                continue
            remaining.append(attachment)
        if len(remaining) == len(attachments):
            return
        item["attachments"] = remaining
        item["attachmentCount"] = len(remaining)
        if removed_path:
            self._remove_attachment_file(removed_path)
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot()
    def toggleTimeline(self) -> None:
        self._timeline_expanded = not self._timeline_expanded
        self.timelineExpandedChanged.emit()

    @pyqtSlot()
    def saveTodo(self) -> None:
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot(float, float)
    def beginPanelDrag(self, offset_x: float, offset_y: float) -> None:
        self.panelDragStarted.emit(float(offset_x), float(offset_y))

    @pyqtSlot()
    def updatePanelDrag(self) -> None:
        self.panelDragMoved.emit()

    @pyqtSlot()
    def finishPanelDrag(self) -> None:
        self.panelDragFinished.emit()

    def _build_payload(self) -> dict[str, object] | None:
        if self._todo_id is None:
            return None
        normalized_summary = self._current_summary.strip()
        normalized_title = self._title.strip() or _DEFAULT_TODO_TITLE
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
                    attachments=[
                        TimelineAttachment(
                            id=str(attachment.get("id", str(uuid.uuid4()))),
                            name=str(attachment.get("name", "")).strip(),
                            path=str(attachment.get("path", "")).strip(),
                            size_bytes=int(attachment.get("sizeBytes", attachment.get("size_bytes", 0)) or 0),
                        )
                        for attachment in item.get("attachments", [])
                        if isinstance(attachment, dict)
                    ],
                )
                for item in reversed(self._timeline)
            ],
        }

    def attach_files_to_event(self, event_id: str, file_paths: list[str]) -> None:
        item = self._find_timeline_item(event_id)
        if item is None or self._todo_id is None:
            return
        attachments = item.setdefault("attachments", [])
        if not isinstance(attachments, list):
            attachments = []
            item["attachments"] = attachments
        added = False
        for file_path in file_paths:
            attachment = self._copy_attachment(file_path, event_id)
            if attachment is None:
                continue
            attachments.append(attachment)
            added = True
        if not added:
            return
        item["attachmentCount"] = len(attachments)
        self.timelineChanged.emit()
        self._emit_save_request()

    def _emit_save_request(self) -> None:
        payload = self._build_payload()
        if self._todo_id is None or payload is None:
            return
        self.saveRequested.emit(self._todo_id, payload)

    def _find_timeline_item(self, event_id: str) -> dict[str, object] | None:
        for item in self._timeline:
            if item.get("id") == event_id:
                return item
        return None

    @staticmethod
    def _attachment_to_dict(attachment: TimelineAttachment) -> dict[str, object]:
        kind = _attachment_kind(attachment.path, attachment.name)
        return {
            "id": attachment.id,
            "name": attachment.name,
            "path": attachment.path,
            "sizeBytes": attachment.size_bytes,
            "kind": kind,
            "isImage": kind == "image",
            "isVideo": kind == "video",
            "isPreviewable": kind in {"image", "video"},
            "fileUrl": QUrl.fromLocalFile(attachment.path).toString() if attachment.path else "",
        }

    def _copy_attachment(self, file_path: str, event_id: str) -> dict[str, object] | None:
        source = Path(str(file_path or "")).expanduser()
        if not source.is_file() or self._todo_id is None:
            return None
        target_dir = self._attachment_root / self._todo_id / event_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        counter = 1
        while target.exists():
            target = target_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        shutil.copy2(source, target)
        return self._build_attachment_payload(target)

    def attach_clipboard_image_to_event(self, event_id: str, image: QImage) -> bool:
        item = self._find_timeline_item(event_id)
        if item is None or self._todo_id is None or image.isNull():
            return False
        target_dir = self._attachment_root / self._todo_id / event_id
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = target_dir / f"clipboard_{stamp}.png"
        counter = 1
        while target.exists():
            target = target_dir / f"clipboard_{stamp}_{counter}.png"
            counter += 1
        if not image.save(str(target), "PNG"):
            return False
        attachments = item.setdefault("attachments", [])
        if not isinstance(attachments, list):
            attachments = []
            item["attachments"] = attachments
        attachments.append(self._build_attachment_payload(target))
        item["attachmentCount"] = len(attachments)
        self.timelineChanged.emit()
        self._emit_save_request()
        return True

    def _build_attachment_payload(self, target: Path) -> dict[str, object]:
        attachment = TimelineAttachment(
            id=str(uuid.uuid4()),
            name=target.name,
            path=str(target),
            size_bytes=target.stat().st_size if target.exists() else 0,
        )
        return self._attachment_to_dict(attachment)

    def _copy_image_attachment(self, path: Path) -> None:
        image = QImage(str(path))
        if image.isNull():
            return
        QGuiApplication.clipboard().setImage(image)

    def _copy_file_to_clipboard(self, path: Path) -> None:
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(path))])
        QGuiApplication.clipboard().setMimeData(mime_data)

    def _download_attachment(self, source: Path, suggested_name: str) -> None:
        target_path, _ = QFileDialog.getSaveFileName(
            None,
            "保存附件",
            str(source.with_name(suggested_name)),
            "所有文件 (*.*)",
        )
        if not target_path:
            return
        shutil.copy2(source, Path(target_path))

    def _delete_attachments_for_item(self, item: dict[str, object]) -> None:
        attachments = item.get("attachments", [])
        if not isinstance(attachments, list):
            return
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            self._remove_attachment_file(str(attachment.get("path", "")))

    def _remove_attachment_file(self, file_path: str) -> None:
        if not file_path:
            return
        try:
            target = Path(file_path).resolve()
            root = self._attachment_root.resolve()
            if root != target and root not in target.parents:
                return
            if target.exists():
                target.unlink()
            parent = target.parent
            while parent != root and parent.exists():
                if any(parent.iterdir()):
                    break
                parent.rmdir()
                parent = parent.parent
        except OSError:
            return

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
                    "attachments": [
                        {
                            "id": str(attachment.get("id", "")),
                            "name": str(attachment.get("name", "")).strip(),
                            "path": str(attachment.get("path", "")).strip(),
                            "sizeBytes": int(attachment.get("sizeBytes", attachment.get("size_bytes", 0)) or 0),
                            "kind": str(attachment.get("kind", "")),
                            "isImage": bool(attachment.get("isImage", False)),
                            "isVideo": bool(attachment.get("isVideo", False)),
                            "isPreviewable": bool(attachment.get("isPreviewable", False)),
                            "fileUrl": str(attachment.get("fileUrl", "")),
                        }
                        for attachment in item.get("attachments", [])
                        if isinstance(attachment, dict)
                    ],
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
        self._drag_active = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0

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
        self._bridge.attachmentSelectionRequested.connect(self._select_attachments)
        self._bridge.clipboardImagePasteRequested.connect(self._paste_clipboard_image)
        self._bridge.closeRequested.connect(self._close_panel)
        self._bridge.completeRequested.connect(self.complete_requested)
        self._bridge.deleteRequested.connect(self.delete_requested)
        self._bridge.exportPlanRequested.connect(self.export_plan_requested)
        self._bridge.panelDragStarted.connect(self._begin_panel_drag)
        self._bridge.panelDragMoved.connect(self._update_panel_drag)
        self._bridge.panelDragFinished.connect(self._finish_panel_drag)

        self.resize(self._panel_width, self._panel_height)
        self.hide()

    def _ensure_qml_loaded(self) -> None:
        if self.status() != QQuickView.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self.errors())
        raise RuntimeError(f"Failed to load TodoDetailPanel.qml:\n{errors}")

    def _select_attachments(self, event_id: str) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            None,
            "\u9009\u62e9\u9644\u4ef6",
            "",
            "\u6240\u6709\u6587\u4ef6 (*.*)",
        )
        if not files:
            return
        self._bridge.attach_files_to_event(event_id, list(files))

    def _paste_clipboard_image(self, event_id: str) -> None:
        clipboard = QGuiApplication.clipboard()
        image = clipboard.image()
        if image.isNull():
            return
        self._bridge.attach_clipboard_image_to_event(event_id, image)

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
            y = anchor_rect.top()
        self._move_within_screen(x, y, screen)

    def _begin_panel_drag(self, offset_x: float, offset_y: float) -> None:
        self._drag_active = True
        self._drag_offset_x = max(0, int(offset_x))
        self._drag_offset_y = max(0, int(offset_y))

    def _update_panel_drag(self) -> None:
        if not self._drag_active:
            return
        cursor_pos = QCursor.pos()
        x = cursor_pos.x() - self._drag_offset_x
        y = cursor_pos.y() - self._drag_offset_y
        self._move_within_screen(x, y, self._screen_for_point(cursor_pos))

    def _finish_panel_drag(self) -> None:
        self._drag_active = False

    def _screen_for_point(self, point: QPoint):
        screen_at = getattr(QGuiApplication, "screenAt", None)
        if callable(screen_at):
            screen = screen_at(point)
            if screen is not None:
                return screen
        return QApplication.primaryScreen()

    def _move_within_screen(self, x: int, y: int, screen) -> None:
        available = _resolve_available_geometry(screen)
        if available is None:
            return
        target_x, target_y = _clamp_panel_position(
            int(x),
            int(y),
            panel_width=self.width(),
            panel_height=self.height(),
            available_left=available.left(),
            available_top=available.top(),
            available_right=available.right(),
            available_bottom=available.bottom(),
            margin=self._screen_margin,
        )
        self.setPosition(target_x, target_y)

    def _close_panel(self) -> None:
        self.hide()
        self.closed.emit()

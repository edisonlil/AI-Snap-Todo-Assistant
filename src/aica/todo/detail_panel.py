"""QML-backed detail panel for a todo item and its timeline."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import urlsplit
from urllib.parse import unquote, urlparse
import uuid

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
_MIN_ASSIST_CASE_MATCH_SCORE = 50

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QMimeData, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
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
                if callable(callback):
                    callback(*args, **kwargs)
                elif hasattr(callback, "emit"):
                    callback.emit(*args, **kwargs)

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
            Window = 0

        class Edge:
            LeftEdge = 0x01
            RightEdge = 0x02
            TopEdge = 0x04
            BottomEdge = 0x08

    class QEvent:  # type: ignore[no-redef]
        class Type:
            WindowDeactivate = 0

    class QTimer:  # type: ignore[no-redef]
        @staticmethod
        def singleShot(_msec, callback):
            callback()

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

    class QSize:  # type: ignore[no-redef]
        def __init__(self, width=0, height=0):
            self._width = width
            self._height = height

        def width(self):
            return self._width

        def height(self):
            return self._height

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

        def setText(self, *_args, **_kwargs):
            return None

    class QGuiApplication:  # type: ignore[no-redef]
        @staticmethod
        def clipboard():
            return _Clipboard()

        @staticmethod
        def focusWindow():
            return None

        @staticmethod
        def screenAt(_point):
            return None

        @staticmethod
        def screens():
            return []

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
            self._width = 0
            self._height = 0
            self._minimum_size = QSize()
            self._visible = False
            self._x = 0
            self._y = 0

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
            if len(_args) >= 2:
                min_width = self._minimum_size.width() if self._minimum_size is not None else 0
                min_height = self._minimum_size.height() if self._minimum_size is not None else 0
                self._width = max(min_width, int(_args[0]))
                self._height = max(min_height, int(_args[1]))
            return None

        def setMinimumSize(self, size):
            self._minimum_size = size
            return None

        def width(self):
            return self._width

        def height(self):
            return self._height

        def hide(self):
            self._visible = False
            return None

        def show(self):
            self._visible = True
            return None

        def raise_(self):
            return None

        def requestActivate(self):
            return None

        def startSystemResize(self, *_args, **_kwargs):
            return True

        def setPosition(self, *_args, **_kwargs):
            if len(_args) >= 2:
                self._x = int(_args[0])
                self._y = int(_args[1])
            return None

        def isVisible(self):
            return self._visible

        def x(self):
            return self._x

        def y(self):
            return self._y

        def event(self, *_args, **_kwargs):
            return False

    class QApplication:  # type: ignore[no-redef]
        @staticmethod
        def primaryScreen():
            return None

        @staticmethod
        def screens():
            return []

        @staticmethod
        def clipboard():
            return _Clipboard()

    class QFileDialog:  # type: ignore[no-redef]
        @staticmethod
        def getOpenFileNames(*_args, **_kwargs):
            return [], ""

        @staticmethod
        def getSaveFileName(*_args, **_kwargs):
            return "", ""

from ..app_notifications import AppNotificationBridge
from .assist_analysis import build_assist_analysis_cache_key
from .conclusion_timeline import build_conclusion_timeline_content
from ..environment_access import EnvironmentAccessService
from ..log_analysis.commands import format_log_analysis_focus, is_log_analysis_command, parse_log_analysis_command
from ..models import TicketSummaryFields
from ..paths import qml_dir, todo_attachments_dir
from ..runtime import RUNTIME_CAPABILITIES
from ..storage.sqlite.environment_repositories import SQLiteProjectEnvironmentRepository
from ..ticket_enrichment import ROOT_CAUSE_OPTIONS
from ..ticket_field_resolver import (
    TICKET_TYPE_OPTIONS,
    normalize_ticket_type,
    resolve_product_line,
)
from ..text_sanitize import sanitize_text, strip_invalid_surrogates
from .store import TimelineAttachment, TimelineEvent, TodoConclusion, TodoItem, TodoProjectLink

_EMPTY_TEXT = "未填写"
_DEFAULT_TODO_TITLE = "\u672a\u5206\u7c7b\u4efb\u52a1"
_MANUAL_SCENARIO = "\u95ee\u9898\u53cd\u9988"
_SYSTEM_SCENARIO = "\u7cfb\u7edf\u8bb0\u5f55"
_CONCLUSION_SCENARIO = "\u95ee\u9898\u7ed3\u8bba"
_LOG_ANALYSIS_TASK_SCENARIO = "\u65e5\u5fd7\u5206\u6790\u4efb\u52a1"
_LOG_ANALYSIS_RESULT_SCENARIO = "\u65e5\u5fd7\u5206\u6790\u7ed3\u679c"
_CONCLUSION_ATTACHMENT_TARGET = "__conclusion__"
_DRAFT_TIMELINE_ATTACHMENT_TARGET = "__draft_timeline__"
_ENTRY_TYPE_FOLLOW_UP = "follow_up"
_ENTRY_TYPE_CONCLUSION = "conclusion"
_ENTRY_TYPE_LOG_ANALYSIS = "log_analysis"
_SAVE_MODE_AUTOSAVE = "autosave"
_SAVE_MODE_MANUAL = "manual"
_TIMELINE_EVENT_TYPE_DEFAULT = "default"
_TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND = "log_analysis_command"
_TIMELINE_EVENT_TYPE_LOG_ANALYSIS_RESULT = "log_analysis_result"
_DETAIL_ACTION_SAVE_FORM = "save_detail_form"
_DETAIL_ACTION_SAVE_CONCLUSION = "save_conclusion"
_DETAIL_ACTION_APPEND_TIMELINE_ENTRY = "append_timeline_entry"
_RUNNING_STATUS = "running"
_SUCCESS_STATUS = "success"
_FAILED_STATUS = "failed"
_LOG_ANALYSIS_STEP_LABELS = [
    "\u6b63\u5728\u6536\u96c6\u9644\u4ef6...",
    "\u6b63\u5728\u6784\u5efa\u6392\u67e5\u4e0a\u4e0b\u6587...",
    "\u6b63\u5728\u68c0\u7d22\u65e5\u5fd7...",
    "\u6b63\u5728\u751f\u6210\u7ed3\u679c...",
]
_ENTRY_COMMAND_PREFIXES = {
    "/问题反馈": _ENTRY_TYPE_FOLLOW_UP,
    "/问题跟进": _ENTRY_TYPE_FOLLOW_UP,
    "/问题结论": _ENTRY_TYPE_CONCLUSION,
}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def _format_ts(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%m-%d %H:%M")
    except ValueError:
        return value


def _clean_text(value: str, fallback: str = _EMPTY_TEXT) -> str:
    text = sanitize_text(value)
    return text or fallback


def _coerce_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_timeline_scenario(kind: str, scenario: str) -> str:
    if kind == "conclusion":
        return _CONCLUSION_SCENARIO
    if kind == "manual":
        return _MANUAL_SCENARIO
    return str(scenario or _SYSTEM_SCENARIO).strip() or _SYSTEM_SCENARIO


def _normalize_entry_submission(value: str, entry_type: str) -> tuple[str, str]:
    content = sanitize_text(value).strip()
    normalized_type = (
        entry_type
        if entry_type in {_ENTRY_TYPE_FOLLOW_UP, _ENTRY_TYPE_CONCLUSION, _ENTRY_TYPE_LOG_ANALYSIS}
        else _ENTRY_TYPE_FOLLOW_UP
    )
    if not content:
        return "", normalized_type

    for prefix, prefix_type in _ENTRY_COMMAND_PREFIXES.items():
        if content == prefix:
            return "", prefix_type
        if content.startswith(f"{prefix} ") or content.startswith(f"{prefix}\n"):
            return content[len(prefix):].strip(), prefix_type

    if content == "/":
        return "", normalized_type
    return content, normalized_type


def _normalize_timeline_draft_entry_type(value: object) -> str:
    normalized = str(value or "").strip()
    if normalized in {_ENTRY_TYPE_CONCLUSION, _ENTRY_TYPE_LOG_ANALYSIS}:
        return normalized
    return _ENTRY_TYPE_FOLLOW_UP


def _normalize_display_timeline(events: list[TimelineEvent]) -> list[TimelineEvent]:
    latest_conclusion: TimelineEvent | None = None
    remaining: list[TimelineEvent] = []
    for event in events:
        if str(event.kind or "").strip() == "conclusion":
            latest_conclusion = event
            continue
        remaining.append(event)
    if latest_conclusion is None:
        return list(reversed(remaining))
    return [latest_conclusion] + list(reversed(remaining))


def _timeline_event_type(event: TimelineEvent) -> str:
    explicit = str(getattr(event, "event_type", "") or "").strip()
    if explicit:
        return explicit
    kind = str(event.kind or "").strip()
    if kind == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND:
        return _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND
    if kind == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_RESULT:
        return _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_RESULT
    if str(event.scenario or "").strip() == _LOG_ANALYSIS_RESULT_SCENARIO:
        return _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_RESULT
    return _TIMELINE_EVENT_TYPE_DEFAULT


def _normalize_card_status(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized in {"queued", _RUNNING_STATUS}:
        return _RUNNING_STATUS
    if normalized in {"completed", _SUCCESS_STATUS}:
        return _SUCCESS_STATUS
    if normalized == _FAILED_STATUS:
        return _FAILED_STATUS
    return ""


def _timeline_card_label(event_type: str, scenario: str) -> str:
    if event_type == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND:
        return _LOG_ANALYSIS_TASK_SCENARIO
    if event_type == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_RESULT:
        return _LOG_ANALYSIS_RESULT_SCENARIO
    return str(scenario or _SYSTEM_SCENARIO).strip() or _SYSTEM_SCENARIO


def _clone_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _clone_list(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else []


def _clone_attachment_payloads(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _project_status_label(status: str) -> str:
    mapping = {
        "matched": "已关联项目",
        "unmatched": "未匹配项目",
        "conflict": "匹配冲突",
        "expired": "命中过保项目",
        "manual": "手动指定项目",
    }
    return mapping.get(str(status or "").strip(), "未匹配项目")


def _project_status_detail(todo: TodoItem) -> str:
    link = todo.project_link
    status = str(link.match_status or "").strip()
    if status == "matched":
        project_name = str(link.project_snapshot.get("project_name") or "").strip()
        task_order_no = str(link.project_snapshot.get("task_order_no") or "").strip()
        if project_name and task_order_no:
            return f"{project_name} {task_order_no}"
        return project_name or task_order_no or "已根据群聊名称命中项目主数据。"
    if status == "conflict":
        reason = str(link.match_reason or "").strip()
        if reason.startswith("multiple_active_projects:"):
            return "命中了多个有效项目，请在项目管理页收敛别名。"
        return reason or "当前群聊名称命中了多个有效项目。"
    if status == "expired":
        project_name = str(link.project_snapshot.get("project_name") or "").strip()
        return f"{project_name} 已过保。" if project_name else "当前群聊名称只命中过保项目。"
    if status == "manual":
        return "当前待办使用了手动项目关联结果。"
    reason = str(link.match_reason or "").strip()
    if reason == "missing_group_name":
        return "当前待办缺少群聊名称，无法自动匹配项目。"
    return "当前群聊名称尚未命中任何项目别名。"


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


def _resolve_neighbor_panel_x(
    anchor_left: int,
    anchor_width: int,
    *,
    panel_width: int,
    available_left: int,
    available_right: int,
    margin: int,
    gap: int,
) -> int:
    min_x = available_left + margin
    max_x = available_right - panel_width - margin
    right_x = anchor_left + anchor_width + gap
    left_x = anchor_left - gap - panel_width

    right_space = max(0, (available_right - margin) - (anchor_left + anchor_width + gap))
    left_space = max(0, (anchor_left - gap) - (available_left + margin))
    right_fits = right_x <= max_x
    left_fits = left_x >= min_x

    if right_fits and not left_fits:
        return right_x
    if left_fits and not right_fits:
        return left_x
    if right_space >= left_space:
        return right_x
    return left_x


def _screen_for_point(point):
    screen_at = getattr(QGuiApplication, "screenAt", None)
    if callable(screen_at):
        screen = screen_at(point)
        if screen is not None:
            return screen
    return QApplication.primaryScreen()


def _virtual_available_geometry():
    screens = QApplication.screens()
    if not screens:
        primary = QApplication.primaryScreen()
        return primary.availableGeometry() if primary is not None else None

    bounds = _resolve_available_geometry(screens[0])
    if bounds is None:
        return None
    for screen in screens[1:]:
        geometry = _resolve_available_geometry(screen)
        if geometry is None:
            continue
        united = getattr(bounds, "united", None)
        if callable(united):
            bounds = united(geometry)
        else:
            return geometry
    return bounds


def _resolve_available_geometry(screen_or_geometry):
    if screen_or_geometry is None:
        return None
    geometry_getter = getattr(screen_or_geometry, "availableGeometry", None)
    if callable(geometry_getter):
        return geometry_getter()
    return screen_or_geometry


def _is_openable_target(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    parsed = urlsplit(text)
    return bool(parsed.scheme and parsed.netloc)


class _TodoDetailBridge(QObject):
    dataChanged = pyqtSignal()
    timelineChanged = pyqtSignal()
    timelineExpandedChanged = pyqtSignal()
    timelineDraftChanged = pyqtSignal()
    environmentAccessMessageChanged = pyqtSignal()
    assistTroubleshootingChanged = pyqtSignal()
    panelDragStarted = pyqtSignal(float, float)
    panelDragMoved = pyqtSignal()
    panelDragFinished = pyqtSignal()

    saveRequested = pyqtSignal(str, object)
    logAnalysisRequested = pyqtSignal(str, object)
    attachmentSelectionRequested = pyqtSignal(str)
    clipboardImagePasteRequested = pyqtSignal(str)
    draftAttachmentSelectionRequested = pyqtSignal()
    draftClipboardImagePasteRequested = pyqtSignal()
    manualSyncRequested = pyqtSignal(str)
    closeRequested = pyqtSignal()
    completeRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)
    exportPlanRequested = pyqtSignal(str, object)
    stageSummaryRequested = pyqtSignal(str, object)
    stageSummaryRewriteRequested = pyqtSignal(str, object)
    assistAnalysisRequested = pyqtSignal(str, object)

    def __init__(
        self,
        attachment_root: Path | None = None,
        *,
        environment_access_service: EnvironmentAccessService | None = None,
        notification_bridge: AppNotificationBridge | None = None,
    ) -> None:
        super().__init__()
        self._notification_bridge = notification_bridge or AppNotificationBridge()
        self._todo_id: str | None = None
        self._title = ""
        self._group_name = _EMPTY_TEXT
        self._environment = _EMPTY_TEXT
        self._product_line = _EMPTY_TEXT
        self._ticket_type = _EMPTY_TEXT
        self._feature_point = ""
        self._feature_point_source = ""
        self._root_cause_desc = ""
        self._root_cause_desc_source = ""
        self._root_cause = ""
        self._root_cause_source = ""
        self._current_summary = ""
        self._conclusion_content = ""
        self._conclusion_updated_at = ""
        self._conclusion_attachments: list[dict[str, object]] = []
        self._conclusion_dirty = False
        self._draft_timeline_attachments: list[dict[str, object]] = []
        self._timeline_draft_text = ""
        self._timeline_draft_entry_type = _ENTRY_TYPE_FOLLOW_UP
        self._timeline_draft_entry_type_selected = False
        self._timeline_draft_cache: dict[str, dict[str, object]] = {}
        self._overview = ""
        self._created_at = ""
        self._updated_at = ""
        self._timeline: list[dict[str, object]] = []
        self._display_timeline: list[dict[str, object]] = []
        self._timeline_expanded = True
        self._todo_session_revision = 0
        self._attachment_root = Path(attachment_root) if attachment_root is not None else todo_attachments_dir()
        self._project_match_status = "未匹配项目"
        self._project_match_detail = "当前群聊名称尚未命中任何项目别名。"
        self._project_name = ""
        self._project_task_order_no = ""
        self._project_manager = ""
        self._ticket_version = ""
        self._project_link = TodoProjectLink()
        self._sync_integration_id = ""
        self._sync_status = "未同步"
        self._sync_status_detail = "当前待办还没有外部绑定。"
        self._external_id = ""
        self._sync_event_label = ""
        self._sync_updated_at = ""
        self._sync_records: list[dict[str, object]] = []
        self._environment_access_service = environment_access_service or EnvironmentAccessService(
            SQLiteProjectEnvironmentRepository()
        )
        self._environment_access_groups: list[dict[str, object]] = []
        self._environment_access_summary_text = "环境访问 · 无可用环境"
        self._environment_access_popover_open = False
        self._environment_access_message = ""
        self._stage_summary_visible = False
        self._stage_summary_busy = False
        self._stage_summary_text = ""
        self._stage_summary_error = ""
        self._stage_summary_notice = ""
        self._stage_summary_requested_once = False
        self._stage_summary_pending_request_id = ""
        self._assist_troubleshooting_visible = False
        self._assist_analysis_busy = False
        self._assist_analysis_error = ""
        self._assist_analysis_requested_once = False
        self._assist_analysis_pending_request_id = ""
        self._assist_analysis_pending_cache_key = ""
        self._assist_analysis_cache: dict[str, dict[str, object]] = {}
        self._assist_analysis_result: dict[str, object] = self._default_assist_analysis_result()

    @property
    def notificationBridge(self) -> AppNotificationBridge:
        return self._notification_bridge

    def _notify(self, level: str, message: str, duration_ms: int | None = None) -> None:
        self._notification_bridge.notify(
            level,
            message,
            duration_ms if duration_ms is not None else 0,
            "todo_detail",
        )

    @pyqtProperty(str, constant=True)
    def uiFont(self) -> str:
        return RUNTIME_CAPABILITIES.ui_font

    @pyqtProperty(str, notify=dataChanged)
    def todoId(self) -> str:
        return str(self._todo_id or "")

    @pyqtProperty(int, notify=dataChanged)
    def todoSessionRevision(self) -> int:
        return self._todo_session_revision

    @pyqtProperty(str, notify=dataChanged)
    def environmentAccessSummaryText(self) -> str:
        return self._environment_access_summary_text

    @pyqtProperty(bool, notify=dataChanged)
    def environmentAccessPopoverOpen(self) -> bool:
        return self._environment_access_popover_open

    @pyqtProperty(bool, notify=dataChanged)
    def hasEnvironmentAccess(self) -> bool:
        return any(bool(group.get("entries")) for group in self._environment_access_groups)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def environmentAccessGroups(self):  # noqa: ANN201
        return self._environment_access_groups

    @pyqtProperty(str, notify=environmentAccessMessageChanged)
    def environmentAccessMessage(self) -> str:
        return self._environment_access_message

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
    def featurePoint(self) -> str:
        return self._feature_point

    @pyqtProperty(str, notify=dataChanged)
    def featurePointSource(self) -> str:
        return self._feature_point_source

    @pyqtProperty(str, notify=dataChanged)
    def rootCauseDesc(self) -> str:
        return self._root_cause_desc

    @pyqtProperty(str, notify=dataChanged)
    def rootCauseDescSource(self) -> str:
        return self._root_cause_desc_source

    @pyqtProperty(str, notify=dataChanged)
    def rootCause(self) -> str:
        return self._root_cause

    @pyqtProperty(str, notify=dataChanged)
    def rootCauseSource(self) -> str:
        return self._root_cause_source

    @pyqtProperty("QVariantList", constant=True)
    def rootCauseOptions(self):  # noqa: ANN201
        return list(ROOT_CAUSE_OPTIONS)

    @pyqtProperty(str, notify=dataChanged)
    def currentSummary(self) -> str:
        return self._current_summary

    @pyqtProperty(str, notify=dataChanged)
    def conclusionContent(self) -> str:
        return self._conclusion_content

    @pyqtProperty(str, notify=dataChanged)
    def conclusionUpdatedAtLabel(self) -> str:
        return _format_ts(self._conclusion_updated_at) if self._conclusion_updated_at else ""

    @pyqtProperty(int, notify=dataChanged)
    def conclusionAttachmentCount(self) -> int:
        return len(self._conclusion_attachments)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def conclusionAttachments(self):  # noqa: ANN201
        return self._conclusion_attachments

    @pyqtProperty(str, notify=timelineDraftChanged)
    def timelineDraftText(self) -> str:
        return self._timeline_draft_text

    @pyqtProperty(str, notify=timelineDraftChanged)
    def timelineDraftEntryType(self) -> str:
        return self._timeline_draft_entry_type

    @pyqtProperty(bool, notify=timelineDraftChanged)
    def timelineDraftEntryTypeSelected(self) -> bool:
        return self._timeline_draft_entry_type_selected

    @pyqtProperty(int, notify=timelineDraftChanged)
    def draftTimelineAttachmentCount(self) -> int:
        return len(self._draft_timeline_attachments)

    @pyqtProperty("QVariantList", notify=timelineDraftChanged)
    def draftTimelineAttachments(self):  # noqa: ANN201
        return self._draft_timeline_attachments

    @pyqtProperty(str, notify=dataChanged)
    def createdAtLabel(self) -> str:
        return self._created_at

    @pyqtProperty(str, notify=dataChanged)
    def updatedAtLabel(self) -> str:
        return self._updated_at

    @pyqtProperty(int, notify=timelineChanged)
    def timelineCount(self) -> int:
        return len(self._display_timeline)

    @pyqtProperty("QVariantList", notify=timelineChanged)
    def timeline(self):  # noqa: ANN201
        return self._display_timeline

    @pyqtProperty(bool, notify=timelineExpandedChanged)
    def timelineExpanded(self) -> bool:
        return self._timeline_expanded

    @pyqtProperty(bool, notify=dataChanged)
    def stageSummaryVisible(self) -> bool:
        return self._stage_summary_visible

    @pyqtProperty(bool, notify=dataChanged)
    def stageSummaryBusy(self) -> bool:
        return self._stage_summary_busy

    @pyqtProperty(str, notify=dataChanged)
    def stageSummaryText(self) -> str:
        return self._stage_summary_text

    @pyqtProperty(str, notify=dataChanged)
    def stageSummaryError(self) -> str:
        return self._stage_summary_error

    @pyqtProperty(bool, notify=dataChanged)
    def hasStageSummary(self) -> bool:
        return bool(self._stage_summary_text.strip())

    @pyqtProperty(str, notify=dataChanged)
    def stageSummaryNotice(self) -> str:
        return self._stage_summary_notice

    @pyqtProperty(bool, notify=assistTroubleshootingChanged)
    def assistTroubleshootingVisible(self) -> bool:
        return self._assist_troubleshooting_visible

    @pyqtProperty(bool, notify=dataChanged)
    def assistAnalysisBusy(self) -> bool:
        return self._assist_analysis_busy

    @pyqtProperty(str, notify=dataChanged)
    def assistAnalysisError(self) -> str:
        return self._assist_analysis_error

    @pyqtProperty(str, notify=dataChanged)
    def assistAnalysisSummary(self) -> str:
        return str(self._assist_analysis_result.get("summary", "") or "")

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def assistInformationStatus(self):  # noqa: ANN201
        value = self._assist_analysis_result.get("informationStatus")
        return dict(value or {}) if isinstance(value, dict) else {}

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def assistMissingSupplement(self):  # noqa: ANN201
        value = self._assist_analysis_result.get("missingSupplement")
        return dict(value or {}) if isinstance(value, dict) else {}

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def assistUpgradeSuggestion(self):  # noqa: ANN201
        value = self._assist_analysis_result.get("upgradeSuggestion")
        return dict(value or {}) if isinstance(value, dict) else {}

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def assistCaseResults(self):  # noqa: ANN201
        value = self._assist_analysis_result.get("caseResults")
        return dict(value or {}) if isinstance(value, dict) else self._empty_assist_case_results(status="loading")

    @pyqtProperty(str, notify=dataChanged)
    def projectMatchStatus(self) -> str:
        return self._project_match_status

    @pyqtProperty(str, notify=dataChanged)
    def projectMatchDetail(self) -> str:
        return self._project_match_detail

    @pyqtProperty(str, notify=dataChanged)
    def projectName(self) -> str:
        return self._project_name

    @pyqtProperty(str, notify=dataChanged)
    def projectTaskOrderNo(self) -> str:
        return self._project_task_order_no

    @pyqtProperty(str, notify=dataChanged)
    def projectManager(self) -> str:
        return self._project_manager

    @pyqtProperty(str, notify=dataChanged)
    def syncIntegrationId(self) -> str:
        return self._sync_integration_id

    @pyqtProperty(str, notify=dataChanged)
    def syncStatus(self) -> str:
        return self._sync_status

    @pyqtProperty(str, notify=dataChanged)
    def syncStatusDetail(self) -> str:
        return self._sync_status_detail

    @pyqtProperty(str, notify=dataChanged)
    def externalId(self) -> str:
        return self._external_id

    @pyqtProperty(bool, notify=dataChanged)
    def hasExternalId(self) -> bool:
        return bool(self._external_id)

    @pyqtProperty(str, notify=dataChanged)
    def syncEventLabel(self) -> str:
        return self._sync_event_label

    @pyqtProperty(str, notify=dataChanged)
    def syncUpdatedAtLabel(self) -> str:
        return self._sync_updated_at

    @pyqtProperty(int, notify=dataChanged)
    def syncRecordCount(self) -> int:
        return len(self._sync_records)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def syncRecords(self):  # noqa: ANN201
        return self._sync_records

    @pyqtSlot()
    def toggleEnvironmentAccessPopover(self) -> None:
        self._environment_access_popover_open = not self._environment_access_popover_open
        self.dataChanged.emit()

    @pyqtSlot()
    def closeEnvironmentAccessPopover(self) -> None:
        if not self._environment_access_popover_open:
            return
        self._environment_access_popover_open = False
        self.dataChanged.emit()

    @pyqtSlot(str)
    def toggleEnvironmentGroup(self, group_id: str) -> None:
        normalized_group_id = str(group_id or "").strip()
        if not normalized_group_id:
            return
        changed = False
        next_groups: list[dict[str, object]] = []
        for group in self._environment_access_groups:
            next_group = dict(group)
            is_target = str(group.get("id") or "") == normalized_group_id
            current = bool(group.get("expanded", False))
            next_value = not current if is_target else False
            if current != next_value:
                changed = True
            next_group["expanded"] = next_value
            next_group["entries"] = [dict(entry) for entry in group.get("entries", []) if isinstance(entry, dict)]
            next_groups.append(next_group)
        if changed:
            self._environment_access_groups = next_groups
            self.dataChanged.emit()

    @staticmethod
    def _clone_environment_groups(
        groups: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        cloned_groups: list[dict[str, object]] = []
        for group in groups:
            next_group = dict(group)
            next_group["entries"] = [
                dict(entry)
                for entry in group.get("entries", [])
                if isinstance(entry, dict)
            ]
            cloned_groups.append(next_group)
        return cloned_groups

    def _replace_environment_groups(self, groups: list[dict[str, object]]) -> None:
        self._environment_access_groups = self._clone_environment_groups(groups)
        self.dataChanged.emit()

    def _set_group_expanded_state(self, target_entry_id: str = "") -> None:
        normalized_entry_id = str(target_entry_id or "").strip()
        next_groups = self._clone_environment_groups(self._environment_access_groups)
        for group in next_groups:
            entries = group.get("entries", [])
            has_target = any(
                str(entry.get("id") or "") == normalized_entry_id
                for entry in entries
                if isinstance(entry, dict)
            )
            group["expanded"] = has_target if normalized_entry_id else bool(group.get("expanded", False))
        self._environment_access_groups = next_groups

    @staticmethod
    def _iterate_environment_entries(groups: list[dict[str, object]]):
        for group in groups:
            entries = group.get("entries", [])
            if not isinstance(entries, list):
                continue
            yield group, entries

    @staticmethod
    def _copy_entry_shape(group: dict[str, object], entry: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        return dict(group), dict(entry)

    def _find_environment_entry(self, entry_id: str) -> dict[str, object] | None:
        normalized_entry_id = str(entry_id or "").strip()
        if not normalized_entry_id:
            return None
        for _group, entries in self._iterate_environment_entries(self._environment_access_groups):
            for entry in entries:
                if str(entry.get("id") or "") == normalized_entry_id:
                    return entry
        return None

    def _update_environment_entries(self, updater) -> bool:
        changed = False
        next_groups = self._clone_environment_groups(self._environment_access_groups)
        for group, entries in self._iterate_environment_entries(next_groups):
            for index, entry in enumerate(entries):
                updated_entry, entry_changed = updater(dict(entry))
                if entry_changed:
                    entries[index] = updated_entry
                    changed = True
        if changed:
            self._environment_access_groups = next_groups
            self.dataChanged.emit()
        return changed

    @pyqtSlot(str)
    def startEnvironmentLogin(self, entry_id: str) -> None:
        result = self._environment_access_service.prepare_login(str(entry_id or "").strip())
        if result is None:
            self._set_environment_access_message("未找到环境访问项", level="warning")
            return
        opened = self._open_environment_target(result.entry.url_or_host)
        copied_username = False
        if result.username:
            QApplication.clipboard().setText(result.username)
            copied_username = True
        helper_available = bool(
            str(result.username or "").strip()
            or result.has_password
            or result.entry.requires_otp
        )
        self._activate_environment_entry(
            result.entry.id,
            login_activated=helper_available,
            password_available=result.has_password,
            otp_available=result.entry.requires_otp,
            otp_code=result.otp_code,
            otp_remaining_seconds=result.otp_remaining_seconds,
        )
        access_name = result.entry.access_name or "访问入口"
        if opened and copied_username:
            message = f"已打开 {access_name}，并复制账号"
        elif opened:
            message = f"已打开 {access_name}"
        elif copied_username:
            message = f"已复制 {access_name} 账号"
        else:
            message = f"已准备 {access_name} 登录动作"
        self._set_environment_access_message(message, level="success")

    @pyqtSlot(str)
    def copyEnvironmentUsername(self, entry_id: str) -> None:
        entry = self._find_environment_entry(entry_id)
        username = str((entry or {}).get("username") or "").strip()
        if not username:
            self._set_environment_access_message("当前访问方式未配置账号", level="warning")
            return
        QApplication.clipboard().setText(username)
        self._set_environment_access_message("已复制账号", level="success")

    @pyqtSlot(str)
    def copyEnvironmentAddress(self, entry_id: str) -> None:
        entry = self._find_environment_entry(entry_id)
        address = str((entry or {}).get("urlOrHost") or "").strip()
        if not address:
            self._set_environment_access_message("当前访问方式未配置地址", level="warning")
            return
        QApplication.clipboard().setText(address)
        self._set_environment_access_message("已复制地址", level="success")

    @pyqtSlot(str)
    def copyEnvironmentAddressAndShowDetails(self, entry_id: str) -> None:
        normalized_entry_id = str(entry_id or "").strip()
        result = self._environment_access_service.prepare_login(normalized_entry_id)
        if result is None:
            self._set_environment_access_message("未找到环境访问项", level="warning")
            return
        address = str(result.entry.url_or_host or "").strip()
        if not address:
            self._set_environment_access_message("当前访问方式未配置地址", level="warning")
            return
        QApplication.clipboard().setText(address)
        self._activate_environment_entry(
            result.entry.id,
            login_activated=True,
            password_available=result.has_password,
            otp_available=result.entry.requires_otp,
            otp_code=result.otp_code,
            otp_remaining_seconds=result.otp_remaining_seconds,
            detail_mode="link",
        )
        self._set_environment_access_message("已复制链接", level="success")

    @pyqtSlot(str)
    def copyEnvironmentPassword(self, entry_id: str) -> None:
        password = self._environment_access_service.get_password(str(entry_id or "").strip())
        if not password:
            self._set_environment_access_message("当前访问方式未配置密码", level="warning")
            return
        QApplication.clipboard().setText(password)
        self._set_environment_access_message("已复制密码", level="success")

    @pyqtSlot(str)
    def copyEnvironmentLoginInfo(self, entry_id: str) -> None:
        normalized_entry_id = str(entry_id or "").strip()
        entry = self._find_environment_entry(normalized_entry_id)
        if entry is None:
            self._set_environment_access_message("未找到环境访问项", level="warning")
            return
        address = str(entry.get("urlOrHost") or "").strip()
        username = str(entry.get("username") or "").strip()
        password = self._environment_access_service.get_password(normalized_entry_id)
        lines = [
            f"地址：{address}" if address else "",
            f"账号：{username}" if username else "",
            f"密码：{password}" if password else "",
        ]
        text = "\n".join(line for line in lines if line)
        if not text:
            self._set_environment_access_message("当前访问方式暂无可复制信息", level="warning")
            return
        QApplication.clipboard().setText(text)
        self._set_environment_access_message("已复制地址/账号/密码", level="success")

    @pyqtSlot(str)
    def copyEnvironmentOtp(self, entry_id: str) -> None:
        code, remaining = self._environment_access_service.get_otp_code(str(entry_id or "").strip())
        if not code:
            self._set_environment_access_message("当前访问方式暂无可用验证码", level="warning")
            return
        QApplication.clipboard().setText(code)
        self._update_entry_otp_state(str(entry_id or "").strip(), code, remaining)
        self._set_environment_access_message("已复制验证码", level="success")

    @pyqtSlot()
    def refreshEnvironmentOtpState(self) -> None:
        def _updater(entry: dict[str, object]) -> tuple[dict[str, object], bool]:
            if not bool(entry.get("loginActivated", False)):
                return entry, False
            if not bool(entry.get("canCopyOtp", False)):
                return entry, False
            next_code, next_remaining = self._environment_access_service.get_otp_code(
                str(entry.get("id") or "")
            )
            if (
                int(entry.get("otpRemainingSeconds", 0) or 0) == next_remaining
                and str(entry.get("otpCode") or "") == next_code
            ):
                return entry, False
            entry["otpCode"] = next_code
            entry["otpRemainingSeconds"] = next_remaining
            return entry, True

        self._update_environment_entries(_updater)

    def _current_timeline_draft_state(self) -> dict[str, object]:
        return {
            "text": self._timeline_draft_text,
            "entry_type": self._timeline_draft_entry_type,
            "entry_type_selected": self._timeline_draft_entry_type_selected,
            "draft_attachments": _clone_attachment_payloads(self._draft_timeline_attachments),
        }

    def _apply_timeline_draft_state(self, draft_state: dict[str, object] | None) -> None:
        state = draft_state if isinstance(draft_state, dict) else {}
        self._timeline_draft_text = str(state.get("text", "") or "")
        self._timeline_draft_entry_type = _normalize_timeline_draft_entry_type(state.get("entry_type"))
        self._timeline_draft_entry_type_selected = bool(state.get("entry_type_selected", False))
        self._draft_timeline_attachments = _clone_attachment_payloads(state.get("draft_attachments"))

    def _store_current_timeline_draft(self) -> None:
        todo_id = str(self._todo_id or "").strip()
        if not todo_id:
            return
        state = self._current_timeline_draft_state()
        has_draft_content = bool(
            str(state.get("text", "") or "").strip()
            or bool(state.get("entry_type_selected", False))
            or bool(state.get("draft_attachments"))
        )
        if has_draft_content:
            self._timeline_draft_cache[todo_id] = state
            return
        self._timeline_draft_cache.pop(todo_id, None)

    def _emit_timeline_draft_changed(self) -> None:
        self.timelineDraftChanged.emit()

    def _reset_current_timeline_draft(self, *, remove_files: bool) -> None:
        attachments = list(self._draft_timeline_attachments)
        self._draft_timeline_attachments = []
        if remove_files:
            for attachment in attachments:
                if not isinstance(attachment, dict):
                    continue
                self._remove_attachment_file(str(attachment.get("path", "")))
        self._timeline_draft_text = ""
        self._timeline_draft_entry_type = _ENTRY_TYPE_FOLLOW_UP
        self._timeline_draft_entry_type_selected = False
        todo_id = str(self._todo_id or "").strip()
        if todo_id:
            self._timeline_draft_cache.pop(todo_id, None)
        self._emit_timeline_draft_changed()

    @staticmethod
    def _is_cleared_conclusion_content(content: object) -> bool:
        return str(content or "").strip() == "结论已清空"

    def _hydrate_conclusion_from_timeline(self, timeline_items: list[dict[str, object]]) -> None:
        for item in timeline_items:
            if str(item.get("kind") or "").strip() != "conclusion":
                continue
            content = str(item.get("content", "") or "").strip()
            attachments = _clone_attachment_payloads(item.get("attachments", []))
            if not content and not attachments:
                continue
            if self._is_cleared_conclusion_content(content):
                continue
            self._conclusion_content = content
            self._conclusion_updated_at = str(item.get("timestamp", "") or item.get("created_at", "") or "").strip()
            self._conclusion_attachments = attachments
            return

    def set_todo(
        self,
        todo: TodoItem,
        sync_records: list[dict[str, object]] | None = None,
        task_status_map: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self._store_current_timeline_draft()
        self._reset_stage_summary_state()
        self.reset_assist_troubleshooting_session()
        self._todo_id = todo.id
        self._group_name = _clean_text(todo.summary_fields.group_name)
        self._environment = _clean_text(todo.summary_fields.environment)
        self._product_line = resolve_product_line(raw_value=todo.summary_fields.product_line)
        self._ticket_type = normalize_ticket_type(
            todo.summary_fields.ticket_type,
            summary_text=todo.current_summary,
        )
        self._feature_point = str(todo.summary_fields.feature_point or "").strip()
        self._feature_point_source = str(todo.summary_fields.feature_point_source or "").strip()
        self._root_cause_desc = str(todo.summary_fields.root_cause_desc or "").strip()
        self._root_cause_desc_source = str(todo.summary_fields.root_cause_desc_source or "").strip()
        self._root_cause = str(todo.summary_fields.root_cause or "").strip()
        self._root_cause_source = str(todo.summary_fields.root_cause_source or "").strip()
        self._ticket_version = str(todo.summary_fields.ticket_version or "").strip()
        self._current_summary = todo.current_summary.strip()
        self._conclusion_content = str(todo.conclusion.content or "").strip()
        self._conclusion_updated_at = str(todo.conclusion.updated_at or "").strip()
        self._conclusion_attachments = [self._attachment_to_dict(item) for item in todo.conclusion.attachments]
        self._conclusion_dirty = False
        self._title = todo.title.strip() or _DEFAULT_TODO_TITLE
        self._overview = self._title
        self._created_at = _format_ts(todo.created_at)
        self._updated_at = _format_ts(todo.updated_at)
        task_status_map = task_status_map or {}
        timeline_items = [
            self._build_timeline_item(event, task_status_map.get(event.id, {}))
            for event in _normalize_display_timeline(todo.timeline)
        ]
        result_event_ids: dict[str, str] = {}
        for item in timeline_items:
            if str(item.get("type") or "") != _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_RESULT:
                continue
            payload = _clone_dict(item.get("payload", {}))
            source_event_id = str(payload.get("source_timeline_entry_id", "") or "").strip()
            if source_event_id and source_event_id not in result_event_ids:
                result_event_ids[source_event_id] = str(item.get("id") or "")
        for item in timeline_items:
            if str(item.get("type") or "") != _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND:
                continue
            payload = _clone_dict(item.get("payload", {}))
            result_event_id = str(payload.get("result_event_id", "") or result_event_ids.get(str(item.get("id") or ""), "")).strip()
            if result_event_id:
                payload["result_event_id"] = result_event_id
                item["payload"] = payload
        if not self._conclusion_content.strip() and not self._conclusion_attachments:
            self._hydrate_conclusion_from_timeline(timeline_items)
        self._timeline = timeline_items
        self._refresh_display_timeline()
        self._apply_timeline_draft_state(self._timeline_draft_cache.get(todo.id))
        if not self._current_summary and self._timeline:
            self._current_summary = self._timeline[0]["content"]
            self._title = todo.title.strip() or _DEFAULT_TODO_TITLE
            self._overview = self._title
        self._timeline_expanded = bool(self._timeline)
        self._todo_session_revision += 1
        self._project_match_status = _project_status_label(todo.project_link.match_status)
        self._project_match_detail = _project_status_detail(todo)
        self._project_name = str(todo.project_link.project_snapshot.get("project_name") or "").strip()
        self._project_task_order_no = str(todo.project_link.project_snapshot.get("task_order_no") or "").strip()
        self._project_manager = str(todo.project_link.project_snapshot.get("project_manager") or "").strip()
        self._project_link = TodoProjectLink.from_dict(todo.project_link.to_dict())
        self._load_environment_access(todo.project_link.project_id)
        self._apply_sync_records(sync_records or [])
        self.dataChanged.emit()
        self.timelineChanged.emit()
        self.timelineExpandedChanged.emit()
        self.timelineDraftChanged.emit()

    def _build_timeline_item(self, event: TimelineEvent, status_payload: dict[str, object]) -> dict[str, object]:
        event_type = _timeline_event_type(event)
        normalized_scenario = _normalize_timeline_scenario(event.kind, event.scenario)
        payload = _clone_dict(getattr(event, "payload", {}))
        status = _normalize_card_status(
            str(status_payload.get("uiStatus", "") or getattr(event, "status", "") or status_payload.get("taskStatus", ""))
        )
        if event_type == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND:
            normalized_scenario = _LOG_ANALYSIS_TASK_SCENARIO
            payload = self._build_log_analysis_task_payload(event, payload, status_payload, status)
        elif event_type == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_RESULT:
            normalized_scenario = _LOG_ANALYSIS_RESULT_SCENARIO
            payload = self._build_log_analysis_result_payload(event, payload)
            status = _SUCCESS_STATUS

        created_at = str(getattr(event, "created_at", "") or event.timestamp or "").strip()
        attachments = [self._attachment_to_dict(item) for item in event.attachments]
        task_status = str(status_payload.get("taskStatus", "") or "").strip()
        card_status_label = self._status_label(status)
        if event_type == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND and str(status_payload.get("taskStatusLabel", "") or "").strip():
            card_status_label = str(status_payload.get("taskStatusLabel", "") or "").strip()
        item = {
            "id": event.id,
            "timestamp": event.timestamp,
            "created_at": created_at,
            "timeLabel": _format_ts(created_at or event.timestamp),
            "scenario": normalized_scenario,
            "cardLabel": _timeline_card_label(event_type, normalized_scenario),
            "content": event.content.strip(),
            "kind": event.kind,
            "type": event_type,
            "payload": payload,
            "status": status,
            "statusLabel": card_status_label,
            "attachments": attachments,
            "attachmentCount": len(attachments),
            "taskId": str(status_payload.get("taskId", "") or "").strip(),
            "taskType": str(status_payload.get("taskType", "") or "").strip(),
            "taskStatus": task_status,
            "taskStatusLabel": str(status_payload.get("taskStatusLabel", "") or "").strip(),
            "taskStatusDetail": str(status_payload.get("taskStatusDetail", "") or "").strip(),
        }
        return item

    def _build_log_analysis_task_payload(
        self,
        event: TimelineEvent,
        payload: dict[str, object],
        status_payload: dict[str, object],
        status: str,
    ) -> dict[str, object]:
        resolved = _clone_dict(payload)
        command_text = str(
            resolved.get("command_text", "")
            or resolved.get("raw_command", "")
            or status_payload.get("rawCommand", "")
            or event.content
            or ""
        ).strip()
        current_step = str(status_payload.get("currentStep", "") or resolved.get("current_step", "") or "").strip()
        step_index = self._step_index_for_label(current_step)
        if step_index < 0:
            step_index = self._infer_log_analysis_step_index(status_payload)
        if not current_step and status == _RUNNING_STATUS:
            current_step = _LOG_ANALYSIS_STEP_LABELS[step_index]
        failure_reason = str(
            resolved.get("failure_reason", "")
            or status_payload.get("errorMessage", "")
            or status_payload.get("taskStatusDetail", "")
            or ""
        ).strip()
        failure_details = [
            str(item).strip()
            for item in _clone_list(resolved.get("failure_details", []))
            if str(item).strip()
        ]
        if not failure_details and failure_reason:
            failure_details = [failure_reason]

        process_steps = []
        raw_steps = _clone_list(resolved.get("process_steps", []))
        if raw_steps:
            for item in raw_steps:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label", "") or "").strip()
                step_state = str(item.get("state", "") or "").strip()
                if label:
                    process_steps.append({"label": label, "state": step_state})
        if not process_steps:
            for index, label in enumerate(_LOG_ANALYSIS_STEP_LABELS):
                if status == _SUCCESS_STATUS:
                    step_state = "done"
                elif status == _RUNNING_STATUS and index == step_index:
                    step_state = "active"
                elif index < step_index:
                    step_state = "done"
                else:
                    step_state = "pending"
                process_steps.append({"label": label, "state": step_state})

        resolved.update(
            {
                "command_text": command_text,
                "raw_command": str(status_payload.get("rawCommand", "") or resolved.get("raw_command", "") or command_text).strip(),
                "current_step": current_step,
                "process_steps": process_steps,
                "result_event_id": str(resolved.get("result_event_id", "") or "").strip(),
                "failure_reason": failure_reason,
                "failure_details": failure_details,
                "task_id": str(status_payload.get("taskId", "") or resolved.get("task_id", "") or "").strip(),
            }
        )
        return resolved

    @staticmethod
    def _step_index_for_label(current_step: str) -> int:
        normalized = str(current_step or "").strip()
        if not normalized:
            return -1
        for index, label in enumerate(_LOG_ANALYSIS_STEP_LABELS):
            if label == normalized:
                return index
        return -1

    @staticmethod
    def _should_hide_timeline_item(item: dict[str, object]) -> bool:
        if str(item.get("type") or "") != _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND:
            return False
        payload = _clone_dict(item.get("payload", {}))
        return bool(str(payload.get("result_event_id", "") or "").strip())

    def _refresh_display_timeline(self) -> None:
        self._display_timeline = [
            item
            for item in self._timeline
            if not self._should_hide_timeline_item(item)
        ]

    def _sync_local_conclusion_timeline_item(self) -> None:
        existing_index: int | None = None
        existing_item: dict[str, object] | None = None
        for index, item in enumerate(self._timeline):
            if str(item.get("kind") or "").strip() != "conclusion":
                continue
            existing_index = index
            existing_item = item
            break
        has_meaningful_conclusion = bool(self._conclusion_content.strip() or self._conclusion_attachments)
        if not has_meaningful_conclusion and not self._conclusion_dirty:
            return
        should_render = bool(has_meaningful_conclusion or existing_item is not None or self._conclusion_dirty)
        if not should_render:
            return
        timestamp = self._conclusion_updated_at or datetime.now().isoformat()
        content = build_conclusion_timeline_content(
            self._conclusion_content,
            [
                str(item.get("name", "")).strip()
                for item in self._conclusion_attachments
                if isinstance(item, dict)
            ],
        )
        conclusion_attachments = [dict(item) for item in self._conclusion_attachments if isinstance(item, dict)]
        next_item = {
            "id": str(existing_item.get("id", "")) if isinstance(existing_item, dict) else str(uuid.uuid4()),
            "timestamp": timestamp,
            "created_at": timestamp,
            "timeLabel": _format_ts(timestamp),
            "scenario": _CONCLUSION_SCENARIO,
            "cardLabel": _CONCLUSION_SCENARIO,
            "content": content,
            "kind": "conclusion",
            "type": _TIMELINE_EVENT_TYPE_DEFAULT,
            "payload": _clone_dict(existing_item.get("payload", {})) if isinstance(existing_item, dict) else {},
            "status": "",
            "statusLabel": "",
            "attachments": conclusion_attachments,
            "attachmentCount": len(conclusion_attachments),
        }
        if existing_index is None:
            self._timeline.insert(0, next_item)
        else:
            self._timeline[existing_index] = next_item
        self._refresh_display_timeline()
        if self._timeline and not self._timeline_expanded:
            self._timeline_expanded = True
            self.timelineExpandedChanged.emit()
        self.timelineChanged.emit()

    def _build_log_analysis_result_payload(self, event: TimelineEvent, payload: dict[str, object]) -> dict[str, object]:
        resolved = _clone_dict(payload)
        analyzed_materials = [
            dict(item)
            for item in _clone_list(resolved.get("analyzed_materials", []))
            if isinstance(item, dict)
        ]
        if not analyzed_materials:
            raw_payload = _clone_dict(resolved.get("raw_result_payload", {}))
            analyzed_materials = [
                dict(item)
                for item in _clone_list(raw_payload.get("analyzed_materials", []))
                if isinstance(item, dict)
            ]

        findings = str(resolved.get("findings", "") or "").strip()
        if not findings:
            finding_items = [
                str(item.get("summary", "") or "").strip()
                for item in _clone_list(resolved.get("key_findings", []))
                if isinstance(item, dict) and str(item.get("summary", "") or "").strip()
            ]
            findings = "\n".join(finding_items).strip()
        if not findings:
            findings = event.content.strip()

        conclusion = str(resolved.get("conclusion", "") or resolved.get("primary_issue", "") or "").strip()
        if not conclusion:
            preliminary_judgment = _clone_dict(resolved.get("preliminary_judgment", {}))
            conclusion = str(preliminary_judgment.get("reason", "") or "").strip()

        judgment = str(resolved.get("judgment", "") or "").strip()
        if not judgment:
            preliminary_judgment = _clone_dict(resolved.get("preliminary_judgment", {}))
            judgment = "：".join(
                part
                for part in [
                    str(preliminary_judgment.get("category", "") or "").strip(),
                    str(preliminary_judgment.get("reason", "") or "").strip(),
                ]
                if part
            ).strip()

        next_steps = str(resolved.get("next_steps", "") or "").strip()
        if not next_steps:
            next_steps = "\n".join(
                str(item).strip()
                for item in _clone_list(resolved.get("suggested_next_steps", []))
                if str(item).strip()
            ).strip()

        finding_lines = [
            str(item).strip()
            for item in _clone_list(resolved.get("finding_lines", []))
            if str(item).strip()
        ]
        if not finding_lines and findings:
            finding_lines = [line.strip() for line in findings.splitlines() if line.strip()]

        next_step_lines = [
            str(item).strip()
            for item in _clone_list(resolved.get("next_step_lines", []))
            if str(item).strip()
        ]
        if not next_step_lines and next_steps:
            next_step_lines = [line.strip() for line in next_steps.splitlines() if line.strip()]

        missing_information_lines = [
            str(item).strip()
            for item in _clone_list(resolved.get("missing_information_lines", []))
            if str(item).strip()
        ]
        material_lines = [
            str(item).strip()
            for item in _clone_list(resolved.get("material_lines", []))
            if str(item).strip()
        ]
        if not material_lines and analyzed_materials:
            material_lines = [
                str(item.get("summary", "") or item.get("name", "") or "").strip()
                for item in analyzed_materials
                if str(item.get("summary", "") or item.get("name", "") or "").strip()
            ]

        resolved.update(
            {
                "source_timeline_entry_id": str(resolved.get("source_timeline_entry_id", "") or "").strip(),
                "task_id": str(resolved.get("task_id", "") or "").strip(),
                "analyzed_materials": analyzed_materials,
                "conclusion": conclusion,
                "findings": findings,
                "judgment": judgment,
                "next_steps": next_steps,
                "finding_lines": finding_lines,
                "next_step_lines": next_step_lines,
                "missing_information_lines": missing_information_lines,
                "material_lines": material_lines,
            }
        )
        return resolved

    @staticmethod
    def _infer_log_analysis_step_index(status_payload: dict[str, object]) -> int:
        if _clone_dict(status_payload.get("resultPayload", {})):
            return 2
        evidence_bundle = _clone_dict(status_payload.get("evidenceBundle", {}))
        if _clone_list(evidence_bundle.get("parts", [])):
            return 2
        investigation_context = _clone_dict(status_payload.get("investigationContext", {}))
        if any(str(value).strip() for value in investigation_context.values()):
            return 1
        if _clone_list(status_payload.get("attachmentSnapshot", [])):
            return 1
        return 0

    @staticmethod
    def _status_label(status: str) -> str:
        mapping = {
            _RUNNING_STATUS: "分析中",
            _SUCCESS_STATUS: "已生成",
            _FAILED_STATUS: "失败",
        }
        return mapping.get(str(status or "").strip(), "")

    @pyqtSlot(str, str)
    def updateField(self, name: str, value: str) -> None:
        text = sanitize_text(value)
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
        elif name == "feature_point":
            self._feature_point = text
            self._feature_point_source = "manual"
        elif name == "root_cause_desc":
            self._root_cause_desc = text
            self._root_cause_desc_source = "manual"
        elif name == "root_cause":
            self._root_cause = text
            self._root_cause_source = "manual"
        elif name == "current_summary":
            self._current_summary = text
        elif name == "conclusion_content":
            self._conclusion_content = text
            self._conclusion_updated_at = datetime.now().isoformat()
            self._conclusion_dirty = True
        else:
            return
        self.dataChanged.emit()

    @pyqtSlot(str, str)
    def updateTimelineContent(self, event_id: str, value: str) -> None:
        item = self._find_timeline_item(event_id)
        if item is not None:
            text = sanitize_text(value)
            item["content"] = text
            if str(item.get("kind") or "").strip() == "conclusion":
                self._conclusion_content = text
                self._conclusion_updated_at = datetime.now().isoformat()
                self._conclusion_dirty = True

    @pyqtSlot(str, str)
    def commitTimelineContent(self, event_id: str, value: str) -> None:
        self.updateTimelineContent(event_id, value)
        self._refresh_display_timeline()
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot(str)
    def requestAttachmentSelection(self, event_id: str) -> None:
        if not self._is_valid_attachment_target(event_id):
            return
        self.attachmentSelectionRequested.emit(event_id)

    @pyqtSlot(str)
    def requestClipboardImagePaste(self, event_id: str) -> None:
        if not self._is_valid_attachment_target(event_id):
            return
        self.clipboardImagePasteRequested.emit(event_id)

    @pyqtSlot()
    def requestDraftTimelineAttachmentSelection(self) -> None:
        self.draftAttachmentSelectionRequested.emit()

    @pyqtSlot()
    def requestDraftTimelineClipboardImagePaste(self) -> None:
        self.draftClipboardImagePasteRequested.emit()

    @pyqtSlot(str)
    def updateTimelineDraftText(self, value: str) -> None:
        text = sanitize_text(value)
        if text == self._timeline_draft_text:
            return
        self._timeline_draft_text = text
        self._store_current_timeline_draft()
        self._emit_timeline_draft_changed()

    @pyqtSlot(str)
    def setTimelineDraftEntryType(self, entry_type: str) -> None:
        normalized = _normalize_timeline_draft_entry_type(entry_type)
        if self._timeline_draft_entry_type == normalized and self._timeline_draft_entry_type_selected:
            return
        self._timeline_draft_entry_type = normalized
        self._timeline_draft_entry_type_selected = True
        self._store_current_timeline_draft()
        self._emit_timeline_draft_changed()

    @pyqtSlot()
    def clearTimelineDraftEntryType(self) -> None:
        if self._timeline_draft_entry_type == _ENTRY_TYPE_FOLLOW_UP and not self._timeline_draft_entry_type_selected:
            return
        self._timeline_draft_entry_type = _ENTRY_TYPE_FOLLOW_UP
        self._timeline_draft_entry_type_selected = False
        self._store_current_timeline_draft()
        self._emit_timeline_draft_changed()

    @pyqtSlot()
    def resetTimelineDraft(self) -> None:
        self._reset_current_timeline_draft(remove_files=True)

    @pyqtSlot(str, "QVariantList")
    def addTimelineAttachmentsFromUrls(self, event_id: str, urls: object) -> None:
        file_paths = _coerce_dropped_file_paths(urls)
        if not file_paths:
            return
        self.attach_files_to_event(event_id, file_paths)

    @pyqtSlot("QVariantList")
    def addDraftTimelineAttachmentsFromUrls(self, urls: object) -> None:
        file_paths = _coerce_dropped_file_paths(urls)
        if not file_paths:
            return
        self.attach_files_to_draft_timeline(file_paths)

    @pyqtSlot(str)
    def previewAttachment(self, file_path: str) -> None:
        path = str(file_path or "").strip()
        if not path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @pyqtSlot(str, bool, bool)
    def copyAttachment(self, file_path: str, is_image: bool, is_video: bool) -> None:
        path = Path(str(file_path or "").strip()).expanduser()
        if not path.is_file():
            return
        if bool(is_image):
            self._copy_image_attachment(path)
            return
        if bool(is_video):
            self._copy_file_to_clipboard(path)

    @pyqtSlot(str)
    def copyAttachmentName(self, file_name: str) -> None:
        name = str(file_name or "").strip()
        if not name:
            return
        QGuiApplication.clipboard().setText(name)

    @pyqtSlot(str)
    def copyAttachmentPath(self, file_path: str) -> None:
        path = Path(str(file_path or "").strip()).expanduser()
        if not path.is_file():
            return
        self._copy_file_path_to_clipboard(path)

    @pyqtSlot(str)
    def openAttachmentFolder(self, file_path: str) -> None:
        path = Path(str(file_path or "").strip()).expanduser()
        if not path.exists():
            return
        target_dir = path.parent if path.is_file() else path
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir)))

    @pyqtSlot(str, str)
    def downloadAttachment(self, file_path: str, file_name: str) -> None:
        path = Path(str(file_path or "").strip()).expanduser()
        if not path.is_file():
            return
        self._download_attachment(path, str(file_name or path.name).strip() or path.name)

    @pyqtSlot(str)
    def copyPlainText(self, value: str) -> None:
        text = str(value or "").strip()
        if not text:
            return
        QGuiApplication.clipboard().setText(text)

    @pyqtSlot(str, bool, bool, str)
    def activateAttachment(self, file_path: str, _is_image: bool, _is_video: bool, _file_name: str) -> None:
        path = Path(str(file_path or "").strip()).expanduser()
        if not path.exists():
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _append_log_analysis_timeline_entry(
        self,
        content: str,
        event_id: str,
        timestamp: str,
        attachments: list[dict[str, object]],
        insert_index: int,
    ) -> None:
        command_text = content if is_log_analysis_command(content) else f"/分析日志 {content}".strip()
        parsed_command = parse_log_analysis_command(command_text)
        focus_text = format_log_analysis_focus(parsed_command)
        self._timeline.insert(
            insert_index,
            {
                "id": event_id,
                "timestamp": timestamp,
                "created_at": timestamp,
                "timeLabel": _format_ts(timestamp),
                "scenario": _LOG_ANALYSIS_TASK_SCENARIO,
                "cardLabel": _LOG_ANALYSIS_TASK_SCENARIO,
                "content": parsed_command.raw_command,
                "kind": _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND,
                "type": _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND,
                "payload": {
                    "command_text": parsed_command.raw_command,
                    "raw_command": parsed_command.raw_command,
                    "focus_text": focus_text,
                    "current_step": _LOG_ANALYSIS_STEP_LABELS[0],
                    "process_steps": [
                        {"label": label, "state": "active" if index == 0 else "pending"}
                        for index, label in enumerate(_LOG_ANALYSIS_STEP_LABELS)
                    ],
                    "failure_reason": "",
                    "failure_details": [],
                    "result_event_id": "",
                },
                "status": _RUNNING_STATUS,
                "statusLabel": "排队中",
                "attachments": attachments,
                "attachmentCount": len(attachments),
                "taskId": "",
                "taskType": "log_analysis",
                "taskStatus": "queued",
                "taskStatusLabel": "排队中",
            },
        )
        self._refresh_display_timeline()
        if not self._timeline_expanded:
            self._timeline_expanded = True
            self.timelineExpandedChanged.emit()
        self.timelineChanged.emit()
        self._emit_save_request()
        self._notify("info", "已提交日志分析任务，后台排查中")
        if self._todo_id is not None:
            self.logAnalysisRequested.emit(
                self._todo_id,
                {
                    "timelineEntryId": event_id,
                    "rawCommand": parsed_command.raw_command,
                    "parsedFocus": parsed_command.to_dict(),
                    "attachments": [dict(item) for item in attachments if isinstance(item, dict)],
                },
            )

    @pyqtSlot(str, str)
    def addTimelineEntry(self, value: str, entry_type: str = _ENTRY_TYPE_FOLLOW_UP) -> None:
        content, resolved_type = _normalize_entry_submission(value, entry_type)
        if not content and resolved_type != _ENTRY_TYPE_LOG_ANALYSIS:
            return
        if is_log_analysis_command(content):
            resolved_type = _ENTRY_TYPE_LOG_ANALYSIS
        if resolved_type == _ENTRY_TYPE_CONCLUSION:
            self._conclusion_content = content
            draft_attachments = self._persist_draft_timeline_attachments(_CONCLUSION_ATTACHMENT_TARGET)
            if draft_attachments:
                self._conclusion_attachments = [*self._conclusion_attachments, *draft_attachments]
            self._conclusion_updated_at = datetime.now().isoformat()
            self._conclusion_dirty = True
            self.dataChanged.emit()
            self._sync_local_conclusion_timeline_item()
            self._emit_command_request(
                action=_DETAIL_ACTION_SAVE_CONCLUSION,
                payload={
                    "conclusion": TodoConclusion(
                        content=self._conclusion_content.strip(),
                        updated_at=self._conclusion_updated_at or datetime.now().isoformat(),
                        attachments=[
                            TimelineAttachment(
                                id=str(attachment.get("id", str(uuid.uuid4()))),
                                name=str(attachment.get("name", "")).strip(),
                                path=str(attachment.get("path", "")).strip(),
                                size_bytes=int(attachment.get("sizeBytes", attachment.get("size_bytes", 0)) or 0),
                            )
                            for attachment in self._conclusion_attachments
                            if isinstance(attachment, dict)
                        ],
                    ),
                },
            )
            self._reset_current_timeline_draft(remove_files=False)
            return

        timestamp = datetime.now().isoformat()
        event_id = str(uuid.uuid4())
        attachments = self._persist_draft_timeline_attachments(event_id)
        insert_index = 1 if self._timeline and self._timeline[0].get("kind") == "conclusion" else 0
        if resolved_type == _ENTRY_TYPE_LOG_ANALYSIS:
            self._append_log_analysis_timeline_entry(content, event_id, timestamp, attachments, insert_index)
            self._reset_current_timeline_draft(remove_files=False)
            return

        self._timeline.insert(
            insert_index,
            {
                "id": event_id,
                "timestamp": timestamp,
                "created_at": timestamp,
                "timeLabel": _format_ts(timestamp),
                "scenario": _MANUAL_SCENARIO,
                "cardLabel": _MANUAL_SCENARIO,
                "content": content,
                "kind": "manual",
                "type": _TIMELINE_EVENT_TYPE_DEFAULT,
                "payload": {},
                "status": "",
                "statusLabel": "",
                "attachments": attachments,
                "attachmentCount": len(attachments),
            },
        )
        self._refresh_display_timeline()
        if not self._timeline_expanded:
            self._timeline_expanded = True
            self.timelineExpandedChanged.emit()
        self.timelineChanged.emit()
        self._emit_command_request(
            action=_DETAIL_ACTION_APPEND_TIMELINE_ENTRY,
            payload={
                "event": TimelineEvent(
                    id=event_id,
                    timestamp=timestamp,
                    kind="manual",
                    scenario=_MANUAL_SCENARIO,
                    event_type=_TIMELINE_EVENT_TYPE_DEFAULT,
                    payload={},
                    status="",
                    content=content,
                    attachments=[
                        TimelineAttachment(
                            id=str(attachment.get("id", str(uuid.uuid4()))),
                            name=str(attachment.get("name", "")).strip(),
                            path=str(attachment.get("path", "")).strip(),
                            size_bytes=int(attachment.get("sizeBytes", attachment.get("size_bytes", 0)) or 0),
                        )
                        for attachment in attachments
                        if isinstance(attachment, dict)
                    ],
                    created_at=timestamp,
                ),
            },
        )
        self._reset_current_timeline_draft(remove_files=False)

    @pyqtSlot(str)
    def deleteTimelineCard(self, event_id: str) -> None:
        event_id = str(event_id or "").strip()
        if not event_id:
            return
        related_ids = self._collect_related_timeline_ids(event_id)
        if not related_ids:
            return
        removed = [item for item in self._timeline if str(item.get("id") or "") in related_ids]
        remaining = [item for item in self._timeline if str(item.get("id") or "") not in related_ids]
        if len(remaining) == len(self._timeline):
            return
        for item in removed:
            self._delete_attachments_for_item(item)
        self._timeline = remaining
        self._refresh_display_timeline()
        self.timelineChanged.emit()
        self._emit_save_request()

    def _collect_related_timeline_ids(self, event_id: str) -> set[str]:
        item = self._find_timeline_item(event_id)
        if item is None:
            return set()
        related_ids = {event_id}
        payload = _clone_dict(item.get("payload", {}))
        if str(item.get("type") or "") == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_RESULT:
            source_id = str(payload.get("source_timeline_entry_id", "") or "").strip()
            if source_id:
                related_ids.add(source_id)
        elif str(item.get("type") or "") == _TIMELINE_EVENT_TYPE_LOG_ANALYSIS_COMMAND:
            result_id = str(payload.get("result_event_id", "") or "").strip()
            if result_id:
                related_ids.add(result_id)
        return related_ids

    @pyqtSlot(str)
    def deleteTimelineEntry(self, event_id: str) -> None:
        removed = [item for item in self._timeline if item["id"] == event_id]
        remaining = [item for item in self._timeline if item["id"] != event_id]
        if len(remaining) == len(self._timeline):
            return
        for item in removed:
            self._delete_attachments_for_item(item)
        self._timeline = remaining
        self._refresh_display_timeline()
        self.timelineChanged.emit()
        self._emit_save_request()

    @pyqtSlot(str, str)
    def removeTimelineAttachment(self, event_id: str, attachment_id: str) -> None:
        if event_id == _CONCLUSION_ATTACHMENT_TARGET:
            self.removeConclusionAttachment(attachment_id)
            return
        item = self._find_timeline_item(event_id)
        if item is None:
            return
        if str(item.get("kind") or "").strip() == "conclusion":
            self.removeConclusionAttachment(attachment_id)
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

    @pyqtSlot(str)
    def removeConclusionAttachment(self, attachment_id: str) -> None:
        remaining: list[dict[str, object]] = []
        removed_path = ""
        for attachment in self._conclusion_attachments:
            if not isinstance(attachment, dict):
                continue
            if attachment.get("id") == attachment_id:
                removed_path = str(attachment.get("path", ""))
                continue
            remaining.append(attachment)
        if len(remaining) == len(self._conclusion_attachments):
            return
        self._conclusion_attachments = remaining
        self._conclusion_updated_at = datetime.now().isoformat()
        self._conclusion_dirty = True
        if removed_path:
            self._remove_attachment_file(removed_path)
        self._sync_local_conclusion_timeline_item()
        self.dataChanged.emit()
        self._emit_save_request()

    @pyqtSlot(str)
    def removeDraftTimelineAttachment(self, attachment_id: str) -> None:
        remaining: list[dict[str, object]] = []
        removed_path = ""
        for attachment in self._draft_timeline_attachments:
            if not isinstance(attachment, dict):
                continue
            if attachment.get("id") == attachment_id:
                removed_path = str(attachment.get("path", ""))
                continue
            remaining.append(attachment)
        if len(remaining) == len(self._draft_timeline_attachments):
            return
        self._draft_timeline_attachments = remaining
        if removed_path:
            self._remove_attachment_file(removed_path)
        self._store_current_timeline_draft()
        self._emit_timeline_draft_changed()

    @pyqtSlot()
    def toggleTimeline(self) -> None:
        self._timeline_expanded = not self._timeline_expanded
        self.timelineExpandedChanged.emit()

    @pyqtSlot()
    def toggleStageSummary(self) -> None:
        self._stage_summary_visible = not self._stage_summary_visible
        self.dataChanged.emit()
        if self._stage_summary_visible and not self._stage_summary_requested_once:
            self.refreshStageSummary()

    @pyqtSlot()
    def toggleAssistTroubleshooting(self) -> None:
        self._set_assist_troubleshooting_visible(not self._assist_troubleshooting_visible)

    @pyqtSlot()
    def closeAssistTroubleshooting(self) -> None:
        self._set_assist_troubleshooting_visible(False)

    @pyqtSlot(str)
    def openAssistResultDetail(self, url: str) -> None:
        normalized = sanitize_text(url).strip()
        if not normalized:
            return
        QDesktopServices.openUrl(QUrl(normalized))

    @pyqtSlot()
    def refreshAssistAnalysis(self) -> None:
        self._request_assist_analysis(force=False, mark_requested=True, show_loading=True)

    def prewarmAssistAnalysisIfNeeded(self) -> None:
        self._prewarm_assist_analysis_if_needed()

    def _request_assist_analysis(self, *, force: bool, mark_requested: bool, show_loading: bool) -> None:
        if self._todo_id is None:
            return
        payload = self._build_payload()
        if payload is None:
            return
        cache_key = self._assist_analysis_cache_key()
        cached = self._assist_analysis_cache.get(cache_key)
        if cached is not None and not force:
            self._assist_analysis_busy = False
            self._assist_analysis_error = ""
            self._assist_analysis_requested_once = True
            self._assist_analysis_pending_request_id = ""
            self._assist_analysis_pending_cache_key = ""
            self._assist_analysis_result = self._normalize_assist_analysis_result(cached)
            self._assist_analysis_result["caseResults"] = self._normalize_assist_case_results(cached.get("caseResults"))
            self.dataChanged.emit()
            return
        if self._assist_analysis_pending_cache_key == cache_key:
            if mark_requested:
                self._assist_analysis_requested_once = True
            if show_loading:
                self._assist_analysis_busy = True
                self._assist_analysis_error = ""
                self._assist_analysis_result["caseResults"] = self._empty_assist_case_results(status="loading")
                self.dataChanged.emit()
            return
        request_id = str(uuid.uuid4())
        self._assist_analysis_busy = bool(show_loading)
        self._assist_analysis_error = ""
        if mark_requested:
            self._assist_analysis_requested_once = True
        self._assist_analysis_pending_request_id = request_id
        self._assist_analysis_pending_cache_key = cache_key
        if show_loading:
            self._assist_analysis_result["caseResults"] = self._empty_assist_case_results(status="loading")
            self.dataChanged.emit()
        self.assistAnalysisRequested.emit(
            self._todo_id,
            {
                "requestId": request_id,
                "todoPayload": payload,
                "cacheKey": cache_key,
            },
        )

    def _prewarm_assist_analysis_if_needed(self) -> None:
        if self._todo_id is None:
            return
        cache_key = self._assist_analysis_cache_key()
        if cache_key in self._assist_analysis_cache:
            return
        if self._assist_analysis_pending_cache_key == cache_key:
            return
        self._request_assist_analysis(force=True, mark_requested=False, show_loading=False)

    @pyqtSlot()
    def refreshStageSummary(self) -> None:
        if self._todo_id is None:
            return
        payload = self._build_payload()
        if payload is None:
            return
        request_id = str(uuid.uuid4())
        self._stage_summary_busy = True
        self._stage_summary_error = ""
        self._stage_summary_notice = ""
        self._stage_summary_requested_once = True
        self._stage_summary_pending_request_id = request_id
        self.dataChanged.emit()
        self.stageSummaryRequested.emit(
            self._todo_id,
            {
                "requestId": request_id,
                "todoPayload": payload,
            },
        )

    @pyqtSlot()
    def copyStageSummary(self) -> None:
        text = self._stage_summary_text.strip()
        if not text:
            return
        QGuiApplication.clipboard().setText(text)

    @pyqtSlot(str)
    def updateStageSummaryText(self, text: str) -> None:
        normalized = strip_invalid_surrogates(str(text or ""))
        if normalized == self._stage_summary_text:
            return
        self._stage_summary_text = normalized
        if normalized.strip():
            self._stage_summary_error = ""
        self._stage_summary_notice = ""
        self.dataChanged.emit()

    @pyqtSlot(str)
    def rewriteStageSummaryWithPreset(self, preset_key: str) -> None:
        self._request_stage_summary_rewrite(
            preset_key=str(preset_key or "").strip(),
            instruction="",
            default_rewrite=False,
        )

    @pyqtSlot()
    def rewriteStageSummaryDefault(self) -> None:
        self._request_stage_summary_rewrite(
            preset_key="",
            instruction="",
            default_rewrite=True,
        )

    @pyqtSlot(str)
    def rewriteStageSummary(self, instruction: str) -> None:
        self._request_stage_summary_rewrite(
            preset_key="",
            instruction=str(instruction or "").strip(),
            default_rewrite=False,
        )

    @pyqtSlot()
    def saveTodo(self) -> None:
        has_existing_conclusion_item = any(
            str(item.get("kind") or "").strip() == "conclusion"
            for item in self._timeline
        )
        if (
            self._conclusion_content.strip()
            or self._conclusion_attachments
            or has_existing_conclusion_item
            or str(self._conclusion_updated_at or "").strip()
        ):
            self._sync_local_conclusion_timeline_item()
        else:
            self.timelineChanged.emit()
        self._emit_save_request(save_mode=_SAVE_MODE_MANUAL)
        if self._todo_id is not None:
            QTimer.singleShot(0, lambda: self._notify("success", "保存成功"))

    @pyqtSlot()
    def copyExternalId(self) -> None:
        if not self._external_id:
            return
        QApplication.clipboard().setText(self._external_id)

    @pyqtSlot()
    def requestManualSync(self) -> None:
        if self._todo_id is None:
            return
        self.manualSyncRequested.emit(self._todo_id)

    @pyqtSlot(float, float)
    def beginPanelDrag(self, offset_x: float, offset_y: float) -> None:
        self.panelDragStarted.emit(float(offset_x), float(offset_y))

    @pyqtSlot()
    def updatePanelDrag(self) -> None:
        self.panelDragMoved.emit()

    @pyqtSlot()
    def finishPanelDrag(self) -> None:
        self.panelDragFinished.emit()

    def _build_detail_draft_payload(self) -> dict[str, object] | None:
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
                feature_point=self._feature_point.strip(),
                feature_point_source=self._feature_point_source,
                root_cause_desc=self._root_cause_desc.strip(),
                root_cause_desc_source=self._root_cause_desc_source,
                root_cause=self._root_cause.strip(),
                root_cause_source=self._root_cause_source,
            ).to_dict(),
            "conclusion": TodoConclusion(
                content=self._conclusion_content.strip(),
                updated_at=self._conclusion_updated_at or datetime.now().isoformat(),
                attachments=[
                    TimelineAttachment(
                        id=str(attachment.get("id", str(uuid.uuid4()))),
                        name=str(attachment.get("name", "")).strip(),
                        path=str(attachment.get("path", "")).strip(),
                        size_bytes=int(attachment.get("sizeBytes", attachment.get("size_bytes", 0)) or 0),
                    )
                    for attachment in self._conclusion_attachments
                    if isinstance(attachment, dict)
                ],
            ),
        }

    def _build_payload(self) -> dict[str, object] | None:
        payload = self._build_detail_draft_payload()
        if self._todo_id is None or payload is None:
            return None
        payload["action"] = _DETAIL_ACTION_SAVE_FORM
        payload["timeline"] = [
            TimelineEvent(
                id=item["id"],
                timestamp=item["timestamp"],
                kind=item.get("kind", "analysis"),
                scenario=item.get("scenario", ""),
                event_type=item.get("type", _TIMELINE_EVENT_TYPE_DEFAULT),
                payload=_clone_dict(item.get("payload", {})),
                status=str(item.get("status", "") or ""),
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
                created_at=str(item.get("created_at", item.get("timestamp", "")) or ""),
            )
            for item in reversed(self._timeline)
        ]
        return payload

    def _assist_analysis_cache_key(self) -> str:
        payload = self._build_payload()
        return build_assist_analysis_cache_key(self._todo_id or "", payload or {})

    def _emit_command_request(
        self,
        *,
        action: str,
        payload: dict[str, object],
        save_mode: str = _SAVE_MODE_AUTOSAVE,
    ) -> None:
        if self._todo_id is None:
            return
        draft_payload = self._build_detail_draft_payload()
        if draft_payload is None:
            return
        command_payload = {
            "action": str(action or "").strip(),
            "draft": draft_payload,
            **dict(payload),
        }
        command_payload["saveMode"] = _SAVE_MODE_MANUAL if save_mode == _SAVE_MODE_MANUAL else _SAVE_MODE_AUTOSAVE
        self.saveRequested.emit(self._todo_id, command_payload)

    def attach_files_to_event(self, event_id: str, file_paths: list[str]) -> None:
        if self._todo_id is None:
            return
        item = None if event_id == _CONCLUSION_ATTACHMENT_TARGET else self._find_timeline_item(event_id)
        is_conclusion_target = (
            event_id == _CONCLUSION_ATTACHMENT_TARGET
            or (item is not None and str(item.get("kind") or "").strip() == "conclusion")
        )
        if is_conclusion_target:
            attachments = self._conclusion_attachments
        else:
            if item is None:
                return
            attachments = item.setdefault("attachments", [])
            if not isinstance(attachments, list):
                attachments = []
                item["attachments"] = attachments
        added = False
        attachment_target = _CONCLUSION_ATTACHMENT_TARGET if is_conclusion_target else event_id
        for file_path in file_paths:
            attachment = self._copy_attachment(file_path, attachment_target)
            if attachment is None:
                continue
            attachments.append(attachment)
            added = True
        if not added:
            return
        if is_conclusion_target:
            self._conclusion_attachments = list(attachments)
            self._conclusion_updated_at = datetime.now().isoformat()
            self._conclusion_dirty = True
            self._sync_local_conclusion_timeline_item()
            self.dataChanged.emit()
        else:
            item["attachmentCount"] = len(attachments)
            self.timelineChanged.emit()
        self._emit_save_request()

    def attach_files_to_draft_timeline(self, file_paths: list[str]) -> None:
        added = False
        attachments = list(self._draft_timeline_attachments)
        for file_path in file_paths:
            attachment = self._copy_attachment(file_path, _DRAFT_TIMELINE_ATTACHMENT_TARGET)
            if attachment is None:
                continue
            attachments.append(attachment)
            added = True
        if not added:
            return
        self._draft_timeline_attachments = attachments
        self._store_current_timeline_draft()
        self._emit_timeline_draft_changed()

    def _emit_save_request(self, *, save_mode: str = _SAVE_MODE_AUTOSAVE) -> None:
        payload = self._build_payload()
        if self._todo_id is None or payload is None:
            return
        payload["saveMode"] = _SAVE_MODE_MANUAL if save_mode == _SAVE_MODE_MANUAL else _SAVE_MODE_AUTOSAVE
        self.saveRequested.emit(self._todo_id, payload)

    def _request_stage_summary_rewrite(self, *, preset_key: str, instruction: str, default_rewrite: bool) -> None:
        if self._todo_id is None:
            return
        current_text = self._stage_summary_text.strip()
        if not current_text:
            return
        if not default_rewrite and not preset_key and not instruction:
            return
        request_id = str(uuid.uuid4())
        self._stage_summary_busy = True
        self._stage_summary_error = ""
        self._stage_summary_notice = ""
        self._stage_summary_pending_request_id = request_id
        self.dataChanged.emit()
        self.stageSummaryRewriteRequested.emit(
            self._todo_id,
            {
                "requestId": request_id,
                "currentText": current_text,
                "presetKey": preset_key,
                "instruction": instruction,
                "defaultRewrite": default_rewrite,
            },
        )

    def _reset_stage_summary_state(self, *, keep_visibility: bool = False) -> None:
        self._stage_summary_visible = self._stage_summary_visible if keep_visibility else False
        self._stage_summary_busy = False
        self._stage_summary_text = ""
        self._stage_summary_error = ""
        self._stage_summary_notice = ""
        self._stage_summary_requested_once = False
        self._stage_summary_pending_request_id = ""

    @staticmethod
    def _default_assist_analysis_result() -> dict[str, object]:
        return {
            "summary": "正在基于问题描述和时间线跟进记录整理问题分析摘要。",
            "informationStatus": {
                "recognized": "等待分析当前描述和时间线证据",
                "checkedDirections": [],
            },
            "missingSupplement": {
                "directions": [],
            },
            "upgradeSuggestion": {
                "decision": "暂不建议升级",
                "reason": "等待完成证据分析后再判断是否需要升级。",
            },
        }

    @staticmethod
    def _empty_assist_case_results(status: str = "empty", error_message: str = "") -> dict[str, object]:
        return {
            "status": status,
            "title": "相似案例",
            "countLabel": "检索中" if status == "loading" else "暂无案例",
            "count": "检索中" if status == "loading" else "暂无案例",
            "emptyText": "正在检索相似案例..." if status == "loading" else "暂无案例",
            "items": [],
            "errorMessage": sanitize_text(error_message).strip(),
        }

    @staticmethod
    def _normalize_assist_case_results(payload: object) -> dict[str, object]:
        if not isinstance(payload, dict):
            return _TodoDetailBridge._empty_assist_case_results()
        items: list[dict[str, str]] = []
        dropped_low_score = False
        raw_items = payload.get("items", [])
        if isinstance(raw_items, list):
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                title = sanitize_text(item.get("title")).strip()
                desc = sanitize_text(item.get("desc")).strip()
                text = sanitize_text(item.get("text")).strip()
                detail_url = sanitize_text(item.get("detailUrl") or item.get("detail_url")).strip()
                source = sanitize_text(item.get("source")).strip()
                score = _coerce_int(item.get("score"))
                score_label = sanitize_text(item.get("scoreLabel") or item.get("score_label")).strip()
                match_reason = sanitize_text(item.get("matchReason") or item.get("match_reason")).strip()
                if score < _MIN_ASSIST_CASE_MATCH_SCORE:
                    dropped_low_score = True
                    continue
                if title:
                    items.append(
                        {
                            "title": title,
                            "desc": desc,
                            "text": text or desc or title,
                            "detailUrl": detail_url,
                            "source": source,
                            "score": score,
                            "scoreLabel": score_label or (f"契合度 {score}" if score > 0 else ""),
                            "matchReason": match_reason,
                        }
                    )
                if len(items) >= 5:
                    break
        status = sanitize_text(payload.get("status")).strip() or ("success" if items else "empty")
        if not items and status == "success":
            status = "empty"
        count_label = sanitize_text(payload.get("countLabel") or payload.get("count")).strip()
        if dropped_low_score and status != "loading":
            count_label = f"检索 {len(items)} 条结果" if items else "暂无案例"
        elif not count_label:
            count_label = f"检索 {len(items)} 条结果" if items else "暂无案例"
        empty_text = sanitize_text(payload.get("emptyText")).strip() or ("正在检索相似案例..." if status == "loading" else "暂无案例")
        return {
            "status": status,
            "title": sanitize_text(payload.get("title")).strip() or "相似案例",
            "countLabel": count_label,
            "count": count_label,
            "emptyText": empty_text,
            "items": items,
            "errorMessage": sanitize_text(payload.get("errorMessage")).strip(),
        }

    @staticmethod
    def _normalize_assist_analysis_result(payload: object) -> dict[str, object]:
        data = dict(payload or {}) if isinstance(payload, dict) else {}
        information = dict(data.get("informationStatus") or {}) if isinstance(data.get("informationStatus"), dict) else {}
        missing = dict(data.get("missingSupplement") or {}) if isinstance(data.get("missingSupplement"), dict) else {}
        upgrade = dict(data.get("upgradeSuggestion") or {}) if isinstance(data.get("upgradeSuggestion"), dict) else {}

        def _items(value: object, body_key: str) -> list[dict[str, str]]:
            result: list[dict[str, str]] = []
            if not isinstance(value, list):
                return result
            for item in value:
                if not isinstance(item, dict):
                    continue
                title = sanitize_text(item.get("title")).strip()
                body = sanitize_text(item.get(body_key) or item.get("evidence") or item.get("reason")).strip()
                if title:
                    result.append({"title": title, body_key: body})
            return result

        default_result = _TodoDetailBridge._default_assist_analysis_result()
        return {
            "summary": sanitize_text(data.get("summary")).strip() or str(default_result["summary"]),
            "informationStatus": {
                "recognized": sanitize_text(information.get("recognized")).strip() or "已基于当前描述和时间线完成初步识别",
                "checkedDirections": _items(information.get("checkedDirections"), "evidence"),
            },
            "missingSupplement": {
                "directions": _items(missing.get("directions"), "reason"),
            },
            "upgradeSuggestion": {
                "decision": sanitize_text(upgrade.get("decision")).strip() or "暂不建议升级",
                "reason": sanitize_text(upgrade.get("reason")).strip() or "当前缺少足够证据，建议先补齐问题现象、请求参数、日志或复现结论。",
            },
        }

    @classmethod
    def _normalize_full_assist_analysis_result(cls, payload: object) -> dict[str, object]:
        result = cls._normalize_assist_analysis_result(payload)
        if isinstance(payload, dict) and "caseResults" in payload:
            result["caseResults"] = cls._normalize_assist_case_results(payload.get("caseResults"))
        else:
            result["caseResults"] = cls._empty_assist_case_results()
        return result

    def _reset_assist_analysis_state(self) -> None:
        self._assist_analysis_busy = False
        self._assist_analysis_error = ""
        self._assist_analysis_requested_once = False
        self._assist_analysis_pending_request_id = ""
        self._assist_analysis_pending_cache_key = ""
        self._assist_analysis_result = self._default_assist_analysis_result()

    def _set_assist_troubleshooting_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if self._assist_troubleshooting_visible == visible:
            return
        self._assist_troubleshooting_visible = visible
        self.assistTroubleshootingChanged.emit()
        if visible and not self._assist_analysis_requested_once:
            self.refreshAssistAnalysis()

    def reset_assist_troubleshooting_session(self) -> None:
        self._set_assist_troubleshooting_visible(False)
        self._reset_assist_analysis_state()

    def reset_stage_summary_session(self) -> None:
        self._reset_stage_summary_state()
        self.dataChanged.emit()

    def apply_stage_summary_result(self, todo_id: str, request_id: str, summary_text: str, notice: str = "") -> bool:
        if self._todo_id is None or str(todo_id or "").strip() != self._todo_id:
            return False
        if str(request_id or "").strip() != self._stage_summary_pending_request_id:
            return False
        normalized = sanitize_text(summary_text).strip()
        self._stage_summary_busy = False
        self._stage_summary_pending_request_id = ""
        self._stage_summary_error = ""
        self._stage_summary_notice = sanitize_text(notice).strip()
        if normalized:
            self._stage_summary_text = normalized
        elif not self._stage_summary_text.strip():
            self._stage_summary_error = "暂无可查看的阶段总结"
        else:
            self._stage_summary_notice = self._stage_summary_notice or "本次整理没有生成新的内容"
        self.dataChanged.emit()
        return True

    def apply_stage_summary_error(self, todo_id: str, request_id: str, message: str) -> bool:
        if self._todo_id is None or str(todo_id or "").strip() != self._todo_id:
            return False
        if str(request_id or "").strip() != self._stage_summary_pending_request_id:
            return False
        self._stage_summary_busy = False
        self._stage_summary_pending_request_id = ""
        self._stage_summary_notice = ""
        normalized = sanitize_text(message).strip()
        if normalized:
            self._stage_summary_error = normalized
        elif not self._stage_summary_text.strip():
            self._stage_summary_error = "阶段总结整理失败"
        self.dataChanged.emit()
        return True

    def apply_assist_analysis_result(self, todo_id: str, request_id: str, payload: object) -> bool:
        if self._todo_id is None or str(todo_id or "").strip() != self._todo_id:
            return False
        if str(request_id or "").strip() != self._assist_analysis_pending_request_id:
            return False
        is_final = bool(dict(payload).get("isFinal", True)) if isinstance(payload, dict) else True
        self._assist_analysis_busy = not is_final
        if is_final:
            self._assist_analysis_pending_request_id = ""
        self._assist_analysis_error = ""
        self._assist_analysis_result = self._normalize_full_assist_analysis_result(payload)
        if is_final and self._assist_analysis_pending_cache_key:
            self._assist_analysis_cache[self._assist_analysis_pending_cache_key] = dict(self._assist_analysis_result)
            self._assist_analysis_pending_cache_key = ""
        self.dataChanged.emit()
        return True

    def cache_assist_analysis_result(self, todo_id: str, payload: object) -> bool:
        if not isinstance(payload, dict):
            return False
        phase = sanitize_text(payload.get("phase")).strip()
        should_update = bool(payload.get("shouldUpdate", True))
        if phase == "review" and not should_update:
            return False
        cache_key = sanitize_text(payload.get("cacheKey")).strip()
        if not cache_key:
            if str(todo_id or "").strip() == str(self._todo_id or "").strip():
                cache_key = self._assist_analysis_cache_key()
            else:
                return False
        is_final = bool(payload.get("isFinal", True))
        normalized = self._normalize_full_assist_analysis_result(payload)
        if is_final:
            self._assist_analysis_cache[cache_key] = dict(normalized)
        if str(todo_id or "").strip() != str(self._todo_id or "").strip():
            return True
        if cache_key != self._assist_analysis_cache_key():
            return True
        self._assist_analysis_busy = not is_final and bool(self._assist_analysis_pending_request_id)
        self._assist_analysis_error = ""
        self._assist_analysis_requested_once = True
        self._assist_analysis_result = normalized
        if is_final and self._assist_analysis_pending_cache_key == cache_key:
            self._assist_analysis_pending_cache_key = ""
            self._assist_analysis_pending_request_id = ""
        self.dataChanged.emit()
        return True

    def apply_assist_analysis_error(self, todo_id: str, request_id: str, message: str) -> bool:
        if self._todo_id is None or str(todo_id or "").strip() != self._todo_id:
            return False
        if str(request_id or "").strip() != self._assist_analysis_pending_request_id:
            return False
        self._assist_analysis_busy = False
        self._assist_analysis_pending_request_id = ""
        self._assist_analysis_result["caseResults"] = self._empty_assist_case_results(error_message=message)
        self._assist_analysis_pending_cache_key = ""
        self._assist_analysis_error = sanitize_text(message).strip() or "辅助排查分析失败"
        self.dataChanged.emit()
        return True

    def _apply_sync_records(self, sync_records: list[dict[str, object]]) -> None:
        if not sync_records:
            self._sync_integration_id = ""
            self._sync_status = "未同步"
            self._sync_status_detail = "当前待办还没有外部绑定。"
            self._external_id = ""
            self._sync_event_label = ""
            self._sync_updated_at = ""
            self._sync_records = []
            return

        latest = sync_records[0]
        self._sync_integration_id = str(latest.get("integration_id") or "").strip()
        self._external_id = str(latest.get("external_id") or "").strip()
        sync_status = str(latest.get("last_sync_status") or "").strip()
        self._sync_status = "已同步" if self._external_id else "未同步"
        self._sync_status_detail = sync_status or ("已获得 external_id" if self._external_id else "等待外部系统返回 external_id")
        self._sync_event_label = str(latest.get("last_event_type") or "").strip()
        self._sync_updated_at = _format_ts(str(latest.get("updated_at") or "").strip())
        self._sync_records = [
            {
                "integrationId": str(item.get("integration_id") or "").strip(),
                "externalId": str(item.get("external_id") or "").strip(),
                "hasExternalId": bool(str(item.get("external_id") or "").strip()),
                "status": str(item.get("last_sync_status") or "").strip(),
                "eventType": str(item.get("last_event_type") or "").strip(),
                "updatedAtLabel": _format_ts(str(item.get("updated_at") or "").strip()),
            }
            for item in sync_records
            if isinstance(item, dict)
        ]

    @staticmethod
    def _is_environment_otp_placeholder(entry: object) -> bool:
        access_name = str(getattr(entry, "access_name", "") or "").strip().casefold()
        if "otp" not in access_name:
            return False
        url_or_host = str(getattr(entry, "url_or_host", "") or "").strip()
        username = str(getattr(entry, "username", "") or "").strip()
        note = str(getattr(entry, "note", "") or "").strip()
        return not any([url_or_host, username, note])

    def _load_environment_access(self, project_id: str) -> None:
        self._environment_access_popover_open = False
        normalized_project_id = str(project_id or "").strip()
        if hasattr(self._environment_access_service, "list_effective_environments"):
            bundles = self._environment_access_service.list_effective_environments(normalized_project_id)
        elif hasattr(self._environment_access_service, "list_project_environments"):
            bundles = self._environment_access_service.list_project_environments(normalized_project_id)
        else:
            bundles = []
        visible_entries_by_environment = {
            bundle.environment.id: [
                entry
                for entry in bundle.entries
                if not self._is_environment_otp_placeholder(entry)
            ]
            for bundle in bundles
        }
        self._environment_access_groups = [
            {
                "id": bundle.environment.id,
                "name": bundle.environment.env_name,
                "scope": str(bundle.environment.scope or bundle.source_scope or ""),
                "scopeLabel": "全局环境" if str(bundle.environment.scope or bundle.source_scope or "") == "global" else "项目环境",
                "isGlobal": str(bundle.environment.scope or bundle.source_scope or "") == "global",
                "isProjectOverride": bool(bundle.is_project_override),
                "type": bundle.environment.env_type,
                "note": bundle.environment.note,
                "expanded": False,
                "entryCount": len(visible_entries_by_environment.get(bundle.environment.id, [])),
                "summary": (
                    f"{len(visible_entries_by_environment.get(bundle.environment.id, []))} 个可用访问方式"
                    if visible_entries_by_environment.get(bundle.environment.id, [])
                    else (bundle.environment.note or "暂无可直接访问入口")
                ),
                "entries": [
                    {
                        "scope": str(entry.source_scope or entry.scope or bundle.environment.scope or bundle.source_scope or ""),
                        "scopeLabel": "全局环境" if str(entry.source_scope or entry.scope or bundle.environment.scope or bundle.source_scope or "") == "global" else "项目环境",
                        "isGlobal": str(entry.source_scope or entry.scope or bundle.environment.scope or bundle.source_scope or "") == "global",
                        "isProjectOverride": bool(entry.is_project_override),
                        "id": entry.id,
                        "name": entry.access_name,
                        "type": entry.access_type,
                        "urlOrHost": entry.url_or_host,
                        "username": entry.username,
                        "requiresOtp": bool(entry.requires_otp),
                        "hasTarget": bool(entry.url_or_host.strip()),
                        "hasPassword": bool(
                            self._environment_access_service.get_password(entry.id)
                            if hasattr(self._environment_access_service, "get_password")
                            else False
                        ),
                        "hasOtpSecret": bool(str(entry.otp_secret_encrypted or "").strip()),
                        "note": entry.note,
                        "loginActivated": False,
                        "detailMode": "",
                        "canCopyPassword": False,
                        "canCopyOtp": False,
                        "otpCode": "",
                        "otpRemainingSeconds": 0,
                    }
                    for entry in visible_entries_by_environment.get(bundle.environment.id, [])
                ],
            }
            for bundle in bundles
        ]
        group_count = len(self._environment_access_groups)
        self._environment_access_summary_text = (
            f"环境访问 · {group_count} 组"
            if group_count > 0
            else "环境访问 · 无可用环境"
        )

    def _activate_environment_entry(
        self,
        entry_id: str,
        *,
        login_activated: bool,
        password_available: bool,
        otp_available: bool,
        otp_code: str,
        otp_remaining_seconds: int,
        detail_mode: str = "login",
    ) -> None:
        normalized_entry_id = str(entry_id or "").strip()
        if not normalized_entry_id:
            return
        next_groups = self._clone_environment_groups(self._environment_access_groups)
        for group, entries in self._iterate_environment_entries(next_groups):
            group_expanded = False
            for index, entry in enumerate(entries):
                is_target = str(entry.get("id") or "") == normalized_entry_id
                should_activate = is_target and login_activated
                next_entry = dict(entry)
                next_entry["loginActivated"] = should_activate
                next_entry["detailMode"] = str(detail_mode or "login") if should_activate else ""
                next_entry["canCopyPassword"] = bool(password_available) if should_activate else False
                next_entry["canCopyOtp"] = bool(otp_available) if should_activate else False
                next_entry["otpCode"] = str(otp_code or "") if should_activate else ""
                next_entry["otpRemainingSeconds"] = int(otp_remaining_seconds) if should_activate else 0
                entries[index] = next_entry
                group_expanded = group_expanded or is_target
            group["expanded"] = group_expanded
        self._environment_access_groups = next_groups
        self.dataChanged.emit()

    def _update_entry_otp_state(self, entry_id: str, code: str, remaining: int) -> None:
        normalized_entry_id = str(entry_id or "").strip()
        if not normalized_entry_id:
            return
        def _updater(entry: dict[str, object]) -> tuple[dict[str, object], bool]:
            if str(entry.get("id") or "") != normalized_entry_id:
                return entry, False
            next_remaining = max(0, int(remaining))
            next_code = str(code or "")
            if (
                int(entry.get("otpRemainingSeconds", 0) or 0) == next_remaining
                and str(entry.get("otpCode") or "") == next_code
            ):
                return entry, False
            entry["otpCode"] = next_code
            entry["otpRemainingSeconds"] = next_remaining
            return entry, True

        self._update_environment_entries(_updater)

    def _set_environment_access_message(self, message: str, *, level: str = "info") -> None:
        self._environment_access_message = str(message or "").strip()
        if self._environment_access_message:
            self._notify(level, self._environment_access_message)
        self.environmentAccessMessageChanged.emit()

    @staticmethod
    def _open_environment_target(target: str) -> bool:
        normalized_target = str(target or "").strip()
        if not _is_openable_target(normalized_target):
            return False
        return bool(QDesktopServices.openUrl(QUrl(normalized_target)))

    def _find_timeline_item(self, event_id: str) -> dict[str, object] | None:
        for item in self._timeline:
            if item.get("id") == event_id:
                return item
        return None

    @staticmethod
    def _is_valid_attachment_target(event_id: str) -> bool:
        return bool(event_id)

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
        target_name = "conclusion" if event_id == _CONCLUSION_ATTACHMENT_TARGET else event_id
        target_dir = self._attachment_root / self._todo_id / target_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        counter = 1
        while target.exists():
            target = target_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        shutil.copy2(source, target)
        return self._build_attachment_payload(target)

    def attach_clipboard_image_to_event(self, event_id: str, image: QImage) -> bool:
        item = self._find_timeline_item(event_id) if event_id != _CONCLUSION_ATTACHMENT_TARGET else None
        is_conclusion_target = (
            event_id == _CONCLUSION_ATTACHMENT_TARGET
            or (item is not None and str(item.get("kind") or "").strip() == "conclusion")
        )
        if not is_conclusion_target and item is None:
            return False
        attachment_target = _CONCLUSION_ATTACHMENT_TARGET if is_conclusion_target else event_id
        attachment = self._save_clipboard_image(image, attachment_target)
        if attachment is None:
            return False
        if is_conclusion_target:
            attachments = self._conclusion_attachments
        else:
            attachments = item.setdefault("attachments", [])
            if not isinstance(attachments, list):
                attachments = []
                item["attachments"] = attachments
        attachments.append(attachment)
        if is_conclusion_target:
            self._conclusion_attachments = list(attachments)
            self._conclusion_updated_at = datetime.now().isoformat()
            self._conclusion_dirty = True
            self._sync_local_conclusion_timeline_item()
            self.dataChanged.emit()
        else:
            item["attachmentCount"] = len(attachments)
            self.timelineChanged.emit()
        self._emit_save_request()
        return True

    def attach_clipboard_image_to_draft_timeline(self, image: QImage) -> bool:
        if image.isNull():
            return False
        attachment = self._save_clipboard_image(image, _DRAFT_TIMELINE_ATTACHMENT_TARGET)
        if attachment is None:
            return False
        self._draft_timeline_attachments = [*self._draft_timeline_attachments, attachment]
        self._store_current_timeline_draft()
        self._emit_timeline_draft_changed()
        return True

    def _save_clipboard_image(self, image: QImage, event_id: str) -> dict[str, object] | None:
        if self._todo_id is None or image.isNull():
            return None
        target_name = "conclusion" if event_id == _CONCLUSION_ATTACHMENT_TARGET else event_id
        if event_id not in {_CONCLUSION_ATTACHMENT_TARGET, _DRAFT_TIMELINE_ATTACHMENT_TARGET}:
            item = self._find_timeline_item(event_id)
            if item is None:
                return None
        target_dir = self._attachment_root / self._todo_id / target_name
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = target_dir / f"clipboard_{stamp}.png"
        counter = 1
        while target.exists():
            target = target_dir / f"clipboard_{stamp}_{counter}.png"
            counter += 1
        if not image.save(str(target), "PNG"):
            return None
        return self._build_attachment_payload(target)

    def _build_attachment_payload(self, target: Path) -> dict[str, object]:
        attachment = TimelineAttachment(
            id=str(uuid.uuid4()),
            name=target.name,
            path=str(target),
            size_bytes=target.stat().st_size if target.exists() else 0,
        )
        return self._attachment_to_dict(attachment)

    def _persist_draft_timeline_attachments(self, event_id: str) -> list[dict[str, object]]:
        attachments = list(self._draft_timeline_attachments)
        self._draft_timeline_attachments = []
        if not attachments:
            return []
        moved: list[dict[str, object]] = []
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            moved_attachment = self._move_attachment_to_target(str(attachment.get("path", "")), event_id)
            if moved_attachment is not None:
                moved.append(moved_attachment)
        self._store_current_timeline_draft()
        self._emit_timeline_draft_changed()
        return moved

    def _move_attachment_to_target(self, file_path: str, event_id: str) -> dict[str, object] | None:
        source = Path(str(file_path or "").strip()).expanduser()
        if not source.is_file() or self._todo_id is None:
            return None
        target_name = "conclusion" if event_id == _CONCLUSION_ATTACHMENT_TARGET else event_id
        target_dir = self._attachment_root / self._todo_id / target_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / source.name
        counter = 1
        while target.exists():
            target = target_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        shutil.move(str(source), str(target))
        self._prune_empty_parent_dirs(source.parent)
        return self._build_attachment_payload(target)

    def _copy_image_attachment(self, path: Path) -> None:
        image = QImage(str(path))
        if image.isNull():
            return
        QGuiApplication.clipboard().setImage(image)

    def _copy_file_to_clipboard(self, path: Path) -> None:
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(path))])
        QGuiApplication.clipboard().setMimeData(mime_data)

    def _copy_file_path_to_clipboard(self, path: Path) -> None:
        QGuiApplication.clipboard().setText(str(path))

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
            self._prune_empty_parent_dirs(target.parent)
        except OSError:
            return

    def _prune_empty_parent_dirs(self, start: Path) -> None:
        try:
            root = self._attachment_root.resolve()
            parent = start.resolve()
            while parent != root and parent.exists():
                if any(parent.iterdir()):
                    break
                parent.rmdir()
                parent = parent.parent
        except OSError:
            return

    def _clear_draft_timeline_attachments(self) -> None:
        self._reset_current_timeline_draft(remove_files=True)

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
                feature_point=self._feature_point.strip(),
                feature_point_source=self._feature_point_source,
                root_cause_desc=self._root_cause_desc.strip(),
                root_cause_desc_source=self._root_cause_desc_source,
                root_cause=self._root_cause.strip(),
                root_cause_source=self._root_cause_source,
                ticket_version=self._ticket_version.strip(),
            ).to_dict(),
            "project_link": self._project_link.to_dict(),
            "conclusion": {
                "content": self._conclusion_content.strip(),
                "updatedAt": self._conclusion_updated_at,
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
                    for attachment in self._conclusion_attachments
                    if isinstance(attachment, dict)
                ],
            },
            "timeline": [
                {
                    "id": item["id"],
                    "timestamp": item["timestamp"],
                    "created_at": str(item.get("created_at", item.get("timestamp", "")) or ""),
                    "kind": item.get("kind", "analysis"),
                    "scenario": item.get("scenario", ""),
                    "type": item.get("type", _TIMELINE_EVENT_TYPE_DEFAULT),
                    "payload": _clone_dict(item.get("payload", {})),
                    "status": str(item.get("status", "") or ""),
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


class _StageSummaryWindow(QQuickView):
    _MIN_PANEL_WIDTH = 380
    _MIN_PANEL_HEIGHT = 420

    def __init__(
        self,
        bridge: _TodoDetailBridge,
        *,
        panel_width: int,
        panel_height: int,
        screen_margin: int,
    ) -> None:
        super().__init__()
        self._owner_panel: TodoDetailPanel | None = None
        self._bridge = bridge
        self._panel_width = panel_width
        self._panel_height = panel_height
        self._screen_margin = screen_margin
        self._drag_active = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._anchor_window: QQuickView | None = None
        self._anchor_width = 0
        self._anchor_gap = 0
        self._top_offset = 0
        self._pinned = False
        self._manual_size_override = False
        self._manual_position_override = False

        self._apply_window_flags()
        self.setColor(QColor(0, 0, 0, 0))
        self.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.setMinimumSize(QSize(self._MIN_PANEL_WIDTH, self._MIN_PANEL_HEIGHT))
        self.rootContext().setContextProperty("todoDetailBridge", self._bridge)
        self.rootContext().setContextProperty("stageSummaryWindowBridge", self)
        self.setSource(
            QUrl.fromLocalFile(
                str(qml_dir() / "StageSummaryWindow.qml")
            )
        )
        self._ensure_qml_loaded()
        self.resize(self._panel_width, self._preferred_panel_height())
        self.hide()

    def set_owner_panel(self, owner_panel: "TodoDetailPanel") -> None:
        self._owner_panel = owner_panel

    def set_pinned(self, pinned: bool) -> None:
        self._pinned = bool(pinned)
        self._apply_window_flags()

    def _apply_window_flags(self) -> None:
        was_visible = self.isVisible()
        self.setFlags(
            RUNTIME_CAPABILITIES.floating_tool_window_flags(
                Qt.WindowType,
                stays_on_top=self._pinned,
            )
        )
        if was_visible:
            self.show()

    def _ensure_qml_loaded(self) -> None:
        if self.status() != QQuickView.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self.errors())
        raise RuntimeError(f"Failed to load StageSummaryWindow.qml:\n{errors}")

    def show_near(
        self,
        anchor_window: QQuickView,
        *,
        anchor_width: int,
        anchor_gap: int,
        top_offset: int,
    ) -> None:
        self._anchor_window = anchor_window
        self._anchor_width = anchor_width
        self._anchor_gap = anchor_gap
        self._top_offset = top_offset
        self._sync_geometry(activate=True)

    def update_near(
        self,
        anchor_window: QQuickView,
        *,
        anchor_width: int,
        anchor_gap: int,
        top_offset: int,
    ) -> None:
        self._anchor_window = anchor_window
        self._anchor_width = anchor_width
        self._anchor_gap = anchor_gap
        self._top_offset = top_offset
        self._sync_geometry(activate=False)

    @pyqtSlot()
    def syncPanelSize(self) -> None:
        self._sync_geometry(activate=False)

    @pyqtSlot(str)
    def startPanelResize(self, edge_name: str) -> None:
        edge_map = {
            "left": Qt.Edge.LeftEdge,
            "right": Qt.Edge.RightEdge,
            "top": Qt.Edge.TopEdge,
            "bottom": Qt.Edge.BottomEdge,
            "top_left": Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
            "top_right": Qt.Edge.TopEdge | Qt.Edge.RightEdge,
            "bottom_left": Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
            "bottom_right": Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
        }
        edge = edge_map.get(str(edge_name or "").strip().lower())
        if edge is None:
            return
        try:
            started = self.startSystemResize(edge)
        except AttributeError:
            self.requestActivate()
            return
        if started is False:
            self.requestActivate()
            return
        self._manual_size_override = True

    @pyqtSlot(float, float)
    def beginPanelDrag(self, offset_x: float, offset_y: float) -> None:
        self._drag_active = True
        self._drag_offset_x = max(0, int(offset_x))
        self._drag_offset_y = max(0, int(offset_y))
        self._manual_position_override = True

    @pyqtSlot()
    def updatePanelDrag(self) -> None:
        if not self._drag_active:
            return
        cursor_pos = QCursor.pos()
        x = cursor_pos.x() - self._drag_offset_x
        y = cursor_pos.y() - self._drag_offset_y
        self._move_within_screen(x, y, _virtual_available_geometry())

    @pyqtSlot()
    def finishPanelDrag(self) -> None:
        self._drag_active = False

    def _preferred_panel_height(self, available_height: int | None = None) -> int:
        preferred_height = self._panel_height
        root_object_method = getattr(self, "rootObject", None)
        if callable(root_object_method):
            root_object = root_object_method()
            if root_object is not None:
                raw_value = root_object.property("preferredHeight")
                if raw_value is not None:
                    try:
                        preferred_height = max(120, int(float(raw_value)))
                    except (TypeError, ValueError):
                        preferred_height = self._panel_height
        preferred_height = min(preferred_height, self._panel_height)
        if available_height is not None:
            preferred_height = min(
                preferred_height,
                max(120, int(available_height) - self._screen_margin * 2),
            )
        return max(120, preferred_height)

    def _manual_panel_size(self, available) -> tuple[int, int]:
        max_width = max(
            self._MIN_PANEL_WIDTH,
            int(available.width()) - self._screen_margin * 2,
        )
        max_height = max(
            self._MIN_PANEL_HEIGHT,
            int(available.height()) - self._screen_margin * 2,
        )
        return (
            max(self._MIN_PANEL_WIDTH, min(int(self.width()), max_width)),
            max(self._MIN_PANEL_HEIGHT, min(int(self.height()), max_height)),
        )

    def _sync_geometry(self, *, activate: bool) -> None:
        anchor_window = self._anchor_window
        if anchor_window is None:
            return

        screen = _screen_for_point(anchor_window.frameGeometry().center())
        if screen is None:
            return
        available = _resolve_available_geometry(screen)
        if available is None:
            return

        set_transient_parent = getattr(self, "setTransientParent", None)
        if callable(set_transient_parent):
            set_transient_parent(anchor_window)

        x = _resolve_neighbor_panel_x(
            anchor_window.x(),
            self._anchor_width,
            panel_width=self._panel_width,
            available_left=available.left(),
            available_right=available.right(),
            margin=self._screen_margin,
            gap=self._anchor_gap,
        )
        y = anchor_window.y() + self._top_offset
        if self._manual_size_override:
            width, height = self._manual_panel_size(available)
        else:
            width = self._panel_width
            height = self._preferred_panel_height(available.height())
        self.resize(width, height)
        if self._manual_position_override and self.isVisible():
            current_screen = _screen_for_point(QPoint(self.x(), self.y()))
            self._move_within_screen(self.x(), self.y(), current_screen or screen)
        else:
            self._move_within_screen(x, y, screen)

        is_visible_method = getattr(self, "isVisible", None)
        is_visible = bool(is_visible_method()) if callable(is_visible_method) else False
        if activate and not is_visible:
            self.show()
            is_visible = True
        if activate and is_visible:
            self.raise_()
            self.requestActivate()

    def hide(self) -> None:
        self._manual_size_override = False
        self._manual_position_override = False
        super().hide()

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

    def event(self, event):  # noqa: ANN001, ANN201
        event_type = getattr(event, "type", None)
        if callable(event_type) and event_type() == QEvent.Type.WindowDeactivate:
            owner_panel = self._owner_panel
            if owner_panel is not None:
                QTimer.singleShot(0, owner_panel._close_if_unpinned_after_deactivate)
        return super().event(event)


class _AssistTroubleshootingWindow(QQuickView):
    _MIN_PANEL_WIDTH = 320
    _MIN_PANEL_HEIGHT = 260

    def __init__(
        self,
        bridge: _TodoDetailBridge,
        *,
        panel_width: int,
        panel_height: int,
        screen_margin: int,
    ) -> None:
        super().__init__()
        self._owner_panel: TodoDetailPanel | None = None
        self._bridge = bridge
        self._panel_width = panel_width
        self._panel_height = panel_height
        self._screen_margin = screen_margin
        self._drag_active = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._anchor_window: QQuickView | None = None
        self._anchor_width = 0
        self._anchor_gap = 0
        self._top_offset = 0
        self._pinned = False
        self._manual_size_override = False
        self._manual_position_override = False

        self._apply_window_flags()
        self.setColor(QColor(0, 0, 0, 0))
        self.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.setMinimumSize(QSize(self._MIN_PANEL_WIDTH, self._MIN_PANEL_HEIGHT))
        self.rootContext().setContextProperty("todoDetailBridge", self._bridge)
        self.rootContext().setContextProperty("assistTroubleshootingWindowBridge", self)
        self.setSource(
            QUrl.fromLocalFile(
                str(qml_dir() / "AssistTroubleshootingWindow.qml")
            )
        )
        self._ensure_qml_loaded()
        self.resize(self._panel_width, self._preferred_panel_height())
        self.hide()

    def set_owner_panel(self, owner_panel: "TodoDetailPanel") -> None:
        self._owner_panel = owner_panel

    def set_pinned(self, pinned: bool) -> None:
        self._pinned = bool(pinned)
        self._apply_window_flags()

    def _apply_window_flags(self) -> None:
        was_visible = self.isVisible()
        self.setFlags(
            RUNTIME_CAPABILITIES.floating_tool_window_flags(
                Qt.WindowType,
                stays_on_top=self._pinned,
            )
        )
        if was_visible:
            self.show()

    def _ensure_qml_loaded(self) -> None:
        if self.status() != QQuickView.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self.errors())
        raise RuntimeError(f"Failed to load AssistTroubleshootingWindow.qml:\n{errors}")

    def show_near(
        self,
        anchor_window: QQuickView,
        *,
        anchor_width: int,
        anchor_gap: int,
        top_offset: int,
    ) -> None:
        self._anchor_window = anchor_window
        self._anchor_width = anchor_width
        self._anchor_gap = anchor_gap
        self._top_offset = top_offset
        self._sync_geometry(activate=True)

    def update_near(
        self,
        anchor_window: QQuickView,
        *,
        anchor_width: int,
        anchor_gap: int,
        top_offset: int,
    ) -> None:
        self._anchor_window = anchor_window
        self._anchor_width = anchor_width
        self._anchor_gap = anchor_gap
        self._top_offset = top_offset
        self._sync_geometry(activate=False)

    @pyqtSlot()
    def syncPanelSize(self) -> None:
        self._sync_geometry(activate=False)

    @pyqtSlot(str)
    def startPanelResize(self, edge_name: str) -> None:
        edge_map = {
            "left": Qt.Edge.LeftEdge,
            "right": Qt.Edge.RightEdge,
            "top": Qt.Edge.TopEdge,
            "bottom": Qt.Edge.BottomEdge,
            "top_left": Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
            "top_right": Qt.Edge.TopEdge | Qt.Edge.RightEdge,
            "bottom_left": Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
            "bottom_right": Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
        }
        edge = edge_map.get(str(edge_name or "").strip().lower())
        if edge is None:
            return
        try:
            started = self.startSystemResize(edge)
        except AttributeError:
            self.requestActivate()
            return
        if started is False:
            self.requestActivate()
            return
        self._manual_size_override = True

    @pyqtSlot(float, float)
    def beginPanelDrag(self, offset_x: float, offset_y: float) -> None:
        self._drag_active = True
        self._drag_offset_x = max(0, int(offset_x))
        self._drag_offset_y = max(0, int(offset_y))
        self._manual_position_override = True

    @pyqtSlot()
    def updatePanelDrag(self) -> None:
        if not self._drag_active:
            return
        cursor_pos = QCursor.pos()
        x = cursor_pos.x() - self._drag_offset_x
        y = cursor_pos.y() - self._drag_offset_y
        self._move_within_screen(x, y, _virtual_available_geometry())

    @pyqtSlot()
    def finishPanelDrag(self) -> None:
        self._drag_active = False

    def _preferred_panel_height(self, available_height: int | None = None) -> int:
        preferred_height = self._panel_height
        root_object_method = getattr(self, "rootObject", None)
        if callable(root_object_method):
            root_object = root_object_method()
            if root_object is not None:
                raw_value = root_object.property("preferredHeight")
                if raw_value is not None:
                    try:
                        preferred_height = max(self._MIN_PANEL_HEIGHT, int(float(raw_value)))
                    except (TypeError, ValueError):
                        preferred_height = self._panel_height
        preferred_height = min(preferred_height, self._panel_height)
        if available_height is not None:
            preferred_height = min(
                preferred_height,
                max(self._MIN_PANEL_HEIGHT, int(available_height) - self._screen_margin * 2),
            )
        return max(self._MIN_PANEL_HEIGHT, preferred_height)

    def _manual_panel_size(self, available) -> tuple[int, int]:
        max_width = max(
            self._MIN_PANEL_WIDTH,
            int(available.width()) - self._screen_margin * 2,
        )
        max_height = max(
            self._MIN_PANEL_HEIGHT,
            int(available.height()) - self._screen_margin * 2,
        )
        return (
            max(self._MIN_PANEL_WIDTH, min(int(self.width()), max_width)),
            max(self._MIN_PANEL_HEIGHT, min(int(self.height()), max_height)),
        )

    def _sync_geometry(self, *, activate: bool) -> None:
        anchor_window = self._anchor_window
        if anchor_window is None:
            return

        screen = _screen_for_point(anchor_window.frameGeometry().center())
        if screen is None:
            return
        available = _resolve_available_geometry(screen)
        if available is None:
            return

        set_transient_parent = getattr(self, "setTransientParent", None)
        if callable(set_transient_parent):
            set_transient_parent(anchor_window)

        x = _resolve_neighbor_panel_x(
            anchor_window.x(),
            self._anchor_width,
            panel_width=self._panel_width,
            available_left=available.left(),
            available_right=available.right(),
            margin=self._screen_margin,
            gap=self._anchor_gap,
        )
        y = anchor_window.y() + self._top_offset
        if self._manual_size_override:
            width, height = self._manual_panel_size(available)
        else:
            width = self._panel_width
            height = self._preferred_panel_height(available.height())
        self.resize(width, height)
        if self._manual_position_override and self.isVisible():
            current_screen = _screen_for_point(QPoint(self.x(), self.y()))
            self._move_within_screen(self.x(), self.y(), current_screen or screen)
        else:
            self._move_within_screen(x, y, screen)

        is_visible_method = getattr(self, "isVisible", None)
        is_visible = bool(is_visible_method()) if callable(is_visible_method) else False
        if activate and not is_visible:
            self.show()
            is_visible = True
        if activate and is_visible:
            self.raise_()
            self.requestActivate()

    def hide(self) -> None:
        self._manual_size_override = False
        self._manual_position_override = False
        super().hide()

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

    def event(self, event):  # noqa: ANN001, ANN201
        event_type = getattr(event, "type", None)
        if callable(event_type) and event_type() == QEvent.Type.WindowDeactivate:
            owner_panel = self._owner_panel
            if owner_panel is not None:
                QTimer.singleShot(0, owner_panel._close_if_unpinned_after_deactivate)
        return super().event(event)


class TodoDetailPanel(QQuickView):
    save_requested = pyqtSignal(str, object)
    log_analysis_requested = pyqtSignal(str, object)
    manual_sync_requested = pyqtSignal(str)
    closed = pyqtSignal()
    complete_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    export_plan_requested = pyqtSignal(str, object)
    stage_summary_requested = pyqtSignal(str, object)
    stage_summary_rewrite_requested = pyqtSignal(str, object)
    assist_analysis_requested = pyqtSignal(str, object)

    def __init__(self, parent=None, *, notification_bridge: AppNotificationBridge | None = None):
        super().__init__(parent)
        self._notification_bridge = notification_bridge or AppNotificationBridge()
        self._bridge = _TodoDetailBridge(notification_bridge=self._notification_bridge)
        self._panel_width = 396
        self._stage_summary_window_width = 443
        self._stage_summary_window_gap = 18
        self._stage_summary_top_offset = 84
        self._stage_summary_window_height = 632
        self._assist_troubleshooting_window_width = 443
        self._assist_troubleshooting_window_gap = 18
        self._assist_troubleshooting_top_offset = 84
        self._assist_troubleshooting_window_height = 632
        self._panel_height = 724
        self._screen_margin = 20
        self._anchor_gap = 16
        self._drag_active = False
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._stage_summary_window_visible = False
        self._assist_troubleshooting_window_visible = False
        self._pinned = False
        self._auto_collapse_hold_count = 0

        self._apply_window_flags()
        self.setColor(QColor(0, 0, 0, 0))
        self.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.rootContext().setContextProperty("todoDetailBridge", self._bridge)
        self.setSource(
            QUrl.fromLocalFile(
                str(qml_dir() / "TodoDetailPanel.qml")
            )
        )
        self._ensure_qml_loaded()
        self._stage_summary_window = _StageSummaryWindow(
            self._bridge,
            panel_width=self._stage_summary_window_width,
            panel_height=self._stage_summary_window_height,
            screen_margin=self._screen_margin,
        )
        self._stage_summary_window.set_owner_panel(self)
        self._stage_summary_window.set_pinned(self._pinned)
        self._assist_troubleshooting_window = _AssistTroubleshootingWindow(
            self._bridge,
            panel_width=self._assist_troubleshooting_window_width,
            panel_height=self._assist_troubleshooting_window_height,
            screen_margin=self._screen_margin,
        )
        self._assist_troubleshooting_window.set_owner_panel(self)
        self._assist_troubleshooting_window.set_pinned(self._pinned)

        self._bridge.saveRequested.connect(self.save_requested)
        self._bridge.logAnalysisRequested.connect(self.log_analysis_requested)
        self._bridge.attachmentSelectionRequested.connect(self._select_attachments)
        self._bridge.clipboardImagePasteRequested.connect(self._paste_clipboard_image)
        self._bridge.draftAttachmentSelectionRequested.connect(self._select_draft_timeline_attachments)
        self._bridge.draftClipboardImagePasteRequested.connect(self._paste_draft_timeline_clipboard_image)
        self._bridge.manualSyncRequested.connect(self.manual_sync_requested)
        self._bridge.closeRequested.connect(self._close_panel)
        self._bridge.completeRequested.connect(self.complete_requested)
        self._bridge.deleteRequested.connect(self.delete_requested)
        self._bridge.exportPlanRequested.connect(self.export_plan_requested)
        self._bridge.stageSummaryRequested.connect(self.stage_summary_requested)
        self._bridge.stageSummaryRewriteRequested.connect(self.stage_summary_rewrite_requested)
        self._bridge.assistAnalysisRequested.connect(self.assist_analysis_requested)
        self._bridge.panelDragStarted.connect(self._begin_panel_drag)
        self._bridge.panelDragMoved.connect(self._update_panel_drag)
        self._bridge.panelDragFinished.connect(self._finish_panel_drag)
        self._bridge.dataChanged.connect(self._sync_stage_summary_window)
        self._bridge.assistTroubleshootingChanged.connect(self._sync_assist_troubleshooting_window)

        self.resize(self._panel_width, self._panel_height)
        self.hide()

    def _hold_auto_collapse(self) -> None:
        self._auto_collapse_hold_count += 1

    def _release_auto_collapse(self) -> None:
        if self._auto_collapse_hold_count > 0:
            self._auto_collapse_hold_count -= 1

    def _apply_window_flags(self) -> None:
        was_visible = self.isVisible()
        self._hold_auto_collapse()
        self.setFlags(
            RUNTIME_CAPABILITIES.floating_tool_window_flags(
                Qt.WindowType,
                stays_on_top=self._pinned,
            )
        )
        if was_visible:
            self.show()
        QTimer.singleShot(0, self._release_auto_collapse)

    def set_pinned(self, pinned: bool) -> None:
        pinned = bool(pinned)
        if self._pinned == pinned:
            return
        self._pinned = pinned
        self._apply_window_flags()
        self._stage_summary_window.set_pinned(pinned)
        self._assist_troubleshooting_window.set_pinned(pinned)
        self._sync_stage_summary_window()
        self._sync_assist_troubleshooting_window()
        if pinned and self.isVisible():
            self.raise_()
            self.requestActivate()

    def _ensure_qml_loaded(self) -> None:
        if self.status() != QQuickView.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self.errors())
        raise RuntimeError(f"Failed to load TodoDetailPanel.qml:\n{errors}")

    def _select_attachments(self, event_id: str) -> None:
        self._hold_auto_collapse()
        try:
            files, _ = QFileDialog.getOpenFileNames(
                None,
                "\u9009\u62e9\u9644\u4ef6",
                "",
                "\u6240\u6709\u6587\u4ef6 (*.*)",
            )
        finally:
            self._release_auto_collapse()
        if not files:
            return
        self._bridge.attach_files_to_event(event_id, list(files))

    def _paste_clipboard_image(self, event_id: str) -> None:
        clipboard = QGuiApplication.clipboard()
        image = clipboard.image()
        if image.isNull():
            return
        self._bridge.attach_clipboard_image_to_event(event_id, image)

    def _select_draft_timeline_attachments(self) -> None:
        self._hold_auto_collapse()
        try:
            files, _ = QFileDialog.getOpenFileNames(
                None,
                "\u9009\u62e9\u9644\u4ef6",
                "",
                "\u6240\u6709\u6587\u4ef6 (*.*)",
            )
        finally:
            self._release_auto_collapse()
        if not files:
            return
        self._bridge.attach_files_to_draft_timeline(list(files))

    def _paste_draft_timeline_clipboard_image(self) -> None:
        clipboard = QGuiApplication.clipboard()
        image = clipboard.image()
        if image.isNull():
            return
        self._bridge.attach_clipboard_image_to_draft_timeline(image)

    def show_todo(
        self,
        todo: TodoItem,
        anchor_rect=None,
        sync_records: list[dict[str, object]] | None = None,
        task_status_map: dict[str, dict[str, object]] | None = None,
        preserve_position: bool = False,
    ) -> None:
        self._bridge.set_todo(todo, sync_records=sync_records, task_status_map=task_status_map)
        self._stage_summary_window.hide()
        self._stage_summary_window_visible = False
        self._assist_troubleshooting_window.hide()
        self._assist_troubleshooting_window_visible = False
        self.resize(self._panel_width, self._panel_height)
        self._bridge.prewarmAssistAnalysisIfNeeded()
        if preserve_position and self.isVisible():
            screen = _screen_for_point(QPoint(self.x(), self.y()))
            if screen is None:
                screen = _virtual_available_geometry()
            self._move_within_screen(self.x(), self.y(), screen)
        else:
            self._reposition(anchor_rect)
        self.show()
        self.raise_()
        self.requestActivate()
        self._sync_stage_summary_window()
        self._sync_assist_troubleshooting_window()

    def _sync_stage_summary_window(self) -> None:
        should_show = bool(self._bridge.stageSummaryVisible) and self.isVisible()
        if should_show and not self._stage_summary_window_visible:
            self._stage_summary_window.show_near(
                self,
                anchor_width=self._panel_width,
                anchor_gap=self._stage_summary_window_gap,
                top_offset=self._stage_summary_top_offset,
            )
            self._stage_summary_window_visible = True
            return
        if should_show and self._stage_summary_window_visible:
            self._stage_summary_window.update_near(
                self,
                anchor_width=self._panel_width,
                anchor_gap=self._stage_summary_window_gap,
                top_offset=self._stage_summary_top_offset,
            )
            return
        if not should_show and self._stage_summary_window_visible:
            self._stage_summary_window.hide()
            self._stage_summary_window_visible = False

    def _sync_assist_troubleshooting_window(self) -> None:
        should_show = bool(self._bridge.assistTroubleshootingVisible) and self.isVisible()
        if should_show and not self._assist_troubleshooting_window_visible:
            self._assist_troubleshooting_window.show_near(
                self,
                anchor_width=self._panel_width,
                anchor_gap=self._assist_troubleshooting_window_gap,
                top_offset=self._assist_troubleshooting_top_offset,
            )
            self._assist_troubleshooting_window_visible = True
            return
        if should_show and self._assist_troubleshooting_window_visible:
            self._assist_troubleshooting_window.update_near(
                self,
                anchor_width=self._panel_width,
                anchor_gap=self._assist_troubleshooting_window_gap,
                top_offset=self._assist_troubleshooting_top_offset,
            )
            return
        if not should_show and self._assist_troubleshooting_window_visible:
            self._assist_troubleshooting_window.hide()
            self._assist_troubleshooting_window_visible = False

    def _reposition(self, anchor_rect=None) -> None:
        if anchor_rect is not None:
            screen = _screen_for_point(anchor_rect.center())
        else:
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = _resolve_available_geometry(screen)
        if available is None:
            return
        if anchor_rect is None:
            x = available.right() - self.width() - self._screen_margin
            y = available.top() + self._screen_margin
        else:
            left_x = anchor_rect.left() - self.width() - self._anchor_gap
            right_x = anchor_rect.right() + self._anchor_gap
            if left_x >= available.left() + self._screen_margin:
                x = left_x
            elif right_x + self.width() <= available.right() - self._screen_margin:
                x = right_x
            else:
                x = left_x
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
        self._move_within_screen(x, y, _virtual_available_geometry())

    def _finish_panel_drag(self) -> None:
        self._drag_active = False

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

    def _close_if_unpinned_after_deactivate(self) -> None:
        if self._pinned or self._auto_collapse_hold_count > 0 or not self.isVisible():
            return
        if QGuiApplication.focusWindow() is not None:
            return
        self._close_panel()

    def _close_panel(self) -> None:
        if (
            not self.isVisible()
            and not self._stage_summary_window_visible
            and not self._assist_troubleshooting_window_visible
        ):
            return
        self._bridge.reset_stage_summary_session()
        self._bridge.reset_assist_troubleshooting_session()
        self._stage_summary_window.hide()
        self._stage_summary_window_visible = False
        self._assist_troubleshooting_window.hide()
        self._assist_troubleshooting_window_visible = False
        self.hide()
        self.closed.emit()

    def hide(self) -> None:
        stage_summary_window = getattr(self, "_stage_summary_window", None)
        if stage_summary_window is not None:
            stage_summary_window.hide()
        self._stage_summary_window_visible = False

        assist_troubleshooting_window = getattr(self, "_assist_troubleshooting_window", None)
        if assist_troubleshooting_window is not None:
            assist_troubleshooting_window.hide()
        self._assist_troubleshooting_window_visible = False

        super().hide()

    def event(self, event):  # noqa: ANN001, ANN201
        event_type = getattr(event, "type", None)
        if callable(event_type) and event_type() == QEvent.Type.WindowDeactivate:
            QTimer.singleShot(0, self._close_if_unpinned_after_deactivate)
        return super().event(event)

    def apply_stage_summary_result(self, todo_id: str, request_id: str, summary_text: str, notice: str = "") -> bool:
        return self._bridge.apply_stage_summary_result(todo_id, request_id, summary_text, notice)

    def apply_stage_summary_error(self, todo_id: str, request_id: str, message: str) -> bool:
        return self._bridge.apply_stage_summary_error(todo_id, request_id, message)

    def apply_assist_analysis_result(self, todo_id: str, request_id: str, payload: object) -> bool:
        return self._bridge.apply_assist_analysis_result(todo_id, request_id, payload)

    def cache_assist_analysis_result(self, todo_id: str, payload: object) -> bool:
        return self._bridge.cache_assist_analysis_result(todo_id, payload)

    def apply_assist_analysis_error(self, todo_id: str, request_id: str, message: str) -> bool:
        return self._bridge.apply_assist_analysis_error(todo_id, request_id, message)

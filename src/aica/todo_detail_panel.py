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

        def setText(self, *_args, **_kwargs):
            return None

    class QGuiApplication:  # type: ignore[no-redef]
        @staticmethod
        def clipboard():
            return _Clipboard()

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

from .models import TicketSummaryFields
from .environment_access import EnvironmentAccessService
from .paths import todo_attachments_dir
from .storage.sqlite.environment_repositories import SQLiteProjectEnvironmentRepository
from .ticket_enrichment import ROOT_CAUSE_OPTIONS
from .ticket_field_resolver import (
    TICKET_TYPE_OPTIONS,
    normalize_ticket_type,
    resolve_product_line,
)
from .text_sanitize import sanitize_text
from .todo_store import TimelineAttachment, TimelineEvent, TodoConclusion, TodoItem

_EMPTY_TEXT = "未填写"
_DEFAULT_TODO_TITLE = "\u672a\u5206\u7c7b\u4efb\u52a1"
_MANUAL_SCENARIO = "\u95ee\u9898\u53cd\u9988"
_SYSTEM_SCENARIO = "\u7cfb\u7edf\u8bb0\u5f55"
_CONCLUSION_SCENARIO = "\u95ee\u9898\u7ed3\u8bba"
_CONCLUSION_ATTACHMENT_TARGET = "__conclusion__"
_ENTRY_TYPE_FOLLOW_UP = "follow_up"
_ENTRY_TYPE_CONCLUSION = "conclusion"
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
        if entry_type in {_ENTRY_TYPE_FOLLOW_UP, _ENTRY_TYPE_CONCLUSION}
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
            return f"{project_name} · {task_order_no}"
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
    environmentAccessMessageChanged = pyqtSignal()
    panelDragStarted = pyqtSignal(float, float)
    panelDragMoved = pyqtSignal()
    panelDragFinished = pyqtSignal()

    saveRequested = pyqtSignal(str, object)
    attachmentSelectionRequested = pyqtSignal(str)
    clipboardImagePasteRequested = pyqtSignal(str)
    manualSyncRequested = pyqtSignal(str)
    closeRequested = pyqtSignal()
    completeRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)
    exportPlanRequested = pyqtSignal(str, object)

    def __init__(
        self,
        attachment_root: Path | None = None,
        *,
        environment_access_service: EnvironmentAccessService | None = None,
    ) -> None:
        super().__init__()
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
        self._overview = ""
        self._created_at = ""
        self._updated_at = ""
        self._timeline: list[dict[str, object]] = []
        self._timeline_expanded = True
        self._attachment_root = Path(attachment_root) if attachment_root is not None else todo_attachments_dir()
        self._project_match_status = "未匹配项目"
        self._project_match_detail = "当前群聊名称尚未命中任何项目别名。"
        self._project_name = ""
        self._project_task_order_no = ""
        self._project_manager = ""
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
            self._set_environment_access_message("未找到环境访问项")
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
        self._set_environment_access_message(message)

    @pyqtSlot(str)
    def copyEnvironmentUsername(self, entry_id: str) -> None:
        entry_id = str(entry_id or "").strip()
        if not entry_id:
            self._set_environment_access_message("当前访问方式未配置账号")
            return
        username = ""
        for _group, entries in self._iterate_environment_entries(self._environment_access_groups):
            for entry in entries:
                if str(entry.get("id") or "") == entry_id:
                    username = str(entry.get("username") or "").strip()
                    break
            if username:
                break
        if not username:
            self._set_environment_access_message("当前访问方式未配置账号")
            return
        QApplication.clipboard().setText(username)
        self._set_environment_access_message("已复制账号")

    @pyqtSlot(str)
    def copyEnvironmentPassword(self, entry_id: str) -> None:
        password = self._environment_access_service.get_password(str(entry_id or "").strip())
        if not password:
            self._set_environment_access_message("当前访问方式未配置密码")
            return
        QApplication.clipboard().setText(password)
        self._set_environment_access_message("已复制密码")

    @pyqtSlot(str)
    def copyEnvironmentOtp(self, entry_id: str) -> None:
        code, remaining = self._environment_access_service.get_otp_code(str(entry_id or "").strip())
        if not code:
            self._set_environment_access_message("当前访问方式暂无可用验证码")
            return
        QApplication.clipboard().setText(code)
        self._update_entry_otp_state(str(entry_id or "").strip(), code, remaining)
        self._set_environment_access_message("已复制验证码")

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

    def set_todo(self, todo: TodoItem, sync_records: list[dict[str, object]] | None = None) -> None:
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
        self._current_summary = todo.current_summary.strip()
        self._conclusion_content = str(todo.conclusion.content or "").strip()
        self._conclusion_updated_at = str(todo.conclusion.updated_at or "").strip()
        self._conclusion_attachments = [self._attachment_to_dict(item) for item in todo.conclusion.attachments]
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
            for event in _normalize_display_timeline(todo.timeline)
        ]
        if not self._current_summary and self._timeline:
            self._current_summary = self._timeline[0]["content"]
            self._title = todo.title.strip() or _DEFAULT_TODO_TITLE
            self._overview = self._title
        self._timeline_expanded = bool(self._timeline)
        self._project_match_status = _project_status_label(todo.project_link.match_status)
        self._project_match_detail = _project_status_detail(todo)
        self._project_name = str(todo.project_link.project_snapshot.get("project_name") or "").strip()
        self._project_task_order_no = str(todo.project_link.project_snapshot.get("task_order_no") or "").strip()
        self._project_manager = str(todo.project_link.project_snapshot.get("project_manager") or "").strip()
        self._load_environment_access(todo.project_link.project_id)
        self._apply_sync_records(sync_records or [])
        self.dataChanged.emit()
        self.timelineChanged.emit()
        self.timelineExpandedChanged.emit()

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
        else:
            return
        self.dataChanged.emit()

    @pyqtSlot(str, str)
    def updateTimelineContent(self, event_id: str, value: str) -> None:
        item = self._find_timeline_item(event_id)
        if item is not None:
            item["content"] = sanitize_text(value)

    @pyqtSlot(str, str)
    def commitTimelineContent(self, event_id: str, value: str) -> None:
        self.updateTimelineContent(event_id, value)
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

    @pyqtSlot(str, str)
    def addTimelineEntry(self, value: str, entry_type: str = _ENTRY_TYPE_FOLLOW_UP) -> None:
        content, resolved_type = _normalize_entry_submission(value, entry_type)
        if not content:
            return
        if resolved_type == _ENTRY_TYPE_CONCLUSION:
            self._conclusion_content = content
            self._conclusion_updated_at = datetime.now().isoformat()
            self.dataChanged.emit()
            self._emit_save_request()
            return
        timestamp = datetime.now().isoformat()
        insert_index = 1 if self._timeline and self._timeline[0].get("kind") == "conclusion" else 0
        self._timeline.insert(
            insert_index,
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
        if event_id == _CONCLUSION_ATTACHMENT_TARGET:
            self.removeConclusionAttachment(attachment_id)
            return
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
        if removed_path:
            self._remove_attachment_file(removed_path)
        self.dataChanged.emit()
        self._emit_save_request()

    @pyqtSlot()
    def toggleTimeline(self) -> None:
        self._timeline_expanded = not self._timeline_expanded
        self.timelineExpandedChanged.emit()

    @pyqtSlot()
    def saveTodo(self) -> None:
        self.timelineChanged.emit()
        self._emit_save_request()

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
        if self._todo_id is None:
            return
        if event_id == _CONCLUSION_ATTACHMENT_TARGET:
            attachments = self._conclusion_attachments
        else:
            item = self._find_timeline_item(event_id)
            if item is None:
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
        if event_id == _CONCLUSION_ATTACHMENT_TARGET:
            self._conclusion_attachments = list(attachments)
            self._conclusion_updated_at = datetime.now().isoformat()
            self.dataChanged.emit()
        else:
            item["attachmentCount"] = len(attachments)
            self.timelineChanged.emit()
        self._emit_save_request()

    def _emit_save_request(self) -> None:
        payload = self._build_payload()
        if self._todo_id is None or payload is None:
            return
        self.saveRequested.emit(self._todo_id, payload)

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
        if not normalized_project_id:
            self._environment_access_groups = []
            self._environment_access_summary_text = "环境访问 · 无可用环境"
            return
        bundles = self._environment_access_service.list_project_environments(normalized_project_id)
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
                        "id": entry.id,
                        "name": entry.access_name,
                        "type": entry.access_type,
                        "urlOrHost": entry.url_or_host,
                        "username": entry.username,
                        "requiresOtp": bool(entry.requires_otp),
                        "hasTarget": bool(entry.url_or_host.strip()),
                        "hasPassword": bool(self._environment_access_service.get_password(entry.id)),
                        "hasOtpSecret": bool(str(entry.otp_secret_encrypted or "").strip()),
                        "note": entry.note,
                        "loginActivated": False,
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

    def _set_environment_access_message(self, message: str) -> None:
        self._environment_access_message = str(message or "").strip()
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
        if self._todo_id is None or image.isNull():
            return False
        target_name = "conclusion" if event_id == _CONCLUSION_ATTACHMENT_TARGET else event_id
        item = self._find_timeline_item(event_id) if event_id != _CONCLUSION_ATTACHMENT_TARGET else None
        if event_id != _CONCLUSION_ATTACHMENT_TARGET and item is None:
            return False
        target_dir = self._attachment_root / self._todo_id / target_name
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = target_dir / f"clipboard_{stamp}.png"
        counter = 1
        while target.exists():
            target = target_dir / f"clipboard_{stamp}_{counter}.png"
            counter += 1
        if not image.save(str(target), "PNG"):
            return False
        if event_id == _CONCLUSION_ATTACHMENT_TARGET:
            attachments = self._conclusion_attachments
        else:
            attachments = item.setdefault("attachments", [])
            if not isinstance(attachments, list):
                attachments = []
                item["attachments"] = attachments
        attachments.append(self._build_attachment_payload(target))
        if event_id == _CONCLUSION_ATTACHMENT_TARGET:
            self._conclusion_attachments = list(attachments)
            self._conclusion_updated_at = datetime.now().isoformat()
            self.dataChanged.emit()
        else:
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
                feature_point=self._feature_point.strip(),
                feature_point_source=self._feature_point_source,
                root_cause_desc=self._root_cause_desc.strip(),
                root_cause_desc_source=self._root_cause_desc_source,
                root_cause=self._root_cause.strip(),
                root_cause_source=self._root_cause_source,
            ).to_dict(),
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
    manual_sync_requested = pyqtSignal(str)
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
        self._bridge.manualSyncRequested.connect(self.manual_sync_requested)
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

    def show_todo(self, todo: TodoItem, anchor_rect=None, sync_records: list[dict[str, object]] | None = None) -> None:
        self._bridge.set_todo(todo, sync_records=sync_records)
        self.resize(self._panel_width, self._panel_height)
        self._reposition(anchor_rect)
        self.show()
        self.raise_()
        self.requestActivate()

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

    def _close_panel(self) -> None:
        self.hide()
        self.closed.emit()

"""QML-backed application control panel."""
from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import sys
import tempfile

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QDate, QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
    from PyQt6.QtGui import QColor, QDesktopServices
    from PyQt6.QtQuickWidgets import QQuickWidget
    from PyQt6.QtWidgets import QApplication, QCalendarWidget, QDialog, QDialogButtonBox, QFileDialog, QWidget, QVBoxLayout
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

    class QDate:  # type: ignore[no-redef]
        def __init__(self, text=""):
            self._text = text

        @staticmethod
        def fromString(text, _format):
            return QDate(str(text or ""))

        @staticmethod
        def currentDate():
            return QDate("2000-01-01")

        def isValid(self):
            return bool(self._text)

        def toString(self, _format):
            return self._text or "2000-01-01"

    class Qt:  # type: ignore[no-redef]
        class WindowType:
            Window = 0
            FramelessWindowHint = 0
            WindowSystemMenuHint = 0
            WindowMinMaxButtonsHint = 0

        class WidgetAttribute:
            WA_TranslucentBackground = 0

        class WindowState:
            WindowMaximized = 0

        class Edge:
            LeftEdge = 0
            RightEdge = 0
            TopEdge = 0
            BottomEdge = 0

    class QUrl:  # type: ignore[no-redef]
        def __init__(self, path=""):
            self._path = path

        @staticmethod
        def fromLocalFile(path):
            return QUrl(path)

        def isLocalFile(self):
            return str(self._path).startswith("file:")

        def toLocalFile(self):
            text = str(self._path)
            if text.startswith("file:///"):
                return text[8:]
            if text.startswith("file://"):
                return text[7:]
            return text

    class QColor:  # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            pass

    class QDesktopServices:  # type: ignore[no-redef]
        @staticmethod
        def openUrl(*_args, **_kwargs):
            return False

    class _DummyContext:
        def setContextProperty(self, *_args, **_kwargs):
            return None

    class QQuickWidget:  # type: ignore[no-redef]
        class ResizeMode:
            SizeRootObjectToView = 0

        class Status:
            Error = "error"

        def __init__(self, *_args, **_kwargs):
            self._context = _DummyContext()

        def setClearColor(self, *_args, **_kwargs):
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

    class _Clipboard:
        def setText(self, *_args, **_kwargs):
            return None

        def text(self):
            return ""

        def image(self):
            return None

        def mimeData(self):
            return None

    class QApplication:  # type: ignore[no-redef]
        @staticmethod
        def clipboard():
            return _Clipboard()

        @staticmethod
        def screenAt(*_args, **_kwargs):
            return None

        @staticmethod
        def primaryScreen():
            return None

    class QCalendarWidget:  # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            self._selected_date = QDate.currentDate()

        def setSelectedDate(self, date):
            self._selected_date = date

        def selectedDate(self):
            return self._selected_date

    class QDialog:  # type: ignore[no-redef]
        class DialogCode:
            Accepted = 1

        def setWindowTitle(self, *_args, **_kwargs):
            return None

        def setModal(self, *_args, **_kwargs):
            return None

        def exec(self):
            return 0

        def accept(self):
            return None

        def reject(self):
            return None

    class _DummySignal:
        def connect(self, *_args, **_kwargs):
            return None

    class QDialogButtonBox:  # type: ignore[no-redef]
        class StandardButton:
            Ok = 1
            Cancel = 2

        def __init__(self, *_args, **_kwargs):
            self.accepted = _DummySignal()
            self.rejected = _DummySignal()

    class QFileDialog:  # type: ignore[no-redef]
        @staticmethod
        def getExistingDirectory(*_args, **_kwargs):
            return ""

        @staticmethod
        def getOpenFileName(*_args, **_kwargs):
            return "", ""

        @staticmethod
        def getSaveFileName(*_args, **_kwargs):
            return "", ""

    class QWidget:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass

    class QVBoxLayout:  # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            pass

        def setSpacing(self, *_args, **_kwargs):
            return None

from aica.analysis.metrics import AnalysisMetricsStore, ModelLatencySummary
from aica.analysis.rules import (
    AnalysisRulesManager,
    PromptDebugStore,
    SceneAnalysisRule,
    UserRuleConfig,
    build_scene_options_payload,
)
from aica.app_notifications import AppNotificationBridge
from aica.config import ConfigManager, ProviderConfig, ProviderModelConfig, TaskModelBinding
from aica.hotkey import normalize_hotkey
from aica.control_panel_state import (
    build_script_integration,
    describe_script_integration_support,
    format_image_limit_megabytes,
    list_script_integrations,
    load_integration_config,
    normalize_directory_path,
    persist_storage_paths,
    persist_control_panel_config,
    replace_script_integrations,
    save_integration_config,
    script_integration_display_path,
    update_script_integration_path,
)
from aica.environment_access import (
    EnvironmentAccessEntryRecord,
    EnvironmentAccessService,
    ProjectEnvironmentBundle,
    ProjectEnvironmentRecord,
    normalize_access_type,
    normalize_environment_scope,
)
from aica.otp_secret_extractor import OtpSecretExtractResult, extract_otp_secret_from_qr_image, parse_otpauth_payload
from aica.project_management import (
    build_project_template_content,
    find_active_alias_conflicts,
    import_projects_from_file,
    project_record_from_payload,
    project_to_payload,
)
from aica.paths import (
    aica_database_file,
    asset_file,
    app_data_dir,
    analysis_rules_file,
    config_file,
    error_log_file,
    feedback_dir,
    integrations_file,
    log_dir,
    prompt_debug_dir,
    storage_config_file,
    qml_dir,
)
from aica.models import TicketSummaryFields, is_unknown_text
from aica.runtime import RUNTIME_CAPABILITIES
from aica.storage.adapters import now_iso
from aica.storage.sqlite.environment_repositories import SQLiteProjectEnvironmentRepository
from aica.storage.sqlite.repositories import SQLiteProjectRepository
from aica.ticket_enrichment import ROOT_CAUSE_OPTIONS, build_feature_point_provider
from aica.todo.models import TodoItem, TodoStatus
from aica.todo.store import TodoStore
from aica.window_effects import disable_windows_window_border

_QT_KEY_ESCAPE = 0x01000000
_QT_KEY_TAB = 0x01000001
_QT_KEY_RETURN = 0x01000004
_QT_KEY_ENTER = 0x01000005
_QT_KEY_SPACE = 0x20
_QT_KEY_SHIFT = 0x01000020
_QT_KEY_CONTROL = 0x01000021
_QT_KEY_META = 0x01000022
_QT_KEY_ALT = 0x01000023
_QT_KEY_F1 = 0x01000030
_QT_KEY_F24 = _QT_KEY_F1 + 23

_QT_SHIFT_MODIFIER = 0x02000000
_QT_CONTROL_MODIFIER = 0x04000000
_QT_ALT_MODIFIER = 0x08000000
_QT_META_MODIFIER = 0x10000000


def _hotkey_primary_from_qt_key(key: int, text: str) -> str | None:
    if key == _QT_KEY_SPACE:
        return "Space"
    if key == _QT_KEY_TAB:
        return "Tab"
    if key in (_QT_KEY_RETURN, _QT_KEY_ENTER):
        return "Enter"
    if key == _QT_KEY_ESCAPE:
        return "Esc"
    if _QT_KEY_F1 <= key <= _QT_KEY_F24:
        return f"F{key - _QT_KEY_F1 + 1}"
    if ord("0") <= key <= ord("9"):
        return chr(key)
    if ord("A") <= key <= ord("Z"):
        return chr(key)
    if ord("a") <= key <= ord("z"):
        return chr(key).upper()
    token = str(text or "").strip()
    if len(token) == 1 and token.isalnum():
        return token.upper()
    return None


def hotkey_from_qt_key_event(
    key: int,
    modifiers: int,
    text: str = "",
    *,
    platform_id: str | None = None,
) -> str | None:
    if key in {_QT_KEY_SHIFT, _QT_KEY_CONTROL, _QT_KEY_ALT, _QT_KEY_META}:
        return None

    primary_key = _hotkey_primary_from_qt_key(int(key or 0), text)
    if not primary_key:
        return None

    normalized_platform = RUNTIME_CAPABILITIES.platform_id if platform_id is None else platform_id
    modifier_parts: list[str] = []
    if normalized_platform == "macos":
        # Qt on macOS maps the physical Command key to ControlModifier,
        # and the physical Control key to MetaModifier.
        if modifiers & _QT_CONTROL_MODIFIER:
            modifier_parts.append("Command")
        if modifiers & _QT_ALT_MODIFIER:
            modifier_parts.append("Option")
        if modifiers & _QT_META_MODIFIER:
            modifier_parts.append("Control")
        if modifiers & _QT_SHIFT_MODIFIER:
            modifier_parts.append("Shift")
    else:
        if modifiers & _QT_CONTROL_MODIFIER:
            modifier_parts.append("Ctrl")
        if modifiers & _QT_ALT_MODIFIER:
            modifier_parts.append("Alt")
        if modifiers & _QT_SHIFT_MODIFIER:
            modifier_parts.append("Shift")
        if modifiers & _QT_META_MODIFIER:
            modifier_parts.append("Win")

    if not modifier_parts:
        raise ValueError("截图热键至少需要一个修饰键")

    return normalize_hotkey("+".join([*modifier_parts, primary_key]), normalized_platform)


_TASK_LABELS = {
    "analysis": "截图分析",
    "plan_export": "方案导出",
}
_TASK_LABELS["context_summary"] = "上下文摘要"
_TASK_LABELS["log_analysis"] = "日志分析"
_SECTION_GROUPS = [
    {
        "id": "business",
        "title": "\u4e1a\u52a1\u7ba1\u7406",
        "items": [
            {
                "id": "projects",
                "title": "\u9879\u76ee\u7ba1\u7406",
                "description": "\u5bfc\u5165\u9879\u76ee\u4e3b\u6570\u636e\u5e76\u7ef4\u62a4\u7fa4\u540d\u522b\u540d\uff0c\u8865\u9f50\u5f85\u529e\u9879\u76ee\u5173\u8054\u3002",
            },
            {
                "id": "tickets",
                "title": "\u5de5\u5355\u7ba1\u7406",
                "description": "\u67e5\u770b\u5de5\u5355\u5217\u8868\uff0c\u5e76\u5728\u63a7\u5236\u9762\u677f\u5185\u67e5\u770b\u5386\u53f2\u8ddf\u8fdb\u8be6\u60c5\u3002",
            },
            {
                "id": "environments",
                "title": "\u73af\u5883\u7ba1\u7406",
                "description": "\u5728\u540c\u4e00\u9875\u9762\u7edf\u4e00\u7ef4\u62a4\u5168\u5c40\u73af\u5883\u4e0e\u9879\u76ee\u73af\u5883\uff0c\u652f\u6301\u6309\u6807\u7b7e\u3001\u68c0\u7d22\u4e0e\u5feb\u901f\u5207\u6362\u3002",
            },
        ],
    },
    {
        "id": "models_and_rules",
        "title": "\u6a21\u578b\u4e0e\u89c4\u5219",
        "items": [
            {
                "id": "models",
                "title": "\u6a21\u578b\u4f9b\u5e94\u5546",
                "description": "\u7ef4\u62a4\u4f9b\u5e94\u5546\u51ed\u8bc1\u3001\u8bf7\u6c42\u5730\u5740\u4e0e\u4efb\u52a1\u6a21\u578b\u7ed1\u5b9a\u3002",
            },
            {
                "id": "analysis_rules",
                "title": "\u89c4\u5219\u4e0e\u8c03\u8bd5",
                "description": "\u914d\u7f6e\u573a\u666f\u5206\u6790\u89c4\u5219\uff0c\u5e76\u67e5\u770b Prompt \u8c03\u8bd5\u5feb\u7167\u3002",
            },
        ],
    },
    {
        "id": "runtime_and_integrations",
        "title": "\u8fd0\u884c\u4e0e\u96c6\u6210",
        "items": [
            {
                "id": "hotkeys",
                "title": "\u5feb\u6377\u952e",
                "description": "\u8c03\u6574\u622a\u56fe\u70ed\u952e\u5e76\u7acb\u5373\u751f\u6548\u3002",
            },
            {
                "id": "storage",
                "title": "\u5b58\u50a8\u4e0e\u65e5\u5fd7",
                "description": "\u67e5\u770b\u914d\u7f6e\u4f4d\u7f6e\u5e76\u5feb\u901f\u8df3\u8f6c\u672c\u5730\u6570\u636e\u76ee\u5f55\u3002",
            },
            {
                "id": "server",
                "title": "\u670d\u52a1\u7aef\u96c6\u6210",
                "description": "\u914d\u7f6e Chattodo \u670d\u52a1\u7aef\u5730\u5740\u548c API Key\uff0c\u4e3a\u540e\u7eed\u80fd\u529b\u63a5\u5165\u505a\u51c6\u5907\u3002",
            },
            {
                "id": "integrations",
                "title": "\u811a\u672c\u96c6\u6210",
                "description": "\u5bfc\u5165\u5916\u90e8\u811a\u672c\uff0c\u5e76\u63a7\u5236\u542f\u7528\u6216\u505c\u7528\u540c\u6b65\u811a\u672c\u3002",
            },
        ],
    },
]
_SECTION_ITEMS = [item for group in _SECTION_GROUPS for item in group["items"]]
_SECTION_VIEW_META = {
    "models": {
        "title": "\u6a21\u578b\u4f9b\u5e94\u5546\u4e0e\u4efb\u52a1\u6a21\u578b",
        "description": "\u7ba1\u7406\u4f9b\u5e94\u5546 API Key\u3001\u8bf7\u6c42\u5730\u5740\u3001\u8d85\u65f6\u548c\u56db\u7c7b\u4efb\u52a1\u6a21\u578b\u7ed1\u5b9a\u3002",
        "primaryActionLabel": "\u4fdd\u5b58\u914d\u7f6e",
    },
    "hotkeys": {
        "title": "\u622a\u56fe\u70ed\u952e",
        "description": "\u622a\u56fe\u70ed\u952e\u4fdd\u5b58\u540e\u4f1a\u7acb\u5373\u91cd\u7ed1\uff0c\u65e0\u9700\u91cd\u542f\u5e94\u7528\u3002",
        "primaryActionLabel": "\u4fdd\u5b58\u914d\u7f6e",
    },
    "analysis_rules": {
        "title": "\u89c4\u5219\u4e0e Prompt \u8c03\u8bd5",
        "description": "\u6309\u573a\u666f\u7ef4\u62a4\u8bc6\u522b\u504f\u597d\uff0c\u5e76\u67e5\u770b\u6bcf\u6b21\u622a\u56fe\u5206\u6790\u7684\u5b8c\u6574 Prompt \u6784\u5efa\u7ed3\u679c\u3002",
        "primaryActionLabel": "\u4fdd\u5b58\u89c4\u5219",
    },
    "storage": {
        "title": "\u5b58\u50a8\u4e0e\u65e5\u5fd7",
        "description": "\u5feb\u901f\u6253\u5f00\u672c\u5730\u6570\u636e\u76ee\u5f55\uff0c\u5b9a\u4f4d\u914d\u7f6e\u3001\u53cd\u9988\u548c\u9519\u8bef\u65e5\u5fd7\u3002",
        "primaryActionLabel": "\u4fdd\u5b58\u76ee\u5f55",
    },
    "server": {
        "title": "\u670d\u52a1\u7aef\u96c6\u6210",
        "description": "\u7ef4\u62a4 Chattodo \u670d\u52a1\u7aef\u8fde\u63a5\u4fe1\u606f\uff0c\u540e\u7eed\u53ef\u7528\u4e8e\u529f\u80fd\u70b9\u63a8\u8350\u3001\u6570\u636e\u540c\u6b65\u7b49\u670d\u52a1\u7aef\u80fd\u529b\u3002",
        "primaryActionLabel": "\u4fdd\u5b58\u670d\u52a1\u914d\u7f6e",
    },
    "integrations": {
        "title": "\u811a\u672c\u96c6\u6210",
        "description": "\u5bfc\u5165\u672c\u5730\u811a\u672c\u5e76\u63a7\u5236\u542f\u7528\u72b6\u6001\uff0c\u4fdd\u5b58\u540e\u4f1a\u5199\u5165 integrations.json\u3002",
        "primaryActionLabel": "\u4fdd\u5b58\u914d\u7f6e",
    },
    "projects": {
        "title": "\u9879\u76ee\u7ba1\u7406",
        "description": "\u6279\u91cf\u5bfc\u5165\u9879\u76ee\u4e3b\u6570\u636e\uff0c\u5e76\u96c6\u4e2d\u7ef4\u62a4\u7fa4\u540d\u522b\u540d\u4e0e\u8f7b\u91cf\u8865\u5173\u8054\u3002",
        "primaryActionLabel": "\u8865\u5173\u8054\u5f85\u529e",
    },
    "tickets": {
        "title": "\u5de5\u5355\u7ba1\u7406",
        "description": "\u67e5\u770b\u6253\u5f00\u4e2d\u6216\u5df2\u5b8c\u6210\u7684\u5de5\u5355\uff0c\u5e76\u5728\u63a7\u5236\u9762\u677f\u5185\u67e5\u770b timeline \u5386\u53f2\u8ddf\u8fdb\u8be6\u60c5\u3002",
        "primaryActionLabel": "\u5237\u65b0\u5217\u8868",
    },
    "environments": {
        "title": "\u73af\u5883\u7ba1\u7406",
        "description": "\u5728\u540c\u4e00\u9875\u9762\u5207\u6362\u5168\u5c40\u73af\u5883\u4e0e\u9879\u76ee\u73af\u5883\uff0c\u9879\u76ee\u7ea7\u540c\u540d\u73af\u5883\u4f1a\u5728\u5f85\u529e\u8be6\u60c5\u4e2d\u8986\u76d6\u5168\u5c40\u7ed3\u679c\u3002",
        "primaryActionLabel": "\u5237\u65b0\u5217\u8868",
    },
}


def _required_capability(task_name: str) -> str:
    if task_name in {"context_summary", "plan_export"}:
        return "text_chat"
    return "vision_chat"


def _provider_payload(provider: ProviderConfig) -> dict[str, object]:
    return {
        "id": provider.id,
        "name": provider.name,
        "kind": provider.kind,
        "apiKey": provider.api_key,
        "baseUrl": provider.base_url,
        "timeoutSeconds": str(provider.timeout_seconds),
        "baseUrlEnabled": provider.kind == "openai_compatible",
    }


def _server_config_payload(config: object) -> dict[str, object]:
    return {
        "enabled": bool(getattr(config, "enabled", False)),
        "baseUrl": str(getattr(config, "base_url", "") or ""),
        "apiKey": str(getattr(config, "api_key", "") or ""),
        "timeoutSeconds": str(getattr(config, "timeout_seconds", 30) or 30),
    }


def _option_payload(value: str, text: str) -> dict[str, str]:
    return {
        "value": value,
        "text": text,
    }


def _model_option_payload(
    model: ProviderModelConfig,
    summary: ModelLatencySummary | None,
) -> dict[str, str]:
    details = ", ".join(model.capabilities)
    if summary is not None and not summary.is_empty:
        details = f"{details} · {summary.to_display_text()}" if details else summary.to_display_text()
    return {
        "value": model.id,
        "text": model.name,
        "details": details,
    }


def _normalize_model_text(value: str) -> str:
    return str(value or "").strip()


def _normalize_capabilities(value: str) -> list[str]:
    items = [item.strip() for item in str(value or "").split(",")]
    capabilities: list[str] = []
    for item in items:
        if item and item not in capabilities:
            capabilities.append(item)
    return capabilities


def _append_metric_suffix(label: str, summary: ModelLatencySummary | None) -> str:
    if summary is None or summary.is_empty:
        return label
    return f"{label} · {summary.to_display_text()}"


def _otp_import_payload(
    parsed: OtpSecretExtractResult,
    *,
    selected_path: str = "",
    preview_image_url: str = "",
    source: str = "",
) -> dict[str, object]:
    otp_config = str(parsed.raw_payload or parsed.secret or "").strip()
    return {
        "success": True,
        "otpConfig": otp_config,
        "secret": parsed.secret,
        "issuer": parsed.issuer,
        "account": parsed.account,
        "algorithm": parsed.algorithm,
        "digits": parsed.digits,
        "period": parsed.period,
        "label": parsed.label,
        "rawPayload": parsed.raw_payload,
        "selectedPath": selected_path,
        "previewImageUrl": preview_image_url,
        "source": source,
    }


def _preview_image_url(image_path: str) -> str:
    normalized = str(image_path or "").strip()
    if not normalized:
        return ""
    try:
        return Path(normalized).expanduser().resolve().as_uri()
    except ValueError:
        return ""


def _local_path_from_url_or_path(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("file:"):
        return QUrl(text).toLocalFile()
    return text


def _build_speed_hint(model_name: str, summary: ModelLatencySummary | None) -> str:
    if summary is None or summary.avg_latency_ms <= 10000:
        return ""
    lowered = str(model_name or "").lower()
    if "thinking" not in lowered and "reasoning" not in lowered:
        return ""
    return "该模型近期平均耗时偏长，更适合重质量场景；若更看重速度，可优先比较 Instruct/Flash 类模型。"


def _parse_project_date(value: str) -> QDate:
    text = str(value or "").strip().replace("/", "-")
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]
    parsed = QDate.fromString(text, "yyyy-MM-dd")
    return parsed if parsed.isValid() else QDate.currentDate()


def _serialize_project_date(field_name: str, selected_date: QDate) -> str:
    normalized_date = selected_date.toString("yyyy-MM-dd")
    if field_name == "supportEndedAt":
        return f"{normalized_date}T23:59:59"
    return f"{normalized_date}T00:00:00"


def _format_display_timestamp(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text).strftime("%m-%d %H:%M")
    except ValueError:
        return text


def _format_attachment_size(size_bytes: int) -> str:
    try:
        normalized = max(0, int(size_bytes))
    except (TypeError, ValueError):
        normalized = 0
    if normalized >= 1024 * 1024:
        return f"{normalized / (1024 * 1024):.1f} MB"
    if normalized >= 1024:
        return f"{normalized / 1024:.1f} KB"
    return f"{normalized} B"


def _todo_status_label(status: str) -> str:
    return "\u5df2\u5b8c\u6210" if str(status or "").strip() == TodoStatus.DONE else "\u8fdb\u884c\u4e2d"


def _todo_status_tone(status: str) -> str:
    return "done" if str(status or "").strip() == TodoStatus.DONE else "open"


def _ticket_field_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _format_ticket_product(product: object) -> str:
    value = _ticket_field_text(product).strip()
    if not value:
        return ""
    if value == "WPS协作":
        return "WPS协作（泛微）协作-私网"
    if value == "文档中台":
        return "文档中台/V7"
    if value == "文档中心":
        return "文档中心/V7"
    return value


def _format_ticket_project_name(project_name: object) -> str:
    if project_name is None:
        return ""
    if isinstance(project_name, list):
        return ",".join(str(item) for item in project_name)
    return str(project_name)


def _format_ticket_copy_text(ticket: dict[str, object]) -> str:
    return (
        f"标题: {_ticket_field_text(ticket.get('title'))}\n"
        "二线: 否\n"
        f"结论: {_ticket_field_text(ticket.get('conclusionContent'))}\n"
        f"客户名称: {_ticket_field_text(ticket.get('customerName'))}\n"
        f"项目名称: {_format_ticket_project_name(ticket.get('projectName'))}\n"
        f"功能点: {_ticket_field_text(ticket.get('featurePoint'))}\n"
        f"版本: {_ticket_field_text(ticket.get('ticketVersion'))}\n"
        f"根因分类: {_ticket_field_text(ticket.get('rootCause'))}\n"
        f"根因描述: {_ticket_field_text(ticket.get('rootCauseDesc'))}\n"
        f"产品: {_format_ticket_product(ticket.get('productLine'))}\n"
        f"描述: {_ticket_field_text(ticket.get('summary'))}"
    )


def _ticket_project_status_label(status: str) -> str:
    mapping = {
        "matched": "\u5df2\u5173\u8054\u9879\u76ee",
        "unmatched": "\u672a\u5339\u914d\u9879\u76ee",
        "conflict": "\u5339\u914d\u51b2\u7a81",
        "expired": "\u547d\u4e2d\u8fc7\u4fdd\u9879\u76ee",
        "manual": "\u624b\u52a8\u6307\u5b9a\u9879\u76ee",
    }
    return mapping.get(str(status or "").strip(), "\u672a\u5339\u914d\u9879\u76ee")


def _ticket_project_status_tone(status: str) -> str:
    mapping = {
        "matched": "matched",
        "manual": "matched",
        "conflict": "warning",
        "expired": "warning",
    }
    return mapping.get(str(status or "").strip(), "default")


def _ticket_project_status_detail(todo: TodoItem) -> str:
    link = todo.project_link
    status = str(link.match_status or "").strip()
    project_name = str(link.project_snapshot.get("project_name") or "").strip()
    task_order_no = str(link.project_snapshot.get("task_order_no") or "").strip()
    if status == "matched":
        if project_name and task_order_no:
            return f"{project_name} / {task_order_no}"
        return project_name or task_order_no or "\u5df2\u6839\u636e\u7fa4\u804a\u540d\u79f0\u547d\u4e2d\u9879\u76ee\u4e3b\u6570\u636e\u3002"
    if status == "conflict":
        reason = str(link.match_reason or "").strip()
        if reason.startswith("multiple_active_projects:"):
            return "\u547d\u4e2d\u4e86\u591a\u4e2a\u6709\u6548\u9879\u76ee\uff0c\u8bf7\u5728\u9879\u76ee\u7ba1\u7406\u9875\u6536\u655b\u522b\u540d\u3002"
        return reason or "\u5f53\u524d\u7fa4\u804a\u540d\u79f0\u547d\u4e2d\u4e86\u591a\u4e2a\u6709\u6548\u9879\u76ee\u3002"
    if status == "expired":
        return f"{project_name} \u5df2\u8fc7\u4fdd\u3002" if project_name else "\u5f53\u524d\u7fa4\u804a\u540d\u79f0\u53ea\u547d\u4e2d\u8fc7\u4fdd\u9879\u76ee\u3002"
    if status == "manual":
        return "\u5f53\u524d\u5de5\u5355\u4f7f\u7528\u4e86\u624b\u52a8\u9879\u76ee\u5173\u8054\u7ed3\u679c\u3002"
    reason = str(link.match_reason or "").strip()
    if reason == "missing_group_name":
        return "\u5f53\u524d\u5de5\u5355\u7f3a\u5c11\u7fa4\u804a\u540d\u79f0\uff0c\u65e0\u6cd5\u81ea\u52a8\u5339\u914d\u9879\u76ee\u3002"
    return "\u5f53\u524d\u7fa4\u804a\u540d\u79f0\u5c1a\u672a\u547d\u4e2d\u4efb\u4f55\u9879\u76ee\u522b\u540d\u3002"


def _ticket_timeline_scenario(kind: str, scenario: str) -> str:
    if str(kind or "").strip() == "manual":
        return "\u624b\u52a8\u8ddf\u8fdb"
    return str(scenario or "").strip() or "\u7cfb\u7edf\u8bb0\u5f55"


class _ControlPanelBridge(QObject):
    dataChanged = pyqtSignal()
    currentSectionChanged = pyqtSignal()
    windowStateChanged = pyqtSignal()
    todoListRefreshRequested = pyqtSignal()
    closeRequested = pyqtSignal()
    minimizeRequested = pyqtSignal()
    maximizeRequested = pyqtSignal()
    dragRequested = pyqtSignal()
    resizeRequested = pyqtSignal(str)
    configSaved = pyqtSignal(object)
    projectDateSelected = pyqtSignal(str, str)

    def __init__(
        self,
        config_manager: ConfigManager,
        *,
        notification_bridge: AppNotificationBridge | None = None,
    ) -> None:
        super().__init__()
        self._notification_bridge = notification_bridge or AppNotificationBridge()
        self._config_manager = config_manager
        self._config = config_manager.load()
        self._analysis_metrics = AnalysisMetricsStore()
        self._analysis_rules_manager = AnalysisRulesManager()
        self._analysis_rules = self._analysis_rules_manager.config
        self._prompt_debug_store = PromptDebugStore()
        self._integrations_path = integrations_file()
        self._integration_payload = load_integration_config(self._integrations_path)
        self._script_integrations = list_script_integrations(self._integration_payload)
        self._current_section = "models"
        self._selected_rule_scene = next(iter(self._analysis_rules.scene_rules), "")
        self._selected_prompt_debug_trace_id = ""
        self._capture_hotkey = self._config.hotkeys.capture
        self._max_image_megabytes = format_image_limit_megabytes(self._config.max_image_bytes)
        self._data_dir = str(app_data_dir())
        self._log_dir = str(log_dir())
        self._project_repository = SQLiteProjectRepository(aica_database_file())
        self._environment_repository = SQLiteProjectEnvironmentRepository(aica_database_file())
        self._environment_access_service = EnvironmentAccessService(self._environment_repository)
        self._todo_store = TodoStore(str(aica_database_file()))
        self._project_query = ""
        self._include_expired_projects = True
        self._projects = self._load_project_payloads()
        self._environment_scope_filter = "global"
        self._project_environment_project_id = ""
        self._project_environment_groups: list[dict[str, object]] = []
        self._global_environment_groups: list[dict[str, object]] = []
        self._selected_environment_id = ""
        self._selected_environment = self._empty_environment_detail_payload()
        self._last_project_import_summary = ""
        self._ticket_query = ""
        self._ticket_status_filter = TodoStatus.OPEN
        self._tickets = self._load_ticket_payloads()
        self._selected_ticket_id = ""
        self._selected_ticket = self._empty_ticket_detail_payload()
        self._error_message = ""
        self._status_message = ""
        self._last_notified_error_message = ""
        self._last_notified_status_message = ""
        self._window_maximized = False
        records = self._prompt_debug_store.list_records(limit=1)
        if records:
            self._selected_prompt_debug_trace_id = str(records[0].get("traceId", "")).strip()

    @property
    def notificationBridge(self) -> AppNotificationBridge:
        return self._notification_bridge

    @pyqtProperty("QVariantList", constant=True)
    def sections(self):  # noqa: ANN201
        return list(_SECTION_ITEMS)

    @pyqtProperty("QVariantList", constant=True)
    def sectionGroups(self):  # noqa: ANN201
        return list(_SECTION_GROUPS)

    @pyqtProperty(str, notify=currentSectionChanged)
    def currentSection(self) -> str:
        return self._current_section

    @pyqtProperty("QVariantMap", notify=currentSectionChanged)
    def currentSectionMeta(self):  # noqa: ANN201
        return dict(_SECTION_VIEW_META.get(self._current_section, _SECTION_VIEW_META["models"]))

    @pyqtProperty(bool, notify=windowStateChanged)
    def windowMaximized(self) -> bool:
        return self._window_maximized

    @pyqtProperty(str, constant=True)
    def uiFont(self) -> str:
        return RUNTIME_CAPABILITIES.ui_font

    @pyqtProperty(str, constant=True)
    def logoSource(self) -> str:
        return asset_file("aica_icon.png").as_uri()

    @pyqtProperty(str, constant=True)
    def refreshFeaturePointIconSource(self) -> str:
        return asset_file("feature-point-refresh.svg").as_uri()

    @pyqtProperty(str, constant=True)
    def integrationScriptFilter(self) -> str:
        return RUNTIME_CAPABILITIES.integration_script_filter

    @pyqtProperty(str, constant=True)
    def integrationScriptHelpText(self) -> str:
        if RUNTIME_CAPABILITIES.is_windows:
            return "支持 .py、.ps1、.bat、.cmd、.exe 文件，AICA 会按 ScriptEventHandler 配置调用。"
        return "支持 .py、.pyw、.sh 文件，Windows 环境建议优先使用可直接执行的脚本。"

    @pyqtProperty(str, constant=True)
    def hotkeyHelpText(self) -> str:
        if RUNTIME_CAPABILITIES.is_macos:
            return "例如 Command+Shift+A、Option+A、Control+Shift+F8，点击输入框后直接按下组合键。"
        return "例如 Alt+A、Ctrl+Shift+A，点击输入框后直接按下组合键。"

    @pyqtProperty(str, constant=True)
    def hotkeyPlaceholder(self) -> str:
        return RUNTIME_CAPABILITIES.default_capture_hotkey

    @pyqtProperty("QVariantList", notify=dataChanged)
    def providers(self):  # noqa: ANN201
        return [_provider_payload(provider) for provider in self._config.providers]

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def serverConfig(self):  # noqa: ANN201
        return _server_config_payload(self._config.server)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def taskBindings(self):  # noqa: ANN201
        payload = []
        for task_name, label in _TASK_LABELS.items():
            binding = getattr(self._config.task_model_bindings, task_name)
            summary = self._analysis_metrics.get_summary(task_name, binding.provider_id, binding.model_id)
            provider = self._find_provider(binding.provider_id)
            model_name = ""
            if provider is not None:
                model = next((item for item in provider.models if item.id == binding.model_id), None)
                model_name = model.name if model is not None else ""
            payload.append(
                {
                    "id": task_name,
                    "label": label,
                    "providerId": binding.provider_id,
                    "modelId": binding.model_id,
                    "performanceSummary": summary.to_display_text() if summary is not None else "暂无耗时样本",
                    "speedHint": _build_speed_hint(model_name, summary),
                    "providerOptions": [
                        _option_payload(provider.id, provider.name)
                        for provider in self._config.providers
                    ],
                    "modelOptions": self._build_model_options(task_name, binding.provider_id),
                }
            )
        return payload

    @pyqtProperty(str, notify=dataChanged)
    def captureHotkey(self) -> str:
        return self._capture_hotkey

    @pyqtProperty(str, notify=dataChanged)
    def maxImageMegabytes(self) -> str:
        return self._max_image_megabytes

    @pyqtProperty(str, notify=dataChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @pyqtProperty(bool, notify=dataChanged)
    def hasError(self) -> bool:
        return bool(self._error_message)

    @pyqtProperty(str, notify=dataChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @pyqtProperty(bool, notify=dataChanged)
    def hasStatus(self) -> bool:
        return bool(self._status_message)

    @pyqtProperty(str, notify=dataChanged)
    def dataDir(self) -> str:
        return self._data_dir

    @pyqtProperty(str, notify=dataChanged)
    def logDir(self) -> str:
        return self._log_dir

    @pyqtProperty(str, notify=dataChanged)
    def storageConfigPath(self) -> str:
        return str(storage_config_file())

    @pyqtProperty(str, notify=dataChanged)
    def configPath(self) -> str:
        return str(config_file())

    @pyqtProperty(str, notify=dataChanged)
    def todosPath(self) -> str:
        return str(aica_database_file())

    @pyqtProperty(str, notify=dataChanged)
    def integrationsPath(self) -> str:
        return str(self._integrations_path)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def integrationScripts(self):  # noqa: ANN201
        payload = []
        for integration in self._script_integrations:
            script_path = script_integration_display_path(integration)
            supported, support_message = describe_script_integration_support(integration)
            payload.append(
                {
                    "id": str(integration.get("id") or "").strip(),
                    "name": str(integration.get("name") or integration.get("id") or "未命名").strip(),
                    "enabled": bool(integration.get("enabled", True)),
                    "scriptPath": script_path,
                    "exists": bool(script_path) and Path(script_path).exists(),
                    "supported": supported,
                    "supportMessage": support_message,
                }
            )
        return payload

    @pyqtProperty("QVariantList", constant=True)
    def analysisRuleScenes(self):  # noqa: ANN201
        return build_scene_options_payload()

    @pyqtProperty("QVariantList", constant=True)
    def rootCauseOptions(self):  # noqa: ANN201
        return list(ROOT_CAUSE_OPTIONS)

    @pyqtProperty(str, notify=dataChanged)
    def selectedAnalysisRuleScene(self) -> str:
        return self._selected_rule_scene

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def analysisRuleForm(self):  # noqa: ANN201
        user_rules = list(self._analysis_rules.scene_rules.get(self._selected_rule_scene, UserRuleConfig()).items)
        if not user_rules:
            user_rules = [""]
        return {
            "userRules": user_rules,
            "sceneLabel": next(
                (
                    option.get("text", "")
                    for option in build_scene_options_payload()
                    if option.get("value", "") == self._selected_rule_scene
                ),
                "",
            ),
            "promptVersion": self._analysis_rules.version,
            "debugEnabled": self._analysis_rules.debug.enabled,
            "debugMaxRecords": str(self._analysis_rules.debug.max_records),
        }

    @pyqtProperty(str, notify=dataChanged)
    def analysisRulesPath(self) -> str:
        return str(analysis_rules_file())

    @pyqtProperty(str, notify=dataChanged)
    def promptDebugDirPath(self) -> str:
        return str(prompt_debug_dir())

    @pyqtProperty("QVariantList", notify=dataChanged)
    def promptDebugRecords(self):  # noqa: ANN201
        return self._prompt_debug_store.list_records(limit=60)

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def selectedPromptDebugRecord(self):  # noqa: ANN201
        payload = self._prompt_debug_store.load_record(self._selected_prompt_debug_trace_id)
        if payload is None:
            return {
                "trace_id": "",
                "scene_label": "",
                "timestamp": "",
                "model": "",
                "status": "",
                "timing_summary": "",
                "system_prompt": "",
                "user_prompt": "",
                "raw_response": "",
                "error_message": "",
                "context_text": "",
            }
        return payload

    @pyqtProperty("QVariantList", notify=dataChanged)
    def projects(self):  # noqa: ANN201
        return list(self._projects)

    @pyqtProperty(str, notify=dataChanged)
    def projectQuery(self) -> str:
        return self._project_query

    @pyqtProperty(bool, notify=dataChanged)
    def includeExpiredProjects(self) -> bool:
        return self._include_expired_projects

    @pyqtProperty(str, notify=dataChanged)
    def lastProjectImportSummary(self) -> str:
        return self._last_project_import_summary

    @pyqtProperty(str, notify=dataChanged)
    def environmentScopeFilter(self) -> str:
        return self._environment_scope_filter

    @pyqtProperty(str, notify=dataChanged)
    def projectEnvironmentProjectId(self) -> str:
        return self._project_environment_project_id

    @pyqtProperty("QVariantList", notify=dataChanged)
    def projectEnvironmentGroups(self):  # noqa: ANN201
        return list(self._project_environment_groups)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def globalEnvironmentGroups(self):  # noqa: ANN201
        return list(self._global_environment_groups)

    @pyqtProperty(str, notify=dataChanged)
    def selectedEnvironmentId(self) -> str:
        return self._selected_environment_id

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def selectedEnvironment(self):  # noqa: ANN201
        return dict(self._selected_environment)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def tickets(self):  # noqa: ANN201
        return list(self._tickets)

    @pyqtProperty(str, notify=dataChanged)
    def ticketQuery(self) -> str:
        return self._ticket_query

    @pyqtProperty(str, notify=dataChanged)
    def ticketStatusFilter(self) -> str:
        return self._ticket_status_filter

    @pyqtProperty("QVariantMap", notify=dataChanged)
    def selectedTicket(self):  # noqa: ANN201
        return dict(self._selected_ticket)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def locations(self):  # noqa: ANN201
        return [
            {
                "id": "data_dir",
                "title": "本地数据目录",
                "description": self._data_dir,
            },
            {
                "id": "knowledge_base_dir",
                "title": "知识库归档目录",
                "description": str(Path(self._data_dir).expanduser() / "knowledge_base"),
            },
            {
                "id": "feedback_dir",
                "title": "反馈目录",
                "description": str(feedback_dir()),
            },
            {
                "id": "analysis_rules_dir",
                "title": "分析规则文件",
                "description": str(analysis_rules_file()),
            },
            {
                "id": "prompt_debug_dir",
                "title": "Prompt 调试目录",
                "description": str(prompt_debug_dir()),
            },
            {
                "id": "error_log_dir",
                "title": "错误日志目录",
                "description": self._log_dir,
            },
            {
                "id": "integrations_dir",
                "title": "脚本集成配置目录",
                "description": str(self._integrations_path.parent),
            },
        ]

    def _build_model_options(self, task_name: str, provider_id: str) -> list[dict[str, str]]:
        provider = self._find_provider(provider_id)
        if provider is None:
            return []
        capability = _required_capability(task_name)
        options = [
            _model_option_payload(
                model,
                self._analysis_metrics.get_summary(task_name, provider.id, model.id),
            )
            for model in provider.models
            if capability in model.capabilities
        ]
        if options:
            return options
        return [
            _model_option_payload(
                model,
                self._analysis_metrics.get_summary(task_name, provider.id, model.id),
            )
            for model in provider.models
        ]

    def _find_provider(self, provider_id: str) -> ProviderConfig | None:
        return next((provider for provider in self._config.providers if provider.id == provider_id), None)

    def _find_provider_model(self, provider: ProviderConfig, model_text: str) -> ProviderModelConfig | None:
        normalized = _normalize_model_text(model_text)
        if not normalized:
            return None
        lowered = normalized.casefold()
        return next(
            (
                model
                for model in provider.models
                if model.id.casefold() == lowered or model.name.casefold() == lowered
            ),
            None,
        )

    def _ensure_provider_model(
        self,
        task_name: str,
        provider: ProviderConfig,
        model_text: str,
        capability_text: str = "",
    ) -> ProviderModelConfig | None:
        normalized = _normalize_model_text(model_text)
        if not normalized:
            return None
        existing = self._find_provider_model(provider, normalized)
        if existing is not None:
            return existing
        capability = _required_capability(task_name)
        capabilities = _normalize_capabilities(capability_text)
        if not capabilities:
            capabilities = [capability, "text_chat"]
        elif capability in capabilities and "text_chat" not in capabilities:
            capabilities.append("text_chat")
        model = ProviderModelConfig(
            id=normalized,
            name=normalized,
            capabilities=capabilities,
        )
        provider.models.append(model)
        return model

    def _clear_messages(self) -> None:
        self._error_message = ""
        self._status_message = ""
        self._last_notified_error_message = ""
        self._last_notified_status_message = ""

    def _emit_data_changed(self) -> None:
        if self._error_message and self._error_message != self._last_notified_error_message:
            self._notification_bridge.notify("error", self._error_message, source="control_panel")
            self._last_notified_error_message = self._error_message
        if self._status_message and self._status_message != self._last_notified_status_message:
            self._notification_bridge.notify("success", self._status_message, source="control_panel")
            self._last_notified_status_message = self._status_message
        self.dataChanged.emit()

    def _load_project_payloads(self) -> list[dict[str, object]]:
        return [
            project_to_payload(project)
            for project in self._project_repository.list_projects(
                query=self._project_query,
                include_expired=self._include_expired_projects,
            )
        ]

    def _refresh_project_payloads(self) -> None:
        self._projects = self._load_project_payloads()

    @staticmethod
    def _normalize_environment_scope_filter(value: str) -> str:
        return "project" if normalize_environment_scope(value, default="global") == "project" else "global"

    def _resolve_project_environment_project_id(self, project_id: str = "") -> str:
        explicit_id = str(project_id or "").strip()
        if explicit_id:
            return explicit_id
        normalized_id = str(self._project_environment_project_id or "").strip()
        if normalized_id and self._find_cached_project(normalized_id) is not None:
            return normalized_id
        if not self._projects:
            return ""
        first_project_id = str(self._projects[0].get("id") or "").strip()
        return first_project_id

    @staticmethod
    def _empty_environment_detail_payload() -> dict[str, object]:
        return {
            "id": "",
            "projectId": "",
            "name": "",
            "type": "",
            "note": "",
            "sortOrder": 0,
            "isActive": True,
            "scope": "global",
            "scopeLabel": "",
            "isGlobal": True,
            "isProjectOverride": False,
            "entryCount": 0,
            "entries": [],
        }

    @staticmethod
    def _environment_scope_label(scope: str) -> str:
        return "全局环境" if normalize_environment_scope(scope) == "global" else "项目环境"

    def _build_environment_entry_payload(self, entry: EnvironmentAccessEntryRecord) -> dict[str, object]:
        source_scope = normalize_environment_scope(entry.source_scope or entry.scope, default="project")
        return {
            "id": entry.id,
            "name": str(entry.access_name or "").strip(),
            "type": normalize_access_type(entry.access_type),
            "urlOrHost": str(entry.url_or_host or "").strip(),
            "username": str(entry.username or "").strip(),
            "note": str(entry.note or "").strip(),
            "sortOrder": int(entry.sort_order or 0),
            "isActive": bool(entry.is_active),
            "requiresOtp": bool(entry.requires_otp),
            "hasPassword": bool(str(entry.password_encrypted or "").strip()),
            "hasOtpConfig": bool(str(entry.otp_secret_encrypted or "").strip()),
            "scope": source_scope,
            "scopeLabel": self._environment_scope_label(source_scope),
            "isGlobal": source_scope == "global",
            "isProjectOverride": bool(entry.is_project_override),
        }

    def _build_environment_summary_payload(self, bundle: ProjectEnvironmentBundle) -> dict[str, object]:
        scope = normalize_environment_scope(bundle.environment.scope or bundle.source_scope, default="project")
        return {
            "id": bundle.environment.id,
            "projectId": str(bundle.environment.project_id or "").strip(),
            "name": str(bundle.environment.env_name or "").strip(),
            "type": str(bundle.environment.env_type or "").strip(),
            "note": str(bundle.environment.note or "").strip(),
            "sortOrder": int(bundle.environment.sort_order or 0),
            "isActive": bool(bundle.environment.is_active),
            "scope": scope,
            "scopeLabel": self._environment_scope_label(scope),
            "isGlobal": scope == "global",
            "isProjectOverride": bool(bundle.is_project_override),
            "entryCount": len(bundle.entries),
        }

    def _build_environment_detail_payload(self, bundle: ProjectEnvironmentBundle) -> dict[str, object]:
        payload = self._build_environment_summary_payload(bundle)
        payload["entries"] = [self._build_environment_entry_payload(entry) for entry in bundle.entries]
        return payload

    def _refresh_selected_environment_payload(self) -> None:
        normalized_id = str(self._selected_environment_id or "").strip()
        if not normalized_id:
            self._selected_environment = self._empty_environment_detail_payload()
            return
        environment, bundle = self._load_environment_bundle_for_edit(normalized_id)
        if environment is None or bundle is None:
            self._clear_selected_environment()
            return
        self._selected_environment = self._build_environment_detail_payload(bundle)

    def _clear_selected_environment(self) -> None:
        self._selected_environment_id = ""
        self._selected_environment = self._empty_environment_detail_payload()

    def _select_environment(self, environment_id: str) -> None:
        self._selected_environment_id = str(environment_id or "").strip()
        self._refresh_selected_environment_payload()

    def _selected_environment_matches_current_scope(self) -> bool:
        if not self._selected_environment_id:
            return False
        scope, payload = self._find_environment_group_payload(self._selected_environment_id)
        if payload is None:
            return False
        if scope != self._environment_scope_filter:
            return False
        if scope != "project":
            return True
        return str(payload.get("projectId") or "").strip() == str(self._project_environment_project_id or "").strip()

    def _sync_selected_environment_for_current_scope(self) -> None:
        if self._selected_environment_matches_current_scope():
            self._refresh_selected_environment_payload()
            return
        self._clear_selected_environment()

    def _refresh_project_environment_payloads(self, project_id: str) -> None:
        self._project_environment_project_id = self._resolve_project_environment_project_id(project_id)
        if not self._project_environment_project_id:
            self._project_environment_groups = []
            self._sync_selected_environment_for_current_scope()
            return
        bundles = self._environment_repository.list_project_environments(
            self._project_environment_project_id,
            include_inactive=True,
        )
        self._project_environment_groups = [self._build_environment_summary_payload(bundle) for bundle in bundles]
        self._sync_selected_environment_for_current_scope()

    def _refresh_global_environment_payloads(self) -> None:
        bundles = self._environment_repository.list_global_environments(include_inactive=True)
        self._global_environment_groups = [self._build_environment_summary_payload(bundle) for bundle in bundles]
        self._sync_selected_environment_for_current_scope()

    def _find_environment_group_payload(self, environment_id: str) -> tuple[str, dict[str, object] | None]:
        normalized_id = str(environment_id or "").strip()
        for item in self._project_environment_groups:
            if str(item.get("id") or "").strip() == normalized_id:
                return "project", item
        for item in self._global_environment_groups:
            if str(item.get("id") or "").strip() == normalized_id:
                return "global", item
        return "", None

    def _load_environment_bundle_for_edit(self, environment_id: str) -> tuple[ProjectEnvironmentRecord | None, ProjectEnvironmentBundle | None]:
        environment = self._environment_repository.get_project_environment(environment_id)
        if environment is None:
            return None, None
        if normalize_environment_scope(environment.scope) == "global":
            bundles = self._environment_repository.list_global_environments(include_inactive=True)
        else:
            bundles = self._environment_repository.list_project_environments(environment.project_id, include_inactive=True)
        bundle = next((item for item in bundles if item.environment.id == environment.id), None)
        return environment, bundle

    def _refresh_environment_scope_payloads(self, scope: str, project_id: str = "") -> None:
        normalized_scope = normalize_environment_scope(scope)
        if normalized_scope == "global":
            self._refresh_global_environment_payloads()
        else:
            self._refresh_project_environment_payloads(project_id or self._project_environment_project_id)

    def _refresh_current_environment_scope_payloads(self) -> None:
        if self._environment_scope_filter == "project":
            self._refresh_project_payloads()
            self._refresh_project_environment_payloads(self._project_environment_project_id)
            return
        self._refresh_global_environment_payloads()

    def _refresh_environment_lists_for_current_scope(self) -> None:
        if self._environment_scope_filter == "project":
            self._refresh_project_payloads()
            self._refresh_project_environment_payloads(self._project_environment_project_id)
            return
        self._refresh_global_environment_payloads()

    def _refresh_environment_scope_after_change(self, scope: str, project_id: str = "") -> None:
        normalized_scope = normalize_environment_scope(scope)
        if normalized_scope == "global":
            self._refresh_global_environment_payloads()
        else:
            self._refresh_project_environment_payloads(project_id or self._project_environment_project_id)
        self._select_environment(self._selected_environment_id)

    def _build_ticket_list_payload(self, todo: TodoItem) -> dict[str, object]:
        snapshot = todo.project_link.project_snapshot
        return {
            "id": todo.id,
            "title": str(todo.title or "").strip() or "\u672a\u5206\u7c7b\u4efb\u52a1",
            "summary": str(todo.current_summary or "").strip(),
            "groupName": str(todo.summary_fields.group_name or "").strip(),
            "environment": str(todo.summary_fields.environment or "").strip(),
            "productLine": str(todo.summary_fields.product_line or "").strip(),
            "ticketType": str(todo.summary_fields.ticket_type or "").strip(),
            "achNo": str(todo.summary_fields.ach_no or "").strip(),
            "achFilledAt": str(todo.summary_fields.ach_filled_at or "").strip(),
            "achFilledAtLabel": _format_display_timestamp(todo.summary_fields.ach_filled_at),
            "status": str(todo.status or TodoStatus.OPEN),
            "statusLabel": _todo_status_label(todo.status),
            "statusTone": _todo_status_tone(todo.status),
            "projectName": str(snapshot.get("project_name") or "").strip(),
            "taskOrderNo": str(snapshot.get("task_order_no") or "").strip(),
            "projectStatus": str(todo.project_link.match_status or "").strip(),
            "projectStatusLabel": _ticket_project_status_label(todo.project_link.match_status),
            "projectStatusTone": _ticket_project_status_tone(todo.project_link.match_status),
            "projectStatusDetail": _ticket_project_status_detail(todo),
            "completedAt": str(todo.completed_at or ""),
            "completedAtLabel": _format_display_timestamp(todo.completed_at),
            "updatedAt": str(todo.updated_at or ""),
            "updatedAtLabel": _format_display_timestamp(todo.updated_at),
            "timelineCount": len(todo.timeline),
        }

    def _build_ticket_detail_payload(self, todo: TodoItem) -> dict[str, object]:
        snapshot = todo.project_link.project_snapshot
        ticket_version = str(todo.summary_fields.ticket_version or "").strip()
        project_snapshot_version = str(snapshot.get("product_version") or "").strip()
        timeline_payload = []
        for event in reversed(todo.timeline):
            attachments = [
                {
                    "id": attachment.id,
                    "name": str(attachment.name or "").strip() or Path(str(attachment.path or "")).name,
                    "path": str(attachment.path or "").strip(),
                    "sizeBytes": int(attachment.size_bytes),
                    "sizeLabel": _format_attachment_size(attachment.size_bytes),
                }
                for attachment in event.attachments
            ]
            timeline_payload.append(
                {
                    "id": event.id,
                    "timestamp": event.timestamp,
                    "timestampLabel": _format_display_timestamp(event.timestamp),
                    "scenario": _ticket_timeline_scenario(event.kind, event.scenario),
                    "kind": str(event.kind or "").strip(),
                    "content": str(event.content or "").strip(),
                    "attachments": attachments,
                }
            )

        return {
            **self._build_ticket_list_payload(todo),
            "createdAt": str(todo.created_at or ""),
            "createdAtLabel": _format_display_timestamp(todo.created_at),
            "currentSummary": str(todo.current_summary or "").strip(),
            "conclusionContent": str(todo.conclusion.content or "").strip(),
            "featurePoint": str(todo.summary_fields.feature_point or "").strip(),
            "rootCauseDesc": str(todo.summary_fields.root_cause_desc or "").strip(),
            "rootCause": str(todo.summary_fields.root_cause or "").strip(),
            "achNo": str(todo.summary_fields.ach_no or "").strip(),
            "achFilledAt": str(todo.summary_fields.ach_filled_at or "").strip(),
            "achFilledAtLabel": _format_display_timestamp(todo.summary_fields.ach_filled_at),
            "projectLinkReason": str(todo.project_link.match_reason or "").strip(),
            "projectAlias": str(todo.project_link.matched_alias or "").strip(),
            "projectName": str(snapshot.get("project_name") or "").strip(),
            "customerName": str(snapshot.get("customer_name") or "").strip(),
            "taskOrderNo": str(snapshot.get("task_order_no") or "").strip(),
            "productLine": "" if is_unknown_text(todo.summary_fields.product_line) else str(todo.summary_fields.product_line or "").strip(),
            "ticketVersion": ticket_version,
            "projectSnapshotVersion": project_snapshot_version,
            "projectManager": str(snapshot.get("project_manager") or "").strip(),
            "timeline": timeline_payload,
        }

    def _empty_ticket_detail_payload(self) -> dict[str, object]:
        return {
            "id": "",
            "title": "",
            "summary": "",
            "currentSummary": "",
            "conclusionContent": "",
            "featurePoint": "",
            "rootCauseDesc": "",
            "rootCause": "",
            "groupName": "",
            "environment": "",
            "ticketType": "",
            "achNo": "",
            "achFilledAt": "",
            "achFilledAtLabel": "",
            "status": "",
            "statusLabel": "",
            "statusTone": "open",
            "projectStatus": "",
            "projectStatusLabel": "",
            "projectStatusTone": "default",
            "projectStatusDetail": "",
            "projectLinkReason": "",
            "projectAlias": "",
            "projectName": "",
            "customerName": "",
            "taskOrderNo": "",
            "productLine": "",
            "ticketVersion": "",
            "projectSnapshotVersion": "",
            "projectManager": "",
            "createdAt": "",
            "createdAtLabel": "",
            "completedAt": "",
            "completedAtLabel": "",
            "updatedAt": "",
            "updatedAtLabel": "",
            "timelineCount": 0,
            "timeline": [],
        }

    @staticmethod
    def _build_updated_ticket_summary_fields(todo: TodoItem, **overrides: object) -> TicketSummaryFields:
        payload = todo.summary_fields.to_dict()
        payload.update(overrides)
        return TicketSummaryFields.from_dict(payload)

    def _resolve_selected_ticket_for_update(self) -> TodoItem | None:
        if not self._selected_ticket_id:
            return None
        todo = self._todo_store.get_todo(self._selected_ticket_id)
        if todo is None:
            self._selected_ticket_id = ""
            self._selected_ticket = self._empty_ticket_detail_payload()
            self._error_message = "\u8be5\u5de5\u5355\u4e0d\u5b58\u5728\u6216\u5df2\u88ab\u5220\u9664\u3002"
            self._emit_data_changed()
            return None
        return todo

    def _apply_selected_ticket_update(self, todo: TodoItem, *, status_message: str) -> None:
        self._refresh_ticket_payloads()
        self._selected_ticket = self._build_ticket_detail_payload(todo)
        self._status_message = status_message
        self._emit_data_changed()
        self.todoListRefreshRequested.emit()

    def _load_ticket_payloads(self) -> list[dict[str, object]]:
        return [
            self._build_ticket_list_payload(todo)
            for todo in self._todo_store.list_todos(
                query=self._ticket_query,
                status=self._ticket_status_filter,
            )
        ]

    def _refresh_ticket_payloads(self) -> None:
        self._tickets = self._load_ticket_payloads()

    def _refresh_selected_ticket_payload(self) -> None:
        if not self._selected_ticket_id:
            self._selected_ticket = self._empty_ticket_detail_payload()
            return
        todo = self._todo_store.get_todo(self._selected_ticket_id)
        if todo is None:
            self._selected_ticket_id = ""
            self._selected_ticket = self._empty_ticket_detail_payload()
            return
        self._selected_ticket = self._build_ticket_detail_payload(todo)

    def _find_cached_project(self, project_id: str) -> dict[str, object] | None:
        normalized_id = str(project_id or "").strip()
        if not normalized_id:
            return None
        return next(
            (item for item in self._projects if str(item.get("id") or "").strip() == normalized_id),
            None,
        )

    @pyqtSlot(str)
    def setCurrentSection(self, section_id: str) -> None:
        section = str(section_id or "").strip()
        if section == "global_environments":
            self._environment_scope_filter = "global"
            section = "environments"
        elif section == "project_environments":
            self._environment_scope_filter = "project"
            section = "environments"
        if not section or section == self._current_section:
            if section == "environments":
                self._refresh_current_environment_scope_payloads()
                self.currentSectionChanged.emit()
                self._emit_data_changed()
            return
        if not any(item["id"] == section for item in _SECTION_ITEMS):
            return
        self._current_section = section
        if section == "environments":
            self._refresh_environment_lists_for_current_scope()
        self.currentSectionChanged.emit()
        self._emit_data_changed()

    @pyqtSlot()
    def reloadConfig(self) -> None:
        self._config_manager = ConfigManager()
        self._config = self._config_manager.load()
        self._analysis_rules = self._analysis_rules_manager.reload()
        self._integrations_path = integrations_file()
        self._integration_payload = load_integration_config(self._integrations_path)
        self._script_integrations = list_script_integrations(self._integration_payload)
        self._capture_hotkey = self._config.hotkeys.capture
        self._max_image_megabytes = format_image_limit_megabytes(self._config.max_image_bytes)
        self._data_dir = str(app_data_dir())
        self._log_dir = str(log_dir())
        self._project_repository = SQLiteProjectRepository(aica_database_file())
        self._environment_repository = SQLiteProjectEnvironmentRepository(aica_database_file())
        self._environment_access_service = EnvironmentAccessService(self._environment_repository)
        self._todo_store = TodoStore(str(aica_database_file()))
        self._refresh_project_payloads()
        if self._project_environment_project_id or self._environment_scope_filter == "project":
            self._refresh_project_environment_payloads(self._project_environment_project_id)
        else:
            self._project_environment_project_id = self._resolve_project_environment_project_id()
            self._project_environment_groups = []
        if self._current_section == "environments" or self._global_environment_groups:
            self._refresh_global_environment_payloads()
        self._refresh_selected_environment_payload()
        self._refresh_ticket_payloads()
        self._refresh_selected_ticket_payload()
        if self._selected_rule_scene not in self._analysis_rules.scene_rules:
            self._selected_rule_scene = next(iter(self._analysis_rules.scene_rules), "")
        if self._selected_prompt_debug_trace_id:
            if self._prompt_debug_store.load_record(self._selected_prompt_debug_trace_id) is None:
                self._selected_prompt_debug_trace_id = ""
        if not self._selected_prompt_debug_trace_id:
            records = self._prompt_debug_store.list_records(limit=1)
            if records:
                self._selected_prompt_debug_trace_id = str(records[0].get("traceId", "")).strip()
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str, str)
    def updateProviderField(self, provider_id: str, field_name: str, value: str) -> None:
        provider = self._find_provider(str(provider_id or "").strip())
        if provider is None:
            return
        if field_name == "api_key":
            provider.api_key = str(value or "").strip()
        elif field_name == "base_url":
            provider.base_url = str(value or "").strip()
        elif field_name == "timeout_seconds":
            provider.timeout_seconds = str(value or "").strip() or "0"  # type: ignore[assignment]
        else:
            return
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str)
    def updateServerField(self, field_name: str, value: str) -> None:
        normalized = str(field_name or "").strip()
        if normalized == "enabled":
            self._config.server.enabled = str(value or "").strip().lower() in {"1", "true", "yes", "on"}
        elif normalized == "base_url":
            self._config.server.base_url = str(value or "").strip()
        elif normalized == "api_key":
            self._config.server.api_key = str(value or "").strip()
        elif normalized == "timeout_seconds":
            self._config.server.timeout_seconds = str(value or "").strip() or "0"  # type: ignore[assignment]
        else:
            return
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str)
    def updateTaskBindingProvider(self, task_name: str, provider_id: str) -> None:
        provider = self._find_provider(str(provider_id or "").strip())
        if provider is None:
            return
        binding = getattr(self._config.task_model_bindings, task_name, None)
        if not isinstance(binding, TaskModelBinding):
            return
        binding.provider_id = provider.id
        model_options = self._build_model_options(task_name, provider.id)
        binding.model_id = model_options[0]["value"] if model_options else ""
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str)
    def updateTaskBindingModel(self, task_name: str, model_id: str) -> None:
        binding = getattr(self._config.task_model_bindings, task_name, None)
        if not isinstance(binding, TaskModelBinding):
            return
        binding.model_id = str(model_id or "").strip()
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str, str)
    def addOrSelectTaskBindingModel(self, task_name: str, model_text: str, capability_text: str) -> None:
        binding = getattr(self._config.task_model_bindings, task_name, None)
        if not isinstance(binding, TaskModelBinding):
            return
        provider = self._find_provider(binding.provider_id)
        if provider is None:
            return
        required_capability = _required_capability(task_name)
        model = self._ensure_provider_model(task_name, provider, model_text, capability_text)
        if model is None:
            return
        self._clear_messages()
        if required_capability in model.capabilities:
            binding.model_id = model.id
        else:
            self._status_message = (
                f"模型 {model.name} 不支持 {required_capability} 能力，已保留当前选择"
            )
        self._emit_data_changed()

    @pyqtSlot(str)
    def updateCaptureHotkey(self, value: str) -> None:
        self._capture_hotkey = str(value or "")
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(int, int, str, result=bool)
    def captureHotkeyFromKeyEvent(self, key: int, modifiers: int, text: str) -> bool:
        try:
            hotkey = hotkey_from_qt_key_event(key, modifiers, text)
        except ValueError as exc:
            self._error_message = str(exc)
            self._status_message = ""
            self._emit_data_changed()
            return False
        if not hotkey:
            return False
        self._capture_hotkey = hotkey
        self._clear_messages()
        self._emit_data_changed()
        return True

    @pyqtSlot(str)
    def updateMaxImageMegabytes(self, value: str) -> None:
        self._max_image_megabytes = str(value or "")
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def updateDataDir(self, value: str) -> None:
        self._data_dir = str(value or "")
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def updateLogDir(self, value: str) -> None:
        self._log_dir = str(value or "")
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def chooseStorageDir(self, target_name: str) -> None:
        normalized_target = str(target_name or "").strip()
        current_value = self._data_dir if normalized_target == "data_dir" else self._log_dir
        start_dir = current_value.strip() or str(app_data_dir())
        selected_path = QFileDialog.getExistingDirectory(
            None,
            "选择目录",
            start_dir,
        )
        if not selected_path:
            return
        if normalized_target == "data_dir":
            self._data_dir = selected_path
        elif normalized_target == "log_dir":
            self._log_dir = selected_path
        else:
            return
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def openLocation(self, location_id: str) -> None:
        mapping = {
            "data_dir": app_data_dir(),
            "knowledge_base_dir": Path(self._data_dir).expanduser() / "knowledge_base",
            "feedback_dir": feedback_dir(),
            "analysis_rules_dir": analysis_rules_file().parent,
            "prompt_debug_dir": prompt_debug_dir(),
            "error_log_dir": error_log_file().parent,
            "integrations_dir": self._integrations_path.parent,
        }
        target = mapping.get(str(location_id or "").strip())
        if target is None:
            return
        target.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    @pyqtSlot()
    def closePanel(self) -> None:
        self.closeRequested.emit()

    @pyqtSlot()
    def minimizePanel(self) -> None:
        self.minimizeRequested.emit()

    @pyqtSlot()
    def toggleMaximizedPanel(self) -> None:
        self.maximizeRequested.emit()

    @pyqtSlot(bool)
    def setWindowMaximized(self, value: bool) -> None:
        normalized = bool(value)
        if self._window_maximized == normalized:
            return
        self._window_maximized = normalized
        self.windowStateChanged.emit()

    @pyqtSlot()
    def startWindowDrag(self) -> None:
        self.dragRequested.emit()

    @pyqtSlot(str)
    def startWindowResize(self, edge: str) -> None:
        self.resizeRequested.emit(str(edge or "").strip())

    @pyqtSlot()
    def saveCurrentSection(self) -> None:
        if self._current_section == "analysis_rules":
            self.saveAnalysisRules()
            return
        if self._current_section == "integrations":
            self.saveIntegrations()
            return
        if self._current_section == "storage":
            self.saveStoragePaths()
            return
        if self._current_section == "projects":
            self.relinkOpenUnresolvedTodos()
            return
        if self._current_section == "environments":
            self._clear_messages()
            self._refresh_current_environment_scope_payloads()
            self._emit_data_changed()
            return
        if self._current_section == "tickets":
            self.refreshTickets()
            return
        self.saveConfig()

    @pyqtSlot(str)
    def setEnvironmentScopeFilter(self, scope: str) -> None:
        normalized_scope = self._normalize_environment_scope_filter(scope)
        if self._environment_scope_filter == normalized_scope:
            return
        self._environment_scope_filter = normalized_scope
        self._clear_selected_environment()
        self._clear_messages()
        if self._current_section == "environments":
            self._refresh_current_environment_scope_payloads()
        self._emit_data_changed()

    @pyqtSlot()
    def saveStoragePaths(self) -> None:
        self._clear_messages()
        try:
            previous_data_dir = str(app_data_dir())
            previous_log_dir = str(log_dir())
            result = persist_storage_paths(
                data_dir=normalize_directory_path(self._data_dir),
                log_dir=normalize_directory_path(self._log_dir),
                previous_data_dir=previous_data_dir,
                previous_log_dir=previous_log_dir,
            )
        except ValueError as exc:
            self._error_message = str(exc)
            self._emit_data_changed()
            return

        self._data_dir = result["data_dir"]
        self._log_dir = result["log_dir"]
        self.reloadConfig()
        self._status_message = "存储目录已保存，配置与数据已重新加载"
        self._emit_data_changed()

    @pyqtSlot(str)
    def setSelectedAnalysisRuleScene(self, scene_type: str) -> None:
        normalized = str(scene_type or "").strip()
        if not normalized or normalized not in self._analysis_rules.scene_rules:
            return
        self._selected_rule_scene = normalized
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str)
    def updateAnalysisRuleField(self, field_name: str, value: str) -> None:
        rule = self._analysis_rules.scenes.get(self._selected_rule_scene, SceneAnalysisRule())
        normalized = str(field_name or "").strip()
        text = str(value or "").strip()
        if normalized == "titlePreference":
            rule.title_preference = text
        elif normalized == "summaryPreference":
            rule.summary_preference = text
        elif normalized == "timelinePreference":
            rule.timeline_preference = text
        elif normalized == "mustInclude":
            rule.must_include = text
        elif normalized == "mustAvoid":
            rule.must_avoid = text
        elif normalized == "extraInstructions":
            rule.extra_instructions = text
        else:
            return
        self._analysis_rules.scenes[self._selected_rule_scene] = rule
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(int, str)
    def updateAnalysisUserRule(self, index: int, value: str) -> None:
        normalized_index = max(0, int(index))
        items = list(self._analysis_rules.scene_rules.get(self._selected_rule_scene, UserRuleConfig()).items)
        while len(items) <= normalized_index:
            items.append("")
        items[normalized_index] = str(value or "").strip()
        self._analysis_rules.scene_rules[self._selected_rule_scene] = UserRuleConfig.from_items(items)

    @pyqtSlot()
    def addAnalysisUserRule(self) -> None:
        items = list(self._analysis_rules.scene_rules.get(self._selected_rule_scene, UserRuleConfig()).items)
        items.append("")
        self._analysis_rules.scene_rules[self._selected_rule_scene] = UserRuleConfig.from_items(items)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(int)
    def removeAnalysisUserRule(self, index: int) -> None:
        normalized_index = int(index)
        items = list(self._analysis_rules.scene_rules.get(self._selected_rule_scene, UserRuleConfig()).items)
        if normalized_index < 0 or normalized_index >= len(items):
            return
        items.pop(normalized_index)
        self._analysis_rules.scene_rules[self._selected_rule_scene] = UserRuleConfig.from_items(items)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(bool)
    def updateAnalysisDebugEnabled(self, enabled: bool) -> None:
        self._analysis_rules.debug.enabled = bool(enabled)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def updateAnalysisDebugMaxRecords(self, value: str) -> None:
        try:
            parsed = int(str(value or "100").strip() or "100")
        except ValueError:
            parsed = 100
        self._analysis_rules.debug.max_records = max(1, parsed)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot()
    def saveAnalysisRules(self) -> None:
        self._clear_messages()
        try:
            self._analysis_rules.debug.max_records = max(1, int(self._analysis_rules.debug.max_records))
        except (TypeError, ValueError):
            self._error_message = "调试记录保留条数必须是正整数"
            self._emit_data_changed()
            return
        self._analysis_rules_manager.update_debug_config(
            enabled=self._analysis_rules.debug.enabled,
            max_records=self._analysis_rules.debug.max_records,
        )
        for scene_type, rules in self._analysis_rules.scene_rules.items():
            self._analysis_rules_manager.update_scene_user_rules(scene_type, rules)
        for scene_type, rule in self._analysis_rules.scenes.items():
            self._analysis_rules_manager.update_scene_rule(scene_type, rule)
        self._analysis_rules = self._analysis_rules_manager.save()
        self._status_message = "分析规则已保存"
        self._emit_data_changed()

    @pyqtSlot(str)
    def selectPromptDebugRecord(self, trace_id: str) -> None:
        self._selected_prompt_debug_trace_id = str(trace_id or "").strip()
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot()
    def refreshPromptDebugRecords(self) -> None:
        records = self._prompt_debug_store.list_records(limit=60)
        if records and not self._selected_prompt_debug_trace_id:
            self._selected_prompt_debug_trace_id = str(records[0].get("traceId", "")).strip()
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def copyPromptDebugField(self, field_name: str) -> None:
        payload = self._prompt_debug_store.load_record(self._selected_prompt_debug_trace_id)
        if payload is None:
            return
        field_value = str(payload.get(str(field_name or "").strip(), "")).strip()
        QApplication.clipboard().setText(field_value)
        self._status_message = "字段内容已复制"
        self._emit_data_changed()

    @pyqtSlot()
    def saveConfig(self) -> None:
        self._clear_messages()
        try:
            self._coerce_provider_timeouts()
            self._coerce_server_timeout()
            self._config = persist_control_panel_config(
                self._config_manager,
                self._config,
                capture_hotkey=self._capture_hotkey,
                max_image_megabytes=self._max_image_megabytes,
            )
        except ValueError as exc:
            self._error_message = str(exc)
            self._emit_data_changed()
            return

        self._capture_hotkey = self._config.hotkeys.capture
        self._max_image_megabytes = format_image_limit_megabytes(self._config.max_image_bytes)
        self._status_message = "配置已保存"
        self._emit_data_changed()
        self.configSaved.emit(self._config)

    @pyqtSlot()
    def saveIntegrations(self) -> None:
        self._clear_messages()
        self._integration_payload = replace_script_integrations(
            self._integration_payload,
            self._script_integrations,
        )
        save_integration_config(self._integrations_path, self._integration_payload)
        self._status_message = "脚本集成已保存"
        self._emit_data_changed()

    @pyqtSlot()
    def addIntegrationScript(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            None,
            "选择外部脚本",
            str(app_data_dir()),
            self.integrationScriptFilter,
        )
        if not selected_path:
            return
        existing_ids = {
            str(item.get("id") or "").strip()
            for item in self._script_integrations
            if str(item.get("id") or "").strip()
        }
        try:
            integration = build_script_integration(selected_path, existing_ids)
        except ValueError as exc:
            self._error_message = str(exc)
            self._status_message = ""
            self._emit_data_changed()
            return
        self._script_integrations.append(integration)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def chooseIntegrationScript(self, integration_id: str) -> None:
        target_id = str(integration_id or "").strip()
        integration = self._find_script_integration(target_id)
        if integration is None:
            return
        current_path = script_integration_display_path(integration)
        start_dir = str(Path(current_path).parent) if current_path else str(app_data_dir())
        selected_path, _ = QFileDialog.getOpenFileName(
            None,
            "选择外部脚本",
            start_dir,
            self.integrationScriptFilter,
        )
        if not selected_path:
            return
        try:
            updated = update_script_integration_path(integration, selected_path)
        except ValueError as exc:
            self._error_message = str(exc)
            self._status_message = ""
            self._emit_data_changed()
            return
        self._replace_script_integration(target_id, updated)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, bool)
    def setIntegrationEnabled(self, integration_id: str, enabled: bool) -> None:
        integration = self._find_script_integration(str(integration_id or "").strip())
        if integration is None:
            return
        integration["enabled"] = bool(enabled)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def removeIntegrationScript(self, integration_id: str) -> None:
        target_id = str(integration_id or "").strip()
        self._script_integrations = [
            item
            for item in self._script_integrations
            if str(item.get("id") or "").strip() != target_id
        ]
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot()
    def chooseProjectImportFile(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            None,
            "选择项目文件",
            str(app_data_dir()),
            "项目文件 (*.csv *.xlsx);;所有文件 (*.*)",
        )
        if selected_path:
            self.importProjectFile(selected_path)

    @pyqtSlot(str)
    def importProjectFile(self, path: str) -> None:
        self._clear_messages()
        try:
            result = import_projects_from_file(path, self._project_repository, self._todo_store)
        except ValueError as exc:
            self._error_message = str(exc)
            self._emit_data_changed()
            return
        self._refresh_project_payloads()
        self._last_project_import_summary = (
            f"新增 {result.created_count} 个，更新 {result.updated_count} 个，"
            f"跳过 {result.skipped_count} 个，关联 {result.relinked_count} 个"
        )
        if result.alias_conflicts or result.error_rows:
            fragments = [self._last_project_import_summary]
            if result.alias_conflicts:
                first_conflict = result.alias_conflicts[0]
                fragments.append(
                    "别名冲突："
                    f"第 {first_conflict.row_number} 行，别名 {first_conflict.alias} "
                    f"已被 {first_conflict.conflicting_project_name}"
                    f"({first_conflict.conflicting_task_order_no}) 使用"
                )
            if result.error_rows:
                first_error = result.error_rows[0]
                fragments.append(f"错误示例：第 {first_error['rowNumber']} 行，{first_error['message']}")
            self._status_message = " ".join(fragments)
        else:
            self._status_message = self._last_project_import_summary
        self._emit_data_changed()

    @pyqtSlot()
    def downloadProjectTemplate(self) -> None:
        selected_path, _ = QFileDialog.getSaveFileName(
            None,
            "保存项目导入模板",
            str(app_data_dir() / "project_import_template.csv"),
            "CSV 文件 (*.csv)",
        )
        if not selected_path:
            return
        target = Path(selected_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(build_project_template_content(), encoding="utf-8-sig")
        self._clear_messages()
        self._status_message = f"项目导入模板已保存到 {target}"
        self._emit_data_changed()

    @pyqtSlot(str, bool)
    def listProjects(self, query: str, include_expired: bool) -> None:
        self._project_query = str(query or "").strip()
        self._include_expired_projects = bool(include_expired)
        self._refresh_project_payloads()
        self._emit_data_changed()

    @pyqtSlot(str)
    def listProjectEnvironments(self, project_id: str) -> None:
        self._refresh_project_environment_payloads(project_id)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot()
    def listGlobalEnvironments(self) -> None:
        self._refresh_global_environment_payloads()
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def openEnvironmentDetail(self, environment_id: str) -> None:
        self._clear_messages()
        environment = self._environment_repository.get_project_environment(environment_id)
        if environment is not None:
            self._environment_scope_filter = self._normalize_environment_scope_filter(environment.scope)
            if normalize_environment_scope(environment.scope) == "project":
                self._project_environment_project_id = str(environment.project_id or "").strip()
        self._select_environment(environment_id)
        self._emit_data_changed()

    @pyqtSlot()
    def closeEnvironmentDetail(self) -> None:
        self._clear_messages()
        self._clear_selected_environment()
        self._emit_data_changed()

    @pyqtSlot(str, "QVariantMap")
    def saveProjectEnvironment(self, project_id: str, payload: object) -> None:
        normalized_project_id = str(project_id or "").strip()
        if not isinstance(payload, dict) or not normalized_project_id:
            return
        env_name = str(payload.get("name") or "").strip()
        if not env_name:
            self._error_message = "环境名称不能为空"
            self._emit_data_changed()
            return
        self._clear_messages()
        record = ProjectEnvironmentRecord(
            id=str(payload.get("id") or "").strip(),
            project_id=normalized_project_id,
            env_name=env_name,
            scope="project",
            env_type=str(payload.get("type") or "").strip(),
            sort_order=int(payload.get("sortOrder") or 0),
            is_active=bool(payload.get("isActive", True)),
            note=str(payload.get("note") or "").strip(),
        )
        saved = self._environment_repository.upsert_project_environment(record)
        self._select_environment(saved.id)
        self._refresh_environment_scope_after_change(saved.scope, saved.project_id)
        self._status_message = f"项目环境已保存：{saved.env_name}"
        self._emit_data_changed()

    @pyqtSlot("QVariantMap")
    def saveGlobalEnvironment(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        env_name = str(payload.get("name") or "").strip()
        if not env_name:
            self._error_message = "环境名称不能为空"
            self._emit_data_changed()
            return
        self._clear_messages()
        record = ProjectEnvironmentRecord(
            id=str(payload.get("id") or "").strip(),
            project_id="",
            env_name=env_name,
            scope="global",
            env_type=str(payload.get("type") or "").strip(),
            sort_order=int(payload.get("sortOrder") or 0),
            is_active=bool(payload.get("isActive", True)),
            note=str(payload.get("note") or "").strip(),
        )
        saved = self._environment_repository.upsert_project_environment(record)
        self._select_environment(saved.id)
        self._refresh_environment_scope_after_change(saved.scope, saved.project_id)
        self._status_message = f"全局环境已保存：{saved.env_name}"
        self._emit_data_changed()

    @pyqtSlot(str)
    def deleteProjectEnvironment(self, environment_id: str) -> None:
        environment = self._environment_repository.get_project_environment(environment_id)
        if environment is None or normalize_environment_scope(environment.scope) != "project":
            return
        self._clear_messages()
        deleted = self._environment_repository.delete_project_environment(environment.id)
        if not deleted:
            self._error_message = "删除项目环境失败"
            self._emit_data_changed()
            return
        if self._selected_environment_id == environment.id:
            self._clear_selected_environment()
        self._refresh_project_environment_payloads(environment.project_id)
        self._status_message = f"项目环境已删除：{environment.env_name}"
        self._emit_data_changed()

    @pyqtSlot(str)
    def deleteGlobalEnvironment(self, environment_id: str) -> None:
        environment = self._environment_repository.get_project_environment(environment_id)
        if environment is None or normalize_environment_scope(environment.scope) != "global":
            return
        self._clear_messages()
        deleted = self._environment_repository.delete_project_environment(environment.id)
        if not deleted:
            self._error_message = "删除全局环境失败"
            self._emit_data_changed()
            return
        if self._selected_environment_id == environment.id:
            self._clear_selected_environment()
        self._refresh_global_environment_payloads()
        self._status_message = f"全局环境已删除：{environment.env_name}"
        self._emit_data_changed()

    def _save_environment_access_entry(self, environment_id: str, payload: object, *, expected_scope: str) -> None:
        if not isinstance(payload, dict):
            return
        environment, bundle = self._load_environment_bundle_for_edit(environment_id)
        if environment is None or bundle is None:
            self._error_message = "未找到环境配置"
            self._emit_data_changed()
            return
        actual_scope = normalize_environment_scope(environment.scope)
        if actual_scope != normalize_environment_scope(expected_scope):
            return
        access_name = str(payload.get("name") or "").strip()
        if not access_name:
            self._error_message = "访问项名称不能为空"
            self._emit_data_changed()
            return
        self._clear_messages()
        existing_entry = self._environment_repository.get_access_entry(str(payload.get("id") or "").strip())
        password_text = str(payload.get("password") or "")
        otp_config_text = str(payload.get("otpConfig") or "")
        clear_password = bool(payload.get("clearPassword", False))
        clear_otp_config = bool(payload.get("clearOtpConfig", False))
        if password_text.strip():
            password_encrypted = self._environment_access_service.encrypt_secret(password_text.strip())
        elif clear_password:
            password_encrypted = ""
        else:
            password_encrypted = str(existing_entry.password_encrypted or "") if existing_entry is not None else ""
        if otp_config_text.strip():
            otp_secret_encrypted = self._environment_access_service.encrypt_secret(otp_config_text.strip())
        elif clear_otp_config:
            otp_secret_encrypted = ""
        else:
            otp_secret_encrypted = str(existing_entry.otp_secret_encrypted or "") if existing_entry is not None else ""
        target_id = str(payload.get("id") or "").strip()
        next_entry = EnvironmentAccessEntryRecord(
            id=target_id,
            environment_id=environment.id,
            access_name=access_name,
            scope=actual_scope,
            source_scope=actual_scope,
            access_type=normalize_access_type(payload.get("type")),
            url_or_host=str(payload.get("urlOrHost") or "").strip(),
            username=str(payload.get("username") or "").strip(),
            password_encrypted=password_encrypted,
            otp_secret_encrypted=otp_secret_encrypted,
            requires_otp=bool(payload.get("requiresOtp", False)),
            note=str(payload.get("note") or "").strip(),
            open_command=(
                str(payload.get("openCommand") or "").strip()
                if "openCommand" in payload
                else (str(existing_entry.open_command or "") if existing_entry is not None else "")
            ),
            sort_order=int(payload.get("sortOrder") or 0),
            is_active=bool(payload.get("isActive", True)),
        )
        existing_entries = list(bundle.entries)
        saved_entries: list[EnvironmentAccessEntryRecord] = []
        replaced = False
        for entry in existing_entries:
            if target_id and entry.id == target_id:
                saved_entries.append(next_entry)
                replaced = True
            else:
                saved_entries.append(entry)
        if not replaced:
            saved_entries.append(next_entry)
        self._environment_repository.replace_access_entries(environment.id, saved_entries)
        self._refresh_environment_scope_payloads(actual_scope, environment.project_id)
        self._status_message = f"访问项已保存：{access_name}"
        self._emit_data_changed()

    @pyqtSlot(str, "QVariantMap")
    def saveProjectEnvironmentAccessEntry(self, environment_id: str, payload: object) -> None:
        self._save_environment_access_entry(environment_id, payload, expected_scope="project")

    @pyqtSlot(str, "QVariantMap")
    def saveGlobalEnvironmentAccessEntry(self, environment_id: str, payload: object) -> None:
        self._save_environment_access_entry(environment_id, payload, expected_scope="global")

    def _delete_environment_access_entry(self, entry_id: str, *, expected_scope: str) -> None:
        existing_entry = self._environment_repository.get_access_entry(entry_id)
        if existing_entry is None:
            return
        environment, bundle = self._load_environment_bundle_for_edit(existing_entry.environment_id)
        if environment is None or bundle is None:
            return
        actual_scope = normalize_environment_scope(environment.scope)
        if actual_scope != normalize_environment_scope(expected_scope):
            return
        self._clear_messages()
        next_entries = [entry for entry in bundle.entries if entry.id != existing_entry.id]
        self._environment_repository.replace_access_entries(environment.id, next_entries)
        self._refresh_environment_scope_payloads(actual_scope, environment.project_id)
        self._status_message = f"访问项已删除：{existing_entry.access_name}"
        self._emit_data_changed()

    @pyqtSlot(str)
    def deleteProjectEnvironmentAccessEntry(self, entry_id: str) -> None:
        self._delete_environment_access_entry(entry_id, expected_scope="project")

    @pyqtSlot(str)
    def deleteGlobalEnvironmentAccessEntry(self, entry_id: str) -> None:
        self._delete_environment_access_entry(entry_id, expected_scope="global")

    @pyqtSlot("QVariantMap", result="QVariantMap")
    def importOtpConfigFromQrImage(self, payload_context: object):  # noqa: ANN201
        start_dir = str(app_data_dir())
        if isinstance(payload_context, dict):
            initial_dir = str(payload_context.get("initialDir") or "").strip()
            if initial_dir:
                start_dir = initial_dir
        selected_path, _ = QFileDialog.getOpenFileName(
            None,
            "选择 OTP 二维码图片",
            start_dir,
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*.*)",
        )
        if not selected_path:
            return {"success": False, "canceled": True}
        return self._import_otp_config_from_qr_image_path(selected_path, source="file_dialog")

    @pyqtSlot(str, result="QVariantMap")
    def importOtpConfigFromQrImagePath(self, image_path: str):  # noqa: ANN201
        normalized_path = _local_path_from_url_or_path(image_path)
        if not normalized_path:
            return {"success": False, "error": "未找到二维码图片路径"}
        return self._import_otp_config_from_qr_image_path(normalized_path, source="drop")

    @pyqtSlot(result="QVariantMap")
    def importOtpConfigFromClipboardQr(self):  # noqa: ANN201
        self._clear_messages()
        clipboard = QApplication.clipboard()
        try:
            image = clipboard.image()
        except Exception:  # noqa: BLE001
            image = None
        if image is not None and not bool(getattr(image, "isNull", lambda: True)()):
            try:
                return self._import_otp_config_from_clipboard_image(image)
            except Exception as exc:  # noqa: BLE001
                self._error_message = f"剪贴板二维码导入失败：{exc}"
                self._emit_data_changed()
                return {"success": False, "error": str(exc)}

        mime_data = clipboard.mimeData() if hasattr(clipboard, "mimeData") else None
        if mime_data is not None and getattr(mime_data, "hasUrls", lambda: False)():
            for item in mime_data.urls():
                normalized_path = _local_path_from_url_or_path(item.toString() if hasattr(item, "toString") else item)
                if normalized_path:
                    return self._import_otp_config_from_qr_image_path(normalized_path, source="clipboard_url")

        text = str(clipboard.text() if hasattr(clipboard, "text") else "").strip()
        if text:
            image_path = _local_path_from_url_or_path(text)
            if Path(image_path).expanduser().is_file():
                return self._import_otp_config_from_qr_image_path(image_path, source="clipboard_path")
            try:
                parsed = parse_otpauth_payload(text)
            except Exception as exc:  # noqa: BLE001
                self._error_message = f"剪贴板内容不是有效的 OTP 二维码或配置：{exc}"
                self._emit_data_changed()
                return {"success": False, "error": str(exc)}
            self._status_message = "OTP 配置已从剪贴板导入"
            self._emit_data_changed()
            return _otp_import_payload(parsed, source="clipboard_text")

        self._error_message = "剪贴板中未找到二维码图片、图片路径或 OTP 配置"
        self._emit_data_changed()
        return {"success": False, "error": self._error_message}

    def _import_otp_config_from_clipboard_image(self, image: object) -> dict[str, object]:
        temp_file = tempfile.NamedTemporaryFile(prefix="aica_otp_qr_", suffix=".png", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()
        saved = image.save(str(temp_path), "PNG")
        if saved is False:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise RuntimeError("剪贴板图片保存失败")
        return self._import_otp_config_from_qr_image_path(str(temp_path), source="clipboard_image")

    def _import_otp_config_from_qr_image_path(self, image_path: str, *, source: str) -> dict[str, object]:
        self._clear_messages()
        try:
            parsed = extract_otp_secret_from_qr_image(image_path)
        except Exception as exc:  # noqa: BLE001
            self._error_message = f"OTP 二维码导入失败：{exc}"
            self._emit_data_changed()
            return {"success": False, "error": str(exc)}
        source_label = {
            "clipboard_image": "剪贴板二维码",
            "clipboard_path": "剪贴板图片路径",
            "clipboard_url": "剪贴板图片",
            "drop": "拖拽二维码",
            "file_dialog": "二维码图片",
        }.get(source, "二维码")
        self._status_message = f"OTP 配置已从{source_label}导入"
        self._emit_data_changed()
        return _otp_import_payload(
            parsed,
            selected_path=image_path,
            preview_image_url=_preview_image_url(image_path),
            source=source,
        )

    @pyqtSlot(str, str)
    def listTickets(self, query: str, status_filter: str) -> None:
        self._ticket_query = str(query or "").strip()
        normalized_status = str(status_filter or TodoStatus.OPEN).strip().lower() or TodoStatus.OPEN
        if normalized_status not in {TodoStatus.OPEN, TodoStatus.DONE, "all", "done_missing_ach", "today_done"}:
            normalized_status = TodoStatus.OPEN
        self._ticket_status_filter = normalized_status
        self._refresh_ticket_payloads()
        self._refresh_selected_ticket_payload()
        self._emit_data_changed()

    @pyqtSlot()
    def refreshTickets(self) -> None:
        self._refresh_ticket_payloads()
        self._refresh_selected_ticket_payload()
        self._clear_messages()
        self._status_message = f"\u5df2\u5237\u65b0 {len(self._tickets)} \u6761\u5de5\u5355\u3002"
        self._emit_data_changed()

    def refresh_ticket_payloads_from_store(self) -> None:
        self._refresh_ticket_payloads()
        self._refresh_selected_ticket_payload()
        self._emit_data_changed()

    @pyqtSlot(str)
    def openTicketDetail(self, todo_id: str) -> None:
        normalized_id = str(todo_id or "").strip()
        if not normalized_id:
            return
        todo = self._todo_store.get_todo(normalized_id)
        if todo is None:
            self._selected_ticket_id = ""
            self._selected_ticket = self._empty_ticket_detail_payload()
            self._error_message = "\u8be5\u5de5\u5355\u4e0d\u5b58\u5728\u6216\u5df2\u88ab\u5220\u9664\u3002"
            self._emit_data_changed()
            return
        self._clear_messages()
        self._selected_ticket_id = normalized_id
        self._selected_ticket = self._build_ticket_detail_payload(todo)
        self._emit_data_changed()

    @pyqtSlot()
    def backToTicketList(self) -> None:
        if not self._selected_ticket_id:
            return
        self._selected_ticket_id = ""
        self._selected_ticket = self._empty_ticket_detail_payload()
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot()
    def copySelectedTicket(self) -> None:
        if not self._selected_ticket_id:
            return
        self.copyTicket(self._selected_ticket_id)

    @pyqtSlot(str)
    def copyTicket(self, todo_id: str) -> None:
        normalized_id = str(todo_id or "").strip()
        if not normalized_id:
            return
        todo = self._todo_store.get_todo(normalized_id)
        if todo is None:
            self._error_message = "未找到对应待办"
            self._emit_data_changed()
            return
        payload = self._build_ticket_detail_payload(todo)
        QApplication.clipboard().setText(_format_ticket_copy_text(payload))
        self._clear_messages()
        self._notification_bridge.notify("success", "工单内容已复制", source="control_panel")
        self._emit_data_changed()

    @pyqtSlot()
    def reopenSelectedTicket(self) -> None:
        if not self._selected_ticket_id:
            return
        self._clear_messages()
        todo = self._resolve_selected_ticket_for_update()
        if todo is None:
            return
        reopened = self._todo_store.reopen_todo(todo.id)
        if not reopened:
            self._error_message = "\u91cd\u65b0\u6253\u5f00\u5de5\u5355\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002"
            self._emit_data_changed()
            return
        updated = self._todo_store.get_todo(todo.id)
        if updated is None:
            self._error_message = "\u5de5\u5355\u72b6\u6001\u5237\u65b0\u5931\u8d25\uff0c\u8bf7\u5237\u65b0\u540e\u91cd\u8bd5\u3002"
            self._emit_data_changed()
            return
        self._apply_selected_ticket_update(updated, status_message="\u5de5\u5355\u5df2\u91cd\u65b0\u6253\u5f00")

    @pyqtSlot()
    def deleteSelectedTicket(self) -> None:
        if not self._selected_ticket_id:
            return
        todo = self._resolve_selected_ticket_for_update()
        if todo is None:
            return
        self._clear_messages()
        deleted = self._todo_store.delete_todo(todo.id)
        if not deleted:
            self._error_message = "\u5220\u9664\u5de5\u5355\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002"
            self._emit_data_changed()
            return
        self._selected_ticket_id = ""
        self._selected_ticket = self._empty_ticket_detail_payload()
        self._refresh_ticket_payloads()
        todo_title = str(todo.title or "").strip() or "\u672a\u5206\u7c7b\u4efb\u52a1"
        self._status_message = f"\u5de5\u5355\u5df2\u5220\u9664\uff1a{todo_title}"
        self._emit_data_changed()
        self.todoListRefreshRequested.emit()

    @pyqtSlot()
    def unlinkSelectedTicketProject(self) -> None:
        if not self._selected_ticket_id:
            return
        self._clear_messages()
        todo = self._resolve_selected_ticket_for_update()
        if todo is None:
            return
        updated = self._todo_store.unlink_todo_project(todo.id)
        if updated is None:
            self._error_message = "\u89e3\u9664\u5173\u8054\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002"
            self._emit_data_changed()
            return
        self._apply_selected_ticket_update(
            updated,
            status_message="\u5df2\u89e3\u9664\u9879\u76ee\u5173\u8054",
        )

    @pyqtSlot(str)
    def saveSelectedTicketVersion(self, value: str) -> None:
        self.saveSelectedTicketField("ticket_version", value)

    @pyqtSlot()
    def refreshSelectedTicketFeaturePoint(self) -> None:
        if not self._selected_ticket_id:
            return
        self._clear_messages()
        todo = self._resolve_selected_ticket_for_update()
        if todo is None:
            return
        product_line = str(todo.summary_fields.product_line or "").strip()
        if is_unknown_text(product_line):
            self._error_message = "\u7f3a\u5c11\u4ea7\u54c1\u7ebf\uff0c\u65e0\u6cd5\u5237\u65b0\u529f\u80fd\u70b9\u3002"
            self._emit_data_changed()
            return
        problem_desc = str(todo.current_summary or "").strip()
        if not problem_desc:
            self._error_message = "\u7f3a\u5c11\u95ee\u9898\u6458\u8981\uff0c\u65e0\u6cd5\u5237\u65b0\u529f\u80fd\u70b9\u3002"
            self._emit_data_changed()
            return

        provider = build_feature_point_provider(self._config_manager.load().ticket_enrichment.feature_point)
        try:
            result = provider.resolve(
                product_line=product_line,
                problem_desc=problem_desc,
            )
        except Exception as exc:  # noqa: BLE001
            self._error_message = f"\u529f\u80fd\u70b9\u5237\u65b0\u5931\u8d25\uff1a{exc}"
            self._emit_data_changed()
            return
        if result.error_message:
            self._error_message = f"\u529f\u80fd\u70b9\u5237\u65b0\u5931\u8d25\uff1a{result.error_message}"
            self._emit_data_changed()
            return
        next_feature_point = str(result.value or "").strip()
        if not next_feature_point:
            self._error_message = "\u529f\u80fd\u70b9\u5339\u914d\u672a\u8fd4\u56de\u6709\u6548\u7ed3\u679c\u3002"
            self._emit_data_changed()
            return

        updated = self._todo_store.update_todo(
            todo.id,
            summary_fields=self._build_updated_ticket_summary_fields(
                todo,
                feature_point=next_feature_point,
                feature_point_source="auto",
            ),
        )
        if updated is None:
            self._error_message = "\u529f\u80fd\u70b9\u5237\u65b0\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002"
            self._emit_data_changed()
            return
        self._apply_selected_ticket_update(updated, status_message="\u529f\u80fd\u70b9\u5df2\u5237\u65b0")

    @pyqtSlot(str, str)
    def saveSelectedTicketField(self, field_name: str, value: str) -> None:
        if not self._selected_ticket_id:
            return
        normalized_field = str(field_name or "").strip()
        if normalized_field not in {"ach_no", "ticket_version", "feature_point", "root_cause", "root_cause_desc"}:
            return
        self._clear_messages()
        todo = self._resolve_selected_ticket_for_update()
        if todo is None:
            return
        next_value = str(value or "").strip()
        ach_filled_at = todo.summary_fields.ach_filled_at
        if normalized_field == "ach_no":
            if next_value and not str(todo.summary_fields.ach_no or "").strip():
                ach_filled_at = now_iso()
            elif not next_value:
                ach_filled_at = ""
        updated = self._todo_store.update_todo(
            todo.id,
            summary_fields=self._build_updated_ticket_summary_fields(
                todo,
                ach_no=next_value if normalized_field == "ach_no" else todo.summary_fields.ach_no,
                ach_filled_at=ach_filled_at,
                ticket_version=next_value if normalized_field == "ticket_version" else todo.summary_fields.ticket_version,
                feature_point=next_value if normalized_field == "feature_point" else todo.summary_fields.feature_point,
                feature_point_source="manual" if normalized_field == "feature_point" else todo.summary_fields.feature_point_source,
                root_cause_desc=next_value if normalized_field == "root_cause_desc" else todo.summary_fields.root_cause_desc,
                root_cause_desc_source="manual" if normalized_field == "root_cause_desc" else todo.summary_fields.root_cause_desc_source,
                root_cause=next_value if normalized_field == "root_cause" else todo.summary_fields.root_cause,
                root_cause_source="manual" if normalized_field == "root_cause" else todo.summary_fields.root_cause_source,
            ),
        )
        if updated is None:
            self._error_message = "\u4fdd\u5b58\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002"
            self._emit_data_changed()
            return
        field_labels = {
            "ach_no": "ach单号",
            "ticket_version": "\u7248\u672c\u53f7",
            "feature_point": "\u529f\u80fd\u70b9",
            "root_cause": "\u95ee\u9898\u6839\u56e0",
            "root_cause_desc": "\u6839\u56e0\u63cf\u8ff0",
        }
        field_label = field_labels.get(normalized_field, "\u5b57\u6bb5")
        self._apply_selected_ticket_update(
            updated,
            status_message=f"{field_label}\u5df2\u4fdd\u5b58",
        )

    @pyqtSlot(str, str)
    def chooseProjectDate(self, field_name: str, current_value: str) -> None:
        normalized_field = str(field_name or "").strip()
        if normalized_field not in {"followUpStartedAt", "supportEndedAt"}:
            return
        dialog = QDialog()
        dialog.setWindowTitle("选择日期")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        calendar = QCalendarWidget(dialog)
        calendar.setSelectedDate(_parse_project_date(current_value))
        layout.addWidget(calendar)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.projectDateSelected.emit(
            normalized_field,
            _serialize_project_date(normalized_field, calendar.selectedDate()),
        )

    @pyqtSlot("QVariantMap")
    def saveProject(self, payload: object) -> None:
        if not isinstance(payload, dict):
            return
        self._clear_messages()
        cached_project = self._find_cached_project(str(payload.get("id") or ""))
        cached_existing = (
            project_record_from_payload(cached_project)
            if isinstance(cached_project, dict) and cached_project
            else None
        )
        existing_by_task_order = self._project_repository.get_project_by_task_order_no(
            str(payload.get("taskOrderNo") or payload.get("task_order_no") or "")
        )
        if cached_existing is not None and existing_by_task_order is not None and existing_by_task_order.id != cached_existing.id:
            self._error_message = "任务单号已被其他项目占用"
            self._emit_data_changed()
            return
        existing = cached_existing or existing_by_task_order
        try:
            project = project_record_from_payload(payload, existing=existing)
        except ValueError as exc:
            self._error_message = str(exc)
            self._emit_data_changed()
            return
        conflicts = find_active_alias_conflicts(
            project,
            self._project_repository.list_projects(include_expired=True),
        )
        if conflicts:
            first_conflict = conflicts[0]
            self._error_message = (
                f"群名别名 {first_conflict.alias} 已被 "
                f"{first_conflict.conflicting_project_name}"
                f"({first_conflict.conflicting_task_order_no}) 使用"
            )
            self._emit_data_changed()
            return
        previous_aliases = list(existing.aliases) if existing is not None else []
        self._project_repository.upsert_project(project)
        relinked_count = self._todo_store.relink_open_unresolved_todos_by_aliases(previous_aliases + list(project.aliases))
        self._refresh_project_payloads()
        self._refresh_project_environment_payloads(project.id)
        self._status_message = (
            f"已保存项目 {project.project_name}，"
            f"关联 {relinked_count} 个未解决待办"
        )
        self._emit_data_changed()

    @pyqtSlot(str)
    def deleteProject(self, project_id: str) -> None:
        cached_project = self._find_cached_project(project_id)
        if not isinstance(cached_project, dict):
            return
        self._clear_messages()
        project = project_record_from_payload(cached_project)
        deleted = self._project_repository.delete_project(project.id)
        if not deleted:
            return
        relinked_count = self._todo_store.relink_open_unresolved_todos_by_aliases(list(project.aliases))
        self._refresh_project_payloads()
        if self._project_environment_project_id == project.id:
            self._project_environment_project_id = ""
            self._project_environment_groups = []
        self._status_message = (
            f"已删除项目 {project.project_name}，"
            f"关联 {relinked_count} 个未解决待办"
        )
        self._emit_data_changed()

    @pyqtSlot()
    def relinkOpenUnresolvedTodos(self) -> None:
        self._clear_messages()
        relinked_count = self._todo_store.relink_open_unresolved_todos()
        self._refresh_project_payloads()
        self._status_message = f"已关联 {relinked_count} 个未解决待办到项目"
        self._emit_data_changed()

    def _coerce_provider_timeouts(self) -> None:
        for provider in self._config.providers:
            try:
                provider.timeout_seconds = int(provider.timeout_seconds)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{provider.name} 的超时时间必须是整数") from exc
            if provider.timeout_seconds <= 0:
                raise ValueError(f"{provider.name} 的超时时间必须大于 0")

    def _coerce_server_timeout(self) -> None:
        try:
            self._config.server.timeout_seconds = int(self._config.server.timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("\u670d\u52a1\u7aef\u8d85\u65f6\u65f6\u95f4\u5fc5\u987b\u662f\u6574\u6570") from exc
        if self._config.server.timeout_seconds <= 0:
            raise ValueError("\u670d\u52a1\u7aef\u8d85\u65f6\u65f6\u95f4\u5fc5\u987b\u5927\u4e8e 0")

    def _find_script_integration(self, integration_id: str) -> dict[str, object] | None:
        return next(
            (
                item
                for item in self._script_integrations
                if str(item.get("id") or "").strip() == integration_id
            ),
            None,
        )

    def _replace_script_integration(self, integration_id: str, updated_item: dict[str, object]) -> None:
        for index, item in enumerate(self._script_integrations):
            if str(item.get("id") or "").strip() == integration_id:
                self._script_integrations[index] = updated_item
                return


class ControlPanelWindow(QWidget):
    config_saved = pyqtSignal(object)
    todo_list_refresh_requested = pyqtSignal()

    def __init__(
        self,
        config_manager: ConfigManager,
        parent=None,
        *,
        notification_bridge: AppNotificationBridge | None = None,
    ) -> None:
        super().__init__(parent)
        self._positioned = False
        self._notification_bridge = notification_bridge or AppNotificationBridge()
        self._bridge = _ControlPanelBridge(
            config_manager,
            notification_bridge=self._notification_bridge,
        )
        self._layout: QVBoxLayout | None = None

        self.setObjectName("controlPanelWindow")
        self.setWindowFlags(RUNTIME_CAPABILITIES.control_panel_window_flags(Qt.WindowType))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("Chattodo Hub")
        self.resize(1040, 760)
        self.setMinimumSize(920, 680)

        self._setup_ui()

        self._bridge.closeRequested.connect(self.hide)
        self._bridge.minimizeRequested.connect(self.showMinimized)
        self._bridge.maximizeRequested.connect(self._toggle_maximized)
        self._bridge.dragRequested.connect(self._start_system_move)
        self._bridge.resizeRequested.connect(self._start_system_resize)
        self._bridge.configSaved.connect(lambda payload: self.config_saved.emit(payload))
        self._bridge.todoListRefreshRequested.connect(lambda: self.todo_list_refresh_requested.emit())
        self._sync_window_state()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        self._layout = layout
        self._update_layout_margins()

        self._view = QQuickWidget(self)
        self._view.setClearColor(QColor(0, 0, 0, 0))
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._view.rootContext().setContextProperty("controlPanelBridge", self._bridge)
        self._view.setSource(QUrl.fromLocalFile(str(qml_dir() / "ControlPanel.qml")))
        self._ensure_qml_loaded()
        layout.addWidget(self._view)

    def _ensure_qml_loaded(self) -> None:
        if self._view.status() != QQuickWidget.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self._view.errors())
        raise RuntimeError(f"Failed to load ControlPanel.qml:\n{errors}")

    def show_panel(self, section_id: str = "models") -> None:
        self._bridge.reloadConfig()
        self._bridge.setCurrentSection(section_id)
        if self.isMinimized():
            if self.windowState() & Qt.WindowState.WindowMaximized:
                self.showMaximized()
            else:
                self.showNormal()
        self.show()
        self._sync_window_state()
        self.raise_()
        self.activateWindow()
        if not self._positioned:
            self._fit_within_screen()
            self._positioned = True

    def refresh_tickets_from_store(self) -> None:
        self._bridge.refresh_ticket_payloads_from_store()

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide()

    def changeEvent(self, event) -> None:  # noqa: N802
        super().changeEvent(event)
        self._sync_window_state()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        disable_windows_window_border(self)

    def _fit_within_screen(self) -> None:
        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = 20
        self.resize(
            min(self.width(), available.width() - margin * 2),
            min(self.height(), available.height() - margin * 2),
        )
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _start_system_move(self) -> None:
        window_handle = self.windowHandle()
        if window_handle is None:
            self.activateWindow()
            return
        try:
            window_handle.startSystemMove()
        except AttributeError:
            self.activateWindow()

    def _start_system_resize(self, edge_name: str) -> None:
        window_handle = self.windowHandle()
        if window_handle is None:
            self.activateWindow()
            return

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
            window_handle.startSystemResize(edge)
        except AttributeError:
            self.activateWindow()

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_window_state()

    def _sync_window_state(self) -> None:
        self._bridge.setWindowMaximized(self.isMaximized())
        self._update_layout_margins()

    def _update_layout_margins(self) -> None:
        if self._layout is None:
            return
        self._layout.setContentsMargins(0, 0, 0, 0)


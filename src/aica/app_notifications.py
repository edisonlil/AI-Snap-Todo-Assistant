"""Lightweight global notification queue and desktop notification window."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import uuid

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QObject, QTimer, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
    from PyQt6.QtGui import QColor, QCursor
    from PyQt6.QtQuick import QQuickView
    from PyQt6.QtWidgets import QApplication
    _QT_RUNTIME_AVAILABLE = True
except Exception:  # pragma: no cover - fallback for test environments without Qt runtime
    _QT_RUNTIME_AVAILABLE = False

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

    class QTimer:  # type: ignore[no-redef]
        @staticmethod
        def singleShot(_msec, _callback):
            return None

from aica.runtime import RUNTIME_CAPABILITIES
from aica.theme_controller import ThemeController


_DEFAULT_DURATIONS = {
    "info": 2200,
    "success": 2200,
    "warning": 3200,
    "error": 4200,
}


class AppNotificationBridge(QObject):
    notificationsChanged = pyqtSignal()

    def __init__(
        self,
        *,
        auto_dismiss_scheduler=None,
        max_visible: int = 3,
    ) -> None:
        super().__init__()
        self._auto_dismiss_scheduler = auto_dismiss_scheduler or QTimer.singleShot
        self._max_visible = max(1, int(max_visible))
        self._notifications: list[dict[str, object]] = []
        self._dismiss_tokens: dict[str, str] = {}

    @pyqtProperty("QVariantList", notify=notificationsChanged)
    def notifications(self):  # noqa: ANN201
        return [dict(item) for item in self._notifications]

    @staticmethod
    def _normalize_level(level: str) -> str:
        normalized = str(level or "").strip().lower()
        if normalized not in _DEFAULT_DURATIONS:
            return "info"
        return normalized

    @staticmethod
    def _resolve_duration(level: str, duration_ms: int | None) -> int:
        if duration_ms is not None:
            try:
                parsed = int(duration_ms)
            except (TypeError, ValueError):
                parsed = 0
            if parsed > 0:
                return parsed
        return _DEFAULT_DURATIONS[level]

    @pyqtSlot(str, str, result=str)
    @pyqtSlot(str, str, int, result=str)
    @pyqtSlot(str, str, int, str, result=str)
    def notify(
        self,
        level: str,
        message: str,
        duration_ms: int | None = None,
        source: str = "",
    ) -> str:
        text = str(message or "").strip()
        if not text:
            return ""
        normalized_level = self._normalize_level(level)
        notification_id = uuid.uuid4().hex
        resolved_duration = self._resolve_duration(normalized_level, duration_ms)
        notification = {
            "id": notification_id,
            "level": normalized_level,
            "message": text,
            "durationMs": resolved_duration,
            "source": str(source or "").strip(),
        }
        self._notifications.append(notification)
        if len(self._notifications) > self._max_visible:
            overflow = self._notifications[:-self._max_visible]
            for item in overflow:
                self._dismiss_tokens.pop(str(item.get("id") or ""), None)
            self._notifications = self._notifications[-self._max_visible:]
        dismiss_token = uuid.uuid4().hex
        self._dismiss_tokens[notification_id] = dismiss_token
        self.notificationsChanged.emit()
        self._auto_dismiss_scheduler(
            resolved_duration,
            lambda notification_id=notification_id, dismiss_token=dismiss_token: (
                self._dismiss_if_current(notification_id, dismiss_token)
            ),
        )
        return notification_id

    def _dismiss_if_current(self, notification_id: str, dismiss_token: str) -> None:
        if self._dismiss_tokens.get(notification_id) != dismiss_token:
            return
        self.dismiss(notification_id)

    @pyqtSlot(str)
    def dismiss(self, notification_id: str) -> None:
        normalized_id = str(notification_id or "").strip()
        if not normalized_id:
            return
        next_notifications = [
            item
            for item in self._notifications
            if str(item.get("id") or "").strip() != normalized_id
        ]
        if len(next_notifications) == len(self._notifications):
            return
        self._notifications = next_notifications
        self._dismiss_tokens.pop(normalized_id, None)
        self.notificationsChanged.emit()

    @pyqtSlot()
    def clear(self) -> None:
        if not self._notifications:
            return
        self._notifications = []
        self._dismiss_tokens = {}
        self.notificationsChanged.emit()


if _QT_RUNTIME_AVAILABLE:
    class AppNotificationWindow(QQuickView):
        """Global desktop notification window anchored to the bottom-right corner."""

        def __init__(
            self,
            bridge: AppNotificationBridge,
            parent=None,
            *,
            theme_controller: ThemeController | None = None,
        ) -> None:
            super().__init__(parent)
            self._bridge = bridge
            self._theme_controller = theme_controller or ThemeController()
            self._screen_margin = 20
            self._window_padding = 14

            flags = RUNTIME_CAPABILITIES.floating_tool_window_flags(
                Qt.WindowType,
                stays_on_top=True,
            )
            if hasattr(Qt.WindowType, "WindowDoesNotAcceptFocus"):
                flags |= Qt.WindowType.WindowDoesNotAcceptFocus
            if hasattr(Qt.WindowType, "WindowTransparentForInput"):
                flags |= Qt.WindowType.WindowTransparentForInput
            self.setFlags(flags)
            self.setColor(QColor(0, 0, 0, 0))
            self.setResizeMode(QQuickView.ResizeMode.SizeViewToRootObject)
            self._theme_controller.apply_to_context(self.rootContext())
            self.rootContext().setContextProperty("notificationBridge", bridge)
            self.rootContext().setContextProperty(
                "notificationUiFont",
                str(self._theme_controller.tokens.get("uiFont") or RUNTIME_CAPABILITIES.ui_font),
            )
            self.setSource(
                QUrl.fromLocalFile(
                    str(Path(__file__).with_name("qml").joinpath("AppNotificationWindow.qml"))
                )
            )
            self._ensure_qml_loaded()
            self.hide()

            bridge.notificationsChanged.connect(self._queue_sync_window)

        def _ensure_qml_loaded(self) -> None:
            if self.status() != QQuickView.Status.Error:
                return
            errors = "\n".join(error.toString() for error in self.errors())
            raise RuntimeError(f"Failed to load AppNotificationWindow.qml:\n{errors}")

        def _queue_sync_window(self) -> None:
            QTimer.singleShot(0, self._sync_window_state)

        def _target_screen(self):
            screen = QApplication.screenAt(QCursor.pos())
            if screen is not None:
                return screen
            focus_window = QApplication.focusWindow()
            if focus_window is not None and focus_window.screen() is not None:
                return focus_window.screen()
            return QApplication.primaryScreen()

        def _sync_window_state(self) -> None:
            root = self.rootObject()
            if root is None:
                return
            notifications = self._bridge.notifications
            if not notifications:
                self.hide()
                return

            width = int(root.property("width") or root.property("implicitWidth") or 360)
            height = int(root.property("height") or root.property("implicitHeight") or 420)
            self.resize(width, height)

            screen = self._target_screen()
            if screen is None:
                return
            available = screen.availableGeometry()
            x = available.right() - width - self._screen_margin
            y = available.bottom() - height - self._screen_margin
            self.setPosition(x, y)
            self.show()
            self.raise_()

else:
    class AppNotificationWindow:  # pragma: no cover - test fallback
        def __init__(self, bridge: AppNotificationBridge, parent=None) -> None:
            self._bridge = bridge

        def hide(self) -> None:
            return None

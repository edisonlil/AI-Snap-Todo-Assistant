"""Global capture hotkey management."""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from typing import Callable

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, pyqtSignal

    _QT_AVAILABLE = True
except Exception:  # pragma: no cover - fallback for test environments without Qt runtime
    _QT_AVAILABLE = False

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

    class QAbstractNativeEventFilter:  # type: ignore[no-redef]
        def nativeEventFilter(self, _event_type, _message):
            return False, 0

    class QCoreApplication:  # type: ignore[no-redef]
        @staticmethod
        def instance():
            return None

    def pyqtSignal(*_args, **_kwargs):  # type: ignore[no-redef]
        return _SignalDescriptor()

try:
    from pynput import keyboard
except Exception:  # pragma: no cover - fallback for test environments without pynput runtime
    class _DummyHotKeys:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            return None

        def stop(self):
            return None

    class _KeyboardModule:
        GlobalHotKeys = _DummyHotKeys

    keyboard = _KeyboardModule()  # type: ignore[assignment]

from aica.config import DEFAULT_CAPTURE_HOTKEY


_IS_WINDOWS = sys.platform.startswith("win")
_WM_HOTKEY = 0x0312
_MOD_ALT = 0x0001
_MOD_CONTROL = 0x0002
_MOD_SHIFT = 0x0004
_MOD_WIN = 0x0008
_MOD_NOREPEAT = 0x4000
_HOTKEY_ID = 0x0A1C

_MODIFIER_ALIASES = {
    "alt": "Alt",
    "ctrl": "Ctrl",
    "control": "Ctrl",
    "shift": "Shift",
    "win": "Win",
    "windows": "Win",
    "meta": "Win",
    "cmd": "Win",
}
_MODIFIER_ORDER = ("Ctrl", "Alt", "Shift", "Win")
_PYNPUT_MODIFIER_MAP = {
    "Ctrl": "<ctrl>",
    "Alt": "<alt>",
    "Shift": "<shift>",
    "Win": "<cmd>",
}
_WINDOWS_MODIFIER_MAP = {
    "Ctrl": _MOD_CONTROL,
    "Alt": _MOD_ALT,
    "Shift": _MOD_SHIFT,
    "Win": _MOD_WIN,
}
_SPECIAL_KEY_MAP = {
    "space": "Space",
    "tab": "Tab",
    "enter": "Enter",
    "esc": "Esc",
    "escape": "Esc",
}
_PYNPUT_SPECIAL_KEY_MAP = {
    "Space": "<space>",
    "Tab": "<tab>",
    "Enter": "<enter>",
    "Esc": "<esc>",
}
_WINDOWS_SPECIAL_KEY_MAP = {
    "Space": 0x20,
    "Tab": 0x09,
    "Enter": 0x0D,
    "Esc": 0x1B,
}


def normalize_hotkey(value: str) -> str:
    parts = [segment.strip() for segment in str(value or "").split("+")]
    if not parts or any(not part for part in parts):
        raise ValueError("截图热键格式无效")

    modifiers: list[str] = []
    primary_key = ""
    for raw_part in parts:
        lowered = raw_part.lower()
        if lowered in _MODIFIER_ALIASES:
            normalized = _MODIFIER_ALIASES[lowered]
            if normalized in modifiers:
                raise ValueError("截图热键不能包含重复修饰键")
            modifiers.append(normalized)
            continue
        if primary_key:
            raise ValueError("截图热键只能包含一个主按键")
        primary_key = _normalize_primary_key(raw_part)

    if not modifiers:
        raise ValueError("截图热键至少需要一个修饰键")
    if not primary_key:
        raise ValueError("截图热键缺少主按键")

    ordered_modifiers = [modifier for modifier in _MODIFIER_ORDER if modifier in modifiers]
    return "+".join([*ordered_modifiers, primary_key])


def hotkey_to_pynput_expression(value: str) -> str:
    modifiers, primary_key = _split_hotkey(value)
    mapped_modifiers = [_PYNPUT_MODIFIER_MAP[modifier] for modifier in modifiers]
    return "+".join([*mapped_modifiers, _primary_key_to_pynput(primary_key)])


def hotkey_to_windows_registration(value: str) -> tuple[int, int]:
    modifiers, primary_key = _split_hotkey(value)
    modifier_flags = _MOD_NOREPEAT
    for modifier in modifiers:
        modifier_flags |= _WINDOWS_MODIFIER_MAP[modifier]
    return modifier_flags, _primary_key_to_windows_vk(primary_key)


def _split_hotkey(value: str) -> tuple[list[str], str]:
    normalized = normalize_hotkey(value)
    parts = normalized.split("+")
    return parts[:-1], parts[-1]


def _normalize_primary_key(value: str) -> str:
    token = str(value or "").strip()
    lowered = token.lower()
    if lowered in _SPECIAL_KEY_MAP:
        return _SPECIAL_KEY_MAP[lowered]
    if len(token) == 1 and token.isalnum():
        return token.upper()
    if lowered.startswith("f") and lowered[1:].isdigit():
        number = int(lowered[1:])
        if 1 <= number <= 24:
            return f"F{number}"
    raise ValueError("截图热键主按键仅支持字母、数字、F1-F24、Space、Tab、Enter、Esc")


def _primary_key_to_pynput(primary_key: str) -> str:
    if primary_key in _PYNPUT_SPECIAL_KEY_MAP:
        return _PYNPUT_SPECIAL_KEY_MAP[primary_key]
    if primary_key.startswith("F") and primary_key[1:].isdigit():
        return f"<{primary_key.lower()}>"
    return primary_key.lower()


def _primary_key_to_windows_vk(primary_key: str) -> int:
    if primary_key in _WINDOWS_SPECIAL_KEY_MAP:
        return _WINDOWS_SPECIAL_KEY_MAP[primary_key]
    if len(primary_key) == 1 and primary_key.isalnum():
        return ord(primary_key.upper())
    if primary_key.startswith("F") and primary_key[1:].isdigit():
        return 0x70 + int(primary_key[1:]) - 1
    raise ValueError(f"Unsupported Windows hotkey primary key: {primary_key}")


class _PynputHotkeyListener:
    def __init__(self, hotkey: str, callback: Callable[[], None]):
        self._listener = keyboard.GlobalHotKeys(
            {hotkey_to_pynput_expression(hotkey): callback}
        )

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()


class _WindowsNativeHotkeyListener(QAbstractNativeEventFilter):
    def __init__(self, hotkey: str, callback: Callable[[], None]):
        super().__init__()
        self._callback = callback
        self._hotkey = normalize_hotkey(hotkey)
        self._modifier_flags, self._vk = hotkey_to_windows_registration(self._hotkey)
        self._registered = False
        self._installed = False
        self._app = None
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self._user32.UnregisterHotKey.restype = wintypes.BOOL

    def start(self) -> None:
        app = QCoreApplication.instance()
        if app is None:
            raise RuntimeError("Global hotkey listener requires a running QApplication")

        app.installNativeEventFilter(self)
        self._installed = True
        self._app = app
        if not self._user32.RegisterHotKey(None, _HOTKEY_ID, self._modifier_flags, self._vk):
            error_code = ctypes.get_last_error()
            self.stop()
            raise OSError(
                error_code,
                f"Failed to register global hotkey {self._hotkey}: "
                f"{_format_registration_debug_info(self._modifier_flags, self._vk)}",
            )
        self._registered = True

    def stop(self) -> None:
        if self._registered:
            self._user32.UnregisterHotKey(None, _HOTKEY_ID)
            self._registered = False

        if self._installed and self._app is not None:
            try:
                self._app.removeNativeEventFilter(self)
            except RuntimeError:
                pass
        self._installed = False
        self._app = None

    def nativeEventFilter(self, _event_type, message):  # noqa: N802
        if message is None:
            return False, 0
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == _WM_HOTKEY and int(msg.wParam) == _HOTKEY_ID:
            self._callback()
        return False, 0


def _format_registration_debug_info(modifier_flags: int, vk: int) -> str:
    return f"modifiers=0x{modifier_flags:04X}, vk=0x{vk:02X}"


class HotkeyManager(QObject):
    hotkey_triggered = pyqtSignal()
    hotkey_changed = pyqtSignal(str)

    def __init__(self, hotkey: str = DEFAULT_CAPTURE_HOTKEY, parent=None):
        super().__init__(parent)
        self._listener: _PynputHotkeyListener | _WindowsNativeHotkeyListener | None = None
        self._hotkey = normalize_hotkey(hotkey)

    @property
    def hotkey(self) -> str:
        return self._hotkey

    def start(self) -> None:
        self.stop()
        listener = self._create_listener()
        listener.start()
        self._listener = listener

    def stop(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is not None:
            listener.stop()

    def update_hotkey(self, hotkey: str) -> str:
        normalized = normalize_hotkey(hotkey)
        was_running = self._listener is not None
        if normalized == self._hotkey and was_running:
            return self._hotkey
        self._hotkey = normalized
        if was_running:
            self.start()
        self.hotkey_changed.emit(self._hotkey)
        return self._hotkey

    def _create_listener(self) -> _PynputHotkeyListener | _WindowsNativeHotkeyListener:
        if _IS_WINDOWS and _QT_AVAILABLE:
            return _WindowsNativeHotkeyListener(self._hotkey, self._on_hotkey)
        return _PynputHotkeyListener(self._hotkey, self._on_hotkey)

    def _on_hotkey(self) -> None:
        self.hotkey_triggered.emit()

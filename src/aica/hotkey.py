"""Global capture hotkey management."""
from __future__ import annotations

import ctypes
import os
import sys
import threading
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

try:
    import Quartz
except Exception:  # pragma: no cover - fallback for non-macOS environments
    Quartz = None  # type: ignore[assignment]

from aica.runtime import (
    PLATFORM_MACOS,
    PLATFORM_WINDOWS,
    current_platform,
    default_capture_hotkey,
)

_WM_HOTKEY = 0x0312
_MOD_ALT = 0x0001
_MOD_CONTROL = 0x0002
_MOD_SHIFT = 0x0004
_MOD_WIN = 0x0008
_MOD_NOREPEAT = 0x4000
_HOTKEY_ID = 0x0A1C

_WINDOWS_MODIFIER_ORDER = ("Ctrl", "Alt", "Shift", "Win")
_MACOS_MODIFIER_ORDER = ("Command", "Option", "Control", "Shift")
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
_MACOS_MODIFIER_FLAGS = {
    "Command": 0 if Quartz is None else Quartz.kCGEventFlagMaskCommand,
    "Option": 0 if Quartz is None else Quartz.kCGEventFlagMaskAlternate,
    "Control": 0 if Quartz is None else Quartz.kCGEventFlagMaskControl,
    "Shift": 0 if Quartz is None else Quartz.kCGEventFlagMaskShift,
}
_MACOS_PRIMARY_KEY_MAP = {
    "A": 0,
    "S": 1,
    "D": 2,
    "F": 3,
    "H": 4,
    "G": 5,
    "Z": 6,
    "X": 7,
    "C": 8,
    "V": 9,
    "B": 11,
    "Q": 12,
    "W": 13,
    "E": 14,
    "R": 15,
    "Y": 16,
    "T": 17,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "6": 22,
    "5": 23,
    "9": 25,
    "7": 26,
    "8": 28,
    "0": 29,
    "O": 31,
    "U": 32,
    "I": 34,
    "P": 35,
    "L": 37,
    "J": 38,
    "K": 40,
    "N": 45,
    "M": 46,
    "Tab": 48,
    "Space": 49,
    "Enter": 36,
    "Esc": 53,
    "F1": 122,
    "F2": 120,
    "F3": 99,
    "F4": 118,
    "F5": 96,
    "F6": 97,
    "F7": 98,
    "F8": 100,
    "F9": 101,
    "F10": 109,
    "F11": 103,
    "F12": 111,
    "F13": 105,
    "F14": 107,
    "F15": 113,
    "F16": 106,
    "F17": 64,
    "F18": 79,
    "F19": 80,
    "F20": 90,
}
_MACOS_RELEVANT_MODIFIER_MASK = 0 if Quartz is None else (
    Quartz.kCGEventFlagMaskCommand
    | Quartz.kCGEventFlagMaskAlternate
    | Quartz.kCGEventFlagMaskControl
    | Quartz.kCGEventFlagMaskShift
)


def _normalize_platform_id(platform_id: str | None = None) -> str:
    detected = platform_id or current_platform()
    return PLATFORM_MACOS if detected == PLATFORM_MACOS else PLATFORM_WINDOWS


def _modifier_aliases(platform_id: str) -> dict[str, str]:
    if platform_id == PLATFORM_MACOS:
        return {
            "command": "Command",
            "cmd": "Command",
            "meta": "Command",
            "win": "Command",
            "windows": "Command",
            "option": "Option",
            "opt": "Option",
            "alt": "Option",
            "control": "Control",
            "ctrl": "Control",
            "shift": "Shift",
        }
    return {
        "alt": "Alt",
        "option": "Alt",
        "opt": "Alt",
        "ctrl": "Ctrl",
        "control": "Ctrl",
        "shift": "Shift",
        "win": "Win",
        "windows": "Win",
        "meta": "Win",
        "cmd": "Win",
        "command": "Win",
    }


def _modifier_order(platform_id: str) -> tuple[str, ...]:
    if platform_id == PLATFORM_MACOS:
        return _MACOS_MODIFIER_ORDER
    return _WINDOWS_MODIFIER_ORDER


def _pynput_modifier_map(platform_id: str) -> dict[str, str]:
    if platform_id == PLATFORM_MACOS:
        return {
            "Command": "<cmd>",
            "Option": "<alt>",
            "Control": "<ctrl>",
            "Shift": "<shift>",
        }
    return {
        "Ctrl": "<ctrl>",
        "Alt": "<alt>",
        "Shift": "<shift>",
        "Win": "<cmd>",
    }


def normalize_hotkey(value: str, platform_id: str | None = None) -> str:
    platform_id = _normalize_platform_id(platform_id)
    modifier_aliases = _modifier_aliases(platform_id)
    parts = [segment.strip() for segment in str(value or "").split("+")]
    if not parts or any(not part for part in parts):
        raise ValueError("截图热键格式无效")

    modifiers: list[str] = []
    primary_key = ""
    for raw_part in parts:
        lowered = raw_part.lower()
        if lowered in modifier_aliases:
            normalized = modifier_aliases[lowered]
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

    ordered_modifiers = [modifier for modifier in _modifier_order(platform_id) if modifier in modifiers]
    return "+".join([*ordered_modifiers, primary_key])


def hotkey_to_pynput_expression(value: str, platform_id: str | None = None) -> str:
    platform_id = _normalize_platform_id(platform_id)
    modifiers, primary_key = _split_hotkey(value, platform_id)
    mapped_modifiers = [_pynput_modifier_map(platform_id)[modifier] for modifier in modifiers]
    return "+".join([*mapped_modifiers, _primary_key_to_pynput(primary_key)])


def hotkey_to_windows_registration(value: str) -> tuple[int, int]:
    modifiers, primary_key = _split_hotkey(value, PLATFORM_WINDOWS)
    modifier_flags = _MOD_NOREPEAT
    for modifier in modifiers:
        modifier_flags |= _WINDOWS_MODIFIER_MAP[modifier]
    return modifier_flags, _primary_key_to_windows_vk(primary_key)


def _split_hotkey(value: str, platform_id: str | None = None) -> tuple[list[str], str]:
    normalized = normalize_hotkey(value, platform_id)
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


def _primary_key_to_macos_vk(primary_key: str) -> int:
    try:
        return _MACOS_PRIMARY_KEY_MAP[primary_key]
    except KeyError as exc:
        raise ValueError(f"Unsupported macOS hotkey primary key: {primary_key}") from exc


def _macos_hotkey_registration(value: str) -> tuple[int, int]:
    modifiers, primary_key = _split_hotkey(value, PLATFORM_MACOS)
    required_flags = 0
    for modifier in modifiers:
        required_flags |= _MACOS_MODIFIER_FLAGS[modifier]
    return required_flags, _primary_key_to_macos_vk(primary_key)


class _PynputHotkeyListener:
    def __init__(self, hotkey: str, callback: Callable[[], None], *, platform_id: str):
        self._listener = keyboard.GlobalHotKeys(
            {hotkey_to_pynput_expression(hotkey, platform_id): callback}
        )

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        self._listener.stop()


class _MacOSNativeHotkeyListener:
    def __init__(self, hotkey: str, callback: Callable[[], None]):
        if Quartz is None:
            raise RuntimeError("Quartz runtime is unavailable")
        self._callback = callback
        self._hotkey = normalize_hotkey(hotkey, PLATFORM_MACOS)
        self._required_flags, self._primary_vk = _macos_hotkey_registration(self._hotkey)
        self._tap = None
        self._loop = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._startup_error: Exception | None = None
        self._pressed = False
        self._running = False
        self._handler = self._handle_event

    def start(self) -> None:
        self.stop()
        self._ready.clear()
        self._startup_error = None
        self._pressed = False
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            name="AICAHotkeyListener",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=3.0)
        if self._startup_error is not None:
            self.stop()
            raise self._startup_error
        if not self._ready.is_set():
            self.stop()
            raise RuntimeError("Timed out while starting macOS hotkey listener")

    def stop(self) -> None:
        self._running = False
        loop = self._loop
        if loop is not None and Quartz is not None:
            try:
                Quartz.CFRunLoopStop(loop)
            except Exception:
                pass
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)
        self._thread = None
        self._loop = None
        self._tap = None
        self._pressed = False

    def _run_loop(self) -> None:
        try:
            if hasattr(Quartz, "CGPreflightListenEventAccess") and not Quartz.CGPreflightListenEventAccess():
                raise PermissionError("macOS 全局热键需要“辅助功能”和“输入监听”权限")

            # Avoid pynput's key translation path on macOS, which can touch
            # input-source APIs from the event tap thread and crash the process.
            event_mask = (
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
                | Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp)
                | Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged)
            )
            tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionListenOnly,
                event_mask,
                self._handler,
                None,
            )
            if tap is None:
                raise RuntimeError("Failed to create macOS global hotkey event tap")

            loop_source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
            loop = Quartz.CFRunLoopGetCurrent()
            Quartz.CFRunLoopAddSource(loop, loop_source, Quartz.kCFRunLoopDefaultMode)
            Quartz.CGEventTapEnable(tap, True)
            self._tap = tap
            self._loop = loop
        except Exception as exc:
            self._startup_error = exc
            self._running = False
        finally:
            self._ready.set()

        if self._startup_error is not None:
            return

        try:
            while self._running:
                result = Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 1.0, False)
                if result != Quartz.kCFRunLoopRunTimedOut:
                    break
        finally:
            self._loop = None
            self._tap = None
            self._pressed = False

    def _handle_event(self, _proxy, event_type, event, _refcon):
        if event_type in (
            Quartz.kCGEventTapDisabledByTimeout,
            Quartz.kCGEventTapDisabledByUserInput,
        ):
            if self._tap is not None:
                Quartz.CGEventTapEnable(self._tap, True)
            return event

        keycode = int(Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode))
        if event_type == Quartz.kCGEventKeyUp:
            if keycode == self._primary_vk:
                self._pressed = False
            return event

        flags = int(Quartz.CGEventGetFlags(event))
        if event_type == Quartz.kCGEventFlagsChanged:
            if not self._modifiers_match(flags):
                self._pressed = False
            return event

        if event_type != Quartz.kCGEventKeyDown or keycode != self._primary_vk:
            return event

        if int(Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventAutorepeat)):
            return event
        if not self._modifiers_match(flags):
            return event
        if self._pressed:
            return event

        self._pressed = True
        self._callback()
        return event

    def _modifiers_match(self, flags: int) -> bool:
        return (flags & _MACOS_RELEVANT_MODIFIER_MASK) == self._required_flags


class _WindowsNativeHotkeyListener(QAbstractNativeEventFilter):
    def __init__(self, hotkey: str, callback: Callable[[], None]):
        super().__init__()
        self._callback = callback
        self._hotkey = normalize_hotkey(hotkey, PLATFORM_WINDOWS)
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

    def __init__(self, hotkey: str | None = None, parent=None, platform_id: str | None = None):
        super().__init__(parent)
        self._platform_id = _normalize_platform_id(platform_id)
        self._listener: _PynputHotkeyListener | _MacOSNativeHotkeyListener | _WindowsNativeHotkeyListener | None = None
        resolved_hotkey = hotkey if hotkey is not None else default_capture_hotkey(self._platform_id)
        self._hotkey = normalize_hotkey(resolved_hotkey, self._platform_id)

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
        normalized = normalize_hotkey(hotkey, self._platform_id)
        was_running = self._listener is not None
        if normalized == self._hotkey and was_running:
            return self._hotkey
        self._hotkey = normalized
        if was_running:
            self.start()
        self.hotkey_changed.emit(self._hotkey)
        return self._hotkey

    def _create_listener(self) -> _PynputHotkeyListener | _MacOSNativeHotkeyListener | _WindowsNativeHotkeyListener:
        if self._platform_id == PLATFORM_WINDOWS and _QT_AVAILABLE:
            return _WindowsNativeHotkeyListener(self._hotkey, self._on_hotkey)
        if self._platform_id == PLATFORM_MACOS:
            return _MacOSNativeHotkeyListener(self._hotkey, self._on_hotkey)
        return _PynputHotkeyListener(self._hotkey, self._on_hotkey, platform_id=self._platform_id)

    def _on_hotkey(self) -> None:
        self.hotkey_triggered.emit()

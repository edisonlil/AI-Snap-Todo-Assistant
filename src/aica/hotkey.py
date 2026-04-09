"""Global capture hotkey management."""
from __future__ import annotations

import os
import sys

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QObject, pyqtSignal
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
    normalized = normalize_hotkey(value)
    parts = normalized.split("+")
    modifiers = [_PYNPUT_MODIFIER_MAP[part] for part in parts[:-1]]
    primary = _primary_key_to_pynput(parts[-1])
    return "+".join([*modifiers, primary])


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


class HotkeyManager(QObject):
    hotkey_triggered = pyqtSignal()
    hotkey_changed = pyqtSignal(str)

    def __init__(self, hotkey: str = DEFAULT_CAPTURE_HOTKEY, parent=None):
        super().__init__(parent)
        self._listener: keyboard.GlobalHotKeys | None = None
        self._hotkey = normalize_hotkey(hotkey)

    @property
    def hotkey(self) -> str:
        return self._hotkey

    def start(self) -> None:
        self.stop()
        self._listener = keyboard.GlobalHotKeys({hotkey_to_pynput_expression(self._hotkey): self._on_hotkey})
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

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

    def _on_hotkey(self) -> None:
        self.hotkey_triggered.emit()

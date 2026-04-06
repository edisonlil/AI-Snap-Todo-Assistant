"""HotkeyManager：全局热键监听（pynput），跨线程安全触发 Qt 信号"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard


class HotkeyManager(QObject):
    hotkey_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        self._listener = keyboard.GlobalHotKeys(
            {"<alt>+a": self._on_hotkey}
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _on_hotkey(self) -> None:
        # pynput 回调在独立线程，通过 Qt 信号安全传递到主线程
        self.hotkey_triggered.emit()

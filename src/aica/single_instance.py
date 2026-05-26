"""Single-instance guard for AICA across platforms."""
from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

try:
    import fcntl
except Exception:  # pragma: no cover - unavailable on Windows
    fcntl = None  # type: ignore[assignment]

from aica.paths import legacy_app_data_dir, safe_expand_user_path
from aica.runtime import PLATFORM_WINDOWS, current_platform


ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Local\\AICA_AI_Capture_Assistant_SingleInstance"
LOCK_FILE_NAME = "aica.lock"
_PROCESS_LOCKS: set[str] = set()


def is_already_running(last_error: int) -> bool:
    return last_error == ERROR_ALREADY_EXISTS


class SingleInstanceGuard:
    def __init__(
        self,
        name: str = MUTEX_NAME,
        *,
        lock_file: str | Path | None = None,
        platform_id: str | None = None,
    ):
        self._name = name
        self._platform_id = platform_id or current_platform()
        self._handle: wintypes.HANDLE | None = None
        self._lock_file = safe_expand_user_path(lock_file) if lock_file is not None else legacy_app_data_dir() / LOCK_FILE_NAME
        self._lock_handle = None

    def acquire(self) -> bool:
        if self._platform_id == PLATFORM_WINDOWS:
            return self._acquire_windows_mutex()
        return self._acquire_lock_file()

    def release(self) -> None:
        if self._platform_id == PLATFORM_WINDOWS:
            self._release_windows_mutex()
            return
        self._release_lock_file()

    def _acquire_windows_mutex(self) -> bool:
        kernel32 = getattr(ctypes, "windll", None)
        if kernel32 is None or not hasattr(kernel32, "kernel32"):
            return True

        kernel32 = kernel32.kernel32
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD

        handle = kernel32.CreateMutexW(None, False, self._name)
        if not handle:
            return True

        self._handle = handle
        return not is_already_running(kernel32.GetLastError())

    def _release_windows_mutex(self) -> None:
        if self._handle is None:
            return

        kernel32 = getattr(ctypes, "windll", None)
        if kernel32 is not None and hasattr(kernel32, "kernel32"):
            kernel32.kernel32.CloseHandle(self._handle)
        self._handle = None

    def _acquire_lock_file(self) -> bool:
        lock_key = str(self._lock_file.resolve())
        if lock_key in _PROCESS_LOCKS:
            return False
        if fcntl is None:
            _PROCESS_LOCKS.add(lock_key)
            return True
        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        handle = self._lock_file.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            return False

        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        self._lock_handle = handle
        _PROCESS_LOCKS.add(lock_key)
        return True

    def _release_lock_file(self) -> None:
        handle = self._lock_handle
        self._lock_handle = None
        lock_key = str(self._lock_file.resolve())
        if handle is None:
            _PROCESS_LOCKS.discard(lock_key)
            return
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            _PROCESS_LOCKS.discard(lock_key)


def show_already_running_message(title: str = "AI Capture Assistant") -> None:
    if current_platform() == PLATFORM_WINDOWS:
        user32 = getattr(ctypes, "windll", None)
        if user32 is None or not hasattr(user32, "user32"):
            return

        user32.user32.MessageBoxW(
            None,
            "AI Capture Assistant 已经在运行，不能重复启动。",
            title,
            0x00000040,
        )
        return

    from PyQt6.QtWidgets import QApplication, QMessageBox

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication([])
    QMessageBox.information(None, title, "AI Capture Assistant 已经在运行，不能重复启动。")
    if owns_app and app is not None:
        app.quit()

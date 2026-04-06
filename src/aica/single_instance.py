"""Windows single-instance guard for AICA."""
from __future__ import annotations

import ctypes
from ctypes import wintypes


ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "Local\\AICA_AI_Capture_Assistant_SingleInstance"


def is_already_running(last_error: int) -> bool:
    return last_error == ERROR_ALREADY_EXISTS


class SingleInstanceGuard:
    def __init__(self, name: str = MUTEX_NAME):
        self._name = name
        self._handle: wintypes.HANDLE | None = None

    def acquire(self) -> bool:
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

    def release(self) -> None:
        if self._handle is None:
            return

        kernel32 = getattr(ctypes, "windll", None)
        if kernel32 is not None and hasattr(kernel32, "kernel32"):
            kernel32.kernel32.CloseHandle(self._handle)
        self._handle = None


def show_already_running_message(title: str = "AI Capture Assistant") -> None:
    user32 = getattr(ctypes, "windll", None)
    if user32 is None or not hasattr(user32, "user32"):
        return

    user32.user32.MessageBoxW(
        None,
        "AI Capture Assistant 已经在运行，不能重复启动。",
        title,
        0x00000040,
    )

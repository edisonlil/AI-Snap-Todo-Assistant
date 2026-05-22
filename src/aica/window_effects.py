"""Small platform window effects shared by Qt surfaces."""
from __future__ import annotations

import sys

_DWMWA_BORDER_COLOR = 34
_DWMWA_COLOR_NONE = 0xFFFFFFFE


def disable_windows_window_border(widget) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(widget.winId())
        color = ctypes.c_uint32(_DWMWA_COLOR_NONE)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint32(_DWMWA_BORDER_COLOR),
            ctypes.byref(color),
            ctypes.c_uint32(ctypes.sizeof(color)),
        )
    except Exception:
        return

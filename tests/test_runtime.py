from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.runtime import PLATFORM_MACOS, PLATFORM_WINDOWS, RuntimeCapabilities


class _WindowType:
    FramelessWindowHint = 0x01
    WindowStaysOnTopHint = 0x02
    Tool = 0x04
    Window = 0x08
    WindowSystemMenuHint = 0x10
    WindowMinMaxButtonsHint = 0x20


def test_floating_tool_window_flags_include_topmost_when_requested() -> None:
    capabilities = RuntimeCapabilities(platform_id=PLATFORM_WINDOWS)

    flags = capabilities.floating_tool_window_flags(_WindowType, stays_on_top=True)

    assert flags & _WindowType.FramelessWindowHint
    assert flags & _WindowType.WindowStaysOnTopHint
    assert flags & _WindowType.Tool


def test_floating_tool_window_flags_drop_topmost_when_unpinned() -> None:
    capabilities = RuntimeCapabilities(platform_id=PLATFORM_MACOS)

    flags = capabilities.floating_tool_window_flags(_WindowType, stays_on_top=False)

    assert flags & _WindowType.FramelessWindowHint
    assert not (flags & _WindowType.WindowStaysOnTopHint)
    assert flags & _WindowType.Window


def test_control_panel_window_flags_keep_frameless_on_windows() -> None:
    capabilities = RuntimeCapabilities(platform_id=PLATFORM_WINDOWS)

    flags = capabilities.control_panel_window_flags(_WindowType)

    assert flags & _WindowType.Window
    assert flags & _WindowType.FramelessWindowHint
    assert flags & _WindowType.WindowSystemMenuHint
    assert flags & _WindowType.WindowMinMaxButtonsHint


def test_control_panel_window_flags_keep_frameless_on_macos() -> None:
    capabilities = RuntimeCapabilities(platform_id=PLATFORM_MACOS)

    flags = capabilities.control_panel_window_flags(_WindowType)

    assert flags & _WindowType.Window
    assert flags & _WindowType.FramelessWindowHint
    assert flags & _WindowType.WindowSystemMenuHint
    assert flags & _WindowType.WindowMinMaxButtonsHint

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.control_panel import hotkey_from_qt_key_event  # noqa: E402
from aica.hotkey import (  # noqa: E402
    HotkeyManager,
    _macos_hotkey_registration,
    hotkey_to_pynput_expression,
    hotkey_to_windows_registration,
    normalize_hotkey,
)
from aica.runtime import (  # noqa: E402
    DEFAULT_MACOS_CAPTURE_HOTKEY,
    DEFAULT_WINDOWS_CAPTURE_HOTKEY,
    PLATFORM_MACOS,
    PLATFORM_WINDOWS,
    default_capture_hotkey,
)


def test_normalize_hotkey_orders_modifiers_and_uppercases_primary_key() -> None:
    assert normalize_hotkey("shift+ctrl+a", PLATFORM_WINDOWS) == "Ctrl+Shift+A"


def test_hotkey_to_pynput_expression_maps_special_keys() -> None:
    assert hotkey_to_pynput_expression("Alt+Enter", PLATFORM_WINDOWS) == "<alt>+<enter>"


def test_hotkey_to_windows_registration_includes_no_repeat_modifier() -> None:
    modifier_flags, vk = hotkey_to_windows_registration("Ctrl+Shift+F12")

    assert modifier_flags == 0x4000 | 0x0002 | 0x0004
    assert vk == 0x7B


def test_normalize_hotkey_rejects_duplicate_modifiers() -> None:
    with pytest.raises(ValueError):
        normalize_hotkey("Ctrl+Ctrl+A", PLATFORM_WINDOWS)


def test_normalize_hotkey_uses_macos_modifier_names() -> None:
    assert normalize_hotkey("cmd+alt+a", PLATFORM_MACOS) == "Command+Option+A"


def test_hotkey_to_pynput_expression_maps_macos_command_key() -> None:
    assert hotkey_to_pynput_expression("Command+Shift+A", PLATFORM_MACOS) == "<cmd>+<shift>+a"


def test_macos_hotkey_registration_builds_flags_and_keycode() -> None:
    modifier_flags, vk = _macos_hotkey_registration("Command+Option+A")

    assert modifier_flags != 0
    assert vk == 0


def test_default_capture_hotkey_is_platform_specific() -> None:
    assert default_capture_hotkey(PLATFORM_WINDOWS) == DEFAULT_WINDOWS_CAPTURE_HOTKEY
    assert default_capture_hotkey(PLATFORM_MACOS) == DEFAULT_MACOS_CAPTURE_HOTKEY


def test_hotkey_manager_restarts_listener_when_hotkey_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Listener:
        def __init__(self) -> None:
            self.started = 0
            self.stopped = 0

        def start(self) -> None:
            self.started += 1

        def stop(self) -> None:
            self.stopped += 1

    manager = HotkeyManager("Alt+A", platform_id=PLATFORM_WINDOWS)
    listeners: list[_Listener] = []

    def _create_listener() -> _Listener:
        listener = _Listener()
        listeners.append(listener)
        return listener

    monkeypatch.setattr(manager, "_create_listener", _create_listener)

    manager.start()
    manager.update_hotkey("Ctrl+B")

    assert manager.hotkey == "Ctrl+B"
    assert len(listeners) == 2
    assert listeners[0].started == 1
    assert listeners[0].stopped == 1
    assert listeners[1].started == 1
    assert listeners[1].stopped == 0


def test_hotkey_manager_keeps_existing_listener_when_hotkey_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Listener:
        def __init__(self) -> None:
            self.started = 0
            self.stopped = 0

        def start(self) -> None:
            self.started += 1

        def stop(self) -> None:
            self.stopped += 1

    manager = HotkeyManager("Alt+A", platform_id=PLATFORM_WINDOWS)
    listeners: list[_Listener] = []

    def _create_listener() -> _Listener:
        listener = _Listener()
        listeners.append(listener)
        return listener

    monkeypatch.setattr(manager, "_create_listener", _create_listener)

    manager.start()
    manager.update_hotkey("alt+a")

    assert manager.hotkey == "Alt+A"
    assert len(listeners) == 1
    assert listeners[0].started == 1
    assert listeners[0].stopped == 0


def test_hotkey_manager_uses_windows_native_listener_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[tuple[str, str]] = []

    class _WindowsListener:
        def __init__(self, hotkey: str, _callback) -> None:
            created.append(("windows", hotkey))

    monkeypatch.setattr("aica.hotkey._QT_AVAILABLE", True)
    monkeypatch.setattr("aica.hotkey._WindowsNativeHotkeyListener", _WindowsListener)

    manager = HotkeyManager("Alt+A", platform_id=PLATFORM_WINDOWS)
    listener = manager._create_listener()  # noqa: SLF001

    assert created == [("windows", "Alt+A")]
    assert isinstance(listener, _WindowsListener)


def test_hotkey_manager_uses_native_listener_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[str] = []

    class _MacOSListener:
        def __init__(self, hotkey: str, _callback) -> None:
            created.append(hotkey)

    monkeypatch.setattr("aica.hotkey._MacOSNativeHotkeyListener", _MacOSListener)

    manager = HotkeyManager("Command+Shift+A", platform_id=PLATFORM_MACOS)
    listener = manager._create_listener()  # noqa: SLF001

    assert created == ["Command+Shift+A"]
    assert isinstance(listener, _MacOSListener)


def test_hotkey_from_qt_key_event_builds_windows_shortcut() -> None:
    result = hotkey_from_qt_key_event(
        ord("A"),
        0x04000000 | 0x02000000,
        "a",
        platform_id=PLATFORM_WINDOWS,
    )

    assert result == "Ctrl+Shift+A"


def test_hotkey_from_qt_key_event_builds_macos_shortcut() -> None:
    result = hotkey_from_qt_key_event(
        ord("A"),
        0x04000000 | 0x08000000,
        "a",
        platform_id=PLATFORM_MACOS,
    )

    assert result == "Command+Option+A"


def test_hotkey_from_qt_key_event_builds_macos_control_shortcut() -> None:
    result = hotkey_from_qt_key_event(
        ord("A"),
        0x10000000 | 0x08000000,
        "a",
        platform_id=PLATFORM_MACOS,
    )

    assert result == "Option+Control+A"


def test_hotkey_from_qt_key_event_supports_special_primary_keys() -> None:
    result = hotkey_from_qt_key_event(
        0x01000004,
        0x08000000,
        "",
        platform_id=PLATFORM_WINDOWS,
    )

    assert result == "Alt+Enter"


def test_hotkey_from_qt_key_event_ignores_modifier_only_keys() -> None:
    assert hotkey_from_qt_key_event(
        0x01000021,
        0x04000000,
        "",
        platform_id=PLATFORM_WINDOWS,
    ) is None

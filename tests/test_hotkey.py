from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.hotkey import (  # noqa: E402
    HotkeyManager,
    hotkey_to_pynput_expression,
    hotkey_to_windows_registration,
    normalize_hotkey,
)


def test_normalize_hotkey_orders_modifiers_and_uppercases_primary_key() -> None:
    assert normalize_hotkey("shift+ctrl+a") == "Ctrl+Shift+A"


def test_hotkey_to_pynput_expression_maps_special_keys() -> None:
    assert hotkey_to_pynput_expression("Alt+Enter") == "<alt>+<enter>"


def test_hotkey_to_windows_registration_includes_no_repeat_modifier() -> None:
    modifier_flags, vk = hotkey_to_windows_registration("Ctrl+Shift+F12")

    assert modifier_flags == 0x4000 | 0x0002 | 0x0004
    assert vk == 0x7B


def test_normalize_hotkey_rejects_duplicate_modifiers() -> None:
    with pytest.raises(ValueError):
        normalize_hotkey("Ctrl+Ctrl+A")


def test_hotkey_manager_restarts_listener_when_hotkey_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Listener:
        def __init__(self) -> None:
            self.started = 0
            self.stopped = 0

        def start(self) -> None:
            self.started += 1

        def stop(self) -> None:
            self.stopped += 1

    manager = HotkeyManager("Alt+A")
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

    manager = HotkeyManager("Alt+A")
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

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.main import _build_hotkey_manager, _notify_plan_export_error, _notify_plan_export_success, _start_hotkey_listener  # noqa: E402


def test_build_hotkey_manager_falls_back_to_platform_default(monkeypatch) -> None:
    saved_configs: list[str] = []

    class _ConfigManager:
        def save(self, config) -> None:
            saved_configs.append(config.hotkeys.capture)

    class _HotkeyManager:
        def __init__(self, hotkey: str, platform_id: str | None = None) -> None:
            if hotkey == "bad":
                raise ValueError("invalid hotkey")
            self.hotkey = hotkey
            self.platform_id = platform_id

    monkeypatch.setattr("aica.main.HotkeyManager", _HotkeyManager)
    monkeypatch.setattr(
        "aica.main.RUNTIME_CAPABILITIES",
        SimpleNamespace(default_capture_hotkey="Command+Shift+A", platform_id="macos"),
    )

    config = SimpleNamespace(hotkeys=SimpleNamespace(capture="bad"))
    manager = _build_hotkey_manager(_ConfigManager(), config)

    assert manager.hotkey == "Command+Shift+A"
    assert config.hotkeys.capture == "Command+Shift+A"
    assert saved_configs == ["Command+Shift+A"]


def test_start_hotkey_listener_returns_exception_instead_of_raising(tmp_path: Path) -> None:
    class _HotkeyManager:
        def start(self) -> None:
            raise RuntimeError("permission denied")

    error = _start_hotkey_listener(_HotkeyManager(), tmp_path / "startup.log")

    assert isinstance(error, RuntimeError)
    assert "permission denied" in str(error)


def test_notify_plan_export_error_uses_bottom_right_notification() -> None:
    calls: list[tuple[str, str, int, str]] = []

    class _NotificationBridge:
        def notify(self, level: str, message: str, duration_ms: int, source: str) -> None:
            calls.append((level, message, duration_ms, source))

    _notify_plan_export_error(_NotificationBridge(), "导出方案失败，模型调用错误")

    assert calls == [("error", "导出方案失败，模型调用错误", 5200, "plan_export")]


def test_notify_plan_export_error_ignores_empty_message() -> None:
    calls: list[tuple[str, str, int, str]] = []

    class _NotificationBridge:
        def notify(self, level: str, message: str, duration_ms: int, source: str) -> None:
            calls.append((level, message, duration_ms, source))

    _notify_plan_export_error(_NotificationBridge(), "   ")

    assert calls == []


def test_notify_plan_export_success_uses_bottom_right_notification() -> None:
    calls: list[tuple[str, str, int, str]] = []

    class _NotificationBridge:
        def notify(self, level: str, message: str, duration_ms: int, source: str) -> None:
            calls.append((level, message, duration_ms, source))

    _notify_plan_export_success(_NotificationBridge(), "C:/tmp/方案.md")

    assert calls == [("success", "方案已导出到: C:/tmp/方案.md", 3600, "plan_export")]


def test_notify_plan_export_success_ignores_empty_path() -> None:
    calls: list[tuple[str, str, int, str]] = []

    class _NotificationBridge:
        def notify(self, level: str, message: str, duration_ms: int, source: str) -> None:
            calls.append((level, message, duration_ms, source))

    _notify_plan_export_success(_NotificationBridge(), " ")

    assert calls == []

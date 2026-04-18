from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.main import _build_hotkey_manager, _start_hotkey_listener  # noqa: E402


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

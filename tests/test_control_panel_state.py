from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.control_panel_state import (  # noqa: E402
    build_script_integration,
    describe_script_integration_support,
    update_script_integration_path,
)


def test_build_script_integration_uses_windows_python_launcher(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("aica.control_panel_state.current_platform", lambda: "windows")

    integration = build_script_integration("scripts/sample.py")

    assert integration["command"] == "py"
    assert integration["args"] == [str(Path("scripts/sample.py").expanduser().resolve())]


def test_build_script_integration_uses_current_python_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("aica.control_panel_state.current_platform", lambda: "macos")

    integration = build_script_integration("scripts/sample.py")

    assert Path(str(integration["command"])).name.startswith("python")
    assert integration["args"] == [str(Path("scripts/sample.py").expanduser().resolve())]


def test_build_script_integration_supports_shell_scripts_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("aica.control_panel_state.current_platform", lambda: "macos")

    integration = build_script_integration("scripts/sample.sh")

    assert integration["command"] == "/bin/sh"
    assert integration["args"] == [str(Path("scripts/sample.sh").expanduser().resolve())]


def test_build_script_integration_rejects_windows_only_scripts_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("aica.control_panel_state.current_platform", lambda: "macos")

    with pytest.raises(ValueError):
        build_script_integration("scripts/sample.ps1")


def test_update_script_integration_path_rebuilds_command_for_current_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("aica.control_panel_state.current_platform", lambda: "macos")
    integration = {
        "id": "sample",
        "name": "sample",
        "enabled": True,
        "type": "script",
        "command": "py",
        "args": ["old.py"],
        "cwd": ".",
        "timeout_seconds": 8,
        "env": {},
    }

    updated = update_script_integration_path(integration, "scripts/new.py")

    assert Path(str(updated["command"])).name.startswith("python")
    assert updated["args"] == [str(Path("scripts/new.py").expanduser().resolve())]


def test_describe_script_integration_support_marks_windows_scripts_unsupported_on_macos() -> None:
    supported, message = describe_script_integration_support(
        {
            "command": "powershell",
            "args": ["-ExecutionPolicy", "Bypass", "-File", "sample.ps1"],
        },
        platform_id="macos",
    )

    assert supported is False
    assert "Windows" in message

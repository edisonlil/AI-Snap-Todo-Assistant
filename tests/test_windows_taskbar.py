from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.app_commands import COMMAND_ARG, COMMAND_CAPTURE  # noqa: E402
from aica.windows_taskbar import build_taskbar_tasks, install_windows_taskbar_tasks  # noqa: E402


def test_build_taskbar_tasks_adds_capture_command_only(monkeypatch, tmp_path: Path) -> None:
    icon_path = tmp_path / "aica_icon.ico"
    launcher_path = tmp_path / "run_aica.py"
    monkeypatch.setattr("aica.windows_taskbar.icon_file", lambda _platform: icon_path)
    monkeypatch.setattr("aica.windows_taskbar.project_root", lambda: tmp_path)

    tasks = build_taskbar_tasks("Chattodo.exe")

    assert [task["title"] for task in tasks] == ["开始截图"]
    assert [task["path"] for task in tasks] == ["Chattodo.exe"]
    assert [task["arguments"] for task in tasks] == [
        f'"{launcher_path}" {COMMAND_ARG} {COMMAND_CAPTURE}',
    ]
    assert [task["icon"] for task in tasks] == [str(icon_path)]


def test_build_taskbar_tasks_use_exe_directly_when_packaged(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("aica.windows_taskbar.icon_file", lambda _platform: tmp_path / "aica_icon.ico")
    monkeypatch.setattr("aica.windows_taskbar.sys.frozen", True, raising=False)

    tasks = build_taskbar_tasks("Chattodo.exe")

    assert [task["arguments"] for task in tasks] == [
        f"{COMMAND_ARG} {COMMAND_CAPTURE}",
    ]


def test_install_windows_taskbar_tasks_skips_non_windows() -> None:
    assert install_windows_taskbar_tasks(platform_id="macos") is False

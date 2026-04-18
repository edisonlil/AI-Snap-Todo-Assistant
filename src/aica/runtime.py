"""Runtime capability helpers for platform-specific behavior."""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


PLATFORM_WINDOWS = "windows"
PLATFORM_MACOS = "macos"
PLATFORM_OTHER = "other"

DEFAULT_WINDOWS_CAPTURE_HOTKEY = "Alt+A"
DEFAULT_MACOS_CAPTURE_HOTKEY = "Command+Shift+A"

WINDOWS_UI_FONT = "Microsoft YaHei UI"
MACOS_UI_FONT = "PingFang SC"
OTHER_UI_FONT = "Sans Serif"

WINDOWS_WIDGET_FONT_CSS = "'Segoe UI Variable Text', 'Microsoft YaHei UI', sans-serif"
MACOS_WIDGET_FONT_CSS = "'PingFang SC', 'Hiragino Sans GB', sans-serif"
OTHER_WIDGET_FONT_CSS = "'Noto Sans CJK SC', sans-serif"

WINDOWS_MONO_FONT_CSS = "'Cascadia Mono', 'Consolas', 'Microsoft YaHei UI', monospace"
MACOS_MONO_FONT_CSS = "'SF Mono', 'Menlo', 'PingFang SC', monospace"
OTHER_MONO_FONT_CSS = "'Noto Sans Mono CJK SC', monospace"

WINDOWS_SCRIPT_FILTER = "脚本文件 (*.py *.pyw *.ps1 *.bat *.cmd *.exe);;所有文件 (*.*)"
MACOS_SCRIPT_FILTER = "脚本文件 (*.py *.pyw *.sh);;所有文件 (*.*)"

WINDOWS_SCRIPT_SUFFIXES = frozenset({".py", ".pyw", ".ps1", ".bat", ".cmd", ".exe"})
MACOS_SCRIPT_SUFFIXES = frozenset({".py", ".pyw", ".sh"})
_WINDOWS_ONLY_SCRIPT_SUFFIXES = frozenset({".ps1", ".bat", ".cmd", ".exe"})


def current_platform() -> str:
    if sys.platform.startswith("win"):
        return PLATFORM_WINDOWS
    if sys.platform == "darwin":
        return PLATFORM_MACOS
    return PLATFORM_OTHER


def default_capture_hotkey(platform_id: str | None = None) -> str:
    platform_id = platform_id or current_platform()
    if platform_id == PLATFORM_MACOS:
        return DEFAULT_MACOS_CAPTURE_HOTKEY
    return DEFAULT_WINDOWS_CAPTURE_HOTKEY


def ui_font_family(platform_id: str | None = None) -> str:
    platform_id = platform_id or current_platform()
    if platform_id == PLATFORM_MACOS:
        return MACOS_UI_FONT
    if platform_id == PLATFORM_WINDOWS:
        return WINDOWS_UI_FONT
    return OTHER_UI_FONT


def widget_font_css(platform_id: str | None = None) -> str:
    platform_id = platform_id or current_platform()
    if platform_id == PLATFORM_MACOS:
        return MACOS_WIDGET_FONT_CSS
    if platform_id == PLATFORM_WINDOWS:
        return WINDOWS_WIDGET_FONT_CSS
    return OTHER_WIDGET_FONT_CSS


def monospace_font_css(platform_id: str | None = None) -> str:
    platform_id = platform_id or current_platform()
    if platform_id == PLATFORM_MACOS:
        return MACOS_MONO_FONT_CSS
    if platform_id == PLATFORM_WINDOWS:
        return WINDOWS_MONO_FONT_CSS
    return OTHER_MONO_FONT_CSS


def script_file_dialog_filter(platform_id: str | None = None) -> str:
    platform_id = platform_id or current_platform()
    return WINDOWS_SCRIPT_FILTER if platform_id == PLATFORM_WINDOWS else MACOS_SCRIPT_FILTER


def supported_script_suffixes(platform_id: str | None = None) -> frozenset[str]:
    platform_id = platform_id or current_platform()
    return WINDOWS_SCRIPT_SUFFIXES if platform_id == PLATFORM_WINDOWS else MACOS_SCRIPT_SUFFIXES


def _supports_python_launcher(platform_id: str) -> bool:
    return platform_id == PLATFORM_WINDOWS


def python_command(platform_id: str | None = None) -> str:
    platform_id = platform_id or current_platform()
    if _supports_python_launcher(platform_id):
        return "py"
    executable = str(Path(sys.executable or "").expanduser())
    if executable:
        return executable
    return shutil.which("python3") or "python3"


def build_script_command(script_path: Path, platform_id: str | None = None) -> tuple[str, list[str]]:
    platform_id = platform_id or current_platform()
    suffix = script_path.suffix.lower()
    script_text = str(script_path)

    if suffix in {".py", ".pyw"}:
        return python_command(platform_id), [script_text]
    if suffix == ".sh":
        return "/bin/sh", [script_text]
    if suffix == ".ps1":
        if platform_id != PLATFORM_WINDOWS:
            raise ValueError("当前平台不支持 PowerShell 脚本集成")
        return "powershell", ["-ExecutionPolicy", "Bypass", "-File", script_text]
    if suffix in {".bat", ".cmd", ".exe"}:
        if platform_id != PLATFORM_WINDOWS:
            raise ValueError("当前平台不支持 Windows 脚本集成")
        return script_text, []
    if platform_id == PLATFORM_WINDOWS:
        return script_text, []
    raise ValueError("当前平台仅支持 .py、.pyw 和 .sh 脚本")


def describe_script_support_for_path(script_path: str | Path, platform_id: str | None = None) -> tuple[bool, str]:
    platform_id = platform_id or current_platform()
    path = Path(script_path)
    suffix = path.suffix.lower()
    if not suffix:
        return True, ""
    if suffix in supported_script_suffixes(platform_id):
        return True, ""
    if suffix in _WINDOWS_ONLY_SCRIPT_SUFFIXES and platform_id != PLATFORM_WINDOWS:
        return False, "当前平台不支持 Windows 专用脚本"
    return False, "当前平台不支持该脚本类型"


def describe_script_support_for_command(
    command: str,
    args: list[str] | None = None,
    *,
    platform_id: str | None = None,
) -> tuple[bool, str]:
    platform_id = platform_id or current_platform()
    args = list(args or [])
    command_path = Path(str(command or "").strip())
    command_name = command_path.name.lower()

    if not command_name:
        return False, "脚本命令为空"
    if command_name in {"py", "py.exe", "python", "python.exe", "pythonw.exe", "python3"}:
        target = next((arg for arg in args if not str(arg).startswith("-")), "")
        if not target:
            return True, ""
        return describe_script_support_for_path(target, platform_id)
    if command_name in {"powershell", "powershell.exe"}:
        if platform_id != PLATFORM_WINDOWS:
            return False, "当前平台不支持 Windows PowerShell 脚本"
        return True, ""
    if command_name in {"sh", "bash"}:
        if platform_id == PLATFORM_WINDOWS:
            return False, "当前平台默认不支持 Shell 脚本集成"
        return True, ""

    target = next(
        (
            arg
            for arg in reversed(args)
            if str(arg).strip() and not str(arg).startswith("-")
        ),
        str(command_path),
    )
    return describe_script_support_for_path(target, platform_id)


def hotkey_failure_message(
    hotkey: str,
    error: Exception,
    *,
    log_file: Path,
    platform_id: str | None = None,
) -> str:
    platform_id = platform_id or current_platform()
    if platform_id == PLATFORM_MACOS:
        return (
            f"全局截图热键 {hotkey} 暂时不可用，但 AICA 已继续启动。\n"
            "你仍然可以通过菜单栏图标打开控制面板。\n"
            "请在“系统设置 > 隐私与安全性”中为当前终端或 AICA 开启“辅助功能”和“输入监听”权限，"
            "然后重启应用后重试。\n\n"
            f"日志: {log_file}\n"
            f"原因: {error}"
        )
    return (
        f"全局截图热键 {hotkey} 注册失败，但 AICA 已继续启动。\n"
        "你仍然可以通过系统托盘图标打开控制面板。\n\n"
        f"日志: {log_file}\n"
        f"原因: {error}"
    )


def _compose_window_flags(window_type, names: tuple[str, ...]):
    flags = getattr(window_type, names[0])
    for name in names[1:]:
        flags |= getattr(window_type, name)
    return flags


@dataclass(frozen=True)
class RuntimeCapabilities:
    platform_id: str = current_platform()

    @property
    def is_windows(self) -> bool:
        return self.platform_id == PLATFORM_WINDOWS

    @property
    def is_macos(self) -> bool:
        return self.platform_id == PLATFORM_MACOS

    @property
    def default_capture_hotkey(self) -> str:
        return default_capture_hotkey(self.platform_id)

    @property
    def ui_font(self) -> str:
        return ui_font_family(self.platform_id)

    @property
    def widget_font_css(self) -> str:
        return widget_font_css(self.platform_id)

    @property
    def monospace_font_css(self) -> str:
        return monospace_font_css(self.platform_id)

    @property
    def integration_script_filter(self) -> str:
        return script_file_dialog_filter(self.platform_id)

    def floating_tool_window_flags(self, window_type):
        names = ("FramelessWindowHint", "WindowStaysOnTopHint")
        if self.is_windows:
            names += ("Tool",)
        else:
            names += ("Window",)
        return _compose_window_flags(window_type, names)

    def overlay_window_flags(self, window_type):
        return self.floating_tool_window_flags(window_type)

    def control_panel_window_flags(self, window_type):
        names = ("Window", "FramelessWindowHint", "WindowSystemMenuHint", "WindowMinMaxButtonsHint")
        return _compose_window_flags(window_type, names)


RUNTIME_CAPABILITIES = RuntimeCapabilities()

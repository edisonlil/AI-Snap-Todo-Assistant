from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.main import _build_hotkey_manager, _setup_exception_handler, _start_hotkey_listener  # noqa: E402


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


def test_exception_handler_exits_when_error_dialog_fails(monkeypatch, tmp_path: Path) -> None:
    exit_codes: list[int] = []

    class _MessageBox:
        @staticmethod
        def critical(*_args) -> None:
            raise RecursionError("dialog recursion")

    class _Application:
        _app = object()

        @staticmethod
        def instance():
            return _Application._app

    def _request_shutdown(exit_code: int = 1) -> None:
        exit_codes.append(exit_code)

    monkeypatch.setattr("aica.main._resolve_error_log_file", lambda: tmp_path / "error.log")
    monkeypatch.setattr("aica.main.QMessageBox", _MessageBox)
    monkeypatch.setattr("aica.main.QApplication", _Application)
    monkeypatch.setattr("aica.main._request_shutdown_after_unhandled_exception", _request_shutdown)

    log_file = _setup_exception_handler()

    try:
        sys.excepthook(RuntimeError, RuntimeError("boom"), None)
    except SystemExit as exc:
        exit_codes.append(exc.code)

    assert exit_codes == [1]
    assert "RuntimeError: boom" in log_file.read_text(encoding="utf-8")
    assert "unhandled exception dialog failed: dialog recursion" in log_file.read_text(encoding="utf-8")


def test_exception_handler_skips_dialog_before_qapplication_exists(monkeypatch, tmp_path: Path) -> None:
    exit_codes: list[int] = []

    class _MessageBox:
        @staticmethod
        def critical(*_args) -> None:
            raise AssertionError("dialog should not be shown")

    class _Application:
        @staticmethod
        def instance():
            return None

    def _request_shutdown(exit_code: int = 1) -> None:
        exit_codes.append(exit_code)

    monkeypatch.setattr("aica.main._resolve_error_log_file", lambda: tmp_path / "error.log")
    monkeypatch.setattr("aica.main.QMessageBox", _MessageBox)
    monkeypatch.setattr("aica.main.QApplication", _Application)
    monkeypatch.setattr("aica.main._request_shutdown_after_unhandled_exception", _request_shutdown)

    log_file = _setup_exception_handler()

    sys.excepthook(RuntimeError, RuntimeError("startup boom"), None)

    assert exit_codes == [1]
    assert "RuntimeError: startup boom" in log_file.read_text(encoding="utf-8")
    assert "unhandled exception dialog skipped: QApplication unavailable" in log_file.read_text(encoding="utf-8")


def test_exception_handler_requests_qapplication_exit(monkeypatch, tmp_path: Path) -> None:
    exit_codes: list[int] = []

    class _MessageBox:
        @staticmethod
        def critical(*_args) -> None:
            return None

    class _App:
        def exit(self, code: int) -> None:
            exit_codes.append(code)

    class _Application:
        @staticmethod
        def instance():
            return _App()

    monkeypatch.setattr("aica.main._resolve_error_log_file", lambda: tmp_path / "error.log")
    monkeypatch.setattr("aica.main.QMessageBox", _MessageBox)
    monkeypatch.setattr("aica.main.QApplication", _Application)

    _setup_exception_handler()

    sys.excepthook(ValueError, ValueError("bad value"), None)

    assert exit_codes == [1]

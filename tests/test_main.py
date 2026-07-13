from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

from PyQt6.QtCore import Qt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.main import (  # noqa: E402
    _TOOLBAR_BASE_SCENARIOS,
    _TOOLBAR_SELECTED_TODO_SCENARIOS,
    _apply_application_icon,
    _build_hotkey_manager,
    _has_visible_top_level_widget,
    _install_windows_taskbar_handlers,
    _install_macos_dock_handlers,
    _MacOSDockReopenHandler,
    _set_windows_app_user_model_id,
    _setup_exception_handler,
    _show_startup_control_panel,
    _start_hotkey_listener,
)


def test_toolbar_scenarios_only_show_problem_conclusion_for_selected_todo() -> None:
    assert _TOOLBAR_BASE_SCENARIOS == {"工单跟进": "chat_feedback"}
    assert _TOOLBAR_SELECTED_TODO_SCENARIOS == {
        "工单跟进": "chat_feedback",
        "问题结论": "problem_conclusion",
    }


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


def test_set_windows_app_user_model_id_uses_shell_api(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    class _Shell32:
        @staticmethod
        def SetCurrentProcessExplicitAppUserModelID(app_id: str) -> None:
            calls.append(app_id)

    monkeypatch.setattr("aica.main.RUNTIME_CAPABILITIES", SimpleNamespace(is_windows=True))
    monkeypatch.setattr("aica.main.ctypes", SimpleNamespace(windll=SimpleNamespace(shell32=_Shell32)))

    log_file = tmp_path / "startup.log"
    _set_windows_app_user_model_id(log_file)

    assert calls == ["edison.Chattodo"]
    assert "windows app user model id set=edison.Chattodo" in log_file.read_text(encoding="utf-8")


def test_install_windows_taskbar_handlers_logs_install_result(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("aica.main.RUNTIME_CAPABILITIES", SimpleNamespace(is_windows=True))
    monkeypatch.setattr("aica.main.install_windows_taskbar_tasks", lambda: True)

    log_file = tmp_path / "startup.log"
    _install_windows_taskbar_handlers(log_file)

    assert "windows taskbar tasks installed=True" in log_file.read_text(encoding="utf-8")


def test_install_windows_taskbar_handlers_skips_non_windows(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("aica.main.RUNTIME_CAPABILITIES", SimpleNamespace(is_windows=False))

    log_file = tmp_path / "startup.log"
    _install_windows_taskbar_handlers(log_file)

    assert not log_file.exists()


def test_apply_application_icon_sets_chattodo_name_and_icon(monkeypatch, tmp_path: Path) -> None:
    icon_path = tmp_path / "aica_icon.png"
    icon_path.write_bytes(b"icon")
    created_icons: list[str] = []

    class _Icon:
        def __init__(self, path: str) -> None:
            created_icons.append(path)
            self.path = path

    class _Application:
        def __init__(self) -> None:
            self.name = ""
            self.icon = None

        def setApplicationName(self, name: str) -> None:
            self.name = name

        def setWindowIcon(self, icon) -> None:
            self.icon = icon

    monkeypatch.setattr("aica.main.icon_file", lambda: icon_path)
    monkeypatch.setattr("aica.main.QIcon", _Icon)

    app = _Application()
    result = _apply_application_icon(app, tmp_path / "startup.log")

    assert app.name == "Chattodo"
    assert app.icon is result
    assert created_icons == [str(icon_path)]


def test_show_startup_control_panel_opens_server_section(tmp_path: Path) -> None:
    calls: list[str] = []

    class _ControlPanel:
        @staticmethod
        def show_panel(section_id: str) -> None:
            calls.append(section_id)

    log_file = tmp_path / "startup.log"
    _show_startup_control_panel(_ControlPanel(), log_file)

    assert calls == ["server"]
    assert "control panel shown" in log_file.read_text(encoding="utf-8")


def test_show_startup_control_panel_relies_on_existing_state_without_forcing_reload(tmp_path: Path) -> None:
    calls: list[str] = []

    class _ControlPanel:
        @staticmethod
        def show_panel(section_id: str) -> None:
            calls.append(section_id)

    _show_startup_control_panel(_ControlPanel(), tmp_path / "startup.log")

    assert calls == ["server"]


def test_macos_dock_handlers_install_capture_and_exit_menu(monkeypatch, tmp_path: Path) -> None:
    class _Signal:
        def __init__(self) -> None:
            self._callbacks = []

        def connect(self, callback) -> None:
            self._callbacks.append(callback)

        def emit(self, *args) -> None:
            for callback in self._callbacks:
                callback(*args)

        @property
        def callbacks(self) -> list:
            return list(self._callbacks)

    class _Action:
        def __init__(self, text: str, _app) -> None:
            self.text = text
            self.triggered = _Signal()

    class _Menu:
        def __init__(self) -> None:
            self.items = []
            self.dock_menu_set = False

        def addAction(self, action) -> None:
            self.items.append(action)

        def addSeparator(self) -> None:
            self.items.append(None)

        def setAsDockMenu(self) -> None:
            self.dock_menu_set = True

    monkeypatch.setattr("aica.main.RUNTIME_CAPABILITIES", SimpleNamespace(is_macos=True))
    monkeypatch.setattr("aica.main.QAction", _Action)
    monkeypatch.setattr("aica.main.QMenu", _Menu)

    shown_sections: list[str] = []
    capture_sources: list[str] = []

    app = SimpleNamespace(applicationStateChanged=_Signal())
    handlers = _install_macos_dock_handlers(
        app,
        show_control_panel=lambda section: shown_sections.append(section),
        request_capture=lambda source: capture_sources.append(source),
        startup_log_file=tmp_path / "startup.log",
    )

    assert handlers.dock_menu.dock_menu_set is True
    assert [getattr(item, "text", None) for item in handlers.dock_menu.items] == ["开始截图", "打开控制面板"]

    handlers.dock_menu.items[0].triggered.emit()
    handlers.dock_menu.items[1].triggered.emit()

    assert capture_sources == ["dock"]
    assert shown_sections == ["server"]
    assert handlers.reopen_handler is not None
    assert len(app.applicationStateChanged.callbacks) == 1
    log_text = (tmp_path / "startup.log").read_text(encoding="utf-8")
    assert "macos dock menu installed" in log_text
    assert "macos dock reopen handler installed" in log_text


def test_has_visible_top_level_widget_ignores_hidden_and_minimized_windows() -> None:
    class _Widget:
        def __init__(self, visible: bool, minimized: bool = False) -> None:
            self._visible = visible
            self._minimized = minimized

        def isVisible(self) -> bool:  # noqa: N802
            return self._visible

        def isMinimized(self) -> bool:  # noqa: N802
            return self._minimized

    class _Window:
        def __init__(self, visible: bool, minimized: bool = False) -> None:
            self._visible = visible
            self._minimized = minimized

        def isVisible(self) -> bool:  # noqa: N802
            return self._visible

        def visibility(self):
            return "minimized" if self._minimized else "windowed"

        def windowState(self):  # noqa: N802
            return Qt.WindowState.WindowMinimized if self._minimized else Qt.WindowState.WindowNoState

    app = SimpleNamespace(
        topLevelWidgets=lambda: [
            _Widget(False),
            _Widget(True, minimized=True),
        ],
        topLevelWindows=lambda: [
            _Window(False),
            _Window(True, minimized=True),
            _Window(True),
        ],
    )

    assert _has_visible_top_level_widget(app) is True


def test_macos_dock_reopen_opens_control_panel_when_no_visible_window(monkeypatch, tmp_path: Path) -> None:
    shown_sections: list[str] = []
    queued_callbacks: list[object] = []
    app = SimpleNamespace(topLevelWidgets=lambda: [], topLevelWindows=lambda: [])
    monkeypatch.setattr("aica.main.QTimer.singleShot", lambda _msec, callback: queued_callbacks.append(callback))
    handler = _MacOSDockReopenHandler(
        app,
        show_control_panel=lambda section: shown_sections.append(section),
        startup_log_file=tmp_path / "startup.log",
    )

    handler.handle_application_state_changed("inactive")
    handler.handle_application_state_changed("active")
    handler.handle_application_state_changed(SimpleNamespace())
    handler.handle_application_state_changed(Qt.ApplicationState.ApplicationActive)

    assert shown_sections == []
    assert len(queued_callbacks) == 1
    queued_callbacks[0]()

    assert shown_sections == ["server"]
    assert "macos dock reopen opened control panel" in (tmp_path / "startup.log").read_text(encoding="utf-8")


def test_macos_dock_reopen_ignores_window_that_becomes_visible_after_activation(monkeypatch, tmp_path: Path) -> None:
    shown_sections: list[str] = []
    queued_callbacks: list[object] = []
    visible_windows: list[object] = []

    class _Window:
        @staticmethod
        def isVisible() -> bool:  # noqa: N802
            return True

        @staticmethod
        def visibility():
            return "windowed"

        @staticmethod
        def windowState():  # noqa: N802
            return Qt.WindowState.WindowNoState

    app = SimpleNamespace(topLevelWidgets=lambda: [], topLevelWindows=lambda: visible_windows)
    monkeypatch.setattr("aica.main.QTimer.singleShot", lambda _msec, callback: queued_callbacks.append(callback))
    handler = _MacOSDockReopenHandler(
        app,
        show_control_panel=lambda section: shown_sections.append(section),
        startup_log_file=tmp_path / "startup.log",
    )

    handler.handle_application_state_changed(Qt.ApplicationState.ApplicationActive)
    handler.handle_application_state_changed(Qt.ApplicationState.ApplicationActive)
    visible_windows.append(_Window())
    queued_callbacks[0]()

    assert shown_sections == []
    assert len(queued_callbacks) == 1
    log_file = tmp_path / "startup.log"
    assert not log_file.exists() or "macos dock reopen opened control panel" not in log_file.read_text(encoding="utf-8")


def test_macos_dock_reopen_is_suppressed_by_todo_panel_interaction(monkeypatch, tmp_path: Path) -> None:
    shown_sections: list[str] = []
    queued_callbacks: list[object] = []
    app = SimpleNamespace(topLevelWidgets=lambda: [], topLevelWindows=lambda: [])
    monkeypatch.setattr("aica.main.QTimer.singleShot", lambda _msec, callback: queued_callbacks.append(callback))
    handler = _MacOSDockReopenHandler(
        app,
        show_control_panel=lambda section: shown_sections.append(section),
        startup_log_file=tmp_path / "startup.log",
    )

    handler.handle_application_state_changed(Qt.ApplicationState.ApplicationActive)
    handler.suppress_reopen_for_todo_interaction()
    queued_callbacks[0]()

    assert shown_sections == []


def test_macos_dock_handlers_are_skipped_on_non_macos(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("aica.main.RUNTIME_CAPABILITIES", SimpleNamespace(is_macos=False))

    handlers = _install_macos_dock_handlers(
        object(),
        show_control_panel=lambda *_args: None,
        request_capture=lambda *_args: None,
        startup_log_file=tmp_path / "startup.log",
    )

    assert handlers is None

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

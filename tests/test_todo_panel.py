from __future__ import annotations

from pathlib import Path
import sys
import types


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _install_pyqt_fakes() -> None:
    if "PyQt6.QtCore" in sys.modules:
        return

    pyqt6 = types.ModuleType("PyQt6")
    qtcore = types.ModuleType("PyQt6.QtCore")
    qtgui = types.ModuleType("PyQt6.QtGui")
    qtquick = types.ModuleType("PyQt6.QtQuick")
    qtwidgets = types.ModuleType("PyQt6.QtWidgets")

    class QObject:
        def __init__(self, *_args, **_kwargs):
            pass

    class QRect:
        def __init__(self, *_args, **_kwargs):
            pass

    class QSize:
        def __init__(self, width=0, height=0):
            self._width = width
            self._height = height

        def width(self):
            return self._width

        def height(self):
            return self._height

    class Qt:
        class WindowType:
            pass

    class QTimer:
        @staticmethod
        def singleShot(_msec, callback):
            callback()

    class QUrl:
        @staticmethod
        def fromLocalFile(path):
            return path

    def pyqtProperty(*_args, **_kwargs):
        def _decorator(func):
            return property(func)

        return _decorator

    def pyqtSignal(*_args, **_kwargs):
        return object()

    def pyqtSlot(*_args, **_kwargs):
        def _decorator(func):
            return func

        return _decorator

    class QColor:
        def __init__(self, *_args, **_kwargs):
            pass

    class QCursor:
        @staticmethod
        def pos():
            return object()

    class QGuiApplication:
        @staticmethod
        def screenAt(_point):
            return None

    class QQuickView:
        class ResizeMode:
            SizeRootObjectToView = 0

    class QApplication:
        @staticmethod
        def primaryScreen():
            return None

        @staticmethod
        def screens():
            return []

    qtcore.QObject = QObject
    qtcore.QRect = QRect
    qtcore.QSize = QSize
    qtcore.Qt = Qt
    qtcore.QTimer = QTimer
    qtcore.QUrl = QUrl
    qtcore.pyqtProperty = pyqtProperty
    qtcore.pyqtSignal = pyqtSignal
    qtcore.pyqtSlot = pyqtSlot
    qtgui.QColor = QColor
    qtgui.QCursor = QCursor
    qtgui.QGuiApplication = QGuiApplication
    qtquick.QQuickView = QQuickView
    qtwidgets.QApplication = QApplication

    sys.modules["PyQt6"] = pyqt6
    sys.modules["PyQt6.QtCore"] = qtcore
    sys.modules["PyQt6.QtGui"] = qtgui
    sys.modules["PyQt6.QtQuick"] = qtquick
    sys.modules["PyQt6.QtWidgets"] = qtwidgets


def test_repair_size_on_screen_change_does_not_recalculate_panel_size(monkeypatch) -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    class FakeScreen:
        def name(self) -> str:
            return "DISPLAY2"

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._last_screen_name = "DISPLAY1"  # noqa: SLF001
    resize_calls: list[str] = []
    restore_calls: list[str] = []
    panel._update_panel_size = lambda: resize_calls.append("resize")  # noqa: SLF001
    panel._restore_fixed_panel_size = lambda: restore_calls.append("restore")  # noqa: SLF001

    monkeypatch.setattr(todo_panel._screen_for_point, "__call__", None, raising=False)
    monkeypatch.setattr(todo_panel, "_screen_for_point", lambda _point: FakeScreen())

    panel._repair_size_if_screen_changed()  # noqa: SLF001

    assert panel._last_screen_name == "DISPLAY2"  # noqa: SLF001
    assert restore_calls == ["restore"]
    assert resize_calls == []


def test_end_drag_keeps_snapped_position_after_restoring_size(monkeypatch) -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    class FakePoint:
        def __init__(self, x: int, y: int) -> None:
            self._x = x
            self._y = y

        def x(self) -> int:
            return self._x

        def y(self) -> int:
            return self._y

    class FakeGeometry:
        def left(self) -> int:
            return 0

        def right(self) -> int:
            return 999

        def top(self) -> int:
            return 0

        def bottom(self) -> int:
            return 799

    class FakeScreen:
        def availableGeometry(self) -> FakeGeometry:
            return FakeGeometry()

    class FakeSignal:
        def emit(self) -> None:
            return None

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._drag_offset = object()  # noqa: SLF001
    panel._custom_position = FakePoint(500, 120)  # noqa: SLF001
    panel._snap_margin = 18  # noqa: SLF001
    panel._snap_threshold = 28  # noqa: SLF001
    panel.geometry_changed = FakeSignal()
    panel.position = lambda: FakePoint(500, 120)
    panel.width = lambda: 286
    panel.height = lambda: 194
    positions: list[tuple[int, int]] = []
    panel.setPosition = lambda x, y: positions.append((int(x), int(y)))
    panel._restore_fixed_panel_size = lambda: None  # noqa: SLF001

    def _unexpected_size_recalculation() -> None:
        positions.append((500, 120))

    panel._update_panel_size = _unexpected_size_recalculation  # noqa: SLF001
    monkeypatch.setattr(todo_panel, "_screen_for_point", lambda _point: FakeScreen())

    panel._end_drag()  # noqa: SLF001

    assert positions[-1] == (695, 120)

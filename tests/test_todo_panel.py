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
        def __init__(self, *_args, **_kwargs):
            self.timeout = types.SimpleNamespace(connect=lambda _callback: None)

        def setSingleShot(self, _single_shot):
            return None

        def setInterval(self, _msec):
            return None

        def start(self, *_args):
            return None

        def stop(self):
            return None

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


def test_set_todos_reanchors_visible_panel_on_size_change(monkeypatch) -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    class FakeTodos(list):
        pass

    class FakeBridge:
        minimized = False
        expanded = False
        miniHovering = False
        pinned = True

        @property
        def visibleCount(self) -> int:
            return 1

        def set_state(self, todos, selected_id) -> None:
            self.todos = FakeTodos(todos)
            self.selected_id = selected_id

    class FakeSignal:
        def emit(self) -> None:
            return None

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._bridge = FakeBridge()  # noqa: SLF001
    panel._drag_offset = None  # noqa: SLF001
    panel._snap_margin = 18  # noqa: SLF001
    panel._mini_snap_margin = 0  # noqa: SLF001
    panel._dock_side = "right"  # noqa: SLF001
    panel.geometry_changed = FakeSignal()
    panel._update_panel_size = lambda: setattr(panel, "_target_panel_size", todo_panel.QSize(286, 158))  # noqa: SLF001
    panel._reposition_calls = []
    panel.isVisible = lambda: True
    panel.show = lambda: None
    panel.raise_ = lambda: None
    panel._schedule_auto_minimize = lambda: None  # noqa: SLF001
    panel._auto_minimize_timer = types.SimpleNamespace(stop=lambda: None)  # noqa: SLF001
    panel._custom_position = types.SimpleNamespace(x=lambda: 100, y=lambda: 200)  # noqa: SLF001
    panel.position = lambda: types.SimpleNamespace(x=lambda: 100, y=lambda: 200)
    panel.width = lambda: 286
    panel.height = lambda: 158
    panel._reposition = lambda: panel._reposition_calls.append("reposition")  # noqa: SLF001
    monkeypatch.setattr(todo_panel, "_screen_for_point", lambda _point: types.SimpleNamespace(availableGeometry=lambda: types.SimpleNamespace(left=lambda: 0, right=lambda: 999, top=lambda: 0, bottom=lambda: 799)))
    panel._target_panel_size = todo_panel.QSize(286, 194)  # noqa: SLF001

    panel.set_todos([object()], "todo-1")  # noqa: SLF001

    assert panel._reposition_calls == ["reposition"]  # noqa: SLF001


def test_set_todos_repairs_drift_when_selection_only_refreshes_content(monkeypatch) -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    class FakeTodos(list):
        pass

    class FakeBridge:
        minimized = False
        expanded = False
        miniHovering = False
        pinned = True

        def __init__(self) -> None:
            self._selected = None

        @property
        def visibleCount(self) -> int:
            return 2

        def set_state(self, todos, selected_id) -> None:
            self.todos = FakeTodos(todos)
            self.selected_id = selected_id

    class FakeSignal:
        def emit(self) -> None:
            return None

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._bridge = FakeBridge()  # noqa: SLF001
    panel._drag_offset = None  # noqa: SLF001
    panel._snap_margin = 18  # noqa: SLF001
    panel._mini_snap_margin = 0  # noqa: SLF001
    panel._dock_side = "right"  # noqa: SLF001
    panel.geometry_changed = FakeSignal()
    panel._update_panel_size = lambda: None  # noqa: SLF001
    panel._reposition_calls = []
    panel.isVisible = lambda: True
    panel.show = lambda: None
    panel.raise_ = lambda: None
    panel._schedule_auto_minimize = lambda: None  # noqa: SLF001
    panel._auto_minimize_timer = types.SimpleNamespace(stop=lambda: None)  # noqa: SLF001
    panel._custom_position = types.SimpleNamespace(x=lambda: 100, y=lambda: 200)  # noqa: SLF001
    panel.position = lambda: types.SimpleNamespace(x=lambda: 100, y=lambda: 200)
    panel.width = lambda: 286
    panel.height = lambda: 158
    panel._reposition = lambda: panel._reposition_calls.append("reposition")  # noqa: SLF001
    monkeypatch.setattr(todo_panel, "_screen_for_point", lambda _point: types.SimpleNamespace(availableGeometry=lambda: types.SimpleNamespace(left=lambda: 0, right=lambda: 999, top=lambda: 0, bottom=lambda: 799)))

    panel._target_panel_size = todo_panel.QSize(286, 158)  # noqa: SLF001
    panel.set_todos([object(), object()], "todo-1")  # noqa: SLF001

    assert panel._reposition_calls == ["reposition"]  # noqa: SLF001


def test_screen_change_restores_size_and_reanchors_visible_panel(monkeypatch) -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._drag_offset = None  # noqa: SLF001
    observed_screens: list[object] = []
    calls: list[str] = []
    screen = object()
    panel._observe_screen = lambda value: observed_screens.append(value)  # noqa: SLF001
    panel._restore_fixed_panel_size = lambda: calls.append("restore")  # noqa: SLF001
    panel._reposition = lambda: calls.append("reposition")  # noqa: SLF001
    panel.isVisible = lambda: True
    monkeypatch.setattr(todo_panel.QTimer, "singleShot", lambda _msec, callback: callback())

    panel._handle_screen_changed(screen)  # noqa: SLF001

    assert observed_screens == [screen]
    assert calls == ["restore", "reposition"]


def test_set_todos_does_not_re_show_visible_panel_on_refresh(monkeypatch) -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    class FakeBridge:
        minimized = False
        expanded = False
        miniHovering = False
        pinned = True

        @property
        def visibleCount(self) -> int:
            return 1

        def set_state(self, todos, selected_id) -> None:
            self.todos = list(todos)
            self.selected_id = selected_id

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._bridge = FakeBridge()  # noqa: SLF001
    panel._drag_offset = None  # noqa: SLF001
    panel._snap_margin = 18  # noqa: SLF001
    panel._mini_snap_margin = 0  # noqa: SLF001
    panel._dock_side = "right"  # noqa: SLF001
    panel._update_panel_size = lambda: None  # noqa: SLF001
    panel._reposition = lambda: None  # noqa: SLF001
    panel._schedule_auto_minimize = lambda: None  # noqa: SLF001
    show_calls: list[str] = []
    raise_calls: list[str] = []
    panel.show = lambda: show_calls.append("show")
    panel.raise_ = lambda: raise_calls.append("raise")
    panel.isVisible = lambda: True
    panel.width = lambda: 286
    panel.height = lambda: 194
    panel._target_panel_size = todo_panel.QSize(286, 194)  # noqa: SLF001
    panel.position = lambda: types.SimpleNamespace(x=lambda: 100, y=lambda: 200)
    panel._auto_minimize_timer = types.SimpleNamespace(stop=lambda: None)  # noqa: SLF001

    panel.set_todos([object()], "todo-1")  # noqa: SLF001

    assert show_calls == []
    assert raise_calls == []


def test_bridge_mini_status_text_prefers_selected_todo_title() -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    bridge = todo_panel._TodoPanelBridge()
    bridge._emit_all = lambda: None  # noqa: SLF001
    todos = [
        types.SimpleNamespace(id="todo-1", title="普通待办"),
        types.SimpleNamespace(id="todo-2", title="这是一个很长的已选中待办标题"),
    ]

    bridge.set_state(todos, "todo-2")

    assert bridge.miniStatusText == "这是一个很长的已选中待办标题"


def test_bridge_mini_status_text_falls_back_to_header_status_text_without_selection() -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    bridge = todo_panel._TodoPanelBridge()
    bridge._emit_all = lambda: None  # noqa: SLF001
    todos = [
        types.SimpleNamespace(id="todo-1", title="普通待办"),
    ]

    bridge.set_state(todos, None)

    assert bridge.miniStatusText == bridge.headerStatusText


def test_bridge_selection_change_does_not_rebuild_todo_model() -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    class CountingSignal:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    bridge = todo_panel._TodoPanelBridge()
    bridge.todosChanged = CountingSignal()  # type: ignore[assignment]  # noqa: SLF001
    bridge.selectedTodoIdChanged = CountingSignal()  # type: ignore[assignment]  # noqa: SLF001
    bridge.hasSelectedChanged = CountingSignal()  # type: ignore[assignment]  # noqa: SLF001
    bridge.miniStatusTextChanged = CountingSignal()  # type: ignore[assignment]  # noqa: SLF001
    bridge.todoCountChanged = CountingSignal()  # type: ignore[assignment]  # noqa: SLF001
    bridge.expandedChanged = CountingSignal()  # type: ignore[assignment]  # noqa: SLF001
    bridge.canExpandChanged = CountingSignal()  # type: ignore[assignment]  # noqa: SLF001
    bridge.headerStatusTextChanged = CountingSignal()  # type: ignore[assignment]  # noqa: SLF001
    todos = [
        types.SimpleNamespace(id="todo-1", title="普通待办"),
        types.SimpleNamespace(id="todo-2", title="第二个待办"),
    ]

    bridge.set_state(todos, None)
    assert bridge.todosChanged.count == 1  # type: ignore[attr-defined]

    bridge.set_state(todos, "todo-2")

    assert bridge.todosChanged.count == 1  # type: ignore[attr-defined]
    assert bridge.selectedTodoIdChanged.count == 1  # type: ignore[attr-defined]
    assert bridge.hasSelectedChanged.count == 1  # type: ignore[attr-defined]
    assert bridge.miniStatusTextChanged.count == 2  # type: ignore[attr-defined]


def test_hover_width_is_initialized_after_panel_width() -> None:
    source = (Path(__file__).resolve().parents[1] / "src" / "aica" / "todo" / "panel.py").read_text(encoding="utf-8")

    panel_width_index = source.index("self._panel_width = 286")
    hover_width_index = source.index("self._minimized_hover_width = self._panel_width")

    assert panel_width_index < hover_width_index


def test_start_drag_emits_interaction_started(monkeypatch) -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    class FakeSignal:
        def __init__(self) -> None:
            self.count = 0

        def emit(self) -> None:
            self.count += 1

    class FakePoint:
        def __sub__(self, _other):
            return "drag-offset"

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._bridge = types.SimpleNamespace(minimized=False)  # noqa: SLF001
    panel.interaction_started = FakeSignal()
    panel.position = lambda: FakePoint()
    monkeypatch.setattr(todo_panel.QCursor, "pos", lambda: FakePoint())

    panel._start_drag()  # noqa: SLF001

    assert panel.interaction_started.count == 1
    assert panel._drag_offset == "drag-offset"  # noqa: SLF001


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
    panel._dock_side = "right"  # noqa: SLF001
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


def test_minimized_panel_uses_compact_size_and_edge_position(monkeypatch) -> None:
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

        def center(self) -> FakePoint:
            return FakePoint(500, 399)

    class FakeScreen:
        def availableGeometry(self) -> FakeGeometry:
            return FakeGeometry()

    class FakeBridge:
        minimized = True
        expanded = False
        miniHovering = False

        @property
        def visibleCount(self) -> int:
            return 0

    class FakeSignal:
        def emit(self) -> None:
            return None

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._bridge = FakeBridge()  # noqa: SLF001
    panel._minimized_width = 100  # noqa: SLF001
    panel._minimized_hover_width = 286  # noqa: SLF001
    panel._minimized_height = 50  # noqa: SLF001
    panel._panel_width = 286  # noqa: SLF001
    panel._snap_margin = 18  # noqa: SLF001
    panel._mini_snap_margin = 0  # noqa: SLF001
    panel._dock_side = "right"  # noqa: SLF001
    panel._custom_position = FakePoint(695, 18)  # noqa: SLF001
    panel._drag_offset = None  # noqa: SLF001
    panel.geometry_changed = FakeSignal()
    panel.isVisible = lambda: True
    panel.position = lambda: FakePoint(695, 18)
    panel.width = lambda: 100
    panel.height = lambda: 50
    sizes: list[tuple[int, int]] = []
    positions: list[tuple[int, int]] = []
    panel._set_fixed_panel_size = lambda width, height, **_kwargs: sizes.append((width, height))  # noqa: SLF001
    panel.setPosition = lambda x, y: positions.append((int(x), int(y)))
    monkeypatch.setattr(todo_panel, "_screen_for_point", lambda _point: FakeScreen())

    panel._update_panel_size()  # noqa: SLF001

    assert sizes == [(100, 50)]
    assert positions[-1] == (899, 18)


def test_reposition_keeps_recorded_right_dock_side_after_window_drift(monkeypatch) -> None:
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

        def center(self) -> FakePoint:
            return FakePoint(500, 399)

    class FakeScreen:
        def availableGeometry(self) -> FakeGeometry:
            return FakeGeometry()

    class FakeBridge:
        minimized = True

        def set_dock_side(self, _side: str) -> None:
            raise AssertionError("window drift must not change the recorded dock side")

    class FakeSignal:
        def emit(self) -> None:
            return None

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._bridge = FakeBridge()  # noqa: SLF001
    panel._dock_side = "right"  # noqa: SLF001
    panel._snap_margin = 18  # noqa: SLF001
    panel._mini_snap_margin = 0  # noqa: SLF001
    panel._custom_position = FakePoint(340, 18)  # noqa: SLF001
    panel.geometry_changed = FakeSignal()
    current_position = FakePoint(340, 18)
    panel.position = lambda: current_position
    panel.width = lambda: 100
    panel.height = lambda: 50
    positions: list[tuple[int, int]] = []
    panel.setPosition = lambda x, y: positions.append((int(x), int(y)))
    monkeypatch.setattr(todo_panel, "_screen_for_point", lambda _point: FakeScreen())

    panel._reposition()  # noqa: SLF001

    assert panel._dock_side == "right"  # noqa: SLF001
    assert positions == [(899, 18)]


def test_minimized_panel_uses_hover_strip_width(monkeypatch) -> None:
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

        def center(self) -> FakePoint:
            return FakePoint(500, 399)

    class FakeScreen:
        def availableGeometry(self) -> FakeGeometry:
            return FakeGeometry()

    class FakeBridge:
        minimized = True
        expanded = False
        miniHovering = True

        @property
        def visibleCount(self) -> int:
            return 0

    class FakeSignal:
        def emit(self) -> None:
            return None

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._bridge = FakeBridge()  # noqa: SLF001
    panel._minimized_width = 100  # noqa: SLF001
    panel._minimized_hover_width = 286  # noqa: SLF001
    panel._minimized_height = 50  # noqa: SLF001
    panel._panel_width = 286  # noqa: SLF001
    panel._snap_margin = 18  # noqa: SLF001
    panel._mini_snap_margin = 0  # noqa: SLF001
    panel._dock_side = "right"  # noqa: SLF001
    panel._custom_position = FakePoint(899, 18)  # noqa: SLF001
    panel._drag_offset = None  # noqa: SLF001
    panel.geometry_changed = FakeSignal()
    panel.isVisible = lambda: True
    panel.position = lambda: FakePoint(899, 18)
    panel.width = lambda: 286
    panel.height = lambda: 50
    sizes: list[tuple[int, int]] = []
    positions: list[tuple[int, int]] = []
    panel._set_fixed_panel_size = lambda width, height, **_kwargs: sizes.append((width, height))  # noqa: SLF001
    panel.setPosition = lambda x, y: positions.append((int(x), int(y)))
    monkeypatch.setattr(todo_panel, "_screen_for_point", lambda _point: FakeScreen())

    panel._update_panel_size()  # noqa: SLF001

    assert sizes == [(286, 50)]
    assert positions[-1] == (713, 18)


def test_update_panel_size_skips_reapply_when_size_is_unchanged() -> None:
    _install_pyqt_fakes()
    from aica.todo import panel as todo_panel

    class FakeBridge:
        minimized = False
        expanded = False

        @property
        def visibleCount(self) -> int:
            return 3

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._bridge = FakeBridge()  # noqa: SLF001
    panel._panel_width = 286  # noqa: SLF001
    panel._panel_chrome_height = 58  # noqa: SLF001
    panel._row_height = 32  # noqa: SLF001
    panel._row_gap = 2  # noqa: SLF001
    panel._max_expanded_rows = 6  # noqa: SLF001
    panel._target_panel_size = todo_panel.QSize(286, 158)  # noqa: SLF001
    panel._drawer_animation = None  # noqa: SLF001
    panel.width = lambda: 286
    panel.height = lambda: 158
    panel.isVisible = lambda: True
    panel._drag_offset = None  # noqa: SLF001
    size_calls: list[tuple[int, int, bool]] = []
    reposition_calls: list[str] = []
    panel._set_fixed_panel_size = lambda width, height, *, animate=False: size_calls.append((width, height, animate)) or False  # noqa: SLF001
    panel._reposition = lambda: reposition_calls.append("reposition")  # noqa: SLF001

    panel._update_panel_size()  # noqa: SLF001

    assert size_calls == []
    assert reposition_calls == []


def test_drawer_animation_keeps_right_edge_fixed() -> None:
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

    class FakeSize:
        def width(self) -> int:
            return 286

        def height(self) -> int:
            return 50

    class FakeTimer:
        def __init__(self) -> None:
            self.started = False

        def start(self) -> None:
            self.started = True

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._dock_side = "right"  # noqa: SLF001
    panel._drawer_animation_timer = FakeTimer()  # noqa: SLF001
    panel.position = lambda: FakePoint(899, 18)
    panel.width = lambda: 100

    panel._start_drawer_animation(FakeSize())  # noqa: SLF001

    animation = panel._drawer_animation  # noqa: SLF001
    assert animation is not None
    assert animation["from_x"] == 899
    assert animation["to_x"] == 713
    assert animation["from_width"] == 100
    assert animation["to_width"] == 286
    assert panel._drawer_animation_timer.started is True  # noqa: SLF001


def test_drawer_animation_keeps_left_edge_fixed() -> None:
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

    class FakeSize:
        def width(self) -> int:
            return 286

        def height(self) -> int:
            return 50

    class FakeTimer:
        def __init__(self) -> None:
            self.started = False

        def start(self) -> None:
            self.started = True

    panel = todo_panel.TodoPanel.__new__(todo_panel.TodoPanel)
    panel._dock_side = "left"  # noqa: SLF001
    panel._drawer_animation_timer = FakeTimer()  # noqa: SLF001
    panel.position = lambda: FakePoint(0, 18)
    panel.width = lambda: 100

    panel._start_drawer_animation(FakeSize())  # noqa: SLF001

    animation = panel._drawer_animation  # noqa: SLF001
    assert animation is not None
    assert animation["from_x"] == 0
    assert animation["to_x"] == 0
    assert animation["from_width"] == 100
    assert animation["to_width"] == 286
    assert panel._drawer_animation_timer.started is True  # noqa: SLF001

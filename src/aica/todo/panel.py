"""QML-backed top-right floating panel for active todos."""
from __future__ import annotations

from time import monotonic

from PyQt6.QtCore import QObject, QRect, QSize, Qt, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QCursor, QGuiApplication
from PyQt6.QtQuick import QQuickView
from PyQt6.QtWidgets import QApplication

from ..paths import asset_file, qml_dir
from ..runtime import RUNTIME_CAPABILITIES
from ..theme_controller import ThemeController
from .store import TodoItem


def _screen_for_point(point):
    screen_at = getattr(QGuiApplication, "screenAt", None)
    if callable(screen_at):
        screen = screen_at(point)
        if screen is not None:
            return screen
    return QApplication.primaryScreen()


def _virtual_available_geometry() -> QRect | None:
    screens = QApplication.screens()
    if not screens:
        primary = QApplication.primaryScreen()
        return primary.availableGeometry() if primary is not None else None

    bounds = QRect(screens[0].availableGeometry())
    for screen in screens[1:]:
        bounds = bounds.united(screen.availableGeometry())
    return bounds


class _TodoPanelBridge(QObject):
    todosChanged = pyqtSignal()
    selectedTodoIdChanged = pyqtSignal()
    todoCountChanged = pyqtSignal()
    hasSelectedChanged = pyqtSignal()
    expandedChanged = pyqtSignal()
    canExpandChanged = pyqtSignal()
    minimizedChanged = pyqtSignal()
    pinnedChanged = pyqtSignal()
    analysisLoadingChanged = pyqtSignal()
    headerStatusTextChanged = pyqtSignal()
    dockSideChanged = pyqtSignal()
    miniHoveringChanged = pyqtSignal()
    miniStatusTextChanged = pyqtSignal()

    todoSelected = pyqtSignal(str)
    todoCompleted = pyqtSignal(str)
    detailRequested = pyqtSignal(str)
    selectionCleared = pyqtSignal()
    dragStarted = pyqtSignal()
    dragMoved = pyqtSignal()
    dragEnded = pyqtSignal()
    pointerEntered = pyqtSignal()
    pointerExited = pyqtSignal()

    def __init__(self, visible_limit: int = 3):
        super().__init__()
        self._todos: list[dict[str, str | bool]] = []
        self._selected_id: str | None = None
        self._selected_title: str = ""
        self._expanded = False
        self._visible_limit = visible_limit
        self._minimized = True
        self._pinned = True
        self._analysis_loading = False
        self._dock_side = "right"
        self._mini_hovering = False

    @staticmethod
    def _emit(signal: object) -> None:
        emit = getattr(signal, "emit", None)
        if callable(emit):
            emit()

    @pyqtProperty("QVariantList", notify=todosChanged)
    def todos(self):  # noqa: ANN201
        if self._minimized:
            return []
        return self._todos if self._expanded else self._todos[: self._visible_limit]

    @pyqtProperty(int, notify=todosChanged)
    def visibleCount(self) -> int:
        return len(self.todos)

    @pyqtProperty(str, notify=selectedTodoIdChanged)
    def selectedTodoId(self) -> str:
        return self._selected_id or ""

    @pyqtProperty(int, notify=todoCountChanged)
    def todoCount(self) -> int:
        return len(self._todos)

    @pyqtProperty(bool, notify=hasSelectedChanged)
    def hasSelected(self) -> bool:
        return bool(self._selected_id)

    @pyqtProperty(bool, notify=expandedChanged)
    def expanded(self) -> bool:
        return self._expanded

    @pyqtProperty(bool, notify=canExpandChanged)
    def canExpand(self) -> bool:
        return len(self._todos) > self._visible_limit

    @pyqtProperty(bool, notify=minimizedChanged)
    def minimized(self) -> bool:
        return self._minimized

    @pyqtProperty(bool, notify=pinnedChanged)
    def pinned(self) -> bool:
        return self._pinned

    @pyqtProperty(bool, notify=analysisLoadingChanged)
    def analysisLoading(self) -> bool:
        return self._analysis_loading

    @pyqtProperty(str, notify=expandedChanged)
    def expandLabel(self) -> str:
        if not self.canExpand:
            return ""
        return "收起" if self._expanded else "展开"

    @pyqtProperty(str, notify=headerStatusTextChanged)
    def headerStatusText(self) -> str:
        status_text = "截图分析中..." if self._analysis_loading else "进行中"
        return f"{len(self._todos)} {status_text}"

    @pyqtProperty(str, notify=miniStatusTextChanged)
    def miniStatusText(self) -> str:
        return self._selected_title or self.headerStatusText

    @pyqtProperty(str, notify=dockSideChanged)
    def dockSide(self) -> str:
        return self._dock_side

    @pyqtProperty(bool, notify=miniHoveringChanged)
    def miniHovering(self) -> bool:
        return self._mini_hovering

    @pyqtProperty(str, constant=True)
    def logoSource(self) -> str:
        return asset_file("aica_icon.png").as_uri()

    def set_state(self, todos: list[TodoItem], selected_id: str | None) -> None:
        next_todos = [
            {
                "id": todo.id,
                "title": todo.title,
            }
            for todo in todos
        ]
        todos_changed = next_todos != self._todos
        previous_selected_id = self._selected_id
        previous_selected_title = self._selected_title

        if todos_changed:
            self._todos = next_todos
            if len(self._todos) <= self._visible_limit:
                self._expanded = False

        self._selected_id = selected_id
        self._selected_title = next(
            (
                str(item["title"])
                for item in self._todos
                if str(item.get("id", "")) == str(selected_id or "") and str(item.get("title", "")).strip()
            ),
            "",
        )
        if todos_changed:
            self._emit(self.todosChanged)
            self._emit(self.todoCountChanged)
            self._emit(self.expandedChanged)
            self._emit(self.canExpandChanged)
            self._emit(self.headerStatusTextChanged)
        if previous_selected_id != self._selected_id:
            self._emit(self.selectedTodoIdChanged)
            self._emit(self.hasSelectedChanged)
        if previous_selected_title != self._selected_title or previous_selected_id != self._selected_id or todos_changed:
            self._emit(self.miniStatusTextChanged)

    @pyqtSlot()
    def toggleExpanded(self) -> None:
        if self._minimized or not self.canExpand:
            return
        self._expanded = not self._expanded
        self.todosChanged.emit()
        self.expandedChanged.emit()

    def set_minimized(self, minimized: bool) -> None:
        minimized = bool(minimized)
        if self._minimized == minimized:
            return
        self._minimized = minimized
        if minimized:
            self._expanded = False
        self.todosChanged.emit()
        self.minimizedChanged.emit()
        self.expandedChanged.emit()

    @pyqtSlot()
    def toggleMinimized(self) -> None:
        self.set_minimized(not self._minimized)

    @pyqtSlot()
    def restoreFromMini(self) -> None:
        self.set_minimized(False)

    @pyqtSlot()
    def togglePinned(self) -> None:
        self._pinned = not self._pinned
        self.pinnedChanged.emit()

    @pyqtSlot()
    def startDrag(self) -> None:
        self.dragStarted.emit()

    @pyqtSlot()
    def moveDrag(self) -> None:
        self.dragMoved.emit()

    @pyqtSlot()
    def endDrag(self) -> None:
        self.dragEnded.emit()

    @pyqtSlot()
    def enterPanel(self) -> None:
        self.pointerEntered.emit()

    @pyqtSlot()
    def leavePanel(self) -> None:
        self.pointerExited.emit()

    @pyqtSlot(str)
    def selectTodo(self, todo_id: str) -> None:
        self.todoSelected.emit(todo_id)

    @pyqtSlot(str)
    def completeTodo(self, todo_id: str) -> None:
        self.todoCompleted.emit(todo_id)

    @pyqtSlot(str)
    def requestDetail(self, todo_id: str) -> None:
        self.detailRequested.emit(todo_id)

    @pyqtSlot()
    def clearSelection(self) -> None:
        self.selectionCleared.emit()

    def set_analysis_loading(self, loading: bool) -> None:
        loading = bool(loading)
        if self._analysis_loading == loading:
            return
        self._analysis_loading = loading
        self.analysisLoadingChanged.emit()
        self.headerStatusTextChanged.emit()
        if not self._selected_title:
            self.miniStatusTextChanged.emit()

    def set_dock_side(self, side: str) -> None:
        normalized = "left" if str(side or "").strip() == "left" else "right"
        if self._dock_side == normalized:
            return
        self._dock_side = normalized
        self.dockSideChanged.emit()

    def set_mini_hovering(self, hovering: bool) -> None:
        hovering = bool(hovering)
        if self._mini_hovering == hovering:
            return
        self._mini_hovering = hovering
        self.miniHoveringChanged.emit()


class TodoPanel(QQuickView):
    todo_selected = pyqtSignal(str)
    todo_completed = pyqtSignal(str)
    selection_cleared = pyqtSignal()
    detail_requested = pyqtSignal(str)
    pinned_changed = pyqtSignal(bool)
    geometry_changed = pyqtSignal()
    interaction_started = pyqtSignal()

    def __init__(self, parent=None, *, theme_controller: ThemeController | None = None):
        super().__init__(parent)
        self._bridge = _TodoPanelBridge()
        self._theme_controller = theme_controller or ThemeController()
        self._panel_chrome_height = 58
        self._row_height = 32
        self._row_gap = 2
        self._max_expanded_rows = 6
        self._panel_width = 286
        self._minimized_width = 100
        self._minimized_hover_width = self._panel_width
        self._minimized_height = 50
        self._target_panel_size = QSize(self._panel_width, 194)
        self._last_screen_name = ""
        self._observed_screen = None
        self._drag_offset = None
        self._custom_position = None
        self._dock_side = "right"
        self._snap_margin = 18
        self._mini_snap_margin = 0
        self._snap_threshold = 28
        self._pointer_inside = False
        self._auto_minimize_delay_ms = 4000
        self._auto_minimize_timer = QTimer(self)
        self._auto_minimize_timer.setSingleShot(True)
        self._auto_minimize_timer.timeout.connect(self._auto_minimize)
        self._drawer_animation_duration_ms = 260
        self._drawer_animation_timer = QTimer(self)
        self._drawer_animation_timer.setInterval(16)
        self._drawer_animation_timer.timeout.connect(self._step_drawer_animation)
        self._drawer_animation: dict[str, float] | None = None

        self._apply_window_flags()
        self.setColor(QColor(0, 0, 0, 0))
        self.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self._theme_controller.apply_to_context(self.rootContext())
        self.rootContext().setContextProperty("todoPanelBridge", self._bridge)
        self.setSource(QUrl.fromLocalFile(str(qml_dir() / "TodoPanel.qml")))
        self.screenChanged.connect(self._handle_screen_changed)
        self._observe_screen(self.screen())

        self._bridge.todoSelected.connect(self.todo_selected)
        self._bridge.todoCompleted.connect(self.todo_completed)
        self._bridge.detailRequested.connect(self.detail_requested)
        self._bridge.selectionCleared.connect(self.selection_cleared)
        self._bridge.expandedChanged.connect(self._update_panel_size)
        self._bridge.minimizedChanged.connect(self._update_panel_size)
        self._bridge.miniHoveringChanged.connect(self._update_panel_size)
        self._bridge.dragStarted.connect(self._start_drag)
        self._bridge.dragMoved.connect(self._move_drag)
        self._bridge.dragEnded.connect(self._end_drag)
        self._bridge.pinnedChanged.connect(self._handle_pinned_changed)
        self._bridge.pointerEntered.connect(self._handle_pointer_entered)
        self._bridge.pointerExited.connect(self._handle_pointer_exited)

        self._set_fixed_panel_size(self._panel_width, 194)
        self.hide()

    def set_todos(self, todos: list[TodoItem], selected_id: str | None) -> None:
        was_visible = self.isVisible()
        self._bridge.set_state(todos, selected_id)
        self._update_panel_size()

        if todos:
            if self._drag_offset is None:
                self._reposition()
            if not was_visible:
                self.show()
                self._schedule_restore_and_reposition()
            if self._bridge.pinned and not was_visible:
                self.raise_()
            self._schedule_auto_minimize()
        else:
            self._auto_minimize_timer.stop()
            self.hide()

    def _update_panel_size(self) -> None:
        if self._bridge.minimized:
            width = self._minimized_hover_width if self._bridge.miniHovering else self._minimized_width
            height = self._minimized_height
        else:
            width = self._panel_width
            visible_count = max(1, self._bridge.visibleCount)
            if self._bridge.expanded:
                visible_count = min(visible_count, self._max_expanded_rows)
            height = (
                self._panel_chrome_height
                + visible_count * self._row_height
                + max(0, visible_count - 1) * self._row_gap
            )
        target_size = QSize(max(1, int(width)), max(1, int(height)))
        current_target = self.__dict__.get("_target_panel_size")
        if (
            current_target is not None
            and current_target.width() == target_size.width()
            and current_target.height() == target_size.height()
            and self.width() == target_size.width()
            and self.height() == target_size.height()
            and self.__dict__.get("_drawer_animation") is None
        ):
            return
        animated = self._set_fixed_panel_size(
            target_size.width(),
            target_size.height(),
            animate=self._should_animate_drawer_size(width, height),
        )
        if self.isVisible() and self._drag_offset is None and not animated:
            self._reposition()

    def _should_animate_drawer_size(self, width: int, height: int) -> bool:
        bridge = self.__dict__.get("_bridge")
        if not self.isVisible() or self._drag_offset is not None or not bool(getattr(bridge, "minimized", False)):
            return False
        target_panel_size = self.__dict__.get("_target_panel_size")
        if target_panel_size is None:
            return False
        return target_panel_size.height() == height and target_panel_size.width() != width

    def _set_fixed_panel_size(self, width: int, height: int, *, animate: bool = False) -> bool:
        size = QSize(max(1, int(width)), max(1, int(height)))
        self._target_panel_size = size
        if animate:
            self._start_drawer_animation(size)
            return True
        self._drawer_animation_timer.stop()
        self._drawer_animation = None
        self._apply_fixed_panel_size(size)
        return False

    def _apply_fixed_panel_size(self, size: QSize) -> None:
        self.setMinimumSize(size)
        self.setMaximumSize(size)
        self.resize(size)
        root_object = self.rootObject()
        if root_object is not None:
            root_object.setProperty("width", size.width())
            root_object.setProperty("height", size.height())

    def _restore_fixed_panel_size(self) -> None:
        self._apply_fixed_panel_size(self._target_panel_size)

    def _start_drawer_animation(self, target_size: QSize) -> None:
        current_x = self.position().x()
        current_y = self.position().y()
        current_width = max(1, int(self.width()))
        target_width = target_size.width()
        if self._dock_side == "left":
            target_x = current_x
        else:
            target_x = current_x + current_width - target_width
        self._drawer_animation = {
            "started_at": monotonic(),
            "from_x": float(current_x),
            "to_x": float(target_x),
            "y": float(current_y),
            "from_width": float(current_width),
            "to_width": float(target_width),
            "height": float(target_size.height()),
        }
        self._drawer_animation_timer.start()

    @staticmethod
    def _drawer_ease_out_cubic(progress: float) -> float:
        progress = max(0.0, min(1.0, progress))
        return 1.0 - pow(1.0 - progress, 3)

    def _step_drawer_animation(self) -> None:
        animation = self._drawer_animation
        if animation is None:
            self._drawer_animation_timer.stop()
            return
        elapsed_ms = (monotonic() - animation["started_at"]) * 1000.0
        progress = elapsed_ms / max(1, self._drawer_animation_duration_ms)
        eased = self._drawer_ease_out_cubic(progress)
        width = int(round(animation["from_width"] + (animation["to_width"] - animation["from_width"]) * eased))
        x = int(round(animation["from_x"] + (animation["to_x"] - animation["from_x"]) * eased))
        height = int(round(animation["height"]))
        current_size = QSize(max(1, width), max(1, height))
        self._apply_fixed_panel_size(current_size)
        self.setPosition(x, int(round(animation["y"])))

        if progress >= 1.0:
            self._drawer_animation_timer.stop()
            self._drawer_animation = None
            self._apply_fixed_panel_size(self._target_panel_size)
            if self._drag_offset is None:
                self._reposition()
            return
        self.geometry_changed.emit()

    @property
    def pinned(self) -> bool:
        return self._bridge.pinned

    def set_analysis_loading(self, loading: bool) -> None:
        self._bridge.set_analysis_loading(loading)

    def _apply_window_flags(self) -> None:
        was_visible = self.isVisible()
        self.setFlags(
            RUNTIME_CAPABILITIES.floating_tool_window_flags(
                Qt.WindowType,
                stays_on_top=self._bridge.pinned,
            )
        )
        if was_visible:
            self.show()
            self._schedule_restore_and_reposition()
            self.geometry_changed.emit()

    def _handle_pinned_changed(self) -> None:
        self._apply_window_flags()
        if self.isVisible() and self._bridge.pinned:
            self.raise_()
        self.pinned_changed.emit(self._bridge.pinned)

    def _current_snap_margin(self) -> int:
        bridge = self.__dict__.get("_bridge")
        minimized = bool(getattr(bridge, "minimized", False))
        if minimized:
            return getattr(self, "_mini_snap_margin", self._snap_margin)
        return self._snap_margin

    def _sync_bridge_dock_side(self) -> None:
        bridge = self.__dict__.get("_bridge")
        if bridge is not None and hasattr(bridge, "set_dock_side"):
            bridge.set_dock_side(self._dock_side)

    def _set_bridge_mini_hovering(self, hovering: bool) -> None:
        bridge = self.__dict__.get("_bridge")
        if bridge is not None and hasattr(bridge, "set_mini_hovering"):
            bridge.set_mini_hovering(hovering)

    def _schedule_auto_minimize(self) -> None:
        if not self.isVisible() or self._pointer_inside or self._bridge.minimized or self._bridge.todoCount <= 0:
            self._auto_minimize_timer.stop()
            return
        self._auto_minimize_timer.start(self._auto_minimize_delay_ms)

    def _auto_minimize(self) -> None:
        if self._pointer_inside or not self.isVisible() or self._bridge.todoCount <= 0:
            return
        self._bridge.set_minimized(True)

    def _handle_pointer_entered(self) -> None:
        self._pointer_inside = True
        self._auto_minimize_timer.stop()
        if self._bridge.minimized:
            self._set_bridge_mini_hovering(True)

    def _handle_pointer_exited(self) -> None:
        self._pointer_inside = False
        self._set_bridge_mini_hovering(False)
        self._schedule_auto_minimize()

    def _reposition(self) -> None:
        current = self.position()
        screen = _screen_for_point(current)
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = self._current_snap_margin()
        min_y = available.top() + margin
        max_y = available.bottom() - self.height() - margin
        y_source = self._custom_position.y() if self._custom_position is not None else min_y
        y = min(max(y_source, min_y), max_y)
        if self._dock_side == "left":
            x = available.left() + margin
        else:
            x = available.right() - self.width() - margin
        if current.x() == x and current.y() == y:
            return
        self.setPosition(x, y)
        self._custom_position = self.position()
        self.geometry_changed.emit()

    def frameGeometry(self):  # noqa: N802, ANN201
        return self.geometry()

    def _start_drag(self) -> None:
        self.interaction_started.emit()
        if self._bridge.minimized:
            self._set_bridge_mini_hovering(True)
        cursor_pos = QCursor.pos()
        self._drag_offset = cursor_pos - self.position()

    def _move_drag(self) -> None:
        if self._drag_offset is None:
            return
        cursor_pos = QCursor.pos()
        available = _virtual_available_geometry()
        if available is None:
            return
        candidate = cursor_pos - self._drag_offset
        margin = self._current_snap_margin()
        x = min(max(candidate.x(), available.left() + margin), available.right() - self.width() - margin)
        y = min(
            max(candidate.y(), available.top() + margin),
            available.bottom() - self.height() - margin,
        )
        self.setPosition(x, y)
        self._repair_size_if_screen_changed()
        self._custom_position = self.position()
        self.geometry_changed.emit()

    def _end_drag(self) -> None:
        if self._drag_offset is None:
            return
        self._drag_offset = None
        self._restore_fixed_panel_size()
        screen = _screen_for_point(QCursor.pos())
        if screen is None:
            return
        available = screen.availableGeometry()
        pos = self.position()
        x = pos.x()
        y = pos.y()

        margin = self._current_snap_margin()
        left_snap = available.left() + margin
        right_snap = available.right() - self.width() - margin
        if abs(x - left_snap) <= abs(x - right_snap):
            x = left_snap
            self._dock_side = "left"
        else:
            x = right_snap
            self._dock_side = "right"
        self._sync_bridge_dock_side()

        top_snap = available.top() + margin
        if abs(y - top_snap) <= self._snap_threshold:
            y = top_snap
        if abs((available.bottom() - self.height() - margin) - y) <= self._snap_threshold:
            y = available.bottom() - self.height() - margin

        self.setPosition(x, y)
        self._custom_position = self.position()
        self._set_bridge_mini_hovering(False)
        self.geometry_changed.emit()

    def _observe_screen(self, screen) -> None:  # noqa: ANN001
        previous = self._observed_screen
        if previous is screen:
            return
        if previous is not None:
            try:
                previous.availableGeometryChanged.disconnect(self._handle_available_geometry_changed)
            except (RuntimeError, TypeError):
                pass
        self._observed_screen = screen
        if screen is not None:
            screen.availableGeometryChanged.connect(self._handle_available_geometry_changed)

    def _handle_screen_changed(self, screen) -> None:  # noqa: ANN001
        self._observe_screen(screen)
        self._schedule_restore_and_reposition()

    def _handle_available_geometry_changed(self, _geometry=None) -> None:  # noqa: ANN001
        self._schedule_restore_and_reposition()

    def _schedule_restore_and_reposition(self) -> None:
        QTimer.singleShot(0, self._restore_and_reposition)

    def _restore_and_reposition(self) -> None:
        self._restore_fixed_panel_size()
        if self.isVisible() and self._drag_offset is None:
            self._reposition()

    def _repair_size_if_screen_changed(self) -> None:
        screen = _screen_for_point(QCursor.pos())
        screen_name = screen.name() if screen is not None else ""
        if screen_name == self._last_screen_name:
            return
        self._last_screen_name = screen_name
        self._restore_fixed_panel_size()

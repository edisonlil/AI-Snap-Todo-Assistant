"""QML-backed top-right floating panel for active todos."""
from __future__ import annotations

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

    todoSelected = pyqtSignal(str)
    todoCompleted = pyqtSignal(str)
    detailRequested = pyqtSignal(str)
    selectionCleared = pyqtSignal()
    dragStarted = pyqtSignal()
    dragMoved = pyqtSignal()
    dragEnded = pyqtSignal()

    def __init__(self, visible_limit: int = 3):
        super().__init__()
        self._todos: list[dict[str, str | bool]] = []
        self._selected_id: str | None = None
        self._expanded = False
        self._visible_limit = visible_limit
        self._minimized = False
        self._pinned = True
        self._analysis_loading = False

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

    @pyqtProperty(str, constant=True)
    def logoSource(self) -> str:
        return asset_file("aica_icon.png").as_uri()

    def set_state(self, todos: list[TodoItem], selected_id: str | None) -> None:
        self._todos = [
            {
                "id": todo.id,
                "title": todo.title,
                "selected": todo.id == selected_id,
            }
            for todo in todos
        ]
        self._selected_id = selected_id
        if len(self._todos) <= self._visible_limit:
            self._expanded = False
        self._emit_all()

    def _emit_all(self) -> None:
        self.todosChanged.emit()
        self.selectedTodoIdChanged.emit()
        self.todoCountChanged.emit()
        self.hasSelectedChanged.emit()
        self.expandedChanged.emit()
        self.canExpandChanged.emit()
        self.minimizedChanged.emit()
        self.analysisLoadingChanged.emit()
        self.headerStatusTextChanged.emit()

    @pyqtSlot()
    def toggleExpanded(self) -> None:
        if self._minimized or not self.canExpand:
            return
        self._expanded = not self._expanded
        self.todosChanged.emit()
        self.expandedChanged.emit()

    @pyqtSlot()
    def toggleMinimized(self) -> None:
        self._minimized = not self._minimized
        self.todosChanged.emit()
        self.minimizedChanged.emit()

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


class TodoPanel(QQuickView):
    todo_selected = pyqtSignal(str)
    todo_completed = pyqtSignal(str)
    selection_cleared = pyqtSignal()
    detail_requested = pyqtSignal(str)
    pinned_changed = pyqtSignal(bool)
    geometry_changed = pyqtSignal()

    def __init__(self, parent=None, *, theme_controller: ThemeController | None = None):
        super().__init__(parent)
        self._bridge = _TodoPanelBridge()
        self._theme_controller = theme_controller or ThemeController()
        self._panel_chrome_height = 58
        self._row_height = 32
        self._row_gap = 2
        self._max_expanded_rows = 6
        self._minimized_height = 50
        self._panel_width = 286
        self._target_panel_size = QSize(self._panel_width, 194)
        self._last_screen_name = ""
        self._drag_offset = None
        self._custom_position = None
        self._snap_margin = 18
        self._snap_threshold = 28

        self._apply_window_flags()
        self.setColor(QColor(0, 0, 0, 0))
        self.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self._theme_controller.apply_to_context(self.rootContext())
        self.rootContext().setContextProperty("todoPanelBridge", self._bridge)
        self.setSource(QUrl.fromLocalFile(str(qml_dir() / "TodoPanel.qml")))
        self.screenChanged.connect(self._handle_screen_changed)

        self._bridge.todoSelected.connect(self.todo_selected)
        self._bridge.todoCompleted.connect(self.todo_completed)
        self._bridge.detailRequested.connect(self.detail_requested)
        self._bridge.selectionCleared.connect(self.selection_cleared)
        self._bridge.expandedChanged.connect(self._update_panel_size)
        self._bridge.minimizedChanged.connect(self._update_panel_size)
        self._bridge.dragStarted.connect(self._start_drag)
        self._bridge.dragMoved.connect(self._move_drag)
        self._bridge.dragEnded.connect(self._end_drag)
        self._bridge.pinnedChanged.connect(self._handle_pinned_changed)

        self._set_fixed_panel_size(self._panel_width, 194)
        self.hide()

    def set_todos(self, todos: list[TodoItem], selected_id: str | None) -> None:
        self._bridge.set_state(todos, selected_id)
        self._update_panel_size()

        if todos:
            self._reposition()
            self.show()
            if self._bridge.pinned:
                self.raise_()
        else:
            self.hide()

    def _update_panel_size(self) -> None:
        if self._bridge.minimized:
            height = self._minimized_height
        else:
            visible_count = max(1, self._bridge.visibleCount)
            if self._bridge.expanded:
                visible_count = min(visible_count, self._max_expanded_rows)
            height = (
                self._panel_chrome_height
                + visible_count * self._row_height
                + max(0, visible_count - 1) * self._row_gap
            )
        self._set_fixed_panel_size(self._panel_width, height)
        if self.isVisible() and self._drag_offset is None:
            self._reposition()

    def _set_fixed_panel_size(self, width: int, height: int) -> None:
        size = QSize(max(1, int(width)), max(1, int(height)))
        self._target_panel_size = size
        self._apply_fixed_panel_size(size)

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
            self.geometry_changed.emit()

    def _handle_pinned_changed(self) -> None:
        self._apply_window_flags()
        if self.isVisible() and self._bridge.pinned:
            self.raise_()
        self.pinned_changed.emit(self._bridge.pinned)

    def _reposition(self) -> None:
        screen = _screen_for_point(self.position())
        if screen is None:
            return
        available = screen.availableGeometry()
        min_y = available.top() + self._snap_margin
        max_y = available.bottom() - self.height() - self._snap_margin
        if self._custom_position is not None:
            x = min(max(self._custom_position.x(), available.left() + self._snap_margin), available.right() - self.width() - self._snap_margin)
            y = min(max(self._custom_position.y(), min_y), max_y)
        else:
            x = available.right() - self.width() - self._snap_margin
            y = min_y
        self.setPosition(x, y)
        self._custom_position = self.position()
        self.geometry_changed.emit()

    def frameGeometry(self):  # noqa: N802, ANN201
        return self.geometry()

    def _start_drag(self) -> None:
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
        x = min(max(candidate.x(), available.left() + self._snap_margin), available.right() - self.width() - self._snap_margin)
        y = min(
            max(candidate.y(), available.top() + self._snap_margin),
            available.bottom() - self.height() - self._snap_margin,
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

        left_snap = available.left() + self._snap_margin
        right_snap = available.right() - self.width() - self._snap_margin
        x = left_snap if abs(x - left_snap) <= abs(x - right_snap) else right_snap

        top_snap = available.top() + self._snap_margin
        if abs(y - top_snap) <= self._snap_threshold:
            y = top_snap
        if abs((available.bottom() - self.height() - self._snap_margin) - y) <= self._snap_threshold:
            y = available.bottom() - self.height() - self._snap_margin

        self.setPosition(x, y)
        self._custom_position = self.position()
        self.geometry_changed.emit()

    def _handle_screen_changed(self, _screen) -> None:  # noqa: ANN001
        QTimer.singleShot(0, self._restore_fixed_panel_size)

    def _repair_size_if_screen_changed(self) -> None:
        screen = _screen_for_point(QCursor.pos())
        screen_name = screen.name() if screen is not None else ""
        if screen_name == self._last_screen_name:
            return
        self._last_screen_name = screen_name
        self._restore_fixed_panel_size()

"""QML-backed top-right floating panel for active todos."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QCursor
from PyQt6.QtQuick import QQuickView
from PyQt6.QtWidgets import QApplication

from .todo_store import TodoItem


class _TodoPanelBridge(QObject):
    todosChanged = pyqtSignal()
    selectedTodoIdChanged = pyqtSignal()
    todoCountChanged = pyqtSignal()
    hasSelectedChanged = pyqtSignal()
    expandedChanged = pyqtSignal()
    canExpandChanged = pyqtSignal()
    minimizedChanged = pyqtSignal()

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

    @pyqtProperty(str, notify=expandedChanged)
    def expandLabel(self) -> str:
        if not self.canExpand:
            return ""
        return "收起" if self._expanded else "展开"

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


class TodoPanel(QQuickView):
    todo_selected = pyqtSignal(str)
    todo_completed = pyqtSignal(str)
    selection_cleared = pyqtSignal()
    detail_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bridge = _TodoPanelBridge()
        self._panel_chrome_height = 58
        self._row_height = 32
        self._row_gap = 2
        self._max_expanded_rows = 6
        self._minimized_height = 50
        self._panel_width = 286
        self._drag_offset = None
        self._custom_position = None
        self._snap_margin = 18
        self._snap_threshold = 28

        self.setFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setColor(QColor(0, 0, 0, 0))
        self.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.rootContext().setContextProperty("todoPanelBridge", self._bridge)
        self.setSource(QUrl.fromLocalFile(str(Path(__file__).with_name("qml").joinpath("TodoPanel.qml"))))

        self._bridge.todoSelected.connect(self.todo_selected)
        self._bridge.todoCompleted.connect(self.todo_completed)
        self._bridge.detailRequested.connect(self.detail_requested)
        self._bridge.selectionCleared.connect(self.selection_cleared)
        self._bridge.expandedChanged.connect(self._update_panel_size)
        self._bridge.minimizedChanged.connect(self._update_panel_size)
        self._bridge.dragStarted.connect(self._start_drag)
        self._bridge.dragMoved.connect(self._move_drag)
        self._bridge.dragEnded.connect(self._end_drag)

        self.resize(self._panel_width, 194)
        self.hide()

    def set_todos(self, todos: list[TodoItem], selected_id: str | None) -> None:
        self._bridge.set_state(todos, selected_id)
        self._update_panel_size()

        if todos:
            self._reposition()
            self.show()
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
        self.resize(self._panel_width, height)
        if self.isVisible():
            self._reposition()

    def _reposition(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        if self._custom_position is not None:
            x = min(max(self._custom_position.x(), available.left() + self._snap_margin), available.right() - self.width() - self._snap_margin)
            y = min(max(self._custom_position.y(), available.top() + self._snap_margin), available.bottom() - self.height() - self._snap_margin)
        else:
            x = available.right() - self.width() - self._snap_margin
            y = available.top() + self._snap_margin
        self.setPosition(x, y)
        self._custom_position = self.position()

    def frameGeometry(self):  # noqa: N802, ANN201
        return self.geometry()

    def _start_drag(self) -> None:
        cursor_pos = QCursor.pos()
        self._drag_offset = cursor_pos - self.position()

    def _move_drag(self) -> None:
        if self._drag_offset is None:
            return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        cursor_pos = QCursor.pos()
        candidate = cursor_pos - self._drag_offset
        x = min(max(candidate.x(), available.left() + self._snap_margin), available.right() - self.width() - self._snap_margin)
        y = min(max(candidate.y(), available.top() + self._snap_margin), available.bottom() - self.height() - self._snap_margin)
        self.setPosition(x, y)
        self._custom_position = self.position()

    def _end_drag(self) -> None:
        if self._drag_offset is None:
            return
        self._drag_offset = None
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        pos = self.position()
        x = pos.x()
        y = pos.y()

        left_snap = available.left() + self._snap_margin
        right_snap = available.right() - self.width() - self._snap_margin
        x = left_snap if abs(x - left_snap) <= abs(x - right_snap) else right_snap

        if abs(y - (available.top() + self._snap_margin)) <= self._snap_threshold:
            y = available.top() + self._snap_margin
        if abs((available.bottom() - self.height() - self._snap_margin) - y) <= self._snap_threshold:
            y = available.bottom() - self.height() - self._snap_margin

        self.setPosition(x, y)
        self._custom_position = self.position()

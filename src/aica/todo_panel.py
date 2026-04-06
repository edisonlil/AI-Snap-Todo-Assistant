"""QML-backed top-right floating panel for active todos."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
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

    todoSelected = pyqtSignal(str)
    todoCompleted = pyqtSignal(str)
    detailRequested = pyqtSignal(str)
    selectionCleared = pyqtSignal()

    def __init__(self, visible_limit: int = 3):
        super().__init__()
        self._todos: list[dict[str, str | bool]] = []
        self._selected_id: str | None = None
        self._expanded = False
        self._visible_limit = visible_limit

    @pyqtProperty("QVariantList", notify=todosChanged)
    def todos(self):  # noqa: ANN201
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

    @pyqtSlot()
    def toggleExpanded(self) -> None:
        if not self.canExpand:
            return
        self._expanded = not self._expanded
        self.todosChanged.emit()
        self.expandedChanged.emit()

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
        self._base_height = 62
        self._row_height = 40
        self._bottom_padding = 12
        self._panel_width = 286

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
        visible_count = max(1, self._bridge.visibleCount)
        height = self._base_height + visible_count * self._row_height + self._bottom_padding
        self.resize(self._panel_width, height)

    def _reposition(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = 18
        x = available.right() - self.width() - margin
        y = available.top() + margin
        self.setPosition(x, y)

    def frameGeometry(self):  # noqa: N802, ANN201
        return self.geometry()

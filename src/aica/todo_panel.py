"""Top-right floating panel for active todos."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .todo_store import TodoItem


class _TodoCard(QFrame):
    clicked = pyqtSignal(str)
    completed = pyqtSignal(str)
    detail_requested = pyqtSignal(str)

    def __init__(self, todo: TodoItem, selected: bool, parent=None):
        super().__init__(parent)
        self._todo_id = todo.id
        self.setObjectName("todoCardSelected" if selected else "todoCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel(todo.title)
        title.setObjectName("todoTitle")
        title.setWordWrap(True)
        header.addWidget(title, 1)

        complete_button = QPushButton("完成")
        complete_button.setObjectName("completeButton")
        complete_button.clicked.connect(lambda: self.completed.emit(self._todo_id))
        header.addWidget(complete_button)

        detail_button = QPushButton("详情")
        detail_button.setObjectName("clearButton")
        detail_button.clicked.connect(lambda: self.detail_requested.emit(self._todo_id))
        header.addWidget(detail_button)

        layout.addLayout(header)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._todo_id)
        super().mousePressEvent(event)


class TodoPanel(QWidget):
    todo_selected = pyqtSignal(str)
    todo_completed = pyqtSignal(str)
    selection_cleared = pyqtSignal()
    detail_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_id: str | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        surface = QFrame()
        surface.setObjectName("panelSurface")
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(14, 12, 14, 12)
        surface_layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel("待办")
        title.setObjectName("panelTitle")
        header.addWidget(title)

        header.addStretch()

        self._hint = QLabel("选中后下一次截图会追加到该任务")
        self._hint.setObjectName("panelHint")
        header.addWidget(self._hint)

        self._clear_button = QPushButton("清除选中")
        self._clear_button.setObjectName("clearButton")
        self._clear_button.clicked.connect(self._on_clear_selection)
        header.addWidget(self._clear_button)

        surface_layout.addLayout(header)

        self._count_label = QLabel("")
        self._count_label.setObjectName("countLabel")
        surface_layout.addWidget(self._count_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("todoScroll")

        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        scroll.setWidget(self._container)
        surface_layout.addWidget(scroll, 1)

        root_layout.addWidget(surface)
        self.setMinimumWidth(320)
        self.setMaximumWidth(360)
        self.resize(340, 420)
        self._apply_style()
        self.hide()

    def set_todos(self, todos: list[TodoItem], selected_id: str | None) -> None:
        self._selected_id = selected_id
        self._count_label.setText(f"{len(todos)} 个进行中")
        self._clear_button.setVisible(bool(selected_id))

        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for todo in todos:
            card = _TodoCard(todo, todo.id == selected_id, self._container)
            card.clicked.connect(self.todo_selected.emit)
            card.completed.connect(self.todo_completed.emit)
            card.detail_requested.connect(self.detail_requested.emit)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

        if todos:
            self._reposition()
            self.show()
            self.raise_()
        else:
            self.hide()

    def _reposition(self) -> None:
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = 18
        x = available.right() - self.width() - margin
        y = available.top() + margin
        self.move(x, y)

    def _on_clear_selection(self) -> None:
        self.selection_cleared.emit()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: transparent;
                color: #e5eefb;
                font-family: 'Segoe UI Variable Text', 'Microsoft YaHei UI', sans-serif;
            }
            QFrame#panelSurface {
                background-color: rgba(9, 14, 24, 148);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 18px;
            }
            QLabel#panelTitle {
                font-size: 16px;
                font-weight: 700;
                color: #f8fbff;
            }
            QLabel#panelHint, QLabel#countLabel {
                font-size: 11px;
                color: rgba(229, 238, 251, 0.72);
            }
            QScrollArea#todoScroll {
                background: transparent;
            }
            QFrame#todoCard, QFrame#todoCardSelected {
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QFrame#todoCard {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QFrame#todoCardSelected {
                background-color: rgba(78, 168, 255, 0.18);
                border: 1px solid rgba(120, 192, 255, 0.48);
            }
            QLabel#todoTitle {
                font-size: 13px;
                font-weight: 700;
                color: #ffffff;
            }
            QPushButton#completeButton, QPushButton#clearButton {
                border-radius: 9px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#completeButton {
                color: #0f172a;
                background-color: rgba(230, 244, 255, 0.92);
                border: 1px solid rgba(255, 255, 255, 0.14);
            }
            QPushButton#completeButton:hover, QPushButton#clearButton:hover {
                background-color: rgba(255, 255, 255, 0.96);
            }
            QPushButton#clearButton {
                color: #f8fbff;
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            """
        )

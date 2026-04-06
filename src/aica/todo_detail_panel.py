"""Detail side panel for a todo item and its timeline."""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .todo_store import TodoItem


def _format_ts(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%m-%d %H:%M")
    except ValueError:
        return value


def _build_detail_excerpt(detail: str, summary: str, limit: int = 220) -> str:
    normalized_detail = detail.strip()
    normalized_summary = summary.strip()
    if not normalized_detail or normalized_detail == normalized_summary:
        return ""
    if len(normalized_detail) <= limit:
        return normalized_detail
    return normalized_detail[:limit].rstrip() + "..."


class _TimelineCard(QFrame):
    def __init__(self, label: str, summary: str, detail: str, parent=None):
        super().__init__(parent)
        self.setObjectName("timelineCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        time_label = QLabel(label)
        time_label.setObjectName("timeLabel")
        layout.addWidget(time_label)

        summary_label = QLabel(summary or "无摘要")
        summary_label.setObjectName("summaryLabel")
        summary_label.setWordWrap(True)
        summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(summary_label)

        detail_excerpt = _build_detail_excerpt(detail, summary)
        if detail_excerpt:
            detail_label = QLabel(detail_excerpt)
            detail_label.setObjectName("detailLabel")
            detail_label.setWordWrap(True)
            detail_label.setToolTip(detail)
            detail_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(detail_label)


class TodoDetailPanel(QWidget):
    save_requested = pyqtSignal(str, str, str)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._todo_id: str | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        surface = QFrame()
        surface.setObjectName("detailSurface")
        layout = QVBoxLayout(surface)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        title = QLabel("任务详情")
        title.setObjectName("headerTitle")
        header.addWidget(title)

        header.addStretch()

        close_button = QPushButton("关闭")
        close_button.setObjectName("ghostButton")
        close_button.clicked.connect(self._close_panel)
        header.addWidget(close_button)
        layout.addLayout(header)

        self._title_edit = QLineEdit()
        self._title_edit.setObjectName("titleEdit")
        self._title_edit.setPlaceholderText("任务标题")
        layout.addWidget(self._title_edit)

        self._summary_edit = QTextEdit()
        self._summary_edit.setObjectName("summaryEdit")
        self._summary_edit.setPlaceholderText("一句话现状摘要")
        self._summary_edit.setMinimumHeight(100)
        layout.addWidget(self._summary_edit)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)

        self._meta_label = QLabel("")
        self._meta_label.setObjectName("metaLabel")
        actions.addWidget(self._meta_label)

        actions.addStretch()

        save_button = QPushButton("保存")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._save)
        actions.addWidget(save_button)
        layout.addLayout(actions)

        timeline_header = QLabel("时间线")
        timeline_header.setObjectName("sectionTitle")
        layout.addWidget(timeline_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._timeline_container = QWidget()
        self._timeline_layout = QVBoxLayout(self._timeline_container)
        self._timeline_layout.setContentsMargins(0, 0, 0, 0)
        self._timeline_layout.setSpacing(8)
        self._timeline_layout.addStretch()
        scroll.setWidget(self._timeline_container)
        layout.addWidget(scroll, 1)

        root_layout.addWidget(surface)
        self.resize(420, 560)
        self.setMinimumWidth(380)
        self.setMaximumWidth(460)
        self._apply_style()
        self.hide()

    def show_todo(self, todo: TodoItem, anchor_rect=None) -> None:
        self._todo_id = todo.id
        self._title_edit.setText(todo.title)
        self._summary_edit.setPlainText(todo.summary)
        self._meta_label.setText(f"{todo.timeline_count} 条记录  ·  更新于 {_format_ts(todo.updated_at)}")

        while self._timeline_layout.count() > 1:
            item = self._timeline_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for event in reversed(todo.timeline):
            card = _TimelineCard(
                f"{_format_ts(event.timestamp)}  ·  {event.scenario or '分析'}",
                event.summary,
                event.detail,
                self._timeline_container,
            )
            self._timeline_layout.insertWidget(self._timeline_layout.count() - 1, card)

        self._reposition(anchor_rect)
        self.show()
        self.raise_()
        self.activateWindow()

    def _reposition(self, anchor_rect=None) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = 18
        if anchor_rect is None:
            x = available.right() - self.width() - margin
            y = available.top() + margin
        else:
            x = anchor_rect.left() - self.width() - 12
            if x < available.left() + margin:
                x = anchor_rect.right() + 12
            x = min(x, available.right() - self.width() - margin)
            y = anchor_rect.top()
            y = max(available.top() + margin, min(y, available.bottom() - self.height() - margin))
        self.move(x, y)

    def _save(self) -> None:
        if self._todo_id is None:
            return
        self.save_requested.emit(
            self._todo_id,
            self._title_edit.text(),
            self._summary_edit.toPlainText(),
        )

    def _close_panel(self) -> None:
        self.hide()
        self.closed.emit()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: transparent;
                color: #e8eef8;
                font-family: 'Segoe UI Variable Text', 'Microsoft YaHei UI', sans-serif;
            }
            QFrame#detailSurface {
                background-color: rgba(11, 17, 29, 224);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 18px;
            }
            QLabel#headerTitle, QLabel#sectionTitle {
                color: #ffffff;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#metaLabel, QLabel#timeLabel {
                color: rgba(232, 238, 248, 0.66);
                font-size: 11px;
            }
            QLabel#summaryLabel {
                color: #ffffff;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#detailLabel {
                color: rgba(232, 238, 248, 0.86);
                font-size: 11px;
            }
            QFrame#timelineCard {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QLineEdit#titleEdit, QTextEdit#summaryEdit {
                background-color: rgba(255, 255, 255, 0.06);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 10px 12px;
                selection-background-color: rgba(120, 192, 255, 0.40);
            }
            QPushButton#primaryButton, QPushButton#ghostButton {
                border-radius: 10px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#primaryButton {
                color: #0f172a;
                background-color: rgba(230, 244, 255, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.14);
            }
            QPushButton#ghostButton {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            """
        )

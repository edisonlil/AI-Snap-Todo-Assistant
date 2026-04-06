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
        layout.setSpacing(5)

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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title = QLabel("任务详情")
        title.setObjectName("headerTitle")
        header.addWidget(title)

        header.addStretch()

        close_button = QPushButton("关闭")
        close_button.setObjectName("ghostButton")
        close_button.clicked.connect(self._close_panel)
        header.addWidget(close_button)
        layout.addLayout(header)

        summary_card = QFrame()
        summary_card.setObjectName("editorCard")
        summary_card_layout = QVBoxLayout(summary_card)
        summary_card_layout.setContentsMargins(12, 12, 12, 12)
        summary_card_layout.setSpacing(8)

        title_hint = QLabel("标题")
        title_hint.setObjectName("fieldLabel")
        summary_card_layout.addWidget(title_hint)

        self._title_edit = QLineEdit()
        self._title_edit.setObjectName("titleEdit")
        self._title_edit.setPlaceholderText("任务标题")
        summary_card_layout.addWidget(self._title_edit)

        summary_hint = QLabel("当前摘要")
        summary_hint.setObjectName("fieldLabel")
        summary_card_layout.addWidget(summary_hint)

        self._summary_edit = QTextEdit()
        self._summary_edit.setObjectName("summaryEdit")
        self._summary_edit.setPlaceholderText("一句话记录当前结论或处理状态")
        self._summary_edit.setMinimumHeight(84)
        summary_card_layout.addWidget(self._summary_edit)

        layout.addWidget(summary_card)

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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("timelineScroll")

        self._timeline_container = QWidget()
        self._timeline_layout = QVBoxLayout(self._timeline_container)
        self._timeline_layout.setContentsMargins(0, 0, 0, 0)
        self._timeline_layout.setSpacing(6)
        self._timeline_layout.addStretch()
        scroll.setWidget(self._timeline_container)
        layout.addWidget(scroll, 1)

        root_layout.addWidget(surface)
        self.resize(420, 540)
        self.setMinimumWidth(392)
        self.setMaximumWidth(460)
        self._apply_style()
        self.hide()

    def show_todo(self, todo: TodoItem, anchor_rect=None) -> None:
        self._todo_id = todo.id
        self._title_edit.setText(todo.title)
        self._summary_edit.setPlainText(todo.summary)
        self._meta_label.setText(f"{todo.timeline_count} 条记录 · 更新于 {_format_ts(todo.updated_at)}")

        while self._timeline_layout.count() > 1:
            item = self._timeline_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for event in reversed(todo.timeline):
            card = _TimelineCard(
                f"{_format_ts(event.timestamp)} · {event.scenario or '分析'}",
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
                color: #1f2937;
                font-family: 'SF Pro Text', 'Segoe UI Variable Text', 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
            }
            QFrame#detailSurface {
                background-color: rgba(247, 246, 242, 242);
                border: 1px solid rgba(255, 255, 255, 0.70);
                border-radius: 28px;
            }
            QLabel#headerTitle, QLabel#sectionTitle {
                color: #171717;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#metaLabel, QLabel#timeLabel {
                color: rgba(23, 23, 23, 0.46);
                font-size: 11px;
            }
            QLabel#fieldLabel {
                color: rgba(23, 23, 23, 0.52);
                font-size: 10px;
                font-weight: 600;
            }
            QLabel#summaryLabel {
                color: #161616;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#detailLabel {
                color: rgba(23, 23, 23, 0.58);
                font-size: 10px;
                line-height: 1.45;
            }
            QScrollArea#timelineScroll {
                background: transparent;
                border: none;
            }
            QFrame#timelineCard {
                background-color: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(17, 24, 39, 0.05);
                border-radius: 18px;
            }
            QFrame#editorCard {
                background-color: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(17, 24, 39, 0.05);
                border-radius: 20px;
            }
            QLineEdit#titleEdit, QTextEdit#summaryEdit {
                background-color: rgba(255, 255, 255, 0.92);
                color: #111827;
                border: 1px solid rgba(17, 24, 39, 0.08);
                border-radius: 14px;
                padding: 9px 11px;
                selection-background-color: rgba(147, 197, 253, 0.42);
            }
            QPushButton#primaryButton, QPushButton#ghostButton {
                border-radius: 999px;
                padding: 5px 12px;
                font-size: 10px;
                font-weight: 500;
            }
            QPushButton#primaryButton {
                color: #1d4ed8;
                background-color: rgba(238, 244, 255, 0.96);
                border: 1px solid rgba(214, 228, 251, 0.92);
            }
            QPushButton#ghostButton {
                color: rgba(17, 24, 39, 0.70);
                background-color: rgba(255, 253, 252, 0.96);
                border: 1px solid rgba(236, 231, 222, 0.96);
            }
            """
        )

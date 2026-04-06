"""Detail side panel for a todo item and its timeline."""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import TicketSummaryFields
from .todo_store import TimelineEvent, TodoItem


def _format_ts(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%m-%d %H:%M")
    except ValueError:
        return value


class _TimelineEditorCard(QFrame):
    def __init__(self, event: TimelineEvent, parent=None):
        super().__init__(parent)
        self._event_id = event.id
        self._timestamp = event.timestamp
        self._scenario = event.scenario
        self.setObjectName("timelineCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        meta = QLabel(f"{_format_ts(event.timestamp)} · {event.scenario or '分析'}")
        meta.setObjectName("timeLabel")
        layout.addWidget(meta)

        self._content_edit = QTextEdit()
        self._content_edit.setObjectName("timelineEdit")
        self._content_edit.setPlainText(event.content)
        self._content_edit.setMinimumHeight(72)
        layout.addWidget(self._content_edit)

    def build_event(self) -> TimelineEvent:
        return TimelineEvent(
            id=self._event_id,
            timestamp=self._timestamp,
            scenario=self._scenario,
            content=self._content_edit.toPlainText().strip(),
        )


class TodoDetailPanel(QWidget):
    save_requested = pyqtSignal(str, object)
    closed = pyqtSignal()
    complete_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._todo_id: str | None = None
        self._timeline_cards: list[_TimelineEditorCard] = []

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
        title = QLabel("任务详情")
        title.setObjectName("headerTitle")
        header.addWidget(title)
        header.addStretch()
        close_button = QPushButton("关闭")
        close_button.setObjectName("ghostButton")
        close_button.clicked.connect(self._close_panel)
        header.addWidget(close_button)
        layout.addLayout(header)

        fields_card = QFrame()
        fields_card.setObjectName("editorCard")
        fields_layout = QVBoxLayout(fields_card)
        fields_layout.setContentsMargins(12, 12, 12, 12)
        fields_layout.setSpacing(8)

        self._title_edit = QLineEdit()
        self._title_edit.setObjectName("titleEdit")
        self._title_edit.setPlaceholderText("任务标题")
        fields_layout.addWidget(self._title_edit)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self._group_name_edit = QLineEdit()
        self._environment_edit = QLineEdit()
        self._product_line_edit = QLineEdit()
        self._ticket_type_edit = QLineEdit()
        form.addRow("群聊名称", self._group_name_edit)
        form.addRow("环境", self._environment_edit)
        form.addRow("产品线", self._product_line_edit)
        form.addRow("工单类型", self._ticket_type_edit)
        fields_layout.addLayout(form)

        summary_label = QLabel("当前摘要")
        summary_label.setObjectName("fieldLabel")
        fields_layout.addWidget(summary_label)

        self._summary_edit = QTextEdit()
        self._summary_edit.setObjectName("summaryEdit")
        self._summary_edit.setPlaceholderText("一句话记录当前结论或处理状态")
        self._summary_edit.setMinimumHeight(84)
        fields_layout.addWidget(self._summary_edit)
        layout.addWidget(fields_card)

        actions = QHBoxLayout()
        self._meta_label = QLabel("")
        self._meta_label.setObjectName("metaLabel")
        actions.addWidget(self._meta_label)
        actions.addStretch()
        complete_button = QPushButton("完成待办")
        complete_button.setObjectName("ghostButton")
        complete_button.clicked.connect(self._complete)
        actions.addWidget(complete_button)
        delete_button = QPushButton("删除待办")
        delete_button.setObjectName("dangerButton")
        delete_button.clicked.connect(self._delete)
        actions.addWidget(delete_button)
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
        scroll.setObjectName("timelineScroll")

        self._timeline_container = QWidget()
        self._timeline_layout = QVBoxLayout(self._timeline_container)
        self._timeline_layout.setContentsMargins(0, 0, 0, 0)
        self._timeline_layout.setSpacing(6)
        self._timeline_layout.addStretch()
        scroll.setWidget(self._timeline_container)
        layout.addWidget(scroll, 1)

        root_layout.addWidget(surface)
        self.resize(440, 560)
        self.setMinimumWidth(408)
        self.setMaximumWidth(480)
        self._apply_style()
        self.hide()

    def show_todo(self, todo: TodoItem, anchor_rect=None) -> None:
        self._todo_id = todo.id
        self._title_edit.setText(todo.title)
        self._group_name_edit.setText(todo.summary_fields.group_name)
        self._environment_edit.setText(todo.summary_fields.environment)
        self._product_line_edit.setText(todo.summary_fields.product_line)
        self._ticket_type_edit.setText(todo.summary_fields.ticket_type)
        self._summary_edit.setPlainText(todo.current_summary)
        self._meta_label.setText(f"{todo.timeline_count} 条记录 · 更新于 {_format_ts(todo.updated_at)}")

        self._timeline_cards = []
        while self._timeline_layout.count() > 1:
            item = self._timeline_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for event in reversed(todo.timeline):
            card = _TimelineEditorCard(event, self._timeline_container)
            self._timeline_cards.append(card)
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
        payload = {
            "title": self._title_edit.text().strip(),
            "current_summary": self._summary_edit.toPlainText().strip(),
            "summary_fields": TicketSummaryFields(
                group_name=self._group_name_edit.text().strip() or "未知",
                environment=self._environment_edit.text().strip() or "未知",
                product_line=self._product_line_edit.text().strip() or "未知",
                ticket_type=self._ticket_type_edit.text().strip() or "未知",
            ).to_dict(),
            "timeline": [card.build_event() for card in self._timeline_cards],
        }
        self.save_requested.emit(self._todo_id, payload)

    def _close_panel(self) -> None:
        self.hide()
        self.closed.emit()

    def _complete(self) -> None:
        if self._todo_id is None:
            return
        self.complete_requested.emit(self._todo_id)

    def _delete(self) -> None:
        if self._todo_id is None:
            return
        self.delete_requested.emit(self._todo_id)

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
            QFrame#editorCard, QFrame#timelineCard {
                background-color: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(17, 24, 39, 0.05);
                border-radius: 18px;
            }
            QLineEdit, QTextEdit {
                background-color: #fffdfc;
                color: #111827;
                border: 1px solid rgba(17, 24, 39, 0.08);
                border-radius: 14px;
                padding: 9px 11px;
                selection-background-color: rgba(147, 197, 253, 0.42);
                font-size: 12px;
            }
            QTextEdit#timelineEdit {
                min-height: 72px;
            }
            QPushButton#primaryButton, QPushButton#ghostButton, QPushButton#dangerButton {
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
            QPushButton#dangerButton {
                color: #b42318;
                background-color: rgba(254, 242, 242, 0.98);
                border: 1px solid rgba(254, 205, 211, 0.98);
            }
            """
        )

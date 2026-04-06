"""Structured confirmation dialog for ticket snapshots."""
from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from aica.feedback import FeedbackData
from aica.models import TicketSnapshot, TicketSummaryFields


class ResultDialog(QDialog):
    """Displays a structured ticket snapshot for review before saving."""

    def __init__(
        self,
        result: TicketSnapshot,
        scenario: str,
        model: str,
        feedback_callback: Optional[Callable] = None,
        save_callback: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._original_result = result
        self._scenario = scenario
        self._model = model
        self._feedback_callback = feedback_callback
        self._save_callback = save_callback

        self.setObjectName("resultDialog")
        self._setup_ui()
        self._apply_style()

        self.setWindowTitle(f"工单待办确认 - {scenario}")
        self.resize(760, 620)
        self.setMinimumSize(660, 520)
        self.setSizeGripEnabled(True)
        self._positioned = False

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        surface = QFrame()
        surface.setObjectName("surface")
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(16, 14, 16, 14)
        surface_layout.setSpacing(10)
        root_layout.addWidget(surface)

        header = QHBoxLayout()
        header_left = QVBoxLayout()
        title = QLabel("工单待办确认")
        title.setObjectName("titleLabel")
        header_left.addWidget(title)

        meta_row = QHBoxLayout()
        meta_row.addWidget(self._build_meta_chip(self._scenario))
        meta_row.addWidget(self._build_meta_chip(self._model))
        meta_row.addStretch()
        header_left.addLayout(meta_row)
        surface_layout.addLayout(header)
        header.addLayout(header_left, 1)

        close_button = QPushButton("关闭")
        close_button.setObjectName("secondaryAction")
        close_button.clicked.connect(self.reject)
        header.addWidget(close_button)

        fields_card = self._build_section_card("工单字段", "确认当前任务的固定字段。")
        fields_body = fields_card.layout().itemAt(2).widget().layout()
        fields_form = QFormLayout()
        fields_form.setContentsMargins(0, 0, 0, 0)
        fields_form.setSpacing(8)

        self._title_edit = QLineEdit(self._original_result.title)
        self._group_name_edit = QLineEdit(self._original_result.fields.group_name)
        self._environment_edit = QLineEdit(self._original_result.fields.environment)
        self._product_line_edit = QLineEdit(self._original_result.fields.product_line)
        self._ticket_type_edit = QLineEdit(self._original_result.fields.ticket_type)

        fields_form.addRow("标题", self._title_edit)
        fields_form.addRow("群聊名称", self._group_name_edit)
        fields_form.addRow("环境", self._environment_edit)
        fields_form.addRow("产品线", self._product_line_edit)
        fields_form.addRow("工单类型", self._ticket_type_edit)
        fields_body.addLayout(fields_form)
        surface_layout.addWidget(fields_card)

        summary_card = self._build_section_card("当前摘要", "用自然语言描述当前结论或状态。")
        summary_body = summary_card.layout().itemAt(2).widget().layout()
        self._summary_edit = QTextEdit()
        self._summary_edit.setObjectName("contentEditor")
        self._summary_edit.setPlainText(self._original_result.current_summary)
        self._summary_edit.setMinimumHeight(120)
        summary_body.addWidget(self._summary_edit)
        surface_layout.addWidget(summary_card)

        timeline_card = self._build_section_card("本次时间线记录", "本次截图分析要追加的一条跟进文本。")
        timeline_body = timeline_card.layout().itemAt(2).widget().layout()
        self._timeline_edit = QTextEdit()
        self._timeline_edit.setObjectName("contentEditor")
        self._timeline_edit.setPlainText(self._original_result.timeline_entry)
        self._timeline_edit.setMinimumHeight(140)
        timeline_body.addWidget(self._timeline_edit)
        surface_layout.addWidget(timeline_card, 1)

        footer = QFrame()
        footer.setObjectName("footerBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)

        footer_hint = QLabel("保存后会创建待办或追加到当前选中的待办。")
        footer_hint.setObjectName("footerHint")
        footer_layout.addWidget(footer_hint)
        footer_layout.addStretch()

        feedback_button = QPushButton("反馈修正")
        feedback_button.setObjectName("secondaryAction")
        feedback_button.clicked.connect(self._on_feedback)
        footer_layout.addWidget(feedback_button)

        save_button = QPushButton("保存并关闭")
        save_button.setObjectName("primaryAction")
        save_button.clicked.connect(self._on_save)
        footer_layout.addWidget(save_button)
        surface_layout.addWidget(footer)

    def _build_meta_chip(self, text: str) -> QLabel:
        chip = QLabel(text)
        chip.setObjectName("metaChip")
        return chip

    def _build_section_card(self, title: str, description: str) -> QFrame:
        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        card_layout.addWidget(title_label)
        desc_label = QLabel(description)
        desc_label.setObjectName("sectionDesc")
        desc_label.setWordWrap(True)
        card_layout.addWidget(desc_label)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        card_layout.addWidget(body)
        return card

    def _build_snapshot(self) -> TicketSnapshot:
        return TicketSnapshot(
            title=self._title_edit.text().strip() or "未分类任务",
            fields=TicketSummaryFields(
                group_name=self._group_name_edit.text().strip() or "未知",
                environment=self._environment_edit.text().strip() or "未知",
                product_line=self._product_line_edit.text().strip() or "未知",
                ticket_type=self._ticket_type_edit.text().strip() or "未知",
            ),
            current_summary=self._summary_edit.toPlainText().strip() or "待补充",
            timeline_entry=self._timeline_edit.toPlainText().strip() or "待补充跟进记录",
        )

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog#resultDialog {
                background-color: #f7f6f2;
                color: #111827;
                font-family: 'SF Pro Text', 'Segoe UI Variable Text', 'PingFang SC', 'Microsoft YaHei UI', sans-serif;
            }
            QFrame#surface {
                background-color: #f7f6f2;
                border: none;
            }
            QLabel#titleLabel {
                color: #171717;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#metaChip {
                color: #374151;
                background-color: #fffdfc;
                border: 1px solid #ece7de;
                border-radius: 999px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 500;
            }
            QFrame#sectionCard, QFrame#footerBar {
                background-color: rgba(255, 255, 255, 0.80);
                border: 1px solid rgba(17, 24, 39, 0.06);
                border-radius: 18px;
            }
            QLabel#sectionTitle {
                color: #111827;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#sectionDesc, QLabel#footerHint {
                color: #6b7280;
                font-size: 11px;
            }
            QLineEdit, QTextEdit {
                background-color: #fffdfc;
                color: #111827;
                border: 1px solid rgba(17, 24, 39, 0.08);
                border-radius: 14px;
                padding: 10px 12px;
                selection-background-color: rgba(147, 197, 253, 0.42);
                font-size: 12px;
            }
            QPushButton {
                border-radius: 999px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton#primaryAction {
                color: #1d4ed8;
                background-color: #eef4ff;
                border: 1px solid #d6e4fb;
            }
            QPushButton#secondaryAction {
                color: #4b5563;
                background-color: #fffdfc;
                border: 1px solid #ece7de;
            }
            """
        )

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._positioned:
            self._fit_within_screen()
            self._positioned = True

    def _fit_within_screen(self) -> None:
        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = 16
        self.resize(
            min(self.width(), available.width() - margin * 2),
            min(self.height(), available.height() - margin * 2),
        )
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def _on_save(self) -> None:
        snapshot = self._build_snapshot()
        if self._save_callback:
            self._save_callback(snapshot)
        self.accept()

    def _on_feedback(self) -> None:
        snapshot = self._build_snapshot()
        feedback_data = FeedbackData(
            scenario=self._scenario,
            model=self._model,
            ai_output=self._original_result.to_dict(),
            user_edited=(snapshot.to_dict() != self._original_result.to_dict()),
            original_result=str(self._original_result),
            edited_result=str(snapshot),
            feedback_status="incorrect",
        )
        if self._feedback_callback:
            self._feedback_callback(snapshot, feedback_data)
        self.reject()

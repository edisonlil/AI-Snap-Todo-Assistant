"""Feedback dialog for reviewing and saving corrections."""
from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from aica.feedback import FeedbackCollector, FeedbackData
from aica.runtime import RUNTIME_CAPABILITIES


class FeedbackPanel(QDialog):
    """Collects user feedback on AI recognition results."""

    def __init__(
        self,
        result_str: str,
        feedback_data: FeedbackData,
        scenario: str,
        model: str,
        save_callback: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._result_str = result_str
        self._feedback_data = feedback_data
        self._scenario = scenario
        self._model = model
        self._save_callback = save_callback
        self._collector = FeedbackCollector()

        self._save_button: QPushButton | None = None

        self.setObjectName("feedbackDialog")
        self._setup_ui()
        self._apply_style()

        self.setWindowTitle("反馈修正")
        self.resize(780, 580)
        self.setMinimumSize(620, 460)
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
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(12)

        header_left = QVBoxLayout()
        header_left.setContentsMargins(0, 0, 0, 0)
        header_left.setSpacing(6)

        title = QLabel("反馈修正")
        title.setObjectName("titleLabel")
        header_left.addWidget(title)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)
        meta_row.addWidget(self._build_meta_chip(self._scenario))
        meta_row.addWidget(self._build_meta_chip(self._model))
        meta_row.addStretch()
        header_left.addLayout(meta_row)

        desc = QLabel("将结果修正为你真正想要的内容，可补充错误原因或格式要求。")
        desc.setObjectName("descLabel")
        desc.setWordWrap(True)
        header_left.addWidget(desc)

        header.addLayout(header_left, 1)

        btn_close = QPushButton("关闭")
        btn_close.setObjectName("secondaryAction")
        btn_close.setMinimumWidth(72)
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)

        surface_layout.addLayout(header)

        result_card = self._build_section_card(
            "修正后的结果",
            "直接修改成你真正想要的输出结果。",
        )
        result_body = result_card.layout().itemAt(2).widget().layout()
        self._ai_result_edit = QTextEdit()
        self._ai_result_edit.setObjectName("resultEditor")
        self._ai_result_edit.setPlainText(self._result_str)
        self._ai_result_edit.setMinimumHeight(280)
        result_body.addWidget(self._ai_result_edit)
        surface_layout.addWidget(result_card, 1)

        notes_card = self._build_section_card(
            "补充说明",
            "可选填写：哪里错了、为什么错、以后希望它遵循什么格式或约束。",
        )
        notes_body = notes_card.layout().itemAt(2).widget().layout()
        self._notes_edit = QTextEdit()
        self._notes_edit.setObjectName("notesEditor")
        self._notes_edit.setPlainText(self._feedback_data.notes)
        self._notes_edit.setPlaceholderText("补充背景、限制条件、风格要求或纠错原因")
        self._notes_edit.setMinimumHeight(96)
        self._notes_edit.setMaximumHeight(124)
        notes_body.addWidget(self._notes_edit)
        surface_layout.addWidget(notes_card)

        footer = QFrame()
        footer.setObjectName("footerBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_layout.setSpacing(8)

        footer_hint = QLabel("保存后会保留纠错内容，并关联本次分析的 Prompt Trace。")
        footer_hint.setObjectName("footerHint")
        footer_layout.addWidget(footer_hint)
        footer_layout.addStretch()

        self._save_button = QPushButton("保存反馈")
        self._save_button.setObjectName("primaryAction")
        self._save_button.setMinimumWidth(102)
        self._save_button.clicked.connect(self._on_save_feedback)
        footer_layout.addWidget(self._save_button)

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

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog#feedbackDialog {
                background-color: #ffffff;
                color: #111827;
                font-family: %s;
            }
            QFrame#surface {
                background-color: #ffffff;
                border: none;
                border-radius: 0;
            }
            QLabel#titleLabel {
                color: #111827;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#descLabel {
                color: #667085;
                font-size: 12px;
                line-height: 1.5;
            }
            QLabel#metaChip {
                color: #344054;
                background-color: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 7px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QFrame#sectionCard {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
            QLabel#sectionTitle {
                color: #111827;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#sectionDesc, QLabel#footerHint {
                color: #667085;
                font-size: 11px;
                line-height: 1.5;
            }
            QTextEdit#resultEditor {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d7dce2;
                border-radius: 10px;
                padding: 12px 14px;
                selection-background-color: #dbeafe;
                font-family: %s;
                font-size: 12px;
                line-height: 1.55;
            }
            QTextEdit#notesEditor {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d7dce2;
                border-radius: 10px;
                padding: 10px 12px;
                selection-background-color: #dbeafe;
                font-size: 12px;
                line-height: 1.5;
            }
            QTextEdit#resultEditor:focus, QTextEdit#notesEditor:focus {
                border: 1px solid #1677ff;
                background-color: #ffffff;
            }
            QFrame#footerBar {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
            QPushButton {
                border-radius: 9px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                min-height: 18px;
            }
            QPushButton#primaryAction {
                color: #ffffff;
                background-color: #1677ff;
                border: 1px solid #1677ff;
            }
            QPushButton#primaryAction:hover {
                background-color: #2b85ff;
                border: 1px solid #2b85ff;
            }
            QPushButton#primaryAction:pressed {
                background-color: #0e63d6;
                border: 1px solid #0e63d6;
            }
            QPushButton#secondaryAction {
                color: #111827;
                background-color: #ffffff;
                border: 1px solid #d1d5db;
            }
            QPushButton#secondaryAction:hover {
                background-color: #f9fafb;
                border: 1px solid #9ca3af;
            }
            QPushButton#secondaryAction:pressed {
                background-color: #f3f4f6;
            }
            """
            % (RUNTIME_CAPABILITIES.widget_font_css, RUNTIME_CAPABILITIES.monospace_font_css)
        )

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._positioned:
            self._fit_within_screen()
            self._positioned = True

    def _fit_within_screen(self) -> None:
        screen = QApplication.screenAt(self.pos()) or QApplication.screenAt(self.mapToGlobal(self.rect().center()))
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        margin = 16
        max_width = max(620, available.width() - margin * 2)
        max_height = max(460, available.height() - margin * 2)

        self.setMaximumSize(max_width, max_height)
        self.resize(
            min(self.width(), max_width),
            min(self.height(), max_height),
        )

        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        x = max(available.left() + margin, min(frame.left(), available.right() - frame.width() - margin + 1))
        y = max(available.top() + margin, min(frame.top(), available.bottom() - frame.height() - margin + 1))
        self.move(x, y)

    def _prepare_feedback_data(self) -> None:
        edited_ai_result = self._ai_result_edit.toPlainText()
        self._feedback_data.user_edited = edited_ai_result != self._result_str
        self._feedback_data.original_result = self._result_str
        self._feedback_data.edited_result = edited_ai_result
        self._feedback_data.notes = self._notes_edit.toPlainText()
        self._feedback_data.problem_tags = []
        self._collector.save_feedback(self._feedback_data)

    def _on_save_feedback(self) -> None:
        self._prepare_feedback_data()

        if self._save_callback:
            self._save_callback(self._feedback_data)

        self.accept()

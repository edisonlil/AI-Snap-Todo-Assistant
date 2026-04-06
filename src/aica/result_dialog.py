"""Result dialog for reviewing and copying extracted AI content."""
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

from aica.feedback import FeedbackData


class ResultDialog(QDialog):
    """Displays extracted content and allows light editing before copy."""

    def __init__(
        self,
        result,
        scenario: str,
        model: str,
        feedback_callback: Optional[Callable] = None,
        save_callback: Optional[Callable] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._original_result = result
        self._original_result_str = str(result)
        self._scenario = scenario
        self._model = model
        self._feedback_callback = feedback_callback
        self._save_callback = save_callback

        self.setObjectName("resultDialog")
        self._setup_ui()
        self._apply_style()

        self.setWindowTitle(f"内容提取结果 - {scenario}")
        self.resize(760, 560)
        self.setMinimumSize(600, 420)
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

        title = QLabel("内容提取结果")
        title.setObjectName("titleLabel")
        header_left.addWidget(title)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)
        meta_row.addWidget(self._build_meta_chip(self._scenario))
        meta_row.addWidget(self._build_meta_chip(self._model))
        meta_row.addStretch()
        header_left.addLayout(meta_row)

        desc = QLabel("可直接修正提取内容。复制后会自动写入剪贴板并结束本次截图流程。")
        desc.setObjectName("descLabel")
        desc.setWordWrap(True)
        header_left.addWidget(desc)

        header.addLayout(header_left, 1)

        self._btn_close = QPushButton("关闭")
        self._btn_close.setObjectName("secondaryAction")
        self._btn_close.setMinimumWidth(72)
        self._btn_close.clicked.connect(self.reject)
        header.addWidget(self._btn_close)

        surface_layout.addLayout(header)

        result_card = self._build_section_card(
            "提取内容",
            "适合处理结构化结果、摘要内容、工单信息或界面文案提取结果。",
        )
        result_body = result_card.layout().itemAt(2).widget().layout()
        self._result_edit = QTextEdit()
        self._result_edit.setObjectName("resultEditor")
        self._result_edit.setPlainText(self._original_result_str)
        self._result_edit.setMinimumHeight(320)
        result_body.addWidget(self._result_edit)
        surface_layout.addWidget(result_card, 1)

        footer = QFrame()
        footer.setObjectName("footerBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_layout.setSpacing(8)

        footer_hint = QLabel("不准确时可进入反馈修正，帮助后续提示词优化。")
        footer_hint.setObjectName("footerHint")
        footer_layout.addWidget(footer_hint)
        footer_layout.addStretch()

        self._btn_feedback = QPushButton("反馈修正")
        self._btn_feedback.setObjectName("secondaryAction")
        self._btn_feedback.setMinimumWidth(88)
        self._btn_feedback.clicked.connect(self._on_feedback)
        footer_layout.addWidget(self._btn_feedback)

        self._btn_copy = QPushButton("复制并关闭")
        self._btn_copy.setObjectName("primaryAction")
        self._btn_copy.setMinimumWidth(98)
        self._btn_copy.clicked.connect(self._on_save)
        footer_layout.addWidget(self._btn_copy)

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
            QDialog#resultDialog {
                background-color: #ffffff;
                color: #111827;
                font-family: 'Segoe UI Variable Text', 'Microsoft YaHei UI', sans-serif;
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
                font-family: 'Cascadia Mono', 'Consolas', 'Microsoft YaHei UI', monospace;
                font-size: 12px;
                line-height: 1.55;
            }
            QTextEdit#resultEditor:focus {
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
        max_width = max(560, available.width() - margin * 2)
        max_height = max(420, available.height() - margin * 2)

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

    def _on_save(self) -> None:
        edited_result = self._result_edit.toPlainText()
        if self._save_callback:
            self._save_callback(edited_result)
        self.accept()

    def _on_feedback(self) -> None:
        edited_result = self._result_edit.toPlainText()
        feedback_data = FeedbackData(
            scenario=self._scenario,
            model=self._model,
            ai_output={"raw": self._original_result_str},
            user_edited=(edited_result != self._original_result_str),
            original_result=self._original_result_str,
            edited_result=edited_result,
            feedback_status="incorrect",
        )
        if self._feedback_callback:
            self._feedback_callback(edited_result, feedback_data)
        self.reject()

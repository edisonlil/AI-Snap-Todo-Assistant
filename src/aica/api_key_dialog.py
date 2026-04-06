"""Dialog for collecting and saving API key configuration."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from aica.config import AppConfig, ConfigManager


class ApiKeyDialog(QDialog):
    """Prompts the user to fill in the API key when it is missing."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._config = config_manager.load()
        self._saved_config: AppConfig | None = None
        self._setup_ui()
        self._apply_style()

        self.setWindowTitle("配置 API Key")
        self.setModal(True)
        self.setMinimumWidth(520)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)
        layout.addWidget(card)

        title = QLabel("还没有配置 API Key")
        title.setObjectName("titleLabel")
        card_layout.addWidget(title)

        desc = QLabel(
            "当前执行智能总结需要可用的视觉模型接口。"
            "请先填写 API Key，保存后会继续本次总结。"
        )
        desc.setObjectName("descLabel")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        key_label = QLabel("API Key")
        key_label.setObjectName("fieldLabel")
        card_layout.addWidget(key_label)

        self._api_key_edit = QLineEdit(self._config.api_key)
        self._api_key_edit.setPlaceholderText("请输入 API Key")
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setClearButtonEnabled(True)
        self._api_key_edit.returnPressed.connect(self._on_save)
        card_layout.addWidget(self._api_key_edit)

        self._error_label = QLabel("")
        self._error_label.setObjectName("errorLabel")
        self._error_label.hide()
        card_layout.addWidget(self._error_label)

        hint = QLabel(f"配置会保存到: {self._config_manager.path}")
        hint.setObjectName("hintLabel")
        hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        buttons.addStretch()

        btn_cancel = QPushButton("取消")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_cancel)

        btn_save = QPushButton("保存并继续")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._on_save)
        buttons.addWidget(btn_save)

        layout.addLayout(buttons)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background-color: #f6f7f9;
                color: #111827;
                font-family: 'Segoe UI Variable Text', 'Microsoft YaHei UI', sans-serif;
            }
            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
            }
            QLabel#titleLabel {
                color: #111827;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#descLabel, QLabel#hintLabel {
                color: #4b5563;
                font-size: 12px;
                line-height: 1.5;
            }
            QLabel#fieldLabel {
                color: #111827;
                font-size: 12px;
                font-weight: 600;
                padding-top: 4px;
            }
            QLabel#errorLabel {
                color: #dc2626;
                font-size: 12px;
                font-weight: 600;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 9px 12px;
                font-size: 12px;
                min-height: 22px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton {
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 700;
                min-width: 92px;
            }
            QPushButton#primaryButton {
                color: #08111f;
                border: 1px solid rgba(125, 211, 252, 0.55);
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #a5f3fc,
                    stop: 0.55 #7dd3fc,
                    stop: 1 #38bdf8
                );
            }
            QPushButton#primaryButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #cffafe,
                    stop: 0.55 #93c5fd,
                    stop: 1 #60a5fa
                );
            }
            QPushButton#secondaryButton {
                color: #111827;
                background-color: #ffffff;
                border: 1px solid #d1d5db;
            }
            QPushButton#secondaryButton:hover {
                background-color: #f9fafb;
            }
            """
        )

    def _on_save(self) -> None:
        api_key = self._api_key_edit.text().strip()
        if not api_key:
            self._error_label.setText("API Key 不能为空")
            self._error_label.show()
            self._api_key_edit.setFocus(Qt.FocusReason.OtherFocusReason)
            return

        self._config.api_key = api_key
        self._config_manager.save(self._config)
        self._saved_config = self._config
        self.accept()

    def get_saved_config(self) -> AppConfig | None:
        return self._saved_config

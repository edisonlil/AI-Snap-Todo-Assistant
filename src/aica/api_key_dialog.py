"""Dialog for configuring providers and task model bindings."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from aica.config import AppConfig, ConfigManager, TaskModelBinding
from aica.llm.service import LLMService, ModelResolutionError


class ApiKeyDialog(QDialog):
    """Collects provider credentials and task model bindings."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._config = config_manager.load()
        self._saved_config: AppConfig | None = None
        self._provider_rows: dict[str, dict[str, object]] = {}
        self._task_provider_boxes: dict[str, QComboBox] = {}
        self._task_model_boxes: dict[str, QComboBox] = {}
        self._setup_ui()
        self._apply_style()

        self.setWindowTitle("配置模型供应商")
        self.setModal(True)
        self.setMinimumWidth(760)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(14)
        layout.addWidget(card)

        title = QLabel("配置模型供应商与任务模型")
        title.setObjectName("titleLabel")
        card_layout.addWidget(title)

        desc = QLabel(
            "AICA 现在支持多模型供应商。请为供应商填写 API Key，并为截图分析、标题生成、方案导出和 Prompt 优化分别选择模型。"
        )
        desc.setObjectName("descLabel")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        provider_section = QFrame()
        provider_layout = QGridLayout(provider_section)
        provider_layout.setContentsMargins(0, 0, 0, 0)
        provider_layout.setHorizontalSpacing(12)
        provider_layout.setVerticalSpacing(10)
        provider_layout.addWidget(self._section_label("供应商"), 0, 0, 1, 4)
        provider_layout.addWidget(QLabel("名称"), 1, 0)
        provider_layout.addWidget(QLabel("类型"), 1, 1)
        provider_layout.addWidget(QLabel("API Key"), 1, 2)
        provider_layout.addWidget(QLabel("Base URL / 说明"), 1, 3)

        for row, provider in enumerate(self._config.providers, 2):
            api_key_edit = QLineEdit(provider.api_key)
            api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            api_key_edit.setClearButtonEnabled(True)

            base_url_edit = QLineEdit(provider.base_url)
            base_url_edit.setPlaceholderText(
                "openai_compatible 必填；Gemini 可留空使用官方接口"
            )
            base_url_edit.setEnabled(provider.kind == "openai_compatible")

            provider_layout.addWidget(QLabel(provider.name), row, 0)
            provider_layout.addWidget(QLabel(provider.kind), row, 1)
            provider_layout.addWidget(api_key_edit, row, 2)
            provider_layout.addWidget(base_url_edit, row, 3)
            self._provider_rows[provider.id] = {
                "api_key": api_key_edit,
                "base_url": base_url_edit,
            }

        card_layout.addWidget(provider_section)

        task_section = QFrame()
        task_layout = QFormLayout(task_section)
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.setSpacing(10)
        task_layout.addRow(self._section_label("任务绑定"))

        task_labels = {
            "analysis": "截图分析",
            "title_generation": "标题生成",
            "plan_export": "方案导出",
            "prompt_optimization": "Prompt 优化",
        }
        bindings = self._config.task_model_bindings
        for task_name, label in task_labels.items():
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)

            provider_box = QComboBox()
            model_box = QComboBox()
            self._task_provider_boxes[task_name] = provider_box
            self._task_model_boxes[task_name] = model_box

            for provider in self._config.providers:
                provider_box.addItem(provider.name, provider.id)

            binding = getattr(bindings, task_name)
            selected_provider_index = max(provider_box.findData(binding.provider_id), 0)
            provider_box.setCurrentIndex(selected_provider_index)
            self._refresh_task_models(task_name, selected_model_id=binding.model_id)
            provider_box.currentIndexChanged.connect(lambda _idx, task=task_name: self._refresh_task_models(task))

            row.addWidget(provider_box, 1)
            row.addWidget(model_box, 1)
            task_layout.addRow(label, row)

        card_layout.addWidget(task_section)

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

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _refresh_task_models(self, task_name: str, selected_model_id: str = "") -> None:
        provider_id = str(self._task_provider_boxes[task_name].currentData() or "")
        model_box = self._task_model_boxes[task_name]
        model_box.blockSignals(True)
        model_box.clear()
        provider = next((item for item in self._config.providers if item.id == provider_id), None)
        if provider is not None:
            for model in provider.models:
                model_box.addItem(f"{model.name} ({', '.join(model.capabilities)})", model.id)
        target_index = model_box.findData(selected_model_id) if selected_model_id else 0
        if target_index < 0:
            target_index = 0
        if model_box.count() > 0:
            model_box.setCurrentIndex(target_index)
        model_box.blockSignals(False)

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
            QLabel#sectionLabel {
                color: #111827;
                font-size: 13px;
                font-weight: 700;
                padding: 6px 0 2px 0;
            }
            QLabel#descLabel, QLabel#hintLabel {
                color: #4b5563;
                font-size: 12px;
                line-height: 1.5;
            }
            QLabel#errorLabel {
                color: #dc2626;
                font-size: 12px;
                font-weight: 600;
            }
            QLineEdit, QComboBox {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 7px 10px;
                font-size: 12px;
                min-height: 20px;
            }
            QLineEdit:focus, QComboBox:focus {
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
            QPushButton#secondaryButton {
                color: #111827;
                background-color: #ffffff;
                border: 1px solid #d1d5db;
            }
            """
        )

    def _on_save(self) -> None:
        for provider in self._config.providers:
            row = self._provider_rows[provider.id]
            provider.api_key = str(row["api_key"].text()).strip()
            provider.base_url = str(row["base_url"].text()).strip()

        for task_name, provider_box in self._task_provider_boxes.items():
            model_box = self._task_model_boxes[task_name]
            setattr(
                self._config.task_model_bindings,
                task_name,
                TaskModelBinding(
                    provider_id=str(provider_box.currentData() or "").strip(),
                    model_id=str(model_box.currentData() or "").strip(),
                ),
            )

        self._config.default_provider_id = self._config.task_model_bindings.analysis.provider_id
        try:
            LLMService(self._config).resolve_task_model("analysis")
            LLMService(self._config).resolve_task_model("title_generation")
            LLMService(self._config).resolve_task_model("plan_export")
            LLMService(self._config).resolve_task_model("prompt_optimization")
        except ModelResolutionError as exc:
            self._error_label.setText(str(exc))
            self._error_label.show()
            return

        self._config_manager.save(self._config)
        self._saved_config = self._config
        self.accept()

    def get_saved_config(self) -> AppConfig | None:
        return self._saved_config

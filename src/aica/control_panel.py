"""QML-backed application control panel."""
from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout

from aica.config import ConfigManager, ProviderConfig, TaskModelBinding
from aica.control_panel_state import (
    format_image_limit_megabytes,
    persist_control_panel_config,
)
from aica.paths import (
    app_data_dir,
    config_file,
    error_log_file,
    feedback_dir,
    prompt_history_dir,
    prompts_file,
    qml_dir,
    todos_file,
)


_TASK_LABELS = {
    "analysis": "截图分析",
    "title_generation": "标题生成",
    "plan_export": "方案导出",
    "prompt_optimization": "Prompt 优化",
}
_SECTION_ITEMS = [
    {
        "id": "models",
        "title": "模型供应商",
        "description": "维护供应商凭证、请求地址与任务模型绑定。",
    },
    {
        "id": "hotkeys",
        "title": "快捷键",
        "description": "调整截图热键并立即生效。",
    },
    {
        "id": "storage",
        "title": "存储与日志",
        "description": "查看配置位置并快速跳转本地数据目录。",
    },
]


def _required_capability(task_name: str) -> str:
    if task_name == "title_generation":
        return "text_chat"
    return "vision_chat"


def _provider_payload(provider: ProviderConfig) -> dict[str, object]:
    return {
        "id": provider.id,
        "name": provider.name,
        "kind": provider.kind,
        "apiKey": provider.api_key,
        "baseUrl": provider.base_url,
        "timeoutSeconds": str(provider.timeout_seconds),
        "baseUrlEnabled": provider.kind == "openai_compatible",
    }


def _option_payload(value: str, text: str) -> dict[str, str]:
    return {
        "value": value,
        "text": text,
    }


class _ControlPanelBridge(QObject):
    dataChanged = pyqtSignal()
    currentSectionChanged = pyqtSignal()
    closeRequested = pyqtSignal()
    configSaved = pyqtSignal(object)

    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self._config_manager = config_manager
        self._config = config_manager.load()
        self._current_section = "models"
        self._capture_hotkey = self._config.hotkeys.capture
        self._max_image_megabytes = format_image_limit_megabytes(self._config.max_image_bytes)
        self._error_message = ""
        self._status_message = ""

    @pyqtProperty("QVariantList", constant=True)
    def sections(self):  # noqa: ANN201
        return list(_SECTION_ITEMS)

    @pyqtProperty(str, notify=currentSectionChanged)
    def currentSection(self) -> str:
        return self._current_section

    @pyqtProperty("QVariantList", notify=dataChanged)
    def providers(self):  # noqa: ANN201
        return [_provider_payload(provider) for provider in self._config.providers]

    @pyqtProperty("QVariantList", notify=dataChanged)
    def taskBindings(self):  # noqa: ANN201
        payload = []
        for task_name, label in _TASK_LABELS.items():
            binding = getattr(self._config.task_model_bindings, task_name)
            payload.append(
                {
                    "id": task_name,
                    "label": label,
                    "providerId": binding.provider_id,
                    "modelId": binding.model_id,
                    "providerOptions": [
                        _option_payload(provider.id, provider.name)
                        for provider in self._config.providers
                    ],
                    "modelOptions": self._build_model_options(task_name, binding.provider_id),
                }
            )
        return payload

    @pyqtProperty(str, notify=dataChanged)
    def captureHotkey(self) -> str:
        return self._capture_hotkey

    @pyqtProperty(str, notify=dataChanged)
    def maxImageMegabytes(self) -> str:
        return self._max_image_megabytes

    @pyqtProperty(str, notify=dataChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @pyqtProperty(bool, notify=dataChanged)
    def hasError(self) -> bool:
        return bool(self._error_message)

    @pyqtProperty(str, notify=dataChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @pyqtProperty(bool, notify=dataChanged)
    def hasStatus(self) -> bool:
        return bool(self._status_message)

    @pyqtProperty(str, constant=True)
    def configPath(self) -> str:
        return str(config_file())

    @pyqtProperty(str, constant=True)
    def promptsPath(self) -> str:
        return str(prompts_file())

    @pyqtProperty(str, constant=True)
    def todosPath(self) -> str:
        return str(todos_file())

    @pyqtProperty("QVariantList", constant=True)
    def locations(self):  # noqa: ANN201
        return [
            {
                "id": "data_dir",
                "title": "本地数据目录",
                "description": str(app_data_dir()),
            },
            {
                "id": "feedback_dir",
                "title": "反馈目录",
                "description": str(feedback_dir()),
            },
            {
                "id": "prompt_history_dir",
                "title": "Prompt 历史目录",
                "description": str(prompt_history_dir()),
            },
            {
                "id": "error_log_dir",
                "title": "错误日志目录",
                "description": str(error_log_file().parent),
            },
        ]

    def _build_model_options(self, task_name: str, provider_id: str) -> list[dict[str, str]]:
        provider = self._find_provider(provider_id)
        if provider is None:
            return []
        capability = _required_capability(task_name)
        options = [
            _option_payload(
                model.id,
                f"{model.name} ({', '.join(model.capabilities)})",
            )
            for model in provider.models
            if capability in model.capabilities
        ]
        if options:
            return options
        return [
            _option_payload(
                model.id,
                f"{model.name} ({', '.join(model.capabilities)})",
            )
            for model in provider.models
        ]

    def _find_provider(self, provider_id: str) -> ProviderConfig | None:
        return next((provider for provider in self._config.providers if provider.id == provider_id), None)

    def _clear_messages(self) -> None:
        self._error_message = ""
        self._status_message = ""

    def _emit_data_changed(self) -> None:
        self.dataChanged.emit()

    @pyqtSlot(str)
    def setCurrentSection(self, section_id: str) -> None:
        section = str(section_id or "").strip()
        if not section or section == self._current_section:
            return
        if not any(item["id"] == section for item in _SECTION_ITEMS):
            return
        self._current_section = section
        self.currentSectionChanged.emit()

    @pyqtSlot()
    def reloadConfig(self) -> None:
        self._config = self._config_manager.load()
        self._capture_hotkey = self._config.hotkeys.capture
        self._max_image_megabytes = format_image_limit_megabytes(self._config.max_image_bytes)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str, str)
    def updateProviderField(self, provider_id: str, field_name: str, value: str) -> None:
        provider = self._find_provider(str(provider_id or "").strip())
        if provider is None:
            return
        if field_name == "api_key":
            provider.api_key = str(value or "").strip()
        elif field_name == "base_url":
            provider.base_url = str(value or "").strip()
        elif field_name == "timeout_seconds":
            provider.timeout_seconds = str(value or "").strip() or "0"  # type: ignore[assignment]
        else:
            return
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str)
    def updateTaskBindingProvider(self, task_name: str, provider_id: str) -> None:
        provider = self._find_provider(str(provider_id or "").strip())
        if provider is None:
            return
        binding = getattr(self._config.task_model_bindings, task_name, None)
        if not isinstance(binding, TaskModelBinding):
            return
        binding.provider_id = provider.id
        model_options = self._build_model_options(task_name, provider.id)
        binding.model_id = model_options[0]["value"] if model_options else ""
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, str)
    def updateTaskBindingModel(self, task_name: str, model_id: str) -> None:
        binding = getattr(self._config.task_model_bindings, task_name, None)
        if not isinstance(binding, TaskModelBinding):
            return
        binding.model_id = str(model_id or "").strip()
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def updateCaptureHotkey(self, value: str) -> None:
        self._capture_hotkey = str(value or "")
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def updateMaxImageMegabytes(self, value: str) -> None:
        self._max_image_megabytes = str(value or "")
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def openLocation(self, location_id: str) -> None:
        mapping = {
            "data_dir": app_data_dir(),
            "feedback_dir": feedback_dir(),
            "prompt_history_dir": prompt_history_dir(),
            "error_log_dir": error_log_file().parent,
        }
        target = mapping.get(str(location_id or "").strip())
        if target is None:
            return
        target.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    @pyqtSlot()
    def closePanel(self) -> None:
        self.closeRequested.emit()

    @pyqtSlot()
    def saveConfig(self) -> None:
        self._clear_messages()
        try:
            self._coerce_provider_timeouts()
            self._config = persist_control_panel_config(
                self._config_manager,
                self._config,
                capture_hotkey=self._capture_hotkey,
                max_image_megabytes=self._max_image_megabytes,
            )
        except ValueError as exc:
            self._error_message = str(exc)
            self._emit_data_changed()
            return

        self._capture_hotkey = self._config.hotkeys.capture
        self._max_image_megabytes = format_image_limit_megabytes(self._config.max_image_bytes)
        self._status_message = "配置已保存，新的截图热键已立即生效。"
        self._emit_data_changed()
        self.configSaved.emit(self._config)

    def _coerce_provider_timeouts(self) -> None:
        for provider in self._config.providers:
            try:
                provider.timeout_seconds = int(provider.timeout_seconds)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{provider.name} 的超时时间必须是正整数") from exc
            if provider.timeout_seconds <= 0:
                raise ValueError(f"{provider.name} 的超时时间必须大于 0")


class ControlPanelWindow(QWidget):
    config_saved = pyqtSignal(object)

    def __init__(self, config_manager: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self._positioned = False
        self._bridge = _ControlPanelBridge(config_manager)

        self.setObjectName("controlPanelWindow")
        self.setWindowTitle("AICA 控制面板")
        self.resize(1040, 760)
        self.setMinimumSize(920, 680)

        self._setup_ui()

        self._bridge.closeRequested.connect(self.hide)
        self._bridge.configSaved.connect(lambda payload: self.config_saved.emit(payload))

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._view = QQuickWidget(self)
        self._view.setClearColor(QColor(0, 0, 0, 0))
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._view.rootContext().setContextProperty("controlPanelBridge", self._bridge)
        self._view.setSource(QUrl.fromLocalFile(str(qml_dir() / "ControlPanel.qml")))
        self._ensure_qml_loaded()
        layout.addWidget(self._view)

    def _ensure_qml_loaded(self) -> None:
        if self._view.status() != QQuickWidget.Status.Error:
            return
        errors = "\n".join(error.toString() for error in self._view.errors())
        raise RuntimeError(f"Failed to load ControlPanel.qml:\n{errors}")

    def show_panel(self, section_id: str = "models") -> None:
        self._bridge.reloadConfig()
        self._bridge.setCurrentSection(section_id)
        self.show()
        self.raise_()
        self.activateWindow()
        if not self._positioned:
            self._fit_within_screen()
            self._positioned = True

    def closeEvent(self, event) -> None:  # noqa: N802
        event.ignore()
        self.hide()

    def _fit_within_screen(self) -> None:
        screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        margin = 20
        self.resize(
            min(self.width(), available.width() - margin * 2),
            min(self.height(), available.height() - margin * 2),
        )
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

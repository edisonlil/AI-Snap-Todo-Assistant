"""QML-backed application control panel."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication, QFileDialog, QWidget, QVBoxLayout

from aica.analysis_metrics import AnalysisMetricsStore, ModelLatencySummary
from aica.config import ConfigManager, ProviderConfig, ProviderModelConfig, TaskModelBinding
from aica.control_panel_state import (
    build_script_integration,
    format_image_limit_megabytes,
    list_script_integrations,
    load_integration_config,
    normalize_directory_path,
    persist_storage_paths,
    persist_control_panel_config,
    replace_script_integrations,
    save_integration_config,
    script_integration_display_path,
    update_script_integration_path,
)
from aica.paths import (
    aica_database_file,
    app_data_dir,
    config_file,
    error_log_file,
    feedback_dir,
    integrations_file,
    log_dir,
    prompt_history_dir,
    prompts_file,
    qml_dir,
    storage_config_file,
)


_TASK_LABELS = {
    "analysis": "截图分析",
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
    {
        "id": "integrations",
        "title": "脚本集成",
        "description": "导入外部脚本，并控制启用或停用同步脚本。",
    },
]


def _required_capability(task_name: str) -> str:
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


def _normalize_model_text(value: str) -> str:
    return str(value or "").strip()


def _normalize_capabilities(value: str) -> list[str]:
    items = [item.strip() for item in str(value or "").split(",")]
    capabilities: list[str] = []
    for item in items:
        if item and item not in capabilities:
            capabilities.append(item)
    return capabilities


def _append_metric_suffix(label: str, summary: ModelLatencySummary | None) -> str:
    if summary is None or summary.is_empty:
        return label
    return f"{label} · {summary.to_display_text()}"


def _build_speed_hint(model_name: str, summary: ModelLatencySummary | None) -> str:
    if summary is None or summary.avg_latency_ms <= 10000:
        return ""
    lowered = str(model_name or "").lower()
    if "thinking" not in lowered and "reasoning" not in lowered:
        return ""
    return "该模型近期平均耗时偏长，通常更适合重质量场景；若更看重速度，可优先比较 Instruct/Flash 类模型。"


class _ControlPanelBridge(QObject):
    dataChanged = pyqtSignal()
    currentSectionChanged = pyqtSignal()
    closeRequested = pyqtSignal()
    minimizeRequested = pyqtSignal()
    dragRequested = pyqtSignal()
    configSaved = pyqtSignal(object)

    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self._config_manager = config_manager
        self._config = config_manager.load()
        self._analysis_metrics = AnalysisMetricsStore()
        self._integrations_path = integrations_file()
        self._integration_payload = load_integration_config(self._integrations_path)
        self._script_integrations = list_script_integrations(self._integration_payload)
        self._current_section = "models"
        self._capture_hotkey = self._config.hotkeys.capture
        self._max_image_megabytes = format_image_limit_megabytes(self._config.max_image_bytes)
        self._data_dir = str(app_data_dir())
        self._log_dir = str(log_dir())
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
            summary = self._analysis_metrics.get_summary(task_name, binding.provider_id, binding.model_id)
            provider = self._find_provider(binding.provider_id)
            model_name = ""
            if provider is not None:
                model = next((item for item in provider.models if item.id == binding.model_id), None)
                model_name = model.name if model is not None else ""
            payload.append(
                {
                    "id": task_name,
                    "label": label,
                    "providerId": binding.provider_id,
                    "modelId": binding.model_id,
                    "performanceSummary": summary.to_display_text() if summary is not None else "暂无耗时样本",
                    "speedHint": _build_speed_hint(model_name, summary),
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

    @pyqtProperty(str, notify=dataChanged)
    def dataDir(self) -> str:
        return self._data_dir

    @pyqtProperty(str, notify=dataChanged)
    def logDir(self) -> str:
        return self._log_dir

    @pyqtProperty(str, notify=dataChanged)
    def storageConfigPath(self) -> str:
        return str(storage_config_file())

    @pyqtProperty(str, notify=dataChanged)
    def configPath(self) -> str:
        return str(config_file())

    @pyqtProperty(str, notify=dataChanged)
    def promptsPath(self) -> str:
        return str(prompts_file())

    @pyqtProperty(str, notify=dataChanged)
    def todosPath(self) -> str:
        return str(aica_database_file())

    @pyqtProperty(str, notify=dataChanged)
    def integrationsPath(self) -> str:
        return str(self._integrations_path)

    @pyqtProperty("QVariantList", notify=dataChanged)
    def integrationScripts(self):  # noqa: ANN201
        payload = []
        for integration in self._script_integrations:
            script_path = script_integration_display_path(integration)
            payload.append(
                {
                    "id": str(integration.get("id") or "").strip(),
                    "name": str(integration.get("name") or integration.get("id") or "未命名脚本").strip(),
                    "enabled": bool(integration.get("enabled", True)),
                    "scriptPath": script_path,
                    "exists": bool(script_path) and Path(script_path).exists(),
                }
            )
        return payload

    @pyqtProperty("QVariantList", notify=dataChanged)
    def locations(self):  # noqa: ANN201
        return [
            {
                "id": "data_dir",
                "title": "本地数据目录",
                "description": self._data_dir,
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
                "description": self._log_dir,
            },
            {
                "id": "integrations_dir",
                "title": "脚本集成配置目录",
                "description": str(self._integrations_path.parent),
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
                _append_metric_suffix(
                    f"{model.name} ({', '.join(model.capabilities)})",
                    self._analysis_metrics.get_summary(task_name, provider.id, model.id),
                ),
            )
            for model in provider.models
            if capability in model.capabilities
        ]
        if options:
            return options
        return [
            _option_payload(
                model.id,
                _append_metric_suffix(
                    f"{model.name} ({', '.join(model.capabilities)})",
                    self._analysis_metrics.get_summary(task_name, provider.id, model.id),
                ),
            )
            for model in provider.models
        ]

    def _find_provider(self, provider_id: str) -> ProviderConfig | None:
        return next((provider for provider in self._config.providers if provider.id == provider_id), None)

    def _find_provider_model(self, provider: ProviderConfig, model_text: str) -> ProviderModelConfig | None:
        normalized = _normalize_model_text(model_text)
        if not normalized:
            return None
        lowered = normalized.casefold()
        return next(
            (
                model
                for model in provider.models
                if model.id.casefold() == lowered or model.name.casefold() == lowered
            ),
            None,
        )

    def _ensure_provider_model(
        self,
        task_name: str,
        provider: ProviderConfig,
        model_text: str,
        capability_text: str = "",
    ) -> ProviderModelConfig | None:
        normalized = _normalize_model_text(model_text)
        if not normalized:
            return None
        existing = self._find_provider_model(provider, normalized)
        if existing is not None:
            return existing
        capability = _required_capability(task_name)
        capabilities = _normalize_capabilities(capability_text)
        if not capabilities:
            capabilities = [capability, "text_chat"]
        elif capability in capabilities and "text_chat" not in capabilities:
            capabilities.append("text_chat")
        model = ProviderModelConfig(
            id=normalized,
            name=normalized,
            capabilities=capabilities,
        )
        provider.models.append(model)
        return model

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
        self._config_manager = ConfigManager()
        self._config = self._config_manager.load()
        self._integrations_path = integrations_file()
        self._integration_payload = load_integration_config(self._integrations_path)
        self._script_integrations = list_script_integrations(self._integration_payload)
        self._capture_hotkey = self._config.hotkeys.capture
        self._max_image_megabytes = format_image_limit_megabytes(self._config.max_image_bytes)
        self._data_dir = str(app_data_dir())
        self._log_dir = str(log_dir())
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

    @pyqtSlot(str, str, str)
    def addOrSelectTaskBindingModel(self, task_name: str, model_text: str, capability_text: str) -> None:
        binding = getattr(self._config.task_model_bindings, task_name, None)
        if not isinstance(binding, TaskModelBinding):
            return
        provider = self._find_provider(binding.provider_id)
        if provider is None:
            return
        required_capability = _required_capability(task_name)
        model = self._ensure_provider_model(task_name, provider, model_text, capability_text)
        if model is None:
            return
        self._clear_messages()
        if required_capability in model.capabilities:
            binding.model_id = model.id
        else:
            self._status_message = (
                f"已添加模型 {model.name}，但当前任务需要 {required_capability} 能力，暂未自动绑定。"
            )
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
    def updateDataDir(self, value: str) -> None:
        self._data_dir = str(value or "")
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def updateLogDir(self, value: str) -> None:
        self._log_dir = str(value or "")
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def chooseStorageDir(self, target_name: str) -> None:
        normalized_target = str(target_name or "").strip()
        current_value = self._data_dir if normalized_target == "data_dir" else self._log_dir
        start_dir = current_value.strip() or str(app_data_dir())
        selected_path = QFileDialog.getExistingDirectory(
            None,
            "选择目录",
            start_dir,
        )
        if not selected_path:
            return
        if normalized_target == "data_dir":
            self._data_dir = selected_path
        elif normalized_target == "log_dir":
            self._log_dir = selected_path
        else:
            return
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def openLocation(self, location_id: str) -> None:
        mapping = {
            "data_dir": app_data_dir(),
            "feedback_dir": feedback_dir(),
            "prompt_history_dir": prompt_history_dir(),
            "error_log_dir": error_log_file().parent,
            "integrations_dir": self._integrations_path.parent,
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
    def minimizePanel(self) -> None:
        self.minimizeRequested.emit()

    @pyqtSlot()
    def startWindowDrag(self) -> None:
        self.dragRequested.emit()

    @pyqtSlot()
    def saveCurrentSection(self) -> None:
        if self._current_section == "integrations":
            self.saveIntegrations()
            return
        if self._current_section == "storage":
            self.saveStoragePaths()
            return
        self.saveConfig()

    @pyqtSlot()
    def saveStoragePaths(self) -> None:
        self._clear_messages()
        try:
            previous_data_dir = str(app_data_dir())
            previous_log_dir = str(log_dir())
            result = persist_storage_paths(
                data_dir=normalize_directory_path(self._data_dir),
                log_dir=normalize_directory_path(self._log_dir),
                previous_data_dir=previous_data_dir,
                previous_log_dir=previous_log_dir,
            )
        except ValueError as exc:
            self._error_message = str(exc)
            self._emit_data_changed()
            return

        self._data_dir = result["data_dir"]
        self._log_dir = result["log_dir"]
        self.reloadConfig()
        self._status_message = "目录设置已保存，新日志会写入新位置；数据目录切换建议重启应用后完全生效。"
        self._emit_data_changed()

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

    @pyqtSlot()
    def saveIntegrations(self) -> None:
        self._clear_messages()
        self._integration_payload = replace_script_integrations(
            self._integration_payload,
            self._script_integrations,
        )
        save_integration_config(self._integrations_path, self._integration_payload)
        self._status_message = "脚本集成配置已保存。"
        self._emit_data_changed()

    @pyqtSlot()
    def addIntegrationScript(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            None,
            "选择外部脚本",
            str(app_data_dir()),
            "脚本文件 (*.py *.pyw *.ps1 *.bat *.cmd *.exe);;所有文件 (*.*)",
        )
        if not selected_path:
            return
        existing_ids = {
            str(item.get("id") or "").strip()
            for item in self._script_integrations
            if str(item.get("id") or "").strip()
        }
        self._script_integrations.append(build_script_integration(selected_path, existing_ids))
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def chooseIntegrationScript(self, integration_id: str) -> None:
        target_id = str(integration_id or "").strip()
        integration = self._find_script_integration(target_id)
        if integration is None:
            return
        current_path = script_integration_display_path(integration)
        start_dir = str(Path(current_path).parent) if current_path else str(app_data_dir())
        selected_path, _ = QFileDialog.getOpenFileName(
            None,
            "选择外部脚本",
            start_dir,
            "脚本文件 (*.py *.pyw *.ps1 *.bat *.cmd *.exe);;所有文件 (*.*)",
        )
        if not selected_path:
            return
        self._replace_script_integration(
            target_id,
            update_script_integration_path(integration, selected_path),
        )
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str, bool)
    def setIntegrationEnabled(self, integration_id: str, enabled: bool) -> None:
        integration = self._find_script_integration(str(integration_id or "").strip())
        if integration is None:
            return
        integration["enabled"] = bool(enabled)
        self._clear_messages()
        self._emit_data_changed()

    @pyqtSlot(str)
    def removeIntegrationScript(self, integration_id: str) -> None:
        target_id = str(integration_id or "").strip()
        self._script_integrations = [
            item
            for item in self._script_integrations
            if str(item.get("id") or "").strip() != target_id
        ]
        self._clear_messages()
        self._emit_data_changed()

    def _coerce_provider_timeouts(self) -> None:
        for provider in self._config.providers:
            try:
                provider.timeout_seconds = int(provider.timeout_seconds)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{provider.name} 的超时时间必须是正整数") from exc
            if provider.timeout_seconds <= 0:
                raise ValueError(f"{provider.name} 的超时时间必须大于 0")

    def _find_script_integration(self, integration_id: str) -> dict[str, object] | None:
        return next(
            (
                item
                for item in self._script_integrations
                if str(item.get("id") or "").strip() == integration_id
            ),
            None,
        )

    def _replace_script_integration(self, integration_id: str, updated_item: dict[str, object]) -> None:
        for index, item in enumerate(self._script_integrations):
            if str(item.get("id") or "").strip() == integration_id:
                self._script_integrations[index] = updated_item
                return


class ControlPanelWindow(QWidget):
    config_saved = pyqtSignal(object)

    def __init__(self, config_manager: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self._positioned = False
        self._bridge = _ControlPanelBridge(config_manager)

        self.setObjectName("controlPanelWindow")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("AICA 控制面板")
        self.resize(1040, 760)
        self.setMinimumSize(920, 680)

        self._setup_ui()

        self._bridge.closeRequested.connect(self.hide)
        self._bridge.minimizeRequested.connect(self.showMinimized)
        self._bridge.dragRequested.connect(self._start_system_move)
        self._bridge.configSaved.connect(lambda payload: self.config_saved.emit(payload))

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
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
        if self.isMinimized():
            self.showNormal()
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

    def _start_system_move(self) -> None:
        window_handle = self.windowHandle()
        if window_handle is None:
            self.activateWindow()
            return
        try:
            window_handle.startSystemMove()
        except AttributeError:
            self.activateWindow()

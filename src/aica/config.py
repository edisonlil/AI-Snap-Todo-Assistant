"""Application configuration persistence."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

from aica.paths import config_file as default_config_file
from aica.runtime import (
    DEFAULT_WINDOWS_CAPTURE_HOTKEY,
    default_capture_hotkey,
)


DEFAULT_CAPTURE_HOTKEY = DEFAULT_WINDOWS_CAPTURE_HOTKEY
_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
_DASHSCOPE_MODEL_ALIASES = {
    "qwen-vl-max-latest": "qwen-vl-max",
    "qwen-plus-latest": "qwen-plus",
}


@dataclass
class ProviderModelConfig:
    id: str
    name: str
    capabilities: list[str]

    @classmethod
    def from_dict(cls, data: object) -> "ProviderModelConfig | None":
        if not isinstance(data, dict):
            return None
        model_id = str(data.get("id", "")).strip()
        name = str(data.get("name", "")).strip()
        raw_capabilities = data.get("capabilities", [])
        capabilities = [str(item).strip() for item in raw_capabilities if str(item).strip()] if isinstance(raw_capabilities, list) else []
        if not model_id or not name:
            return None
        return cls(id=model_id, name=name, capabilities=capabilities)


@dataclass
class ProviderConfig:
    id: str
    kind: str
    name: str
    api_key: str = ""
    base_url: str = ""
    timeout_seconds: int = 30
    models: list[ProviderModelConfig] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: object) -> "ProviderConfig | None":
        if not isinstance(data, dict):
            return None
        provider_id = str(data.get("id", "")).strip()
        kind = str(data.get("kind", "")).strip()
        name = str(data.get("name", "")).strip()
        if not provider_id or not kind or not name:
            return None
        raw_models = data.get("models", [])
        models = []
        if isinstance(raw_models, list):
            for item in raw_models:
                model = ProviderModelConfig.from_dict(item)
                if model is not None:
                    models.append(model)
        return cls(
            id=provider_id,
            kind=kind,
            name=name,
            api_key=str(data.get("api_key", "")).strip(),
            base_url=str(data.get("base_url", "")).strip(),
            timeout_seconds=_coerce_positive_int(data.get("timeout_seconds"), 30),
            models=models,
        )


@dataclass
class TaskModelBinding:
    provider_id: str = ""
    model_id: str = ""

    @classmethod
    def from_dict(cls, data: object) -> "TaskModelBinding":
        if not isinstance(data, dict):
            return cls()
        return cls(
            provider_id=str(data.get("provider_id", "")).strip(),
            model_id=str(data.get("model_id", "")).strip(),
        )


@dataclass
class TaskModelBindings:
    analysis: TaskModelBinding = field(default_factory=TaskModelBinding)
    log_analysis: TaskModelBinding = field(default_factory=TaskModelBinding)
    plan_export: TaskModelBinding = field(default_factory=TaskModelBinding)
    context_summary: TaskModelBinding = field(default_factory=TaskModelBinding)

    @classmethod
    def from_dict(cls, data: object) -> "TaskModelBindings":
        if not isinstance(data, dict):
            return default_task_model_bindings()
        return cls(
            analysis=TaskModelBinding.from_dict(data.get("analysis")),
            log_analysis=TaskModelBinding.from_dict(data.get("log_analysis")),
            plan_export=TaskModelBinding.from_dict(data.get("plan_export")),
            context_summary=TaskModelBinding.from_dict(data.get("context_summary")),
        )


@dataclass
class HotkeyConfig:
    capture: str = field(default_factory=default_capture_hotkey)

    @classmethod
    def from_dict(cls, data: object) -> "HotkeyConfig":
        if not isinstance(data, dict):
            return cls()
        capture = str(data.get("capture", default_capture_hotkey())).strip() or default_capture_hotkey()
        return cls(capture=capture)


@dataclass
class ServerConfig:
    enabled: bool = False
    base_url: str = ""
    api_key: str = ""
    timeout_seconds: int = 30

    @classmethod
    def from_dict(cls, data: object) -> "ServerConfig":
        if not isinstance(data, dict):
            return cls()
        return cls(
            enabled=_coerce_bool(data.get("enabled"), False),
            base_url=str(data.get("base_url", "")).strip(),
            api_key=str(data.get("api_key", "")).strip(),
            timeout_seconds=_coerce_positive_int(data.get("timeout_seconds"), 30),
        )


@dataclass
class AppConfig:
    default_provider_id: str = "siliconflow"
    providers: list[ProviderConfig] = field(default_factory=list)
    task_model_bindings: TaskModelBindings = field(default_factory=lambda: default_task_model_bindings("siliconflow"))
    hotkeys: HotkeyConfig = field(default_factory=HotkeyConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    max_image_bytes: int = 4 * 1024 * 1024


def _binding(provider_id: str, model_id: str) -> TaskModelBinding:
    return TaskModelBinding(provider_id=provider_id, model_id=model_id)


def default_provider_configs() -> list[ProviderConfig]:
    return [
        ProviderConfig(
            id="siliconflow",
            kind="openai_compatible",
            name="SiliconFlow",
            base_url="https://api.siliconflow.cn/v1/chat/completions",
            timeout_seconds=30,
            models=[
                ProviderModelConfig(
                    id="qwen25-vl-72b",
                    name="Qwen/Qwen2.5-VL-72B-Instruct",
                    capabilities=["vision_chat", "text_chat"],
                ),
                ProviderModelConfig(
                    id="qwen3-8b",
                    name="Qwen/Qwen3-8B",
                    capabilities=["text_chat"],
                ),
            ],
        ),
        ProviderConfig(
            id="dashscope",
            kind="openai_compatible",
            name="阿里云百炼",
            base_url=_DASHSCOPE_BASE_URL,
            timeout_seconds=30,
            models=[
                ProviderModelConfig(
                    id="qwen-vl-max",
                    name="qwen-vl-max",
                    capabilities=["vision_chat", "text_chat"],
                ),
                ProviderModelConfig(
                    id="qwen-plus",
                    name="qwen-plus",
                    capabilities=["text_chat"],
                ),
            ],
        ),
        ProviderConfig(
            id="minmax",
            kind="openai_compatible",
            name="MiniMax",
            base_url="https://api.minimax.io/v1/chat/completions",
            timeout_seconds=30,
            models=[
                ProviderModelConfig(
                    id="minimax-m2-5",
                    name="MiniMax-M2.5",
                    capabilities=["text_chat"],
                ),
                ProviderModelConfig(
                    id="minimax-m2-5-highspeed",
                    name="MiniMax-M2.5-highspeed",
                    capabilities=["text_chat"],
                ),
            ],
        ),
        ProviderConfig(
            id="gemini",
            kind="gemini",
            name="Google Gemini",
            timeout_seconds=30,
            models=[
                ProviderModelConfig(
                    id="gemini-2.5-flash",
                    name="gemini-2.5-flash",
                    capabilities=["vision_chat", "text_chat"],
                ),
            ],
        ),
    ]


def default_task_model_bindings(default_provider_id: str = "siliconflow") -> TaskModelBindings:
    if default_provider_id == "gemini":
        return TaskModelBindings(
            analysis=_binding("gemini", "gemini-2.5-flash"),
            log_analysis=_binding("gemini", "gemini-2.5-flash"),
            plan_export=_binding("gemini", "gemini-2.5-flash"),
            context_summary=_binding("gemini", "gemini-2.5-flash"),
        )
    if default_provider_id == "dashscope":
        return TaskModelBindings(
            analysis=_binding("dashscope", "qwen-vl-max"),
            log_analysis=_binding("dashscope", "qwen-vl-max"),
            plan_export=_binding("dashscope", "qwen-vl-max"),
            context_summary=_binding("dashscope", "qwen-plus"),
        )
    if default_provider_id == "minmax":
        return TaskModelBindings(
            analysis=_binding("siliconflow", "qwen25-vl-72b"),
            log_analysis=_binding("siliconflow", "qwen25-vl-72b"),
            plan_export=_binding("siliconflow", "qwen25-vl-72b"),
            context_summary=_binding("minmax", "minimax-m2-5"),
        )
    return TaskModelBindings(
        analysis=_binding("siliconflow", "qwen25-vl-72b"),
        log_analysis=_binding("siliconflow", "qwen25-vl-72b"),
        plan_export=_binding("siliconflow", "qwen25-vl-72b"),
        context_summary=_binding("siliconflow", "qwen3-8b"),
    )


def build_default_config() -> AppConfig:
    return AppConfig(
        default_provider_id="siliconflow",
        providers=default_provider_configs(),
        task_model_bindings=default_task_model_bindings("siliconflow"),
        hotkeys=HotkeyConfig(),
        server=ServerConfig(),
        max_image_bytes=4 * 1024 * 1024,
    )


def _coerce_positive_int(value: object, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _coerce_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _normalize_provider_configs(providers: list[ProviderConfig], default_provider_id: str) -> list[ProviderConfig]:
    defaults_by_id = {provider.id: provider for provider in default_provider_configs()}
    normalized: list[ProviderConfig] = []
    seen_ids: set[str] = set()

    for provider in providers:
        if not provider.id or provider.id in seen_ids:
            continue
        seen_ids.add(provider.id)
        default_provider = defaults_by_id.get(provider.id)
        if provider.kind == "openai_compatible" and not provider.base_url and default_provider is not None:
            provider.base_url = default_provider.base_url
        if not provider.models and default_provider is not None:
            provider.models = default_provider.models
        if provider.timeout_seconds <= 0:
            provider.timeout_seconds = default_provider.timeout_seconds if default_provider is not None else 30
        if provider.id == "dashscope":
            _normalize_dashscope_provider(provider)
        normalized.append(provider)

    if default_provider_id not in seen_ids:
        fallback = defaults_by_id.get(default_provider_id)
        if fallback is not None:
            normalized.append(fallback)
            seen_ids.add(default_provider_id)

    for provider_id, provider in defaults_by_id.items():
        if provider_id not in seen_ids:
            normalized.append(provider)

    return normalized


def _normalize_dashscope_provider(provider: ProviderConfig) -> None:
    if provider.base_url.rstrip("/").endswith("/compatible-mode/v1"):
        provider.base_url = _DASHSCOPE_BASE_URL
    elif not provider.base_url:
        provider.base_url = _DASHSCOPE_BASE_URL

    for model in provider.models:
        canonical_id = _DASHSCOPE_MODEL_ALIASES.get(model.id, model.id)
        canonical_name = _DASHSCOPE_MODEL_ALIASES.get(model.name, model.name)
        model.id = canonical_id
        model.name = canonical_name


def _normalize_task_bindings(bindings: TaskModelBindings, providers: list[ProviderConfig], default_provider_id: str) -> TaskModelBindings:
    provider_map = {provider.id: provider for provider in providers}
    defaults = default_task_model_bindings(default_provider_id)

    def normalize(binding: TaskModelBinding, fallback: TaskModelBinding, capability: str) -> TaskModelBinding:
        provider = provider_map.get(binding.provider_id)
        model = None
        if provider is not None:
            model = next((item for item in provider.models if item.id == binding.model_id), None)
        if provider is None or model is None or capability not in model.capabilities:
            return fallback
        return binding

    return TaskModelBindings(
        analysis=normalize(bindings.analysis, defaults.analysis, "vision_chat"),
        log_analysis=normalize(
            bindings.log_analysis,
            defaults.log_analysis if bindings.log_analysis.provider_id and bindings.log_analysis.model_id else defaults.analysis,
            "vision_chat",
        ),
        plan_export=normalize(bindings.plan_export, defaults.plan_export, "text_chat"),
        context_summary=normalize(
            bindings.context_summary,
            defaults.context_summary if bindings.context_summary.provider_id and bindings.context_summary.model_id else defaults.context_summary,
            "text_chat",
        ),
    )


def _app_config_from_dict(data: object) -> AppConfig:
    defaults = build_default_config()
    if not isinstance(data, dict):
        return defaults

    raw_providers = data.get("providers", [])
    providers = []
    if isinstance(raw_providers, list):
        for item in raw_providers:
            provider = ProviderConfig.from_dict(item)
            if provider is not None:
                providers.append(provider)

    default_provider_id = str(data.get("default_provider_id", defaults.default_provider_id)).strip() or defaults.default_provider_id
    providers = _normalize_provider_configs(providers, default_provider_id)
    bindings = _normalize_task_bindings(
        TaskModelBindings.from_dict(data.get("task_model_bindings")),
        providers,
        default_provider_id,
    )
    return AppConfig(
        default_provider_id=default_provider_id,
        providers=providers,
        task_model_bindings=bindings,
        hotkeys=HotkeyConfig.from_dict(data.get("hotkeys")),
        server=ServerConfig.from_dict(data.get("server")),
        max_image_bytes=_coerce_positive_int(data.get("max_image_bytes"), defaults.max_image_bytes),
    )


def _migrate_legacy_config(data: dict[str, object]) -> AppConfig:
    defaults = build_default_config()
    api_key = str(data.get("api_key", "")).strip()
    model_name = str(data.get("model", "")).strip() or defaults.providers[0].models[0].name
    plan_export_model_name = str(data.get("plan_export_model", "")).strip() or model_name
    api_base_url = str(data.get("api_base_url", "")).strip() or defaults.providers[0].base_url
    timeout_seconds = _coerce_positive_int(data.get("timeout_seconds"), 30)

    migrated = build_default_config()
    migrated.providers[0].api_key = api_key
    migrated.providers[0].base_url = api_base_url
    migrated.providers[0].timeout_seconds = timeout_seconds
    migrated.providers[0].models = [
        ProviderModelConfig(id="analysis-model", name=model_name, capabilities=["vision_chat", "text_chat"]),
        ProviderModelConfig(id="plan-export-model", name=plan_export_model_name, capabilities=["vision_chat", "text_chat"]),
    ]
    migrated.task_model_bindings = TaskModelBindings(
        analysis=TaskModelBinding(provider_id="siliconflow", model_id="analysis-model"),
        log_analysis=TaskModelBinding(provider_id="siliconflow", model_id="analysis-model"),
        plan_export=TaskModelBinding(provider_id="siliconflow", model_id="plan-export-model"),
        context_summary=TaskModelBinding(provider_id="siliconflow", model_id="analysis-model"),
    )
    migrated.hotkeys = HotkeyConfig()
    migrated.server = ServerConfig()
    migrated.max_image_bytes = _coerce_positive_int(data.get("max_image_bytes"), migrated.max_image_bytes)
    return migrated


def _needs_legacy_migration(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    return "providers" not in data and any(
        key in data
        for key in ("api_key", "model", "title_generation_model", "plan_export_model", "api_base_url")
    )


class ConfigManager:
    def __init__(self, config_path: str | None = None):
        self._path = config_path or str(default_config_file())

    @property
    def path(self) -> str:
        return self._path

    def load(self) -> AppConfig:
        if not os.path.exists(self._path):
            return build_default_config()

        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return build_default_config()

        if _needs_legacy_migration(data):
            migrated = _migrate_legacy_config(data)
            self.save(migrated)
            return migrated

        return _app_config_from_dict(data)

    def save(self, config: AppConfig) -> None:
        normalized = _app_config_from_dict(asdict(config))
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(asdict(normalized), handle, ensure_ascii=False, indent=2)

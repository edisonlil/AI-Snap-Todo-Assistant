"""Pure helpers for control panel config persistence."""
from __future__ import annotations

from copy import deepcopy

from aica.config import AppConfig
from aica.hotkey import normalize_hotkey
from aica.llm.service import LLMService, ModelResolutionError


MEGABYTE = 1024 * 1024
TASK_NAMES = (
    "analysis",
    "title_generation",
    "plan_export",
    "prompt_optimization",
)


def format_image_limit_megabytes(image_bytes: int) -> str:
    value = max(1, int(image_bytes)) / MEGABYTE
    formatted = f"{value:.2f}".rstrip("0").rstrip(".")
    return formatted or "1"


def parse_image_limit_megabytes(value: str) -> int:
    text = str(value or "").strip()
    if not text:
        raise ValueError("图片压缩阈值不能为空")
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError("图片压缩阈值必须是数字") from exc
    if parsed <= 0:
        raise ValueError("图片压缩阈值必须大于 0")
    return max(1, int(round(parsed * MEGABYTE)))


def validate_runtime_bindings(config: AppConfig) -> None:
    service = LLMService(config)
    try:
        for task_name in TASK_NAMES:
            service.resolve_task_model(task_name)
    except ModelResolutionError as exc:
        raise ValueError(str(exc)) from exc


def persist_control_panel_config(
    config_manager,
    config: AppConfig,
    *,
    capture_hotkey: str,
    max_image_megabytes: str,
) -> AppConfig:
    updated = deepcopy(config)
    updated.hotkeys.capture = normalize_hotkey(capture_hotkey)
    updated.max_image_bytes = parse_image_limit_megabytes(max_image_megabytes)
    updated.default_provider_id = updated.task_model_bindings.analysis.provider_id
    validate_runtime_bindings(updated)
    config_manager.save(updated)
    return updated

"""Helpers for local data, log, and bundled resource paths."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from aica.runtime import PLATFORM_MACOS, PLATFORM_WINDOWS, current_platform


_ENV_HOME = "AICA_HOME"
_ENV_DATA_DIR = "AICA_DATA_DIR"
_ENV_LOG_DIR = "AICA_LOG_DIR"
_STORAGE_CONFIG_NAME = "storage.json"


@dataclass(frozen=True)
class StoragePaths:
    data_dir: Path
    log_dir: Path


def legacy_app_data_dir() -> Path:
    return Path.home() / ".aica"


def storage_config_file() -> Path:
    return legacy_app_data_dir() / _STORAGE_CONFIG_NAME


def _normalize_directory(value: object) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    return Path(text).expanduser()


def _load_storage_config_payload() -> dict[str, object]:
    path = storage_config_file()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def storage_paths() -> StoragePaths:
    env_home = _normalize_directory(os.getenv(_ENV_HOME, ""))
    env_data_dir = _normalize_directory(os.getenv(_ENV_DATA_DIR, ""))
    env_log_dir = _normalize_directory(os.getenv(_ENV_LOG_DIR, ""))

    payload = _load_storage_config_payload()
    configured_data_dir = _normalize_directory(payload.get("data_dir"))
    configured_log_dir = _normalize_directory(payload.get("log_dir"))

    base_dir = env_home or legacy_app_data_dir()
    data_dir = env_data_dir or configured_data_dir or base_dir
    log_dir = env_log_dir or configured_log_dir or data_dir
    return StoragePaths(data_dir=data_dir, log_dir=log_dir)


def save_storage_paths(*, data_dir: str = "", log_dir: str = "") -> StoragePaths:
    payload: dict[str, str] = {}
    normalized_data_dir = _normalize_directory(data_dir)
    normalized_log_dir = _normalize_directory(log_dir)
    if normalized_data_dir is not None:
        payload["data_dir"] = str(normalized_data_dir)
    if normalized_log_dir is not None:
        payload["log_dir"] = str(normalized_log_dir)

    config_path = storage_config_file()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return storage_paths()


def app_data_dir() -> Path:
    return storage_paths().data_dir


def log_dir() -> Path:
    return storage_paths().log_dir


def config_file() -> Path:
    return app_data_dir() / "config.json"


def analysis_rules_file() -> Path:
    return app_data_dir() / "analysis_rules.json"


def prompts_file() -> Path:
    return app_data_dir() / "prompts.json"


def aica_database_file() -> Path:
    return app_data_dir() / "aica.db"


def todos_file() -> Path:
    return app_data_dir() / "todos.json"


def todo_bindings_file() -> Path:
    return app_data_dir() / "todo_bindings.json"


def integrations_file() -> Path:
    return app_data_dir() / "integrations.json"


def feedback_dir() -> Path:
    return app_data_dir() / "feedback"


def feedback_images_dir() -> Path:
    return feedback_dir() / "images"


def prompt_history_dir() -> Path:
    return app_data_dir() / "prompt_history"


def prompt_debug_dir() -> Path:
    return app_data_dir() / "prompt_debug"


def error_log_file() -> Path:
    return log_dir() / "error.log"


def analysis_metrics_file() -> Path:
    return app_data_dir() / "analysis_metrics.json"


def todo_attachments_dir() -> Path:
    return app_data_dir() / "todo_attachments"


def knowledge_base_dir() -> Path:
    return app_data_dir() / "knowledge_base"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def runtime_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", project_root()))


def assets_dir() -> Path:
    return runtime_root() / "assets"


def asset_file(name: str) -> Path:
    return assets_dir() / name


def qml_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return runtime_root() / "aica" / "qml"
    return Path(__file__).resolve().with_name("qml")


def icon_file(platform_id: str | None = None, *, dark_mode: bool = False) -> Path:
    platform_id = platform_id or current_platform()
    bundled_assets_dir = assets_dir()
    if platform_id == PLATFORM_MACOS:
        if dark_mode:
            candidate = bundled_assets_dir / "aica_icon_dark.icns"
            if candidate.exists():
                return candidate
        candidate = bundled_assets_dir / "aica_icon.icns"
        if candidate.exists():
            return candidate
    if platform_id == PLATFORM_WINDOWS:
        candidate = bundled_assets_dir / "aica_icon.ico"
        if candidate.exists():
            return candidate
    return bundled_assets_dir / "aica_icon.png"

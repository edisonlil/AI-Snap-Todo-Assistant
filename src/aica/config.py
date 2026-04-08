"""Application configuration persistence."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass


@dataclass
class AppConfig:
    api_key: str = ""
    model: str = "Qwen/Qwen2.5-VL-72B-Instruct"
    title_generation_model: str = "Qwen/Qwen3-8B"
    plan_export_model: str = "Qwen/Qwen2.5-VL-72B-Instruct"
    api_base_url: str = "https://api.siliconflow.cn/v1/chat/completions"
    timeout_seconds: int = 30
    max_image_bytes: int = 4 * 1024 * 1024


_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".aica")
_CONFIG_FILE = os.path.join(_CONFIG_DIR, "config.json")


class ConfigManager:
    def __init__(self, config_path: str = _CONFIG_FILE):
        self._path = config_path

    @property
    def path(self) -> str:
        return self._path

    def load(self) -> AppConfig:
        if not os.path.exists(self._path):
            return AppConfig()

        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            known = {key: value for key, value in data.items() if key in AppConfig.__dataclass_fields__}
            return AppConfig(**known)
        except Exception:
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(asdict(config), handle, ensure_ascii=False, indent=2)

    def get_api_key(self) -> str:
        return self.load().api_key

    def get_model(self) -> str:
        return self.load().model

    def get_title_generation_model(self) -> str:
        return self.load().title_generation_model

    def get_plan_export_model(self) -> str:
        return self.load().plan_export_model

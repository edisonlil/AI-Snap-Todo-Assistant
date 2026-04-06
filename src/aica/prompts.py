"""Prompt management with built-in default scenarios."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class PromptTemplate:
    system: str
    user: str
    version: str = "v1.0"
    last_improved_feedback_count: int = 0


def _default_scenarios() -> Dict[str, PromptTemplate]:
    return {
        "工单提取": PromptTemplate(
            system=(
                "你是一名资深交付与运维支持专家。"
                "请根据截图中的聊天内容、界面文案和上下文，提取适合录入工单的关键信息。"
            ),
            user=(
                "请输出 JSON，包含字段 task_desc、platform、group_name、ticket_type、environment。"
                "task_desc 控制在 100 字内；若信息缺失请填“未知”；不要输出 JSON 以外的内容。"
            ),
        ),
        "代码审查": PromptTemplate(
            system=(
                "你是一名严格的软件工程代码审查者，重点关注缺陷、风险、边界条件和可维护性问题。"
            ),
            user=(
                "请结合截图中的代码和上下文，输出：1. 关键问题 2. 风险等级 3. 修改建议。"
                "优先列出会导致错误、回归或安全问题的点，尽量简洁。"
            ),
        ),
        "数据提取": PromptTemplate(
            system=(
                "你是一名擅长从截图中整理结构化数据的分析助手。"
            ),
            user=(
                "请从截图中提取可识别的数据并按清晰结构输出。"
                "如果适合表格，请使用 Markdown 表格；如果适合键值结构，请使用 JSON。"
                "不要编造无法确认的数据。"
            ),
        ),
        "界面审计": PromptTemplate(
            system=(
                "你是一名产品设计与前端体验审计专家，关注信息层级、可读性、交互反馈和视觉一致性。"
            ),
            user=(
                "请审计截图中的界面，输出：1. 主要问题 2. 影响 3. 优化建议。"
                "优先指出最影响理解或操作效率的问题。"
            ),
        ),
    }


def _clone_default_scenarios() -> Dict[str, PromptTemplate]:
    return {
        name: PromptTemplate(
            system=template.system,
            user=template.user,
            version=template.version,
            last_improved_feedback_count=template.last_improved_feedback_count,
        )
        for name, template in _default_scenarios().items()
    }


@dataclass
class PromptsConfig:
    current_scenario: str = "工单提取"
    scenarios: Dict[str, PromptTemplate] = field(default_factory=_clone_default_scenarios)

    def __post_init__(self) -> None:
        if not self.scenarios:
            self.scenarios = _clone_default_scenarios()
        if self.current_scenario not in self.scenarios:
            self.current_scenario = next(iter(self.scenarios))


class PromptManager:
    """Manages prompt templates for different usage scenarios."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".aica")
            config_path = os.path.join(config_dir, "prompts.json")
        self._path = config_path
        self._config = self._load_config()

    def _load_config(self) -> PromptsConfig:
        if not os.path.exists(self._path):
            return PromptsConfig()

        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            scenarios = {}
            for name, template_data in data.get("scenarios", {}).items():
                scenarios[name] = PromptTemplate(
                    system=template_data.get("system", ""),
                    user=template_data.get("user", ""),
                    version=template_data.get("version", "v1.0"),
                    last_improved_feedback_count=template_data.get("last_improved_feedback_count", 0),
                )

            return PromptsConfig(
                current_scenario=data.get("current_scenario", "工单提取"),
                scenarios=scenarios or _clone_default_scenarios(),
            )
        except Exception:
            return PromptsConfig()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {
            "current_scenario": self._config.current_scenario,
            "scenarios": {
                name: asdict(template)
                for name, template in self._config.scenarios.items()
            },
        }
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def get_current_prompt(self) -> PromptTemplate:
        scenario = self._config.current_scenario
        if scenario not in self._config.scenarios:
            if self._config.scenarios:
                fallback_name = next(iter(self._config.scenarios))
                self._config.current_scenario = fallback_name
                return self._config.scenarios[fallback_name]
            return PromptTemplate(system="", user="")
        return self._config.scenarios[scenario]

    def get_prompt(self, scenario: str) -> Optional[PromptTemplate]:
        return self._config.scenarios.get(scenario)

    def set_current_scenario(self, scenario: str) -> bool:
        if scenario not in self._config.scenarios:
            return False
        self._config.current_scenario = scenario
        self.save()
        return True

    def add_scenario(self, name: str, template: PromptTemplate) -> None:
        self._config.scenarios[name] = template
        self.save()

    def update_scenario(self, name: str, template: PromptTemplate, reason: str = "") -> bool:
        if name not in self._config.scenarios:
            return False

        self.save_version_history(name, reason=reason or "更新前自动归档")
        self._config.scenarios[name] = template
        self.save()
        return True

    def delete_scenario(self, name: str) -> bool:
        if name not in self._config.scenarios:
            return False
        if name == self._config.current_scenario:
            return False

        del self._config.scenarios[name]
        self.save()
        return True

    def list_scenarios(self) -> Dict[str, PromptTemplate]:
        return self._config.scenarios.copy()

    def get_current_scenario_name(self) -> str:
        return self._config.current_scenario

    def is_scenario_exists(self, name: str) -> bool:
        return name in self._config.scenarios

    def increment_version(self, scenario: str) -> Optional[str]:
        if scenario not in self._config.scenarios:
            return None

        template = self._config.scenarios[scenario]
        try:
            version_str = template.version.lstrip("v")
            parts = version_str.split(".")
            if len(parts) >= 2:
                parts[-1] = str(int(parts[-1]) + 1)
            else:
                parts.append("1")

            new_version = f"v{'.'.join(parts)}"
            template.version = new_version
            self.save()
            return new_version
        except Exception:
            return None

    def save_version_history(self, scenario: str, reason: str = "") -> bool:
        if scenario not in self._config.scenarios:
            return False

        try:
            history_dir = os.path.join(os.path.dirname(self._path), "prompt_history")
            os.makedirs(history_dir, exist_ok=True)

            template = self._config.scenarios[scenario]
            history_file = os.path.join(history_dir, f"{scenario}_{template.version}.json")
            history_data = {
                "scenario": scenario,
                "version": template.version,
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
                "system": template.system,
                "user": template.user,
                "last_improved_feedback_count": template.last_improved_feedback_count,
            }

            with open(history_file, "w", encoding="utf-8") as handle:
                json.dump(history_data, handle, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def get_version_history(self, scenario: str) -> list:
        try:
            history_dir = os.path.join(os.path.dirname(self._path), "prompt_history")
            if not os.path.exists(history_dir):
                return []

            histories = []
            for filename in sorted(os.listdir(history_dir), reverse=True):
                if not filename.startswith(f"{scenario}_"):
                    continue
                with open(os.path.join(history_dir, filename), "r", encoding="utf-8") as handle:
                    histories.append(json.load(handle))
            return histories
        except Exception:
            return []

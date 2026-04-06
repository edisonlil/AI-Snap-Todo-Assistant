"""Prompt management for the ticket assistant workflow."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, Optional


DEFAULT_SCENARIO_NAME = "工单待办助手"


@dataclass
class PromptTemplate:
    system: str
    user: str
    version: str = "v2.0"
    last_improved_feedback_count: int = 0


def _default_prompt() -> PromptTemplate:
    return PromptTemplate(
        system=(
            "你是一个工单待办助手。"
            "用户会通过截图收集群聊、工单、报错、环境等信息。"
            "你的目标不是做通用内容提取，而是生成适合工单跟进的结构化摘要。"
        ),
        user=(
            "请仅输出 JSON，字段固定为："
            "title, group_name, environment, product_line, ticket_type, current_summary, timeline_entry。"
            "要求："
            "1. title 是待办标题，简洁明确；"
            "2. group_name/environment/product_line/ticket_type 缺失时填“未知”；"
            "3. current_summary 是当前结论或现状摘要，用自然语言；"
            "4. timeline_entry 是适合写入时间线的一条跟进记录，用自然语言，不要输出 JSON 串到文本字段；"
            "5. 不要输出 JSON 以外的解释。"
        ),
    )


def _clone_default_scenarios() -> Dict[str, PromptTemplate]:
    template = _default_prompt()
    return {
        DEFAULT_SCENARIO_NAME: PromptTemplate(
            system=template.system,
            user=template.user,
            version=template.version,
            last_improved_feedback_count=template.last_improved_feedback_count,
        )
    }


@dataclass
class PromptsConfig:
    current_scenario: str = DEFAULT_SCENARIO_NAME
    scenarios: Dict[str, PromptTemplate] = field(default_factory=_clone_default_scenarios)

    def __post_init__(self) -> None:
        if DEFAULT_SCENARIO_NAME not in self.scenarios:
            self.scenarios = _clone_default_scenarios()
        self.current_scenario = DEFAULT_SCENARIO_NAME


class PromptManager:
    """Manages the single ticket-assistant prompt template."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".aica")
            config_path = os.path.join(config_dir, "prompts.json")
        self._path = config_path
        self._config = self._load_config()

    def _load_config(self) -> PromptsConfig:
        default = _default_prompt()
        if not os.path.exists(self._path):
            return PromptsConfig(
                current_scenario=DEFAULT_SCENARIO_NAME,
                scenarios={DEFAULT_SCENARIO_NAME: default},
            )

        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            scenarios = data.get("scenarios", {})
            active = scenarios.get(DEFAULT_SCENARIO_NAME) or next(iter(scenarios.values()), {})
            template = PromptTemplate(
                system=active.get("system", default.system),
                user=active.get("user", default.user),
                version=active.get("version", default.version),
                last_improved_feedback_count=active.get("last_improved_feedback_count", 0),
            )
            return PromptsConfig(
                current_scenario=DEFAULT_SCENARIO_NAME,
                scenarios={DEFAULT_SCENARIO_NAME: template},
            )
        except Exception:
            return PromptsConfig(
                current_scenario=DEFAULT_SCENARIO_NAME,
                scenarios={DEFAULT_SCENARIO_NAME: default},
            )

    def save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {
            "current_scenario": DEFAULT_SCENARIO_NAME,
            "scenarios": {
                DEFAULT_SCENARIO_NAME: asdict(self._config.scenarios[DEFAULT_SCENARIO_NAME]),
            },
        }
        with open(self._path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def get_current_prompt(self) -> PromptTemplate:
        return self._config.scenarios[DEFAULT_SCENARIO_NAME]

    def get_prompt(self, scenario: str) -> Optional[PromptTemplate]:
        if scenario != DEFAULT_SCENARIO_NAME:
            return None
        return self.get_current_prompt()

    def set_current_scenario(self, scenario: str) -> bool:
        return scenario == DEFAULT_SCENARIO_NAME

    def add_scenario(self, name: str, template: PromptTemplate) -> None:
        if name != DEFAULT_SCENARIO_NAME:
            return
        self._config.scenarios[DEFAULT_SCENARIO_NAME] = template
        self.save()

    def update_scenario(self, name: str, template: PromptTemplate, reason: str = "") -> bool:
        if name != DEFAULT_SCENARIO_NAME:
            return False
        self.save_version_history(name, reason=reason or "更新前自动归档")
        self._config.scenarios[DEFAULT_SCENARIO_NAME] = template
        self.save()
        return True

    def delete_scenario(self, name: str) -> bool:
        return False

    def list_scenarios(self) -> Dict[str, PromptTemplate]:
        return {DEFAULT_SCENARIO_NAME: self.get_current_prompt()}

    def get_current_scenario_name(self) -> str:
        return DEFAULT_SCENARIO_NAME

    def is_scenario_exists(self, name: str) -> bool:
        return name == DEFAULT_SCENARIO_NAME

    def increment_version(self, scenario: str) -> Optional[str]:
        if scenario != DEFAULT_SCENARIO_NAME:
            return None
        template = self._config.scenarios[DEFAULT_SCENARIO_NAME]
        version_str = template.version.lstrip("v")
        parts = version_str.split(".")
        if len(parts) >= 2:
            parts[-1] = str(int(parts[-1]) + 1)
        else:
            parts.append("1")
        template.version = f"v{'.'.join(parts)}"
        self.save()
        return template.version

    def save_version_history(self, scenario: str, reason: str = "") -> bool:
        if scenario != DEFAULT_SCENARIO_NAME:
            return False
        try:
            history_dir = os.path.join(os.path.dirname(self._path), "prompt_history")
            os.makedirs(history_dir, exist_ok=True)
            template = self._config.scenarios[DEFAULT_SCENARIO_NAME]
            history_file = os.path.join(history_dir, f"{DEFAULT_SCENARIO_NAME}_{template.version}.json")
            history_data = {
                "scenario": DEFAULT_SCENARIO_NAME,
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
        if scenario != DEFAULT_SCENARIO_NAME:
            return []
        try:
            history_dir = os.path.join(os.path.dirname(self._path), "prompt_history")
            if not os.path.exists(history_dir):
                return []
            histories = []
            for filename in sorted(os.listdir(history_dir), reverse=True):
                if not filename.startswith(f"{DEFAULT_SCENARIO_NAME}_"):
                    continue
                with open(os.path.join(history_dir, filename), "r", encoding="utf-8") as handle:
                    histories.append(json.load(handle))
            return histories
        except Exception:
            return []

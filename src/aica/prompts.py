"""Prompt management for the ticket assistant workflow."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, Optional

from aica.paths import prompts_file as default_prompts_file


DEFAULT_SCENARIO_NAME = "工单待办助手"


@dataclass
class PromptTemplate:
    system: str
    user: str
    version: str = "v2.3"
    last_improved_feedback_count: int = 0


_TITLE_FOCUS_RULES = (
    "e. 如果原始信息同时包含前置条件、复现步骤、排查动作和最终异常现象，"
    "标题必须优先保留最终用户可见的异常现象，不要把“上传时未勾选”“正在确认字体”“排查服务器字体”这类背景或排查动作写成标题主体。"
    "f. 例如“上传时未勾选，但线上勾选后重新打开变成字符Q”，"
    "标题应优先概括为“文档勾选框线上勾选后重新打开变成字符Q”，不要概括成“上传时未勾选”。"
)

_FIELD_RULES = (
    "2. product_line 为预埋字段，当前固定返回“文档中台”，不要输出其他产品线值。"
    "3. ticket_type 只能从“排查类”“咨询类”“操作类”中选择一个，必须结合描述智能判断："
    "出现报错、异常、失败、无法使用等现象归为“排查类”；"
    "询问规则、能力、使用方式、是否支持等归为“咨询类”；"
    "请求开通、配置、修改、加白、导入导出等人工执行动作归为“操作类”。"
    "4. group_name/environment 缺失时填“未知”。"
)


def _apply_title_focus_rules(user_prompt: str) -> str:
    prompt = str(user_prompt or "").strip()
    if not prompt:
        return prompt
    if "最终用户可见的异常现象" in prompt:
        return prompt
    marker = "2. group_name/environment/product_line/ticket_type 缺失时填“未知”。"
    if marker in prompt:
        return prompt.replace(marker, f"{_TITLE_FOCUS_RULES}{marker}")
    return f"{prompt}{_TITLE_FOCUS_RULES}"


def _apply_field_rules(user_prompt: str) -> str:
    prompt = str(user_prompt or "").strip()
    if not prompt:
        return prompt
    if "当前固定返回“文档中台”" in prompt and "排查类" in prompt and "咨询类" in prompt and "操作类" in prompt:
        return prompt

    legacy_marker = "2. group_name/environment/product_line/ticket_type 缺失时填“未知”。"
    if legacy_marker in prompt:
        return prompt.replace(legacy_marker, _FIELD_RULES)
    return f"{prompt}{_FIELD_RULES}"


def _apply_prompt_upgrades(user_prompt: str) -> str:
    return _apply_field_rules(_apply_title_focus_rules(user_prompt))


def _default_prompt() -> PromptTemplate:
    return PromptTemplate(
        system=(
            "你是一位资深的 B 端技术支持专家，擅长从截图、群聊、工单和报错信息中提炼标准化工单内容。"
            "你的目标不是泛化总结，而是输出适合技术支持团队流转、检索和跟进的结构化结果。"
        ),
        user=(
            "请仅输出 JSON，字段固定为："
            "title, group_name, environment, product_line, ticket_type, current_summary, timeline_entry。"
            "要求："
            "1. title 必须按照以下工单标题规范生成，不要直接照抄原文。"
            "角色：你是一位资深的B端技术支持专家，擅长将琐碎的客户反馈转化为标准化的工单标题。"
            "任务：请根据我提供的“原始问题信息”，总结出一个符合 2026 年规范的工单标题。"
            "标题格式规范：【关联产品】[触发操作/核心异常点] + [关键报错/现象]。"
            "填写要求（严格遵守）："
            "a. 严禁口语化：禁止使用“坏了”、“打不开”、“不行”、“有问题”等词汇。"
            "b. 技术化表述：必须优先使用“接口超时”、“API返回500”、“样张跑版”、“鉴权失败”等专业词汇。"
            "c. 精简准确：标题需直击痛点，让人一眼看清现象，建议控制在 50 字以内。"
            "d. 如果信息不足以明确关联产品，可结合 product_line、截图上下文或业务对象补全；仍无法判断时再使用中性产品名。"
            f"{_TITLE_FOCUS_RULES}"
            f"{_FIELD_RULES}"
            "5. 如果输入中带有已有待办上下文，它只用于理解背景，不要直接复述旧摘要。"
            "6. current_summary 是当前结论或现状摘要，用自然语言描述当前问题和进展。"
            "7. timeline_entry 必须聚焦当前截图新增的跟进信息、观察结论或待处理点，用自然语言描述。"
            "8. 不要输出 JSON 以外的解释，不要输出 markdown。"
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
            config_path = str(default_prompts_file())
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
            active = scenarios.get(DEFAULT_SCENARIO_NAME) or {}
            template = PromptTemplate(
                system=active.get("system", default.system),
                user=_apply_prompt_upgrades(active.get("user", default.user)),
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

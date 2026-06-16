"""Prompt strategy builder for intent-driven screenshot analysis."""
from __future__ import annotations

from dataclasses import dataclass

from .rules import AnalysisRuleConfig, SceneAnalysisRule, UserRuleConfig
from .intent import (
    AnalysisIntent,
    CAPTURE_MODE_SEQUENCE,
    SCENE_CHAT_FEEDBACK,
    SCENE_PROBLEM_CONCLUSION,
    SCENE_STEP_SEQUENCE,
)


_BASE_SYSTEM_PROMPT = (
    "你是一位资深的 B 端技术支持专家。"
    "你要根据截图内容输出适合工单待办流转的结构化结果。"
    "不要泛化总结，不要编造截图中没有的信息，优先保留排查和跟进真正需要的细节。"
)

_JSON_CONTRACT = (
    "请仅输出 JSON，字段固定为："
    "title, group_name, environment, product_line, ticket_type, current_summary, timeline_entry。"
)

_COMMON_RULES = (
    "通用要求："
    "1. title 必须直接给出可展示、可保存的最终工单标题，优先保留最终用户可见的异常现象或核心诉求，不要写成“客户反馈问题”“排查截图”这类泛化标题。"
    "2. product_line 固定返回空字符串，不要根据截图推测或编造产品线。"
    "3. ticket_type 只能从“排查类”“咨询类”“操作类”中选择一个。"
    "4. current_summary 只写当前问题现状或本批截图的核心结论，不要塞入过多参数明细。"
    "5. timeline_entry 只写本批截图新增的跟进、观察、待确认项或下一步。"
    "6. 参数、关键日志、URL、TraceId、返回结果、错误码等细节都直接写进 timeline_entry，不要单独输出其他字段，也不要只概括成“已提供参数”或“有日志”。"
    "7. group_name/environment 缺失时填“未知”。（group_name信息通常在左上角，需重点关注，它是关键信息）"
    "8. 不要输出 JSON 以外的解释或 markdown。"
)

_USER_RULE_TEMPLATE = "【用户规则】\n{{RULE}}\n"

_SCENE_RULES = {
    SCENE_CHAT_FEEDBACK: (
        "当前场景：工单跟进。"
        "重点提取：问题现象、客户诉求、当前结论、待确认项、下一步动作。"
        "如果聊天里只提到客户补充了截图、参数、日志，但明细不在当前截图里，不要编造具体值。"
    ),
    SCENE_PROBLEM_CONCLUSION: (
        "当前场景：问题结论。"
        "重点提取：本次分析的最终结论、根因判断、已确认事实和可直接写入结论的内容。"
        "timeline_entry 仍然输出简要结论文本，但保存时应作为待办结论而不是普通跟进。"
    ),
    SCENE_STEP_SEQUENCE: (
        "当前场景：连续步骤截图。"
        "重点提取：按截图顺序归纳操作步骤、在哪一步出现异常、有哪些关键观察。"
        "timeline_entry 需要体现步骤链路或异常出现点。"
    ),
}


@dataclass(frozen=True)
class AnalysisPromptBundle:
    system_prompt: str
    user_prompt: str
    scene_type: str
    scene_label: str
    context_text: str
    image_count: int
    applied_rule_snapshot: dict[str, object]
    prompt_version: str
    trace_id: str


def build_analysis_system_prompt() -> str:
    return _BASE_SYSTEM_PROMPT


def _build_sequence_section(intent: AnalysisIntent, image_count: int) -> str:
    return (
        "这是一组连续截图，请按顺序综合理解；相邻截图有重复时要去重，但不要丢失后续截图新增信息。"
        if intent.capture_group_mode == CAPTURE_MODE_SEQUENCE or image_count > 1
        else "这是一张单图，请直接围绕当前截图提取结构化结果。"
    )


def _build_context_section(context_text: str) -> str:
    return (
        f"【已有待办上下文】\n{context_text}\n\n"
        "这些内容只用于理解背景，不要直接复述为本次分析结果；请基于当前截图内容产出本次新增跟进。\n\n"
        if context_text.strip()
        else ""
    )


def _build_user_rule_section(rule: UserRuleConfig) -> str:
    rendered_rules = [f"{index}. {text}" for index, text in enumerate(rule.to_lines(), start=1)]
    replacement_text = "\n".join(rendered_rules) if rendered_rules else "无"
    return _USER_RULE_TEMPLATE.replace("{{RULE}}", replacement_text)


def build_analysis_prompt_bundle(
    intent: AnalysisIntent,
    *,
    rule: UserRuleConfig | SceneAnalysisRule | None = None,
    prompt_version: str = "built-in",
    trace_id: str = "",
    context_text: str = "",
    image_count: int = 1,
) -> AnalysisPromptBundle:
    applied_rule = UserRuleConfig.from_dict(rule)
    user_sections = [
        _build_context_section(context_text),
        f"{_JSON_CONTRACT}\n",
        f"{_COMMON_RULES}\n",
        f"{_SCENE_RULES.get(intent.scene_type, _SCENE_RULES[SCENE_CHAT_FEEDBACK])}\n",
        f"{_build_sequence_section(intent, image_count)}\n",
        "\n",
        _build_user_rule_section(applied_rule),
    ]
    return AnalysisPromptBundle(
        system_prompt=_BASE_SYSTEM_PROMPT,
        user_prompt="".join(section for section in user_sections if section),
        scene_type=intent.scene_type,
        scene_label=intent.scene_label,
        context_text=context_text.strip(),
        image_count=max(1, int(image_count)),
        applied_rule_snapshot={"items": applied_rule.to_lines()},
        prompt_version=str(prompt_version or "built-in"),
        trace_id=str(trace_id or "").strip(),
    )


def build_analysis_prompt_bundle_from_rules(
    intent: AnalysisIntent,
    *,
    rules_config: AnalysisRuleConfig | None = None,
    trace_id: str = "",
    context_text: str = "",
    image_count: int = 1,
) -> AnalysisPromptBundle:
    config = rules_config or AnalysisRuleConfig()
    applied_rule = config.scene_rules.get(intent.scene_type, UserRuleConfig())
    if applied_rule.is_empty():
        if not config.rules.is_empty():
            applied_rule = config.rules
        else:
            applied_rule = UserRuleConfig.from_dict(config.scenes.get(intent.scene_type, SceneAnalysisRule()))
    return build_analysis_prompt_bundle(
        intent,
        rule=applied_rule,
        prompt_version=config.version,
        trace_id=trace_id,
        context_text=context_text,
        image_count=image_count,
    )


def build_analysis_text_prompt(intent: AnalysisIntent, *, context_text: str = "", image_count: int = 1) -> str:
    return build_analysis_prompt_bundle(
        intent,
        context_text=context_text,
        image_count=image_count,
    ).user_prompt

"""Prompt strategy builder for intent-driven screenshot analysis."""
from __future__ import annotations

from .analysis_intent import (
    AnalysisIntent,
    CAPTURE_MODE_SEQUENCE,
    SCENE_API_DETAIL,
    SCENE_CHAT_FEEDBACK,
    SCENE_CUSTOM,
    SCENE_ERROR_LOG,
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
    "1. title 要简洁专业，优先保留最终用户可见的异常现象或核心诉求。"
    "2. product_line 固定返回“文档中台”。"
    "3. ticket_type 只能从“排查类”“咨询类”“操作类”中选择一个。"
    "4. current_summary 只写当前问题现状或本批截图的核心结论，不要塞入过多参数明细。"
    "5. timeline_entry 只写本批截图新增的跟进、观察、待确认项或下一步。"
    "6. 参数、关键日志、URL、TraceId、返回结果、错误码等细节都直接写进 timeline_entry，不要单独输出其他字段，也不要只概括成“已提供参数”或“有日志”。"
    "7. group_name/environment 缺失时填“未知”。"
    "8. 不要输出 JSON 以外的解释或 markdown。"
)

_SCENE_RULES = {
    SCENE_CHAT_FEEDBACK: (
        "当前场景：工单跟进。"
        "重点提取：问题现象、客户诉求、当前结论、待确认项、下一步动作。"
        "如果聊天里只提到客户补充了截图、参数、日志，但明细不在当前截图里，不要编造具体值。"
    ),
    SCENE_ERROR_LOG: (
        "当前场景：错误与日志。"
        "重点提取：错误信息、错误码、TraceId、关键日志行、推断方向。"
        "timeline_entry 中要尽量保留原始报错词、关键信息和排查方向。"
    ),
    SCENE_API_DETAIL: (
        "当前场景：参数与接口详情。"
        "重点提取：请求 URL、请求参数、返回参数、结果码、关键字段。"
        "需要尽量保留字段名和字段值，不要只总结成“客户提供了请求参数”。"
    ),
    SCENE_STEP_SEQUENCE: (
        "当前场景：连续步骤截图。"
        "重点提取：按截图顺序归纳操作步骤、在哪一步出现异常、有哪些关键观察。"
        "timeline_entry 需要体现步骤链路或异常出现点。"
    ),
    SCENE_CUSTOM: (
        "当前场景：其他自定义。"
        "请根据用户补充重点决定提取重心。"
        "若截图包含参数、日志或返回结果，也直接写进 timeline_entry。"
    ),
}


def build_analysis_system_prompt() -> str:
    return _BASE_SYSTEM_PROMPT


def build_analysis_text_prompt(intent: AnalysisIntent, *, context_text: str = "", image_count: int = 1) -> str:
    focus_hint = intent.focus_hint.strip()
    sequence_hint = (
        "这是一组连续截图，请按顺序综合理解；相邻截图有重复时要去重，但不要丢失后续截图新增信息。"
        if intent.capture_group_mode == CAPTURE_MODE_SEQUENCE or image_count > 1
        else "这是一张单图，请直接围绕当前截图提取结构化结果。"
    )
    focus_section = (
        f"用户补充重点：{focus_hint}。请优先满足这个提取重点。"
        if focus_hint
        else "用户没有额外补充重点。"
    )
    context_section = (
        f"【已有待办上下文】\n{context_text}\n\n"
        "这些内容只用于理解背景，不要直接复述为本次分析结果；请基于当前截图内容产出本次新增跟进。\n\n"
        if context_text.strip()
        else ""
    )
    return (
        f"{context_section}"
        f"{_JSON_CONTRACT}\n"
        f"{_COMMON_RULES}\n"
        f"{_SCENE_RULES.get(intent.scene_type, _SCENE_RULES[SCENE_CUSTOM])}\n"
        f"{sequence_hint}\n"
        f"{focus_section}"
    )

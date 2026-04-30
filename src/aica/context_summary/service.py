"""Service facade for shared context-summary generation."""
from __future__ import annotations

from .agent import DefaultContextSummaryAgent
from .models import ContextSummaryAgent, ContextSummaryRequest, ContextSummaryResult
from ..llm.service import LLMService
from ..text_sanitize import sanitize_text


class ContextSummaryService:
    def __init__(
        self,
        llm_service: LLMService | None = None,
        agent: ContextSummaryAgent | None = None,
    ) -> None:
        self._agent = agent or DefaultContextSummaryAgent(llm_service)

    def summarize(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        try:
            return self._agent.summarize_with_llm(request)
        except Exception:
            return self._agent.summarize_locally(request)


def format_summary_for_analysis_context(request: ContextSummaryRequest, result: ContextSummaryResult) -> str:
    title = sanitize_text(request.extra_context.get("title", "")).strip()
    group_name = sanitize_text(request.extra_context.get("group_name", "")).strip()
    environment = sanitize_text(request.extra_context.get("environment", "")).strip()
    product_line = sanitize_text(request.extra_context.get("product_line", "")).strip()
    ticket_type = sanitize_text(request.extra_context.get("ticket_type", "")).strip()
    current_summary = sanitize_text(request.extra_context.get("current_summary", "")).strip() or request.description
    summary_text = sanitize_text(result.summary_text).strip() or "问题概述: 暂无"
    return (
        "以下内容是当前已选中待办的压缩上下文，仅供参考，不要直接复述为本次分析结果。\n"
        "请重点根据当前这张新截图提炼新增信息。\n"
        "current_summary 是创建时摘要，后续追加时不要改写旧摘要；"
        "请把本次新增进展写入 timeline_entry，把参数、日志、TraceId、URL 等排查依据写入 evidence_items。\n\n"
        f"待办标题: {title}\n"
        f"群聊名称: {group_name}\n"
        f"环境: {environment}\n"
        f"产品线: {product_line}\n"
        f"工单类型: {ticket_type}\n"
        f"当前摘要: {current_summary}\n"
        "压缩上下文:\n"
        f"{summary_text}"
    ).strip()

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import AppConfig, ProviderConfig, ProviderModelConfig, TaskModelBinding, TaskModelBindings
from aica.control_panel_state import TASK_NAMES
from aica.context_summary_models import ContextSummaryRequest, ContextSummaryResult, build_context_summary_request_for_todo
from aica.context_summary_service import ContextSummaryService, format_summary_for_analysis_context
from aica.llm.service import LLMService
from aica.log_analysis_commands import parse_log_analysis_command
from aica.log_analysis_context import summarize_investigation_context
from aica.models import TicketSummaryFields
from aica.todo_models import TimelineEvent, TodoConclusion, TodoItem


class _FailingAgent:
    def summarize_with_llm(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        raise RuntimeError(f"boom: {request.summary_goal}")

    def summarize_locally(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        return ContextSummaryResult(
            summary_text="问题概述: 本地降级",
            problem_brief="本地降级",
            source_stats={"mode": "fallback_local"},
        )


def _build_todo() -> TodoItem:
    todo = TodoItem(
        id="todo-ctx-1",
        title="接口调用失败",
        current_summary="客户反馈接口调用失败，偶发 500。",
        summary_fields=TicketSummaryFields(
            group_name="测试群",
            environment="生产",
            product_line="智能助手",
            ticket_type="排查类",
        ),
        conclusion=TodoConclusion(),
        timeline=[
            TimelineEvent(
                id="event-1",
                timestamp="2026-04-16T10:00:00",
                kind="follow_up",
                scenario="客户反馈",
                content="客户反馈接口报错，请协助排查 request_id=req-1",
            ),
            TimelineEvent(
                id="event-2",
                timestamp="2026-04-16T10:15:00",
                kind="log_analysis_command",
                event_type="log_analysis_command",
                scenario="日志分析任务",
                content="/分析日志 request_id=req-1 权限报错",
                payload={"command_text": "/分析日志 request_id=req-1 权限报错"},
            ),
            TimelineEvent(
                id="event-3",
                timestamp="2026-04-16T10:20:00",
                kind="log_analysis_result",
                event_type="log_analysis_result",
                scenario="日志分析结果",
                content="日志分析结果",
                payload={
                    "findings": "app.log:12 - HTTP 500 | request_id=req-1",
                    "judgment": "下游服务异常",
                    "next_steps": "补充 gateway.log 继续排查",
                },
            ),
            TimelineEvent(
                id="event-4",
                timestamp="2026-04-16T10:30:00",
                kind="follow_up",
                scenario="跟进记录",
                content="待确认是否和用户权限配置有关",
            ),
        ],
    )
    return todo


def test_context_summary_service_hides_failure_mode_from_callers() -> None:
    request = ContextSummaryRequest(
        summary_goal="append_screenshot_context",
        description="接口报错",
    )

    result = ContextSummaryService(agent=_FailingAgent()).summarize(request)

    assert result.problem_brief == "本地降级"


def test_control_panel_runtime_task_names_include_log_analysis_and_context_summary() -> None:
    assert "log_analysis" in TASK_NAMES
    assert "context_summary" in TASK_NAMES


def test_llm_service_resolves_context_summary_text_model() -> None:
    config = AppConfig(
        default_provider_id="stub",
        providers=[
            ProviderConfig(
                id="stub",
                kind="openai_compatible",
                name="Stub",
                api_key="key",
                base_url="https://example.com",
                models=[
                    ProviderModelConfig(id="vision", name="vision", capabilities=["vision_chat", "text_chat"]),
                    ProviderModelConfig(id="text", name="text", capabilities=["text_chat"]),
                ],
            )
        ],
        task_model_bindings=TaskModelBindings(
            analysis=TaskModelBinding(provider_id="stub", model_id="vision"),
            log_analysis=TaskModelBinding(provider_id="stub", model_id="vision"),
            plan_export=TaskModelBinding(provider_id="stub", model_id="vision"),
            context_summary=TaskModelBinding(provider_id="stub", model_id="text"),
        ),
    )

    resolved = LLMService(config).resolve_task_model("context_summary")

    assert resolved.reference.model_id == "text"
    assert resolved.task_name == "context_summary"
    assert resolved.fallback_used is False


def test_llm_service_context_summary_falls_back_to_analysis_binding() -> None:
    config = AppConfig(
        default_provider_id="stub",
        providers=[
            ProviderConfig(
                id="stub",
                kind="openai_compatible",
                name="Stub",
                api_key="key",
                base_url="https://example.com",
                models=[ProviderModelConfig(id="vision", name="vision", capabilities=["vision_chat", "text_chat"])],
            )
        ],
        task_model_bindings=TaskModelBindings(
            analysis=TaskModelBinding(provider_id="stub", model_id="vision"),
            log_analysis=TaskModelBinding(provider_id="stub", model_id="vision"),
            plan_export=TaskModelBinding(provider_id="stub", model_id="vision"),
            context_summary=TaskModelBinding(),
        ),
    )

    resolved = LLMService(config).resolve_task_model("context_summary")

    assert resolved.reference.model_id == "vision"
    assert resolved.task_name == "analysis"
    assert resolved.fallback_used is True


def test_append_screenshot_context_summary_prefers_recent_high_value_entries() -> None:
    todo = _build_todo()
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="append_screenshot_context",
        max_items=8,
        max_chars=1800,
    )

    result = ContextSummaryService().summarize(request)
    context_text = format_summary_for_analysis_context(request, result)

    assert result.source_stats["mode"] == "fallback_local"
    assert any("HTTP 500" in item.text or "下游服务异常" in item.text for item in result.key_points)
    assert "接口调用失败" in context_text
    assert "压缩上下文" in context_text


def test_summarize_investigation_context_uses_shared_summary_mapping() -> None:
    todo = _build_todo()

    result = summarize_investigation_context(
        todo,
        parse_log_analysis_command("/分析日志 request_id=req-1 权限报错"),
    )

    assert result.problem_summary
    assert result.actions_taken
    assert result.confirmed_facts
    assert any(item == "request_id=req-1" for item in result.current_focus)

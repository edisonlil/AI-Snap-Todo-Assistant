from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import AppConfig, ProviderConfig, ProviderModelConfig, ServerConfig, TaskModelBinding, TaskModelBindings
from aica.context_summary.agent import DefaultContextSummaryAgent
from aica.context_summary.models import ContextSummaryRequest, ContextSummaryResult, build_context_summary_request_for_todo
from aica.context_summary.service import ContextSummaryService, format_summary_for_analysis_context
from aica.control_panel_state import TASK_NAMES
from aica.llm.service import LLMService
from aica.log_analysis.commands import parse_log_analysis_command
from aica.log_analysis.context import summarize_investigation_context
from aica.models import TicketSummaryFields
from aica.todo.models import TimelineAttachment, TimelineEvent, TodoConclusion, TodoItem
from aica.worker import StageSummaryWorker, _rewrite_stage_summary_locally, _stage_summary_rewrite_instruction


class _FailingAgent:
    def summarize_with_llm(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        raise RuntimeError(f"boom: {request.summary_goal}")

    def summarize_locally(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        return ContextSummaryResult(
            summary_text="问题概述: 本地降级",
            problem_brief="本地降级",
            source_stats={"mode": "fallback_local"},
        )


class _RecordingLLMService:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[dict[str, object]] = []

    def run_task(self, task_name: str, *, messages, temperature: float = 0.2, **_kwargs) -> str:  # noqa: ANN001
        self.calls.append(
            {
                "task_name": task_name,
                "messages": list(messages),
                "temperature": temperature,
            }
        )
        return self.response_text


class _RecordingStageSummaryClient:
    calls: list[dict[str, str]] = []
    response_text = "### 服务端阶段总结\n- 已整理当前阶段进展"

    @classmethod
    def from_config(cls, _config):  # noqa: ANN001
        return cls()

    def generate_stage_summary(
        self,
        *,
        current_markdown: str,
        stage_materials: str,
        task_title: str,
        stage_name: str,
        stage_goal: str,
    ) -> str:
        self.calls.append(
            {
                "current_markdown": current_markdown,
                "stage_materials": stage_materials,
                "task_title": task_title,
                "stage_name": stage_name,
                "stage_goal": stage_goal,
            }
        )
        return self.response_text


class _FailingStageSummaryClient:
    @classmethod
    def from_config(cls, _config):  # noqa: ANN001
        return cls()

    def generate_stage_summary(self, **_kwargs) -> str:  # noqa: ANN003
        raise RuntimeError("server down")


def _build_todo() -> TodoItem:
    return TodoItem(
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


def test_timeline_rollup_prompt_forbids_expansion_and_does_not_fix_template() -> None:
    todo = _build_todo()
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="timeline_rollup",
        max_items=8,
        max_chars=1800,
    )
    agent = DefaultContextSummaryAgent()

    messages = agent._build_messages(request, agent._select_entries(request))  # noqa: SLF001
    system_prompt = messages[0].content
    user_prompt = messages[1].content

    assert "宁可遗漏，也不要编造" in system_prompt
    assert "只能基于输入时间线原文" in user_prompt
    assert "阶段现状" in user_prompt
    assert "当前结论" in user_prompt
    assert "已发生进展" in user_prompt
    assert "待确认事项" in user_prompt
    assert "不要新增“今天”“昨天”“随后”“最终”等时间锚点" in user_prompt


def test_select_entries_returns_full_timeline_in_original_order() -> None:
    todo = _build_todo()
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="append_screenshot_context",
        max_items=1,
        max_chars=32,
    )
    agent = DefaultContextSummaryAgent()

    entries = agent._select_entries(request)  # noqa: SLF001

    assert [entry.timestamp for entry in entries] == [
        "2026-04-16T10:00:00",
        "2026-04-16T10:15:00",
        "2026-04-16T10:20:00",
        "2026-04-16T10:30:00",
    ]


def test_build_messages_keeps_full_long_timeline_content() -> None:
    long_text = ("very-long-timeline-content-" * 20) + "tail-marker"
    todo = _build_todo()
    todo.timeline[0] = TimelineEvent(
        id="event-long",
        timestamp="2026-04-16T10:00:00",
        kind="follow_up",
        scenario="客户反馈",
        content=long_text,
    )
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="append_screenshot_context",
        max_items=1,
        max_chars=32,
    )
    agent = DefaultContextSummaryAgent()

    messages = agent._build_messages(request, agent._select_entries(request))  # noqa: SLF001

    assert long_text in messages[1].content


def test_timeline_rollup_local_summary_keeps_order_and_uncertainty() -> None:
    todo = _build_todo()
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="timeline_rollup",
        max_items=8,
        max_chars=1800,
    )

    result = ContextSummaryService().summarize(request)
    summary_text = result.summary_text

    assert result.source_stats["mode"] == "fallback_local"
    assert "### 阶段现状" in summary_text
    assert "### 当前结论" in summary_text
    assert "暂无明确结论" in summary_text
    assert "### 已发生进展" in summary_text
    assert "### 待确认事项" in summary_text
    assert summary_text.index("请协助排查 request\\_id=req-1") < summary_text.index("/分析日志 request\\_id=req-1 权限报错")
    assert summary_text.index("/分析日志 request\\_id=req-1 权限报错") < summary_text.index("日志分析结果")
    assert summary_text.index("日志分析结果") < summary_text.index("待确认是否和用户权限配置有关")
    assert "待确认是否和用户权限配置有关" in summary_text
    assert "今天" not in summary_text
    assert "昨天" not in summary_text
    assert "随后" not in summary_text
    assert "最终" not in summary_text
    assert "\n\n### 当前结论\n" in summary_text
    assert "\n\n### 待确认事项\n" in summary_text


def test_timeline_rollup_prompt_hides_attachment_filenames_without_links() -> None:
    todo = _build_todo()
    todo.timeline[0] = TimelineEvent(
        id="event-with-attachments",
        timestamp="2026-04-16T10:00:00",
        kind="follow_up",
        scenario="客户反馈",
        content="客户反馈只要带 wpsPreview 参数就会出现问题",
        attachments=[
            TimelineAttachment(name="f847e28bc0c8d842ecd5459dc0a9c267.png", path="C:\\tmp\\f847e28bc0c8d842ecd5459dc0a9c267.png"),
            TimelineAttachment(name="17a45e4abd8da4e0ee7ecafedff66f68.png", path="C:\\tmp\\17a45e4abd8da4e0ee7ecafedff66f68.png"),
        ],
    )
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="timeline_rollup",
        max_items=8,
        max_chars=1800,
    )
    agent = DefaultContextSummaryAgent()

    messages = agent._build_messages(request, agent._select_entries(request))  # noqa: SLF001

    assert "f847e28bc0c8d842ecd5459dc0a9c267.png" not in messages[1].content
    assert "17a45e4abd8da4e0ee7ecafedff66f68.png" not in messages[1].content
    assert "附件:" not in messages[1].content


def test_timeline_rollup_summary_filters_attachment_suffix_noise() -> None:
    todo = _build_todo()
    todo.timeline.append(
        TimelineEvent(
            id="event-conclusion",
            timestamp="2026-04-16T10:40:00",
            kind="conclusion",
            scenario="结论更新",
            content="建议客户先不携带该参数保证业务正常\n附件: f847e28bc0c8d842ecd5459dc0a9c267.png, 关于进一步加强维修工属具使用安全的通知.docx",
        )
    )
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="timeline_rollup",
        max_items=8,
        max_chars=1800,
    )

    result = ContextSummaryService().summarize(request)

    assert "附件:" not in result.summary_text
    assert "f847e28bc0c8d842ecd5459dc0a9c267.png" not in result.summary_text
    assert "关于进一步加强维修工属具使用安全的通知.docx" not in result.summary_text
    assert "建议客户先不携带该参数保证业务正常" in result.summary_text


def test_timeline_rollup_summary_keeps_real_urls_in_body() -> None:
    todo = _build_todo()
    todo.timeline.append(
        TimelineEvent(
            id="event-link",
            timestamp="2026-04-16T10:35:00",
            kind="follow_up",
            scenario="客户补充",
            content="客户提供预览链接: https://wpszt.bbwport.com/micsweb/viewweb/reader/439e8b9faf195951c968bced2424908a?wpsPreview=0010000",
        )
    )
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="timeline_rollup",
        max_items=8,
        max_chars=1800,
    )

    result = ContextSummaryService().summarize(request)

    assert "https://wpszt.bbwport.com/micsweb/viewweb/reader/439e8b9faf195951c968bced2424908a?wpsPreview=0010000" in result.summary_text


def test_timeline_rollup_summary_surfaces_explicit_conclusion() -> None:
    todo = _build_todo()
    todo.conclusion = TodoConclusion(content="已定位为用户权限配置缺失")
    request = build_context_summary_request_for_todo(
        todo,
        summary_goal="timeline_rollup",
        max_items=8,
        max_chars=1800,
    )
    agent = DefaultContextSummaryAgent()

    messages = agent._build_messages(request, agent._select_entries(request))  # noqa: SLF001
    result = ContextSummaryService().summarize(request)

    assert "当前结论（单独输入）" in messages[1].content
    assert "已定位为用户权限配置缺失" in messages[1].content
    assert "### 当前结论" in result.summary_text
    assert "已定位为用户权限配置缺失" in result.summary_text


def test_stage_summary_rewrite_prompt_forbids_new_facts_and_time_anchors() -> None:
    llm_service = _RecordingLLMService("更短的阶段总结")
    worker = StageSummaryWorker(
        llm_service=llm_service,
        todo_id="todo-1",
        request_id="req-1",
        mode="rewrite",
        payload={
            "currentText": "待确认是否为权限问题，客户已提供 request_id=req-1。",
            "presetKey": "shorter",
        },
    )

    result = worker._rewrite_summary()  # noqa: SLF001

    assert result == "更短的阶段总结"
    assert len(llm_service.calls) == 1
    messages = llm_service.calls[0]["messages"]
    assert messages[0].content.startswith("你是一位阶段总结整理助手。")
    assert "不新增时间点" in messages[0].content
    assert "不允许新增事实" in messages[1].content
    assert "不要新增“今天”“昨天”“随后”“最终”等时间锚点" in messages[1].content
    assert "不确定表述必须保留" in messages[1].content
    assert "Markdown" in messages[0].content
    assert "Markdown 结构" in messages[1].content

def test_stage_summary_default_polish_preset_is_available() -> None:
    instruction = _stage_summary_rewrite_instruction("polish", "")

    assert "重新梳理" in instruction


def test_stage_summary_local_polish_fallback_preserves_markdown_text() -> None:
    current_text = (
        "### 阶段现状\n"
        "客户反馈接口偶发 500\n\n"
        "### 当前结论\n"
        "暂无明确结论\n\n"
        "### 已发生进展\n"
        "- 已收集 request_id=req-1\n"
        "- 已完成日志分析\n\n"
        "### 待确认事项\n"
        "- 待确认是否与权限有关"
    )

    rewritten = _rewrite_stage_summary_locally(current_text, "polish", "")

    assert "### 阶段现状" in rewritten
    assert "### 当前结论" in rewritten
    assert "### 已发生进展" in rewritten
    assert "### 待确认事项" in rewritten
    assert "客户反馈接口偶发 500" in rewritten


def test_stage_summary_default_rewrite_calls_llm() -> None:
    llm_service = _RecordingLLMService("重新整理后的阶段总结")
    worker = StageSummaryWorker(
        llm_service=llm_service,
        todo_id="todo-1",
        request_id="req-1",
        mode="rewrite",
        payload={
            "currentText": "原始阶段总结",
            "defaultRewrite": True,
        },
    )

    result = worker._rewrite_summary()  # noqa: SLF001

    assert result == "重新整理后的阶段总结"
    assert len(llm_service.calls) == 1
    messages = llm_service.calls[0]["messages"]
    assert "不要套固定四段模板" in messages[0].content
    assert "不要套固定模板" in messages[1].content


def test_stage_summary_rollup_prefers_server_runtime(monkeypatch) -> None:
    _RecordingStageSummaryClient.calls = []
    monkeypatch.setattr("aica.worker.ChattodoServerClient", _RecordingStageSummaryClient)
    llm_service = _RecordingLLMService("本地阶段总结")
    worker = StageSummaryWorker(
        llm_service=llm_service,
        todo_id="todo-1",
        request_id="req-1",
        mode="rollup",
        payload={"todoPayload": _build_todo()},
        server_config=ServerConfig(
            enabled=True,
            base_url="https://server.example.com",
            api_key="server-key",
        ),
    )

    result = worker._build_rollup_summary()  # noqa: SLF001

    assert result == "### 服务端阶段总结\n- 已整理当前阶段进展"
    assert llm_service.calls == []
    assert _RecordingStageSummaryClient.calls[0]["current_markdown"] == ""
    assert _RecordingStageSummaryClient.calls[0]["task_title"] == "接口调用失败"
    assert _RecordingStageSummaryClient.calls[0]["stage_name"] == "当前阶段"
    assert "客户反馈接口调用失败" in _RecordingStageSummaryClient.calls[0]["stage_materials"]
    assert "request_id=req-1" in _RecordingStageSummaryClient.calls[0]["stage_materials"]


def test_stage_summary_rewrite_sends_current_markdown_and_materials_to_server(monkeypatch) -> None:
    _RecordingStageSummaryClient.calls = []
    monkeypatch.setattr("aica.worker.ChattodoServerClient", _RecordingStageSummaryClient)
    llm_service = _RecordingLLMService("本地阶段总结")
    worker = StageSummaryWorker(
        llm_service=llm_service,
        todo_id="todo-1",
        request_id="req-1",
        mode="rewrite",
        payload={
            "currentText": "### 原阶段总结\n- 待确认权限配置",
            "presetKey": "customer",
            "todoPayload": _build_todo(),
        },
        server_config=ServerConfig(
            enabled=True,
            base_url="https://server.example.com",
            api_key="server-key",
        ),
    )

    result = worker._rewrite_summary()  # noqa: SLF001

    assert result == "### 服务端阶段总结\n- 已整理当前阶段进展"
    assert llm_service.calls == []
    assert _RecordingStageSummaryClient.calls[0]["current_markdown"] == "### 原阶段总结\n- 待确认权限配置"
    assert _RecordingStageSummaryClient.calls[0]["stage_goal"] == "把现有总结整理成更适合发给客户的表述，语气克制、清楚，弱化内部排查术语。"
    assert "客户反馈接口调用失败" in _RecordingStageSummaryClient.calls[0]["stage_materials"]


def test_stage_summary_rollup_reports_server_failure_when_server_ready(monkeypatch) -> None:
    monkeypatch.setattr("aica.worker.ChattodoServerClient", _FailingStageSummaryClient)
    llm_service = _RecordingLLMService("本地阶段总结")
    worker = StageSummaryWorker(
        llm_service=llm_service,
        todo_id="todo-1",
        request_id="req-1",
        mode="rollup",
        payload={"todoPayload": _build_todo()},
        server_config=ServerConfig(
            enabled=True,
            base_url="https://server.example.com",
            api_key="server-key",
        ),
    )

    try:
        worker._build_rollup_summary()  # noqa: SLF001
    except RuntimeError as exc:
        assert "服务端阶段总结失败" in str(exc)
        assert "server down" in str(exc)
    else:
        raise AssertionError("expected server failure")
    assert llm_service.calls == []

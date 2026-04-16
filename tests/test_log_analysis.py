from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import AppConfig, ProviderConfig, ProviderModelConfig, TaskModelBinding, TaskModelBindings
from aica.llm.service import LLMService
from aica.log_analysis_attachments import build_default_attachment_handler_registry
from aica.log_analysis_agent import DefaultLogAnalysisAgent
from aica.log_analysis_commands import format_log_analysis_focus, parse_log_analysis_command
from aica.log_analysis_consumers import TimelineLogAnalysisPresenter
from aica.log_analysis_models import CollectedEvidencePart, EvidenceBundle, InvestigationContextSummary, LogAnalysisRequest, LogAnalysisTask
from aica.models import TicketSummaryFields
from aica.todo_detail_panel import _TodoDetailBridge
from aica.todo_models import TimelineEvent, TodoConclusion, TodoItem

def _build_todo(todo_id: str = "todo-1") -> TodoItem:
    return TodoItem(
        id=todo_id,
        title="娴嬭瘯寰呭姙",
        current_summary="褰撳墠鎽樿",
        summary_fields=TicketSummaryFields(),
        conclusion=TodoConclusion(),
        timeline=[],
    )


def test_parse_log_analysis_command_extracts_focus_terms() -> None:
    command = parse_log_analysis_command("/分析日志 重点看 tradId=tx-1 request_id=req-9 和权限报错")

    assert command.trad_id == "tx-1"
    assert command.request_id == "req-9"
    assert "权限报错" in command.focus_terms
    assert format_log_analysis_focus(command) == "tradId=tx-1 / request_id=req-9 / 权限报错"


def test_llm_service_resolves_log_analysis_with_analysis_fallback() -> None:
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
            log_analysis=TaskModelBinding(),
            plan_export=TaskModelBinding(provider_id="stub", model_id="vision"),
        ),
    )

    resolved = LLMService(config).resolve_task_model("log_analysis")

    assert resolved.reference.model_id == "vision"
    assert resolved.task_name == "analysis"
    assert resolved.fallback_used is True


def test_attachment_handler_registry_collects_zip_and_text() -> None:
    registry = build_default_attachment_handler_registry()
    text_handler = registry.resolve(SimpleNamespace(name="app.log", path="C:/logs/app.log"))
    zip_handler = registry.resolve(SimpleNamespace(name="bundle.zip", path="C:/logs/bundle.zip"))
    image_handler = registry.resolve(SimpleNamespace(name="error.png", path="C:/logs/error.png"))

    assert text_handler is not None
    assert text_handler.__class__.__name__ == "TextLogAttachmentHandler"
    assert zip_handler is not None
    assert zip_handler.__class__.__name__ == "ZipAttachmentHandler"
    assert image_handler is not None
    assert image_handler.__class__.__name__ == "ImageAttachmentHandler"


def test_log_analysis_task_from_row_parses_json_payloads() -> None:
    task = LogAnalysisTask.from_row(
        {
            "id": "task-1",
            "todo_id": "todo-1",
            "timeline_entry_id": "event-1",
            "status": "queued",
            "raw_command": "/鍒嗘瀽鏃ュ織 request_id=req-1",
            "parsed_focus_json": '{"request_id":"req-1","focus_terms":["鏉冮檺鎶ラ敊"]}',
            "attachment_snapshot_json": '[{"name":"app.log","path":"C:/logs/app.log"}]',
            "investigation_context_json": '{"problem_summary":"鎺ュ彛鎶ラ敊"}',
            "evidence_bundle_json": '{"parts":[],"metadata":{"attachment_count":1}}',
            "result_summary": "",
            "result_payload_json": '{"analysis_focus":{"request_id":"req-1"}}',
            "error_message": "",
            "model_binding_used": "Stub / vision (fallback analysis)",
            "started_at": "",
            "completed_at": "",
            "failed_at": "",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
    )

    assert task.timeline_entry_id == "event-1"
    assert task.parsed_focus_json["request_id"] == "req-1"
    assert task.attachment_snapshot_json[0]["name"] == "app.log"
    assert task.evidence_bundle_json["metadata"]["attachment_count"] == 1


def test_todo_detail_bridge_add_log_analysis_entry_emits_task_request() -> None:
    bridge = _TodoDetailBridge(
        attachment_root=Path("."),
        environment_access_service=SimpleNamespace(list_project_environments=lambda _project_id: []),
    )
    bridge.set_todo(_build_todo())

    emitted: list[tuple[str, object]] = []
    bridge.logAnalysisRequested.connect(lambda todo_id, payload: emitted.append((todo_id, payload)))

    bridge.addTimelineEntry("/分析日志 request_id=req-1 和权限报错", "follow_up")

    assert bridge.timelineCount == 1
    event = bridge.timeline[0]
    assert event["kind"] == "log_analysis_command"
    assert event["type"] == "log_analysis_command"
    assert event["status"] == "running"
    assert event["taskStatus"] == "queued"
    assert event["payload"]["command_text"].startswith("/分析日志")
    assert emitted and emitted[0][0] == "todo-1"
    payload = emitted[0][1]
    assert payload["parsedFocus"]["request_id"] == "req-1"
def test_todo_detail_bridge_preserves_log_analysis_type_when_prefix_was_stripped() -> None:
    bridge = _TodoDetailBridge(
        attachment_root=Path("."),
        environment_access_service=SimpleNamespace(list_project_environments=lambda _project_id: []),
    )
    bridge.set_todo(_build_todo())

    emitted: list[tuple[str, object]] = []
    bridge.logAnalysisRequested.connect(lambda todo_id, payload: emitted.append((todo_id, payload)))

    bridge.addTimelineEntry("request_id=req-2 和权限报错", "log_analysis")

    assert bridge.timelineCount == 1
    event = bridge.timeline[0]
    assert event["kind"] == "log_analysis_command"
    assert event["scenario"] == "日志分析任务"
    assert event["taskType"] == "log_analysis"
    payload = emitted[0][1]
    assert payload["rawCommand"].startswith("/分析日志")
    assert payload["parsedFocus"]["request_id"] == "req-2"


def test_default_log_analysis_agent_prioritizes_error_and_non_200_hits() -> None:
    preview = "\n".join(
        [
            '{"time":"2026-04-13T16:14:10+08:00","level":"INFO","msg":"log_resp","status_code":200,"request_id":"14160111b60252e1870c","server_url":"/app/v1/search/gpt"}',
            '{"time":"2026-04-13T16:14:10+08:00","level":"ERROR","msg":"getAnwserFrom Aiserver error 510201 510201:涓嬫父鎺ュ彛鏁版嵁閿欒, userid is 0","request_id":"14160111b60252e1870c","pos":"service/qa_v1/query.go:359"}',
            '{"time":"2026-04-13T16:14:10+08:00","level":"ERROR","msg":"log_resp","upstream":"encs-pri-api-gateway","status_code":400,"request_id":"14160111b60252e1870c","server_url":"/v7/brands/{app}/settings"}',
            '{"time":"2026-04-13T16:14:10+08:00","level":"ERROR","msg":"GetaAppBrand unmarshal error unexpected end of JSON input","request_id":"14160111b60252e1870c"}',
        ]
    )
    request = LogAnalysisRequest(
        todo_snapshot={
            "title": "API璋冪敤澶辫触锛岃繑鍥炵姸鎬侀潪200",
            "current_summary": "客户提供 TraceId=14160111b60252e1870c，建议查日志定位具体报错原因。",
            "conclusion": "",
        },
        parsed_command=parse_log_analysis_command("/鍒嗘瀽鏃ュ織 1"),
        investigation_context=InvestigationContextSummary(
            problem_summary="客户提供 TraceId=14160111b60252e1870c，建议查日志定位具体报错原因。",
            current_focus=["TraceId=14160111b60252e1870c"],
        ),
        evidence_bundle=EvidenceBundle(
            parts=[
                CollectedEvidencePart(
                    source_name="app.log",
                    source_type="text_log",
                    summary="璇诲彇 app.log",
                    details={"preview": preview, "line_count": 4},
                )
            ]
        ),
    )

    produced = DefaultLogAnalysisAgent().analyze(request)

    findings = [item["summary"] for item in produced.result_payload.key_findings]
    assert any("HTTP 400" in item or "userid is 0" in item for item in findings)
    assert produced.result_payload.preliminary_judgment["category"] in {"请求链路问题", "下游服务异常"}
    assert produced.result_payload.problem_to_answer
    assert produced.result_payload.question_answered is True
    assert produced.result_payload.analysis_mode
    assert produced.result_payload.investigation_steps
    assert any(item.get("context_window") for item in produced.result_payload.key_findings)


def test_default_log_analysis_agent_reports_missing_info_without_identifiers() -> None:
    preview = "\n".join(
        [
            '{"time":"2026-04-13T16:14:10+08:00","level":"INFO","msg":"startup ok","status_code":200}',
            '{"time":"2026-04-13T16:14:11+08:00","level":"WARN","msg":"upstream unstable","server_url":"/foo/bar","status_code":200}',
        ]
    )
    request = LogAnalysisRequest(
        todo_snapshot={
            "title": "鎺ュ彛鍋跺彂澶辫触",
            "current_summary": "瀹㈡埛鍙嶉鎺ュ彛鍋跺彂澶辫触锛屼絾娌℃湁鎻愪緵traceId",
            "conclusion": "",
        },
        parsed_command=parse_log_analysis_command("/鍒嗘瀽鏃ュ織 閲嶇偣鐪?鎺ュ彛瓒呮椂"),
        investigation_context=InvestigationContextSummary(
            problem_summary="瀹㈡埛鍙嶉鎺ュ彛鍋跺彂澶辫触锛屼絾娌℃湁鎻愪緵traceId",
            current_focus=["鎺ュ彛瓒呮椂"],
        ),
        evidence_bundle=EvidenceBundle(
            parts=[
                CollectedEvidencePart(
                    source_name="gateway.log",
                    source_type="text_log",
                    summary="璇诲彇 gateway.log",
                    details={"preview": preview, "line_count": 2},
                )
            ]
        ),
    )

    produced = DefaultLogAnalysisAgent().analyze(request)

    assert produced.result_payload.analysis_mode in {"按上下文重点排查", "按异常聚类排查"}
    assert produced.result_payload.investigation_steps
    assert produced.result_payload.question_answered is False
    assert produced.result_payload.answer_gap_reason
    assert produced.result_payload.missing_information
    assert any("上下游日志" in item or "接口路径" in item for item in produced.result_payload.suggested_next_steps)

def test_todo_detail_bridge_exposes_structured_timeline_card_fields() -> None:
    bridge = _TodoDetailBridge(
        attachment_root=Path('.'),
        environment_access_service=SimpleNamespace(list_project_environments=lambda _project_id: []),
    )
    bridge.set_todo(_build_todo())

    bridge.addTimelineEntry('普通跟进', 'follow_up')
    bridge.addTimelineEntry('/分析日志 request_id=req-9 权限报错', 'follow_up')

    assert bridge.timeline[0]['type'] == 'log_analysis_command'
    assert bridge.timeline[0]['status'] == 'running'
    assert bridge.timeline[0]['payload']['command_text'].startswith('/分析日志')
    assert bridge.timeline[1]['type'] == 'default'
    assert bridge.timeline[1]['payload'] == {}


def test_timeline_log_analysis_presenter_produces_structured_result_event() -> None:
    request = LogAnalysisRequest(
        todo_snapshot={'title': '娴嬭瘯', 'current_summary': '娴嬭瘯', 'conclusion': ''},
        parsed_command=parse_log_analysis_command('/鍒嗘瀽鏃ュ織 request_id=req-3'),
        investigation_context=InvestigationContextSummary(problem_summary='鏉冮檺鎶ラ敊', current_focus=['request_id=req-3']),
        evidence_bundle=EvidenceBundle(),
    )
    produced = DefaultLogAnalysisAgent().analyze(request)

    event = TimelineLogAnalysisPresenter().consume(
        produced,
        SimpleNamespace(
            timeline_entry_id='cmd-1',
            task_id='task-1',
            todo_id='todo-1',
            investigation_context=request.investigation_context,
            evidence_bundle=request.evidence_bundle,
        ),
    )

    assert event.event_type == 'log_analysis_result'
    assert event.status == 'success'
    assert event.payload['source_timeline_entry_id'] == 'cmd-1'
    assert 'analyzed_materials' in event.payload
    assert 'findings' in event.payload
    assert 'judgment' in event.payload
    assert 'next_steps' in event.payload

def test_todo_detail_bridge_maps_current_step_from_task_status() -> None:
    bridge = _TodoDetailBridge(
        attachment_root=Path('.'),
        environment_access_service=SimpleNamespace(list_project_environments=lambda _project_id: []),
    )
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(
            id='cmd-1',
            kind='log_analysis_command',
            scenario='日志分析任务',
            event_type='log_analysis_command',
            content='/分析日志 request_id=req-1',
        )
    ]

    bridge.set_todo(
        todo,
        task_status_map={
            'cmd-1': {
                'taskId': 'task-1',
                'taskStatus': 'running',
                'uiStatus': 'running',
                'currentStep': '正在构建排查上下文...',
                'taskStatusLabel': '分析中',
                'taskType': 'log_analysis',
            }
        },
    )

    assert bridge.timelineCount == 1
    assert bridge.timeline[0]['payload']['current_step'] == '正在构建排查上下文...'


def test_todo_detail_bridge_hides_successful_command_when_result_exists() -> None:
    bridge = _TodoDetailBridge(
        attachment_root=Path('.'),
        environment_access_service=SimpleNamespace(list_project_environments=lambda _project_id: []),
    )
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(
            id='cmd-1',
            kind='log_analysis_command',
            scenario='日志分析任务',
            event_type='log_analysis_command',
            content='/分析日志 request_id=req-1',
        ),
        TimelineEvent(
            id='result-1',
            kind='log_analysis_result',
            scenario='日志分析结果',
            event_type='log_analysis_result',
            status='success',
            content='日志分析结果',
            payload={
                'source_timeline_entry_id': 'cmd-1',
                'analyzed_materials': [],
                'findings': '命中 request_id=req-1',
                'judgment': '权限问题',
                'next_steps': '联系研发',
            },
        ),
    ]

    bridge.set_todo(
        todo,
        task_status_map={
            'cmd-1': {
                'taskId': 'task-1',
                'taskStatus': 'completed',
                'uiStatus': 'success',
                'currentStep': '',
                'taskStatusLabel': '已完成',
                'taskType': 'log_analysis',
            }
        },
    )

    assert bridge.timelineCount == 1
    assert bridge.timeline[0]['type'] == 'log_analysis_result'
    payload = bridge._build_payload()  # noqa: SLF001
    assert payload is not None
    assert len(payload['timeline']) == 2

def test_delete_timeline_card_removes_related_log_analysis_events() -> None:
    bridge = _TodoDetailBridge(
        attachment_root=Path('.'),
        environment_access_service=SimpleNamespace(list_project_environments=lambda _project_id: []),
    )
    todo = _build_todo()
    todo.timeline = [
        TimelineEvent(
            id='cmd-1',
            kind='log_analysis_command',
            scenario='日志分析任务',
            event_type='log_analysis_command',
            content='/分析日志 request_id=req-1',
            payload={'result_event_id': 'result-1'},
        ),
        TimelineEvent(
            id='result-1',
            kind='log_analysis_result',
            scenario='日志分析结果',
            event_type='log_analysis_result',
            status='success',
            content='日志分析结果',
            payload={
                'source_timeline_entry_id': 'cmd-1',
                'analyzed_materials': [],
                'findings': '命中 request_id=req-1',
                'judgment': '权限问题',
                'next_steps': '联系研发',
            },
        ),
    ]
    bridge.set_todo(todo)

    bridge.deleteTimelineCard('result-1')

    assert bridge.timelineCount == 0
    payload = bridge._build_payload()  # noqa: SLF001
    assert payload is not None
    assert payload['timeline'] == []

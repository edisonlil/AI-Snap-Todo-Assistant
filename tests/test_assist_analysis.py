from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.todo.assist_analysis import (  # noqa: E402
    build_assist_todo_payload,
    should_update_assist_analysis,
)
from aica.error_codes import ErrorCodeLookupService  # noqa: E402
from aica.storage.sqlite.error_code_repository import ErrorCodeRecord, SQLiteErrorCodeRepository  # noqa: E402
from aica.case_search import CaseSearchItem, CaseSearchResult  # noqa: E402
from aica.models import TicketSummaryFields  # noqa: E402
from aica.todo.models import TodoItem  # noqa: E402
from aica.worker import AssistAnalysisWorker  # noqa: E402
import tempfile


class _LLM:
    def run_task(self, task_name: str, *, messages, temperature: float = 0.2, **_kwargs):  # noqa: ANN001
        return (
            '{"summary":"LLM 第一版建议",'
            '"informationStatus":{"recognized":"已识别到环境差异","checkedDirections":[{"title":"demo 已验证","evidence":"demo 正常"}]},'
            '"missingSupplement":{"directions":[{"title":"生产参数","reason":"用于对比差异"}]},'
            '"upgradeSuggestion":{"decision":"暂不建议升级","reason":"证据仍不完整"}}'
        )


class _FastLLM:
    def run_task(self, task_name: str, *, messages, temperature: float = 0.2, **_kwargs):  # noqa: ANN001
        return (
            '{"summary":"Fast summary",'
            '"informationStatus":{"recognized":"recognized","checkedDirections":[{"title":"known","evidence":"demo ok"}]},'
            '"missingSupplement":{"directions":[{"title":"params","reason":"need compare"}]},'
            '"upgradeSuggestion":{"decision":"wait","reason":"need logs"}}'
        )


class _FailingCaseProvider:
    def search_many(self, queries):  # noqa: ANN001
        raise RuntimeError("case search down")


class _ExplodingQueryLLM(_LLM):
    def run_task(self, task_name: str, *, messages, temperature: float = 0.2, **_kwargs):  # noqa: ANN001
        if task_name == "context_summary":
            return super().run_task(task_name, messages=messages, temperature=temperature, **_kwargs)
        raise AssertionError("case query rewrite should stay disabled by default")


class _SuccessfulCaseProvider:
    def search_many(self, queries):  # noqa: ANN001
        return CaseSearchResult(
            status="success",
            count_label="1 result",
            items=[CaseSearchItem(title="Case A", score=81)],
        )


class _SignalRecorder:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def emit(self, _todo_id: str, _request_id: str, payload: object) -> None:
        self.items.append(dict(payload))


def _todo() -> TodoItem:
    return TodoItem(
        id="todo-1",
        title="测试待办",
        current_summary="当前摘要",
        summary_fields=TicketSummaryFields(),
    )


def test_assist_analysis_review_requires_clear_improvement() -> None:
    previous = {
        "summary": "第一版建议",
        "caseResults": {"items": [{"title": "案例 A", "score": 72}]},
    }
    same_quality = {
        "summary": "第一版建议换一种说法",
        "caseResults": {"items": [{"title": "案例 A", "score": 73}]},
    }
    better = {
        "summary": "第二版补充了更具体的环境对比和日志排查建议",
        "informationStatus": {
            "recognized": "已识别到环境差异",
            "checkedDirections": [{"title": "demo 已验证", "evidence": "demo 正常"}],
        },
        "missingSupplement": {
            "directions": [{"title": "生产请求参数", "reason": "用于核对参数差异"}],
        },
        "upgradeSuggestion": {"decision": "暂不建议升级", "reason": "证据链仍不完整"},
        "caseResults": {"items": [{"title": "案例 B", "score": 88}]},
    }

    assert should_update_assist_analysis(previous, same_quality) is False
    assert should_update_assist_analysis(previous, better) is True


def test_initial_assist_analysis_keeps_llm_result_when_case_search_fails() -> None:
    todo = _todo()
    worker = AssistAnalysisWorker(
        llm_service=_LLM(),
        todo_id=todo.id,
        request_id="req-1",
        payload={"todoPayload": build_assist_todo_payload(todo)},
        case_search_provider=_FailingCaseProvider(),
    )

    result = worker._build_initial_result(todo)  # noqa: SLF001

    assert result["summary"] == "LLM 第一版建议"
    assert result["caseResults"]["status"] == "error"
    assert "case search down" in result["caseResults"]["errorMessage"]


def test_initial_assist_analysis_disables_case_search_by_default() -> None:
    todo = _todo()
    worker = AssistAnalysisWorker(
        llm_service=_ExplodingQueryLLM(),
        todo_id=todo.id,
        request_id="req-default",
        payload={"todoPayload": build_assist_todo_payload(todo)},
    )

    result = worker._build_initial_result(todo)  # noqa: SLF001

    assert result["summary"] == "LLM 第一版建议"
    assert result["caseResults"]["status"] == "empty"
    assert result["caseResults"]["items"] == []


def test_assist_analysis_worker_emits_partial_result_before_case_search_finishes() -> None:
    todo = _todo()
    worker = AssistAnalysisWorker(
        llm_service=_FastLLM(),
        todo_id=todo.id,
        request_id="req-2",
        payload={"todoPayload": build_assist_todo_payload(todo)},
        case_search_provider=_SuccessfulCaseProvider(),
    )
    recorder = _SignalRecorder()
    worker.result_ready = recorder

    worker.run()

    assert len(recorder.items) == 2
    assert recorder.items[0]["isFinal"] is False
    assert recorder.items[0]["summary"] == "Fast summary"
    assert recorder.items[0]["caseResults"]["status"] == "loading"
    assert recorder.items[1]["isFinal"] is True
    assert recorder.items[1]["summary"] == "Fast summary"
    assert recorder.items[1]["caseResults"]["status"] != "loading"


def test_initial_assist_analysis_includes_error_code_results_when_case_search_fails() -> None:
    todo = TodoItem(
        id="todo-1",
        title="文档中台错误",
        current_summary="用户反馈错误码 15041",
        summary_fields=TicketSummaryFields(),
    )
    repository = SQLiteErrorCodeRepository(Path(tempfile.mkdtemp()) / "aica.db")
    repository.upsert_many(
        [
            ErrorCodeRecord(
                code="15041",
                title="EditNoAvailableWpsService",
                message="文字组件服务所有节点均已下线",
                meaning="无可用服务节点",
                suggestion="检查 editserver 节点状态",
                source_name="文档中台错误码说明",
            )
        ]
    )
    worker = AssistAnalysisWorker(
        llm_service=_LLM(),
        todo_id=todo.id,
        request_id="req-3",
        payload={"todoPayload": build_assist_todo_payload(todo)},
        case_search_provider=_FailingCaseProvider(),
        error_code_lookup_service=ErrorCodeLookupService(repository=repository),
    )

    result = worker._build_initial_result(todo)  # noqa: SLF001

    assert result["caseResults"]["status"] == "error"
    assert result["errorCodeResults"]["status"] == "success"
    assert result["errorCodeResults"]["items"][0]["code"] == "15041"

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.assist_analysis import (  # noqa: E402
    build_assist_todo_payload,
    should_update_assist_analysis,
)
from aica.models import TicketSummaryFields  # noqa: E402
from aica.todo_models import TodoItem  # noqa: E402
from aica.worker import AssistAnalysisWorker  # noqa: E402


class _LLM:
    def run_task(self, task_name: str, *, messages, temperature: float = 0.2, **_kwargs):  # noqa: ANN001
        return (
            '{"summary":"LLM 第一版建议",'
            '"informationStatus":{"recognized":"已识别到环境差异","checkedDirections":[{"title":"demo 已验证","evidence":"demo 正常"}]},'
            '"missingSupplement":{"directions":[{"title":"生产参数","reason":"用于对比差异"}]},'
            '"upgradeSuggestion":{"decision":"暂不建议升级","reason":"证据仍不完整"}}'
        )


class _FailingCaseProvider:
    def search_many(self, queries):  # noqa: ANN001
        raise RuntimeError("case search down")


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
        "informationStatus": {"recognized": "已识别到环境差异", "checkedDirections": [{"title": "demo 已验证", "evidence": "demo 正常"}]},
        "missingSupplement": {"directions": [{"title": "生产请求参数", "reason": "用于核对参数差异"}]},
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

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSummaryFields
from aica.config import ServerConfig
from aica.ticket_enrichment import (
    ChattodoFeaturePointProvider,
    ChattodoRootCauseProvider,
    RootCauseResult,
    TicketEnrichmentService,
    build_ticket_enrichment_job,
    is_ticket_enrichment_job_still_current,
    merge_async_enrichment_fields,
)
from aica.todo.models import TodoConclusion, TodoItem


class _FeaturePointSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> object:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _FeaturePointResponse(
            {
                "answer": "自动功能点",
                "trace_id": "trace_001",
                "usage": {"total_tokens": 10},
            }
        )


class _FeaturePointResponse:
    status_code = 200
    text = ""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload


class _FeaturePointProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def resolve(self, *, issue_product: str, problem_desc: str):  # noqa: ANN201
        self.calls.append({"issue_product": issue_product, "problem_desc": problem_desc})
        return SimpleFeaturePointResult("自动功能点")


class SimpleFeaturePointResult:
    def __init__(self, value: str) -> None:
        self.value = value
        self.error_message = ""


class _RootCauseSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> object:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _FeaturePointResponse(
            {
                "answer": (
                    "{\n"
                    '  "root_cause_description": "服务节点下线导致创建失败",\n'
                    '  "root_cause_category": "环境问题/服务器宕机"\n'
                    "}"
                ),
                "trace_id": "trace_001",
            }
        )


class _RootCauseProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def generate(self, *, problem_desc: str, conclusion: str) -> RootCauseResult:
        self.calls.append({"problem_desc": problem_desc, "conclusion": conclusion})
        return RootCauseResult(
            description="服务节点下线导致创建失败",
            category="环境问题/服务器宕机",
        )


def _build_todo(
    *,
    todo_id: str = "todo-1",
    current_summary: str = "现象描述",
    product_line: str = "产品线A",
    issue_product: str = "产品A/模块B/功能C",
    conclusion: str = "定位到配置缺失",
    feature_point: str = "",
    feature_point_source: str = "",
    root_cause_desc: str = "",
    root_cause_desc_source: str = "",
    root_cause: str = "",
    root_cause_source: str = "",
) -> TodoItem:
    return TodoItem(
        id=todo_id,
        title="测试待办",
        current_summary=current_summary,
        summary_fields=TicketSummaryFields(
            product_line=product_line,
            issue_product=issue_product,
            feature_point=feature_point,
            feature_point_source=feature_point_source,
            root_cause_desc=root_cause_desc,
            root_cause_desc_source=root_cause_desc_source,
            root_cause=root_cause,
            root_cause_source=root_cause_source,
        ),
        conclusion=TodoConclusion(content=conclusion),
        timeline=[],
    )


def test_ticket_enrichment_job_detects_stale_saved_context() -> None:
    previous = _build_todo(current_summary="旧描述", conclusion="")
    current = _build_todo(current_summary="新描述", conclusion="新结论", product_line="产品线B")
    job = build_ticket_enrichment_job(previous_todo=previous, current_todo=current)

    assert is_ticket_enrichment_job_still_current(current, job) is True

    changed_summary = _build_todo(current_summary="又改了描述", conclusion="新结论", product_line="产品线B")
    assert is_ticket_enrichment_job_still_current(changed_summary, job) is False

    changed_conclusion = _build_todo(current_summary="新描述", conclusion="又改了结论", product_line="产品线B")
    assert is_ticket_enrichment_job_still_current(changed_conclusion, job) is False

    changed_product_line = _build_todo(current_summary="新描述", conclusion="新结论", product_line="产品线C")
    assert is_ticket_enrichment_job_still_current(changed_product_line, job) is False


def test_merge_async_enrichment_fields_preserves_manual_overrides() -> None:
    current_fields = TicketSummaryFields(
        product_line="产品线A",
        feature_point="手动功能点",
        feature_point_source="manual",
        root_cause_desc="手动根因描述",
        root_cause_desc_source="manual",
        root_cause="手动根因分类",
        root_cause_source="manual",
    )
    enriched_fields = TicketSummaryFields(
        product_line="产品线A",
        feature_point="自动功能点",
        feature_point_source="auto",
        root_cause_desc="自动根因描述",
        root_cause_desc_source="auto",
        root_cause="自动根因分类",
        root_cause_source="auto",
    )

    merged = merge_async_enrichment_fields(
        current_fields=current_fields,
        enriched_fields=enriched_fields,
    )

    assert merged.feature_point == "手动功能点"
    assert merged.feature_point_source == "manual"
    assert merged.root_cause_desc == "手动根因描述"
    assert merged.root_cause_desc_source == "manual"
    assert merged.root_cause == "手动根因分类"
    assert merged.root_cause_source == "manual"


def test_merge_async_enrichment_fields_applies_auto_values_when_fields_are_not_manual() -> None:
    current_fields = TicketSummaryFields(
        product_line="产品线A",
        feature_point="",
        feature_point_source="",
        root_cause_desc="",
        root_cause_desc_source="",
        root_cause="",
        root_cause_source="",
    )
    enriched_fields = TicketSummaryFields(
        product_line="产品线A",
        feature_point="自动功能点",
        feature_point_source="auto",
        root_cause_desc="自动根因描述",
        root_cause_desc_source="auto",
        root_cause="自动根因分类",
        root_cause_source="auto",
    )

    merged = merge_async_enrichment_fields(
        current_fields=current_fields,
        enriched_fields=enriched_fields,
    )

    assert merged.feature_point == "自动功能点"
    assert merged.feature_point_source == "auto"
    assert merged.root_cause_desc == "自动根因描述"
    assert merged.root_cause_desc_source == "auto"
    assert merged.root_cause == "自动根因分类"
    assert merged.root_cause_source == "auto"


def test_chattodo_feature_point_provider_uses_workflow_answer(monkeypatch) -> None:  # noqa: ANN001
    session = _FeaturePointSession()

    monkeypatch.setattr(
        "aica.server_api.requests.Session",
        lambda: session,
    )
    provider = ChattodoFeaturePointProvider(
        ServerConfig(
            enabled=True,
            base_url="https://server.example.com/",
            api_key="server-key",
            timeout_seconds=20,
        )
    )

    result = provider.resolve(issue_product="产品A/模块A/功能A", problem_desc="用户反馈无法保存")

    assert result.value == "自动功能点"
    assert result.matched is True
    assert result.provider_name == "chattodo"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/workflow-mphzwo1h/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "product_line": "产品A/模块A/功能A",
            "desc": "用户反馈无法保存",
        }
    }


def test_chattodo_root_cause_provider_uses_single_turn_answer(monkeypatch) -> None:  # noqa: ANN001
    session = _RootCauseSession()

    monkeypatch.setattr(
        "aica.server_api.requests.Session",
        lambda: session,
    )
    provider = ChattodoRootCauseProvider(
        ServerConfig(
            enabled=True,
            base_url="https://server.example.com/",
            api_key="server-key",
            timeout_seconds=20,
        )
    )

    result = provider.generate(problem_desc="问题描述", conclusion="问题结论")

    assert result.description == "服务节点下线导致创建失败"
    assert result.category == "环境问题/服务器宕机"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/single-turn-mpkqa7ch/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "task_desc": "问题描述",
            "answer": "问题结论",
        }
    }


def test_ticket_enrichment_refreshes_feature_point_for_newly_saved_ticket() -> None:
    provider = _FeaturePointProvider()
    service = TicketEnrichmentService(feature_point_provider=provider)
    todo = _build_todo(
        current_summary="保存后自动匹配",
        product_line="产品线A",
        issue_product="产品A/模块A/功能A",
        feature_point="",
    )

    outcome = service.enrich_for_update(
        previous_fields=todo.summary_fields,
        current_fields=todo.summary_fields,
        previous_problem_desc=todo.current_summary,
        current_problem_desc=todo.current_summary,
        previous_conclusion=todo.conclusion.content,
        current_conclusion=todo.conclusion.content,
    )

    assert provider.calls == [{"issue_product": "产品A/模块A/功能A", "problem_desc": "保存后自动匹配"}]
    assert outcome.summary_fields.feature_point == "自动功能点"
    assert outcome.summary_fields.feature_point_source == "auto"


def test_ticket_enrichment_uses_root_cause_provider_without_local_generation() -> None:
    provider = _RootCauseProvider()
    service = TicketEnrichmentService(root_cause_provider=provider)

    outcome = service.enrich_for_update(
        previous_fields=TicketSummaryFields(
            product_line="product",
            root_cause_desc="manual desc",
            root_cause_desc_source="manual",
            root_cause="manual cause",
            root_cause_source="manual",
        ),
        current_fields=TicketSummaryFields(
            product_line="product",
            root_cause_desc="manual desc",
            root_cause_desc_source="manual",
            root_cause="manual cause",
            root_cause_source="manual",
        ),
        previous_problem_desc="problem desc",
        current_problem_desc="problem desc",
        previous_conclusion="old conclusion",
        current_conclusion="new conclusion",
    )

    assert provider.calls == [{"problem_desc": "problem desc", "conclusion": "new conclusion"}]
    assert outcome.summary_fields.root_cause_desc == "服务节点下线导致创建失败"
    assert outcome.summary_fields.root_cause_desc_source == "auto"
    assert outcome.summary_fields.root_cause == "环境问题/服务器宕机"
    assert outcome.summary_fields.root_cause_source == "auto"

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.case_search import (
    CaseSearchItem,
    CaseSearchQuery,
    CaseSearchRequest,
    KDocsSseCaseSearchProvider,
    build_case_search_queries,
    parse_kdocs_sse_lines,
)


class _LLM:
    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def run_task(self, task_name: str, *, messages, temperature: float = 0.1, **_kwargs):  # noqa: ANN001
        self.calls.append({"task_name": task_name, "messages": list(messages), "temperature": temperature})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_case_query_rewrite_uses_llm_queries() -> None:
    request = CaseSearchRequest(
        title="文档预览异常",
        current_summary="客户反馈移动端鉴权 token 没带到中台",
        timeline_text="- 已提供截图\n- demo 正常，生产异常",
    )
    llm = _LLM('[{"query":"移动端鉴权 token 未带到中台 排查","reason":"核心现象"},{"query":"生产 demo 鉴权 token 差异","reason":"环境差异"}]')

    queries = build_case_search_queries(llm, request)

    assert [item.query for item in queries] == [
        "移动端鉴权 token 未带到中台 排查",
        "生产 demo 鉴权 token 差异",
    ]
    assert llm.calls[0]["task_name"] == "context_summary"


def test_case_query_rewrite_falls_back_to_current_summary_when_llm_unavailable() -> None:
    request = CaseSearchRequest(
        title="标题兜底",
        current_summary="客户反馈打开文档空白",
        timeline_text="- 已收集日志",
    )

    queries = build_case_search_queries(_LLM(RuntimeError("no model")), request)

    assert queries == [CaseSearchQuery(query="客户反馈打开文档空白", reason="当前问题描述")]


def test_parse_kdocs_sse_lines_extracts_recall_content() -> None:
    lines = [
        "event:message",
        'data:{"code":100000,"data":{"recall_content":[{"file_meta":{"fname":"2093562 移动端鉴权token未带到中台.otl","link_url":"https://www.kdocs.cn/l/case1","drive_info":{"name":"产品技术服务知识库"},"pages":[{"paragraphs":[{"content":"正常打开时 cookies 和 headers 都有鉴权 token"},{"content":"异常时 token 未透传到中台"}]}]}}]}}',
    ]

    items = parse_kdocs_sse_lines(lines)

    assert len(items) == 1
    assert items[0].title == "2093562 移动端鉴权token未带到中台.otl"
    assert items[0].detail_url == "https://www.kdocs.cn/l/case1"
    assert "token 未透传" in items[0].desc
    assert items[0].source == "产品技术服务知识库"


def test_parse_kdocs_sse_lines_uses_answer_text_when_no_recall_content() -> None:
    lines = [
        "data:not-json",
        'data:{"code":100000,"data":{"dynamic":{"answer_citations":[{"type":"thinking","text":"不要展示"},{"type":"answer_gen","text":"建议补充 request_id。"}]}}}',
    ]

    items = parse_kdocs_sse_lines(lines)

    assert len(items) == 1
    assert items[0].title == "智能问答结果"
    assert "建议补充 request_id" in items[0].desc
    assert "不要展示" not in items[0].text


def test_kdocs_provider_merges_dedupes_and_tolerates_single_query_failure() -> None:
    class _Provider(KDocsSseCaseSearchProvider):
        def _search_one(self, query: str) -> list[CaseSearchItem]:
            if query == "bad":
                raise RuntimeError("boom")
            return [
                CaseSearchItem(title="案例A", desc=query, detail_url="https://www.kdocs.cn/l/a"),
                CaseSearchItem(title="案例A重复", desc=query, detail_url="https://www.kdocs.cn/l/a"),
                CaseSearchItem(title=f"案例{query}", desc=query, detail_url=f"https://www.kdocs.cn/l/{query}"),
            ]

    result = _Provider(max_results=5).search_many(
        [
            CaseSearchQuery("one"),
            CaseSearchQuery("bad"),
            CaseSearchQuery("two"),
        ]
    )

    assert result.status == "success"
    assert len(result.items) == 3
    assert [item.detail_url for item in result.items].count("https://www.kdocs.cn/l/a") == 1

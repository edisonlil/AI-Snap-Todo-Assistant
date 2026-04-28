"""Case-search providers for assist troubleshooting."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import json
import re
import time
import uuid
from typing import Iterable, Protocol

import requests

from aica.llm.types import Message
from aica.text_sanitize import sanitize_text


@dataclass(frozen=True)
class CaseSearchRequest:
    todo_id: str = ""
    title: str = ""
    current_summary: str = ""
    timeline_text: str = ""


@dataclass(frozen=True)
class CaseSearchQuery:
    query: str
    reason: str = ""


@dataclass(frozen=True)
class CaseSearchItem:
    title: str
    desc: str = ""
    text: str = ""
    detail_url: str = ""
    source: str = ""

    def to_payload(self) -> dict[str, str]:
        return {
            "title": self.title,
            "desc": self.desc,
            "text": self.text or self.desc or self.title,
            "detailUrl": self.detail_url,
            "source": self.source,
        }


@dataclass(frozen=True)
class CaseSearchResult:
    status: str = "empty"
    title: str = "相似案例"
    count_label: str = "暂无案例"
    items: list[CaseSearchItem] = field(default_factory=list)
    error_message: str = ""

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "title": self.title,
            "countLabel": self.count_label,
            "count": self.count_label,
            "emptyText": "正在检索相似案例..." if self.status == "loading" else "暂无案例",
            "items": [item.to_payload() for item in self.items],
            "errorMessage": self.error_message,
        }


class CaseSearchProvider(Protocol):
    def search_many(self, queries: list[CaseSearchQuery]) -> CaseSearchResult:
        """Search case results from one or more rewritten queries."""


class NullCaseSearchProvider:
    def search_many(self, queries: list[CaseSearchQuery]) -> CaseSearchResult:
        return empty_case_result()


def loading_case_result() -> CaseSearchResult:
    return CaseSearchResult(status="loading", count_label="检索中")


def empty_case_result(*, error_message: str = "") -> CaseSearchResult:
    return CaseSearchResult(
        status="error" if error_message else "empty",
        count_label="暂无案例",
        error_message=error_message,
    )


_KDOCS_COOKIE = (
    "Hm_lvt_cb2fa0997df4ff8e739c666ee2487fd9=1763351581; "
    "weboffice_device_id=76cca76cc70a48fa469994f00c944e40; wps_endcloud=1; "
    "userInNewLayout=true; _ku=1; cid=41000207; coa_id=0; uid=1762364959; "
    "wps_sid=V02ShP185CfUvMT6-yIzdzg4htzCMsg00a22337700690b8e1f; "
    "kso-wx-quick-login=315; lang=zh-CN; xsr-diffversion=3; "
    "tfstk=gFlq-fVcYIdVjiKn82VwUfPCYYVYG5-BjfZ_SV0gloq0mPfoUmm3cjZjSlkaqPUs1SVjS1oz2fMb5ELZbVnU5o0XHAPZxDz_mKmYE44a8r40nRXR2xhOHRhZW1ziScLYfEpSkqFTsHtI_BgxkH6jjCK7sF0u1PJBvbDIkqFOyDz139uv_ExNFrVij72uRrPgoo2Dzz4Lqs4Gi5qkzPEussfGsgjuRPWgS-mirUzTqlVgscVkzPEuj5ViMnrgA_zUnEulUYm61uy4xqqP_qhzo-Wxou5Gsbk03kAa41fiaruiuFpRTdZnpowQb0A5g5uu70yI3H5qbV0KI8lNmEinqAogyYKNQkkilvHgUEAmzSr4UrwV7tVqImhaHx79J4Vm2vELnLK8zjGQQkePqn0Szo2EQmtRsoMEr0yINg1Qtvnr_JVh4OsTr4WZ6xSGQ-48zkTyziJjhHyoJuYFBOexezrBkEBOB-48zkTyzOBTHWUzAELA.; "
    "_c_WBKFRo=qq1dzIYrRg9wYFGDVSGiATzLAiO9eRoRrxGQl6g2; exp=259200; "
    "weboffice_cdn=19; "
    "cv=krXjrp5O31wAz9zBptfaXMj5RfJd6zzyahHzL1FLuUGTgaH-tlxgmZs9pNBk_7r2GAPmTp9a.RELmr9fagmS; "
    "kso_sid=TKS-f0fpeN_8Kx79EigP0poTTKS7fKoAKQKSdpWewrTeA-orTJE1gZr8SIEFxpR7Se0odC5uXeNt1zogOfYqA7oBN9kyIeopTp-SVXzkJj-GxPgiI9NeOf78eRIyy0IJRf0pR9IzRz1eQOOjVo1I-KN_Krr6.n6NX740WSg6OIM6Cj6pKKCldjdHljZ6WyoCyhG03Bdjbm_5Hle5Shs8XPs67JxFWHKuApi87o_idkAlwxqYz1r; "
    "nexp=129600; env=prod_rc; visitorid=718999236; "
    "csrf=5p2QN8KKX8ahnM6AaJzewaFSiHthwrZc; swi_acc_redirect_limit=0; "
    "wpsua=V1BTVUEvMS4wICh3ZWIta2RvY3M6Q2hyb21lXzE0Ny4wLjAuMDsgd2luZG93czpXaW5kb3dzIDEwLjA7IG8tSDNCQjVDUUVlNTlMS0UtUEdWb1E9PTpRMmh5YjIxbElDQXhORGN1TUM0d0xqQT0pIENocm9tZS8xNDcuMC4wLjA=; "
    "region=hwy"
)


class KDocsSseCaseSearchProvider:
    _ENDPOINT = "https://365.kdocs.cn/insight/api/app/v1/search/gpt"
    _SESSION_ID = "5h2nsCzjoPggL1DsuHVWxXhR"
    _DRIVE_ID = "2343012230"
    _GROUP_NAME = "产品技术服务知识库"

    def __init__(
        self,
        *,
        timeout_seconds: int = 25,
        max_queries: int = 3,
        max_results: int = 5,
        session_factory=requests.Session,
    ) -> None:
        self._timeout_seconds = max(1, int(timeout_seconds))
        self._max_queries = max(1, int(max_queries))
        self._max_results = max(1, int(max_results))
        self._session_factory = session_factory

    def search_many(self, queries: list[CaseSearchQuery]) -> CaseSearchResult:
        normalized_queries = [
            query for query in queries[: self._max_queries]
            if sanitize_text(query.query).strip()
        ]
        if not normalized_queries:
            return empty_case_result()

        results: list[CaseSearchItem] = []
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=min(len(normalized_queries), self._max_queries)) as executor:
            futures = [executor.submit(self._search_one, query.query) for query in normalized_queries]
            for future in as_completed(futures):
                try:
                    results.extend(future.result())
                except Exception as exc:  # noqa: BLE001
                    errors.append(str(exc))

        deduped = _dedupe_case_items(results)[: self._max_results]
        if deduped:
            return CaseSearchResult(
                status="success",
                count_label=f"检索 {len(deduped)} 条结果",
                items=deduped,
            )
        if errors:
            return empty_case_result(error_message="; ".join(errors[:2]))
        return empty_case_result()

    def _search_one(self, query: str) -> list[CaseSearchItem]:
        session = self._session_factory()
        try:
            response = session.post(
                self._ENDPOINT,
                headers=self._headers(),
                json=self._payload(query),
                stream=True,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            return parse_kdocs_sse_lines(response.iter_lines(decode_unicode=True))
        finally:
            close = getattr(session, "close", None)
            if callable(close):
                close()

    def _headers(self) -> dict[str, str]:
        return {
            "accept": "text/event-stream",
            "content-type": "application/json",
            "origin": "https://365.kdocs.cn",
            "referer": f"https://365.kdocs.cn/wiki/l/0sfGPFcL/qa/?sessionId={self._SESSION_ID}",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36 Edg/147.0.0.0"
            ),
            "x-docqa-client-type": "wiki-webwin",
            "x-docqa-id": "aidocs_standard",
            "cookie": _KDOCS_COOKIE,
        }

    def _payload(self, query: str) -> dict[str, object]:
        return {
            "action": "qa",
            "request_id": f"kg-qa-app_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}",
            "session_id": self._SESSION_ID,
            "searchname": sanitize_text(query).strip(),
            "query_source": "user_input",
            "use_web_search": False,
            "switch_markdown": True,
            "switch_thinking": True,
            "no_cache": False,
            "scene": "group_view",
            "trigger_scene": "wiki",
            "disable_reference": False,
            "resources": [],
            "product_name": "saas_knowledgebase_web",
            "intention_code": "saas_knowledgebase_session",
            "qa_drive_ids": [self._DRIVE_ID],
            "scope": "default",
            "qa_group_names": [self._GROUP_NAME],
        }


def build_case_search_request(todo_id: str, title: str, current_summary: str, timeline_lines: list[str]) -> CaseSearchRequest:
    return CaseSearchRequest(
        todo_id=sanitize_text(todo_id).strip(),
        title=sanitize_text(title).strip(),
        current_summary=sanitize_text(current_summary).strip(),
        timeline_text="\n".join(sanitize_text(line).strip() for line in timeline_lines if sanitize_text(line).strip()),
    )


def build_case_search_queries(llm_service: object, request: CaseSearchRequest) -> list[CaseSearchQuery]:
    fallback = _fallback_case_search_queries(request)
    if not fallback:
        return []
    try:
        raw = llm_service.run_task(
            "context_summary",
            messages=[
                Message(role="system", content=_QUERY_REWRITE_SYSTEM_PROMPT),
                Message(role="user", content=_build_query_rewrite_prompt(request)),
            ],
            temperature=0.1,
        )
        queries = _parse_query_rewrite_response(raw)
        return queries[:3] or fallback
    except Exception:
        return fallback


_QUERY_REWRITE_SYSTEM_PROMPT = (
    "你是技术支持知识库检索 query 改写助手。"
    "只能基于输入的摘要和时间线事实生成检索 query，不得新增事实、猜测根因或扩展错误码。"
    "输出 JSON 数组，每项包含 query 和 reason。"
)


def _build_query_rewrite_prompt(request: CaseSearchRequest) -> str:
    payload = {
        "title": request.title,
        "current_summary": request.current_summary,
        "timeline": request.timeline_text,
    }
    return (
        "请生成 2-3 条中文知识库检索 query，用于查找历史案例、相似问题、处理结论。\n"
        "只输出 JSON 数组，例如：[{\"query\":\"...\",\"reason\":\"...\"}]。\n\n"
        f"待办上下文：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _fallback_case_search_queries(request: CaseSearchRequest) -> list[CaseSearchQuery]:
    query = sanitize_text(request.current_summary).strip() or sanitize_text(request.title).strip()
    return [CaseSearchQuery(query=query, reason="当前问题描述")] if query else []


def _parse_query_rewrite_response(raw: str) -> list[CaseSearchQuery]:
    text = sanitize_text(raw).strip()
    if text.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        data = json.loads(text[start:end + 1])
    else:
        data = json.loads(text)
    queries: list[CaseSearchQuery] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                query = sanitize_text(item.get("query")).strip()
                reason = sanitize_text(item.get("reason")).strip()
            else:
                query = sanitize_text(item).strip()
                reason = ""
            if query and query not in {existing.query for existing in queries}:
                queries.append(CaseSearchQuery(query=query, reason=reason))
            if len(queries) >= 3:
                break
    return queries


def parse_kdocs_sse_lines(lines: Iterable[object]) -> list[CaseSearchItem]:
    items: list[CaseSearchItem] = []
    answer_parts: list[str] = []
    for raw_line in lines:
        line = raw_line.decode("utf-8", errors="ignore") if isinstance(raw_line, bytes) else str(raw_line or "")
        line = line.strip()
        if not line.startswith("data:"):
            continue
        try:
            envelope = json.loads(line[5:].strip())
        except ValueError:
            continue
        data = envelope.get("data") if isinstance(envelope, dict) else None
        if not isinstance(data, dict):
            continue
        items.extend(_items_from_recall_content(data.get("recall_content")))
        answer_parts.extend(_answer_parts_from_dynamic(data.get("dynamic")))

    deduped = _dedupe_case_items(items)
    if deduped:
        return deduped
    answer = sanitize_text("".join(answer_parts)).strip()
    if not answer:
        return []
    return [
        CaseSearchItem(
            title="智能问答结果",
            desc=_truncate(answer, 180),
            text=f"【相似案例】{answer}",
            source="KDocs",
        )
    ]


def _items_from_recall_content(value: object) -> list[CaseSearchItem]:
    if not isinstance(value, list):
        return []
    results: list[CaseSearchItem] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        file_meta = item.get("file_meta")
        if not isinstance(file_meta, dict):
            continue
        title = sanitize_text(file_meta.get("fname")).strip()
        if not title:
            continue
        detail_url = sanitize_text(file_meta.get("link_url")).strip()
        source = _extract_source_name(file_meta)
        desc = _truncate(" ".join(_paragraph_texts(file_meta.get("pages"))), 220)
        text_parts = [f"【相似案例】{title}"]
        if desc:
            text_parts.append(desc)
        if detail_url:
            text_parts.append(f"详情：{detail_url}")
        results.append(
            CaseSearchItem(
                title=title,
                desc=desc or "知识库召回相似案例",
                text="\n".join(text_parts),
                detail_url=detail_url,
                source=source,
            )
        )
    return results


def _extract_source_name(file_meta: dict[str, object]) -> str:
    drive_info = file_meta.get("drive_info")
    if isinstance(drive_info, dict):
        return sanitize_text(drive_info.get("name")).strip()
    return "KDocs"


def _paragraph_texts(pages: object) -> list[str]:
    texts: list[str] = []
    if not isinstance(pages, list):
        return texts
    for page in pages:
        if not isinstance(page, dict):
            continue
        paragraphs = page.get("paragraphs")
        if not isinstance(paragraphs, list):
            continue
        for paragraph in paragraphs:
            if not isinstance(paragraph, dict):
                continue
            content = sanitize_text(paragraph.get("content")).strip()
            if content:
                texts.append(content)
    return texts


def _answer_parts_from_dynamic(dynamic: object) -> list[str]:
    if not isinstance(dynamic, dict):
        return []
    citations = dynamic.get("answer_citations")
    if not isinstance(citations, list):
        return []
    parts: list[str] = []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        if sanitize_text(citation.get("type")).strip() != "answer_gen":
            continue
        text = sanitize_text(citation.get("text")).strip()
        if text:
            parts.append(text)
    return parts


def _dedupe_case_items(items: list[CaseSearchItem]) -> list[CaseSearchItem]:
    deduped: list[CaseSearchItem] = []
    seen: set[str] = set()
    for item in items:
        key = (item.detail_url or item.title).strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _truncate(value: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", sanitize_text(value)).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"

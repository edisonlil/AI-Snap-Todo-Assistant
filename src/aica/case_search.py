"""Case-search helpers for assist troubleshooting."""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from aica.text_sanitize import sanitize_text

MIN_CASE_MATCH_SCORE = 50


@dataclass(frozen=True)
class CaseSearchRequest:
    todo_id: str = ""
    title: str = ""
    current_summary: str = ""
    timeline_text: str = ""
    function_point: str = ""


@dataclass(frozen=True)
class CaseSearchItem:
    title: str
    desc: str = ""
    text: str = ""
    detail_url: str = ""
    source: str = ""
    score: int = 0
    score_label: str = ""
    match_reason: str = ""
    raw_content: str = ""

    def to_payload(self) -> dict[str, object]:
        return {
            "title": self.title,
            "desc": self.desc,
            "text": self.text or (
                _case_reference_text(self)
                if self.score > 0 or self.score_label or self.match_reason
                else self.desc or self.title
            ),
            "detailUrl": self.detail_url,
            "source": self.source,
            "score": self.score,
            "scoreLabel": self.score_label or (f"契合度 {self.score}" if self.score > 0 else ""),
            "matchReason": self.match_reason,
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


def loading_case_result() -> CaseSearchResult:
    return CaseSearchResult(status="loading", count_label="检索中")


def empty_case_result(*, error_message: str = "") -> CaseSearchResult:
    return CaseSearchResult(
        status="error" if error_message else "empty",
        count_label="暂无案例",
        error_message=error_message,
    )


def build_case_search_request(
    todo_id: str,
    title: str,
    current_summary: str,
    timeline_lines: list[str],
    *,
    function_point: str = "",
) -> CaseSearchRequest:
    return CaseSearchRequest(
        todo_id=sanitize_text(todo_id).strip(),
        title=sanitize_text(title).strip(),
        current_summary=sanitize_text(current_summary).strip(),
        timeline_text="\n".join(sanitize_text(line).strip() for line in timeline_lines if sanitize_text(line).strip()),
        function_point=sanitize_text(function_point).strip(),
    )


def build_server_case_search_question(request: CaseSearchRequest) -> str:
    parts: list[str] = []
    if request.title:
        parts.append(f"工单标题：{request.title}")
    if request.current_summary:
        parts.append(f"问题描述：{request.current_summary}")
    if request.timeline_text:
        parts.append(f"跟进记录：\n{request.timeline_text}")
    return "\n".join(parts).strip() or request.current_summary or request.title


def build_case_search_result_from_server_items(payload: object) -> CaseSearchResult:
    raw_items = payload
    if isinstance(payload, dict):
        raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        return empty_case_result(error_message="服务端案例结果格式错误。")

    items: list[CaseSearchItem] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        title = sanitize_text(raw_item.get("title")).strip()
        if not title:
            continue
        description = sanitize_text(raw_item.get("description")).strip()
        solution = sanitize_text(raw_item.get("solution")).strip()
        match_reason = sanitize_text(raw_item.get("match_reason") or raw_item.get("matchReason")).strip()
        confidence = sanitize_text(raw_item.get("match_confidence") or raw_item.get("matchConfidence")).strip()
        detail_url = sanitize_text(raw_item.get("detail_url") or raw_item.get("detailUrl")).strip()
        score = _server_case_score(confidence, raw_item.get("score"))
        items.append(
            CaseSearchItem(
                title=title,
                desc=_server_case_desc(description, solution),
                text=_server_case_text(
                    title=title,
                    description=description,
                    match_reason=match_reason,
                    solution=solution,
                    detail_url=detail_url,
                ),
                detail_url=detail_url,
                source="Chattodo 服务端",
                score=score,
                score_label=_server_case_score_label(confidence, score),
                match_reason=match_reason,
                raw_content="\n".join(part for part in (description, match_reason, solution) if part),
            )
        )

    ranked = sorted(items, key=lambda item: (-item.score, item.title))[:5]
    eligible = [item for item in ranked if item.score >= MIN_CASE_MATCH_SCORE]
    return CaseSearchResult(
        status="success" if eligible else "empty",
        count_label=f"检索 {len(eligible)} 条结果" if eligible else "暂无案例",
        items=eligible,
    )


def _server_case_score(confidence: str, raw_score: object) -> int:
    explicit = _clamp_score(raw_score)
    if explicit > 0:
        return explicit
    normalized = sanitize_text(confidence).strip().casefold()
    if normalized == "high":
        return 85
    if normalized == "medium":
        return 70
    if normalized == "low":
        return 45
    return 70


def _server_case_score_label(confidence: str, score: int) -> str:
    normalized = sanitize_text(confidence).strip().casefold()
    if normalized == "high":
        return "高匹配"
    if normalized == "medium":
        return "中匹配"
    if normalized == "low":
        return "低匹配"
    return f"契合度 {score}" if score > 0 else ""


def _server_case_desc(description: str, solution: str) -> str:
    parts: list[str] = []
    if description:
        parts.append(f"问题现象：{_truncate(description, 90)}")
    if solution:
        parts.append(f"处理方案：{_truncate(solution, 120)}")
    return "\n".join(parts) or "服务端返回相似案例"


def _server_case_text(
    *,
    title: str,
    description: str,
    match_reason: str,
    solution: str,
    detail_url: str,
) -> str:
    lines = [f"【相似案例】{title}"]
    if description:
        lines.append(f"问题现象：{description}")
    if match_reason:
        lines.append(f"相似原因：{match_reason}")
    if solution:
        lines.append(f"处理方案：{solution}")
    if detail_url:
        lines.append(f"详情：{detail_url}")
    return "\n".join(lines)


def _case_reference_text(item: CaseSearchItem) -> str:
    lines = [f"【相似案例】{item.title}"]
    score_label = item.score_label or (f"契合度 {item.score}" if item.score > 0 else "")
    if score_label:
        lines.append(score_label)
    if item.desc:
        lines.append(f"关键结论：{item.desc}")
    if item.match_reason:
        lines.append(f"契合原因：{item.match_reason}")
    if item.detail_url:
        lines.append(f"详情：{item.detail_url}")
    return "\n".join(lines)


def _clamp_score(value: object) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _truncate(value: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", sanitize_text(value)).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"

"""Domain models for ticket-oriented Todo workflows."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any


UNKNOWN_TEXT = "未知"
UNCLASSIFIED_TASK = "未分类任务"
PENDING_TEXT = "待补充"

_TITLE_PREFIXES = (
    "客户反馈",
    "客户表示",
    "客户反映",
    "客户需要",
    "客户要求",
    "用户反馈",
    "用户表示",
    "用户反映",
    "用户需要",
    "用户要求",
    "目前",
    "当前",
    "现象",
    "问题",
    "出现",
    "现需",
)

_STRONG_ISSUE_KEYWORDS = (
    "失败",
    "异常",
    "报错",
    "错误",
    "卡顿",
    "超时",
    "中断",
    "无法",
    "不能",
    "未",
    "不生效",
    "不显示",
    "不通过",
    "丢失",
    "缺失",
    "失效",
)

_WEAK_ISSUE_KEYWORDS = (
    "定制",
    "适配",
    "整改",
    "优化",
    "补充",
    "新增",
    "处理",
    "排查",
    "修复",
    "完善",
    "支持",
    "同步",
    "搭建",
    "实现",
)


def _clean(value: Any, fallback: str = UNKNOWN_TEXT) -> str:
    text = str(value or "").strip()
    return text or fallback


def summarize_issue_title(text: Any, fallback: str = UNCLASSIFIED_TASK, max_length: int = 20) -> str:
    cleaned = re.sub(r"\s+", "", str(text or ""))
    if not cleaned:
        return fallback[:max_length]

    clauses = [clause for clause in re.split(r"[^\u4e00-\u9fffA-Za-z0-9]+", cleaned) if clause]

    candidate = next(
        (clause for clause in clauses if any(keyword in clause for keyword in _STRONG_ISSUE_KEYWORDS)),
        "",
    )
    if not candidate:
        weak_matches = [
            clause for clause in clauses if any(keyword in clause for keyword in _WEAK_ISSUE_KEYWORDS)
        ]
        candidate = weak_matches[-1] if weak_matches else (clauses[0] if clauses else cleaned)

    for prefix in _TITLE_PREFIXES:
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):]
            break

    candidate = candidate.strip("：:，,。.；; ")
    if candidate.startswith("需要"):
        candidate = candidate[2:]
    elif candidate.startswith("需"):
        candidate = candidate[1:]
    if candidate.startswith("进一步") and len(candidate) > 3:
        candidate = candidate[3:]
    if candidate.startswith(("对", "将", "把")) and len(candidate) > 1:
        candidate = candidate[1:]

    candidate = candidate or cleaned
    return candidate[:max_length]


@dataclass
class TicketSummaryFields:
    group_name: str = UNKNOWN_TEXT
    environment: str = UNKNOWN_TEXT
    product_line: str = UNKNOWN_TEXT
    ticket_type: str = UNKNOWN_TEXT

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "TicketSummaryFields":
        payload = payload or {}
        return cls(
            group_name=_clean(payload.get("group_name")),
            environment=_clean(payload.get("environment")),
            product_line=_clean(payload.get("product_line")),
            ticket_type=_clean(payload.get("ticket_type")),
        )


@dataclass
class TicketSnapshot:
    title: str
    fields: TicketSummaryFields
    current_summary: str
    timeline_entry: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "group_name": self.fields.group_name,
            "environment": self.fields.environment,
            "product_line": self.fields.product_line,
            "ticket_type": self.fields.ticket_type,
            "current_summary": self.current_summary,
            "timeline_entry": self.timeline_entry,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TicketSnapshot":
        raw_summary = payload.get("current_summary") or payload.get("summary") or payload.get("task_desc")
        title_source = raw_summary or payload.get("title")
        title = summarize_issue_title(title_source, fallback=UNCLASSIFIED_TASK)
        current_summary = _clean(raw_summary, fallback=PENDING_TEXT)
        timeline_entry = _clean(
            payload.get("timeline_entry") or payload.get("follow_up") or current_summary,
            fallback=current_summary,
        )
        fields = TicketSummaryFields.from_dict(
            {
                "group_name": payload.get("group_name"),
                "environment": payload.get("environment"),
                "product_line": payload.get("product_line") or payload.get("platform"),
                "ticket_type": payload.get("ticket_type"),
            }
        )
        return cls(
            title=title[:80],
            fields=fields,
            current_summary=current_summary[:400],
            timeline_entry=timeline_entry[:600],
        )

    @classmethod
    def from_text(cls, text: str) -> "TicketSnapshot":
        cleaned = text.strip()
        summary = cleaned or PENDING_TEXT
        title = summarize_issue_title(summary, fallback=UNCLASSIFIED_TASK)
        return cls(
            title=title[:80],
            fields=TicketSummaryFields(),
            current_summary=summary[:400],
            timeline_entry=summary[:600],
        )

    def __str__(self) -> str:
        return (
            f"标题: {self.title}\n"
            f"群聊名称: {self.fields.group_name}\n"
            f"环境: {self.fields.environment}\n"
            f"产品线: {self.fields.product_line}\n"
            f"工单类型: {self.fields.ticket_type}\n"
            f"当前摘要: {self.current_summary}\n"
            f"跟进记录: {self.timeline_entry}"
        )

"""Domain models for ticket-oriented Todo workflows."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


def _clean(value: Any, fallback: str = "未知") -> str:
    text = str(value or "").strip()
    return text or fallback


@dataclass
class TicketSummaryFields:
    group_name: str = "未知"
    environment: str = "未知"
    product_line: str = "未知"
    ticket_type: str = "未知"

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
        title = _clean(
            payload.get("title") or payload.get("task_desc") or payload.get("summary"),
            fallback="未分类任务",
        )
        current_summary = _clean(
            payload.get("current_summary") or payload.get("summary") or payload.get("task_desc"),
            fallback="待补充",
        )
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
        lines = [line.strip("-• \t") for line in cleaned.splitlines() if line.strip()]
        title = lines[0] if lines else "未分类任务"
        summary = cleaned or "待补充"
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

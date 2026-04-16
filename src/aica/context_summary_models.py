"""Shared models for context-summary infrastructure."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Protocol

from .text_sanitize import sanitize_text
from .todo_models import TimelineAttachment, TimelineEvent, TodoItem

ContextSummaryGoal = Literal[
    "append_screenshot_context",
    "log_analysis_context",
    "timeline_rollup",
]

_DEFAULT_GOAL = "append_screenshot_context"


def _clean_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for item in values:
        text = sanitize_text(item).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _clean_mapping(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for raw_key, raw_value in payload.items():
        key = sanitize_text(raw_key).strip()
        if not key:
            continue
        if isinstance(raw_value, str):
            value = sanitize_text(raw_value).strip()
            if value:
                cleaned[key] = value
        elif isinstance(raw_value, list):
            values = _clean_string_list(raw_value)
            if values:
                cleaned[key] = values
        elif raw_value is not None:
            cleaned[key] = raw_value
    return cleaned


def _normalize_goal(value: object) -> ContextSummaryGoal:
    normalized = sanitize_text(value).strip()
    if normalized in {"append_screenshot_context", "log_analysis_context", "timeline_rollup"}:
        return normalized
    return _DEFAULT_GOAL


def _build_attachment_summaries(attachments: list[TimelineAttachment]) -> list[str]:
    summaries: list[str] = []
    for attachment in attachments:
        if not isinstance(attachment, TimelineAttachment):
            continue
        name = sanitize_text(attachment.name).strip()
        if name:
            summaries.append(name)
    return summaries


def _build_event_context_text(event: TimelineEvent) -> str:
    parts: list[str] = []
    content = sanitize_text(event.content).strip()
    if content:
        parts.append(content)

    payload = event.payload if isinstance(event.payload, dict) else {}
    if event.event_type == "log_analysis_result":
        findings = sanitize_text(payload.get("findings", "")).strip()
        judgment = sanitize_text(payload.get("judgment", "")).strip()
        next_steps = sanitize_text(payload.get("next_steps", "")).strip()
        if findings:
            parts.append(f"命中线索: {findings}")
        if judgment:
            parts.append(f"初步判断: {judgment}")
        if next_steps:
            parts.append(f"建议下一步: {next_steps}")
    elif event.event_type == "log_analysis_command":
        command_text = sanitize_text(payload.get("command_text", "")).strip()
        if command_text and command_text not in parts:
            parts.append(command_text)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in parts:
        normalized = sanitize_text(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return "\n".join(deduped).strip()


@dataclass(frozen=True)
class ContextSummaryPoint:
    category: str = ""
    text: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "category", sanitize_text(self.category).strip())
        object.__setattr__(self, "text", sanitize_text(self.text).strip())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: object) -> "ContextSummaryPoint":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            category=payload.get("category", ""),
            text=payload.get("text", ""),
        )


@dataclass(frozen=True)
class ContextSummaryEntry:
    timestamp: str = ""
    kind: str = ""
    event_type: str = ""
    scenario: str = ""
    content: str = ""
    attachment_summaries: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", sanitize_text(self.timestamp).strip())
        object.__setattr__(self, "kind", sanitize_text(self.kind).strip())
        object.__setattr__(self, "event_type", sanitize_text(self.event_type).strip())
        object.__setattr__(self, "scenario", sanitize_text(self.scenario).strip())
        object.__setattr__(self, "content", sanitize_text(self.content).strip())
        object.__setattr__(self, "attachment_summaries", _clean_string_list(list(self.attachment_summaries or [])))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: object) -> "ContextSummaryEntry":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            timestamp=payload.get("timestamp", ""),
            kind=payload.get("kind", ""),
            event_type=payload.get("event_type", ""),
            scenario=payload.get("scenario", ""),
            content=payload.get("content", ""),
            attachment_summaries=payload.get("attachment_summaries", []),
        )

    @classmethod
    def from_timeline_event(cls, event: TimelineEvent) -> "ContextSummaryEntry":
        return cls(
            timestamp=event.timestamp,
            kind=event.kind,
            event_type=event.event_type,
            scenario=event.scenario,
            content=_build_event_context_text(event),
            attachment_summaries=_build_attachment_summaries(list(event.attachments or [])),
        )


@dataclass(frozen=True)
class ContextSummaryRequest:
    summary_goal: ContextSummaryGoal = _DEFAULT_GOAL
    description: str = ""
    timeline_entries: list[ContextSummaryEntry] = field(default_factory=list)
    extra_context: dict[str, Any] = field(default_factory=dict)
    max_items: int = 8
    max_chars: int = 1800

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_goal", _normalize_goal(self.summary_goal))
        object.__setattr__(self, "description", sanitize_text(self.description).strip())
        object.__setattr__(
            self,
            "timeline_entries",
            [
                item if isinstance(item, ContextSummaryEntry) else ContextSummaryEntry.from_dict(item)
                for item in list(self.timeline_entries or [])
            ],
        )
        object.__setattr__(self, "extra_context", _clean_mapping(dict(self.extra_context or {})))
        object.__setattr__(self, "max_items", max(1, int(self.max_items or 8)))
        object.__setattr__(self, "max_chars", max(600, int(self.max_chars or 1800)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_goal": self.summary_goal,
            "description": self.description,
            "timeline_entries": [item.to_dict() for item in self.timeline_entries],
            "extra_context": dict(self.extra_context),
            "max_items": self.max_items,
            "max_chars": self.max_chars,
        }


@dataclass(frozen=True)
class ContextSummaryResult:
    summary_text: str = ""
    problem_brief: str = ""
    key_points: list[ContextSummaryPoint] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    next_focus: list[str] = field(default_factory=list)
    source_stats: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary_text", sanitize_text(self.summary_text).strip())
        object.__setattr__(self, "problem_brief", sanitize_text(self.problem_brief).strip())
        object.__setattr__(
            self,
            "key_points",
            [
                item if isinstance(item, ContextSummaryPoint) else ContextSummaryPoint.from_dict(item)
                for item in list(self.key_points or [])
            ],
        )
        object.__setattr__(self, "open_questions", _clean_string_list(list(self.open_questions or [])))
        object.__setattr__(self, "next_focus", _clean_string_list(list(self.next_focus or [])))
        object.__setattr__(self, "source_stats", _clean_mapping(dict(self.source_stats or {})))

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_text": self.summary_text,
            "problem_brief": self.problem_brief,
            "key_points": [item.to_dict() for item in self.key_points],
            "open_questions": list(self.open_questions),
            "next_focus": list(self.next_focus),
            "source_stats": dict(self.source_stats),
        }

    @classmethod
    def from_dict(cls, payload: object) -> "ContextSummaryResult":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            summary_text=payload.get("summary_text", ""),
            problem_brief=payload.get("problem_brief", ""),
            key_points=payload.get("key_points", []),
            open_questions=payload.get("open_questions", []),
            next_focus=payload.get("next_focus", []),
            source_stats=payload.get("source_stats", {}),
        )


class ContextSummaryAgent(Protocol):
    def summarize_with_llm(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        """Summarize by calling a configured LLM task."""

    def summarize_locally(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        """Summarize with local heuristics."""


def build_context_summary_request_for_todo(
    todo: TodoItem,
    *,
    summary_goal: ContextSummaryGoal,
    description: str = "",
    extra_context: dict[str, Any] | None = None,
    max_items: int = 8,
    max_chars: int = 1800,
) -> ContextSummaryRequest:
    metadata = {
        "title": sanitize_text(todo.title).strip(),
        "group_name": sanitize_text(todo.summary_fields.group_name).strip(),
        "environment": sanitize_text(todo.summary_fields.environment).strip(),
        "product_line": sanitize_text(todo.summary_fields.product_line).strip(),
        "ticket_type": sanitize_text(todo.summary_fields.ticket_type).strip(),
        "current_summary": sanitize_text(todo.current_summary).strip(),
    }
    if extra_context:
        metadata.update(_clean_mapping(extra_context))
    return ContextSummaryRequest(
        summary_goal=summary_goal,
        description=description or sanitize_text(todo.current_summary).strip() or sanitize_text(todo.title).strip(),
        timeline_entries=[ContextSummaryEntry.from_timeline_event(event) for event in todo.timeline],
        extra_context=metadata,
        max_items=max_items,
        max_chars=max_chars,
    )

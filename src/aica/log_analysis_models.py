"""Domain models for async log analysis tasks and structured results."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Protocol

from .text_sanitize import sanitize_text


def _now_iso() -> str:
    return datetime.now().isoformat()


def _clean_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for item in values:
        text = sanitize_text(item)
        if text:
            normalized.append(text)
    return normalized


def _clean_dict(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        normalized_key = sanitize_text(key)
        if not normalized_key:
            continue
        if isinstance(value, str):
            cleaned[normalized_key] = sanitize_text(value)
        else:
            cleaned[normalized_key] = value
    return cleaned


@dataclass(frozen=True)
class LogAnalysisCommand:
    command_name: str = "analyze_logs"
    trad_id: str = ""
    request_id: str = ""
    focus_terms: list[str] = field(default_factory=list)
    raw_command: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "command_name", sanitize_text(self.command_name) or "analyze_logs")
        object.__setattr__(self, "trad_id", sanitize_text(self.trad_id))
        object.__setattr__(self, "request_id", sanitize_text(self.request_id))
        object.__setattr__(self, "focus_terms", _clean_list(list(self.focus_terms or [])))
        object.__setattr__(self, "raw_command", sanitize_text(self.raw_command))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: object) -> "LogAnalysisCommand":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            command_name=payload.get("command_name", "analyze_logs"),
            trad_id=payload.get("trad_id", ""),
            request_id=payload.get("request_id", ""),
            focus_terms=payload.get("focus_terms", []),
            raw_command=payload.get("raw_command", ""),
        )


@dataclass(frozen=True)
class InvestigationContextSummary:
    problem_summary: str = ""
    actions_taken: list[str] = field(default_factory=list)
    confirmed_facts: list[str] = field(default_factory=list)
    suspected_causes: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    current_focus: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "problem_summary", sanitize_text(self.problem_summary))
        object.__setattr__(self, "actions_taken", _clean_list(list(self.actions_taken or [])))
        object.__setattr__(self, "confirmed_facts", _clean_list(list(self.confirmed_facts or [])))
        object.__setattr__(self, "suspected_causes", _clean_list(list(self.suspected_causes or [])))
        object.__setattr__(self, "open_questions", _clean_list(list(self.open_questions or [])))
        object.__setattr__(self, "current_focus", _clean_list(list(self.current_focus or [])))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: object) -> "InvestigationContextSummary":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            problem_summary=payload.get("problem_summary", ""),
            actions_taken=payload.get("actions_taken", []),
            confirmed_facts=payload.get("confirmed_facts", []),
            suspected_causes=payload.get("suspected_causes", []),
            open_questions=payload.get("open_questions", []),
            current_focus=payload.get("current_focus", []),
        )


@dataclass(frozen=True)
class CollectedEvidencePart:
    source_name: str = ""
    source_type: str = ""
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", sanitize_text(self.source_name))
        object.__setattr__(self, "source_type", sanitize_text(self.source_type))
        object.__setattr__(self, "summary", sanitize_text(self.summary))
        object.__setattr__(self, "details", _clean_dict(dict(self.details or {})))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: object) -> "CollectedEvidencePart":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            source_name=payload.get("source_name", ""),
            source_type=payload.get("source_type", ""),
            summary=payload.get("summary", ""),
            details=payload.get("details", {}),
        )


@dataclass(frozen=True)
class EvidenceBundle:
    parts: list[CollectedEvidencePart] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "parts",
            [
                item if isinstance(item, CollectedEvidencePart) else CollectedEvidencePart.from_dict(item)
                for item in list(self.parts or [])
            ],
        )
        object.__setattr__(self, "metadata", _clean_dict(dict(self.metadata or {})))

    def to_dict(self) -> dict[str, Any]:
        return {
            "parts": [part.to_dict() for part in self.parts],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: object) -> "EvidenceBundle":
        if not isinstance(payload, dict):
            return cls()
        return cls(parts=payload.get("parts", []), metadata=payload.get("metadata", {}))


@dataclass(frozen=True)
class LogAnalysisResultPayload:
    analyzed_materials: list[dict[str, Any]] = field(default_factory=list)
    problem_to_answer: str = ""
    analysis_focus: dict[str, Any] = field(default_factory=dict)
    analysis_mode: str = ""
    investigation_steps: list[dict[str, Any]] = field(default_factory=list)
    key_findings: list[dict[str, Any]] = field(default_factory=list)
    preliminary_judgment: dict[str, Any] = field(default_factory=dict)
    question_answered: bool = False
    answer_gap_reason: str = ""
    missing_information: list[str] = field(default_factory=list)
    suggested_next_steps: list[str] = field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    image_clues: list[dict[str, Any]] = field(default_factory=list)
    search_hits: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: object) -> "LogAnalysisResultPayload":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            analyzed_materials=list(payload.get("analyzed_materials", [])),
            problem_to_answer=sanitize_text(payload.get("problem_to_answer", "")),
            analysis_focus=_clean_dict(payload.get("analysis_focus", {})),
            analysis_mode=sanitize_text(payload.get("analysis_mode", "")),
            investigation_steps=list(payload.get("investigation_steps", [])),
            key_findings=list(payload.get("key_findings", [])),
            preliminary_judgment=_clean_dict(payload.get("preliminary_judgment", {})),
            question_answered=bool(payload.get("question_answered", False)),
            answer_gap_reason=sanitize_text(payload.get("answer_gap_reason", "")),
            missing_information=_clean_list(payload.get("missing_information", [])),
            suggested_next_steps=_clean_list(payload.get("suggested_next_steps", [])),
            evidence_refs=list(payload.get("evidence_refs", [])),
            image_clues=list(payload.get("image_clues", [])),
            search_hits=list(payload.get("search_hits", [])),
        )


@dataclass(frozen=True)
class LogAnalysisProducedResult:
    result_payload: LogAnalysisResultPayload = field(default_factory=LogAnalysisResultPayload)
    result_summary: str = ""
    producer_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        payload = self.result_payload
        if not isinstance(payload, LogAnalysisResultPayload):
            payload = LogAnalysisResultPayload.from_dict(payload)
        object.__setattr__(self, "result_payload", payload)
        object.__setattr__(self, "result_summary", sanitize_text(self.result_summary))
        object.__setattr__(self, "producer_metadata", _clean_dict(dict(self.producer_metadata or {})))

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_payload": self.result_payload.to_dict(),
            "result_summary": self.result_summary,
            "producer_metadata": dict(self.producer_metadata),
        }


@dataclass(frozen=True)
class LogAnalysisTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    todo_id: str = ""
    timeline_entry_id: str = ""
    status: str = "queued"
    current_step: str = ""
    raw_command: str = ""
    parsed_focus_json: dict[str, Any] = field(default_factory=dict)
    attachment_snapshot_json: list[dict[str, Any]] = field(default_factory=list)
    investigation_context_json: dict[str, Any] = field(default_factory=dict)
    evidence_bundle_json: dict[str, Any] = field(default_factory=dict)
    result_summary: str = ""
    result_payload_json: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    model_binding_used: str = ""
    started_at: str = ""
    completed_at: str = ""
    failed_at: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", sanitize_text(self.id) or str(uuid.uuid4()))
        object.__setattr__(self, "todo_id", sanitize_text(self.todo_id))
        object.__setattr__(self, "timeline_entry_id", sanitize_text(self.timeline_entry_id))
        object.__setattr__(self, "status", sanitize_text(self.status) or "queued")
        object.__setattr__(self, "current_step", sanitize_text(self.current_step))
        object.__setattr__(self, "raw_command", sanitize_text(self.raw_command))
        object.__setattr__(self, "parsed_focus_json", _clean_dict(dict(self.parsed_focus_json or {})))
        object.__setattr__(self, "attachment_snapshot_json", list(self.attachment_snapshot_json or []))
        object.__setattr__(self, "investigation_context_json", _clean_dict(dict(self.investigation_context_json or {})))
        object.__setattr__(self, "evidence_bundle_json", _clean_dict(dict(self.evidence_bundle_json or {})))
        object.__setattr__(self, "result_summary", sanitize_text(self.result_summary))
        object.__setattr__(self, "result_payload_json", _clean_dict(dict(self.result_payload_json or {})))
        object.__setattr__(self, "error_message", sanitize_text(self.error_message))
        object.__setattr__(self, "model_binding_used", sanitize_text(self.model_binding_used))
        object.__setattr__(self, "started_at", sanitize_text(self.started_at))
        object.__setattr__(self, "completed_at", sanitize_text(self.completed_at))
        object.__setattr__(self, "failed_at", sanitize_text(self.failed_at))
        object.__setattr__(self, "created_at", sanitize_text(self.created_at) or _now_iso())
        object.__setattr__(self, "updated_at", sanitize_text(self.updated_at) or _now_iso())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "LogAnalysisTask":
        return cls(
            id=row.get("id", ""),
            todo_id=row.get("todo_id", ""),
            timeline_entry_id=row.get("timeline_entry_id", ""),
            status=row.get("status", "queued"),
            current_step=row.get("current_step", ""),
            raw_command=row.get("raw_command", ""),
            parsed_focus_json=_loads_json_object(row.get("parsed_focus_json"), default={}),
            attachment_snapshot_json=_loads_json_object(row.get("attachment_snapshot_json"), default=[]),
            investigation_context_json=_loads_json_object(row.get("investigation_context_json"), default={}),
            evidence_bundle_json=_loads_json_object(row.get("evidence_bundle_json"), default={}),
            result_summary=row.get("result_summary", ""),
            result_payload_json=_loads_json_object(row.get("result_payload_json"), default={}),
            error_message=row.get("error_message", ""),
            model_binding_used=row.get("model_binding_used", ""),
            started_at=row.get("started_at", ""),
            completed_at=row.get("completed_at", ""),
            failed_at=row.get("failed_at", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )


@dataclass(frozen=True)
class LogAnalysisRequest:
    todo_snapshot: dict[str, Any]
    parsed_command: LogAnalysisCommand
    investigation_context: InvestigationContextSummary
    evidence_bundle: EvidenceBundle
    task_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LogAnalysisConsumeContext:
    todo_id: str
    task_id: str
    timeline_entry_id: str
    investigation_context: InvestigationContextSummary
    evidence_bundle: EvidenceBundle


class LogAnalysisAgent(Protocol):
    def analyze(self, request: LogAnalysisRequest) -> LogAnalysisProducedResult:
        """Produce structured log-analysis output from structured inputs."""


class LogAnalysisResultConsumer(Protocol):
    def consume(self, produced: LogAnalysisProducedResult, context: LogAnalysisConsumeContext) -> None:
        """Consume the producer output into a downstream presentation or export target."""


def _loads_json_object(value: object, *, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = sanitize_text(value)
    if not text:
        return default
    try:
        parsed = json.loads(text)
    except Exception:
        return default
    return parsed if isinstance(parsed, type(default)) else default

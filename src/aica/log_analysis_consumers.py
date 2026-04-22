"""Consumers and presenters for structured log analysis output."""
from __future__ import annotations

import re

from .log_analysis_models import LogAnalysisConsumeContext, LogAnalysisProducedResult, LogAnalysisResultConsumer
from .text_sanitize import sanitize_text
from .todo_models import TimelineEvent


_URL_RE = re.compile(r"https?://\S+|//\S+")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text(value: object) -> str:
    return _WHITESPACE_RE.sub(" ", sanitize_text(value)).strip()


def _truncate(value: str, limit: int = 120) -> str:
    text = _normalize_text(value)
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def _strip_urls(value: str) -> str:
    return _URL_RE.sub("", value).strip()


def _clean_evidence(value: str) -> str:
    parts = [
        _normalize_text(part)
        for part in _strip_urls(value).split("|")
        if _normalize_text(part)
    ]
    return " | ".join(parts)


def _dedupe_lines(items: list[str], *, limit: int) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _normalize_text(item)
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        lines.append(text)
        if len(lines) >= limit:
            break
    return lines


def _judgment_text(judgment: dict) -> str:
    category = sanitize_text(judgment.get("category", ""))
    reason = sanitize_text(judgment.get("reason", ""))
    return "：".join(part for part in [category, reason] if part).strip()


def _format_conclusion(produced: LogAnalysisProducedResult) -> str:
    issue = sanitize_text(produced.result_payload.primary_issue)
    if issue:
        return issue
    return _judgment_text(produced.result_payload.preliminary_judgment or {})


def _format_finding_line(item: dict) -> str:
    kind = sanitize_text(item.get("kind", ""))
    summary = _strip_urls(_normalize_text(item.get("summary", "")))
    evidence = _clean_evidence(sanitize_text(item.get("evidence", "")))
    source = sanitize_text(item.get("source", ""))
    line_no = int(item.get("line_no", 0) or 0)

    if kind == "request_chain":
        prefix = summary
    else:
        prefix = f"{source}:{line_no}" if source and line_no else "线索"
        prefix = f"{prefix} {summary}".strip()
    if evidence:
        return _truncate(f"{prefix} [{evidence}]".strip(), 128)
    return _truncate(prefix, 128)


def _request_chain_lines(chain: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in chain:
        stage = _normalize_text(item.get("stage", ""))
        component = _normalize_text(item.get("component", ""))
        summary = _normalize_text(item.get("summary", ""))
        evidence = _clean_evidence(sanitize_text(item.get("evidence", "")))
        prefix = " -> ".join(part for part in [stage, component] if part)
        text = f"{prefix}: {summary}" if prefix and summary else (summary or prefix)
        if evidence:
            text = f"{text} [{evidence}]"
        if text:
            lines.append(_truncate(text, 132))
    return _dedupe_lines(lines, limit=3)


def _finding_lines(payload: LogAnalysisProducedResult) -> list[str]:
    chain_lines = _request_chain_lines(payload.result_payload.request_chain or [])
    if chain_lines:
        return chain_lines
    source_items = payload.result_payload.evidence_items or payload.result_payload.key_findings or []
    return _dedupe_lines([_format_finding_line(item) for item in source_items], limit=3)


def _next_step_lines(next_steps: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in next_steps:
        text = _normalize_text(item)
        if not text:
            continue
        if text.startswith("补充信息："):
            continue
        cleaned.append(_truncate(text, 88))
    return _dedupe_lines(cleaned, limit=3)


def _missing_info_lines(payload: LogAnalysisProducedResult) -> list[str]:
    lines = [
        _truncate(item, 88)
        for item in payload.result_payload.missing_information
        if sanitize_text(item)
    ]
    return _dedupe_lines(lines, limit=2)


def _material_lines(materials: list[dict]) -> list[str]:
    lines: list[str] = []
    for item in materials:
        summary = _normalize_text(item.get("summary", ""))
        name = _normalize_text(item.get("name", ""))
        if summary:
            lines.append(_truncate(summary, 96))
        elif name:
            lines.append(_truncate(name, 96))
    return _dedupe_lines(lines, limit=3)


def _findings_text(lines: list[str]) -> str:
    return "\n".join(lines).strip()


def _next_steps_text(lines: list[str]) -> str:
    return "\n".join(lines).strip()


class TimelineLogAnalysisPresenter(LogAnalysisResultConsumer):
    def consume(self, produced: LogAnalysisProducedResult, context: LogAnalysisConsumeContext) -> TimelineEvent:
        payload = produced.result_payload
        analyzed_materials = payload.analyzed_materials or []
        next_steps = payload.suggested_next_steps or []
        judgment = payload.preliminary_judgment or {}

        conclusion_text = _format_conclusion(produced)
        finding_lines = _finding_lines(produced)
        next_step_lines = _next_step_lines(next_steps)
        missing_lines = _missing_info_lines(produced)
        material_lines = _material_lines(analyzed_materials)
        findings_text = _findings_text(finding_lines)
        judgment_text = _judgment_text(judgment)
        next_steps_text = _next_steps_text(next_step_lines)

        summary_lines = ["日志分析结果"]
        if conclusion_text:
            summary_lines.append(conclusion_text)
        if finding_lines:
            summary_lines.append(f"关键依据：{finding_lines[0]}")
        if next_step_lines:
            summary_lines.append(f"建议动作：{next_step_lines[0]}")

        return TimelineEvent(
            kind="log_analysis_result",
            scenario="日志分析结果",
            event_type="log_analysis_result",
            status="success",
            content="\n".join(summary_lines).strip(),
            payload={
                "source_timeline_entry_id": context.timeline_entry_id,
                "task_id": context.task_id,
                "analyzed_materials": analyzed_materials,
                "conclusion": conclusion_text,
                "findings": findings_text,
                "judgment": judgment_text,
                "next_steps": next_steps_text,
                "confidence": payload.confidence,
                "finding_lines": finding_lines,
                "next_step_lines": next_step_lines,
                "missing_information_lines": missing_lines,
                "material_lines": material_lines,
                "evidence_items": payload.evidence_items,
                "primary_issue": payload.primary_issue,
                "noise_items": payload.noise_items,
                "key_findings": payload.key_findings,
                "preliminary_judgment": judgment,
                "suggested_next_steps": next_steps,
                "analysis_focus": payload.analysis_focus,
                "analysis_mode": payload.analysis_mode,
                "investigation_steps": payload.investigation_steps,
                "problem_to_answer": payload.problem_to_answer,
                "question_answered": payload.question_answered,
                "answer_gap_reason": payload.answer_gap_reason,
                "missing_information": payload.missing_information,
                "evidence_refs": payload.evidence_refs,
                "image_clues": payload.image_clues,
                "search_hits": payload.search_hits,
                "request_chain": payload.request_chain,
                "root_cause_signature": payload.root_cause_signature,
                "affected_entities": payload.affected_entities,
                "log_vs_ticket_note": payload.log_vs_ticket_note,
                "raw_result_payload": payload.to_dict(),
            },
        )


class StageSummaryConsumer(LogAnalysisResultConsumer):
    def consume(self, produced: LogAnalysisProducedResult, context: LogAnalysisConsumeContext) -> None:
        return None


class RAndDSummaryConsumer(LogAnalysisResultConsumer):
    def consume(self, produced: LogAnalysisProducedResult, context: LogAnalysisConsumeContext) -> None:
        return None


class CustomerSummaryConsumer(LogAnalysisResultConsumer):
    def consume(self, produced: LogAnalysisProducedResult, context: LogAnalysisConsumeContext) -> None:
        return None


class KnowledgeFeedbackConsumer(LogAnalysisResultConsumer):
    def consume(self, produced: LogAnalysisProducedResult, context: LogAnalysisConsumeContext) -> None:
        return None


class SimilarIssueRetrievalConsumer(LogAnalysisResultConsumer):
    def consume(self, produced: LogAnalysisProducedResult, context: LogAnalysisConsumeContext) -> None:
        return None

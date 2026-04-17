"""Consumers and presenters for structured log analysis output."""
from __future__ import annotations

from .log_analysis_models import LogAnalysisConsumeContext, LogAnalysisProducedResult, LogAnalysisResultConsumer
from .text_sanitize import sanitize_text
from .todo_models import TimelineEvent


def _finding_text(evidence_items: list[dict], key_findings: list[dict]) -> str:
    lines: list[str] = []
    for item in (evidence_items or key_findings)[:6]:
        summary = sanitize_text(item.get("summary", ""))
        evidence = sanitize_text(item.get("evidence", ""))
        if summary:
            lines.append(f"{summary} [{evidence}]".strip(" []") if evidence else summary)
    return "\n".join(lines).strip()


def _judgment_text(judgment: dict) -> str:
    category = sanitize_text(judgment.get("category", ""))
    reason = sanitize_text(judgment.get("reason", ""))
    return "：".join(part for part in [category, reason] if part).strip()


def _next_steps_text(next_steps: list[str]) -> str:
    return "\n".join(sanitize_text(item) for item in next_steps[:6] if sanitize_text(item)).strip()


class TimelineLogAnalysisPresenter(LogAnalysisResultConsumer):
    def consume(self, produced: LogAnalysisProducedResult, context: LogAnalysisConsumeContext) -> TimelineEvent:
        payload = produced.result_payload
        analyzed_materials = payload.analyzed_materials or []
        evidence_items = payload.evidence_items or []
        key_findings = payload.key_findings or []
        next_steps = payload.suggested_next_steps or []
        judgment = payload.preliminary_judgment or {}
        conclusion_text = sanitize_text(payload.primary_issue) or _judgment_text(judgment)
        findings_text = _finding_text(evidence_items, key_findings)
        judgment_text = _judgment_text(judgment)
        next_steps_text = _next_steps_text(next_steps)

        summary_lines = ["日志分析结果"]
        if conclusion_text:
            summary_lines.append(conclusion_text)
        if findings_text:
            summary_lines.append(f"关键证据：{findings_text.splitlines()[0]}")
        if next_steps_text:
            summary_lines.append(f"建议下一步：{next_steps_text.splitlines()[0]}")

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
                "evidence_items": evidence_items,
                "primary_issue": payload.primary_issue,
                "noise_items": payload.noise_items,
                "key_findings": key_findings,
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

"""Structured log analysis agent with iterative investigation loop."""
from __future__ import annotations

import json
import re
from typing import Any

from .llm.service import LLMService
from .log_analysis_models import (
    EvidenceBundle,
    InvestigationContextSummary,
    LogAnalysisProducedResult,
    LogAnalysisRequest,
    LogAnalysisResultPayload,
)
from .text_sanitize import sanitize_text


_IDENTIFIER_RE = re.compile(r"\b[a-zA-Z0-9_-]{8,64}\b")
_TRACE_RE = re.compile(
    r"(?i)(?:trace[_ -]?id|request[_ -]?id|x[-_]?request[-_]?id|trad[_ -]?id)\s*[:=：]\s*([a-zA-Z0-9_-]{4,128})"
)
_ERROR_CODE_RE = re.compile(r"\b\d{6}\b")
_PATH_RE = re.compile(r"/[a-zA-Z0-9_./{}-]{3,}")
_MAX_CONTEXT_LINES = 2


class DefaultLogAnalysisAgent:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm_service = llm_service

    def analyze(self, request: LogAnalysisRequest) -> LogAnalysisProducedResult:
        problem_to_answer = self._build_problem_to_answer(request)
        identifiers = self._collect_identifiers(request, problem_to_answer)
        plan = self._build_search_plan(request, identifiers, problem_to_answer)
        best_hits: list[dict[str, Any]] = []
        selected_mode = "按异常聚类排查"
        investigation_steps: list[dict[str, Any]] = []

        for round_index, step in enumerate(plan, 1):
            hits = self._collect_ranked_hits(
                request.evidence_bundle,
                identifiers=step.get("identifiers", []),
                focus_terms=step.get("focus_terms", []),
                mode=step.get("mode", ""),
            )
            investigation_steps.append(
                {
                    "round": round_index,
                    "label": step.get("label", f"第 {round_index} 轮排查"),
                    "detail": step.get("detail", ""),
                    "result": self._describe_round_result(hits),
                    "hit_count": len(hits),
                }
            )
            if hits and (not best_hits or self._total_score(hits) > self._total_score(best_hits)):
                best_hits = hits
                selected_mode = str(step.get("display_mode", selected_mode))
            if self._should_stop_loop(hits, step.get("mode", "")):
                break
            derived_clues = self._derive_clues_from_hits(hits)
            if derived_clues and round_index < len(plan):
                plan[round_index]["focus_terms"] = self._merge_terms(plan[round_index].get("focus_terms", []), derived_clues)

        key_findings = self._build_key_findings(best_hits)
        analyzed_materials = self._collect_materials(request.evidence_bundle)
        image_clues = self._collect_image_clues(request.evidence_bundle)
        judgment = self._build_judgment(best_hits, request.investigation_context)
        question_answered, answer_gap_reason = self._evaluate_answerability(problem_to_answer, best_hits, judgment)
        missing_information = self._build_missing_information(
            request,
            best_hits,
            identifiers,
            question_answered=question_answered,
            answer_gap_reason=answer_gap_reason,
        )
        next_steps = self._build_next_steps(judgment, best_hits, request.investigation_context, missing_information)
        result_payload = LogAnalysisResultPayload(
            analyzed_materials=analyzed_materials,
            problem_to_answer=problem_to_answer,
            analysis_focus={
                "trad_id": request.parsed_command.trad_id,
                "request_id": request.parsed_command.request_id,
                "focus_terms": list(request.parsed_command.focus_terms),
                "inferred_identifiers": identifiers,
            },
            analysis_mode=selected_mode,
            investigation_steps=investigation_steps,
            key_findings=key_findings,
            preliminary_judgment=judgment,
            question_answered=question_answered,
            answer_gap_reason=answer_gap_reason,
            missing_information=missing_information,
            suggested_next_steps=next_steps,
            evidence_refs=[
                {"source_name": part.source_name, "source_type": part.source_type}
                for part in request.evidence_bundle.parts
            ],
            image_clues=image_clues,
            search_hits=best_hits[:12],
        )
        summary = self._build_summary(judgment, key_findings, question_answered)
        producer_metadata = {
            "agent": self.__class__.__name__,
            "model_binding_used": self._describe_model_binding(),
        }
        return LogAnalysisProducedResult(
            result_payload=result_payload,
            result_summary=summary,
            producer_metadata=producer_metadata,
        )

    def _describe_model_binding(self) -> str:
        if self._llm_service is None:
            return ""
        try:
            resolved = self._llm_service.resolve_task_model("log_analysis")
            suffix = " (fallback analysis)" if resolved.fallback_used else ""
            return f"{resolved.reference.display_name}{suffix}"
        except Exception:
            return "local-only"

    def _build_problem_to_answer(self, request: LogAnalysisRequest) -> str:
        candidates = [
            sanitize_text(request.todo_snapshot.get("title", "")),
            sanitize_text(request.todo_snapshot.get("current_summary", "")),
            request.investigation_context.problem_summary,
        ]
        text = "；".join(item for item in candidates if item)
        return text[:240]

    def _collect_identifiers(self, request: LogAnalysisRequest, problem_to_answer: str) -> list[str]:
        candidates: list[str] = []
        direct = [
            request.parsed_command.trad_id,
            request.parsed_command.request_id,
            *request.parsed_command.focus_terms,
            request.investigation_context.problem_summary,
            *request.investigation_context.current_focus,
            sanitize_text(request.todo_snapshot.get("current_summary", "")),
            sanitize_text(request.todo_snapshot.get("title", "")),
            sanitize_text(request.todo_snapshot.get("conclusion", "")),
            problem_to_answer,
        ]
        for item in direct:
            text = sanitize_text(item)
            if not text:
                continue
            candidates.extend(_TRACE_RE.findall(text))
            candidates.extend(_PATH_RE.findall(text))
            candidates.extend(_ERROR_CODE_RE.findall(text))
            if len(text) >= 8 and not any(sep in text for sep in (" ", "，", ",")):
                candidates.append(text)
            for token in _IDENTIFIER_RE.findall(text):
                if any(char.isdigit() for char in token):
                    candidates.append(token)
        result: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            normalized = sanitize_text(item).strip()
            if len(normalized) < 4 or normalized.lower() in seen:
                continue
            seen.add(normalized.lower())
            result.append(normalized)
        return result[:12]

    def _build_search_plan(
        self,
        request: LogAnalysisRequest,
        identifiers: list[str],
        problem_to_answer: str,
    ) -> list[dict[str, Any]]:
        focus_terms = [item for item in request.parsed_command.focus_terms if item]
        context_terms = [
            *request.investigation_context.current_focus,
            request.investigation_context.problem_summary,
            *request.investigation_context.suspected_causes,
            sanitize_text(request.todo_snapshot.get("title", "")),
            problem_to_answer,
        ]
        normalized_context_terms = [sanitize_text(item) for item in context_terms if sanitize_text(item)]
        plan: list[dict[str, Any]] = []
        if identifiers:
            plan.append(
                {
                    "mode": "identifier-first",
                    "display_mode": "按标识精确排查",
                    "label": "第 1 轮：标识精确定位",
                    "detail": f"优先使用 {', '.join(identifiers[:4])} 精确筛查相关日志。",
                    "identifiers": identifiers,
                    "focus_terms": focus_terms,
                }
            )
        plan.append(
            {
                "mode": "context-first",
                "display_mode": "按上下文重点排查",
                "label": f"第 {len(plan) + 1} 轮：问题导向收敛",
                "detail": "先尝试回答工单描述里的问题，围绕接口路径、错误码、问题现象收敛线索。",
                "identifiers": identifiers,
                "focus_terms": self._merge_terms(focus_terms, normalized_context_terms),
            }
        )
        plan.append(
            {
                "mode": "error-first",
                "display_mode": "按异常聚类排查",
                "label": f"第 {len(plan) + 1} 轮：异常优先筛查",
                "detail": "若上下文证据不足，则先 grep 高价值异常，再沿错误信息继续下钻。",
                "identifiers": identifiers,
                "focus_terms": focus_terms,
            }
        )
        return plan

    def _collect_materials(self, bundle: EvidenceBundle) -> list[dict[str, str]]:
        materials: list[dict[str, str]] = []
        for part in bundle.parts:
            details = part.details
            summary = part.summary
            if details.get("extracted_files"):
                summary = f"{summary}: {', '.join(str(item) for item in details['extracted_files'][:5])}"
            materials.append({"name": part.source_name, "type": part.source_type, "summary": summary})
        return materials[:20]

    def _collect_ranked_hits(
        self,
        bundle: EvidenceBundle,
        *,
        identifiers: list[str],
        focus_terms: list[str],
        mode: str,
    ) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        for part in bundle.parts:
            if part.source_type not in {"text_log", "zip_entry"}:
                continue
            preview = sanitize_text(part.details.get("preview", ""))
            lines = preview.splitlines()
            for index, line in enumerate(lines):
                structured = self._parse_line(line)
                score = self._score_line(structured, line, identifiers, focus_terms, mode)
                if score <= 0:
                    continue
                hits.append(self._build_hit(part.source_name, index, lines, structured, score))
        hits.sort(key=lambda item: (-int(item.get("score", 0)), int(item.get("line_no", 0))))
        return self._dedupe_hits(hits)[:20]

    @staticmethod
    def _parse_line(line: str) -> dict[str, Any]:
        text = sanitize_text(line).strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                payload = json.loads(text)
                if isinstance(payload, dict):
                    return payload
            except Exception:
                return {}
        return {}

    def _score_line(
        self,
        structured: dict[str, Any],
        line: str,
        identifiers: list[str],
        focus_terms: list[str],
        mode: str,
    ) -> int:
        text = sanitize_text(line)
        lowered = text.lower()
        score = 0
        matched_identifier = any(identifier.lower() in lowered for identifier in identifiers if identifier)
        matched_focus = any(term.lower() in lowered for term in focus_terms if term)
        if matched_identifier:
            score += 25
        if matched_focus:
            score += 18

        level = sanitize_text(structured.get("level", "")).upper()
        if level == "ERROR":
            score += 100
        elif level == "WARN":
            score += 60
        elif level == "INFO":
            score += 10
        elif level == "DEBUG":
            score -= 20

        status_code = self._coerce_int(structured.get("status_code"))
        if status_code >= 500:
            score += 120
        elif status_code >= 400:
            score += 100
        elif status_code == 200:
            score -= 15

        if any(keyword in lowered for keyword in ("error", "exception", "fail", "invalid", "denied", "panic", "timeout")):
            score += 40
        if any(keyword in text for keyword in ("错误", "异常", "失败", "超时", "下游接口数据错误", "unexpected end of json input")):
            score += 45
        if "userid is 0" in lowered:
            score += 80
        if "no results found" in lowered:
            score += 35
        if structured.get("upstream"):
            score += 10
        if structured.get("server_url"):
            score += 10
        if mode == "identifier-first" and not matched_identifier:
            score -= 20
        if mode == "context-first" and not matched_focus:
            score -= 10
        if mode == "error-first" and level in {"ERROR", "WARN"}:
            score += 20
        return score

    def _build_hit(
        self,
        source_name: str,
        index: int,
        lines: list[str],
        structured: dict[str, Any],
        score: int,
    ) -> dict[str, Any]:
        line = lines[index]
        message = sanitize_text(structured.get("msg", "")) or sanitize_text(line)
        level = sanitize_text(structured.get("level", "")) or self._infer_level(line)
        status_code = self._coerce_int(structured.get("status_code"))
        server_url = sanitize_text(structured.get("server_url", ""))
        request_id = sanitize_text(structured.get("request_id", "")) or sanitize_text(structured.get("requestId", ""))
        error_codes = _ERROR_CODE_RE.findall(message)
        context_window = self._extract_context_window(lines, index)
        summary_parts = [part for part in [level, f"HTTP {status_code}" if status_code else "", server_url, message[:180]] if part]
        return {
            "source": source_name,
            "line_no": index + 1,
            "score": score,
            "level": level,
            "status_code": status_code,
            "server_url": server_url,
            "request_id": request_id,
            "error_codes": error_codes[:3],
            "message": message[:400],
            "summary": " | ".join(summary_parts),
            "raw": sanitize_text(line)[:400],
            "context_window": context_window,
        }

    def _extract_context_window(self, lines: list[str], center_index: int) -> list[str]:
        start = max(0, center_index - _MAX_CONTEXT_LINES)
        end = min(len(lines), center_index + _MAX_CONTEXT_LINES + 1)
        window: list[str] = []
        for index in range(start, end):
            prefix = ">>" if index == center_index else "  "
            window.append(f"{prefix} L{index + 1}: {sanitize_text(lines[index])[:220]}")
        return window

    def _build_key_findings(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for hit in hits[:8]:
            parts = []
            if hit.get("level"):
                parts.append(str(hit["level"]))
            if hit.get("status_code"):
                parts.append(f"HTTP {hit['status_code']}")
            if hit.get("server_url"):
                parts.append(str(hit["server_url"]))
            if hit.get("error_codes"):
                parts.append(f"错误码 {','.join(hit['error_codes'])}")
            parts.append(str(hit.get("message", "")))
            findings.append(
                {
                    "summary": f"{hit['source']}:{hit['line_no']} - {' | '.join(part for part in parts if part)[:260]}",
                    "source": str(hit["source"]),
                    "context_window": list(hit.get("context_window", [])),
                }
            )
        return findings

    def _collect_image_clues(self, bundle: EvidenceBundle) -> list[dict[str, str]]:
        clues: list[dict[str, str]] = []
        for part in bundle.parts:
            if part.source_type == "image":
                clues.append({"source": part.source_name, "summary": "存在图片证据，可辅助核对报错文案/错误码/界面现象"})
        return clues

    def _build_judgment(self, hits: list[dict[str, Any]], context: InvestigationContextSummary) -> dict[str, str]:
        top_messages = "\n".join(str(item.get("message", "")) for item in hits[:6]).lower()
        top_urls = "\n".join(str(item.get("server_url", "")) for item in hits[:6]).lower()
        if "userid is 0" in top_messages and "/v7/brands/" in top_urls:
            return {
                "category": "请求链路问题",
                "reason": "请求已进入当前服务，但下游品牌设置接口返回 400，且日志明确提示 userid is 0，疑似用户上下文缺失导致下游调用失败。",
            }
        if any(int(item.get("status_code", 0) or 0) >= 400 for item in hits):
            return {
                "category": "下游服务异常",
                "reason": "已命中下游接口 4xx/5xx 返回，当前更像依赖接口调用失败而非单纯日志缺失。",
            }
        if "unexpected end of json input" in top_messages:
            return {"category": "服务异常", "reason": "下游返回体异常，导致反序列化失败。"}
        if any(str(item.get("level", "")) == "ERROR" for item in hits):
            return {"category": "服务异常", "reason": "已命中与当前上下文相关的 ERROR 日志，需要继续沿调用链定位根因。"}
        return {"category": "未确定", "reason": "现有材料中缺少足够强的异常命中，暂时无法稳定收敛根因。"}

    def _evaluate_answerability(
        self,
        problem_to_answer: str,
        hits: list[dict[str, Any]],
        judgment: dict[str, str],
    ) -> tuple[bool, str]:
        if not hits:
            return False, "现有日志里没有命中足够强的相关异常，无法回答工单描述中的问题。"
        top_score = max(int(item.get("score", 0)) for item in hits[:3])
        if top_score < 110:
            return False, "虽然命中了部分线索，但证据强度不足，当前结论还不能稳定回答工单问题。"
        if sanitize_text(judgment.get("category", "")) == "未确定":
            return False, "现有线索不足以形成稳定结论，暂时不能直接回答工单问题。"
        return True, ""

    def _build_missing_information(
        self,
        request: LogAnalysisRequest,
        hits: list[dict[str, Any]],
        identifiers: list[str],
        *,
        question_answered: bool,
        answer_gap_reason: str,
    ) -> list[str]:
        missing: list[str] = []
        if not request.evidence_bundle.parts:
            missing.append("当前没有可分析的日志类附件。")
        if not identifiers:
            missing.append("未提供明确的 TraceId/request_id/tradId，可补充接口路径、错误码或发生时间。")
        if not hits:
            missing.append("现有日志中未命中与工单上下文强相关的异常，建议补充更完整的入口/网关/下游日志。")
        elif max(int(item.get("score", 0)) for item in hits[:3]) < 110:
            missing.append("已命中少量线索，但相关性不足，建议补充更明确的标识或报错上下文。")
        elif len(hits) < 2:
            missing.append("当前仅命中单条异常，建议补充同一时段上下游日志以确认因果链。")
        if not question_answered and answer_gap_reason:
            missing.append(answer_gap_reason)
        return missing[:5]

    def _build_next_steps(
        self,
        judgment: dict[str, str],
        hits: list[dict[str, Any]],
        context: InvestigationContextSummary,
        missing_information: list[str],
    ) -> list[str]:
        category = sanitize_text(judgment.get("category", ""))
        suggestions: list[str] = []
        if category == "请求链路问题":
            suggestions.extend(
                [
                    "优先核对该请求对应的用户上下文是否为空，特别是 userid/companyId/sid 等鉴权字段。",
                    "继续补充网关与目标下游接口的上下游日志，确认 4xx 返回原因。",
                    "若为生产问题，建议把当前请求参数和鉴权信息同步给研发。",
                ]
            )
        elif category == "下游服务异常":
            suggestions.extend(
                [
                    "补充下游服务或网关日志，确认具体 4xx/5xx 返回体。",
                    "按当前工单上下文继续向前回溯最近一次错误分支。",
                ]
            )
        else:
            suggestions.extend(
                [
                    "补充更完整日志包，并尽量覆盖请求入口、网关、下游依赖三段日志。",
                    "优先提供 TraceId/request_id、接口路径、错误码或问题发生时间。",
                ]
            )
        if hits:
            suggestions.append(f"建议重点查看 {hits[0]['source']} 第 {hits[0]['line_no']} 行附近上下文。")
        if context.open_questions:
            suggestions.append(f"待补充：{context.open_questions[0]}")
        suggestions.extend(f"补充信息：{item}" for item in missing_information[:2])
        return suggestions[:6]

    def _build_summary(self, judgment: dict[str, str], findings: list[dict[str, Any]], question_answered: bool) -> str:
        category = sanitize_text(judgment.get("category", "未确定"))
        suffix = "，可以回答当前工单问题" if question_answered else "，但当前仍不足以完整回答工单问题"
        if findings:
            return f"{category}，已提炼 {len(findings)} 条高价值异常线索{suffix}"
        return f"{category}，未命中明显异常片段{suffix}"

    @staticmethod
    def _should_stop_loop(hits: list[dict[str, Any]], mode: str) -> bool:
        if not hits:
            return False
        top_score = max(int(hit.get("score", 0)) for hit in hits[:3])
        if mode == "identifier-first":
            return top_score >= 145 and len(hits) >= 2
        if mode == "context-first":
            return top_score >= 150 and len(hits) >= 2
        return top_score >= 155

    @staticmethod
    def _describe_round_result(hits: list[dict[str, Any]]) -> str:
        if not hits:
            return "未命中足够强的相关异常。"
        top_hit = hits[0]
        return f"命中 {len(hits)} 条候选，其中最高优先级为 {top_hit.get('source')}:{top_hit.get('line_no')}。"

    @staticmethod
    def _derive_clues_from_hits(hits: list[dict[str, Any]]) -> list[str]:
        clues: list[str] = []
        for hit in hits[:3]:
            for value in [hit.get("server_url", ""), *(hit.get("error_codes", []) or [])]:
                text = sanitize_text(value)
                if text:
                    clues.append(text)
            message = sanitize_text(hit.get("message", ""))
            for phrase in ("userid is 0", "unexpected end of json input", "no results found"):
                if phrase in message.lower():
                    clues.append(phrase)
        return clues[:6]

    @staticmethod
    def _merge_terms(base_terms: list[str], extra_terms: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for item in [*base_terms, *extra_terms]:
            text = sanitize_text(item)
            if not text or text.lower() in seen:
                continue
            seen.add(text.lower())
            merged.append(text)
        return merged[:12]

    @staticmethod
    def _total_score(hits: list[dict[str, Any]]) -> int:
        return sum(int(item.get("score", 0)) for item in hits[:5])

    @staticmethod
    def _coerce_int(value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _infer_level(line: str) -> str:
        lowered = sanitize_text(line).lower()
        if '"level":"error"' in lowered or " error " in lowered:
            return "ERROR"
        if '"level":"warn"' in lowered or " warn " in lowered:
            return "WARN"
        if '"level":"info"' in lowered or " info " in lowered:
            return "INFO"
        if '"level":"debug"' in lowered or " debug " in lowered:
            return "DEBUG"
        return ""

    @staticmethod
    def _dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for hit in hits:
            key = "|".join(
                [
                    str(hit.get("source", "")),
                    str(hit.get("level", "")),
                    str(hit.get("status_code", "")),
                    str(hit.get("server_url", "")),
                    str(hit.get("message", ""))[:120],
                ]
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(hit)
        return result

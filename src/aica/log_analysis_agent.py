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


_TRACE_RE = re.compile(
    r"(?i)(?:trace[_ -]?id|request[_ -]?id|x[-_]?request[-_]?id|trad[_ -]?id)\s*[:=\uff1a]\s*([a-zA-Z0-9_-]{4,128})"
)
_PATH_RE = re.compile(r"/[a-zA-Z0-9_./{}-]{3,}")
_ID_TOKEN_RE = re.compile(r"\b[a-zA-Z0-9][a-zA-Z0-9:_-]{5,127}\b")
_CODE_HINT_RE = re.compile(
    r"(?i)(?:error(?:_?code)?|err(?:or)?code|errno|ret(?:urn)?code|code)\s*[:=\uff1a ]+\s*([a-zA-Z]?\d{4,10})"
)
_EXCEPTION_TYPE_RE = re.compile(r"\b([A-Za-z_][\w.]*?(?:Error|Exception))\b")
_SUCCESS_MARKERS = ('"ok":true', '"error":"ok"', '"status":"success"', " status=success")
_ERROR_KEYWORDS = ("error", "failed", "fail", "invalid", "denied", "timeout", "panic", "exception", "异常", "错误", "失败", "超时")
_EXCEPTION_KEYWORDS = ("traceback", "typeerror", "referenceerror", "syntaxerror", "valueerror", "runtimeerror", "panic", "exception", "unexpected end of json input")
_REQUEST_ID_KEYS = {"request_id", "requestid", "traceid", "trace_id", "tradid", "trad_id", "x-request-id"}
_LEVEL_KEYS = {"level", "severity", "log_level"}
_STATUS_KEYS = {"status_code", "statuscode", "http_status", "httpstatus", "status"}
_PATH_KEYS = {"server_url", "uri", "url", "path", "operation", "api", "endpoint"}
_STACK_KEYS = {"stack", "traceback", "exception", "error_stack"}
_MESSAGE_KEYS = {"msg", "message", "error", "detail", "reason", "description"}
_ERROR_CODE_KEYS = {"error_code", "errorcode", "errno", "retcode", "code"}
_TRIVIAL_MESSAGES = {"ok", "success", "log_resp", "startup ok"}
_MAX_CONTEXT_LINES = 2


class DefaultLogAnalysisAgent:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm_service = llm_service

    def analyze(self, request: LogAnalysisRequest) -> LogAnalysisProducedResult:
        problem_to_answer = self._build_problem_to_answer(request)
        identifiers = self._collect_identifiers(request, problem_to_answer)
        plan = self._build_search_plan(request, identifiers, problem_to_answer)
        best_hits: list[dict[str, Any]] = []
        selected_mode = "按异常优先排查"
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
        primary_issue, judgment = self._build_judgment(best_hits)
        confidence = self._build_confidence(best_hits, judgment)
        question_answered, answer_gap_reason = self._evaluate_answerability(best_hits, judgment, confidence)
        missing_information = self._build_missing_information(request, best_hits, identifiers, question_answered=question_answered, answer_gap_reason=answer_gap_reason)
        next_steps = self._build_next_steps(judgment, best_hits, request.investigation_context, missing_information)
        result_payload = LogAnalysisResultPayload(
            analyzed_materials=self._collect_materials(request.evidence_bundle),
            problem_to_answer=problem_to_answer,
            analysis_focus={"trad_id": request.parsed_command.trad_id, "request_id": request.parsed_command.request_id, "focus_terms": list(request.parsed_command.focus_terms), "inferred_identifiers": identifiers},
            analysis_mode=selected_mode,
            investigation_steps=investigation_steps,
            primary_issue=primary_issue,
            confidence=confidence,
            evidence_items=[{"kind": item.get("kind", ""), "summary": item.get("summary", ""), "evidence": item.get("evidence", ""), "source": item.get("source", ""), "line_no": item.get("line_no", 0), "request_id": item.get("request_id", ""), "context_window": item.get("context_window", [])} for item in key_findings[:6]],
            noise_items=[],
            key_findings=key_findings,
            preliminary_judgment=judgment,
            question_answered=question_answered,
            answer_gap_reason=answer_gap_reason,
            missing_information=missing_information,
            suggested_next_steps=next_steps,
            evidence_refs=[{"source_name": part.source_name, "source_type": part.source_type} for part in request.evidence_bundle.parts],
            image_clues=self._collect_image_clues(request.evidence_bundle),
            search_hits=best_hits[:12],
        )
        return LogAnalysisProducedResult(result_payload=result_payload, result_summary=self._build_summary(judgment, key_findings, question_answered, confidence), producer_metadata={"agent": self.__class__.__name__, "model_binding_used": self._describe_model_binding()})

    def _describe_model_binding(self) -> str:
        if self._llm_service is None:
            return ""
        try:
            resolved = self._llm_service.resolve_task_model("log_analysis")
        except Exception:
            return "local-only"
        suffix = " (fallback analysis)" if resolved.fallback_used else ""
        return f"{resolved.reference.display_name}{suffix}"

    def _build_problem_to_answer(self, request: LogAnalysisRequest) -> str:
        items = [
            sanitize_text(request.todo_snapshot.get("title", "")),
            sanitize_text(request.todo_snapshot.get("current_summary", "")),
            request.investigation_context.problem_summary,
        ]
        return "；".join(item for item in items if item)[:240]

    def _collect_identifiers(self, request: LogAnalysisRequest, problem_to_answer: str) -> list[str]:
        sources = [
            request.parsed_command.trad_id,
            request.parsed_command.request_id,
            *request.parsed_command.focus_terms,
            *request.investigation_context.current_focus,
            request.investigation_context.problem_summary,
            sanitize_text(request.todo_snapshot.get("current_summary", "")),
            sanitize_text(request.todo_snapshot.get("title", "")),
            problem_to_answer,
        ]
        result: list[str] = []
        seen: set[str] = set()
        for item in sources:
            text = sanitize_text(item)
            if not text:
                continue
            candidates = [*_TRACE_RE.findall(text), *_PATH_RE.findall(text)]
            candidates.extend(token for token in _ID_TOKEN_RE.findall(text) if self._looks_like_identifier(token))
            for token in candidates:
                normalized = sanitize_text(token)
                lowered = normalized.lower()
                if normalized and lowered not in seen:
                    seen.add(lowered)
                    result.append(normalized)
        return result[:10]

    def _build_search_plan(self, request: LogAnalysisRequest, identifiers: list[str], problem_to_answer: str) -> list[dict[str, Any]]:
        focus_terms = [sanitize_text(item) for item in request.parsed_command.focus_terms if sanitize_text(item)]
        context_terms = [
            *request.investigation_context.current_focus,
            request.investigation_context.problem_summary,
            *request.investigation_context.suspected_causes,
            sanitize_text(request.todo_snapshot.get("title", "")),
            problem_to_answer,
        ]
        normalized_context_terms = [text for item in context_terms if (text := sanitize_text(item)) and len(text) <= 40 and "\n" not in text]
        plan: list[dict[str, Any]] = []
        if identifiers:
            plan.append({"mode": "identifier-first", "display_mode": "按标识精确定位", "label": "第 1 轮：标识精确定位", "detail": f"优先使用 {', '.join(identifiers[:4])} 精确筛查相关日志。", "identifiers": identifiers, "focus_terms": focus_terms})
        plan.append({"mode": "context-first", "display_mode": "按上下文重点排查", "label": f"第 {len(plan) + 1} 轮：问题导向收敛", "detail": "围绕工单描述、异常现象和接口路径收敛线索。", "identifiers": identifiers, "focus_terms": self._merge_terms(focus_terms, normalized_context_terms)})
        plan.append({"mode": "error-first", "display_mode": "按异常优先排查", "label": f"第 {len(plan) + 1} 轮：异常优先筛查", "detail": "优先锁定异常栈、ERROR/WARN 和显式失败日志。", "identifiers": identifiers, "focus_terms": focus_terms})
        return plan

    def _collect_materials(self, bundle: EvidenceBundle) -> list[dict[str, str]]:
        materials: list[dict[str, str]] = []
        for part in bundle.parts:
            summary = part.summary
            extracted = part.details.get("extracted_files")
            if extracted:
                summary = f"{summary}: {', '.join(str(item) for item in extracted[:5])}"
            materials.append({"name": part.source_name, "type": part.source_type, "summary": summary})
        return materials[:20]

    def _collect_ranked_hits(self, bundle: EvidenceBundle, *, identifiers: list[str], focus_terms: list[str], mode: str) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        for part in bundle.parts:
            if part.source_type not in {"text_log", "zip_entry"}:
                continue
            lines = sanitize_text(part.details.get("preview", "")).splitlines()
            for index, line in enumerate(lines):
                candidate = self._extract_candidate(line)
                score = self._score_candidate(candidate, identifiers, focus_terms, mode)
                if score > 0:
                    hits.append(self._build_hit(part.source_name, index, lines, candidate, score))
        hits.sort(key=lambda item: (-int(item.get("score", 0)), int(item.get("line_no", 0))))
        return self._dedupe_hits(hits)[:20]

    def _extract_candidate(self, line: str) -> dict[str, Any]:
        text = sanitize_text(line)
        structured = self._parse_line(text)
        scalars = self._walk_scalars(structured)
        level = self._extract_level(text, scalars)
        status_code = self._extract_status_code(scalars)
        request_id = self._extract_request_id(text, scalars)
        server_url = self._extract_server_url(text, scalars)
        stack = self._extract_stack(scalars)
        exception_type = self._extract_exception_type(stack or text)
        error_codes = self._extract_error_codes(text, scalars)
        success = self._is_success_line(text, structured, level, status_code, stack)
        message = self._extract_message(text, scalars, stack, server_url, request_id, success)
        kind = self._classify_candidate(level, status_code, message, stack, success)
        return {"raw": text, "level": level, "status_code": status_code, "request_id": request_id, "server_url": server_url, "stack": stack, "exception_type": exception_type, "error_codes": error_codes, "message": message, "kind": kind, "success": success}

    @staticmethod
    def _parse_line(line: str) -> dict[str, Any]:
        text = sanitize_text(line)
        if not (text.startswith("{") and text.endswith("}")):
            return {}
        try:
            payload = json.loads(text)
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _walk_scalars(self, payload: object, prefix: str = "") -> list[tuple[str, str]]:
        if isinstance(payload, dict):
            result: list[tuple[str, str]] = []
            for key, value in payload.items():
                key_text = sanitize_text(key)
                next_prefix = f"{prefix}.{key_text}" if prefix else key_text
                result.extend(self._walk_scalars(value, next_prefix))
            return result
        if isinstance(payload, list):
            result = []
            for index, value in enumerate(payload[:12]):
                result.extend(self._walk_scalars(value, f"{prefix}[{index}]"))
            return result
        text = sanitize_text(payload)
        if not text:
            return []
        key = prefix.rsplit(".", 1)[-1].split("[", 1)[0].lower()
        return [(key, text)]

    def _extract_level(self, text: str, scalars: list[tuple[str, str]]) -> str:
        for key, value in scalars:
            if key in _LEVEL_KEYS:
                return sanitize_text(value).upper()
        return self._infer_level(text)

    def _extract_status_code(self, scalars: list[tuple[str, str]]) -> int:
        for key, value in scalars:
            if key not in _STATUS_KEYS:
                continue
            parsed = self._coerce_int(value)
            if 100 <= parsed <= 599:
                return parsed
        return 0

    def _extract_request_id(self, text: str, scalars: list[tuple[str, str]]) -> str:
        for key, value in scalars:
            if key in _REQUEST_ID_KEYS and self._looks_like_identifier(value):
                return sanitize_text(value)
        matches = _TRACE_RE.findall(text)
        return sanitize_text(matches[0]) if matches else ""

    def _extract_server_url(self, text: str, scalars: list[tuple[str, str]]) -> str:
        for key, value in scalars:
            if key not in _PATH_KEYS:
                continue
            path = sanitize_text(value)
            match = _PATH_RE.search(path)
            if match:
                return sanitize_text(match.group(0))
            if key == "operation" and "_" in path:
                match = _PATH_RE.search(path.split("_", 1)[-1])
                if match:
                    return sanitize_text(match.group(0))
        match = _PATH_RE.search(text)
        return sanitize_text(match.group(0)) if match else ""

    def _extract_stack(self, scalars: list[tuple[str, str]]) -> str:
        for key, value in scalars:
            if key in _STACK_KEYS and any(marker in value.lower() for marker in _EXCEPTION_KEYWORDS):
                return sanitize_text(value)
        return ""

    def _extract_exception_type(self, text: str) -> str:
        match = _EXCEPTION_TYPE_RE.search(sanitize_text(text))
        return sanitize_text(match.group(1)) if match else ""

    def _extract_error_codes(self, text: str, scalars: list[tuple[str, str]]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for key, value in scalars:
            if key in _ERROR_CODE_KEYS and self._looks_like_error_code(value):
                normalized = sanitize_text(value)
                lowered = normalized.lower()
                if lowered not in seen:
                    seen.add(lowered)
                    result.append(normalized)
        for token in _CODE_HINT_RE.findall(text):
            normalized = sanitize_text(token)
            lowered = normalized.lower()
            if self._looks_like_error_code(normalized) and lowered not in seen:
                seen.add(lowered)
                result.append(normalized)
        return result[:3]

    def _is_success_line(self, text: str, structured: dict[str, Any], level: str, status_code: int, stack: str) -> bool:
        lowered = text.lower()
        if stack:
            return False
        if any(marker in lowered for marker in _SUCCESS_MARKERS):
            return True
        ok_value = sanitize_text(structured.get("ok", "")).lower()
        error_value = sanitize_text(structured.get("error", "")).lower()
        status_value = sanitize_text(structured.get("status", "")).lower()
        if ok_value == "true" and error_value in {"", "ok"}:
            return True
        if status_value in {"success", "ok"}:
            return True
        return level == "INFO" and status_code == 200 and not any(keyword in lowered for keyword in _ERROR_KEYWORDS)

    def _extract_message(self, text: str, scalars: list[tuple[str, str]], stack: str, server_url: str, request_id: str, success: bool) -> str:
        if stack:
            first_line = sanitize_text(stack.splitlines()[0])
            if first_line:
                return first_line[:220]
        for key, value in scalars:
            lowered = value.lower()
            if key in _MESSAGE_KEYS and lowered not in _TRIVIAL_MESSAGES and not (success and lowered in {"ok", "success"}):
                return sanitize_text(value)[:220]
        if success:
            parts = ["接口调用成功"]
            if server_url:
                parts.append(server_url)
            if request_id:
                parts.append(f"request_id={request_id}")
            return " | ".join(parts)
        return text[:220]

    def _classify_candidate(self, level: str, status_code: int, message: str, stack: str, success: bool) -> str:
        lowered = sanitize_text(message).lower()
        if stack or any(keyword in lowered for keyword in _EXCEPTION_KEYWORDS):
            return "exception"
        if status_code >= 400:
            return "error_response"
        if success:
            return "success"
        if level == "ERROR" or any(keyword in lowered for keyword in _ERROR_KEYWORDS):
            return "error"
        if level == "WARN":
            return "warning"
        return "context"

    def _score_candidate(self, candidate: dict[str, Any], identifiers: list[str], focus_terms: list[str], mode: str) -> int:
        raw_text = sanitize_text(candidate.get("raw", "")).lower()
        kind = sanitize_text(candidate.get("kind", ""))
        score = 0
        matched_identifier = any(identifier.lower() in raw_text for identifier in identifiers if identifier)
        matched_focus = any(term.lower() in raw_text for term in focus_terms if term)
        if matched_identifier:
            score += 60
        if matched_focus:
            score += 18
        score += {"exception": 160, "error_response": 130, "error": 100, "warning": 40, "context": 5, "success": -110}.get(kind, 0)
        level = sanitize_text(candidate.get("level", "")).upper()
        score += {"ERROR": 45, "WARN": 20, "INFO": -5, "DEBUG": -20}.get(level, 0)
        status_code = int(candidate.get("status_code", 0) or 0)
        if status_code >= 500:
            score += 70
        elif status_code >= 400:
            score += 55
        elif status_code == 200:
            score -= 20
        if candidate.get("stack"):
            score += 45
        if candidate.get("exception_type"):
            score += 45
        if candidate.get("error_codes"):
            score += 20
        if mode == "identifier-first" and not matched_identifier:
            score -= 35
        if mode == "context-first" and not matched_focus:
            score -= 15
        if mode == "error-first" and kind not in {"exception", "error_response", "error", "warning"}:
            score -= 25
        return score

    def _build_hit(self, source_name: str, index: int, lines: list[str], candidate: dict[str, Any], score: int) -> dict[str, Any]:
        return {
            "source": source_name,
            "line_no": index + 1,
            "score": score,
            "kind": candidate.get("kind", ""),
            "level": candidate.get("level", ""),
            "status_code": int(candidate.get("status_code", 0) or 0),
            "server_url": candidate.get("server_url", ""),
            "request_id": candidate.get("request_id", ""),
            "error_codes": list(candidate.get("error_codes", [])),
            "exception_type": candidate.get("exception_type", ""),
            "message": sanitize_text(candidate.get("message", ""))[:400],
            "summary": self._build_hit_summary(candidate, index + 1),
            "evidence": self._build_hit_evidence(candidate),
            "raw": sanitize_text(candidate.get("raw", ""))[:400],
            "context_window": self._extract_context_window(lines, index),
            "success": bool(candidate.get("success", False)),
        }

    def _build_hit_summary(self, candidate: dict[str, Any], line_no: int) -> str:
        kind = sanitize_text(candidate.get("kind", ""))
        message = sanitize_text(candidate.get("message", ""))
        exception_type = sanitize_text(candidate.get("exception_type", ""))
        status_code = int(candidate.get("status_code", 0) or 0)
        server_url = sanitize_text(candidate.get("server_url", ""))
        error_codes = [sanitize_text(item) for item in candidate.get("error_codes", []) if sanitize_text(item)]
        if kind == "exception":
            prefix = f"第 {line_no} 行命中异常"
            if exception_type:
                prefix = f"{prefix} {exception_type}"
            return f"{prefix}：{message[:160]}"
        if kind == "error_response":
            detail = f"HTTP {status_code}"
            if server_url:
                detail = f"{detail} {server_url}"
            return f"第 {line_no} 行命中接口异常：{detail}"
        if error_codes:
            return f"第 {line_no} 行命中错误码 {','.join(error_codes[:2])}：{message[:160]}"
        if kind == "warning":
            return f"第 {line_no} 行命中告警：{message[:160]}"
        if kind == "error":
            return f"第 {line_no} 行命中错误：{message[:160]}"
        return f"第 {line_no} 行相关线索：{message[:160]}"

    def _build_hit_evidence(self, candidate: dict[str, Any]) -> str:
        parts: list[str] = []
        if sanitize_text(candidate.get("exception_type", "")):
            parts.append(sanitize_text(candidate.get("exception_type", "")))
        status_code = int(candidate.get("status_code", 0) or 0)
        if status_code:
            parts.append(f"HTTP {status_code}")
        if sanitize_text(candidate.get("server_url", "")):
            parts.append(sanitize_text(candidate.get("server_url", "")))
        if sanitize_text(candidate.get("request_id", "")):
            parts.append(f"request_id={sanitize_text(candidate.get('request_id', ''))}")
        error_codes = [sanitize_text(item) for item in candidate.get("error_codes", []) if sanitize_text(item)]
        if error_codes:
            parts.append(f"错误码 {','.join(error_codes[:2])}")
        return " | ".join(parts)

    def _extract_context_window(self, lines: list[str], center_index: int) -> list[str]:
        start = max(0, center_index - _MAX_CONTEXT_LINES)
        end = min(len(lines), center_index + _MAX_CONTEXT_LINES + 1)
        result: list[str] = []
        for index in range(start, end):
            prefix = ">>" if index == center_index else "  "
            result.append(f"{prefix} L{index + 1}: {sanitize_text(lines[index])[:220]}")
        return result

    def _build_key_findings(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{"kind": str(hit.get("kind", "")), "summary": str(hit.get("summary", "")), "evidence": str(hit.get("evidence", "")), "source": str(hit.get("source", "")), "line_no": int(hit.get("line_no", 0) or 0), "request_id": str(hit.get("request_id", "")), "context_window": list(hit.get("context_window", []))} for hit in hits[:8]]

    def _collect_image_clues(self, bundle: EvidenceBundle) -> list[dict[str, str]]:
        return [{"source": part.source_name, "summary": "存在图片证据，可辅助核对报错文案、错误码或界面现象。"} for part in bundle.parts if part.source_type == "image"]

    def _build_judgment(self, hits: list[dict[str, Any]]) -> tuple[str, dict[str, str]]:
        if not hits:
            reason = "现有材料里没有命中足够强的异常证据，暂时无法稳定定位根因。"
            return reason, {"category": "未发现明确异常", "reason": reason}
        top_hit = hits[0]
        top_kind = sanitize_text(top_hit.get("kind", ""))
        top_messages = "\n".join(sanitize_text(item.get("message", "")) for item in hits[:3]).lower()
        top_urls = "\n".join(sanitize_text(item.get("server_url", "")) for item in hits[:3]).lower()
        if "userid is 0" in top_messages and "/v7/brands/" in top_urls:
            reason = "已命中下游接口异常，并出现 userid is 0，更像请求上下文缺失导致的链路问题。"
            return reason, {"category": "请求链路问题", "reason": reason}
        if any(int(item.get("status_code", 0) or 0) >= 400 for item in hits[:3]):
            reason = "已命中 4xx/5xx 返回，当前更像下游接口调用失败，而不是日志不足。"
            return reason, {"category": "下游服务异常", "reason": reason}
        if top_kind == "exception":
            exception_type = sanitize_text(top_hit.get("exception_type", "")) or "异常"
            if exception_type.endswith("Error"):
                reason = f"已命中明确异常栈，当前更像前端渲染或文档兼容问题，核心异常为 {exception_type}。"
                return reason, {"category": "前端异常", "reason": reason}
            reason = f"已命中明确异常栈，当前主要异常为 {exception_type}，可以直接沿异常栈继续排查。"
            return reason, {"category": "服务异常", "reason": reason}
        reason = "已命中与工单相关的异常线索，但还需要更多上下游证据补强结论。"
        return reason, {"category": "存在异常线索", "reason": reason}

    def _build_confidence(self, hits: list[dict[str, Any]], judgment: dict[str, str]) -> str:
        if not hits or sanitize_text(judgment.get("category", "")) == "未发现明确异常":
            return "low"
        top_hit = hits[0]
        top_score = int(top_hit.get("score", 0) or 0)
        if sanitize_text(top_hit.get("kind", "")) == "exception" and top_score >= 180:
            return "high"
        if top_score >= 140:
            return "medium"
        return "low"

    def _evaluate_answerability(self, hits: list[dict[str, Any]], judgment: dict[str, str], confidence: str) -> tuple[bool, str]:
        if not hits:
            return False, "现有日志里没有命中足够强的相关异常，无法直接回答工单里的问题。"
        if sanitize_text(hits[0].get("kind", "")) in {"exception", "error_response"} or confidence == "high":
            return True, ""
        if sanitize_text(judgment.get("category", "")) == "未发现明确异常":
            return False, "现有线索不足以形成稳定结论，暂时不能直接回答工单问题。"
        return False, "虽然命中了部分线索，但证据强度仍不足，当前结论还不够稳定。"

    def _build_missing_information(self, request: LogAnalysisRequest, hits: list[dict[str, Any]], identifiers: list[str], *, question_answered: bool, answer_gap_reason: str) -> list[str]:
        missing: list[str] = []
        if not request.evidence_bundle.parts:
            missing.append("当前没有可分析的日志类附件。")
        if not identifiers:
            missing.append("缺少明确的 TraceId/request_id/tradId，建议补充接口路径、错误码或问题发生时间。")
        if not hits:
            missing.append("现有日志里没有命中与工单强相关的异常，建议补充更完整的入口、网关和下游日志。")
        elif len(hits) < 2 and not question_answered:
            missing.append("当前只命中少量异常线索，建议补充同一时间段的上下游日志以确认因果链。")
        if not question_answered and answer_gap_reason:
            missing.append(answer_gap_reason)
        return missing[:5]

    def _build_next_steps(self, judgment: dict[str, str], hits: list[dict[str, Any]], context: InvestigationContextSummary, missing_information: list[str]) -> list[str]:
        category = sanitize_text(judgment.get("category", ""))
        suggestions: list[str] = []
        if category == "请求链路问题":
            suggestions.extend(["优先核对该请求对应的用户上下文是否为空，特别是 userid/companyId/sid 等鉴权字段。", "继续补充网关与下游接口日志，确认 4xx 返回的真实原因。"])
        elif category == "下游服务异常":
            suggestions.extend(["补充下游服务或网关日志，确认具体 4xx/5xx 返回体。", "按当前工单上下文继续向前回溯最近一次错误分支。"])
        elif category == "前端异常":
            suggestions.extend(["优先核对触发异常的文档内容、对象结构和前端渲染参数，确认是否存在缺失字段。", "结合异常栈定位对应前端资源版本，确认是否为版本兼容或特定文档触发。"])
        else:
            suggestions.extend(["补充更完整日志包，并尽量覆盖请求入口、网关、下游依赖三段日志。", "优先提供 TraceId/request_id、接口路径、错误码或问题发生时间。"])
        if hits:
            suggestions.append(f"建议重点查看 {hits[0]['source']} 第 {hits[0]['line_no']} 行附近上下文。")
        if context.open_questions:
            suggestions.append(f"待补充：{context.open_questions[0]}")
        suggestions.extend(f"补充信息：{item}" for item in missing_information[:2])
        return suggestions[:6]

    def _build_summary(self, judgment: dict[str, str], findings: list[dict[str, Any]], question_answered: bool, confidence: str) -> str:
        category = sanitize_text(judgment.get("category", "未发现明确异常"))
        if findings:
            suffix = "可以直接回答当前工单问题" if question_answered else "但当前仍不足以完整回答工单问题"
            return f"{category}，已提炼 {len(findings)} 条关键证据，置信度 {confidence}，{suffix}"
        return f"{category}，当前未命中明确异常片段"

    @staticmethod
    def _should_stop_loop(hits: list[dict[str, Any]], mode: str) -> bool:
        if not hits:
            return False
        top_score = max(int(hit.get("score", 0) or 0) for hit in hits[:3])
        top_kind = sanitize_text(hits[0].get("kind", ""))
        if top_kind == "exception" and top_score >= 170:
            return True
        if mode == "identifier-first":
            return top_score >= 170 and len(hits) >= 2
        if mode == "context-first":
            return top_score >= 180 and len(hits) >= 2
        return top_score >= 190

    @staticmethod
    def _describe_round_result(hits: list[dict[str, Any]]) -> str:
        if not hits:
            return "未命中足够强的相关异常。"
        return f"命中 {len(hits)} 条候选，其中最高优先级为 {hits[0].get('source')}:{hits[0].get('line_no')}。"

    @staticmethod
    def _derive_clues_from_hits(hits: list[dict[str, Any]]) -> list[str]:
        clues: list[str] = []
        for hit in hits[:3]:
            for value in [hit.get("server_url", ""), hit.get("request_id", ""), *(hit.get("error_codes", []) or [])]:
                text = sanitize_text(value)
                if text:
                    clues.append(text)
        return clues[:6]

    @staticmethod
    def _merge_terms(base_terms: list[str], extra_terms: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in [*base_terms, *extra_terms]:
            text = sanitize_text(item)
            lowered = text.lower()
            if text and lowered not in seen:
                seen.add(lowered)
                result.append(text)
        return result[:12]

    @staticmethod
    def _total_score(hits: list[dict[str, Any]]) -> int:
        return sum(int(item.get("score", 0) or 0) for item in hits[:5])

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
            key = "|".join([str(hit.get("source", "")), str(hit.get("kind", "")), str(hit.get("status_code", "")), str(hit.get("exception_type", "")), str(hit.get("message", ""))[:120]])
            if key not in seen:
                seen.add(key)
                result.append(hit)
        return result

    @staticmethod
    def _looks_like_identifier(token: str) -> bool:
        text = sanitize_text(token)
        if len(text) < 6 or len(text) > 128 or any(char.isspace() for char in text):
            return False
        return any(char.isdigit() for char in text) or ":" in text or "_" in text or "-" in text

    @staticmethod
    def _looks_like_error_code(token: str) -> bool:
        digits = "".join(char for char in sanitize_text(token) if char.isdigit())
        return 4 <= len(digits) <= 10

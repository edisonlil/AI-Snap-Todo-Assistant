"""Structured log analysis agent with request-chain attribution and LLM fallback."""
from __future__ import annotations

import json
import re
from typing import Any

from .llm.service import LLMService
from .llm.types import Message
from .log_analysis_models import (
    EvidenceBundle,
    InvestigationContextSummary,
    LogAnalysisProducedResult,
    LogAnalysisRequest,
    LogAnalysisResultPayload,
)
from .text_sanitize import sanitize_text


_TRACE_RE = re.compile(
    r"(?i)(?:trace[_ -]?id|request[_ -]?id|requestid|x[-_]?request[-_]?id|trad[_ -]?id)\s*[:=\uff1a]\s*([a-zA-Z0-9_-]{4,128})"
)
_NAMED_ID_RE = re.compile(
    r"(?i)\b(trace[_ -]?id|request[_ -]?id|requestid|trad[_ -]?id|app[_ -]?id|appid|file[_ -]?id|fileid|error[_ -]?code|errno|code)\b\s*[:=\uff1a]\s*([^\s,&\"']{2,128})"
)
_URL_PARAM_RE = re.compile(r"(?i)(?:[?&]|^)([a-zA-Z0-9_]+)=([a-zA-Z0-9._:-]{3,128})")
_PATH_RE = re.compile(r"/[a-zA-Z0-9_./{}:-]{3,}")
_ID_TOKEN_RE = re.compile(r"\b[a-zA-Z0-9][a-zA-Z0-9:_=-]{5,127}\b")
_HTTP_CODE_RE = re.compile(r"(?i)\bhttp\s*([45]\d{2})\b")
_STATUS_RE = re.compile(r"\b([1-5]\d{2})\b")
_EXCEPTION_TYPE_RE = re.compile(r"\b([A-Za-z_][\w.]*?(?:Error|Exception))\b")
_KEY_VALUE_QUOTED_RE = r'(?i)\b{key}\b\s*[:=]\s*"([^"]+)"'
_KEY_VALUE_BARE_RE = r"(?i)\b{key}\b\s*[:=]\s*([^\s,\]]+)"
_SUCCESS_MARKERS = ('"ok":true', '"error":"ok"', '"status":"success"', " status=success")
_ERROR_KEYWORDS = ("error", "failed", "fail", "invalid", "denied", "timeout", "panic", "exception", "forbidden")
_PERMISSION_KEYWORDS = ("denied", "forbidden", "permission", "unauthorized", "auth")
_EXCEPTION_KEYWORDS = ("traceback", "typeerror", "referenceerror", "syntaxerror", "valueerror", "runtimeerror", "panic", "exception", "unexpected end of json input")
_REQUEST_ID_KEYS = {"request_id", "requestid", "traceid", "trace_id", "tradid", "trad_id", "x-request-id"}
_LEVEL_KEYS = {"level", "severity", "log_level"}
_STATUS_KEYS = {"status_code", "statuscode", "http_status", "httpstatus", "status"}
_PATH_KEYS = {"server_url", "uri", "url", "path", "operation", "api", "endpoint", "detail"}
_STACK_KEYS = {"stack", "traceback", "exception", "error_stack"}
_MESSAGE_KEYS = {"msg", "message", "error", "detail", "reason", "description"}
_ERROR_CODE_KEYS = {"error_code", "errorcode", "retcode"}
_COMPONENT_KEYS = {"hostname", "service", "component", "module", "logger"}
_FILE_ID_KEYS = {"fileid", "file_id", "id", "param.id"}
_APP_ID_KEYS = {"app_id", "appid"}
_OPERATION_KEYS = {"operation", "method", "rpc", "server_url"}
_TYPE_KEYS = {"param.type", "type", "filetype"}
_TRIVIAL_MESSAGES = {"ok", "success", "log_resp", "startup ok"}
_MAX_CONTEXT_LINES = 2
_MAX_HITS = 24
_LLM_SYSTEM_PROMPT = (
    "你是一位日志排查助手。"
    "你必须只基于给定证据输出 JSON，不得脑补。"
    "日志证据优先于工单现象文案。"
    "当日志已经命中稳定错误签名或闭合链路时，不要输出“证据不足”。"
)


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

        chain_summary = self._build_request_chain(best_hits)
        primary_issue, judgment, root_cause_signature = self._build_judgment(best_hits, chain_summary)
        confidence = self._build_confidence(best_hits, chain_summary, judgment)
        question_answered, answer_gap_reason = self._evaluate_answerability(
            best_hits,
            chain_summary,
            root_cause_signature,
            judgment,
            confidence,
        )
        affected_entities = self._collect_affected_entities(best_hits, chain_summary)
        key_findings = self._build_key_findings(best_hits)
        evidence_items = self._build_evidence_items(best_hits, chain_summary)
        missing_information = self._build_missing_information(
            request,
            best_hits,
            identifiers,
            question_answered=question_answered,
            answer_gap_reason=answer_gap_reason,
            root_cause_signature=root_cause_signature,
        )
        next_steps = self._build_next_steps(
            judgment,
            chain_summary,
            request.investigation_context,
            missing_information,
            affected_entities,
        )
        payload = LogAnalysisResultPayload(
            analyzed_materials=self._collect_materials(request.evidence_bundle),
            problem_to_answer=problem_to_answer,
            analysis_focus={
                "trad_id": request.parsed_command.trad_id,
                "request_id": request.parsed_command.request_id,
                "focus_terms": list(request.parsed_command.focus_terms),
                "inferred_identifiers": identifiers,
            },
            analysis_mode=selected_mode,
            investigation_steps=investigation_steps,
            primary_issue=primary_issue,
            confidence=confidence,
            evidence_items=evidence_items,
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
            root_cause_signature=root_cause_signature,
            request_chain=chain_summary,
            affected_entities=affected_entities,
            log_vs_ticket_note="以日志证据为主完成归因，工单现象描述仅作为检索线索。",
        )
        payload = self._enhance_with_llm(request, payload)
        result_summary = self._build_summary(
            payload.preliminary_judgment,
            payload.key_findings,
            payload.question_answered,
            payload.confidence,
        )
        return LogAnalysisProducedResult(
            result_payload=payload,
            result_summary=result_summary,
            producer_metadata={
                "agent": self.__class__.__name__,
                "model_binding_used": self._describe_model_binding(),
            },
        )

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
        return "；".join(item for item in items if item)[:320]

    def _collect_identifiers(self, request: LogAnalysisRequest, problem_to_answer: str) -> list[str]:
        sources = [
            request.parsed_command.trad_id and f"tradId={request.parsed_command.trad_id}",
            request.parsed_command.request_id and f"request_id={request.parsed_command.request_id}",
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
            candidates: list[str] = []
            candidates.extend(self._extract_identifier_pairs(text))
            candidates.extend(_PATH_RE.findall(text))
            candidates.extend(token for token in _ID_TOKEN_RE.findall(text) if self._looks_like_identifier(token))
            for token in candidates:
                normalized = sanitize_text(token)
                lowered = normalized.lower()
                if normalized and lowered not in seen and self._should_keep_identifier(normalized):
                    seen.add(lowered)
                    result.append(normalized)
        return result[:16]

    def _extract_identifier_pairs(self, text: str) -> list[str]:
        candidates: list[str] = []
        for key, value in _NAMED_ID_RE.findall(text):
            normalized_key = sanitize_text(key).replace(" ", "").replace("-", "_").lower()
            normalized_value = sanitize_text(value).strip("\"'")
            if not normalized_value:
                continue
            if normalized_key in {"appid", "app_id"}:
                candidates.append(f"app_id={normalized_value}")
            elif normalized_key in {"fileid", "file_id"}:
                candidates.append(f"file_id={normalized_value}")
            elif normalized_key in {"requestid", "request_id"}:
                candidates.append(f"request_id={normalized_value}")
            elif normalized_key in {"traceid", "trace_id"}:
                candidates.append(f"traceid={normalized_value}")
            elif normalized_key in {"tradid", "trad_id"}:
                candidates.append(f"tradId={normalized_value}")
            else:
                candidates.append(f"{normalized_key}={normalized_value}")
        for value in _TRACE_RE.findall(text):
            candidates.append(f"request_id={sanitize_text(value)}")
        for key, value in _URL_PARAM_RE.findall(text):
            normalized_key = sanitize_text(key).lower()
            normalized_value = sanitize_text(value)
            if normalized_key in {"requestid", "request_id"}:
                candidates.append(f"request_id={normalized_value}")
            elif normalized_key in {"traceid", "trace_id"}:
                candidates.append(f"traceid={normalized_value}")
            elif normalized_key in {"appid", "app_id", "w_third_appid"}:
                candidates.append(f"app_id={normalized_value}")
            elif normalized_key in {"fileid", "file_id", "w_third_file_id"}:
                candidates.append(f"file_id={normalized_value}")
            elif self._looks_like_identifier(normalized_value):
                candidates.append(f"{normalized_key}={normalized_value}")
        return candidates

    def _build_search_plan(self, request: LogAnalysisRequest, identifiers: list[str], problem_to_answer: str) -> list[dict[str, Any]]:
        focus_terms = [sanitize_text(item) for item in request.parsed_command.focus_terms if sanitize_text(item)]
        context_terms = [
            *request.investigation_context.current_focus,
            request.investigation_context.problem_summary,
            *request.investigation_context.suspected_causes,
            sanitize_text(request.todo_snapshot.get("title", "")),
            problem_to_answer,
        ]
        normalized_context_terms = [
            text
            for item in context_terms
            if (text := sanitize_text(item)) and len(text) <= 80 and "\n" not in text
        ]
        plan: list[dict[str, Any]] = []
        if identifiers:
            plan.append(
                {
                    "mode": "identifier-first",
                    "display_mode": "按标识精准定位",
                    "label": "第 1 轮：按标识精准定位",
                    "detail": f"优先使用 {', '.join(identifiers[:4])} 定位同一请求链路。",
                    "identifiers": identifiers,
                    "focus_terms": focus_terms,
                }
            )
        plan.append(
            {
                "mode": "context-first",
                "display_mode": "按上下文重点排查",
                "label": f"第 {len(plan) + 1} 轮：按问题上下文排查",
                "detail": "结合工单标题、当前摘要、接口路径和错误现象补全检索范围。",
                "identifiers": identifiers,
                "focus_terms": self._merge_terms(focus_terms, normalized_context_terms),
            }
        )
        plan.append(
            {
                "mode": "error-first",
                "display_mode": "按异常聚类排查",
                "label": f"第 {len(plan) + 1} 轮：按异常聚类排查",
                "detail": "优先锁定 ERROR/WARN、异常栈和非 2xx 错误响应。",
                "identifiers": identifiers,
                "focus_terms": focus_terms,
            }
        )
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
            lines = self._extract_part_lines(part)
            for index, line in enumerate(lines):
                candidate = self._extract_candidate(line, part.source_name)
                score = self._score_candidate(candidate, identifiers, focus_terms, mode)
                if score > 0:
                    hits.append(self._build_hit(part.source_name, index, lines, candidate, score))
        hits.sort(key=lambda item: (-int(item.get("score", 0)), int(item.get("line_no", 0))))
        return self._dedupe_hits(hits)[:_MAX_HITS]

    def _extract_part_lines(self, part: Any) -> list[str]:
        details = part.details if isinstance(part.details, dict) else {}
        lines = details.get("line_samples")
        if isinstance(lines, list) and lines:
            return [sanitize_text(item) for item in lines if sanitize_text(item)]
        excerpt = sanitize_text(details.get("text_excerpt", "")) or sanitize_text(details.get("preview", ""))
        return excerpt.splitlines()

    def _extract_candidate(self, line: str, source_name: str) -> dict[str, Any]:
        text = sanitize_text(line)
        structured = self._parse_line(text)
        scalars = self._walk_scalars(structured)
        level = self._extract_level(text, scalars)
        status_code = self._extract_status_code(text, scalars)
        request_id = self._extract_request_id(text, scalars)
        trace_id = self._extract_trace_id(text, scalars)
        server_url = self._extract_server_url(text, scalars)
        operation = self._extract_named_field(text, scalars, _OPERATION_KEYS)
        stack = self._extract_stack(scalars)
        exception_type = self._extract_exception_type(stack or text)
        error_codes = self._extract_error_codes(text, scalars)
        code_label = self._extract_code_label(text, scalars)
        errno = self._extract_errno(text, scalars)
        app_id = self._extract_named_field(text, scalars, _APP_ID_KEYS)
        file_id = self._extract_named_field(text, scalars, _FILE_ID_KEYS)
        file_type = self._extract_named_field(text, scalars, _TYPE_KEYS)
        permission = self._extract_named_field(text, scalars, {"permission"})
        ok_value = self._extract_named_field(text, scalars, {"ok"})
        detail = self._extract_named_field(text, scalars, {"detail"})
        source_component = self._extract_source_component(text, scalars, source_name)
        success = self._is_success_line(text, structured, level, status_code, stack)
        message = self._extract_message(text, scalars, stack, server_url, request_id or trace_id, success)
        kind = self._classify_candidate(level, status_code, message, stack, success)
        return {
            "raw": text,
            "level": level,
            "status_code": status_code,
            "request_id": request_id,
            "trace_id": trace_id,
            "server_url": server_url,
            "operation": operation,
            "stack": stack,
            "exception_type": exception_type,
            "error_codes": error_codes,
            "code_label": code_label,
            "errno": errno,
            "message": message,
            "detail": detail,
            "kind": kind,
            "success": success,
            "app_id": app_id,
            "file_id": file_id,
            "file_type": file_type,
            "permission": permission,
            "ok": ok_value,
            "source_component": source_component,
            "signature": self._build_signature(request_id or trace_id, operation or server_url, code_label, errno, detail or message),
        }

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
            for index, value in enumerate(payload[:20]):
                result.extend(self._walk_scalars(value, f"{prefix}[{index}]"))
            return result
        text = sanitize_text(payload)
        if not text:
            return []
        return [(prefix.lower(), text)]

    def _extract_level(self, text: str, scalars: list[tuple[str, str]]) -> str:
        value = self._extract_from_scalars(scalars, _LEVEL_KEYS)
        return sanitize_text(value).upper() if value else self._infer_level(text)

    def _extract_status_code(self, text: str, scalars: list[tuple[str, str]]) -> int:
        value = self._extract_from_scalars(scalars, _STATUS_KEYS)
        if value:
            parsed = self._coerce_int(value)
            if 100 <= parsed <= 599:
                return parsed
        for token in _HTTP_CODE_RE.findall(text):
            parsed = self._coerce_int(token)
            if 400 <= parsed <= 599:
                return parsed
        return 0

    def _extract_request_id(self, text: str, scalars: list[tuple[str, str]]) -> str:
        value = self._extract_from_scalars(scalars, {"request_id", "requestid", "x-request-id", "tradid", "trad_id"})
        if self._looks_like_identifier(value):
            return sanitize_text(value)
        for key, value in _NAMED_ID_RE.findall(text):
            if sanitize_text(key).replace(" ", "").replace("-", "_").lower() in {"requestid", "request_id", "tradid", "trad_id"}:
                return sanitize_text(value).strip("\"'")
        return ""

    def _extract_trace_id(self, text: str, scalars: list[tuple[str, str]]) -> str:
        value = self._extract_from_scalars(scalars, {"traceid", "trace_id"})
        if self._looks_like_identifier(value):
            return sanitize_text(value)
        matches = _TRACE_RE.findall(text)
        return sanitize_text(matches[0]) if matches else ""

    def _extract_server_url(self, text: str, scalars: list[tuple[str, str]]) -> str:
        for key, value in scalars:
            leaf = self._leaf_key(key)
            if leaf not in _PATH_KEYS and key not in _PATH_KEYS:
                continue
            path = self._extract_path_from_value(value)
            if path:
                return path
        return self._extract_path_from_value(text)

    def _extract_stack(self, scalars: list[tuple[str, str]]) -> str:
        for key, value in scalars:
            leaf = self._leaf_key(key)
            if leaf in _STACK_KEYS and any(marker in value.lower() for marker in _EXCEPTION_KEYWORDS):
                return sanitize_text(value)
        return ""

    def _extract_exception_type(self, text: str) -> str:
        match = _EXCEPTION_TYPE_RE.search(sanitize_text(text))
        return sanitize_text(match.group(1)) if match else ""

    def _extract_error_codes(self, text: str, scalars: list[tuple[str, str]]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for key, value in scalars:
            leaf = self._leaf_key(key)
            if leaf not in _ERROR_CODE_KEYS:
                continue
            normalized = sanitize_text(value)
            if self._looks_like_error_code(normalized) and normalized.lower() not in seen:
                seen.add(normalized.lower())
                result.append(normalized)
        for token in re.findall(r"(?i)\b(?:error(?:_?code)?|ret(?:urn)?code)\b\s*[:=\uff1a ]+\s*([A-Za-z]?\d{4,10})", text):
            normalized = sanitize_text(token)
            if self._looks_like_error_code(normalized) and normalized.lower() not in seen:
                seen.add(normalized.lower())
                result.append(normalized)
        return result[:3]

    def _extract_code_label(self, text: str, scalars: list[tuple[str, str]]) -> str:
        for key, value in scalars:
            leaf = self._leaf_key(key)
            if leaf not in {"code", "result", "error"}:
                continue
            normalized = sanitize_text(value)
            lowered = normalized.lower()
            if lowered in _TRIVIAL_MESSAGES or lowered in {"true", "false"}:
                continue
            if self._looks_like_symbolic_code(normalized):
                return normalized
        for name in ("code", "result", "error"):
            extracted = self._extract_raw_named_value(text, name)
            if self._looks_like_symbolic_code(extracted):
                return extracted
        return ""

    def _extract_errno(self, text: str, scalars: list[tuple[str, str]]) -> str:
        for key, value in scalars:
            leaf = self._leaf_key(key)
            if leaf != "errno":
                continue
            normalized = sanitize_text(value)
            if self._looks_like_symbolic_code(normalized):
                return normalized
        return self._extract_raw_named_value(text, "errno")

    def _extract_source_component(self, text: str, scalars: list[tuple[str, str]], source_name: str) -> str:
        value = self._extract_from_scalars(scalars, _COMPONENT_KEYS)
        if value:
            return sanitize_text(value)
        match = re.match(r"^\S+\s+\S+\s+([^\s[]+)", text)
        if match:
            return sanitize_text(match.group(1))
        return sanitize_text(source_name)

    def _extract_named_field(self, text: str, scalars: list[tuple[str, str]], names: set[str]) -> str:
        value = self._extract_from_scalars(scalars, names)
        if value:
            return sanitize_text(value)
        for name in names:
            extracted = self._extract_raw_named_value(text, name)
            if extracted:
                return extracted
        return ""

    def _extract_message(
        self,
        text: str,
        scalars: list[tuple[str, str]],
        stack: str,
        server_url: str,
        request_id: str,
        success: bool,
    ) -> str:
        if stack:
            first_line = sanitize_text(stack.splitlines()[0])
            if first_line:
                return first_line[:220]
        for key, value in scalars:
            leaf = self._leaf_key(key)
            lowered = value.lower()
            if leaf in _MESSAGE_KEYS and lowered not in _TRIVIAL_MESSAGES and not (success and lowered in {"ok", "success"}):
                return sanitize_text(value)[:220]
        if success:
            parts = ["接口调用成功"]
            if server_url:
                parts.append(server_url)
            if request_id:
                parts.append(f"request_id={request_id}")
            return " | ".join(parts)
        return text[:220]

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
        score = 0
        matched_identifier = any(identifier.lower() in raw_text for identifier in identifiers if identifier)
        matched_focus = any(term.lower() in raw_text for term in focus_terms if term)
        kind = sanitize_text(candidate.get("kind", ""))
        if matched_identifier:
            score += 70
        if matched_focus:
            score += 20
        score += {"exception": 170, "error_response": 135, "error": 105, "warning": 45, "context": 6, "success": -110}.get(kind, 0)
        level = sanitize_text(candidate.get("level", "")).upper()
        score += {"ERROR": 45, "WARN": 18, "INFO": -6, "DEBUG": -24}.get(level, 0)
        status_code = int(candidate.get("status_code", 0) or 0)
        if status_code >= 500:
            score += 72
        elif status_code >= 400:
            score += 55
        elif status_code == 200:
            score -= 18
        if candidate.get("stack"):
            score += 45
        if candidate.get("exception_type"):
            score += 30
        if candidate.get("code_label"):
            score += 24
        if candidate.get("errno"):
            score += 30
        if candidate.get("server_url"):
            score += 10
        if candidate.get("request_id") or candidate.get("trace_id"):
            score += 18
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
            "operation": candidate.get("operation", ""),
            "request_id": candidate.get("request_id", "") or candidate.get("trace_id", ""),
            "trace_id": candidate.get("trace_id", ""),
            "error_codes": list(candidate.get("error_codes", [])),
            "code_label": candidate.get("code_label", ""),
            "errno": candidate.get("errno", ""),
            "exception_type": candidate.get("exception_type", ""),
            "message": sanitize_text(candidate.get("message", ""))[:400],
            "detail": sanitize_text(candidate.get("detail", ""))[:400],
            "summary": self._build_hit_summary(candidate, index + 1),
            "evidence": self._build_hit_evidence(candidate),
            "raw": sanitize_text(candidate.get("raw", ""))[:400],
            "context_window": self._extract_context_window(lines, index),
            "success": bool(candidate.get("success", False)),
            "source_component": candidate.get("source_component", ""),
            "app_id": candidate.get("app_id", ""),
            "file_id": candidate.get("file_id", ""),
            "file_type": candidate.get("file_type", ""),
            "permission": candidate.get("permission", ""),
            "signature": candidate.get("signature", ""),
            "stage": self._infer_stage(candidate),
        }

    def _build_hit_summary(self, candidate: dict[str, Any], line_no: int) -> str:
        kind = sanitize_text(candidate.get("kind", ""))
        message = sanitize_text(candidate.get("message", ""))
        exception_type = sanitize_text(candidate.get("exception_type", ""))
        status_code = int(candidate.get("status_code", 0) or 0)
        server_url = sanitize_text(candidate.get("server_url", ""))
        code_label = sanitize_text(candidate.get("code_label", ""))
        errno = sanitize_text(candidate.get("errno", ""))
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
        if code_label or errno:
            label = " / ".join(part for part in [code_label, errno] if part)
            return f"第 {line_no} 行命中错误签名 {label}：{message[:160]}"
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
        for key in ("server_url", "operation"):
            value = sanitize_text(candidate.get(key, ""))
            if value and value not in parts:
                parts.append(value)
        request_id = sanitize_text(candidate.get("request_id", "") or candidate.get("trace_id", ""))
        if request_id:
            parts.append(f"request_id={request_id}")
        for value in (candidate.get("code_label", ""), candidate.get("errno", "")):
            normalized = sanitize_text(value)
            if normalized:
                parts.append(normalized)
        app_id = sanitize_text(candidate.get("app_id", ""))
        file_id = sanitize_text(candidate.get("file_id", ""))
        if app_id:
            parts.append(f"app_id={app_id}")
        if file_id:
            parts.append(f"file_id={file_id}")
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
        return [
            {
                "kind": str(hit.get("kind", "")),
                "summary": str(hit.get("summary", "")),
                "evidence": str(hit.get("evidence", "")),
                "source": str(hit.get("source", "")),
                "line_no": int(hit.get("line_no", 0) or 0),
                "request_id": str(hit.get("request_id", "")),
                "context_window": list(hit.get("context_window", [])),
            }
            for hit in hits[:8]
        ]

    def _build_request_chain(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for hit in hits:
            chain_key = sanitize_text(hit.get("request_id", "")) or sanitize_text(hit.get("trace_id", ""))
            if not chain_key:
                chain_key = sanitize_text(hit.get("signature", "")) or sanitize_text(hit.get("server_url", "")) or "global"
            bucket = grouped.setdefault(
                chain_key,
                {"chain_key": chain_key, "total_score": 0, "error_count": 0, "items": []},
            )
            bucket["total_score"] += int(hit.get("score", 0) or 0)
            if sanitize_text(hit.get("kind", "")) in {"exception", "error_response", "error", "warning"}:
                bucket["error_count"] += 1
            bucket["items"].append(hit)

        if not grouped:
            return []
        best_bucket = max(grouped.values(), key=lambda item: (int(item["total_score"]), int(item["error_count"])))
        stage_map: dict[str, dict[str, Any]] = {}
        for hit in best_bucket["items"]:
            stage = sanitize_text(hit.get("stage", "")) or "相关链路"
            dedupe_key = "|".join(
                [
                    stage,
                    sanitize_text(hit.get("signature", "")),
                    sanitize_text(hit.get("source_component", "")),
                    sanitize_text(hit.get("message", ""))[:80],
                ]
            )
            if dedupe_key in stage_map:
                continue
            stage_map[dedupe_key] = {
                "stage": stage,
                "component": sanitize_text(hit.get("source_component", "")) or sanitize_text(hit.get("source", "")),
                "summary": self._chain_item_summary(hit),
                "request_id": sanitize_text(hit.get("request_id", "")),
                "trace_id": sanitize_text(hit.get("trace_id", "")),
                "source": sanitize_text(hit.get("source", "")),
                "line_no": int(hit.get("line_no", 0) or 0),
                "signature": sanitize_text(hit.get("signature", "")),
                "evidence": sanitize_text(hit.get("evidence", "")),
                "status_code": int(hit.get("status_code", 0) or 0),
                "code_label": sanitize_text(hit.get("code_label", "")),
                "errno": sanitize_text(hit.get("errno", "")),
                "server_url": sanitize_text(hit.get("server_url", "")),
                "operation": sanitize_text(hit.get("operation", "")),
                "app_id": sanitize_text(hit.get("app_id", "")),
                "file_id": sanitize_text(hit.get("file_id", "")),
            }
        ordered = sorted(stage_map.values(), key=lambda item: self._stage_rank(item.get("stage", "")))
        return ordered[:6]

    def _chain_item_summary(self, hit: dict[str, Any]) -> str:
        status_code = int(hit.get("status_code", 0) or 0)
        code_bits = " / ".join(
            part
            for part in [sanitize_text(hit.get("code_label", "")), sanitize_text(hit.get("errno", ""))]
            if part
        )
        target = sanitize_text(hit.get("server_url", "")) or sanitize_text(hit.get("operation", ""))
        message = sanitize_text(hit.get("message", ""))
        if status_code >= 400 and target:
            return f"{target} 返回 HTTP {status_code}"
        if code_bits and target:
            return f"{target} 命中 {code_bits}"
        if code_bits:
            return f"命中 {code_bits}"
        return message[:160]

    def _build_judgment(self, hits: list[dict[str, Any]], request_chain: list[dict[str, Any]]) -> tuple[str, dict[str, str], str]:
        if not hits:
            reason = "现有日志里没有命中足够强的相关异常，暂时无法稳定定位根因。"
            return reason, {"category": "未发现明确异常", "reason": reason}, ""

        top_hit = hits[0]
        top_messages = "\n".join(sanitize_text(item.get("message", "")) for item in hits[:4]).lower()
        top_paths = "\n".join(
            sanitize_text(item.get("server_url", "")) or sanitize_text(item.get("operation", ""))
            for item in hits[:4]
        ).lower()
        top_raw = "\n".join(sanitize_text(item.get("raw", "")) for item in hits[:4]).lower()
        code_labels = " ".join(
            sanitize_text(item.get("code_label", "")) + " " + sanitize_text(item.get("errno", ""))
            for item in hits[:4]
        ).lower()

        if "userid is 0" in top_messages and "/v7/brands/" in top_paths:
            reason = "已命中下游接口异常，并出现 userid is 0，更像是请求上下文缺失导致的链路问题。"
            return reason, {"category": "请求链路问题", "reason": reason}, "userid is 0 / 下游接口上下文缺失"

        if sanitize_text(top_hit.get("kind", "")) == "exception":
            exception_type = sanitize_text(top_hit.get("exception_type", "")) or "异常"
            reason = f"已命中明确异常栈，当前核心异常为 {exception_type}。"
            return reason, {"category": "前端异常", "reason": reason}, exception_type

        if (
            "driverneterror" in code_labels
            and "providerrequesttimeout" in code_labels
            and "/prod/api/wps/v1/3rd/file/info" in f"{top_paths}\n{top_raw}"
        ):
            reason = "根因指向第三方文件信息接口 /prod/api/wps/v1/3rd/file/info 超时或不可达，错误签名为 DriverNetError / ProviderRequestTimeout。"
            return reason, {"category": "下游服务异常", "reason": reason}, "DriverNetError / ProviderRequestTimeout"

        if any(
            int(item.get("status_code", 0) or 0) in {401, 403}
            or any(keyword in sanitize_text(item.get("message", "")).lower() for keyword in _PERMISSION_KEYWORDS)
            for item in hits[:4]
        ):
            reason = "日志命中 401/403 或明确权限拒绝信息，当前更像鉴权或权限失败。"
            return reason, {"category": "鉴权/权限失败", "reason": reason}, "HTTP 401/403 / permission denied"

        if any(int(item.get("status_code", 0) or 0) >= 400 for item in hits[:4]):
            reason = "已命中 4xx/5xx 返回，当前更像下游接口调用失败，而不是缺少日志证据。"
            return reason, {"category": "下游服务异常", "reason": reason}, self._first_non_empty(hits[0].get("server_url", ""), hits[0].get("operation", ""))

        if request_chain and len(request_chain) >= 2:
            reason = "已命中同一请求链路上的多段异常，可直接按链路继续排查。"
            return reason, {"category": "请求链路问题", "reason": reason}, sanitize_text(request_chain[0].get("signature", ""))

        reason = "已命中与工单相关的异常线索，但还需要更多上下游证据补强结论。"
        return reason, {"category": "存在异常线索", "reason": reason}, ""

    def _build_confidence(self, hits: list[dict[str, Any]], request_chain: list[dict[str, Any]], judgment: dict[str, str]) -> str:
        if not hits or sanitize_text(judgment.get("category", "")) == "未发现明确异常":
            return "low"
        top_hit = hits[0]
        top_score = int(top_hit.get("score", 0) or 0)
        if sanitize_text(top_hit.get("kind", "")) == "exception" and top_score >= 180:
            return "high"
        if request_chain and len(request_chain) >= 3 and top_score >= 150:
            return "high"
        if top_score >= 140:
            return "medium"
        return "low"

    def _evaluate_answerability(
        self,
        hits: list[dict[str, Any]],
        request_chain: list[dict[str, Any]],
        root_cause_signature: str,
        judgment: dict[str, str],
        confidence: str,
    ) -> tuple[bool, str]:
        if not hits:
            return False, "现有日志里没有命中足够强的相关异常，无法直接回答工单里的问题。"
        if sanitize_text(hits[0].get("kind", "")) in {"exception", "error_response"}:
            return True, ""
        if request_chain and len(request_chain) >= 2:
            return True, ""
        if root_cause_signature:
            return True, ""
        if any(int(item.get("status_code", 0) or 0) >= 400 for item in hits[:3]):
            return True, ""
        if sanitize_text(judgment.get("category", "")) == "未发现明确异常":
            return False, "现有线索不足以形成稳定结论，暂时不能直接回答工单问题。"
        if confidence == "high":
            return True, ""
        return False, "虽然命中了部分线索，但证据强度仍不足，当前结论还不够稳定。"

    def _build_missing_information(
        self,
        request: LogAnalysisRequest,
        hits: list[dict[str, Any]],
        identifiers: list[str],
        *,
        question_answered: bool,
        answer_gap_reason: str,
        root_cause_signature: str,
    ) -> list[str]:
        missing: list[str] = []
        if not request.evidence_bundle.parts:
            missing.append("当前没有可分析的日志类附件。")
        if not identifiers and not question_answered:
            missing.append("缺少明确的 TraceId/request_id/tradId，建议补充接口路径、错误码或问题发生时间。")
        if not hits:
            missing.append("现有日志里没有命中与工单强相关的异常，建议补充更完整的入口、网关和下游日志。")
        elif len(hits) < 2 and not question_answered and not root_cause_signature:
            missing.append("当前只命中少量异常线索，建议补充同一时间段的上下游日志以确认因果链。")
        if not question_answered and answer_gap_reason:
            missing.append(answer_gap_reason)
        return missing[:5]

    def _build_next_steps(
        self,
        judgment: dict[str, str],
        request_chain: list[dict[str, Any]],
        context: InvestigationContextSummary,
        missing_information: list[str],
        affected_entities: dict[str, str],
    ) -> list[str]:
        category = sanitize_text(judgment.get("category", ""))
        suggestions: list[str] = []
        if category == "请求链路问题":
            suggestions.extend(
                [
                    "优先核对该请求上下文是否完整，重点检查用户标识、租户标识和鉴权透传字段。",
                    "继续补充网关与下游接口日志，确认链路中最早出现异常的位置。",
                ]
            )
        elif category == "下游服务异常":
            target = sanitize_text(affected_entities.get("server_url", "")) or "/prod/api/wps/v1/3rd/file/info"
            suggestions.extend(
                [
                    f"检查 {target} 的可达性、响应时间和超时配置。",
                    "确认 cloudprovider 到第三方接口的网络链路、DNS、代理和防火墙状态。",
                ]
            )
        elif category == "鉴权/权限失败":
            suggestions.extend(
                [
                    "核对调用方权限、token、租户隔离和目标资源授权是否匹配。",
                    "补充鉴权网关或认证服务日志，确认 401/403 是谁返回的。",
                ]
            )
        elif category == "前端异常":
            suggestions.extend(
                [
                    "优先核对触发异常的前端资源版本、入参结构和文档元数据。",
                    "结合异常栈继续定位具体文件和函数调用位置。",
                ]
            )
        else:
            suggestions.extend(
                [
                    "补充更完整日志包，并尽量覆盖请求入口、网关、下游依赖三段日志。",
                    "优先提供接口路径、错误码和问题发生时间。",
                ]
            )
        if request_chain:
            first = request_chain[0]
            source = sanitize_text(first.get("source", ""))
            line_no = int(first.get("line_no", 0) or 0)
            if source and line_no:
                suggestions.append(f"建议重点查看 {source} 第 {line_no} 行附近上下文。")
        if context.open_questions:
            suggestions.append(f"待补充：{context.open_questions[0]}")
        suggestions.extend(f"补充信息：{item}" for item in missing_information[:2])
        return suggestions[:6]

    def _build_summary(
        self,
        judgment: dict[str, str],
        findings: list[dict[str, Any]],
        question_answered: bool,
        confidence: str,
    ) -> str:
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
            return top_score >= 175 and len(hits) >= 2
        return top_score >= 188

    @staticmethod
    def _describe_round_result(hits: list[dict[str, Any]]) -> str:
        if not hits:
            return "未命中足够强的相关异常。"
        return f"命中 {len(hits)} 条候选，最高优先级为 {hits[0].get('source')}:{hits[0].get('line_no')}。"

    @staticmethod
    def _derive_clues_from_hits(hits: list[dict[str, Any]]) -> list[str]:
        clues: list[str] = []
        for hit in hits[:4]:
            for value in [
                hit.get("server_url", ""),
                hit.get("operation", ""),
                hit.get("request_id", ""),
                hit.get("trace_id", ""),
                hit.get("code_label", ""),
                hit.get("errno", ""),
                hit.get("app_id", ""),
                hit.get("file_id", ""),
            ]:
                text = sanitize_text(value)
                if text:
                    clues.append(text)
        return clues[:8]

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
        return result[:14]

    @staticmethod
    def _total_score(hits: list[dict[str, Any]]) -> int:
        return sum(int(item.get("score", 0) or 0) for item in hits[:6])

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
    def _leaf_key(key: str) -> str:
        return sanitize_text(key).rsplit(".", 1)[-1].split("[", 1)[0].lower()

    def _extract_from_scalars(self, scalars: list[tuple[str, str]], keys: set[str]) -> str:
        normalized_keys = {sanitize_text(key).lower() for key in keys}
        for key, value in scalars:
            if self._leaf_key(key) in normalized_keys or sanitize_text(key).lower() in normalized_keys:
                return sanitize_text(value)
        return ""

    def _extract_raw_named_value(self, text: str, key: str) -> str:
        quoted = re.search(_KEY_VALUE_QUOTED_RE.format(key=re.escape(key)), text)
        if quoted:
            return sanitize_text(quoted.group(1))
        bare = re.search(_KEY_VALUE_BARE_RE.format(key=re.escape(key)), text)
        if bare:
            return sanitize_text(bare.group(1)).strip("\"'")
        return ""

    @staticmethod
    def _extract_path_from_value(value: object) -> str:
        text = sanitize_text(value)
        if not text:
            return ""
        match = _PATH_RE.search(text)
        return sanitize_text(match.group(0)) if match else ""

    @staticmethod
    def _build_signature(request_id: str, path: str, code_label: str, errno: str, detail: str) -> str:
        parts = [sanitize_text(item) for item in [request_id, path, code_label, errno, detail] if sanitize_text(item)]
        return " | ".join(parts[:5])

    def _infer_stage(self, candidate: dict[str, Any]) -> str:
        component = sanitize_text(candidate.get("source_component", "")).lower()
        target = (
            sanitize_text(candidate.get("server_url", "")).lower()
            or sanitize_text(candidate.get("operation", "")).lower()
        )
        if "/3rd/" in target or "third" in target:
            return "第三方接口"
        if "cloudprovider" in component or "cloudprovider" in target:
            return "cloudprovider"
        if "apiserver" in component or "/office/session" in target:
            return "apiserver"
        if "middleware" in component or "metric" in component:
            return "请求入口"
        if sanitize_text(candidate.get("kind", "")) == "success":
            return "入口成功日志"
        return "相关链路"

    @staticmethod
    def _stage_rank(stage: str) -> int:
        order = {
            "请求入口": 1,
            "入口成功日志": 2,
            "apiserver": 3,
            "cloudprovider": 4,
            "第三方接口": 5,
            "相关链路": 6,
        }
        return order.get(sanitize_text(stage), 99)

    @staticmethod
    def _dedupe_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for hit in hits:
            key = "|".join(
                [
                    str(hit.get("source", "")),
                    str(hit.get("kind", "")),
                    str(hit.get("status_code", "")),
                    str(hit.get("signature", "")),
                    str(hit.get("message", ""))[:120],
                ]
            )
            if key not in seen:
                seen.add(key)
                result.append(hit)
        return result

    def _build_evidence_items(self, hits: list[dict[str, Any]], request_chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for chain_item in request_chain:
            items.append(
                {
                    "kind": "request_chain",
                    "summary": f"{chain_item.get('stage', '相关链路')}：{chain_item.get('summary', '')}",
                    "evidence": chain_item.get("evidence", ""),
                    "source": chain_item.get("source", ""),
                    "line_no": chain_item.get("line_no", 0),
                    "request_id": chain_item.get("request_id", "") or chain_item.get("trace_id", ""),
                    "context_window": [],
                }
            )
        for hit in hits[: max(0, 6 - len(items))]:
            items.append(
                {
                    "kind": hit.get("kind", ""),
                    "summary": hit.get("summary", ""),
                    "evidence": hit.get("evidence", ""),
                    "source": hit.get("source", ""),
                    "line_no": hit.get("line_no", 0),
                    "request_id": hit.get("request_id", ""),
                    "context_window": hit.get("context_window", []),
                }
            )
        return items[:6]

    def _collect_affected_entities(self, hits: list[dict[str, Any]], request_chain: list[dict[str, Any]]) -> dict[str, str]:
        entities: dict[str, str] = {}
        for container in [*request_chain, *hits]:
            for key in ("request_id", "trace_id", "server_url", "operation", "app_id", "file_id", "file_type"):
                value = sanitize_text(container.get(key, ""))
                if value and key not in entities:
                    entities[key] = value
        return entities

    def _enhance_with_llm(self, request: LogAnalysisRequest, payload: LogAnalysisResultPayload) -> LogAnalysisResultPayload:
        if self._llm_service is None:
            return payload
        messages = self._build_llm_messages(request, payload)
        try:
            raw_text = self._llm_service.run_task("log_analysis", messages=messages, temperature=0.1)
            merged = self._merge_llm_payload(payload, self._parse_llm_result(raw_text))
        except Exception:
            return payload
        return merged

    def _build_llm_messages(self, request: LogAnalysisRequest, payload: LogAnalysisResultPayload) -> list[Message]:
        user_prompt = (
            "请基于以下日志分析证据输出 JSON，对象字段固定为：\n"
            "primary_issue: string\n"
            "confidence: string\n"
            "preliminary_judgment: {category: string, reason: string}\n"
            "question_answered: boolean\n"
            "answer_gap_reason: string\n"
            "missing_information: string[]\n"
            "suggested_next_steps: string[]\n"
            "root_cause_signature: string\n"
            "request_chain: object[]\n"
            "affected_entities: object\n"
            "log_vs_ticket_note: string\n"
            "key_findings: object[]\n"
            "evidence_items: object[]\n\n"
            "要求：\n"
            "1. 只能基于输入证据回答。\n"
            "2. 日志证据优先于工单现象描述。\n"
            "3. 若已命中稳定错误签名或闭合链路，不要输出“证据不足”。\n"
            "4. suggested_next_steps 和 missing_information 最多各 4 条。\n\n"
            f"工单标题: {sanitize_text(request.todo_snapshot.get('title', ''))}\n"
            f"当前摘要: {sanitize_text(request.todo_snapshot.get('current_summary', ''))}\n"
            f"排查上下文: {sanitize_text(request.investigation_context.summary_text if hasattr(request.investigation_context, 'summary_text') else request.investigation_context.problem_summary)}\n"
            f"分析焦点: {json.dumps(payload.analysis_focus, ensure_ascii=False)}\n"
            f"请求链路: {json.dumps(payload.request_chain, ensure_ascii=False)}\n"
            f"关键证据: {json.dumps(payload.evidence_items, ensure_ascii=False)}\n"
            f"当前本地结论: {json.dumps({'primary_issue': payload.primary_issue, 'judgment': payload.preliminary_judgment, 'confidence': payload.confidence}, ensure_ascii=False)}"
        )
        return [
            Message(role="system", content=_LLM_SYSTEM_PROMPT),
            Message(role="user", content=user_prompt),
        ]

    def _parse_llm_result(self, raw_text: str) -> dict[str, Any]:
        text = str(raw_text or "").strip()
        if text.startswith("```"):
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
            if match:
                text = match.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("log analysis response is not JSON")
        payload = json.loads(text[start : end + 1])
        if not isinstance(payload, dict):
            raise ValueError("log analysis response is not an object")
        return payload

    def _merge_llm_payload(self, payload: LogAnalysisResultPayload, llm_payload: dict[str, Any]) -> LogAnalysisResultPayload:
        merged = payload.to_dict()
        for key in (
            "primary_issue",
            "confidence",
            "question_answered",
            "answer_gap_reason",
            "root_cause_signature",
            "log_vs_ticket_note",
        ):
            value = llm_payload.get(key)
            if value not in (None, ""):
                merged[key] = value
        for key in (
            "preliminary_judgment",
            "affected_entities",
        ):
            value = llm_payload.get(key)
            if isinstance(value, dict) and value:
                merged[key] = value
        for key in (
            "missing_information",
            "suggested_next_steps",
            "request_chain",
            "key_findings",
            "evidence_items",
        ):
            value = llm_payload.get(key)
            if isinstance(value, list) and value:
                merged[key] = value
        return LogAnalysisResultPayload.from_dict(merged)

    @staticmethod
    def _collect_image_clues(bundle: EvidenceBundle) -> list[dict[str, str]]:
        return [
            {"source": part.source_name, "summary": "存在图片证据，可辅助核对错误文案、错误码或界面现象。"}
            for part in bundle.parts
            if part.source_type == "image"
        ]

    @staticmethod
    def _looks_like_identifier(token: str) -> bool:
        text = sanitize_text(token)
        if len(text) < 4 or len(text) > 128 or any(char.isspace() for char in text):
            return False
        return any(char.isdigit() for char in text) or ":" in text or "_" in text or "-" in text or "=" in text

    def _should_keep_identifier(self, token: str) -> bool:
        lowered = sanitize_text(token).lower()
        if not lowered:
            return False
        if any(word in lowered for word in ("验证附件", "检查日志文件结构", "完整性及可读性")):
            return False
        return self._looks_like_identifier(token) or bool(_PATH_RE.search(lowered))

    @staticmethod
    def _looks_like_error_code(token: str) -> bool:
        digits = "".join(char for char in sanitize_text(token) if char.isdigit())
        return 4 <= len(digits) <= 10

    @staticmethod
    def _looks_like_symbolic_code(token: str) -> bool:
        text = sanitize_text(token)
        if not text or len(text) > 64:
            return False
        lowered = text.lower()
        if lowered in _TRIVIAL_MESSAGES or lowered in {"true", "false"}:
            return False
        return any(char.isupper() for char in text) or "error" in lowered or "timeout" in lowered

    @staticmethod
    def _first_non_empty(*values: object) -> str:
        for value in values:
            text = sanitize_text(value)
            if text:
                return text
        return ""

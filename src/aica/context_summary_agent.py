"""Default implementation for shared context-summary generation."""
from __future__ import annotations

import json
import re

from .context_summary_models import (
    ContextSummaryEntry,
    ContextSummaryPoint,
    ContextSummaryRequest,
    ContextSummaryResult,
)
from .llm.service import LLMService
from .llm.types import Message
from .text_sanitize import sanitize_text

_ACTION_KEYWORDS = ("排查", "检查", "查看", "验证", "尝试", "复现", "补充", "回查")
_FACT_KEYWORDS = ("确认", "已知", "命中", "返回", "日志显示", "截图显示", "定位到")
_SUSPECT_KEYWORDS = ("怀疑", "可能", "疑似", "权限", "配置", "环境", "链路", "下游")
_QUESTION_KEYWORDS = ("待确认", "未确认", "为什么", "是否", "未解决", "?")
_IMPORTANT_KEYWORDS = (
    "报错",
    "异常",
    "失败",
    "超时",
    "权限",
    "request_id",
    "trace",
    "trad",
    "日志",
    "接口",
    "http",
    "url",
    "状态码",
)
_IDENTIFIER_PATTERNS = [
    re.compile(r"(?i)(?:trace[_ -]?id|request[_ -]?id|trad[_ -]?id)\s*[:=：]?\s*([a-zA-Z0-9_-]{4,128})"),
    re.compile(r"\b\d{6}\b"),
    re.compile(r"/[a-zA-Z0-9_./{}-]{3,}"),
]

_SYSTEM_PROMPT = (
    "你是一个上下文压缩助手，负责把待办描述和时间线压缩成高质量摘要，"
    "供后续截图分析或日志分析复用。"
    "必须忠于原文，不编造事实，只保留后续分析真正需要的信息。"
    "输出必须是 JSON 对象，不要输出解释。"
)

_GOAL_INSTRUCTIONS = {
    "append_screenshot_context": (
        "摘要目标：截图追加上下文压缩。"
        "重点保留最近进展、关键参数、日志片段、TraceId/RequestId、待确认项，"
        "不要把旧摘要整段重复展开。"
    ),
    "log_analysis_context": (
        "摘要目标：日志分析前置上下文压缩。"
        "重点提炼问题概述、已做动作、已确认事实、可疑原因、待确认项、当前排查焦点。"
    ),
    "timeline_rollup": (
        "摘要目标：时间线阶段总结。"
        "按时间顺序提炼阶段性进展、阻塞点和结论。"
    ),
}


class DefaultContextSummaryAgent:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm_service = llm_service

    def summarize_with_llm(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        if self._llm_service is None:
            raise RuntimeError("LLM service unavailable for context summary")
        selected_entries = self._select_entries(request)
        messages = self._build_messages(request, selected_entries)
        raw_text = self._llm_service.run_task(
            "context_summary",
            messages=messages,
            temperature=0.2,
        )
        parsed = self._parse_result(raw_text)
        if not parsed.problem_brief and not parsed.key_points and not parsed.summary_text:
            raise ValueError("Empty context summary result")
        return self._with_source_stats(parsed, request=request, selected_entries=selected_entries, mode="llm")

    def summarize_locally(self, request: ContextSummaryRequest) -> ContextSummaryResult:
        selected_entries = self._select_entries(request)
        if request.summary_goal == "log_analysis_context":
            result = self._summarize_log_analysis_context(request, selected_entries)
        elif request.summary_goal == "timeline_rollup":
            result = self._summarize_timeline_rollup(request, selected_entries)
        else:
            result = self._summarize_append_screenshot_context(request, selected_entries)
        return self._with_source_stats(result, request=request, selected_entries=selected_entries, mode="fallback_local")

    def _build_messages(self, request: ContextSummaryRequest, selected_entries: list[ContextSummaryEntry]) -> list[Message]:
        goal_instruction = _GOAL_INSTRUCTIONS.get(request.summary_goal, _GOAL_INSTRUCTIONS["append_screenshot_context"])
        entry_lines = []
        for index, entry in enumerate(selected_entries, 1):
            prefix_parts = [part for part in [entry.timestamp or "未知时间", entry.scenario or entry.kind or entry.event_type] if part]
            body = self._entry_text(entry, limit=220)
            line = f"{index}. [{' / '.join(prefix_parts)}] {body}"
            if entry.attachment_summaries:
                line = f"{line}\n   附件: {', '.join(entry.attachment_summaries[:4])}"
            entry_lines.append(line)

        user_prompt = (
            f"{goal_instruction}\n"
            "请输出 JSON，对象字段固定为：\n"
            "problem_brief: string\n"
            "key_points: [{category: string, text: string}]\n"
            "open_questions: string[]\n"
            "next_focus: string[]\n"
            "summary_text: string\n\n"
            "要求：\n"
            "1. key_points 最多 8 条，每条尽量短。\n"
            "2. category 只使用 progress / finding / action / fact / suspect。\n"
            "3. open_questions 和 next_focus 最多各 5 条。\n"
            "4. 不要输出 Markdown，不要输出额外字段。\n\n"
            f"原始描述:\n{request.description or '暂无'}\n\n"
            f"补充上下文:\n{json.dumps(request.extra_context, ensure_ascii=False)}\n\n"
            f"时间线:\n{chr(10).join(entry_lines) if entry_lines else '暂无时间线'}"
        )
        return [
            Message(role="system", content=_SYSTEM_PROMPT),
            Message(role="user", content=user_prompt),
        ]

    def _parse_result(self, raw_text: str) -> ContextSummaryResult:
        text = str(raw_text or "").strip()
        if text.startswith("```"):
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
            if match:
                text = match.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Context summary response is not JSON")
        payload = json.loads(text[start:end + 1])
        if not isinstance(payload, dict):
            raise ValueError("Context summary response is not an object")
        return ContextSummaryResult.from_dict(payload)

    def _with_source_stats(
        self,
        result: ContextSummaryResult,
        *,
        request: ContextSummaryRequest,
        selected_entries: list[ContextSummaryEntry],
        mode: str,
    ) -> ContextSummaryResult:
        stats = {
            "summary_goal": request.summary_goal,
            "input_timeline_count": len(request.timeline_entries),
            "selected_timeline_count": len(selected_entries),
            "mode": mode,
        }
        return ContextSummaryResult(
            summary_text=result.summary_text or self._render_summary_text(
                problem_brief=result.problem_brief,
                key_points=result.key_points,
                open_questions=result.open_questions,
                next_focus=result.next_focus,
            ),
            problem_brief=result.problem_brief,
            key_points=result.key_points,
            open_questions=result.open_questions,
            next_focus=result.next_focus,
            source_stats=stats,
        )

    def _select_entries(self, request: ContextSummaryRequest) -> list[ContextSummaryEntry]:
        scored: list[tuple[int, int, ContextSummaryEntry]] = []
        normalized_entries = [
            entry
            for entry in request.timeline_entries
            if entry.content or entry.attachment_summaries
        ]
        total = len(normalized_entries)
        for index, entry in enumerate(normalized_entries):
            score = self._entry_score(entry, goal=request.summary_goal, recency_rank=total - index)
            scored.append((score, index, entry))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

        selected_pairs = scored[: request.max_items]
        selected_pairs.sort(key=lambda item: item[1])
        selected = [item[2] for item in selected_pairs]

        budget = 0
        fitted: list[ContextSummaryEntry] = []
        for entry in selected:
            estimated = len(entry.content) + sum(len(item) for item in entry.attachment_summaries)
            if fitted and budget + estimated > request.max_chars:
                continue
            fitted.append(entry)
            budget += estimated
        return fitted or selected[:1]

    def _entry_score(self, entry: ContextSummaryEntry, *, goal: str, recency_rank: int) -> int:
        text = self._entry_text(entry, limit=400).lower()
        score = max(1, recency_rank * 5)
        if entry.kind == "conclusion":
            score += 100
        if entry.event_type == "log_analysis_result":
            score += 90
        if entry.event_type == "log_analysis_command":
            score += 30
        if any(keyword in text for keyword in _IMPORTANT_KEYWORDS):
            score += 45
        if entry.attachment_summaries:
            score += 10
        if goal == "log_analysis_context":
            if "日志分析" in entry.scenario:
                score += 40
            if any(keyword in text for keyword in ("trace", "request_id", "trad", "接口", "日志", "error", "exception")):
                score += 40
        if goal == "append_screenshot_context":
            if any(keyword in text for keyword in ("参数", "trace", "request_id", "url", "日志", "报错")):
                score += 30
        return score

    def _summarize_append_screenshot_context(
        self,
        request: ContextSummaryRequest,
        selected_entries: list[ContextSummaryEntry],
    ) -> ContextSummaryResult:
        problem_brief = request.description or self._fallback_problem_brief(request, selected_entries)
        key_points: list[ContextSummaryPoint] = []
        for entry in selected_entries[-5:]:
            text = self._entry_text(entry, limit=180)
            if not text:
                continue
            category = "finding" if entry.kind == "conclusion" or entry.event_type == "log_analysis_result" else "progress"
            key_points.append(ContextSummaryPoint(category=category, text=text))

        open_questions = self._collect_open_questions(selected_entries, limit=5)
        next_focus = self._collect_focus_terms(request, selected_entries, limit=5)
        summary_text = self._render_summary_text(
            problem_brief=problem_brief,
            key_points=key_points,
            open_questions=open_questions,
            next_focus=next_focus,
        )
        return ContextSummaryResult(
            summary_text=summary_text,
            problem_brief=problem_brief,
            key_points=key_points[:6],
            open_questions=open_questions,
            next_focus=next_focus,
        )

    def _summarize_log_analysis_context(
        self,
        request: ContextSummaryRequest,
        selected_entries: list[ContextSummaryEntry],
    ) -> ContextSummaryResult:
        problem_brief = request.description or self._fallback_problem_brief(request, selected_entries)
        actions: list[ContextSummaryPoint] = []
        facts: list[ContextSummaryPoint] = []
        suspects: list[ContextSummaryPoint] = []
        carryover: list[ContextSummaryPoint] = []

        for entry in selected_entries:
            text = self._entry_text(entry, limit=180)
            if not text:
                continue
            lowered = text.lower()
            if entry.event_type == "log_analysis_command" or any(keyword in text for keyword in _ACTION_KEYWORDS):
                actions.append(ContextSummaryPoint(category="action", text=text))
            elif entry.event_type == "log_analysis_result" or any(keyword in text for keyword in _FACT_KEYWORDS):
                facts.append(ContextSummaryPoint(category="fact", text=text))
            elif any(keyword in text for keyword in _SUSPECT_KEYWORDS):
                suspects.append(ContextSummaryPoint(category="suspect", text=text))
            elif "?" in lowered or any(keyword in text for keyword in _QUESTION_KEYWORDS):
                carryover.append(ContextSummaryPoint(category="finding", text=text))
            else:
                carryover.append(ContextSummaryPoint(category="finding", text=text))

        key_points = self._dedupe_points([*actions[:3], *facts[:4], *suspects[:3], *carryover[:2]], limit=8)
        open_questions = self._collect_open_questions(selected_entries, limit=5)
        next_focus = self._collect_focus_terms(request, selected_entries, limit=6)
        summary_text = self._render_log_analysis_summary(
            problem_brief=problem_brief,
            actions=actions,
            facts=facts,
            suspects=suspects,
            open_questions=open_questions,
            next_focus=next_focus,
        )
        return ContextSummaryResult(
            summary_text=summary_text,
            problem_brief=problem_brief,
            key_points=key_points,
            open_questions=open_questions,
            next_focus=next_focus,
        )

    def _summarize_timeline_rollup(
        self,
        request: ContextSummaryRequest,
        selected_entries: list[ContextSummaryEntry],
    ) -> ContextSummaryResult:
        problem_brief = request.description or self._fallback_problem_brief(request, selected_entries)
        key_points = [
            ContextSummaryPoint(category="progress", text=self._entry_text(entry, limit=180))
            for entry in selected_entries[-6:]
            if self._entry_text(entry, limit=180)
        ]
        open_questions = self._collect_open_questions(selected_entries, limit=5)
        next_focus = self._collect_focus_terms(request, selected_entries, limit=5)
        return ContextSummaryResult(
            summary_text=self._render_summary_text(
                problem_brief=problem_brief,
                key_points=key_points,
                open_questions=open_questions,
                next_focus=next_focus,
            ),
            problem_brief=problem_brief,
            key_points=key_points[:6],
            open_questions=open_questions,
            next_focus=next_focus,
        )

    def _fallback_problem_brief(
        self,
        request: ContextSummaryRequest,
        selected_entries: list[ContextSummaryEntry],
    ) -> str:
        if request.description:
            return request.description[:220]
        title = sanitize_text(request.extra_context.get("title", "")).strip()
        if title:
            return title[:220]
        for entry in selected_entries:
            text = self._entry_text(entry, limit=220)
            if text:
                return text
        return ""

    def _collect_open_questions(self, entries: list[ContextSummaryEntry], *, limit: int) -> list[str]:
        questions: list[str] = []
        for entry in entries:
            text = self._entry_text(entry, limit=220)
            if not text:
                continue
            clauses = re.split(r"[。；;！!\n]+", text)
            for clause in clauses:
                normalized = sanitize_text(clause).strip(" ，,。；;：:")
                lowered = normalized.lower()
                if not normalized:
                    continue
                if "?" in normalized or any(keyword in normalized for keyword in _QUESTION_KEYWORDS):
                    questions.append(normalized)
                elif any(keyword in lowered for keyword in ("todo", "待确认", "待补充")):
                    questions.append(normalized)
        return self._dedupe_strings(questions, limit=limit)

    def _collect_focus_terms(
        self,
        request: ContextSummaryRequest,
        entries: list[ContextSummaryEntry],
        *,
        limit: int,
    ) -> list[str]:
        focus: list[str] = []
        for key in ("trad_id", "request_id"):
            value = sanitize_text(request.extra_context.get(key, "")).strip()
            if value:
                label = "tradId" if key == "trad_id" else "request_id"
                focus.append(f"{label}={value}")
        focus.extend(
            item
            for item in request.extra_context.get("focus_terms", [])
            if isinstance(item, str) and sanitize_text(item).strip()
        )
        for entry in entries:
            text = self._entry_text(entry, limit=240)
            for pattern in _IDENTIFIER_PATTERNS:
                for matched in pattern.findall(text):
                    if isinstance(matched, tuple):
                        matched = next((part for part in matched if part), "")
                    normalized = sanitize_text(matched).strip()
                    if normalized:
                        focus.append(normalized)
        return self._dedupe_strings(focus, limit=limit)

    @staticmethod
    def _entry_text(entry: ContextSummaryEntry, *, limit: int) -> str:
        base = sanitize_text(entry.content).strip()
        if entry.attachment_summaries:
            attachment_text = ", ".join(entry.attachment_summaries[:4])
            base = f"{base} 附件: {attachment_text}".strip()
        return base[:limit]

    @staticmethod
    def _dedupe_strings(items: list[str], *, limit: int) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in items:
            normalized = sanitize_text(item).strip()
            if not normalized or normalized.casefold() in seen:
                continue
            seen.add(normalized.casefold())
            result.append(normalized)
            if len(result) >= limit:
                break
        return result

    @classmethod
    def _dedupe_points(cls, items: list[ContextSummaryPoint], *, limit: int) -> list[ContextSummaryPoint]:
        deduped = cls._dedupe_strings([item.text for item in items], limit=limit)
        index = {item.text: item for item in items if item.text}
        return [index[text] for text in deduped if text in index]

    @staticmethod
    def _render_summary_text(
        *,
        problem_brief: str,
        key_points: list[ContextSummaryPoint],
        open_questions: list[str],
        next_focus: list[str],
    ) -> str:
        lines = [f"问题概述: {problem_brief or '暂无'}"]
        if key_points:
            lines.append("关键进展:")
            lines.extend(f"- {item.text}" for item in key_points[:6] if item.text)
        if open_questions:
            lines.append("待确认:")
            lines.extend(f"- {item}" for item in open_questions[:5])
        if next_focus:
            lines.append("当前关注:")
            lines.extend(f"- {item}" for item in next_focus[:5])
        return "\n".join(lines).strip()

    @staticmethod
    def _render_log_analysis_summary(
        *,
        problem_brief: str,
        actions: list[ContextSummaryPoint],
        facts: list[ContextSummaryPoint],
        suspects: list[ContextSummaryPoint],
        open_questions: list[str],
        next_focus: list[str],
    ) -> str:
        lines = [f"问题概述: {problem_brief or '暂无'}"]
        if actions:
            lines.append("已做动作:")
            lines.extend(f"- {item.text}" for item in actions[:4] if item.text)
        if facts:
            lines.append("已确认事实:")
            lines.extend(f"- {item.text}" for item in facts[:4] if item.text)
        if suspects:
            lines.append("可疑点:")
            lines.extend(f"- {item.text}" for item in suspects[:4] if item.text)
        if open_questions:
            lines.append("待确认:")
            lines.extend(f"- {item}" for item in open_questions[:5])
        if next_focus:
            lines.append("当前关注:")
            lines.extend(f"- {item}" for item in next_focus[:6])
        return "\n".join(lines).strip()

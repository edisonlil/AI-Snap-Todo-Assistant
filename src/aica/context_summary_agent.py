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
_IDENTIFIER_PATTERNS = [
    re.compile(r"(?i)(?:trace[_ -]?id|request[_ -]?id|trad[_ -]?id)\s*[:=：]?\s*([a-zA-Z0-9_-]{4,128})"),
    re.compile(r"\b\d{6}\b"),
    re.compile(r"/[a-zA-Z0-9_./{}-]{3,}"),
]
_ATTACHMENT_LINE_PATTERN = re.compile(r"^(?:[-*]\s*)?附件[:：].*$", re.IGNORECASE)
_ATTACHMENT_FILENAME_PATTERN = re.compile(
    r"(?i)^[^\\/:*?\"<>|\r\n]+?\.(?:png|jpe?g|gif|bmp|webp|docx?|xlsx?|pptx?|pdf|zip|rar|7z|txt|log|csv)$"
)
_WINDOWS_PATH_PATTERN = re.compile(r"(?i)^[a-z]:\\")
_URL_PATTERN = re.compile(r"(?i)https?://\S+")

_SYSTEM_PROMPT = (
    "你是一位上下文压缩助手，负责把待办描述和时间线整理成可信、克制的结构化摘要。"
    "你必须严格忠于输入原文，只能复述输入里明确出现的事实。"
    "宁可遗漏，也不要编造；不要补全省略主语、宾语或因果链后形成新事实。"
    "如果信息是不确定、待确认或疑似，必须保留这种不确定性，不能改写成确定结论。"
    "输出必须是 JSON 对象，不要输出解释。"
)

_GOAL_INSTRUCTIONS = {
    "append_screenshot_context": (
        "摘要目标：截图追加上下文压缩。"
        "重点保留最近进展、关键参数、日志片段、TraceId/RequestId 和待确认项，"
        "不要把旧摘要整段展开，也不要补充截图里没有的新细节。"
    ),
    "log_analysis_context": (
        "摘要目标：日志分析前置上下文压缩。"
        "重点提炼问题概述、已做动作、已确认事实、可疑原因、待确认项和当前排查焦点，"
        "不要把推测写成结论。"
    ),
    "timeline_rollup": (
        "摘要目标：时间线阶段总结。"
        "只能基于输入时间线原文梳理阶段现状、当前结论、已发生进展和待确认事项。"
        "必须保持事件先后顺序，不要重排成更完整的故事线；"
        "不要补充未出现的时间点、责任方、根因和结论。"
    ),
}


def _build_output_rules(summary_goal: str) -> list[str]:
    rules = [
        "problem_brief 只概括当前问题，不扩写历史过程。",
        "key_points 最多 8 条，每条尽量贴近原文，不做因果推断。",
        "category 只能使用 progress / finding / action / fact / suspect。",
        "open_questions 和 next_focus 最多各 5 条。",
        "不要输出 Markdown，不要输出额外字段。",
    ]
    if summary_goal == "timeline_rollup":
        rules.extend(
            [
                "summary_text 必须使用固定四段：阶段现状、当前结论、已发生进展、待确认事项。",
                "已发生进展中的每一条都必须能在输入时间线中找到对应事件，尽量复用原始动作或观察。",
                "如果已有明确结论，当前结论段落必须单独写出，不要混入“已发生进展”。",
                "如果没有明确结论，就写“暂无明确结论”。",
                "待确认事项只写输入里明确未确认的问题；如果没有，就写“暂无明确待确认事项”。",
                "如果输入没有具体时间点，不要新增“今天”“昨天”“随后”“最终”等时间锚点。",
            ]
        )
    return rules


def _conclusion_text_from_request(request: ContextSummaryRequest) -> str:
    return sanitize_text(request.extra_context.get("conclusion_content", "")).strip()


def _timeline_rollup_summary_format_hint() -> str:
    return (
        "summary_text 的文本结构固定为：\n"
        "阶段现状:\n"
        "...\n"
        "当前结论:\n"
        "...\n"
        "已发生进展:\n"
        "- ...\n"
        "待确认事项:\n"
        "- ...\n"
    )


def _has_timeline_rollup_sections(text: str) -> bool:
    normalized = sanitize_text(text)
    return all(section in normalized for section in ("阶段现状", "当前结论", "已发生进展", "待确认事项"))


def _strip_attachment_lines(text: str) -> str:
    compact_lines: list[str] = []
    pending_blank = False
    for raw_line in sanitize_text(text).splitlines():
        line = raw_line.strip()
        if not line:
            pending_blank = bool(compact_lines)
            continue
        if _ATTACHMENT_LINE_PATTERN.match(line):
            continue
        if pending_blank and compact_lines:
            compact_lines.append("")
        compact_lines.append(line)
        pending_blank = False
    return "\n".join(compact_lines).strip()


def _looks_like_attachment_reference(text: str) -> bool:
    normalized = sanitize_text(text).strip().strip(",，;；")
    if not normalized or _URL_PATTERN.search(normalized):
        return False
    parts = [part.strip() for part in re.split(r"[，,]\s*", normalized) if part.strip()]
    if not parts:
        return False
    return all(_WINDOWS_PATH_PATTERN.match(part) or _ATTACHMENT_FILENAME_PATTERN.match(part) for part in parts)


def _clean_timeline_rollup_text(text: str) -> str:
    cleaned = _strip_attachment_lines(text)
    if _looks_like_attachment_reference(cleaned):
        return ""
    return cleaned


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
        rules_text = "\n".join(
            f"{index}. {rule}"
            for index, rule in enumerate(_build_output_rules(request.summary_goal), start=1)
        )
        entry_lines = []
        for index, entry in enumerate(selected_entries, 1):
            prefix_parts = [part for part in [entry.timestamp or "未知时间", entry.scenario or entry.kind or entry.event_type] if part]
            body = self._entry_text_for_goal(entry, request.summary_goal)
            line = f"{index}. [{' / '.join(prefix_parts)}] {body}"
            if request.summary_goal != "timeline_rollup" and entry.attachment_summaries:
                line = f"{line}\n   附件: {', '.join(entry.attachment_summaries[:4])}"
            entry_lines.append(line)

        summary_format_hint = (
            f"{_timeline_rollup_summary_format_hint()}\n"
            if request.summary_goal == "timeline_rollup"
            else ""
        )
        conclusion_context = ""
        if request.summary_goal == "timeline_rollup":
            conclusion_text = _conclusion_text_from_request(request)
            conclusion_context = (
                f"当前结论（单独输入）:\n{conclusion_text or '暂无明确结论'}\n\n"
            )
        user_prompt = (
            f"{goal_instruction}\n"
            "请输出 JSON，对象字段固定为：\n"
            "problem_brief: string\n"
            "key_points: [{category: string, text: string}]\n"
            "open_questions: string[]\n"
            "next_focus: string[]\n"
            "summary_text: string\n\n"
            "要求：\n"
            f"{rules_text}\n\n"
            f"{summary_format_hint}"
            f"原始描述:\n{request.description or '暂无'}\n\n"
            f"补充上下文:\n{json.dumps(request.extra_context, ensure_ascii=False)}\n\n"
            f"{conclusion_context}"
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
        summary_text = sanitize_text(result.summary_text).strip()
        if request.summary_goal == "timeline_rollup":
            problem_brief = _clean_timeline_rollup_text(result.problem_brief) or self._fallback_problem_brief(request, selected_entries)
            key_points = self._normalize_timeline_rollup_points(result.key_points, selected_entries)
            open_questions = self._normalize_timeline_rollup_open_questions(result.open_questions, request, selected_entries)
            summary_text = self._normalize_timeline_rollup_summary(
                summary_text=summary_text,
                problem_brief=problem_brief,
                conclusion_text=_conclusion_text_from_request(request),
                key_points=key_points,
                open_questions=open_questions,
            )
            return ContextSummaryResult(
                summary_text=summary_text,
                problem_brief=problem_brief,
                key_points=key_points,
                open_questions=open_questions,
                next_focus=result.next_focus,
                source_stats=stats,
            )
        elif not summary_text:
            summary_text = self._render_summary_text(
                problem_brief=result.problem_brief,
                key_points=result.key_points,
                open_questions=result.open_questions,
                next_focus=result.next_focus,
            )
        return ContextSummaryResult(
            summary_text=summary_text,
            problem_brief=result.problem_brief,
            key_points=result.key_points,
            open_questions=result.open_questions,
            next_focus=result.next_focus,
            source_stats=stats,
        )

    def _select_entries(self, request: ContextSummaryRequest) -> list[ContextSummaryEntry]:
        return [
            entry
            for entry in request.timeline_entries
            if self._entry_text_for_goal(entry, request.summary_goal)
            or (request.summary_goal != "timeline_rollup" and entry.attachment_summaries)
        ]

    def _summarize_append_screenshot_context(
        self,
        request: ContextSummaryRequest,
        selected_entries: list[ContextSummaryEntry],
    ) -> ContextSummaryResult:
        problem_brief = request.description or self._fallback_problem_brief(request, selected_entries)
        key_points: list[ContextSummaryPoint] = []
        for entry in selected_entries[-5:]:
            text = self._entry_text(entry)
            if not text:
                continue
            category = "finding" if entry.kind == "conclusion" or entry.event_type == "log_analysis_result" else "progress"
            key_points.append(ContextSummaryPoint(category=category, text=text))

        open_questions = self._collect_open_questions(request, selected_entries, limit=5)
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
            text = self._entry_text(entry)
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
        open_questions = self._collect_open_questions(request, selected_entries, limit=5)
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
        conclusion_text = _conclusion_text_from_request(request)
        key_points = [
            ContextSummaryPoint(category="progress", text=self._timeline_rollup_entry_text(entry))
            for entry in selected_entries[-6:]
            if self._timeline_rollup_entry_text(entry)
        ]
        open_questions = self._collect_open_questions(request, selected_entries, limit=5)
        next_focus = self._collect_focus_terms(request, selected_entries, limit=5)
        return ContextSummaryResult(
            summary_text=self._render_timeline_rollup_summary(
                problem_brief=problem_brief,
                conclusion_text=conclusion_text,
                key_points=key_points,
                open_questions=open_questions,
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
            return _clean_timeline_rollup_text(request.description) if request.summary_goal == "timeline_rollup" else request.description
        title = sanitize_text(request.extra_context.get("title", "")).strip()
        if title:
            return title
        for entry in selected_entries:
            text = self._entry_text_for_goal(entry, request.summary_goal)
            if text:
                return text
        return ""

    def _collect_open_questions(
        self,
        request: ContextSummaryRequest,
        entries: list[ContextSummaryEntry],
        *,
        limit: int,
    ) -> list[str]:
        questions: list[str] = []
        for entry in entries:
            text = self._entry_text_for_goal(entry, request.summary_goal)
            if not text:
                continue
            clauses = re.split(r"[。；;？?\n]+", text)
            for clause in clauses:
                normalized = sanitize_text(clause).strip(" ：:，,。；;？?")
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
            text = self._entry_text_for_goal(entry, request.summary_goal)
            for pattern in _IDENTIFIER_PATTERNS:
                for matched in pattern.findall(text):
                    if isinstance(matched, tuple):
                        matched = next((part for part in matched if part), "")
                    normalized = sanitize_text(matched).strip()
                    if normalized:
                        focus.append(normalized)
        return self._dedupe_strings(focus, limit=limit)

    @staticmethod
    def _entry_text(entry: ContextSummaryEntry) -> str:
        base = sanitize_text(entry.content).strip()
        if entry.attachment_summaries:
            attachment_text = ", ".join(entry.attachment_summaries[:4])
            base = f"{base} 附件: {attachment_text}".strip()
        return base

    @staticmethod
    def _timeline_rollup_entry_text(entry: ContextSummaryEntry) -> str:
        return _clean_timeline_rollup_text(entry.content)

    def _entry_text_for_goal(self, entry: ContextSummaryEntry, summary_goal: str) -> str:
        if summary_goal == "timeline_rollup":
            return self._timeline_rollup_entry_text(entry)
        return self._entry_text(entry)

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

    @staticmethod
    def _render_timeline_rollup_summary(
        *,
        problem_brief: str,
        conclusion_text: str,
        key_points: list[ContextSummaryPoint],
        open_questions: list[str],
    ) -> str:
        lines = [
            f"阶段现状: {problem_brief or '暂无'}",
            "",
            f"当前结论: {conclusion_text or '暂无明确结论'}",
            "",
            "已发生进展:",
        ]
        if key_points:
            lines.extend(f"- {item.text}" for item in key_points[:6] if item.text)
        else:
            lines.append("- 暂无明确阶段进展")
        lines.append("")
        lines.append("待确认事项:")
        if open_questions:
            lines.extend(f"- {item}" for item in open_questions[:5])
        else:
            lines.append("- 暂无明确待确认事项")
        return "\n".join(lines).strip()

    def _normalize_timeline_rollup_summary(
        self,
        *,
        summary_text: str,
        problem_brief: str,
        conclusion_text: str,
        key_points: list[ContextSummaryPoint],
        open_questions: list[str],
    ) -> str:
        return self._render_timeline_rollup_summary(
            problem_brief=problem_brief,
            conclusion_text=conclusion_text,
            key_points=key_points,
            open_questions=open_questions,
        )

    def _normalize_timeline_rollup_points(
        self,
        key_points: list[ContextSummaryPoint],
        selected_entries: list[ContextSummaryEntry],
    ) -> list[ContextSummaryPoint]:
        normalized = [
            ContextSummaryPoint(category=item.category or "progress", text=_clean_timeline_rollup_text(item.text))
            for item in key_points
            if _clean_timeline_rollup_text(item.text)
        ]
        deduped = self._dedupe_points(normalized, limit=6)
        if deduped:
            return deduped
        fallback = [
            ContextSummaryPoint(category="progress", text=self._timeline_rollup_entry_text(entry))
            for entry in selected_entries[-6:]
            if self._timeline_rollup_entry_text(entry)
        ]
        return self._dedupe_points(fallback, limit=6)

    def _normalize_timeline_rollup_open_questions(
        self,
        open_questions: list[str],
        request: ContextSummaryRequest,
        selected_entries: list[ContextSummaryEntry],
    ) -> list[str]:
        normalized = self._dedupe_strings(
            [_clean_timeline_rollup_text(item) for item in open_questions if _clean_timeline_rollup_text(item)],
            limit=5,
        )
        if normalized:
            return normalized
        return self._collect_open_questions(request, selected_entries, limit=5)

"""Investigation context compression for log analysis tasks."""
from __future__ import annotations

from .log_analysis_models import InvestigationContextSummary, LogAnalysisCommand
from .todo_models import TimelineEvent, TodoItem
from .text_sanitize import sanitize_text


_ACTION_KEYWORDS = ("排查", "检查", "查看", "验证", "尝试", "重试", "复现")
_FACT_KEYWORDS = ("确认", "已知", "命中", "返回", "日志显示", "截图显示")
_SUSPECT_KEYWORDS = ("怀疑", "可能", "疑似", "权限", "配置", "环境", "链路")
_QUESTION_KEYWORDS = ("待确认", "未确认", "为什么", "是否", "未解决", "?")
_RELEVANT_KEYWORDS = ("报错", "异常", "失败", "超时", "权限", "request_id", "trad", "日志", "trace", "接口")


def collect_relevant_timeline_entries(todo: TodoItem, limit: int = 12) -> list[TimelineEvent]:
    relevant: list[TimelineEvent] = []
    for event in reversed(todo.timeline):
        content = sanitize_text(event.content).strip()
        scenario = sanitize_text(event.scenario).strip()
        if (
            event.kind == "conclusion"
            or any(keyword.lower() in content.lower() for keyword in _RELEVANT_KEYWORDS)
            or "日志分析" in scenario
        ):
            relevant.append(event)
        if len(relevant) >= max(1, int(limit)):
            break
    return list(reversed(relevant))


def summarize_investigation_context(
    todo: TodoItem,
    parsed_command: LogAnalysisCommand,
    recent_entries: list[TimelineEvent],
) -> InvestigationContextSummary:
    actions: list[str] = []
    facts: list[str] = []
    suspects: list[str] = []
    questions: list[str] = []
    problem_summary = sanitize_text(todo.current_summary).strip()

    for event in recent_entries:
        content = sanitize_text(event.content).strip()
        if not content:
            continue
        lowered = content.lower()
        if not problem_summary:
            problem_summary = content[:200]
        if any(keyword in content for keyword in _ACTION_KEYWORDS):
            actions.append(content[:180])
        if any(keyword in content for keyword in _FACT_KEYWORDS):
            facts.append(content[:180])
        if any(keyword in content for keyword in _SUSPECT_KEYWORDS):
            suspects.append(content[:180])
        if any(keyword in content for keyword in _QUESTION_KEYWORDS) or "?" in lowered:
            questions.append(content[:180])

    current_focus = []
    if parsed_command.trad_id:
        current_focus.append(f"tradId={parsed_command.trad_id}")
    if parsed_command.request_id:
        current_focus.append(f"request_id={parsed_command.request_id}")
    current_focus.extend(parsed_command.focus_terms)

    return InvestigationContextSummary(
        problem_summary=problem_summary or sanitize_text(todo.title),
        actions_taken=_dedupe(actions, limit=5),
        confirmed_facts=_dedupe(facts, limit=5),
        suspected_causes=_dedupe(suspects, limit=5),
        open_questions=_dedupe(questions, limit=5),
        current_focus=_dedupe(current_focus, limit=6),
    )


def _dedupe(items: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = sanitize_text(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if len(result) >= limit:
            break
    return result

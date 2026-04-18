"""Slash command parsing for async log analysis."""
from __future__ import annotations

import re

from .log_analysis_models import LogAnalysisCommand
from .text_sanitize import sanitize_text


_COMMAND_PREFIX = "/分析日志"
_KV_PATTERNS = {
    "trad_id": re.compile(r"(?i)\b(?:tradId|trad_id)\s*=\s*([^\s,，;；]+)"),
    "request_id": re.compile(r"(?i)\b(?:request_id|requestId)\s*=\s*([^\s,，;；]+)"),
}
_STOP_TERMS = {"重点看", "重点", "查看", "分析", "日志", "和", "以及"}


def is_log_analysis_command(text: str) -> bool:
    return sanitize_text(text).strip().startswith(_COMMAND_PREFIX)


def parse_log_analysis_command(text: str) -> LogAnalysisCommand:
    raw_command = sanitize_text(text).strip()
    body = raw_command[len(_COMMAND_PREFIX):].strip() if raw_command.startswith(_COMMAND_PREFIX) else raw_command
    extracted: dict[str, str] = {}
    remainder = body
    for field_name, pattern in _KV_PATTERNS.items():
        match = pattern.search(remainder)
        if match is None:
            continue
        extracted[field_name] = sanitize_text(match.group(1))
        remainder = pattern.sub(" ", remainder)

    focus_terms = _extract_focus_terms(remainder)
    return LogAnalysisCommand(
        trad_id=extracted.get("trad_id", ""),
        request_id=extracted.get("request_id", ""),
        focus_terms=focus_terms,
        raw_command=raw_command,
    )


def format_log_analysis_focus(command: LogAnalysisCommand) -> str:
    parts: list[str] = []
    if command.trad_id:
        parts.append(f"tradId={command.trad_id}")
    if command.request_id:
        parts.append(f"request_id={command.request_id}")
    parts.extend(command.focus_terms)
    return " / ".join(parts)


def _extract_focus_terms(text: str) -> list[str]:
    normalized = sanitize_text(text)
    if not normalized:
        return []
    for stop_term in sorted(_STOP_TERMS, key=len, reverse=True):
        normalized = normalized.replace(stop_term, " ")
    segments = re.split(r"[\n,，;；]|(?:\s+和\s+)|(?:\s+以及\s+)", normalized)
    focus_terms: list[str] = []
    seen: set[str] = set()
    for segment in segments:
        candidate = sanitize_text(segment).strip(" ：:,.，;；")
        candidate = re.sub(r"\s+", " ", candidate)
        if not candidate or candidate in _STOP_TERMS:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        focus_terms.append(candidate)
    return focus_terms

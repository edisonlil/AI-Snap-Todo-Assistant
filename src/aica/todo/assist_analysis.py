"""Shared helpers for assist troubleshooting analysis."""
from __future__ import annotations

import hashlib
from typing import Any

from ..text_sanitize import sanitize_text
from .models import TimelineEvent, TodoConclusion, TodoItem

_ASSIST_CACHE_TIMELINE_WINDOW = 5


def build_assist_todo_payload(todo: TodoItem) -> dict[str, object]:
    """Build the worker payload used by assist troubleshooting tasks."""
    return {
        "title": sanitize_text(todo.title).strip(),
        "current_summary": sanitize_text(todo.current_summary).strip(),
        "summary_fields": todo.summary_fields.to_dict(),
        "conclusion": todo.conclusion,
        "timeline": list(todo.timeline),
    }


def build_assist_analysis_cache_key(todo_id: str, todo_payload: object) -> str:
    payload = dict(todo_payload or {}) if isinstance(todo_payload, dict) else {}
    digest = hashlib.sha256()
    digest.update(sanitize_text(todo_id).strip().encode("utf-8", errors="ignore"))
    for value in (
        payload.get("title"),
        payload.get("current_summary"),
        _conclusion_content(payload.get("conclusion")),
    ):
        digest.update(b"\0")
        digest.update(sanitize_text(value).strip().encode("utf-8", errors="ignore"))
    timeline_summary = _timeline_cache_summary(payload.get("timeline"))
    digest.update(b"\0")
    digest.update(str(timeline_summary["count"]).encode("utf-8", errors="ignore"))
    digest.update(b"\0")
    digest.update(str(timeline_summary["latest_timestamp"]).encode("utf-8", errors="ignore"))
    digest.update(b"\0")
    digest.update(str(timeline_summary["light_digest"]).encode("utf-8", errors="ignore"))
    digest.update(b"\0")
    digest.update(str(timeline_summary["window_digest"]).encode("utf-8", errors="ignore"))
    return digest.hexdigest()


def should_update_assist_analysis(previous: object, candidate: object) -> bool:
    previous_data = dict(previous or {}) if isinstance(previous, dict) else {}
    candidate_data = dict(candidate or {}) if isinstance(candidate, dict) else {}
    if not candidate_data:
        return False
    previous_score = _assist_result_quality_score(previous_data)
    candidate_score = _assist_result_quality_score(candidate_data)
    if candidate_score >= previous_score + 8:
        return True
    previous_cases = _case_stats(previous_data)
    candidate_cases = _case_stats(candidate_data)
    if candidate_cases["top_score"] >= previous_cases["top_score"] + 10:
        return True
    return (
        candidate_cases["count"] > previous_cases["count"]
        and candidate_cases["top_score"] >= max(50, previous_cases["top_score"])
    )


def _timeline_items(value: object) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for item in list(value or []) if isinstance(value, list) else []:
        if isinstance(item, TimelineEvent):
            result.append(
                {
                    "id": item.id,
                    "timestamp": item.timestamp,
                    "content": item.content,
                    "kind": item.kind,
                    "scenario": item.scenario,
                    "event_type": item.event_type,
                    "status": item.status,
                    "payload": dict(item.payload),
                }
            )
        elif isinstance(item, dict):
            result.append(
                {
                    "id": item.get("id", ""),
                    "timestamp": item.get("timestamp", ""),
                    "content": item.get("content", ""),
                    "kind": item.get("kind", ""),
                    "scenario": item.get("scenario", ""),
                    "event_type": item.get("event_type", item.get("type", "")),
                    "status": item.get("status", ""),
                    "payload": item.get("payload", {}),
                }
            )
    return result


def _timeline_cache_summary(value: object) -> dict[str, object]:
    items = _timeline_items(value)
    recent_items = items[-_ASSIST_CACHE_TIMELINE_WINDOW:]
    light_digest = hashlib.sha256()
    window_digest = hashlib.sha256()
    latest_timestamp = ""
    for item in items:
        light_digest.update(b"\0")
        light_digest.update(_timeline_cache_item_fingerprint(item).encode("utf-8", errors="ignore"))
    for item in recent_items:
        latest_timestamp = sanitize_text(item.get("timestamp")).strip() or latest_timestamp
        window_digest.update(b"\0")
        window_digest.update(_timeline_cache_item_text(item).encode("utf-8", errors="ignore"))
    return {
        "count": len(items),
        "latest_timestamp": latest_timestamp,
        "light_digest": light_digest.hexdigest(),
        "window_digest": window_digest.hexdigest(),
    }


def _timeline_cache_item_text(item: dict[str, object]) -> str:
    payload = _dict(item.get("payload"))
    parts = [
        sanitize_text(item.get("timestamp")).strip(),
        sanitize_text(item.get("event_type")).strip(),
        sanitize_text(item.get("kind")).strip(),
        sanitize_text(item.get("scenario")).strip(),
        sanitize_text(item.get("status")).strip(),
        sanitize_text(item.get("content")).strip(),
        sanitize_text(payload.get("current_step")).strip(),
        sanitize_text(payload.get("summary")).strip(),
        sanitize_text(payload.get("result")).strip(),
    ]
    normalized_parts = [part[:120] for part in parts if part]
    return "\n".join(normalized_parts)


def _timeline_cache_item_fingerprint(item: dict[str, object]) -> str:
    content = sanitize_text(item.get("content")).strip()
    preview = content[:32]
    parts = [
        sanitize_text(item.get("id")).strip(),
        sanitize_text(item.get("timestamp")).strip(),
        sanitize_text(item.get("event_type")).strip(),
        sanitize_text(item.get("kind")).strip(),
        sanitize_text(item.get("status")).strip(),
        str(len(content)),
        preview,
    ]
    return "\n".join(part for part in parts if part)


def _conclusion_content(value: object) -> str:
    if isinstance(value, TodoConclusion):
        return value.content
    if isinstance(value, dict):
        return sanitize_text(value.get("content")).strip()
    return ""


def _assist_result_quality_score(payload: dict[str, object]) -> int:
    score = 0
    score += min(len(sanitize_text(payload.get("summary")).strip()), 80) // 8
    information = _dict(payload.get("informationStatus"))
    missing = _dict(payload.get("missingSupplement"))
    upgrade = _dict(payload.get("upgradeSuggestion"))
    score += _item_score(information.get("checkedDirections"), body_keys=("evidence", "reason"))
    score += _item_score(missing.get("directions"), body_keys=("reason", "evidence"))
    if sanitize_text(information.get("recognized")).strip():
        score += 4
    decision = sanitize_text(upgrade.get("decision")).strip()
    reason = sanitize_text(upgrade.get("reason")).strip()
    if decision:
        score += 3
    if reason:
        score += min(len(reason), 80) // 10
    cases = _case_stats(payload)
    score += cases["count"] * 4
    score += cases["top_score"] // 12
    return score


def _item_score(value: object, *, body_keys: tuple[str, ...]) -> int:
    score = 0
    if not isinstance(value, list):
        return score
    for item in value[:5]:
        if not isinstance(item, dict):
            continue
        title = sanitize_text(item.get("title")).strip()
        body = ""
        for key in body_keys:
            body = sanitize_text(item.get(key)).strip()
            if body:
                break
        if title:
            score += 4
        if body:
            score += 3
    return score


def _case_stats(payload: dict[str, object]) -> dict[str, int]:
    case_results = _dict(payload.get("caseResults"))
    items = case_results.get("items")
    scores = [
        _coerce_int(item.get("score"))
        for item in items
        if isinstance(item, dict)
    ] if isinstance(items, list) else []
    return {"count": len(scores), "top_score": max(scores) if scores else 0}


def _dict(value: object) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, dict) else {}


def _coerce_int(value: object) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0

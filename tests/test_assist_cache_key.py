from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.assist_analysis import build_assist_analysis_cache_key, build_assist_todo_payload  # noqa: E402
from aica.models import TicketSummaryFields  # noqa: E402
from aica.todo_models import TimelineEvent, TodoConclusion, TodoItem  # noqa: E402


def _build_todo(*, timeline: list[TimelineEvent]) -> TodoItem:
    return TodoItem(
        id="todo-1",
        title="测试待办",
        current_summary="当前摘要",
        summary_fields=TicketSummaryFields(),
        conclusion=TodoConclusion(content="结论"),
        timeline=timeline,
    )


def _event(index: int, content: str) -> TimelineEvent:
    return TimelineEvent(
        id=f"event-{index}",
        timestamp=f"2026-04-29T10:00:0{index}",
        kind="analysis",
        scenario="跟进",
        event_type="default",
        status="success",
        content=content,
    )


def _cache_key(timeline: list[TimelineEvent]) -> str:
    return build_assist_analysis_cache_key(
        "todo-1",
        build_assist_todo_payload(_build_todo(timeline=timeline)),
    )


def test_assist_cache_key_changes_when_old_timeline_changes() -> None:
    original_timeline = [_event(index, f"历史内容 {index}") for index in range(7)]
    updated_timeline = [_event(index, f"历史内容 {index}") for index in range(7)]
    updated_timeline[0].content = "更早历史被改写"

    assert _cache_key(original_timeline) != _cache_key(updated_timeline)


def test_assist_cache_key_changes_when_recent_timeline_changes() -> None:
    original_timeline = [_event(index, f"历史内容 {index}") for index in range(7)]
    updated_timeline = [_event(index, f"历史内容 {index}") for index in range(7)]
    updated_timeline[-1].content = "最近一条发生变化"

    assert _cache_key(original_timeline) != _cache_key(updated_timeline)


def test_assist_cache_key_changes_when_timeline_count_changes() -> None:
    original_timeline = [_event(index, f"历史内容 {index}") for index in range(4)]
    updated_timeline = [*original_timeline, _event(4, "新增跟进")]

    assert _cache_key(original_timeline) != _cache_key(updated_timeline)


def test_assist_cache_key_ignores_old_timeline_changes_beyond_preview_length() -> None:
    base_prefix = "A" * 32
    original_timeline = [_event(index, f"历史内容 {index}") for index in range(7)]
    updated_timeline = [_event(index, f"历史内容 {index}") for index in range(7)]
    updated_timeline[0].content = base_prefix + "尾部一"
    original_timeline[0].content = base_prefix + "尾部二"

    assert _cache_key(original_timeline) == _cache_key(updated_timeline)

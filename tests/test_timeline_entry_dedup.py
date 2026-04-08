from aica.models import TicketSnapshot, TicketSummaryFields, UNKNOWN_TEXT
from aica.todo_controller import TodoController
from aica.todo_store import TimelineEvent, TodoItem


def test_extract_incremental_timeline_entry_keeps_only_new_follow_up() -> None:
    todo = TodoItem(
        title="checkbox issue",
        summary_fields=TicketSummaryFields(),
        current_summary="initial issue observed in upload flow",
        timeline=[
            TimelineEvent(content="initial issue observed in upload flow"),
            TimelineEvent(content="checking gateway layer"),
        ],
    )

    cumulative_timeline = (
        "initial issue observed in upload flow. "
        "checking gateway layer. "
        "latest follow-up confirms http 500 is returned by gateway"
    )

    incremental = TodoController._extract_incremental_timeline_entry(todo, cumulative_timeline)

    assert incremental == "latest follow-up confirms http 500 is returned by gateway"


def test_normalize_snapshot_for_append_preserves_existing_summary_and_backfills_unknown_fields() -> None:
    todo = TodoItem(
        title="existing title",
        summary_fields=TicketSummaryFields(
            group_name=UNKNOWN_TEXT,
            environment=UNKNOWN_TEXT,
        ),
        current_summary="existing summary",
        timeline=[TimelineEvent(content="first follow-up")],
    )
    snapshot = TicketSnapshot(
        title="new title",
        fields=TicketSummaryFields(
            group_name="recognized-group",
            environment="staging",
        ),
        current_summary="new summary",
        timeline_entry="first follow-up. latest follow-up confirms font package missing",
    )

    normalized = TodoController._normalize_snapshot_for_append(todo, snapshot)

    assert normalized.title == "existing title"
    assert normalized.current_summary == "existing summary"
    assert normalized.fields.group_name == "recognized-group"
    assert normalized.fields.environment == "staging"
    assert normalized.timeline_entry == "latest follow-up confirms font package missing"

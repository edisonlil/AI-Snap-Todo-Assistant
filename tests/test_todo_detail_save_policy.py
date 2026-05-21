from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.todo.detail_save_policy import should_run_ticket_enrichment_for_todo_detail_save


def test_manual_save_triggers_ticket_enrichment() -> None:
    assert should_run_ticket_enrichment_for_todo_detail_save("save_detail_form", "manual") is True


def test_conclusion_autosave_triggers_ticket_enrichment() -> None:
    assert should_run_ticket_enrichment_for_todo_detail_save("save_conclusion", "autosave") is True


def test_regular_autosave_does_not_trigger_ticket_enrichment() -> None:
    assert should_run_ticket_enrichment_for_todo_detail_save("append_timeline_entry", "autosave") is False

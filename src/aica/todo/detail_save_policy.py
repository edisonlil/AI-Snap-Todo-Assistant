"""Policies for deciding which todo detail saves should trigger enrichment."""
from __future__ import annotations


def should_run_ticket_enrichment_for_todo_detail_save(action: object, save_mode: object) -> bool:
    normalized_action = str(action or "").strip().lower()
    if normalized_action == "save_conclusion":
        return True
    return str(save_mode or "").strip().lower() == "manual"

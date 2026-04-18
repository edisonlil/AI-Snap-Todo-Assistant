"""Compatibility wrapper for log analysis task persistence."""
from __future__ import annotations

from typing import Any

from .log_analysis_models import LogAnalysisTask
from .storage.sqlite.repositories import SQLiteLogAnalysisTaskRepository


class LogAnalysisTaskStore:
    def __init__(self, store_path: str | None = None):
        self._repository = SQLiteLogAnalysisTaskRepository(store_path)

    @property
    def path(self) -> str:
        return self._repository.path

    def create_task(self, task: LogAnalysisTask) -> LogAnalysisTask:
        return self._repository.create_task(task)

    def get_task(self, task_id: str) -> LogAnalysisTask | None:
        return self._repository.get_task(task_id)

    def get_task_by_timeline_entry(self, todo_id: str, timeline_entry_id: str) -> LogAnalysisTask | None:
        return self._repository.get_task_by_timeline_entry(todo_id, timeline_entry_id)

    def list_task_status_by_timeline_ids(self, todo_id: str, timeline_ids: list[str]) -> dict[str, dict[str, Any]]:
        return self._repository.list_task_status_by_timeline_ids(todo_id, timeline_ids)

    def list_recent_tasks(self, todo_id: str, limit: int = 10) -> list[LogAnalysisTask]:
        return self._repository.list_recent_tasks(todo_id, limit=limit)

    def mark_running(self, task_id: str, *, started_at: str, current_step: str = "") -> LogAnalysisTask | None:
        return self._repository.mark_running(task_id, started_at=started_at, current_step=current_step)

    def update_progress(self, task_id: str, *, current_step: str, status: str = "running") -> LogAnalysisTask | None:
        return self._repository.update_progress(task_id, current_step=current_step, status=status)

    def mark_completed(
        self,
        task_id: str,
        *,
        result_summary: str,
        result_payload_json: dict,
        investigation_context_json: dict,
        evidence_bundle_json: dict,
        model_binding_used: str,
        completed_at: str,
    ) -> LogAnalysisTask | None:
        return self._repository.mark_completed(
            task_id,
            result_summary=result_summary,
            result_payload_json=result_payload_json,
            investigation_context_json=investigation_context_json,
            evidence_bundle_json=evidence_bundle_json,
            model_binding_used=model_binding_used,
            completed_at=completed_at,
        )

    def mark_failed(self, task_id: str, *, error_message: str, failed_at: str) -> LogAnalysisTask | None:
        return self._repository.mark_failed(task_id, error_message=error_message, failed_at=failed_at)

    def update_context(
        self,
        task_id: str,
        *,
        investigation_context_json: dict,
        evidence_bundle_json: dict,
        model_binding_used: str = "",
    ) -> LogAnalysisTask | None:
        return self._repository.update_context(
            task_id,
            investigation_context_json=investigation_context_json,
            evidence_bundle_json=evidence_bundle_json,
            model_binding_used=model_binding_used,
        )

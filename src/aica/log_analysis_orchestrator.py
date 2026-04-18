"""Task orchestration for async log analysis."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from .config import AppConfig
from .context_summary_service import ContextSummaryService
from .llm.service import LLMService
from .log_analysis_agent import DefaultLogAnalysisAgent
from .log_analysis_attachments import AttachmentCollectContext, build_default_attachment_handler_registry
from .log_analysis_commands import parse_log_analysis_command
from .log_analysis_consumers import TimelineLogAnalysisPresenter
from .log_analysis_context import summarize_investigation_context
from .log_analysis_models import (
    LogAnalysisAgent,
    LogAnalysisCommand,
    LogAnalysisConsumeContext,
    LogAnalysisRequest,
    LogAnalysisResultConsumer,
)
from .log_analysis_store import LogAnalysisTaskStore
from .todo_models import TimelineAttachment, TimelineEvent
from .todo_store import TodoStore

STEP_COLLECT_ATTACHMENTS = "正在收集附件..."
STEP_BUILD_CONTEXT = "正在构建排查上下文..."
STEP_RETRIEVE_LOGS = "正在检索日志..."
STEP_GENERATE_RESULT = "正在生成分析结果..."


class LogAnalysisTaskDeleted(RuntimeError):
    """Raised when a log analysis task is deleted while the worker is still running."""


class LogAnalysisOrchestrator:
    def __init__(
        self,
        *,
        todo_store: TodoStore,
        task_store: LogAnalysisTaskStore,
        app_config: AppConfig,
        agent: LogAnalysisAgent | None = None,
        timeline_consumer: LogAnalysisResultConsumer | None = None,
    ) -> None:
        self._todo_store = todo_store
        self._task_store = task_store
        self._app_config = app_config
        self._llm_service = LLMService(app_config)
        self._context_summary_service = ContextSummaryService(self._llm_service)
        self._agent = agent or DefaultLogAnalysisAgent(self._llm_service)
        self._timeline_consumer = timeline_consumer or TimelineLogAnalysisPresenter()
        self._attachment_registry = build_default_attachment_handler_registry()

    def update_app_config(self, app_config: AppConfig) -> None:
        self._app_config = app_config
        self._llm_service = LLMService(app_config)
        self._context_summary_service = ContextSummaryService(self._llm_service)
        if isinstance(self._agent, DefaultLogAnalysisAgent):
            self._agent = DefaultLogAnalysisAgent(self._llm_service)

    def run_task(self, task_id: str, *, progress_callback: Callable[[str], None] | None = None) -> None:
        task = self._task_store.get_task(task_id)
        if task is None:
            raise KeyError(f"Log analysis task not found: {task_id}")
        now = datetime.now().isoformat()
        self._task_store.mark_running(task_id, started_at=now, current_step=STEP_COLLECT_ATTACHMENTS)
        if progress_callback is not None:
            progress_callback(task_id)
        try:
            self._ensure_task_active(task_id)
            todo = self._todo_store.get_todo(task.todo_id)
            if todo is None:
                raise KeyError(f"Todo not found: {task.todo_id}")
            parsed_command = LogAnalysisCommand.from_dict(task.parsed_focus_json) if task.parsed_focus_json else parse_log_analysis_command(task.raw_command)
            self._task_store.update_progress(task_id, current_step=STEP_BUILD_CONTEXT)
            if progress_callback is not None:
                progress_callback(task_id)
            self._ensure_task_active(task_id)
            investigation_context = summarize_investigation_context(
                todo,
                parsed_command,
                summary_service=self._context_summary_service,
            )
            self._task_store.update_progress(task_id, current_step=STEP_RETRIEVE_LOGS)
            if progress_callback is not None:
                progress_callback(task_id)
            self._ensure_task_active(task_id)
            attachments = [
                TimelineAttachment(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    path=str(item.get("path", "")),
                    size_bytes=int(item.get("sizeBytes", item.get("size_bytes", 0)) or 0),
                )
                for item in task.attachment_snapshot_json
                if isinstance(item, dict)
            ]
            evidence_bundle = self._attachment_registry.collect_bundle(attachments, AttachmentCollectContext(task_id=task_id))
            model_binding_used = ""
            try:
                resolved = self._llm_service.resolve_task_model("log_analysis")
                model_binding_used = (
                    f"{resolved.reference.display_name}{' (fallback analysis)' if resolved.fallback_used else ''}"
                )
            except Exception:
                resolved = None
            self._task_store.update_context(
                task_id,
                investigation_context_json=investigation_context.to_dict(),
                evidence_bundle_json=evidence_bundle.to_dict(),
                model_binding_used=model_binding_used,
            )
            self._task_store.update_progress(task_id, current_step=STEP_GENERATE_RESULT)
            if progress_callback is not None:
                progress_callback(task_id)
            self._ensure_task_active(task_id)
            request = LogAnalysisRequest(
                todo_snapshot={
                    "todo_id": todo.id,
                    "title": todo.title,
                    "current_summary": todo.current_summary,
                    "conclusion": todo.conclusion.content,
                },
                parsed_command=parsed_command,
                investigation_context=investigation_context,
                evidence_bundle=evidence_bundle,
                task_metadata={"task_id": task_id},
            )
            produced = self._agent.analyze(request)
            self._ensure_task_active(task_id)
            task_model_used = str(produced.producer_metadata.get("model_binding_used") or model_binding_used)
            self._task_store.mark_completed(
                task_id,
                result_summary=produced.result_summary,
                result_payload_json=produced.result_payload.to_dict(),
                investigation_context_json=investigation_context.to_dict(),
                evidence_bundle_json=evidence_bundle.to_dict(),
                model_binding_used=task_model_used,
                completed_at=datetime.now().isoformat(),
            )
            result_event = self._timeline_consumer.consume(
                produced,
                LogAnalysisConsumeContext(
                    todo_id=todo.id,
                    task_id=task_id,
                    timeline_entry_id=task.timeline_entry_id,
                    investigation_context=investigation_context,
                    evidence_bundle=evidence_bundle,
                ),
            )
            if isinstance(result_event, TimelineEvent):
                updated_todo = self._todo_store.get_todo(todo.id)
                if updated_todo is not None:
                    self._todo_store.update_todo(todo.id, timeline=[*updated_todo.timeline, result_event])
        except LogAnalysisTaskDeleted:
            return
        except Exception as exc:  # noqa: BLE001
            self._task_store.mark_failed(task_id, error_message=str(exc), failed_at=datetime.now().isoformat())
            raise

    def _ensure_task_active(self, task_id: str) -> LogAnalysisTask:
        task = self._task_store.get_task(task_id)
        if task is None:
            raise LogAnalysisTaskDeleted(task_id)
        return task

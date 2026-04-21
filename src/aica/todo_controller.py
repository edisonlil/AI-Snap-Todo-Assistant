"""Application-facing coordination for Todo state and workflows."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .models import (
    TicketSnapshot,
    TicketSummaryFields,
    merge_timeline_with_evidence,
    merge_summary_fields_for_append,
)
from .storage.contracts import TodoRepository
from .ticket_enrichment import TicketEnrichmentService
from .todo_events import TodoDomainEvent, TodoEventPublisher
from .todo_store import TimelineEvent, TodoConclusion, TodoItem


@dataclass(frozen=True)
class SaveAnalysisResult:
    action: str
    todo: TodoItem


class TodoController:
    """Coordinates Todo workflow state between UI and persistence."""

    def __init__(
        self,
        store: TodoRepository,
        event_publisher: TodoEventPublisher | None = None,
        enrichment_service: TicketEnrichmentService | None = None,
    ):
        self._store = store
        self._event_publisher = event_publisher
        self._enrichment_service = enrichment_service
        self._selected_todo_id: str | None = None
        self._detail_todo_id: str | None = None

    @property
    def selected_todo_id(self) -> str | None:
        return self._selected_todo_id

    @property
    def detail_todo_id(self) -> str | None:
        return self._detail_todo_id

    def set_enrichment_service(self, enrichment_service: TicketEnrichmentService | None) -> None:
        self._enrichment_service = enrichment_service

    def get_active_todos(self) -> list[TodoItem]:
        return self._store.list_active_todos()

    def get_todo_detail(self, todo_id: str) -> TodoItem | None:
        todo = self._store.get_todo(todo_id)
        if todo is not None:
            self._detail_todo_id = todo_id
        return todo

    def get_selected_todo(self) -> TodoItem | None:
        if self._selected_todo_id is None:
            return None
        return self._store.get_todo(self._selected_todo_id)

    def close_detail(self) -> None:
        self._detail_todo_id = None

    def toggle_selected_todo(self, todo_id: str) -> str | None:
        self._selected_todo_id = None if self._selected_todo_id == todo_id else todo_id
        return self._selected_todo_id

    def clear_selected_todo(self) -> None:
        self._selected_todo_id = None

    @staticmethod
    def _normalize_timeline_text(text: str) -> str:
        return re.sub(r"[\s\u3000，。；：、,.!?！？“”\"'‘’（）()【】\[\]<>《》]+", "", str(text or ""))

    @classmethod
    def _extract_incremental_timeline_entry(cls, todo: TodoItem, timeline_entry: str) -> str:
        original = str(timeline_entry or "").strip()
        if not original:
            return original

        existing_sources = [todo.current_summary] + [event.content for event in todo.timeline[-5:]]
        existing_text = "".join(
            cls._normalize_timeline_text(source)
            for source in existing_sources
            if str(source or "").strip()
        )
        clauses = [
            clause.strip(" ，。；：、,.!?！？")
            for clause in re.split(r"[，。；：、,.!?！？\n]+", original)
            if clause.strip(" ，。；：、,.!?！？")
        ]

        first_new_index: int | None = None
        for index, clause in enumerate(clauses):
            normalized_clause = cls._normalize_timeline_text(clause)
            if len(normalized_clause) < 2:
                continue
            if not existing_text or normalized_clause not in existing_text:
                first_new_index = index
                break

        incremental_clauses: list[str] = []
        seen: set[str] = set()
        start_index = first_new_index if first_new_index is not None else 0
        for clause in clauses[start_index:]:
            normalized_clause = cls._normalize_timeline_text(clause)
            if len(normalized_clause) < 2 or normalized_clause in seen:
                continue
            seen.add(normalized_clause)
            if first_new_index is not None and normalized_clause in existing_text:
                continue
            incremental_clauses.append(clause)

        if incremental_clauses and first_new_index is not None:
            return "，".join(incremental_clauses)

        trimmed = original
        for source in existing_sources:
            source_text = str(source or "").strip()
            if source_text and trimmed.startswith(source_text):
                trimmed = trimmed[len(source_text):].strip(" ，。；：、,.!?！？")
        return trimmed or original

    @classmethod
    def _normalize_snapshot_for_append(cls, todo: TodoItem, snapshot: TicketSnapshot) -> TicketSnapshot:
        incremental_timeline_entry = cls._extract_incremental_timeline_entry(todo, snapshot.timeline_entry)
        return TicketSnapshot(
            title=todo.title,
            fields=merge_summary_fields_for_append(todo.summary_fields, snapshot.fields),
            current_summary=todo.current_summary,
            timeline_entry=merge_timeline_with_evidence(incremental_timeline_entry, snapshot.evidence_items),
            evidence_items=[],
        )

    @staticmethod
    def _resolve_todo_scenario(todo: TodoItem) -> str:
        for event in reversed(todo.timeline):
            scenario = str(event.scenario or "").strip()
            if scenario:
                return scenario
        return ""

    def _publish_event(self, event: TodoDomainEvent | None) -> None:
        if event is None or self._event_publisher is None:
            return
        self._event_publisher.publish(event)

    def save_analysis_result(self, snapshot: TicketSnapshot, scenario: str) -> SaveAnalysisResult:
        if self._selected_todo_id:
            selected_todo = self.get_selected_todo()
            if selected_todo is not None:
                snapshot = self._normalize_snapshot_for_append(selected_todo, snapshot)
            todo = self._store.append_analysis_to_todo(
                self._selected_todo_id,
                snapshot,
                scenario,
            )
            if todo is not None:
                self._selected_todo_id = None
                self._publish_event(TodoDomainEvent.appended(todo, scenario))
                return SaveAnalysisResult(action="append", todo=todo)

        todo = self._store.create_todo_from_analysis(snapshot, scenario)
        self._publish_event(TodoDomainEvent.created(todo, scenario))
        return SaveAnalysisResult(action="create", todo=todo)

    def complete_todo(self, todo_id: str) -> bool:
        completed = self._store.complete_todo(todo_id)
        if not completed:
            return False

        updated_todo = self._store.get_todo(todo_id)
        if updated_todo is not None:
            self._publish_event(
                TodoDomainEvent.completed(updated_todo, self._resolve_todo_scenario(updated_todo))
            )

        if self._selected_todo_id == todo_id:
            self._selected_todo_id = None
        if self._detail_todo_id == todo_id:
            self._detail_todo_id = None
        return True

    def delete_todo(self, todo_id: str) -> bool:
        todo_snapshot = self._store.get_todo(todo_id)
        deleted = self._store.delete_todo(todo_id)
        if not deleted:
            return False
        if self._selected_todo_id == todo_id:
            self._selected_todo_id = None
        if self._detail_todo_id == todo_id:
            self._detail_todo_id = None
        if todo_snapshot is not None:
            self._publish_event(
                TodoDomainEvent.deleted(todo_snapshot, self._resolve_todo_scenario(todo_snapshot))
            )
        return True

    def update_todo(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        current_summary: str | None = None,
        summary_fields: TicketSummaryFields | None = None,
        timeline: list[TimelineEvent] | None = None,
        conclusion: TodoConclusion | None = None,
        run_enrichment: bool = True,
    ) -> TodoItem | None:
        existing = self._store.get_todo(todo_id)
        if existing is None:
            return None
        changed_fields: list[str] = []
        if title is not None:
            changed_fields.append("title")
        if current_summary is not None:
            changed_fields.append("current_summary")
        if summary_fields is not None:
            changed_fields.append("summary_fields")
        if timeline is not None:
            changed_fields.append("timeline")
        if conclusion is not None:
            changed_fields.append("conclusion")

        resolved_summary = summary_fields or existing.summary_fields
        resolved_current_summary = current_summary if current_summary is not None else existing.current_summary
        resolved_timeline = timeline if timeline is not None else existing.timeline
        resolved_conclusion = conclusion if conclusion is not None else existing.conclusion

        if run_enrichment and self._enrichment_service is not None:
            enrichment = self._enrichment_service.enrich_for_update(
                previous_fields=existing.summary_fields,
                current_fields=resolved_summary,
                previous_problem_desc=existing.current_summary,
                current_problem_desc=resolved_current_summary,
                previous_conclusion=existing.conclusion.content,
                current_conclusion=resolved_conclusion.content,
            )
            resolved_summary = enrichment.summary_fields

        if self._conclusion_changed(existing.conclusion, resolved_conclusion):
            conclusion_event = self._build_conclusion_timeline_event(resolved_conclusion)
            resolved_timeline = self._replace_conclusion_timeline_event(resolved_timeline, conclusion_event)
            if "timeline" not in changed_fields:
                changed_fields.append("timeline")

        updated = self._store.update_todo(
            todo_id,
            title=title,
            current_summary=resolved_current_summary,
            summary_fields=resolved_summary,
            timeline=resolved_timeline,
            conclusion=resolved_conclusion,
        )
        if updated is not None and changed_fields:
            self._publish_event(
                TodoDomainEvent.updated(
                    updated,
                    self._resolve_todo_scenario(updated),
                    changed_fields,
                )
            )
        return updated

    @staticmethod
    def _conclusion_changed(previous: TodoConclusion, current: TodoConclusion) -> bool:
        if str(previous.content or "").strip() != str(current.content or "").strip():
            return True
        previous_attachments = [
            (attachment.name, attachment.path, int(attachment.size_bytes))
            for attachment in previous.attachments
        ]
        current_attachments = [
            (attachment.name, attachment.path, int(attachment.size_bytes))
            for attachment in current.attachments
        ]
        return previous_attachments != current_attachments

    @staticmethod
    def _build_conclusion_timeline_event(conclusion: TodoConclusion) -> TimelineEvent:
        attachment_names = [attachment.name for attachment in conclusion.attachments if attachment.name]
        suffix = f"\n附件: {', '.join(attachment_names[:5])}" if attachment_names else ""
        content = str(conclusion.content or "").strip() or "结论已清空"
        return TimelineEvent(
            kind="conclusion",
            scenario="结论更新",
            content=f"{content}{suffix}".strip(),
            attachments=[],
        )

    @staticmethod
    def _replace_conclusion_timeline_event(
        timeline: list[TimelineEvent],
        conclusion_event: TimelineEvent,
    ) -> list[TimelineEvent]:
        remaining = [
            event
            for event in timeline
            if str(event.kind or "").strip() != "conclusion"
        ]
        return remaining + [conclusion_event]

    def build_manual_sync_event(self, todo_id: str) -> TodoDomainEvent | None:
        todo = self._store.get_todo(todo_id)
        if todo is None:
            return None
        return TodoDomainEvent.manual_sync(
            todo,
            self._resolve_todo_scenario(todo),
        )

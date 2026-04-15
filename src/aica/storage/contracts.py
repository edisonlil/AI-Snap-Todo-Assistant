"""Storage contracts for Todo, project, and binding persistence."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from aica.environment_access import (
        EnvironmentAccessEntryRecord,
        ProjectEnvironmentBundle,
        ProjectEnvironmentRecord,
    )
    from aica.models import TicketSnapshot, TicketSummaryFields
    from aica.todo_models import TimelineEvent, TodoConclusion, TodoItem, TodoProjectLink


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass(frozen=True)
class ProjectRecord:
    id: str
    project_name: str
    customer_name: str = ""
    task_order_no: str = ""
    follow_up_started_at: str = ""
    support_ended_at: str = ""
    product_line: str = ""
    product_version: str = ""
    project_manager: str = ""
    project_level: str = "normal"
    aliases: tuple[str, ...] = ()
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_snapshot(self) -> dict[str, str]:
        return {
            "project_id": self.id,
            "project_name": self.project_name,
            "customer_name": self.customer_name,
            "task_order_no": self.task_order_no,
            "follow_up_started_at": self.follow_up_started_at,
            "support_ended_at": self.support_ended_at,
            "product_line": self.product_line,
            "product_version": self.product_version,
            "project_manager": self.project_manager,
            "project_level": self.project_level,
        }


@dataclass(frozen=True)
class ProjectMatchResult:
    status: str
    reason: str = ""
    project_id: str = ""
    matched_group_name: str = ""
    matched_alias: str = ""
    project_snapshot: dict[str, str] = field(default_factory=dict)


class TodoRepository(Protocol):
    path: str

    def list_active_todos(self) -> list["TodoItem"]:
        """Return active todos ordered by last update time."""

    def get_todo(self, todo_id: str) -> "TodoItem | None":
        """Return a single todo detail when present."""

    def create_todo_from_analysis(self, snapshot: "TicketSnapshot", scenario: str) -> "TodoItem":
        """Create a Todo from a parsed analysis snapshot."""

    def append_analysis_to_todo(
        self,
        todo_id: str,
        snapshot: "TicketSnapshot",
        scenario: str,
    ) -> "TodoItem | None":
        """Append a new timeline event to an existing Todo."""

    def complete_todo(self, todo_id: str) -> bool:
        """Mark a Todo as done."""

    def delete_todo(self, todo_id: str) -> bool:
        """Delete a Todo."""

    def update_todo(
        self,
        todo_id: str,
        *,
        title: str | None = None,
        current_summary: str | None = None,
        summary_fields: "TicketSummaryFields | None" = None,
        timeline: list["TimelineEvent"] | None = None,
        conclusion: "TodoConclusion | None" = None,
    ) -> "TodoItem | None":
        """Update editable Todo fields."""


class ProjectRepository(Protocol):
    path: str

    def upsert_projects(self, projects: list[ProjectRecord]) -> list[ProjectRecord]:
        """Create or update project master data."""

    def upsert_project(self, project: ProjectRecord) -> ProjectRecord:
        """Create or update a single project record."""

    def list_projects(
        self,
        query: str = "",
        *,
        include_expired: bool = True,
        now: str | None = None,
    ) -> list[ProjectRecord]:
        """List project records and their aliases."""

    def get_project_by_task_order_no(self, task_order_no: str) -> ProjectRecord | None:
        """Fetch a project by business key."""

    def replace_project_aliases(self, project_id: str, aliases: list[str]) -> list[str]:
        """Replace normalized aliases for a project."""

    def delete_project(self, project_id: str) -> bool:
        """Delete a project record and its aliases."""

    def match_project_by_group_name(
        self,
        group_name: str,
        *,
        now: str | None = None,
    ) -> ProjectMatchResult:
        """Resolve a project from a group name."""

    def get_project_link(self, todo_id: str) -> "TodoProjectLink | None":
        """Fetch the current project link for a Todo."""

    def bind_todo_to_project(self, todo_id: str, match_result: ProjectMatchResult) -> "TodoProjectLink":
        """Persist the latest project match result for a Todo."""


class BindingRepository(Protocol):
    path: str

    def list_bindings(self, todo_id: str) -> list[dict[str, Any]]:
        """Return bound records only."""

    def list_records(self, todo_id: str) -> list[dict[str, Any]]:
        """Return all sync records for a Todo."""

    def get_binding(self, todo_id: str, integration_id: str) -> dict[str, Any] | None:
        """Return a bound record when external_id exists."""

    def get_record(self, todo_id: str, integration_id: str) -> dict[str, Any] | None:
        """Return a record regardless of binding state."""

    def has_binding(self, todo_id: str, integration_id: str) -> bool:
        """Check if an integration currently has an external binding."""

    def upsert_binding(
        self,
        todo_id: str,
        integration_id: str,
        external_id: str,
        *,
        external_url: str = "",
        event_id: str = "",
        event_type: str = "",
        sync_status: str = "",
        metadata: dict[str, Any] | None = None,
        deleted_locally: bool | None = None,
    ) -> dict[str, Any] | None:
        """Create or update a successful binding."""

    def update_sync_status(
        self,
        todo_id: str,
        integration_id: str,
        *,
        event_id: str = "",
        event_type: str = "",
        sync_status: str = "",
        metadata: dict[str, Any] | None = None,
        deleted_locally: bool | None = None,
        external_url: str = "",
    ) -> dict[str, Any] | None:
        """Update sync metadata without requiring an external id."""


class ProjectEnvironmentRepository(Protocol):
    path: str

    def list_project_environments(
        self,
        project_id: str,
        *,
        include_inactive: bool = False,
    ) -> list["ProjectEnvironmentBundle"]:
        """List project environments and their access entries."""

    def get_access_entry(self, entry_id: str) -> "EnvironmentAccessEntryRecord | None":
        """Fetch one environment access entry."""

    def upsert_project_environment(
        self,
        environment: "ProjectEnvironmentRecord",
    ) -> "ProjectEnvironmentRecord":
        """Create or update a project environment."""

    def replace_access_entries(
        self,
        environment_id: str,
        entries: list["EnvironmentAccessEntryRecord"],
    ) -> list["EnvironmentAccessEntryRecord"]:
        """Replace all access entries under one environment."""


class StorageMigrator(Protocol):
    path: str

    def ensure_schema(self) -> None:
        """Create or upgrade database schema."""

    def get_schema_version(self) -> str:
        """Return the current schema version."""

    def migrate_json_to_sqlite(self) -> None:
        """Import legacy JSON state into SQLite once."""

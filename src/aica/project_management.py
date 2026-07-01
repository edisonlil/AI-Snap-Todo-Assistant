"""Project validation and server sync helpers for the control panel."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any

from aica.storage.adapters import normalize_group_alias
from aica.storage.contracts import ProjectRecord
from aica.text_sanitize import sanitize_text

_PROJECT_FIELD_SEPARATOR_RE = re.compile(r"[\n,;\uFF0C\uFF1B\u3001]+")


def _now_iso() -> str:
    return datetime.now().isoformat()


def split_project_aliases(raw_value: Any) -> tuple[str, ...]:
    aliases: list[str] = []
    seen: set[str] = set()
    for item in re.split(r"[\n,，;；]+", sanitize_text(raw_value)):
        alias = sanitize_text(item)
        normalized = normalize_group_alias(alias)
        if not alias or not normalized or normalized in seen:
            continue
        aliases.append(alias)
        seen.add(normalized)
    return tuple(aliases)


def split_project_product_lines(raw_value: Any) -> tuple[str, ...]:
    product_lines: list[str] = []
    seen: set[str] = set()
    for item in _PROJECT_FIELD_SEPARATOR_RE.split(sanitize_text(raw_value)):
        product_line = sanitize_text(item)
        normalized = product_line.casefold()
        if not product_line or not normalized or normalized in seen:
            continue
        product_lines.append(product_line)
        seen.add(normalized)
    return tuple(product_lines)


def normalize_project_level(value: str) -> str:
    text = sanitize_text(value).casefold()
    if text in {"重要", "important", "high", "critical"}:
        return "important"
    return "normal"


def _parse_datetime_value(value: str, *, end_of_day: bool = False) -> datetime | None:
    text = sanitize_text(value)
    if not text:
        return None
    normalized = text.replace("/", "-")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed_date = datetime.strptime(normalized, "%Y-%m-%d").date()
        except ValueError:
            return None
        parsed = datetime.combine(parsed_date, time.max if end_of_day else time.min)
    else:
        if "T" not in normalized and " " not in normalized:
            parsed = datetime.combine(parsed.date(), time.max if end_of_day else time.min)
    return parsed


def is_project_active(support_ended_at: str, *, now: str | None = None) -> bool:
    parsed_end = _parse_datetime_value(support_ended_at, end_of_day=True)
    if parsed_end is None:
        normalized_end = sanitize_text(support_ended_at)
        current_time = sanitize_text(now) or _now_iso()
        return not normalized_end or normalized_end >= current_time
    parsed_now = _parse_datetime_value(sanitize_text(now) or _now_iso()) or datetime.now()
    return parsed_end >= parsed_now


@dataclass(frozen=True)
class ProjectAliasConflict:
    row_number: int
    task_order_no: str
    alias: str
    conflicting_project_id: str
    conflicting_project_name: str
    conflicting_task_order_no: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rowNumber": self.row_number,
            "taskOrderNo": self.task_order_no,
            "alias": self.alias,
            "conflictingProjectId": self.conflicting_project_id,
            "conflictingProjectName": self.conflicting_project_name,
            "conflictingTaskOrderNo": self.conflicting_task_order_no,
        }


@dataclass
class ProjectImportResult:
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    relinked_count: int = 0
    error_rows: list[dict[str, object]] = field(default_factory=list)
    alias_conflicts: list[ProjectAliasConflict] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "createdCount": self.created_count,
            "updatedCount": self.updated_count,
            "skippedCount": self.skipped_count,
            "relinkedCount": self.relinked_count,
            "errorRows": list(self.error_rows),
            "aliasConflicts": [item.to_dict() for item in self.alias_conflicts],
        }


def _payload_value(payload: dict[str, Any], snake_key: str, camel_key: str = "") -> Any:
    if snake_key in payload:
        return payload.get(snake_key)
    if camel_key and camel_key in payload:
        return payload.get(camel_key)
    return ""


def _payload_text(payload: dict[str, Any], snake_key: str, camel_key: str = "") -> str:
    return sanitize_text(_payload_value(payload, snake_key, camel_key))


def _payload_aliases(payload: dict[str, Any]) -> tuple[str, ...]:
    raw_aliases = _payload_value(payload, "chat_group_names", "chatGroupNames")
    if isinstance(raw_aliases, list):
        return split_project_aliases("\n".join(str(item) for item in raw_aliases))
    return split_project_aliases(raw_aliases)


def _merge_project_aliases(existing: ProjectRecord | None, remote_aliases: tuple[str, ...]) -> tuple[str, ...]:
    aliases: list[str] = []
    seen: set[str] = set()
    for alias in [*(existing.aliases if existing is not None else ()), *remote_aliases]:
        alias_name = sanitize_text(alias)
        normalized = normalize_group_alias(alias_name)
        if not alias_name or not normalized or normalized in seen:
            continue
        aliases.append(alias_name)
        seen.add(normalized)
    return tuple(aliases)


def project_record_from_server_payload(
    payload: dict[str, Any],
    *,
    existing: ProjectRecord | None = None,
) -> ProjectRecord:
    task_order_no = _payload_text(payload, "task_order_no", "taskOrderNo")
    project_name = _payload_text(payload, "project_name", "projectName")
    if not task_order_no:
        raise ValueError("task_order_no 不能为空")
    if not project_name:
        raise ValueError("project_name 不能为空")
    created_at = _payload_text(payload, "created_at", "createdAt")
    updated_at = _payload_text(payload, "updated_at", "updatedAt")
    remote_aliases = _payload_aliases(payload)
    return ProjectRecord(
        id=existing.id if existing is not None else str(uuid.uuid4()),
        project_name=project_name,
        customer_name=_payload_text(payload, "customer_name", "customerName"),
        task_order_no=task_order_no,
        follow_up_started_at=_payload_text(payload, "follow_up_started_at", "followUpStartedAt"),
        support_ended_at=_payload_text(payload, "support_ended_at", "supportEndedAt"),
        product_line=_payload_text(payload, "product_line", "productLine"),
        project_manager=_payload_text(payload, "project_manager", "projectManager"),
        project_level=normalize_project_level(_payload_text(payload, "project_level", "projectLevel") or "normal"),
        aliases=_merge_project_aliases(existing, remote_aliases),
        created_at=created_at or (existing.created_at if existing is not None else _now_iso()),
        updated_at=updated_at or _now_iso(),
    )


def project_record_from_payload(payload: dict[str, Any], existing: ProjectRecord | None = None) -> ProjectRecord:
    task_order_no = sanitize_text(payload.get("taskOrderNo") or payload.get("task_order_no"))
    project_name = sanitize_text(payload.get("projectName") or payload.get("project_name"))
    if not task_order_no:
        raise ValueError("任务单号不能为空")
    if not project_name:
        raise ValueError("项目名称不能为空")
    aliases_payload = payload.get("aliases", ())
    aliases = split_project_aliases(
        "\n".join(str(item) for item in aliases_payload) if isinstance(aliases_payload, list) else aliases_payload
    )
    return ProjectRecord(
        id=sanitize_text(payload.get("id")) or (existing.id if existing is not None else str(uuid.uuid4())),
        project_name=project_name,
        customer_name=sanitize_text(payload.get("customerName") or payload.get("customer_name")),
        task_order_no=task_order_no,
        follow_up_started_at=sanitize_text(payload.get("followUpStartedAt") or payload.get("follow_up_started_at")),
        support_ended_at=sanitize_text(payload.get("supportEndedAt") or payload.get("support_ended_at")),
        product_line=sanitize_text(payload.get("productLine") or payload.get("product_line")),
        project_manager=sanitize_text(payload.get("projectManager") or payload.get("project_manager")),
        project_level=normalize_project_level(
            sanitize_text(payload.get("projectLevel") or payload.get("project_level")) or "normal"
        ),
        aliases=aliases,
        created_at=existing.created_at if existing is not None else _now_iso(),
        updated_at=_now_iso(),
    )


def project_to_payload(project: ProjectRecord, *, now: str | None = None) -> dict[str, object]:
    current_time = sanitize_text(now) or _now_iso()
    return {
        "id": project.id,
        "projectName": project.project_name,
        "customerName": project.customer_name,
        "taskOrderNo": project.task_order_no,
        "followUpStartedAt": project.follow_up_started_at,
        "supportEndedAt": project.support_ended_at,
        "productLine": project.product_line,
        "projectManager": project.project_manager,
        "projectLevel": project.project_level,
        "aliases": list(project.aliases),
        "aliasCount": len(project.aliases),
        "isExpired": not is_project_active(project.support_ended_at, now=current_time),
    }


def _release_project_aliases(
    reservations: dict[str, list[tuple[str, str, str]]],
    project_id: str,
) -> None:
    for normalized_alias in list(reservations.keys()):
        remaining = [item for item in reservations[normalized_alias] if item[0] != project_id]
        if remaining:
            reservations[normalized_alias] = remaining
            continue
        reservations.pop(normalized_alias, None)


def _reserve_project_aliases(
    reservations: dict[str, list[tuple[str, str, str]]],
    project: ProjectRecord,
    *,
    now: str,
) -> None:
    if not is_project_active(project.support_ended_at, now=now):
        return
    for alias in project.aliases:
        normalized_alias = normalize_group_alias(alias)
        if not normalized_alias:
            continue
        reservations.setdefault(normalized_alias, []).append(
            (project.id, project.project_name, project.task_order_no)
        )


def find_active_alias_conflicts(
    project: ProjectRecord,
    projects: list[ProjectRecord],
    *,
    now: str | None = None,
) -> list[ProjectAliasConflict]:
    current_time = sanitize_text(now) or _now_iso()
    conflicts: list[ProjectAliasConflict] = []
    reservations: dict[str, list[tuple[str, str, str]]] = {}
    for existing in projects:
        _reserve_project_aliases(reservations, existing, now=current_time)
    _release_project_aliases(reservations, project.id)
    if not is_project_active(project.support_ended_at, now=current_time):
        return []
    for alias in project.aliases:
        normalized_alias = normalize_group_alias(alias)
        for conflicting_id, conflicting_name, conflicting_task_order in reservations.get(normalized_alias, []):
            if conflicting_id == project.id:
                continue
            conflicts.append(
                ProjectAliasConflict(
                    row_number=0,
                    task_order_no=project.task_order_no,
                    alias=alias,
                    conflicting_project_id=conflicting_id,
                    conflicting_project_name=conflicting_name,
                    conflicting_task_order_no=conflicting_task_order,
                )
            )
    return conflicts


def sync_projects_from_server(client, project_repository, todo_store) -> ProjectImportResult:
    result = ProjectImportResult()
    items = client.fetch_my_latest_projects(page_size=200, max_pages=100)
    existing_projects = project_repository.list_projects(include_expired=True)
    existing_by_task_order = {project.task_order_no: project for project in existing_projects if project.task_order_no}

    saved_records: list[tuple[ProjectRecord, bool]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            result.skipped_count += 1
            continue
        task_order_no = _payload_text(item, "task_order_no", "taskOrderNo")
        project_name = _payload_text(item, "project_name", "projectName")
        if not task_order_no or not project_name:
            result.skipped_count += 1
            result.error_rows.append(
                {
                    "rowNumber": index,
                    "message": "task_order_no 和 project_name 为必填字段",
                }
            )
            continue
        existing = existing_by_task_order.get(task_order_no)
        try:
            project = project_record_from_server_payload(item, existing=existing)
        except ValueError as exc:
            result.skipped_count += 1
            result.error_rows.append(
                {
                    "rowNumber": index,
                    "message": str(exc),
                }
            )
            continue
        saved_records.append((project, existing is None))
        existing_by_task_order[project.task_order_no] = project

    for project, created in saved_records:
        project_repository.upsert_project(project)
        if created:
            result.created_count += 1
        else:
            result.updated_count += 1

    if saved_records:
        result.relinked_count = todo_store.relink_open_unresolved_todos()
    return result

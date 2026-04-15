from __future__ import annotations

import sqlite3
from pathlib import Path
import os
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.environment_access import (
    EnvironmentAccessEntryRecord,
    EnvironmentAccessService,
    ProjectEnvironmentBundle,
    ProjectEnvironmentRecord,
    TotpService,
)
from aica.storage.contracts import ProjectRecord
from aica.storage.sqlite.environment_repositories import SQLiteProjectEnvironmentRepository
from aica.storage.sqlite.repositories import SQLiteProjectRepository, SQLiteStorageMigrator
from aica.todo_detail_panel import _TodoDetailBridge
from aica.todo_models import TodoItem, TodoProjectLink


class _FakeEnvironmentRepository:
    def __init__(self, bundles: list[ProjectEnvironmentBundle]) -> None:
        self._bundles = bundles
        self._entries = {
            entry.id: entry
            for bundle in bundles
            for entry in bundle.entries
        }

    @property
    def path(self) -> str:
        return ""

    def list_project_environments(self, project_id: str, *, include_inactive: bool = False) -> list[ProjectEnvironmentBundle]:
        return list(self._bundles) if project_id == "project-1" else []

    def get_access_entry(self, entry_id: str) -> EnvironmentAccessEntryRecord | None:
        return self._entries.get(entry_id)

    def upsert_project_environment(self, environment: ProjectEnvironmentRecord) -> ProjectEnvironmentRecord:
        return environment

    def replace_access_entries(
        self,
        environment_id: str,
        entries: list[EnvironmentAccessEntryRecord],
    ) -> list[EnvironmentAccessEntryRecord]:
        return list(entries)


def test_environment_schema_and_repository_roundtrip() -> None:
    fd, raw_path = tempfile.mkstemp(suffix=".db", dir=Path.cwd())
    os.close(fd)
    Path(raw_path).unlink(missing_ok=True)
    db_path = Path(raw_path)
    SQLiteStorageMigrator(db_path).ensure_schema()

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "project_environments" in tables
    assert "environment_access_entries" in tables

    project_repository = SQLiteProjectRepository(db_path)
    environment_repository = SQLiteProjectEnvironmentRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="示例项目",
            task_order_no="WO-001",
        )
    )

    environment = environment_repository.upsert_project_environment(
        ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="测试环境",
            env_type="test",
            note="3 个可用访问方式",
        )
    )
    entries = environment_repository.replace_access_entries(
        environment.id,
        [
                EnvironmentAccessEntryRecord(
                    id="entry-1",
                    environment_id=environment.id,
                    access_name="应用后台",
                    access_type="web",
                    sort_order=1,
                    url_or_host="https://test.example.com",
                    username="admin",
                    password_encrypted="pass-1",
                requires_otp=True,
                otp_secret_encrypted="JBSWY3DPEHPK3PXP",
            ),
                EnvironmentAccessEntryRecord(
                    id="entry-2",
                    environment_id=environment.id,
                    access_name="客户现场环境",
                    sort_order=2,
                    note="仅备注说明",
                ),
        ],
    )

    bundles = environment_repository.list_project_environments("project-1")
    assert len(bundles) == 1
    assert bundles[0].environment.env_name == "测试环境"
    assert [entry.access_name for entry in bundles[0].entries] == ["应用后台", "客户现场环境"]
    assert environment_repository.get_access_entry(entries[0].id) is not None


def test_environment_access_service_and_totp() -> None:
    bundle = ProjectEnvironmentBundle(
        environment=ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="测试环境",
        ),
        entries=(
            EnvironmentAccessEntryRecord(
                id="entry-1",
                environment_id="env-1",
                access_name="应用后台",
                username="admin",
                password_encrypted="secret-pass",
                requires_otp=True,
                otp_secret_encrypted="JBSWY3DPEHPK3PXP",
            ),
        ),
    )
    service = EnvironmentAccessService(_FakeEnvironmentRepository([bundle]))
    launch = service.prepare_login("entry-1")

    assert launch is not None
    assert launch.username == "admin"
    assert launch.password == "secret-pass"
    assert len(launch.otp_code) == 6
    assert 1 <= launch.otp_remaining_seconds <= 30

    code, remaining = TotpService().generate("JBSWY3DPEHPK3PXP", for_timestamp=0)
    assert code == "282760"
    assert remaining == 30


def test_todo_detail_bridge_environment_access_flow() -> None:
    bundle = ProjectEnvironmentBundle(
        environment=ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="测试环境",
            note="可直接访问",
        ),
        entries=(
            EnvironmentAccessEntryRecord(
                id="entry-1",
                environment_id="env-1",
                access_name="应用后台",
                url_or_host="https://test.example.com",
                username="admin",
                password_encrypted="secret-pass",
                requires_otp=True,
                otp_secret_encrypted="JBSWY3DPEHPK3PXP",
            ),
        ),
    )
    bridge = _TodoDetailBridge(
        environment_access_service=EnvironmentAccessService(_FakeEnvironmentRepository([bundle]))
    )
    todo = TodoItem(
        id="todo-1",
        title="排查登录问题",
        project_link=TodoProjectLink(
            todo_id="todo-1",
            project_id="project-1",
            match_status="matched",
            project_snapshot={"project_name": "示例项目"},
        ),
    )

    bridge.set_todo(todo)
    assert bridge.environmentAccessSummaryText == "环境访问 · 1 组"
    assert len(bridge.environmentAccessGroups) == 1
    assert bridge.environmentAccessGroups[0]["expanded"] is False

    bridge.toggleEnvironmentGroup("env-1")
    assert bridge.environmentAccessGroups[0]["expanded"] is True

    bridge.startEnvironmentLogin("entry-1")
    first_group = bridge.environmentAccessGroups[0]
    first_entry = first_group["entries"][0]
    assert first_group["expanded"] is True
    assert first_entry["loginActivated"] is True
    assert first_entry["canCopyPassword"] is True
    assert first_entry["canCopyOtp"] is True

    bridge.copyEnvironmentOtp("entry-1")
    assert bridge.environmentAccessMessage == "已复制验证码"

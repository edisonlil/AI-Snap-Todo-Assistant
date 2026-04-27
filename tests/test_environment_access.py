from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.environment_access import (  # noqa: E402
    EnvironmentAccessEntryRecord,
    EnvironmentAccessService,
    ProjectEnvironmentBundle,
    ProjectEnvironmentRecord,
    TotpService,
)
from aica.storage.contracts import ProjectRecord  # noqa: E402
from aica.storage.sqlite.environment_repositories import SQLiteProjectEnvironmentRepository  # noqa: E402
from aica.storage.sqlite.repositories import SQLiteProjectRepository, SQLiteStorageMigrator  # noqa: E402
import aica.todo_detail_panel as todo_detail_panel  # noqa: E402
from aica.todo_detail_panel import _TodoDetailBridge  # noqa: E402
from aica.todo_models import TodoItem, TodoProjectLink  # noqa: E402


class _Clipboard:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, value: str) -> None:
        self.text = value


class _FakeEnvironmentRepository:
    def __init__(self, bundles: list[ProjectEnvironmentBundle]) -> None:
        self._bundles = bundles
        self._entries = {
            entry.id: entry
            for bundle in bundles
            for entry in bundle.entries
        }
        self._environments = {
            bundle.environment.id: bundle.environment
            for bundle in bundles
        }

    @property
    def path(self) -> str:
        return ""

    def list_global_environments(self, *, include_inactive: bool = False) -> list[ProjectEnvironmentBundle]:
        return [bundle for bundle in self._bundles if bundle.environment.scope == "global"]

    def list_project_environments(self, project_id: str, *, include_inactive: bool = False) -> list[ProjectEnvironmentBundle]:
        return [
            bundle
            for bundle in self._bundles
            if bundle.environment.scope == "project" and bundle.environment.project_id == project_id
        ]

    def list_effective_environments(self, project_id: str, *, include_inactive: bool = False) -> list[ProjectEnvironmentBundle]:
        return [*self.list_project_environments(project_id), *self.list_global_environments()]

    def get_project_environment(self, environment_id: str) -> ProjectEnvironmentRecord | None:
        return self._environments.get(environment_id)

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

    def delete_project_environment(self, environment_id: str) -> bool:
        return bool(self._environments.pop(environment_id, None))


def _notification_messages(bridge: _TodoDetailBridge) -> list[str]:
    return [str(item["message"]) for item in bridge.notificationBridge.notifications]


def test_environment_schema_and_repository_roundtrip() -> None:
    fd, raw_path = tempfile.mkstemp(suffix=".db", dir=Path.cwd())
    os.close(fd)
    Path(raw_path).unlink(missing_ok=True)
    db_path = Path(raw_path)
    SQLiteStorageMigrator(db_path).ensure_schema()

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    assert "project_environments" in tables
    assert "environment_access_entries" in tables

    project_repository = SQLiteProjectRepository(db_path)
    environment_repository = SQLiteProjectEnvironmentRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="demo project",
            task_order_no="WO-001",
        )
    )

    environment = environment_repository.upsert_project_environment(
        ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="test-env",
            scope="project",
            env_type="test",
            note="two entries",
        )
    )
    entries = environment_repository.replace_access_entries(
        environment.id,
        [
            EnvironmentAccessEntryRecord(
                id="entry-1",
                environment_id=environment.id,
                access_name="console",
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
                access_name="customer-site",
                sort_order=2,
                note="manual only",
            ),
        ],
    )

    bundles = environment_repository.list_project_environments("project-1")

    assert len(bundles) == 1
    assert bundles[0].environment.env_name == "test-env"
    assert bundles[0].environment.scope == "project"
    assert [entry.access_name for entry in bundles[0].entries] == ["console", "customer-site"]
    assert environment_repository.get_access_entry(entries[0].id) is not None


def test_environment_repository_supports_global_and_effective_scope() -> None:
    fd, raw_path = tempfile.mkstemp(suffix=".db", dir=Path.cwd())
    os.close(fd)
    Path(raw_path).unlink(missing_ok=True)
    db_path = Path(raw_path)
    SQLiteStorageMigrator(db_path).ensure_schema()

    project_repository = SQLiteProjectRepository(db_path)
    environment_repository = SQLiteProjectEnvironmentRepository(db_path)
    project_repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="demo",
            task_order_no="WO-001",
        )
    )
    global_env = environment_repository.upsert_project_environment(
        ProjectEnvironmentRecord(
            id="global-1",
            project_id="",
            env_name="253-env",
            scope="global",
        )
    )
    project_env = environment_repository.upsert_project_environment(
        ProjectEnvironmentRecord(
            id="project-env-1",
            project_id="project-1",
            env_name="253-env",
            scope="project",
        )
    )
    environment_repository.replace_access_entries(
        global_env.id,
        [
            EnvironmentAccessEntryRecord(
                id="global-entry",
                environment_id=global_env.id,
                access_name="console",
                username="global-user",
                otp_secret_encrypted="JBSWY3DPEHPK3PXP",
                requires_otp=True,
            ),
        ],
    )
    environment_repository.replace_access_entries(
        project_env.id,
        [
            EnvironmentAccessEntryRecord(
                id="project-entry",
                environment_id=project_env.id,
                access_name="console",
                username="project-user",
            ),
        ],
    )

    global_bundles = environment_repository.list_global_environments()
    effective_bundles = environment_repository.list_effective_environments("project-1")

    assert len(global_bundles) == 1
    assert global_bundles[0].environment.scope == "global"
    assert len(effective_bundles) == 1
    assert effective_bundles[0].environment.scope == "project"
    assert effective_bundles[0].is_project_override is True
    assert [entry.username for entry in effective_bundles[0].entries] == ["project-user"]


def test_environment_access_service_and_totp() -> None:
    bundle = ProjectEnvironmentBundle(
        environment=ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="test-env",
            scope="project",
        ),
        entries=(
            EnvironmentAccessEntryRecord(
                id="entry-1",
                environment_id="env-1",
                access_name="console",
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


def test_totp_service_supports_unpadded_freeotp_base32_secret() -> None:
    code, remaining = TotpService().generate("MZXW6YTBOI", for_timestamp=0)

    assert len(code) == 6
    assert remaining == 30


def test_totp_service_supports_otpauth_uri_with_sha256() -> None:
    service = EnvironmentAccessService(_FakeEnvironmentRepository([]))
    parsed = service._parse_otp_config(  # noqa: SLF001
        "otpauth://totp/demo:admin?secret=JZ3UMYBQNQDRDL7D&algorithm=SHA256"
    )
    code, remaining = TotpService().generate(
        str(parsed["secret"]),
        for_timestamp=0,
        digits=int(parsed["digits"]),
        period_seconds=int(parsed["period_seconds"]),
        algorithm=str(parsed["algorithm"]),
    )

    assert code == "849342"
    assert remaining == 30


def test_todo_detail_bridge_environment_access_flow() -> None:
    bundle = ProjectEnvironmentBundle(
        environment=ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="test-env",
            scope="project",
            note="direct access",
        ),
        entries=(
            EnvironmentAccessEntryRecord(
                id="entry-1",
                environment_id="env-1",
                access_name="console",
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
        title="check login flow",
        project_link=TodoProjectLink(
            todo_id="todo-1",
            project_id="project-1",
            match_status="matched",
            project_snapshot={"project_name": "demo"},
        ),
    )

    bridge.set_todo(todo)
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
    assert len(first_entry["otpCode"]) == 6

    bridge.copyEnvironmentOtp("entry-1")
    assert bridge.environmentAccessMessage
    assert _notification_messages(bridge)


def test_todo_detail_bridge_copies_environment_login_fields(monkeypatch) -> None:
    clipboard = _Clipboard()
    monkeypatch.setattr(todo_detail_panel.QApplication, "clipboard", lambda: clipboard)
    bundle = ProjectEnvironmentBundle(
        environment=ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="test-env",
            scope="project",
        ),
        entries=(
            EnvironmentAccessEntryRecord(
                id="entry-1",
                environment_id="env-1",
                access_name="console",
                url_or_host="https://example.com/login",
                username="admin",
                password_encrypted="secret-pass",
            ),
        ),
    )
    bridge = _TodoDetailBridge(
        environment_access_service=EnvironmentAccessService(_FakeEnvironmentRepository([bundle]))
    )
    todo = TodoItem(
        id="todo-1",
        title="copy login fields",
        project_link=TodoProjectLink(
            todo_id="todo-1",
            project_id="project-1",
            match_status="matched",
            project_snapshot={"project_name": "demo"},
        ),
    )

    bridge.set_todo(todo)
    bridge.copyEnvironmentAddress("entry-1")
    assert clipboard.text == "https://example.com/login"

    bridge.copyEnvironmentUsername("entry-1")
    assert clipboard.text == "admin"

    bridge.copyEnvironmentPassword("entry-1")
    assert clipboard.text == "secret-pass"

    bridge.copyEnvironmentLoginInfo("entry-1")
    assert clipboard.text.splitlines() == [
        "地址：https://example.com/login",
        "账号：admin",
        "密码：secret-pass",
    ]


def test_todo_detail_bridge_includes_global_environment_entries() -> None:
    bundle = ProjectEnvironmentBundle(
        environment=ProjectEnvironmentRecord(
            id="global-env-1",
            project_id="",
            env_name="253-env",
            scope="global",
        ),
        entries=(
            EnvironmentAccessEntryRecord(
                id="global-entry-1",
                environment_id="global-env-1",
                access_name="console",
                url_or_host="https://example.com/login",
            ),
        ),
    )
    bridge = _TodoDetailBridge(
        environment_access_service=EnvironmentAccessService(_FakeEnvironmentRepository([bundle]))
    )
    todo = TodoItem(
        id="todo-1",
        title="check global environment",
        project_link=TodoProjectLink(
            todo_id="todo-1",
            project_id="project-1",
            match_status="matched",
            project_snapshot={"project_name": "demo"},
        ),
    )

    bridge.set_todo(todo)

    assert bridge.environmentAccessGroups[0]["scope"] == "global"
    assert bridge.environmentAccessGroups[0]["isGlobal"] is True
    assert bridge.environmentAccessGroups[0]["entries"][0]["scope"] == "global"


def test_todo_detail_bridge_login_without_helper_data_does_not_expand_helper() -> None:
    bundle = ProjectEnvironmentBundle(
        environment=ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="test-env",
            scope="project",
        ),
        entries=(
            EnvironmentAccessEntryRecord(
                id="entry-1",
                environment_id="env-1",
                access_name="console",
                url_or_host="https://example.com/login",
            ),
        ),
    )
    bridge = _TodoDetailBridge(
        environment_access_service=EnvironmentAccessService(_FakeEnvironmentRepository([bundle]))
    )
    todo = TodoItem(
        id="todo-1",
        title="check helper",
        project_link=TodoProjectLink(
            todo_id="todo-1",
            project_id="project-1",
            match_status="matched",
            project_snapshot={"project_name": "demo"},
        ),
    )

    bridge.set_todo(todo)
    bridge.startEnvironmentLogin("entry-1")

    first_group = bridge.environmentAccessGroups[0]
    first_entry = first_group["entries"][0]
    assert first_group["expanded"] is True
    assert first_entry["loginActivated"] is False
    assert first_entry["canCopyPassword"] is False
    assert first_entry["canCopyOtp"] is False


def test_todo_detail_bridge_hides_standalone_otp_placeholder() -> None:
    bundle = ProjectEnvironmentBundle(
        environment=ProjectEnvironmentRecord(
            id="env-1",
            project_id="project-1",
            env_name="prod-env",
            scope="project",
        ),
        entries=(
            EnvironmentAccessEntryRecord(
                id="otp-1",
                environment_id="env-1",
                access_name="OTP",
            ),
            EnvironmentAccessEntryRecord(
                id="entry-1",
                environment_id="env-1",
                access_name="admin-console",
                url_or_host="https://example.com/login",
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
        title="check otp placeholder",
        project_link=TodoProjectLink(
            todo_id="todo-1",
            project_id="project-1",
            match_status="matched",
            project_snapshot={"project_name": "demo"},
        ),
    )

    bridge.set_todo(todo)
    group = bridge.environmentAccessGroups[0]
    assert group["entryCount"] == 1
    assert [entry["name"] for entry in group["entries"]] == ["admin-console"]

from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.storage.contracts import ProjectRecord  # noqa: E402
from aica.storage.sqlite.repositories import SQLiteProjectRepository  # noqa: E402


def _make_db_path(name: str) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix=f"{name}-", suffix=".db", dir=Path.cwd())
    os.close(fd)
    path = Path(raw_path)
    path.unlink(missing_ok=True)
    return path


def test_search_project_candidates_prefers_exact_alias_then_name() -> None:
    repository = SQLiteProjectRepository(_make_db_path("project-candidate-search"))
    repository.upsert_project(
        ProjectRecord(
            id="project-1",
            project_name="Demo Project",
            customer_name="Demo Customer",
            task_order_no="WO-001",
            product_line="WPS协作",
            aliases=("测试群",),
        )
    )
    repository.upsert_project(
        ProjectRecord(
            id="project-2",
            project_name="测试群项目",
            customer_name="Other Customer",
            task_order_no="WO-002",
            product_line="文档中台",
            aliases=("other-group",),
        )
    )

    candidates = repository.search_project_candidates_by_group_name("测试群")

    assert [candidate.project_id for candidate in candidates][:2] == ["project-1", "project-2"]
    assert candidates[0].match_reason == "alias_exact"
    assert candidates[0].project_snapshot["project_name"] == "Demo Project"


def test_search_project_candidates_returns_empty_for_blank_query() -> None:
    repository = SQLiteProjectRepository(_make_db_path("project-candidate-empty"))

    assert repository.search_project_candidates_by_group_name("") == []


def test_search_project_candidates_excludes_expired_projects_by_default() -> None:
    repository = SQLiteProjectRepository(_make_db_path("project-candidate-expired"))
    repository.upsert_project(
        ProjectRecord(
            id="expired-project",
            project_name="广汽过保项目",
            customer_name="广汽传祺",
            task_order_no="WO-EXPIRED",
            support_ended_at="2024-01-01T00:00:00",
            aliases=("广汽",),
        )
    )
    repository.upsert_project(
        ProjectRecord(
            id="active-project",
            project_name="广汽在保项目",
            customer_name="广汽传祺",
            task_order_no="WO-ACTIVE",
            support_ended_at="2099-01-01T00:00:00",
            aliases=("广汽",),
        )
    )

    candidates = repository.search_project_candidates_by_group_name("广汽")

    assert [candidate.project_id for candidate in candidates] == ["active-project"]
    assert all(candidate.is_expired is False for candidate in candidates)

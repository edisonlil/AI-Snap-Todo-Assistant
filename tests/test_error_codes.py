from __future__ import annotations

from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.error_codes import (  # noqa: E402
    ErrorCodeLookupService,
    ExternalErrorCodeClient,
    extract_error_codes,
    load_builtin_error_code_records,
)
from aica.storage.sqlite.error_code_repository import ErrorCodeRecord, SQLiteErrorCodeRepository  # noqa: E402
from aica.todo.models import TimelineEvent, TodoItem  # noqa: E402


def _db_path() -> Path:
    return Path(tempfile.mkdtemp()) / "aica.db"


def test_extract_error_codes_keeps_only_explicit_error_codes() -> None:
    text = (
        "2026-05-03 用户反馈接口返回 403，request_id=14160111d8a9c2c4d58d，"
        "错误码 400000007，编辑失败 code=15041，补充错误码:20023。"
    )

    assert extract_error_codes(text) == ["400000007", "15041", "20023"]


def test_repository_returns_cached_records() -> None:
    repository = SQLiteErrorCodeRepository(_db_path())
    repository.upsert_many(
        [
            ErrorCodeRecord(
                code="15041",
                title="EditNoAvailableWpsService",
                message="文字组件服务所有节点均已下线",
                meaning="无可用服务节点",
                suggestion="检查 editserver 节点状态并扩容",
                source_name="文档中台错误码说明",
                category="编辑服务",
            )
        ]
    )

    records = repository.get_many(["15041", "400000007"])

    assert records["15041"].title == "EditNoAvailableWpsService"
    assert records["15041"].source_type == "online_doc"
    assert "400000007" not in records


class _SuccessfulClient(ExternalErrorCodeClient):
    def fetch_many(self, codes: list[str]) -> list[ErrorCodeRecord]:
        return [
            ErrorCodeRecord(
                code=code,
                title=f"Remote {code}",
                message="远端说明",
                meaning="远端含义",
                suggestion="远端建议",
                source_name="在线文档",
                category="远端",
            )
            for code in codes
        ]


def test_lookup_fetches_and_caches_missing_codes_when_api_succeeds() -> None:
    repository = SQLiteErrorCodeRepository(_db_path())
    service = ErrorCodeLookupService(repository=repository, external_client=_SuccessfulClient())
    todo = TodoItem(id="todo-1", title="接口失败", current_summary="错误码 88888888")

    payload = service.lookup_for_todo(todo)

    assert payload["items"][0]["code"] == "88888888"
    assert payload["items"][0]["title"] == "88888888"
    assert payload["items"][0]["desc"] == "远端说明"
    assert repository.get_many(["88888888"])["88888888"].message == "远端说明"


def test_lookup_api_failure_without_cache_returns_generic_empty_state() -> None:
    repository = SQLiteErrorCodeRepository(_db_path())
    service = ErrorCodeLookupService(repository=repository)
    todo = TodoItem(id="todo-1", title="接口失败", current_summary="错误码 99999999")

    payload = service.lookup_for_todo(todo)

    assert payload["status"] == "empty"
    assert payload["items"] == []
    assert "request_id" in payload["emptyText"]


def test_lookup_uses_timeline_and_seeded_builtin_records() -> None:
    repository = SQLiteErrorCodeRepository(_db_path())
    repository.seed_builtin_if_needed(load_builtin_error_code_records(), "test-seed")
    service = ErrorCodeLookupService(repository=repository)
    todo = TodoItem(
        id="todo-1",
        title="打开文档失败",
        current_summary="用户反馈保存失败",
        timeline=[TimelineEvent(content="日志显示错误码 15041")],
    )

    payload = service.lookup_for_todo(todo)

    assert payload["status"] == "success"
    assert payload["items"][0]["code"] == "15041"
    assert payload["items"][0]["source"] == "文档中台错误码说明"


def test_builtin_seed_includes_storage_backend_5xx_code_from_pdf() -> None:
    records = {record.code: record for record in load_builtin_error_code_records()}

    assert records["11002"].title == "StorageBackendStore5XX"
    assert records["11002"].source_name == "文档中台错误码说明"


def test_seed_builtin_records_only_runs_once_for_same_version() -> None:
    repository = SQLiteErrorCodeRepository(_db_path())
    records = [
        ErrorCodeRecord(
            code="77777777",
            title="First",
            message="第一次导入",
            source_name="在线文档",
        )
    ]

    assert repository.seed_builtin_if_needed(records, "seed-v1") is True
    assert repository.seed_builtin_if_needed(
        [
            ErrorCodeRecord(
                code="77777777",
                title="Second",
                message="第二次导入",
                source_name="在线文档",
            )
        ],
        "seed-v1",
    ) is False

    assert repository.get_many(["77777777"])["77777777"].title == "First"

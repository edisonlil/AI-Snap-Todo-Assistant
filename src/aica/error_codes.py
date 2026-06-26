"""Error-code extraction and lookup for assist troubleshooting."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from aica.paths import aica_database_file, runtime_root
from aica.storage.sqlite.error_code_repository import ErrorCodeRecord, SQLiteErrorCodeRepository
from aica.config import ServerConfig
from aica.server_api import ChattodoServerClient, ChattodoServerError
from aica.text_sanitize import sanitize_text
from aica.todo.models import TodoItem


BUILTIN_ERROR_CODE_SEED_VERSION = "2026-05-03-online-docs-v2"
_ERROR_CODE_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])(?:错误码|error\s*code|code)\s*[:=：]?\s*(\d{5,9})", re.IGNORECASE)
_BARE_LONG_CODE_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])(\d{5,9})(?![A-Za-z0-9_-])")


class ExternalErrorCodeClient:
    """Placeholder client for future online-doc error-code lookup."""

    def fetch_many(self, codes: list[str]) -> list[ErrorCodeRecord]:
        return []


class ChattodoServerErrorCodeClient(ExternalErrorCodeClient):
    def __init__(self, config: ServerConfig) -> None:
        self._config = config

    def fetch_many(self, codes: list[str]) -> list[ErrorCodeRecord]:
        if not codes:
            return []
        describe = _build_describe_text(codes)
        try:
            payload = ChattodoServerClient.from_config(self._config).lookup_error_codes(describe=describe)
        except ChattodoServerError as exc:
            raise exc
        return [
            ErrorCodeRecord(
                code=item["code"],
                title=item["code"],
                message=item["description"],
                meaning=item["value"],
                suggestion="",
                source_name="Chattodo 服务端",
                source_type="runtime_workflow",
                raw_payload=dict(item),
            )
            for item in payload.get("items", [])
            if isinstance(item, dict) and sanitize_text(item.get("code")).strip()
        ]


class ErrorCodeLookupService:
    def __init__(
        self,
        *,
        repository: SQLiteErrorCodeRepository | None = None,
        external_client: ExternalErrorCodeClient | None = None,
    ) -> None:
        self._repository = repository or SQLiteErrorCodeRepository(aica_database_file())
        self._external_client = external_client or ExternalErrorCodeClient()
        self._repository.seed_builtin_if_needed(
            load_builtin_error_code_records(),
            BUILTIN_ERROR_CODE_SEED_VERSION,
        )

    def lookup_for_todo(self, todo: TodoItem) -> dict[str, object]:
        codes = extract_error_codes(_todo_text(todo))
        if not codes:
            return _empty_result()

        cached = self._repository.get_many(codes)
        missing_codes = [code for code in codes if code not in cached]
        if missing_codes:
            try:
                fetched = self._external_client.fetch_many(missing_codes)
            except Exception:
                fetched = []
            if fetched:
                self._repository.upsert_many(fetched)
                cached.update(self._repository.get_many(missing_codes))

        items = [
            _record_to_payload(cached[code])
            for code in codes
            if code in cached
        ]
        if not items:
            result = _empty_result()
            result["countLabel"] = f"识别 {len(codes)} 个错误码，暂无本地说明"
            return result
        return {
            "status": "success",
            "title": "错误码说明",
            "countLabel": f"命中 {len(items)} 条说明",
            "count": f"命中 {len(items)} 条说明",
            "emptyText": _GENERIC_EMPTY_TEXT,
            "items": items,
        }

    def lookup_for_todo_with_server(self, todo: TodoItem, *, server_config: ServerConfig | None = None) -> dict[str, object]:
        codes = extract_error_codes(_todo_text(todo))
        if server_config is not None and bool(getattr(server_config, "enabled", False)):
            try:
                client = ChattodoServerErrorCodeClient(server_config)
                fetched = client.fetch_many(codes)
            except Exception:
                fetched = []
            if fetched:
                try:
                    self._repository.upsert_many(fetched)
                    cached = self._repository.get_many(codes)
                    items = [
                        _record_to_payload(cached[code])
                        for code in codes
                        if code in cached
                    ]
                except Exception:
                    items = [_record_to_payload(record) for record in fetched]
                if items:
                    return {
                        "status": "success",
                        "title": "错误码说明",
                        "countLabel": f"命中 {len(items)} 条说明",
                        "count": f"命中 {len(items)} 条说明",
                        "emptyText": _GENERIC_EMPTY_TEXT,
                        "items": items,
                    }
        return self.lookup_for_todo(todo)


def extract_error_codes(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", sanitize_text(text))
    result: list[str] = []
    seen: set[str] = set()
    for pattern in (_ERROR_CODE_PATTERN, _BARE_LONG_CODE_PATTERN):
        for match in pattern.finditer(normalized):
            code = match.group(1)
            if _looks_like_non_error_code(normalized, match.start(1), match.end(1)):
                continue
            if code not in seen:
                seen.add(code)
                result.append(code)
    return result


def load_builtin_error_code_records() -> list[ErrorCodeRecord]:
    path = _resource_file("error_codes_seed.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return []
    result: list[ErrorCodeRecord] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        code = sanitize_text(item.get("code"))
        if not code:
            continue
        result.append(
            ErrorCodeRecord(
                code=code,
                title=sanitize_text(item.get("title")),
                message=sanitize_text(item.get("message")),
                meaning=sanitize_text(item.get("meaning")),
                suggestion=sanitize_text(item.get("suggestion")),
                source_name=sanitize_text(item.get("source_name")),
                source_type=sanitize_text(item.get("source_type")) or "online_doc",
                source_url=sanitize_text(item.get("source_url")),
                category=sanitize_text(item.get("category")),
                raw_payload=dict(item),
            )
        )
    return result


def _todo_text(todo: TodoItem) -> str:
    parts = [
        sanitize_text(todo.title),
        sanitize_text(todo.current_summary),
        sanitize_text(getattr(todo.conclusion, "content", "")),
    ]
    for event in list(todo.timeline or []):
        parts.append(sanitize_text(getattr(event, "content", "")))
        payload = getattr(event, "payload", {}) or {}
        if isinstance(payload, dict):
            parts.extend(sanitize_text(value) for value in payload.values())
    return "\n".join(part for part in parts if part)


def _resource_file(name: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return runtime_root() / "aica" / "resources" / name
    return Path(__file__).resolve().with_name("resources") / name


def _looks_like_non_error_code(text: str, start: int, end: int) -> bool:
    code = text[start:end]
    if len(code) < 5 or len(code) > 9:
        return True
    before = text[max(0, start - 16):start].lower()
    after = text[end:min(len(text), end + 16)].lower()
    if re.search(r"\d{4}[-/.]\d{1,2}[-/.]?$", before) or re.match(r"^[-/.]\d{1,2}", after):
        return True
    if any(keyword in before for keyword in ("request_id", "requestid", "traceid", "trace_id")):
        return True
    if any(keyword in after for keyword in ("request_id", "requestid", "traceid", "trace_id")):
        return True
    return False


def _record_to_payload(record: ErrorCodeRecord) -> dict[str, str]:
    desc = record.message or record.meaning or record.suggestion
    text_parts = [f"【错误码】{record.code}"]
    if record.title:
        text_parts.append(record.title)
    if record.message:
        text_parts.append(record.message)
    if record.meaning and record.meaning != record.message:
        text_parts.append(f"含义：{record.meaning}")
    if record.suggestion:
        text_parts.append(f"建议：{record.suggestion}")
    if record.source_name:
        text_parts.append(f"来源：{record.source_name}")
    return {
        "code": record.code,
        "title": record.code,
        "desc": desc,
        "text": "\n".join(text_parts),
        "source": record.source_name,
        "category": record.category,
    }


_GENERIC_EMPTY_TEXT = "暂无命中，建议补充完整错误码、request_id、发生时间和接口返回体"


def _empty_result() -> dict[str, object]:
    return {
        "status": "empty",
        "title": "错误码说明",
        "countLabel": "暂无错误码说明",
        "count": "暂无错误码说明",
        "emptyText": _GENERIC_EMPTY_TEXT,
        "items": [],
    }


def _build_describe_text(codes: list[str]) -> str:
    unique_codes = [sanitize_text(code).strip() for code in codes if sanitize_text(code).strip()]
    return "；".join(f"错误码 {code}" for code in unique_codes)

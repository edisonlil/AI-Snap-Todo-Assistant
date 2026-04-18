"""Pure helpers for control panel config persistence."""
from __future__ import annotations

import json
import re
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from aica.config import AppConfig
from aica.hotkey import normalize_hotkey
from aica.llm.service import LLMService, ModelResolutionError
from aica.paths import save_storage_paths, storage_config_file


MEGABYTE = 1024 * 1024
TASK_NAMES = (
    "analysis",
    "log_analysis",
    "plan_export",
    "context_summary",
)


def format_image_limit_megabytes(image_bytes: int) -> str:
    value = max(1, int(image_bytes)) / MEGABYTE
    formatted = f"{value:.2f}".rstrip("0").rstrip(".")
    return formatted or "1"


def parse_image_limit_megabytes(value: str) -> int:
    text = str(value or "").strip()
    if not text:
        raise ValueError("图片压缩阈值不能为空")
    try:
        parsed = float(text)
    except ValueError as exc:
        raise ValueError("图片压缩阈值必须是数字") from exc
    if parsed <= 0:
        raise ValueError("图片压缩阈值必须大于 0")
    return max(1, int(round(parsed * MEGABYTE)))


def validate_runtime_bindings(config: AppConfig) -> None:
    service = LLMService(config)
    try:
        for task_name in TASK_NAMES:
            service.resolve_task_model(task_name)
    except ModelResolutionError as exc:
        raise ValueError(str(exc)) from exc


def normalize_directory_path(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("目录不能为空")
    return str(Path(text).expanduser())


def persist_storage_paths(
    *,
    data_dir: str,
    log_dir: str,
    previous_data_dir: str,
    previous_log_dir: str,
) -> dict[str, str]:
    normalized_data_dir = Path(normalize_directory_path(data_dir))
    normalized_log_dir = Path(normalize_directory_path(log_dir))
    _migrate_storage_contents(
        source_dir=Path(previous_data_dir).expanduser(),
        target_dir=normalized_data_dir,
        skip_name=storage_config_file().name,
    )
    _migrate_log_files(
        source_dir=Path(previous_log_dir).expanduser(),
        target_dir=normalized_log_dir,
    )
    saved = save_storage_paths(
        data_dir=str(normalized_data_dir),
        log_dir=str(normalized_log_dir),
    )
    return {
        "data_dir": str(saved.data_dir),
        "log_dir": str(saved.log_dir),
        "storage_config_path": str(storage_config_file()),
    }


def _migrate_storage_contents(source_dir: Path, target_dir: Path, *, skip_name: str = "") -> None:
    if source_dir == target_dir or not source_dir.exists():
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        if skip_name and item.name == skip_name:
            continue
        destination = target_dir / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
            continue
        if not destination.exists():
            shutil.copy2(item, destination)


def _migrate_log_files(source_dir: Path, target_dir: Path) -> None:
    if source_dir == target_dir or not source_dir.exists():
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    for file_name in ("error.log",):
        source_file = source_dir / file_name
        target_file = target_dir / file_name
        if source_file.exists() and not target_file.exists():
            shutil.copy2(source_file, target_file)


def persist_control_panel_config(
    config_manager,
    config: AppConfig,
    *,
    capture_hotkey: str,
    max_image_megabytes: str,
) -> AppConfig:
    updated = deepcopy(config)
    updated.hotkeys.capture = normalize_hotkey(capture_hotkey)
    updated.max_image_bytes = parse_image_limit_megabytes(max_image_megabytes)
    updated.default_provider_id = updated.task_model_bindings.analysis.provider_id
    validate_runtime_bindings(updated)
    config_manager.save(updated)
    return updated


def load_integration_config(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_integration_config(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_script_integrations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = payload.get("todo_event_integrations", []) if isinstance(payload, dict) else []
    if not isinstance(raw_items, list):
        return []
    return [
        deepcopy(item)
        for item in raw_items
        if isinstance(item, dict) and str(item.get("type") or "").strip() == "script"
    ]


def replace_script_integrations(
    payload: dict[str, Any],
    integrations: list[dict[str, Any]],
) -> dict[str, Any]:
    updated = deepcopy(payload) if isinstance(payload, dict) else {}
    raw_items = updated.get("todo_event_integrations", [])
    other_items = [
        deepcopy(item)
        for item in raw_items
        if not (isinstance(item, dict) and str(item.get("type") or "").strip() == "script")
    ] if isinstance(raw_items, list) else []
    updated["todo_event_integrations"] = [deepcopy(item) for item in integrations] + other_items
    return updated


def build_script_integration(script_path: str, existing_ids: set[str] | None = None) -> dict[str, Any]:
    path = Path(script_path).expanduser().resolve()
    command, args = _build_script_command(path)
    return {
        "id": _make_unique_integration_id(path.stem, existing_ids or set()),
        "name": path.stem,
        "enabled": True,
        "type": "script",
        "command": command,
        "args": args,
        "cwd": str(path.parent),
        "timeout_seconds": 8,
        "env": {},
    }


def update_script_integration_path(integration: dict[str, Any], script_path: str) -> dict[str, Any]:
    updated = deepcopy(integration)
    path = Path(script_path).expanduser().resolve()
    command, args = _build_script_command(path)
    updated["type"] = "script"
    updated["command"] = command
    updated["args"] = args
    updated["cwd"] = str(path.parent)
    updated["name"] = path.stem
    return updated


def script_integration_display_path(integration: dict[str, Any]) -> str:
    command = str(integration.get("command") or "").strip()
    args_payload = integration.get("args", [])
    args = [str(item) for item in args_payload if str(item).strip()] if isinstance(args_payload, list) else []
    command_name = Path(command).name.lower()
    if command_name in {"py", "py.exe", "python", "python.exe", "pythonw.exe"}:
        for arg in args:
            if not arg.startswith("-"):
                return arg
    if "powershell" in command_name:
        for index, arg in enumerate(args[:-1]):
            if arg.lower() == "-file":
                return args[index + 1]
    return command


def _build_script_command(script_path: Path) -> tuple[str, list[str]]:
    suffix = script_path.suffix.lower()
    script_text = str(script_path)
    if suffix in {".py", ".pyw"}:
        return "py", [script_text]
    if suffix == ".ps1":
        return "powershell", ["-ExecutionPolicy", "Bypass", "-File", script_text]
    return script_text, []


def _make_unique_integration_id(stem: str, existing_ids: set[str]) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "script"
    if normalized not in existing_ids:
        return normalized
    index = 2
    while f"{normalized}-{index}" in existing_ids:
        index += 1
    return f"{normalized}-{index}"

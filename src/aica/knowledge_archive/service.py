"""Automatic knowledge-base archive for completed Todo items."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from os.path import relpath
from typing import Protocol

from ..llm.types import Message
from ..models import summarize_issue_title
from ..paths import error_log_file, knowledge_base_dir
from ..text_sanitize import sanitize_text
from ..ticket_field_resolver import normalize_ticket_type
from ..todo.events import TodoDomainEvent, TodoDomainEventType, TodoEventHandler
from ..todo.models import TodoItem, TodoStatus
from ..worker import (
    append_plan_export_attachment_section,
    append_plan_export_timeline_visual_section,
    build_plan_export_timeline_markdown,
    ensure_plan_export_timeline_section,
    normalize_markdown_content,
)

_PATH_PLACEHOLDER = "未提供"
_TEXT_PLACEHOLDER = "未提供"
_UNKNOWN_TEXT = "未知"
_UNSPECIFIED_FEATURE = "未明确"
_WIKI_DIRNAME = "_wiki"
_OPERATION_TICKET_TYPE = "操作类"
_INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_ARCHIVE_TITLE_PREFIX = "aica"


class TodoReader(Protocol):
    def get_todo(self, todo_id: str) -> TodoItem | None:
        """Return a Todo by id."""


class RuntimeConfigProvider(Protocol):
    def __call__(self) -> object:
        """Return the latest runtime config."""


@dataclass(frozen=True)
class KnowledgeArchivePaths:
    archive_root: Path
    product_line: str
    version: str
    ticket_type: str
    note_path: Path
    wiki_index_path: Path


def _append_archive_log(message: str) -> None:
    normalized = str(message or "").strip()
    if not normalized:
        return
    try:
        log_file = error_log_file()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[knowledge_archive] {datetime.now().isoformat()} {normalized}\n")
    except OSError:
        return


def _clean_text(value: object, *, fallback: str = _TEXT_PLACEHOLDER) -> str:
    text = sanitize_text(value).strip()
    if not text or text == _UNKNOWN_TEXT:
        return fallback
    return text


def _clean_optional_text(value: object) -> str:
    text = sanitize_text(value).strip()
    if not text or text == _UNKNOWN_TEXT:
        return ""
    return text


def _safe_segment(value: object, *, fallback: str = _PATH_PLACEHOLDER) -> str:
    text = _clean_text(value, fallback=fallback)
    text = _INVALID_PATH_CHARS_RE.sub("_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or fallback


def _ticket_type_for_archive(todo: TodoItem) -> str:
    summary = "\n".join(part for part in (todo.title, todo.current_summary) if str(part or "").strip())
    return normalize_ticket_type(todo.summary_fields.ticket_type, summary_text=summary)


def should_archive_todo(todo: TodoItem) -> bool:
    if str(todo.status or "").strip() != TodoStatus.DONE:
        return False
    return _ticket_type_for_archive(todo) != _OPERATION_TICKET_TYPE


def _short_todo_id(todo_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]", "", str(todo_id or "").strip())
    if not normalized:
        return "unknown"
    return normalized[:8]


def _short_title(todo: TodoItem) -> str:
    title_source = todo.current_summary.strip() or todo.title.strip() or "未分类任务"
    title = summarize_issue_title(title_source, fallback="未分类任务", max_length=30)
    return _safe_segment(title, fallback="未分类任务")


def _build_note_stem(todo: TodoItem) -> str:
    return f"{_ARCHIVE_TITLE_PREFIX}_{_short_todo_id(todo.id)}_{_short_title(todo)}"


def build_knowledge_archive_paths(archive_root: Path, todo: TodoItem) -> KnowledgeArchivePaths:
    product_line = _safe_segment(todo.summary_fields.product_line)
    version = _safe_segment(todo.summary_fields.ticket_version)
    ticket_type = _safe_segment(_ticket_type_for_archive(todo), fallback="未分类")
    note_dir = archive_root / product_line / version / ticket_type
    note_path = note_dir / f"{_build_note_stem(todo)}.md"
    wiki_index_path = archive_root / product_line / _WIKI_DIRNAME / "index.md"
    return KnowledgeArchivePaths(
        archive_root=archive_root,
        product_line=product_line,
        version=version,
        ticket_type=ticket_type,
        note_path=note_path,
        wiki_index_path=wiki_index_path,
    )


def _todo_to_payload(todo: TodoItem) -> dict[str, object]:
    timeline_items = sorted(
        list(todo.timeline),
        key=lambda item: (sanitize_text(item.timestamp), sanitize_text(item.created_at), sanitize_text(item.id)),
    )
    return {
        "id": todo.id,
        "title": todo.title.strip(),
        "current_summary": todo.current_summary.strip(),
        "summary_fields": todo.summary_fields.to_dict(),
        "conclusion": {
            "content": todo.conclusion.content.strip(),
            "updatedAt": todo.conclusion.updated_at,
            "attachments": [
                {
                    "id": attachment.id,
                    "name": attachment.name,
                    "path": attachment.path,
                    "sizeBytes": attachment.size_bytes,
                    "kind": _attachment_kind(attachment.name),
                }
                for attachment in todo.conclusion.attachments
            ],
        },
        "project_link": todo.project_link.to_dict(),
        "timeline": [
            {
                "id": item.id,
                "timestamp": item.timestamp,
                "created_at": item.created_at,
                "kind": item.kind,
                "scenario": item.scenario,
                "type": item.event_type,
                "payload": dict(item.payload),
                "status": item.status,
                "content": item.content.strip(),
                "attachments": [
                    {
                        "id": attachment.id,
                        "name": attachment.name,
                        "path": attachment.path,
                        "sizeBytes": attachment.size_bytes,
                        "kind": _attachment_kind(attachment.name),
                    }
                    for attachment in item.attachments
                ],
            }
            for item in timeline_items
        ],
    }


def _looks_like_image(name: str) -> bool:
    normalized = str(name or "").strip().lower()
    return normalized.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))


def _looks_like_video(name: str) -> bool:
    normalized = str(name or "").strip().lower()
    return normalized.endswith((".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm"))


def _attachment_kind(name: str) -> str:
    if _looks_like_image(name):
        return "image"
    if _looks_like_video(name):
        return "video"
    return ""


def _build_archive_metadata_lines(todo_payload: dict[str, object]) -> list[str]:
    summary_fields = dict(todo_payload.get("summary_fields", {}) or {})
    project_link = dict(todo_payload.get("project_link", {}) or {})
    project_snapshot = dict(project_link.get("project_snapshot", {}) or {})
    product_line = _clean_text(summary_fields.get("product_line"))
    ticket_version = _clean_text(summary_fields.get("ticket_version"))
    ticket_summary = "\n".join(
        part for part in (todo_payload.get("title", ""), todo_payload.get("current_summary", "")) if str(part or "").strip()
    )
    ticket_type = normalize_ticket_type(summary_fields.get("ticket_type"), summary_text=ticket_summary)
    feature_point = _clean_text(summary_fields.get("feature_point"), fallback=_UNSPECIFIED_FEATURE)
    return [
        f"工单标题: {_clean_text(todo_payload.get('title'))}",
        f"产品线: {product_line}",
        f"版本号: {ticket_version}",
        f"功能点: {feature_point}",
        f"工单类型: {ticket_type}",
        f"环境: {_clean_text(summary_fields.get('environment'))}",
        f"项目名: {_clean_text(project_snapshot.get('project_name'))}",
        f"项目编号: {_clean_text(project_snapshot.get('task_order_no'))}",
        f"项目客户: {_clean_text(project_snapshot.get('customer_name'))}",
        f"项目经理: {_clean_text(project_snapshot.get('project_manager'))}",
        f"根因分类: {_clean_text(summary_fields.get('root_cause'))}",
        f"根因说明: {_clean_text(summary_fields.get('root_cause_desc'))}",
        f"当前摘要: {_clean_text(todo_payload.get('current_summary'))}",
        f"问题结论: {_clean_text(dict(todo_payload.get('conclusion', {}) or {}).get('content'), fallback='暂无明确结论')}",
    ]


def build_knowledge_archive_messages(todo_payload: dict[str, object]) -> list[Message]:
    timeline_lines = build_plan_export_timeline_markdown(todo_payload).replace("## 时间线回顾", "").strip()
    metadata_text = "\n".join(_build_archive_metadata_lines(todo_payload))
    user_prompt = (
        "请基于以下工单信息，整理成适合本地知识库归档的 Markdown 解决方案文档。\n"
        "只输出 Markdown 正文，不要解释，不要输出代码块围栏。\n\n"
        "写作目标：\n"
        "1. 文档用于沉淀已处理工单的解决经验，重点是问题现象、定位过程、最终结论、复用建议。\n"
        "2. 不要记录群聊名称、沟通过程话术或泛化管理动作。\n"
        "3. 没有提供的信息统一写“未提供”“未明确”或“待确认”，不要猜测。\n"
        "4. 文档结构稳定，便于后续作为本地 wiki 和检索知识库继续加工。\n\n"
        "推荐结构：\n"
        "# 解决方案标题\n"
        "## 元数据\n"
        "- 用表格记录：产品线、版本号、功能点、项目名、环境、工单类型。\n"
        "## 问题描述\n"
        "## 解决过程\n"
        "## 问题结论\n"
        "## 复用建议\n"
        "## 时间线回顾\n\n"
        f"元数据:\n{metadata_text}\n\n"
        f"时间线:\n{timeline_lines or '- 暂无时间线记录'}"
    )
    return [
        Message(
            role="system",
            content=(
                "你是一名负责沉淀工单解决方案的知识库编辑助手。"
                "输出内容必须准确、可检索、适合长期维护。"
            ),
        ),
        Message(role="user", content=user_prompt),
    ]


def _metadata_table_lines(todo_payload: dict[str, object]) -> list[str]:
    summary_fields = dict(todo_payload.get("summary_fields", {}) or {})
    project_link = dict(todo_payload.get("project_link", {}) or {})
    project_snapshot = dict(project_link.get("project_snapshot", {}) or {})
    ticket_summary = "\n".join(
        part for part in (todo_payload.get("title", ""), todo_payload.get("current_summary", "")) if str(part or "").strip()
    )
    ticket_type = normalize_ticket_type(summary_fields.get("ticket_type"), summary_text=ticket_summary)
    return [
        "| 字段 | 内容 |",
        "| --- | --- |",
        f"| 产品线 | {_clean_text(summary_fields.get('product_line'))} |",
        f"| 版本号 | {_clean_text(summary_fields.get('ticket_version'))} |",
        f"| 功能点 | {_clean_text(summary_fields.get('feature_point'), fallback=_UNSPECIFIED_FEATURE)} |",
        f"| 项目名 | {_clean_text(project_snapshot.get('project_name'))} |",
        f"| 环境 | {_clean_text(summary_fields.get('environment'))} |",
        f"| 工单类型 | {_clean_text(ticket_type, fallback='未分类')} |",
    ]


def _build_archive_fallback_markdown(todo_payload: dict[str, object]) -> str:
    title = _clean_text(todo_payload.get("title"))
    conclusion_content = _clean_text(
        dict(todo_payload.get("conclusion", {}) or {}).get("content"),
        fallback="暂无明确结论",
    )
    summary = _clean_text(todo_payload.get("current_summary"))
    metadata_block = "\n".join(_metadata_table_lines(todo_payload))
    timeline_block = build_plan_export_timeline_markdown(todo_payload).strip()
    return (
        f"# {title}\n\n"
        "## 元数据\n\n"
        f"{metadata_block}\n\n"
        "## 问题描述\n\n"
        f"{summary}\n\n"
        "## 解决过程\n\n"
        "- 详见时间线回顾中的排查与处理记录。\n\n"
        "## 问题结论\n\n"
        f"{conclusion_content}\n\n"
        "## 复用建议\n\n"
        "- 后续遇到相似问题时，优先根据标题、功能点、错误现象和时间线中的关键动作进行检索。\n\n"
        f"{timeline_block}"
    ).strip()


def _yaml_scalar(value: object, *, fallback: str = _TEXT_PLACEHOLDER) -> str:
    return json.dumps(_clean_text(value, fallback=fallback), ensure_ascii=False)


def _yaml_optional_scalar(value: object) -> str:
    return json.dumps(_clean_optional_text(value), ensure_ascii=False)


def _frontmatter_tags(todo: TodoItem) -> list[str]:
    tags: list[str] = []
    for candidate in (
        _clean_optional_text(todo.summary_fields.product_line),
        _clean_optional_text(todo.summary_fields.ticket_version),
        _clean_optional_text(_ticket_type_for_archive(todo)),
        _clean_optional_text(todo.summary_fields.feature_point),
        _clean_optional_text(todo.summary_fields.root_cause),
    ):
        if candidate and candidate not in tags:
            tags.append(candidate)
    return tags


def build_knowledge_frontmatter(todo: TodoItem) -> str:
    project_snapshot = dict(todo.project_link.project_snapshot or {})
    lines = [
        "---",
        f"todo_id: {_yaml_scalar(todo.id)}",
        f"title: {_yaml_scalar(_short_title(todo), fallback='未分类任务')}",
        f"product_line: {_yaml_scalar(todo.summary_fields.product_line)}",
        f"ticket_version: {_yaml_scalar(todo.summary_fields.ticket_version)}",
        f"ticket_type: {_yaml_scalar(_ticket_type_for_archive(todo), fallback='未分类')}",
        f"feature_point: {_yaml_scalar(todo.summary_fields.feature_point, fallback=_UNSPECIFIED_FEATURE)}",
        f"root_cause: {_yaml_scalar(todo.summary_fields.root_cause)}",
        f"root_cause_desc: {_yaml_scalar(todo.summary_fields.root_cause_desc)}",
        f"environment: {_yaml_scalar(todo.summary_fields.environment)}",
        f"project_name: {_yaml_scalar(project_snapshot.get('project_name'))}",
        f"project_task_order_no: {_yaml_scalar(project_snapshot.get('task_order_no'))}",
        f"completed_at: {_yaml_scalar(todo.completed_at or todo.updated_at)}",
        f"updated_at: {_yaml_scalar(todo.updated_at)}",
        f"archive_generated_at: {_yaml_scalar(datetime.now().isoformat())}",
        "tags:",
    ]
    for tag in _frontmatter_tags(todo):
        lines.append(f"  - {json.dumps(tag, ensure_ascii=False)}")
    if lines[-1] == "tags:":
        lines.append(f"  - {json.dumps('未分类', ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def _render_archive_body(todo_payload: dict[str, object], llm_service: object | None, timeout: int) -> str:
    if llm_service is not None and hasattr(llm_service, "run_task"):
        try:
            raw_markdown = llm_service.run_task(
                "plan_export",
                messages=build_knowledge_archive_messages(todo_payload),
                temperature=0.2,
                timeout=min(max(1, int(timeout or 30)), 30),
            )
            normalized = ensure_plan_export_timeline_section(
                normalize_markdown_content(str(raw_markdown or "")),
                todo_payload,
            )
            if normalized:
                return normalized
        except Exception as exc:  # noqa: BLE001
            _append_archive_log(f"LLM archive generation failed for todo {todo_payload.get('id', '')}: {exc}")
    return _build_archive_fallback_markdown(todo_payload)


def archive_completed_todo(
    todo: TodoItem,
    *,
    llm_service: object | None = None,
    timeout_seconds: int = 30,
    archive_root: Path | None = None,
) -> Path | None:
    if not should_archive_todo(todo):
        return None
    root = Path(archive_root or knowledge_base_dir()).expanduser()
    paths = build_knowledge_archive_paths(root, todo)
    todo_payload = _todo_to_payload(todo)
    body = _render_archive_body(todo_payload, llm_service, timeout_seconds)
    paths.note_path.parent.mkdir(parents=True, exist_ok=True)
    body = append_plan_export_timeline_visual_section(body, todo_payload, paths.note_path)
    body = append_plan_export_attachment_section(body, todo_payload, paths.note_path)
    markdown = f"{build_knowledge_frontmatter(todo)}\n\n{body.strip()}\n"
    paths.note_path.write_text(markdown, encoding="utf-8")
    rebuild_product_line_wiki_index(root, paths.product_line)
    return paths.note_path


def _parse_frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---\n"):
        return {}
    lines = text.splitlines()
    data: dict[str, str] = {}
    index = 1
    while index < len(lines):
        line = lines[index]
        if line.strip() == "---":
            break
        if not line or line.startswith("  - "):
            index += 1
            continue
        if ":" not in line:
            index += 1
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        if value:
            try:
                parsed = json.loads(value)
            except Exception:
                parsed = value
            data[key.strip()] = str(parsed)
        index += 1
    return data


def _note_title_from_frontmatter(path: Path) -> str:
    frontmatter = _parse_frontmatter(path)
    if frontmatter.get("title"):
        return frontmatter["title"]
    stem = path.stem
    if "_" in stem:
        return stem.split("_", 2)[-1]
    return stem


def rebuild_product_line_wiki_index(archive_root: Path, product_line: str) -> Path:
    product_line_dir = Path(archive_root) / product_line
    wiki_dir = product_line_dir / _WIKI_DIRNAME
    wiki_dir.mkdir(parents=True, exist_ok=True)
    note_files = [
        path
        for path in product_line_dir.rglob("*.md")
        if _WIKI_DIRNAME not in path.parts
    ]
    entries: dict[str, dict[str, list[Path]]] = {}
    for path in note_files:
        version = path.parent.parent.name
        ticket_type = path.parent.name
        entries.setdefault(version, {}).setdefault(ticket_type, []).append(path)

    lines = [
        f"# {product_line} Wiki 索引",
        "",
        "> 自动生成，请勿手动编辑。",
        "",
    ]
    if not note_files:
        lines.extend(["- 暂无已归档方案", ""])
    else:
        lines.extend(["## 版本导航", ""])
        for version in sorted(entries):
            lines.append(f"- {version}")
        lines.append("")
        for version in sorted(entries):
            lines.append(f"## {version}")
            lines.append("")
            for ticket_type in sorted(entries[version]):
                lines.append(f"### {ticket_type}")
                lines.append("")
                for path in sorted(entries[version][ticket_type], key=lambda item: item.name):
                    title = _note_title_from_frontmatter(path)
                    relative_path = relpath(path, wiki_dir).replace("\\", "/")
                    updated_label = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    lines.append(f"- [{title}]({relative_path}) · 更新 {updated_label}")
                lines.append("")
    index_path = wiki_dir / "index.md"
    index_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return index_path


class KnowledgeArchiveEventHandler(TodoEventHandler):
    def __init__(
        self,
        *,
        todo_store: TodoReader,
        runtime_config_provider: RuntimeConfigProvider,
        archive_root: Path | None = None,
    ) -> None:
        self._todo_store = todo_store
        self._runtime_config_provider = runtime_config_provider
        self._archive_root = Path(archive_root).expanduser() if archive_root is not None else knowledge_base_dir()

    def handle(self, event: TodoDomainEvent) -> None:
        if event.event_type != TodoDomainEventType.COMPLETED:
            return
        todo = self._todo_store.get_todo(event.todo_id)
        if todo is None or not should_archive_todo(todo):
            return
        llm_service = None
        timeout_seconds = 30
        try:
            runtime_config = self._runtime_config_provider()
            llm_service = getattr(runtime_config, "llm_service", None)
            timeout_seconds = int(getattr(runtime_config, "plan_export_timeout_seconds", 30) or 30)
        except Exception as exc:  # noqa: BLE001
            _append_archive_log(f"Runtime config unavailable for todo {event.todo_id}: {exc}")
        try:
            archive_completed_todo(
                todo,
                llm_service=llm_service,
                timeout_seconds=timeout_seconds,
                archive_root=self._archive_root,
            )
        except Exception as exc:  # noqa: BLE001
            _append_archive_log(f"Knowledge archive failed for todo {event.todo_id}: {exc}")

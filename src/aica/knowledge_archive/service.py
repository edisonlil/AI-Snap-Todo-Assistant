"""Automatic knowledge-base archive for completed Todo items."""
from __future__ import annotations

import json
import re
import filecmp
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from os.path import relpath
from typing import Protocol

from ..llm.types import Message
from ..models import normalize_issue_product_path
from ..paths import error_log_file, knowledge_base_dir
from ..text_sanitize import sanitize_text
from ..ticket_field_resolver import normalize_ticket_type
from ..todo.events import TodoDomainEvent, TodoDomainEventType, TodoEventHandler
from ..todo.models import TodoItem, TodoStatus
from ..worker import (
    normalize_markdown_content,
)

_PATH_PLACEHOLDER = "未提供"
_TEXT_PLACEHOLDER = "未提供"
_UNKNOWN_TEXT = "未知"
_UNSPECIFIED_FEATURE = "未明确"
_WIKI_DIRNAME = "_wiki"
_OPERATION_TICKET_TYPE = "操作类"
_INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_URL_RE = re.compile(r"https?://[^\s<>\"]+")
_DEFAULT_MAJOR_VERSION = "V7"
_MAJOR_VERSION_RE = re.compile(r"(?:^|[_-])v(?P<major>\d+)(?:[._-]|$)", re.IGNORECASE)


class TodoReader(Protocol):
    def get_todo(self, todo_id: str) -> TodoItem | None:
        """Return a Todo by id."""


class RuntimeConfigProvider(Protocol):
    def __call__(self) -> object:
        """Return the latest runtime config."""


@dataclass(frozen=True)
class KnowledgeArchivePaths:
    archive_root: Path
    issue_product: str
    major_version: str
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


def _wiki_index_filename(product_line: str) -> str:
    return f"{product_line} Wiki 索引.md"


def _ticket_type_for_archive(todo: TodoItem) -> str:
    summary = "\n".join(part for part in (todo.title, todo.current_summary) if str(part or "").strip())
    return normalize_ticket_type(todo.summary_fields.ticket_type, summary_text=summary)


def should_archive_todo(todo: TodoItem) -> bool:
    if str(todo.status or "").strip() != TodoStatus.DONE:
        return False
    return _ticket_type_for_archive(todo) != _OPERATION_TICKET_TYPE


def _archive_title(todo: TodoItem) -> str:
    return _clean_text(todo.title, fallback="未分类任务")


def _build_note_stem(todo: TodoItem) -> str:
    return _safe_segment(_archive_title(todo), fallback="未分类任务")


def _archive_issue_product(todo: TodoItem) -> str:
    issue_product = _archive_issue_product_from_value(todo.summary_fields.issue_product)
    return issue_product or _PATH_PLACEHOLDER


def _archive_issue_product_segments(todo: TodoItem) -> list[str]:
    issue_product = _archive_issue_product(todo)
    segments = [_safe_segment(part) for part in issue_product.split("/") if str(part or "").strip()]
    return segments or [_PATH_PLACEHOLDER]


def _archive_issue_product_label(todo: TodoItem) -> str:
    issue_product = _archive_issue_product(todo)
    return _safe_segment(issue_product.replace("/", " - "))


def _archive_issue_product_from_value(value: object) -> str:
    issue_product = normalize_issue_product_path(value)
    if not issue_product:
        return ""
    segments = [segment for segment in issue_product.split("/") if segment]
    if len(segments) > 1 and re.fullmatch(r"V\d+", segments[-1], re.IGNORECASE):
        segments = segments[:-1]
    return "/".join(segments)


def _archive_major_version(raw_version: object) -> str:
    version_text = sanitize_text(raw_version).strip()
    match = _MAJOR_VERSION_RE.search(version_text)
    if match is not None:
        return f"V{match.group('major')}"
    return _DEFAULT_MAJOR_VERSION


def build_knowledge_archive_paths(archive_root: Path, todo: TodoItem) -> KnowledgeArchivePaths:
    issue_product_segments = _archive_issue_product_segments(todo)
    issue_product_label = _archive_issue_product_label(todo)
    major_version = _archive_major_version(todo.summary_fields.ticket_version)
    version = _safe_segment(todo.summary_fields.ticket_version)
    ticket_type = _safe_segment(_ticket_type_for_archive(todo), fallback="未分类")
    note_dir = archive_root.joinpath(*issue_product_segments, major_version, version, ticket_type)
    note_path = note_dir / f"{_build_note_stem(todo)}.md"
    wiki_index_path = archive_root.joinpath(
        *issue_product_segments,
        major_version,
        _WIKI_DIRNAME,
        _wiki_index_filename(issue_product_label),
    )
    return KnowledgeArchivePaths(
        archive_root=archive_root,
        issue_product=issue_product_label,
        major_version=major_version,
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
        "current_summary_attachments": [
            {
                "id": attachment.id,
                "name": attachment.name,
                "path": attachment.path,
                "sizeBytes": attachment.size_bytes,
                "kind": _attachment_kind(attachment.name),
            }
            for attachment in todo.current_summary_attachments
        ],
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


def _format_archive_timestamp(value: object) -> str:
    text = sanitize_text(value).strip()
    if not text:
        return _UNKNOWN_TEXT
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return text.replace("T", " ")
    return parsed.strftime("%Y-%m-%d %H:%M")


def _markdown_escape_cell(value: object, *, fallback: str = _TEXT_PLACEHOLDER) -> str:
    return _clean_text(value, fallback=fallback).replace("|", "\\|").replace("\n", "<br>")


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
        f"项目名: {_clean_text(project_snapshot.get('project_name'))}",
        f"项目编号: {_clean_text(project_snapshot.get('task_order_no'))}",
        f"项目客户: {_clean_text(project_snapshot.get('customer_name'))}",
        f"项目经理: {_clean_text(project_snapshot.get('project_manager'))}",
        f"根因分类: {_clean_text(summary_fields.get('root_cause'))}",
        f"根因说明: {_clean_text(summary_fields.get('root_cause_desc'))}",
        f"当前摘要: {_clean_text(todo_payload.get('current_summary'))}",
        f"当前描述附件: {_clean_text('、'.join(str(item.get('name') or '').strip() for item in list(todo_payload.get('current_summary_attachments') or []) if isinstance(item, dict)), fallback='无')}",
        f"问题结论: {_clean_text(dict(todo_payload.get('conclusion', {}) or {}).get('content'), fallback='暂无明确结论')}",
    ]


def build_knowledge_archive_messages(todo_payload: dict[str, object]) -> list[Message]:
    timeline_lines: list[str] = []
    timeline_items = todo_payload.get("timeline", [])
    if isinstance(timeline_items, list):
        for item in timeline_items:
            if not isinstance(item, dict):
                continue
            timestamp = _format_archive_timestamp(item.get("timestamp"))
            scenario = _clean_text(item.get("scenario"), fallback="系统记录")
            content = _clean_optional_text(item.get("content"))
            attachments = item.get("attachments", [])
            attachment_names: list[str] = []
            if isinstance(attachments, list):
                for attachment in attachments:
                    if isinstance(attachment, dict):
                        name = _clean_optional_text(attachment.get("name"))
                        if name:
                            attachment_names.append(name)
            attachment_text = f"；附件：{'、'.join(attachment_names)}" if attachment_names else ""
            if content:
                timeline_lines.append(f"- [{timestamp}] {scenario}: {content}{attachment_text}")
    metadata_text = "\n".join(_build_archive_metadata_lines(todo_payload))
    timeline_text = "\n".join(timeline_lines) or "- 暂无有效排查记录"
    user_prompt = (
        "请基于以下工单信息，整理成适合本地知识库归档的 Markdown 解决方案文档。\n"
        "只输出 Markdown 正文，不要解释，不要输出代码块围栏。\n\n"
        "写作目标：\n"
        "1. 文档用于后续遇到类似问题时检索、定位和复用解决思路，不是工单流水账。\n"
        "2. 重点沉淀问题现象、关键错误、定位过程、解决方案、最终结论。\n"
        "3. 不要写当前状态、影响范围、原始时间线、聊天过程、群聊名称或泛化管理动作。\n"
        "4. 不要输出“时间线回顾”“时间线图示”“附件图示”“关联证据”章节；关联证据会由程序统一追加。\n"
        "5. 没有提供的信息统一写“未提供”“未明确”或“待确认”，不要猜测。\n"
        "6. 不要把“问题恢复”本身写成解决方案，除非存在明确处理动作。\n\n"
        "7. 结论和排查记录中的链接、参考文档、错误码、索引名、配置名、接口名等关键信息必须原样保留，并写入解决方案或最终结论，不要只做概括。\n\n"
        "固定结构（不要输出一级标题，正文从二级标题开始）：\n"
        "## 问题概览\n\n"
        "- 问题现象：...\n"
        "- 关键错误：...\n"
        "- 涉及模块：...\n"
        "- 最终结论：...\n"
        "## 基本信息\n\n"
        "- 用表格记录：产品线、版本号、功能点、项目名、工单类型、根因分类。\n"
        "## 问题现象\n\n"
        "## 定位过程\n\n"
        "## 解决方案\n\n"
        "## 最终结论\n\n"
        f"元数据:\n{metadata_text}\n\n"
        f"排查记录:\n{timeline_text}"
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
        f"| 产品线 | {_markdown_escape_cell(summary_fields.get('product_line'))} |",
        f"| 版本号 | {_markdown_escape_cell(summary_fields.get('ticket_version'))} |",
        f"| 功能点 | {_markdown_escape_cell(summary_fields.get('feature_point'), fallback=_UNSPECIFIED_FEATURE)} |",
        f"| 项目名 | {_markdown_escape_cell(project_snapshot.get('project_name'))} |",
        f"| 工单类型 | {_markdown_escape_cell(ticket_type, fallback='未分类')} |",
        f"| 根因分类 | {_markdown_escape_cell(summary_fields.get('root_cause'))} |",
    ]


def _build_archive_fallback_markdown(todo_payload: dict[str, object]) -> str:
    conclusion_content = _clean_text(
        dict(todo_payload.get("conclusion", {}) or {}).get("content"),
        fallback="暂无明确结论",
    )
    summary = _clean_text(todo_payload.get("current_summary"))
    metadata_block = "\n".join(_metadata_table_lines(todo_payload))
    return (
        "## 问题概览\n\n"
        f"- 问题现象：{summary}\n"
        "- 关键错误：未明确\n"
        "- 涉及模块：未明确\n"
        f"- 最终结论：{conclusion_content}\n\n"
        "## 基本信息\n\n"
        f"{metadata_block}\n\n"
        "## 问题现象\n\n"
        f"{summary}\n\n"
        "## 定位过程\n\n"
        "- 根据工单记录中的错误现象、关键错误和附件证据进行定位；如信息不足，需结合复现时间和相关服务日志继续确认。\n\n"
        "## 解决方案\n\n"
        "- 后续遇到相似问题时，优先根据标题、功能点、错误现象、错误码和关键日志进行检索。\n"
        "- 若当前记录未包含明确处理动作，应补充复现条件、请求时间、接口返回和相关服务日志后再定位。\n\n"
        "## 最终结论\n\n"
        f"{conclusion_content}"
    ).strip()


def _strip_archive_body_title(markdown: str) -> str:
    normalized = str(markdown or "").strip()
    if not normalized:
        return ""
    return re.sub(r"^#\s+.*(?:\r?\n)+", "", normalized, count=1).strip()


def _ensure_archive_heading_spacing(markdown: str) -> str:
    lines = str(markdown or "").strip().splitlines()
    if not lines:
        return ""
    output: list[str] = []
    for index, line in enumerate(lines):
        output.append(line)
        if re.match(r"^##\s+\S", line):
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if next_line.strip():
                output.append("")
    return "\n".join(output).strip()


def _normalize_archive_body(markdown: str) -> str:
    return _ensure_archive_heading_spacing(_strip_archive_body_title(markdown))


def _has_archive_required_sections(markdown: str) -> bool:
    normalized = str(markdown or "")
    required = ("问题概览", "基本信息", "问题现象", "定位过程", "解决方案", "最终结论")
    return all(re.search(rf"^##\s+{re.escape(title)}\s*$", normalized, re.MULTILINE) for title in required)


def _strip_archive_generated_sections(markdown: str) -> str:
    normalized = str(markdown or "").strip()
    if not normalized:
        return ""
    forbidden = ("时间线回顾", "时间线图示", "附件图示", "关联证据")
    heading_re = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading_re.finditer(normalized))
    if not matches:
        return normalized
    chunks: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        title = match.group(1).strip()
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        if any(title == item or title.startswith(item) for item in forbidden):
            chunks.append(normalized[cursor:match.start()])
            cursor = next_start
    chunks.append(normalized[cursor:])
    return "\n\n".join(part.strip() for part in chunks if part.strip()).strip()


def _extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip("。.,，；;：:)）]")
        if url and url not in urls:
            urls.append(url)
    return urls


def _collect_key_reference_lines(todo_payload: dict[str, object]) -> list[tuple[str, list[str]]]:
    references: list[tuple[str, list[str]]] = []
    seen_urls: set[str] = set()

    def add_reference(label: str, content: object) -> None:
        text = _clean_optional_text(content)
        if not text:
            return
        urls = [url for url in _extract_urls(text) if url not in seen_urls]
        if not urls:
            return
        seen_urls.update(urls)
        references.append((f"{label}：{text}", urls))

    conclusion = dict(todo_payload.get("conclusion", {}) or {})
    add_reference("问题结论", conclusion.get("content"))

    timeline_items = todo_payload.get("timeline", [])
    if isinstance(timeline_items, list):
        for item in timeline_items:
            if not isinstance(item, dict):
                continue
            timestamp = _format_archive_timestamp(item.get("timestamp"))
            scenario = _clean_text(item.get("scenario"), fallback="工单记录")
            add_reference(f"{timestamp} {scenario}", item.get("content"))

    return references


def _ensure_key_references_in_solution(markdown: str, todo_payload: dict[str, object]) -> str:
    references = [
        line
        for line, urls in _collect_key_reference_lines(todo_payload)
        if any(url not in markdown for url in urls)
    ]
    if not references:
        return markdown

    block = "\n\n### 关键参考信息\n\n" + "\n".join(f"- {line}" for line in references)
    solution_heading = re.search(r"^##\s+解决方案\s*$", markdown, re.MULTILINE)
    if solution_heading is None:
        return f"{markdown.rstrip()}{block}"

    next_heading = re.search(r"^##\s+\S.*$", markdown[solution_heading.end():], re.MULTILINE)
    insert_at = len(markdown) if next_heading is None else solution_heading.end() + next_heading.start()
    return f"{markdown[:insert_at].rstrip()}{block}\n\n{markdown[insert_at:].lstrip()}".strip()


def _copy_archive_attachment(source_path: str, asset_dir: Path) -> Path | None:
    source = Path(str(source_path or "")).expanduser()
    if not source.is_file():
        return None
    asset_dir.mkdir(parents=True, exist_ok=True)
    target = asset_dir / source.name
    if target.exists():
        try:
            if target.is_file() and filecmp.cmp(source, target, shallow=False):
                return target
        except OSError:
            pass
    counter = 1
    while target.exists():
        target = asset_dir / f"{source.stem}_{counter}{source.suffix}"
        if target.exists():
            try:
                if target.is_file() and filecmp.cmp(source, target, shallow=False):
                    return target
            except OSError:
                pass
        counter += 1
    shutil.copy2(source, target)
    return target


def _iter_archive_evidence_entries(todo_payload: dict[str, object]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen_keys: set[str] = set()

    def _add_entries(container: dict[str, object], *, default_scenario: str, default_timestamp: object = "") -> None:
        attachments = container.get("attachments", [])
        if not isinstance(attachments, list):
            return
        timestamp = _format_archive_timestamp(container.get("timestamp") or container.get("updatedAt") or default_timestamp)
        scenario = _clean_text(container.get("scenario"), fallback=default_scenario)
        content = _clean_optional_text(container.get("content"))
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            name = _clean_optional_text(attachment.get("name"))
            path = _clean_optional_text(attachment.get("path"))
            kind = _clean_optional_text(attachment.get("kind")) or _attachment_kind(name)
            if not name or not path:
                continue
            key = str(Path(path).expanduser()).lower()
            if key in seen_keys:
                continue
            seen_keys.add(key)
            entries.append(
                {
                    "timestamp": timestamp,
                    "scenario": scenario,
                    "content": content,
                    "name": name,
                    "path": path,
                    "kind": kind,
                }
            )

    timeline = todo_payload.get("timeline", [])
    if isinstance(timeline, list):
        for item in timeline:
            if isinstance(item, dict):
                _add_entries(item, default_scenario="工单记录")
    conclusion = todo_payload.get("conclusion", {})
    if isinstance(conclusion, dict):
        _add_entries(conclusion, default_scenario="问题结论")
    return entries


def _render_evidence_attachment(entry: dict[str, str], relative_path: str) -> str:
    name = entry.get("name", "附件")
    if entry.get("kind") == "image":
        return f"![{name}]({relative_path})"
    return f"[{name}]({relative_path})"


def append_archive_evidence_section(markdown: str, todo_payload: dict[str, object], note_path: Path) -> str:
    entries = _iter_archive_evidence_entries(todo_payload)
    if not entries:
        return _strip_archive_generated_sections(markdown)
    asset_dir = note_path.parent / "assets"
    lines = ["## 关联证据", ""]
    evidence_index = 1
    for entry in entries:
        copied = _copy_archive_attachment(entry.get("path", ""), asset_dir)
        if copied is None:
            continue
        relative_path = copied.relative_to(note_path.parent).as_posix()
        scenario = _clean_text(entry.get("scenario"), fallback="证据材料")
        lines.append(f"### 证据 {evidence_index}：{scenario}")
        lines.append("")
        lines.append(f"- 时间：{_clean_text(entry.get('timestamp'))}")
        lines.append(f"- 来源：{scenario}")
        if entry.get("content"):
            lines.append(f"- 说明：{_clean_text(entry.get('content'))}")
        lines.append("")
        lines.append(_render_evidence_attachment(entry, relative_path))
        lines.append("")
        evidence_index += 1
    if evidence_index == 1:
        return _strip_archive_generated_sections(markdown)
    normalized = _strip_archive_generated_sections(markdown)
    evidence_markdown = "\n".join(lines).strip()
    return f"{normalized}\n\n{evidence_markdown}".strip()


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
        f"title: {_yaml_scalar(_archive_title(todo), fallback='未分类任务')}",
        f"product_line: {_yaml_scalar(todo.summary_fields.product_line)}",
        f"issue_product: {_yaml_scalar(_archive_issue_product(todo), fallback=_PATH_PLACEHOLDER)}",
        f"ticket_version: {_yaml_scalar(todo.summary_fields.ticket_version)}",
        f"ticket_type: {_yaml_scalar(_ticket_type_for_archive(todo), fallback='未分类')}",
        f"feature_point: {_yaml_scalar(todo.summary_fields.feature_point, fallback=_UNSPECIFIED_FEATURE)}",
        f"root_cause: {_yaml_scalar(todo.summary_fields.root_cause)}",
        f"root_cause_desc: {_yaml_scalar(todo.summary_fields.root_cause_desc)}",
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
            normalized = normalize_markdown_content(str(raw_markdown or ""))
            if normalized and _has_archive_required_sections(normalized):
                return _normalize_archive_body(normalized)
        except Exception as exc:  # noqa: BLE001
            _append_archive_log(f"LLM archive generation failed for todo {todo_payload.get('id', '')}: {exc}")
    return _normalize_archive_body(_build_archive_fallback_markdown(todo_payload))


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
    body = _ensure_key_references_in_solution(body, todo_payload)
    paths.note_path.parent.mkdir(parents=True, exist_ok=True)
    body = append_archive_evidence_section(body, todo_payload, paths.note_path)
    markdown = f"{build_knowledge_frontmatter(todo)}\n\n{body.strip()}\n"
    paths.note_path.write_text(markdown, encoding="utf-8")
    rebuild_issue_product_wiki_index(
        root,
        todo.summary_fields.issue_product,
        _archive_major_version(todo.summary_fields.ticket_version),
    )
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


def rebuild_issue_product_wiki_index(archive_root: Path, issue_product: str, major_version: str = _DEFAULT_MAJOR_VERSION) -> Path:
    issue_product_dir = Path(archive_root)
    normalized_issue_product = _archive_issue_product_from_value(issue_product)
    if normalized_issue_product:
        for part in normalized_issue_product.split("/"):
            segment = _safe_segment(part)
            if segment:
                issue_product_dir = issue_product_dir / segment
    else:
        issue_product_dir = issue_product_dir / _PATH_PLACEHOLDER
    issue_product_dir = issue_product_dir / _safe_segment(major_version, fallback=_DEFAULT_MAJOR_VERSION)
    wiki_dir = issue_product_dir / _WIKI_DIRNAME
    wiki_dir.mkdir(parents=True, exist_ok=True)
    note_files = [
        path
        for path in issue_product_dir.rglob("*.md")
        if _WIKI_DIRNAME not in path.parts
    ]
    entries: dict[str, dict[str, list[Path]]] = {}
    for path in note_files:
        version = path.parent.parent.name
        ticket_type = path.parent.name
        entries.setdefault(version, {}).setdefault(ticket_type, []).append(path)

    lines = [
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
    index_path = wiki_dir / _wiki_index_filename(_archive_issue_product_label_from_value(issue_product))
    index_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return index_path


def _archive_issue_product_label_from_value(value: object) -> str:
    issue_product = _archive_issue_product_from_value(value)
    if issue_product:
        return _safe_segment(issue_product.replace("/", " - "))
    return _safe_segment(value)


def rebuild_product_line_wiki_index(
    archive_root: Path,
    product_line: str,
    major_version: str = _DEFAULT_MAJOR_VERSION,
) -> Path:
    return rebuild_issue_product_wiki_index(archive_root, product_line, major_version)


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

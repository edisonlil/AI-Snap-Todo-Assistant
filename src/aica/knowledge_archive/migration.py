"""Legacy knowledge archive migration helpers."""
from __future__ import annotations

import filecmp
import json
import sqlite3
import re
import shutil
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..models import normalize_issue_product_path
from ..paths import knowledge_base_dir
from ..text_sanitize import sanitize_text
from .service import (
    _archive_major_version,
    archive_completed_todo,
    rebuild_issue_product_wiki_index,
    rebuild_product_line_wiki_index,
)
from ..todo.models import TodoItem, TodoStatus

_TARGET_VERSION = "V7"
_WIKI_DIRNAME = "_wiki"
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.S)
_DOCUMENT_MIDDLE_KEYWORDS = ("文档中台",)
_DOCUMENT_CENTER_KEYWORDS = ("文档中心", "云文档", "应用文档", "私有云文档")
_WPS_COLLAB_ROOT = "WPS协作（泛）/协作-私网"
_WPS_COLLAB_PRODUCT_LINES = {
    "私网WPS协作",
    "WPS协作",
    "WPS协作（PC_Web端）",
    "WPS协作（PC/Web端）",
}
_WPS_COLLAB_TITLE_KEYWORDS = ("WPS协作", "公文", "会议按钮", "统一身份认证平台", "金山工作台")
_NON_ARCHIVE_TOP_LEVELS = {"skills", ".workbuddy"}
_V7_SEGMENT_RE = re.compile(r"^V\d+$", re.IGNORECASE)


@dataclass(frozen=True)
class MigrationRecord:
    source_path: Path
    target_path: Path | None
    target_root: str
    reason: str
    moved: bool


@dataclass(frozen=True)
class MigrationResult:
    archive_root: Path
    migrated: tuple[MigrationRecord, ...] = field(default_factory=tuple)
    skipped: tuple[MigrationRecord, ...] = field(default_factory=tuple)

    @property
    def migrated_count(self) -> int:
        return sum(1 for item in self.migrated if item.moved)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def migrate_legacy_knowledge_archive(archive_root: Path | None = None) -> MigrationResult:
    root = Path(archive_root or knowledge_base_dir()).expanduser()
    note_files = [
        path
        for path in root.rglob("*.md")
        if path.name != "AGENTS.md"
        and _WIKI_DIRNAME not in path.parts
        and not _is_already_migrated(path, root)
        and _is_archive_note(path, root)
    ]
    migrated: list[MigrationRecord] = []
    skipped: list[MigrationRecord] = []
    copied_assets: set[tuple[Path, Path]] = set()
    touched_roots: set[tuple[str, str]] = set()
    source_parents: set[Path] = set()

    for source_path in sorted(note_files):
        source_parents.add(source_path.parent)
        frontmatter = _parse_frontmatter(source_path)
        enriched_todo, enriched_reason = _lookup_todo_for_note(root, frontmatter)
        if enriched_todo is not None:
            target_root, reason = _infer_target_root_from_todo(enriched_todo, source_path)
        else:
            target_root, reason = _infer_target_root(source_path, frontmatter)
        if not target_root:
            skipped.append(
                MigrationRecord(
                    source_path=source_path,
                    target_path=None,
                    target_root="",
                    reason=reason if enriched_todo is None else f"{reason}; {enriched_reason}",
                    moved=False,
                )
            )
            continue

        if enriched_todo is not None:
            ticket_type = _ticket_type_from_todo(enriched_todo, source_path)
            major_version = _archive_major_version(enriched_todo.summary_fields.ticket_version)
            small_version = _small_version_from_todo(enriched_todo, source_path)
            archive_todo = _prepare_todo_for_archive(enriched_todo, target_root)
            destination_path = _archive_todo_with_move(
                archive_todo,
                root=root,
                source_path=source_path,
                target_root=target_root,
                ticket_type=ticket_type,
                major_version=major_version,
                small_version=small_version,
                copied_assets=copied_assets,
            )
            if destination_path is None:
                skipped.append(
                    MigrationRecord(
                        source_path=source_path,
                        target_path=None,
                        target_root=target_root,
                        reason="destination collision unresolved",
                        moved=False,
                    )
                )
                continue
            migrated.append(
                MigrationRecord(
                    source_path=source_path,
                    target_path=destination_path,
                    target_root=target_root,
                    reason=f"{reason}; {enriched_reason}; major={major_version}; version={small_version}",
                    moved=True,
                )
            )
            touched_roots.add((target_root, major_version))
            continue

        ticket_type = _ticket_type(frontmatter, source_path)
        major_version = _major_version(frontmatter)
        small_version = _small_version(frontmatter, source_path)
        target_dir = root / target_root / major_version / small_version / ticket_type
        target_dir.mkdir(parents=True, exist_ok=True)
        destination_path = _resolve_destination_path(source_path, target_dir)
        if destination_path is None:
            skipped.append(
                MigrationRecord(
                    source_path=source_path,
                    target_path=None,
                    target_root=target_root,
                    reason="destination collision unresolved",
                    moved=False,
                )
            )
            continue

        source_text = source_path.read_text(encoding="utf-8")
        migrated_text = _ensure_issue_product_frontmatter(source_text, target_root)
        if destination_path.exists():
            if _files_equal_text(destination_path, migrated_text):
                source_path.unlink()
            else:
                destination_path.write_text(migrated_text, encoding="utf-8")
                source_path.unlink()
        else:
            destination_path.write_text(migrated_text, encoding="utf-8")
            source_path.unlink()
        _copy_assets(source_path.parent, target_dir, copied_assets)
        migrated.append(
            MigrationRecord(
                source_path=source_path,
                target_path=destination_path,
                target_root=target_root,
                reason=f"{reason}; major={major_version}; version={small_version}",
                moved=True,
            )
        )
        touched_roots.add((target_root, major_version))

    _cleanup_empty_source_dirs(source_parents, root)
    _cleanup_orphan_legacy_roots(root)

    for target_root, major_version in sorted(touched_roots):
        rebuild_issue_product_wiki_index(root, target_root, major_version)

    for legacy_root in sorted(_discover_remaining_legacy_roots(root)):
        rebuild_product_line_wiki_index(root, legacy_root)

    return MigrationResult(
        archive_root=root,
        migrated=tuple(migrated),
        skipped=tuple(skipped),
    )


def _archive_issue_product_root(value: object) -> str:
    issue_product = normalize_issue_product_path(value)
    if not issue_product:
        return ""
    segments = [segment for segment in issue_product.split("/") if segment]
    if len(segments) > 1 and _V7_SEGMENT_RE.fullmatch(segments[-1]):
        segments = segments[:-1]
    return "/".join(segments)


def _copy_source_assets(source_path: Path, target_dir: Path, copied_assets: set[tuple[Path, Path]]) -> None:
    _copy_assets(source_path.parent, target_dir, copied_assets)


def _archive_todo_with_move(
    todo: TodoItem,
    *,
    root: Path,
    source_path: Path,
    target_root: str,
    ticket_type: str,
    major_version: str,
    small_version: str,
    copied_assets: set[tuple[Path, Path]],
) -> Path | None:
    target_dir = root / target_root / major_version / small_version / ticket_type
    target_dir.mkdir(parents=True, exist_ok=True)
    note_path = target_dir / source_path.name
    if note_path.exists():
        try:
            if note_path.is_file() and filecmp.cmp(source_path, note_path, shallow=False):
                source_path.unlink()
                _copy_source_assets(source_path, target_dir, copied_assets)
                return note_path
        except OSError:
            pass
    archived_path = archive_completed_todo(todo, archive_root=root)
    if archived_path is None:
        return None
    if archived_path != note_path:
        if note_path.exists():
            try:
                if note_path.is_file() and filecmp.cmp(archived_path, note_path, shallow=False):
                    source_path.unlink()
                    _copy_source_assets(source_path, target_dir, copied_assets)
                    return note_path
            except OSError:
                pass
        if note_path.exists():
            note_path.unlink()
        archived_path.replace(note_path)
    source_path.unlink()
    _copy_source_assets(source_path, target_dir, copied_assets)
    return note_path


def _prepare_todo_for_archive(todo: TodoItem, target_root: str) -> TodoItem:
    summary_fields = replace(todo.summary_fields)
    issue_product = _archive_issue_product_root(summary_fields.issue_product) or target_root
    summary_fields.issue_product = issue_product
    return TodoItem(
        id=todo.id,
        title=todo.title,
        summary_fields=summary_fields,
        current_summary=todo.current_summary,
        current_summary_attachments=list(todo.current_summary_attachments),
        created_at=todo.created_at,
        updated_at=todo.updated_at,
        completed_at=todo.completed_at or todo.updated_at,
        status=TodoStatus.DONE,
        timeline=list(todo.timeline),
        conclusion=todo.conclusion,
        project_link=todo.project_link,
    )


def _ticket_type_from_todo(todo: TodoItem, source_path: Path) -> str:
    value = sanitize_text(todo.summary_fields.ticket_type).strip()
    if value:
        return value
    return source_path.parent.name or "未分类"


def _small_version_from_todo(todo: TodoItem, source_path: Path) -> str:
    version = sanitize_text(todo.summary_fields.ticket_version).strip()
    if version:
        return version
    return _small_version({}, source_path)


def _infer_target_root_from_todo(todo: TodoItem, source_path: Path) -> tuple[str, str]:
    issue_product = _archive_issue_product_root(todo.summary_fields.issue_product)
    feature_point = sanitize_text(todo.summary_fields.feature_point).strip()
    product_line = sanitize_text(todo.summary_fields.product_line).strip()
    title = sanitize_text(todo.title).strip() or sanitize_text(source_path.stem).strip()

    target, _ = _target_from_text(issue_product)
    if target:
        return target, f"issue_product={issue_product or '未提供'}"

    target, _ = _target_from_text(feature_point)
    if target:
        return target, f"feature_point={feature_point or '未提供'}"

    if product_line in _WPS_COLLAB_PRODUCT_LINES:
        return _WPS_COLLAB_ROOT, f"legacy product_line={product_line}"
    if feature_point.startswith("WPS协作（泛）"):
        return _WPS_COLLAB_ROOT, f"feature_point={feature_point}"
    if product_line == "未提供" and title and any(keyword in title for keyword in _WPS_COLLAB_TITLE_KEYWORDS):
        return _WPS_COLLAB_ROOT, f"title={title}"

    if product_line == "私网文档中台":
        return "文档中台", "legacy product_line=私网文档中台"
    if product_line == "私有云文档":
        return "文档中心", "legacy product_line=私有云文档"

    return "", f"unmapped todo: {todo.id}"


def _lookup_todo_for_note(archive_root: Path, frontmatter: dict[str, str]) -> tuple[TodoItem | None, str]:
    todo_id = sanitize_text(frontmatter.get("todo_id", "")).strip()
    title = sanitize_text(frontmatter.get("title", "")).strip()
    db_path = archive_root.parent / "aica.db"
    if not db_path.exists():
        return None, "local todo database unavailable"
    try:
        with sqlite3.connect(db_path) as connection:
            connection.row_factory = sqlite3.Row
            if todo_id:
                row = connection.execute("SELECT id FROM todos WHERE id = ?", (todo_id,)).fetchone()
                if row is not None:
                    from ..todo.store import TodoStore

                    todo = TodoStore(str(db_path)).get_todo(todo_id)
                    if todo is not None:
                        return todo, f"todo_id={todo_id}"
            if title:
                row = connection.execute(
                    """
                    SELECT id
                    FROM todos
                    WHERE title = ?
                    ORDER BY updated_at DESC, created_at DESC, id DESC
                    LIMIT 1
                    """,
                    (title,),
                ).fetchone()
                if row is not None:
                    from ..todo.store import TodoStore

                    todo = TodoStore(str(db_path)).get_todo(str(row["id"]))
                    if todo is not None:
                        return todo, f"title={title}"
    except (OSError, sqlite3.Error):
        return None, "local todo database unavailable"
    return None, "no matching todo found"


def _is_already_migrated(path: Path, archive_root: Path) -> bool:
    relative = path.relative_to(archive_root)
    if len(relative.parts) < 4:
        return False
    try:
        major_index = relative.parts.index(_TARGET_VERSION)
    except ValueError:
        return False
    if len(relative.parts) - major_index < 4:
        return False
    return relative.parts[major_index + 2] != _WIKI_DIRNAME


def _parse_frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        if value:
            try:
                parsed = json.loads(value)
            except Exception:
                parsed = value
            data[key.strip()] = str(parsed)
    return data


def _ticket_type(frontmatter: dict[str, str], source_path: Path) -> str:
    value = sanitize_text(frontmatter.get("ticket_type", "")).strip()
    if value:
        return value
    return source_path.parent.name or "未分类"


def _major_version(frontmatter: dict[str, str]) -> str:
    version = sanitize_text(frontmatter.get("ticket_version", "")).strip()
    return _archive_major_version(version or _TARGET_VERSION)


def _small_version(frontmatter: dict[str, str], source_path: Path) -> str:
    version = sanitize_text(frontmatter.get("ticket_version", "")).strip()
    if version:
        return version
    candidate = source_path.parent.parent.name
    if candidate in {"咨询类", "排查类", _TARGET_VERSION}:
        candidate = ""
    return sanitize_text(candidate).strip() or "未提供"


def _infer_target_root(source_path: Path, frontmatter: dict[str, str]) -> tuple[str, str]:
    title = sanitize_text(frontmatter.get("title", "")).strip() or sanitize_text(source_path.stem).strip()
    issue_product = sanitize_text(frontmatter.get("issue_product", "")).strip()
    feature_point = sanitize_text(frontmatter.get("feature_point", "")).strip()
    product_line = sanitize_text(frontmatter.get("product_line", "")).strip()

    target, reason = _target_from_text(issue_product)
    if target:
        return target, f"issue_product={issue_product or '未提供'}"

    target, reason = _target_from_text(feature_point)
    if target:
        return target, f"feature_point={feature_point or '未提供'}"

    if product_line in _WPS_COLLAB_PRODUCT_LINES:
        return _WPS_COLLAB_ROOT, f"legacy product_line={product_line}"
    if feature_point.startswith("WPS协作（泛）"):
        return _WPS_COLLAB_ROOT, f"feature_point={feature_point}"
    if product_line == "未提供" and title and any(keyword in title for keyword in _WPS_COLLAB_TITLE_KEYWORDS):
        return _WPS_COLLAB_ROOT, f"title={title}"

    if product_line == "私网文档中台":
        return "文档中台", "legacy product_line=私网文档中台"
    if product_line == "私有云文档":
        return "文档中心", "legacy product_line=私有云文档"

    return "", f"unmapped: {source_path.relative_to(source_path.parents[2])}"


def _target_from_text(text: str) -> tuple[str, str]:
    normalized = sanitize_text(text).strip()
    if not normalized:
        return "", ""
    if any(keyword in normalized for keyword in _DOCUMENT_MIDDLE_KEYWORDS):
        return "文档中台", normalized
    if any(keyword in normalized for keyword in _DOCUMENT_CENTER_KEYWORDS):
        return "文档中心", normalized
    return "", ""


def _ensure_issue_product_frontmatter(markdown: str, target_root: str) -> str:
    text = str(markdown or "")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return text
    frontmatter = match.group(1).splitlines()
    replacement = f'issue_product: {json.dumps(target_root, ensure_ascii=False)}'
    updated: list[str] = []
    inserted = False
    for line in frontmatter:
        if line.startswith("issue_product:"):
            updated.append(replacement)
            inserted = True
            continue
        updated.append(line)
        if not inserted and line.startswith("product_line:"):
            updated.append(replacement)
            inserted = True
    if not inserted:
        updated.append(replacement)
    return f"---\n{chr(10).join(updated)}\n---\n{text[match.end():].lstrip()}"


def _resolve_destination_path(source_path: Path, target_dir: Path) -> Path | None:
    candidate = target_dir / source_path.name
    if not candidate.exists():
        return candidate
    try:
        if candidate.is_file() and filecmp.cmp(source_path, candidate, shallow=False):
            return candidate
    except OSError:
        pass
    suffix = sanitize_text(source_path.parent.parent.name).replace("/", "_").replace("\\", "_") or "legacy"
    candidate = target_dir / f"{source_path.stem}__{suffix}{source_path.suffix}"
    if not candidate.exists():
        return candidate
    counter = 2
    while candidate.exists():
        try:
            if candidate.is_file() and filecmp.cmp(source_path, candidate, shallow=False):
                return candidate
        except OSError:
            pass
        candidate = target_dir / f"{source_path.stem}__{suffix}_{counter}{source_path.suffix}"
        counter += 1
        if counter > 999:
            return None
    return candidate


def _copy_assets(source_parent: Path, target_dir: Path, copied_assets: set[tuple[Path, Path]]) -> None:
    source_assets = source_parent / "assets"
    if not source_assets.is_dir():
        return
    cache_key = (source_assets.resolve(), target_dir.resolve())
    if cache_key in copied_assets:
        return
    copied_assets.add(cache_key)
    destination_assets = target_dir / "assets"
    destination_assets.mkdir(parents=True, exist_ok=True)
    for item in sorted(source_assets.rglob("*")):
        if item.is_dir():
            continue
        relative = item.relative_to(source_assets)
        target = destination_assets / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            try:
                if target.is_file() and filecmp.cmp(item, target, shallow=False):
                    continue
            except OSError:
                pass
            suffix = 1
            while target.exists():
                target = target.parent / f"{target.stem}_{suffix}{target.suffix}"
                suffix += 1
        shutil.copy2(item, target)


def _cleanup_empty_source_dirs(source_parents: set[Path], archive_root: Path) -> None:
    for parent in sorted(source_parents, key=lambda path: len(path.parts), reverse=True):
        if any(path for path in parent.rglob("*.md") if path.name != "AGENTS.md" and _WIKI_DIRNAME not in path.parts):
            continue
        wiki_dir = parent / _WIKI_DIRNAME
        assets_dir = parent / "assets"
        if wiki_dir.exists():
            shutil.rmtree(wiki_dir, ignore_errors=True)
        if assets_dir.exists():
            shutil.rmtree(assets_dir, ignore_errors=True)
        current = parent
        while current != archive_root and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def _cleanup_orphan_legacy_roots(archive_root: Path) -> None:
    for top_level in sorted(archive_root.iterdir(), key=lambda path: path.name):
        if not top_level.is_dir() or top_level.name.startswith(".") or top_level.name in _NON_ARCHIVE_TOP_LEVELS:
            continue
        has_notes = any(
            path
            for path in top_level.rglob("*.md")
            if path.name != "AGENTS.md" and _WIKI_DIRNAME not in path.parts
        )
        if has_notes:
            continue
        shutil.rmtree(top_level, ignore_errors=True)


def _discover_remaining_legacy_roots(archive_root: Path) -> set[str]:
    roots: set[str] = set()
    for path in archive_root.rglob("*.md"):
        if (
            path.name == "AGENTS.md"
            or _WIKI_DIRNAME in path.parts
            or _is_already_migrated(path, archive_root)
            or not _is_archive_note(path, archive_root)
        ):
            continue
        relative = path.relative_to(archive_root)
        if relative.parts:
            roots.add(relative.parts[0])
    return roots


def _files_equal_text(path: Path, text: str) -> bool:
    try:
        return path.read_text(encoding="utf-8") == text
    except OSError:
        return False


def _is_archive_note(path: Path, archive_root: Path) -> bool:
    try:
        relative = path.relative_to(archive_root)
    except ValueError:
        return False
    if not relative.parts:
        return False
    top_level = relative.parts[0]
    top_level_path = archive_root / top_level
    return top_level_path.is_dir() and not top_level.startswith(".") and top_level not in _NON_ARCHIVE_TOP_LEVELS

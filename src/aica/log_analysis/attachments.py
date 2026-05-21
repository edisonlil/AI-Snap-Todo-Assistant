"""Attachment handler registry and evidence collection for log analysis."""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from .models import CollectedEvidencePart, EvidenceBundle
from ..text_sanitize import sanitize_text
from ..todo.models import TimelineAttachment


_TEXT_LOG_SUFFIXES = {".log", ".txt", ".json", ".trace"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

_MAX_TEXT_BYTES = 128_000
_HEAD_LINE_BUDGET = 180
_TAIL_LINE_BUDGET = 120
_WINDOW_RADIUS = 2
_WINDOW_KEYWORDS = (
    "error",
    "exception",
    "traceback",
    "timeout",
    "failed",
    "denied",
    "forbidden",
    "requestid",
    "request_id",
    "traceid",
    "tradid",
    "errno",
    "http 4",
    "http 5",
    "403",
    "401",
)


@dataclass(frozen=True)
class AttachmentCollectContext:
    task_id: str


class AttachmentHandler(Protocol):
    def can_handle(self, attachment: TimelineAttachment) -> bool:
        ...

    def collect(self, attachment: TimelineAttachment, context: AttachmentCollectContext) -> list[CollectedEvidencePart]:
        ...


class AttachmentHandlerRegistry:
    def __init__(self, handlers: list[AttachmentHandler] | None = None) -> None:
        self._handlers = list(handlers or [])

    def register(self, handler: AttachmentHandler) -> None:
        self._handlers.append(handler)

    def resolve(self, attachment: TimelineAttachment) -> AttachmentHandler | None:
        return next((handler for handler in self._handlers if handler.can_handle(attachment)), None)

    def collect_bundle(self, attachments: list[TimelineAttachment], context: AttachmentCollectContext) -> EvidenceBundle:
        parts: list[CollectedEvidencePart] = []
        for attachment in attachments:
            handler = self.resolve(attachment)
            if handler is None:
                continue
            parts.extend(handler.collect(attachment, context))
        return EvidenceBundle(parts=parts, metadata={"attachment_count": len(attachments)})


class ZipAttachmentHandler:
    def can_handle(self, attachment: TimelineAttachment) -> bool:
        return Path(attachment.name or attachment.path).suffix.lower() == ".zip"

    def collect(self, attachment: TimelineAttachment, context: AttachmentCollectContext) -> list[CollectedEvidencePart]:
        source = Path(attachment.path).expanduser()
        if not source.is_file():
            return []
        parts: list[CollectedEvidencePart] = []
        with TemporaryDirectory(prefix=f"log-analysis-{context.task_id}-") as temp_dir:
            target_dir = Path(temp_dir)
            try:
                with zipfile.ZipFile(source) as archive:
                    archive.extractall(target_dir)
            except Exception as exc:  # noqa: BLE001
                return [
                    CollectedEvidencePart(
                        source_name=attachment.name,
                        source_type="zip",
                        summary="zip 解压失败",
                        details={"error": sanitize_text(str(exc))},
                    )
                ]
            extracted_files: list[str] = []
            for child in sorted(target_dir.rglob("*")):
                if not child.is_file() or child.suffix.lower() not in _TEXT_LOG_SUFFIXES:
                    continue
                extracted_files.append(str(child))
                parts.append(_build_text_part(child, source_type="zip_entry"))
                if len(extracted_files) >= 20:
                    break
            parts.insert(
                0,
                CollectedEvidencePart(
                    source_name=attachment.name,
                    source_type="zip",
                    summary=f"提取 {len(extracted_files)} 个日志文件",
                    details={"extracted_files": [Path(path).name for path in extracted_files]},
                ),
            )
        return parts


class TextLogAttachmentHandler:
    def can_handle(self, attachment: TimelineAttachment) -> bool:
        return Path(attachment.name or attachment.path).suffix.lower() in _TEXT_LOG_SUFFIXES

    def collect(self, attachment: TimelineAttachment, context: AttachmentCollectContext) -> list[CollectedEvidencePart]:
        source = Path(attachment.path).expanduser()
        if not source.is_file():
            return []
        return [_build_text_part(source, source_type="text_log")]


class ImageAttachmentHandler:
    def can_handle(self, attachment: TimelineAttachment) -> bool:
        return Path(attachment.name or attachment.path).suffix.lower() in _IMAGE_SUFFIXES

    def collect(self, attachment: TimelineAttachment, context: AttachmentCollectContext) -> list[CollectedEvidencePart]:
        source = Path(attachment.path).expanduser()
        if not source.is_file():
            return []
        return [
            CollectedEvidencePart(
                source_name=attachment.name or source.name,
                source_type="image",
                summary="图片证据",
                details={"path": str(source), "size_bytes": source.stat().st_size},
            )
        ]


def build_default_attachment_handler_registry() -> AttachmentHandlerRegistry:
    registry = AttachmentHandlerRegistry()
    registry.register(ZipAttachmentHandler())
    registry.register(TextLogAttachmentHandler())
    registry.register(ImageAttachmentHandler())
    return registry


def _build_text_part(path: Path, *, source_type: str) -> CollectedEvidencePart:
    text = _safe_read_text(path)
    lines = text.splitlines()
    excerpt, line_samples, truncated = _build_excerpt(lines)
    line_count = len(lines) if lines else (1 if text else 0)
    return CollectedEvidencePart(
        source_name=path.name,
        source_type=source_type,
        summary=f"读取 {path.name}",
        details={
            "path": str(path),
            "preview": excerpt[:4000],
            "text_excerpt": excerpt,
            "line_samples": line_samples,
            "line_count": line_count,
            "truncated": truncated,
        },
    )


def _build_excerpt(lines: list[str]) -> tuple[str, list[str], bool]:
    if not lines:
        return "", [], False
    if len(lines) <= _HEAD_LINE_BUDGET + _TAIL_LINE_BUDGET:
        text = "\n".join(lines)
        return text, list(lines), False

    selected_indexes: set[int] = set(range(min(len(lines), _HEAD_LINE_BUDGET)))
    selected_indexes.update(range(max(0, len(lines) - _TAIL_LINE_BUDGET), len(lines)))
    for index, line in enumerate(lines):
        lowered = sanitize_text(line).lower()
        if not lowered:
            continue
        if not any(keyword in lowered for keyword in _WINDOW_KEYWORDS):
            continue
        start = max(0, index - _WINDOW_RADIUS)
        end = min(len(lines), index + _WINDOW_RADIUS + 1)
        selected_indexes.update(range(start, end))

    ordered = sorted(selected_indexes)
    sampled_lines: list[str] = []
    excerpt_lines: list[str] = []
    previous_index = -2
    for index in ordered:
        if index - previous_index > 1 and excerpt_lines:
            excerpt_lines.append("... [truncated] ...")
        line = lines[index]
        sampled_lines.append(line)
        excerpt_lines.append(line)
        previous_index = index
    excerpt = "\n".join(excerpt_lines)[:24_000]
    return excerpt, sampled_lines[:2_400], True


def _safe_read_text(path: Path) -> str:
    try:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            return json.dumps(payload, ensure_ascii=False, indent=2)[:_MAX_TEXT_BYTES]
        return path.read_text(encoding="utf-8", errors="ignore")[:_MAX_TEXT_BYTES]
    except Exception:
        try:
            return path.read_text(encoding="gbk", errors="ignore")[:_MAX_TEXT_BYTES]
        except Exception:
            return ""

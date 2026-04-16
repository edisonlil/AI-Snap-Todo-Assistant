"""AI workers: screenshot analysis and feedback optimization."""
import base64
import json
import mimetypes
import os
import re
import shutil
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

_SKIP_QT_IMPORT = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

try:
    if _SKIP_QT_IMPORT:
        raise RuntimeError("Skip Qt import while running tests")
    from PyQt6.QtCore import QBuffer, QByteArray, QThread, pyqtSignal
    from PyQt6.QtGui import QPainter, QPixmap
except Exception:  # pragma: no cover - fallback for test environments without Qt runtime
    class QThread:  # type: ignore[no-redef]
        def __init__(self, parent=None):
            self._parent = parent

    def pyqtSignal(*_args, **_kwargs):  # type: ignore[no-redef]
        return None

    class QByteArray(bytearray):  # type: ignore[no-redef]
        pass

    class QBuffer:  # type: ignore[no-redef]
        class OpenModeFlag:
            WriteOnly = 0

        def __init__(self, byte_array):
            self._byte_array = byte_array

        def open(self, _mode):
            return True

        def close(self):
            return None

    class QPixmap:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self._width = 0
            self._height = 0

        def save(self, *_args, **_kwargs):
            return False

        def width(self):
            return self._width

        def height(self):
            return self._height

        def fill(self):
            return None

    class QPainter:  # type: ignore[no-redef]
        def __init__(self, *_args, **_kwargs):
            pass

        def drawPixmap(self, *_args, **_kwargs):
            return None

        def end(self):
            return None

from .analysis_rules import AnalysisRulesManager, PromptDebugStore
from .analysis_intent import AnalysisIntent, build_analysis_intent
from .analysis_metrics import AnalysisRunStats
from .analysis_strategy import AnalysisPromptBundle, build_analysis_prompt_bundle_from_rules
from .context_summary_models import ContextSummaryRequest
from .context_summary_service import ContextSummaryService, format_summary_for_analysis_context
from .image_utils import EncodedImage, encode_image_for_api
from .llm.service import LLMService, LLMServiceError, TaskExecutionError
from .llm.types import ContentPart, Message, TaskRunResult
from .parser import ResultParser

PLAN_EXPORT_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"
_PLAN_EXPORT_SYSTEM_PROMPT = (
    "你是一位资深的B端技术支持与实施专家，负责基于待办上下文输出可执行的处理方案。"
    "你的输出会直接保存为 Markdown 文档发给同事或客户，因此必须结构清晰、专业准确、可落地。"
)
_PLAN_EXPORT_MAX_IMAGE_ATTACHMENTS = 6


def _format_plan_export_attachment_text(attachments_payload: object) -> str:
    if not isinstance(attachments_payload, list):
        return ""

    attachment_lines: list[str] = []
    for index, item in enumerate(attachments_payload, 1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        kind = str(item.get("kind", "")).strip()
        size_bytes = item.get("sizeBytes", item.get("size_bytes", 0))
        try:
            normalized_size = max(0, int(size_bytes))
        except (TypeError, ValueError):
            normalized_size = 0
        size_label = f"{normalized_size}B" if normalized_size else ""
        detail_parts = [part for part in (kind, size_label) if part]
        detail_text = f"（{'，'.join(detail_parts)}）" if detail_parts else ""
        attachment_lines.append(f"{index}. {name}{detail_text}")
    return "；".join(attachment_lines)


def _iter_plan_export_attachment_entries(todo_payload: dict[str, object]) -> list[dict[str, str]]:
    timeline_payload = todo_payload.get("timeline", [])
    entries: list[dict[str, str]] = []
    if not isinstance(timeline_payload, list):
        return entries

    for item in timeline_payload:
        if not isinstance(item, dict):
            continue
        timestamp = str(item.get("timestamp", "")).strip() or "未知时间"
        scenario = str(item.get("scenario", "")).strip() or "系统记录"
        content = str(item.get("content", "")).strip()
        attachments = item.get("attachments", [])
        if not isinstance(attachments, list):
            continue
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            name = str(attachment.get("name", "")).strip()
            path = str(attachment.get("path", "")).strip()
            kind = str(attachment.get("kind", "")).strip()
            if not name:
                continue
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
    return entries


def _group_plan_export_attachment_entries(
    todo_payload: dict[str, object],
) -> list[dict[str, object]]:
    timeline_payload = todo_payload.get("timeline", [])
    grouped_entries: list[dict[str, object]] = []
    if not isinstance(timeline_payload, list):
        return grouped_entries

    for item in timeline_payload:
        if not isinstance(item, dict):
            continue
        attachments = item.get("attachments", [])
        if not isinstance(attachments, list) or not attachments:
            continue
        timestamp = str(item.get("timestamp", "")).strip() or "未知时间"
        scenario = str(item.get("scenario", "")).strip() or "系统记录"
        content = str(item.get("content", "")).strip()
        normalized_attachments: list[dict[str, str]] = []
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            name = str(attachment.get("name", "")).strip()
            path = str(attachment.get("path", "")).strip()
            kind = str(attachment.get("kind", "")).strip()
            if not name:
                continue
            normalized_attachments.append(
                {
                    "name": name,
                    "path": path,
                    "kind": kind,
                }
            )
        if not normalized_attachments:
            continue
        grouped_entries.append(
            {
                "timestamp": timestamp,
                "scenario": scenario,
                "content": content,
                "attachments": normalized_attachments,
            }
        )
    return grouped_entries


def _encode_local_image_to_data_url(path: str) -> str:
    source = Path(str(path or "")).expanduser()
    if not source.is_file():
        return ""
    mime_type, _ = mimetypes.guess_type(str(source))
    if not mime_type or not mime_type.startswith("image/"):
        return ""
    encoded = base64.b64encode(source.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _build_plan_export_timeline_lines(todo_payload: dict[str, object]) -> list[str]:
    timeline_payload = todo_payload.get("timeline", [])
    timeline_lines: list[str] = []
    if not isinstance(timeline_payload, list):
        return timeline_lines

    for index, item in enumerate(timeline_payload, 1):
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        timestamp = str(item.get("timestamp", "")).strip() or "未知时间"
        scenario = str(item.get("scenario", "")).strip() or "系统记录"
        line = f"{index}. [{timestamp}] {scenario}: {content}"
        attachment_text = _format_plan_export_attachment_text(item.get("attachments", []))
        if attachment_text:
            line = f"{line}\n   附件: {attachment_text}"
        timeline_lines.append(line)
    return timeline_lines


def build_plan_export_timeline_markdown(todo_payload: dict[str, object]) -> str:
    timeline_lines = _build_plan_export_timeline_lines(todo_payload)
    if not timeline_lines:
        return "## 时间线回顾\n\n- 暂无时间线记录"
    return "## 时间线回顾\n\n" + "\n".join(f"- {line}" for line in timeline_lines)


class _BaseVisionWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    parse_error = pyqtSignal(str)
    show_result = pyqtSignal(object, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis_stats: AnalysisRunStats | None = None
        self._prompt_bundle: AnalysisPromptBundle | None = None
        self._prompt_trace_id = ""
        self._prompt_version = "built-in"
        self._rules_manager = AnalysisRulesManager()
        self._prompt_debug_store = PromptDebugStore()

    def _pixmap_to_bytes(self, pixmap: QPixmap) -> bytes:
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        buffer.close()
        return bytes(byte_array)

    def _pixmap_to_base64(self, pixmap: QPixmap) -> str:
        img_bytes = self._pixmap_to_bytes(pixmap)
        return base64.b64encode(img_bytes).decode("utf-8")

    def _encode_for_api(self, pixmap: QPixmap, *, image_count: int) -> EncodedImage:
        img_bytes = self._pixmap_to_bytes(pixmap)
        return encode_image_for_api(
            img_bytes,
            image_count=image_count,
            max_image_bytes=getattr(self, "_max_image_bytes", 4 * 1024 * 1024),
        )

    def _build_combined_preview(self, pixmaps: list[QPixmap]) -> QPixmap:
        if not pixmaps:
            return QPixmap()

        width = max(pixmap.width() for pixmap in pixmaps)
        total_height = sum(pixmap.height() for pixmap in pixmaps)
        combined = QPixmap(width, total_height)
        combined.fill()

        painter = QPainter(combined)
        offset_y = 0
        for pixmap in pixmaps:
            painter.drawPixmap(0, offset_y, pixmap)
            offset_y += pixmap.height()
        painter.end()
        return combined

    def _run_llm_task(
        self,
        task_name: str,
        *,
        messages: list[Message],
        temperature: float,
        timeout: int | None = None,
    ) -> str:
        return self._llm_service.run_task(
            task_name,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
        )

    def _run_llm_task_detailed(
        self,
        task_name: str,
        *,
        messages: list[Message],
        temperature: float,
        timeout: int | None = None,
    ) -> TaskRunResult:
        return self._llm_service.run_task_detailed(
            task_name,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
        )

    @staticmethod
    def _build_analysis_stats(
        *,
        run_result: TaskRunResult,
        preprocess_ms: int,
        input_bytes: int,
        image_count: int,
        latency_ms: int,
    ) -> AnalysisRunStats:
        return AnalysisRunStats(
            provider_id=run_result.reference.provider_id,
            provider_name=run_result.reference.provider_name,
            model_id=run_result.reference.model_id,
            model_name=run_result.reference.model_name,
            latency_ms=latency_ms,
            llm_latency_ms=run_result.latency_ms,
            preprocess_ms=preprocess_ms,
            attempts=run_result.attempts,
            image_count=image_count,
            input_bytes=input_bytes,
        )

    @staticmethod
    def _build_prompt_trace_id() -> str:
        return f"{time.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _build_prompt_bundle(self, *, image_count: int) -> AnalysisPromptBundle:
        config = self._rules_manager.reload()
        bundle = build_analysis_prompt_bundle_from_rules(
            self._analysis_intent,
            rules_config=config,
            trace_id=self._build_prompt_trace_id(),
            context_text=self._context_text,
            image_count=image_count,
        )
        self._prompt_bundle = bundle
        self._prompt_trace_id = bundle.trace_id
        self._prompt_version = bundle.prompt_version
        return bundle

    def _resolve_context_text(self) -> str:
        context_request = getattr(self, "_context_request", None)
        if not isinstance(context_request, ContextSummaryRequest):
            return str(getattr(self, "_context_text", "") or "").strip()
        summary_service = getattr(self, "_context_summary_service", None)
        if not isinstance(summary_service, ContextSummaryService):
            return str(getattr(self, "_context_text", "") or "").strip()
        result = summary_service.summarize(context_request)
        return format_summary_for_analysis_context(context_request, result)

    def _record_prompt_trace(
        self,
        *,
        status: str,
        raw_response: str = "",
        error_message: str = "",
        image_payloads: list[EncodedImage],
    ) -> None:
        bundle = self._prompt_bundle
        config = self._rules_manager.config
        if bundle is None or not config.debug.enabled:
            return

        payload = {
            "trace_id": bundle.trace_id,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "model": self._model,
            "scenario": self._scenario,
            "scene_type": bundle.scene_type,
            "scene_label": bundle.scene_label,
            "prompt_version": bundle.prompt_version,
            "focus_hint": bundle.focus_hint,
            "context_text": bundle.context_text,
            "image_count": bundle.image_count,
            "system_prompt": bundle.system_prompt,
            "user_prompt": bundle.user_prompt,
            "applied_rule_snapshot": bundle.applied_rule_snapshot,
            "image_payloads": [
                {
                    "index": index,
                    "byte_size": image.byte_size,
                    "preprocess_ms": image.preprocess_ms,
                }
                for index, image in enumerate(image_payloads, 1)
            ],
            "raw_response": str(raw_response or ""),
            "error_message": str(error_message or ""),
            "timing_summary": self._analysis_stats.timing_summary if self._analysis_stats is not None else "",
            "analysis_stats": (
                {
                    "provider_id": self._analysis_stats.provider_id,
                    "provider_name": self._analysis_stats.provider_name,
                    "model_id": self._analysis_stats.model_id,
                    "model_name": self._analysis_stats.model_name,
                    "latency_ms": self._analysis_stats.latency_ms,
                    "llm_latency_ms": self._analysis_stats.llm_latency_ms,
                    "preprocess_ms": self._analysis_stats.preprocess_ms,
                    "attempts": self._analysis_stats.attempts,
                    "image_count": self._analysis_stats.image_count,
                    "input_bytes": self._analysis_stats.input_bytes,
                }
                if self._analysis_stats is not None
                else {}
            ),
        }
        self._prompt_debug_store.write_record(
            payload,
            max_records=config.debug.max_records,
        )


def build_plan_export_messages(todo_payload: dict[str, object]) -> list[Message]:
    summary_fields = todo_payload.get("summary_fields")
    if isinstance(summary_fields, dict):
        group_name = str(summary_fields.get("group_name", "")).strip()
        environment = str(summary_fields.get("environment", "")).strip()
        product_line = str(summary_fields.get("product_line", "")).strip()
        ticket_type = str(summary_fields.get("ticket_type", "")).strip()
    else:
        group_name = ""
        environment = ""
        product_line = ""
        ticket_type = ""

    timeline_lines = _build_plan_export_timeline_lines(todo_payload)
    timeline_text = "\n".join(timeline_lines) if timeline_lines else "暂无时间线记录"
    user_prompt = (
        "请基于以下待办信息，编写一份可直接导出的 Markdown 处理方案。\n"
        "只输出 Markdown 正文，不要解释，不要输出代码块围栏。\n"
        "要求：\n"
        "1. 文档包含标题，并尽量使用以下二级标题：问题概述、现状分析、处理方案、执行步骤、风险与注意事项、结论。\n"
        "2. 内容要结合待办现状和时间线，避免脱离上下文的空泛表述。\n"
        "3. 如果关键信息不足，要明确写出待确认项，不要编造事实。\n"
        "4. 方案偏向企业内部协作场景，兼顾排查、执行、沟通和交付。\n"
        "5. 使用简体中文，表达专业、可执行，适合保存归档。\n\n"
        "6. 必须包含“时间线回顾”或等价小节，并且每个时间线节点都要保留明确时间点，格式优先使用 `[YYYY-MM-DDTHH:MM:SS]`。\n"
        "7. 如果时间线里带有附件，要把附件内容纳入现状分析、处理方案或执行步骤，不要忽略附件提供的信息。\n\n"
        f"待办标题: {str(todo_payload.get('title', '')).strip()}\n"
        f"群聊名称: {group_name}\n"
        f"环境: {environment}\n"
        f"产品线: {product_line}\n"
        f"工单类型: {ticket_type}\n"
        f"当前摘要: {str(todo_payload.get('current_summary', '')).strip()}\n"
        f"时间线:\n{timeline_text}"
    )
    user_content: str | list[ContentPart] = user_prompt
    image_entries = [
        entry
        for entry in _iter_plan_export_attachment_entries(todo_payload)
        if entry.get("kind") == "image" and entry.get("path")
    ]
    image_content: list[ContentPart] = []
    for entry in image_entries[:_PLAN_EXPORT_MAX_IMAGE_ATTACHMENTS]:
        data_url = _encode_local_image_to_data_url(entry.get("path", ""))
        if not data_url:
            continue
        image_content.append(
            ContentPart(
                type="text",
                text=(
                    f"附件图片，时间节点 [{entry['timestamp']}]，"
                    f"场景 {entry['scenario']}，文件名 {entry['name']}。"
                    f"{(' 关联说明：' + entry['content']) if entry['content'] else ''}"
                ),
            )
        )
        image_content.append(ContentPart(type="image_data_url", data_url=data_url))

    if image_content:
        user_content = [ContentPart(type="text", text=user_prompt), *image_content]

    return [
        Message(role="system", content=_PLAN_EXPORT_SYSTEM_PROMPT),
        Message(role="user", content=user_content),
    ]


def normalize_markdown_content(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""

    md_match = re.search(r"```(?:markdown|md)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if md_match:
        raw = md_match.group(1).strip()

    return raw.strip()


def ensure_plan_export_timeline_section(markdown: str, todo_payload: dict[str, object]) -> str:
    normalized = str(markdown or "").strip()
    timeline_markdown = build_plan_export_timeline_markdown(todo_payload).strip()
    if not normalized:
        return timeline_markdown

    if re.search(r"^##\s*时间线回顾\s*$", normalized, re.MULTILINE):
        return normalized

    return f"{normalized}\n\n{timeline_markdown}".strip()


def _copy_plan_export_attachment(path: str, asset_dir: Path) -> Path | None:
    source = Path(str(path or "")).expanduser()
    if not source.is_file():
        return None
    asset_dir.mkdir(parents=True, exist_ok=True)
    target = asset_dir / source.name
    counter = 1
    while target.exists():
        target = asset_dir / f"{source.stem}_{counter}{source.suffix}"
        counter += 1
    shutil.copy2(source, target)
    return target


def _build_plan_export_attachment_markdown_item(entry: dict[str, str], relative_path: str) -> str:
    if entry.get("kind") == "image":
        return f"![{entry['name']}]({relative_path})"
    if entry.get("kind") == "video":
        return f"- 视频附件: [{entry['name']}]({relative_path})"
    return f"- 附件文件: [{entry['name']}]({relative_path})"


def append_plan_export_timeline_visual_section(
    markdown: str,
    todo_payload: dict[str, object],
    export_path: Path,
) -> str:
    grouped_entries = _group_plan_export_attachment_entries(todo_payload)
    if not grouped_entries:
        return markdown

    asset_dir = export_path.with_name(f"{export_path.stem}_assets")
    section_lines = ["## 时间线图示", ""]
    has_content = False

    for group in grouped_entries:
        rendered_items: list[str] = []
        for attachment in group["attachments"]:
            copied = _copy_plan_export_attachment(attachment.get("path", ""), asset_dir)
            if copied is None:
                continue
            relative_path = copied.relative_to(export_path.parent).as_posix()
            rendered_items.append(_build_plan_export_attachment_markdown_item(attachment, relative_path))
        if not rendered_items:
            continue

        section_lines.append(f"### [{group['timestamp']}] {group['scenario']}")
        if group.get("content"):
            section_lines.append(f"> {group['content']}")
        section_lines.extend(rendered_items)
        section_lines.append("")
        has_content = True

    if not has_content:
        return markdown

    normalized = str(markdown or "").strip()
    visual_markdown = "\n".join(section_lines).strip()
    if "## 时间线图示" in normalized:
        return normalized

    timeline_match = re.search(r"^##\s*时间线回顾\s*$", normalized, re.MULTILINE)
    if not timeline_match:
        return f"{normalized}\n\n{visual_markdown}".strip()

    insertion_index = normalized.find("\n## ", timeline_match.end())
    if insertion_index == -1:
        return f"{normalized}\n\n{visual_markdown}".strip()
    return f"{normalized[:insertion_index].rstrip()}\n\n{visual_markdown}\n\n{normalized[insertion_index + 1:].lstrip()}".strip()


def append_plan_export_attachment_section(
    markdown: str,
    todo_payload: dict[str, object],
    export_path: Path,
) -> str:
    attachment_entries = _iter_plan_export_attachment_entries(todo_payload)
    if not attachment_entries:
        return markdown

    asset_dir = export_path.with_name(f"{export_path.stem}_assets")
    section_lines = ["## 附件图示", ""]
    has_content = False

    for entry in attachment_entries:
        copied = _copy_plan_export_attachment(entry.get("path", ""), asset_dir)
        if copied is None:
            continue
        relative_path = copied.relative_to(export_path.parent).as_posix()
        heading = f"### [{entry['timestamp']}] {entry['scenario']} - {entry['name']}"
        section_lines.append(heading)
        if entry.get("content"):
            section_lines.append(f"> {entry['content']}")
        section_lines.append(_build_plan_export_attachment_markdown_item(entry, relative_path))
        section_lines.append("")
        has_content = True

    if not has_content:
        return markdown

    normalized = str(markdown or "").strip()
    attachment_markdown = "\n".join(section_lines).strip()
    if "## 附件图示" in normalized:
        return normalized
    return f"{normalized}\n\n{attachment_markdown}".strip()


def build_plan_export_filename(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(title or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return f"{cleaned or '待办处理方案'}.md"


class PlanExportWorker(_BaseVisionWorker):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        llm_service: LLMService,
        model_label: str,
        timeout: int,
        todo_payload: dict[str, object],
        export_path: str,
        parent=None,
    ):
        super().__init__(parent)
        self._llm_service = llm_service
        self._model = model_label
        self._timeout = timeout
        self._todo_payload = todo_payload
        self._export_path = export_path

    def run(self) -> None:
        try:
            raw_markdown = self._run_llm_task(
                "plan_export",
                messages=build_plan_export_messages(self._todo_payload),
                temperature=0.2,
                timeout=min(self._timeout, 30),
            )
            markdown = ensure_plan_export_timeline_section(
                normalize_markdown_content(raw_markdown),
                self._todo_payload,
            )
            if not markdown:
                raise ValueError("生成的方案内容为空")
            export_file = Path(self._export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            markdown = append_plan_export_timeline_visual_section(
                markdown,
                self._todo_payload,
                export_file,
            )
            markdown = append_plan_export_attachment_section(
                markdown,
                self._todo_payload,
                export_file,
            )
            export_file.write_text(markdown, encoding="utf-8")
            self.finished.emit(str(export_file))
        except LLMServiceError as exc:
            self.error.emit(f"导出方案失败，模型调用错误: {exc}")
        except Exception as exc:
            self.error.emit(f"导出方案失败: {exc}")


class AIWorker(_BaseVisionWorker):
    def __init__(self, image: QPixmap, llm_service: LLMService, model_label: str,
                 timeout: int = 30,
                 scenario: str = "工单跟进",
                 analysis_intent: AnalysisIntent | None = None,
                 context_text: str | ContextSummaryRequest = "",
                 max_image_bytes: int = 4 * 1024 * 1024,
                 parent=None):
        super().__init__(parent)
        self._image = image
        self._feedback_image_base64 = self._pixmap_to_base64(image)
        self._llm_service = llm_service
        self._model = model_label
        self._timeout = timeout
        self._max_image_bytes = max_image_bytes
        self._scenario = scenario
        self._analysis_intent = analysis_intent or build_analysis_intent("chat_feedback")
        self._context_request = context_text if isinstance(context_text, ContextSummaryRequest) else None
        self._context_text = context_text.strip() if isinstance(context_text, str) else ""
        self._context_summary_service = ContextSummaryService(llm_service)

    def run(self) -> None:
        encoded_images: list[EncodedImage] = []
        try:
            raw_text, encoded_images = self._call_api()
            try:
                result = ResultParser.parse(raw_text)
                self._record_prompt_trace(status="success", raw_response=raw_text, image_payloads=encoded_images)
                self.show_result.emit(result, self._scenario, self._model)
                self.finished.emit(result)
            except (ValueError, KeyError, TypeError):
                self._record_prompt_trace(status="parse_error", raw_response=raw_text, image_payloads=encoded_images)
                self.parse_error.emit(raw_text)
        except LLMServiceError as exc:
            self._record_prompt_trace(status="error", error_message=str(exc), image_payloads=encoded_images)
            self.error.emit(f"模型调用失败: {exc}")
        except Exception as exc:
            self._record_prompt_trace(status="error", error_message=str(exc), image_payloads=encoded_images)
            self.error.emit(f"未知错误: {exc}")

    def _call_api(self) -> tuple[str, list[EncodedImage]]:
        started_at = time.perf_counter()
        encoded_image = self._encode_for_api(self._image, image_count=1)
        self._context_text = self._resolve_context_text()
        bundle = self._build_prompt_bundle(image_count=1)
        messages = [
            Message(role="system", content=bundle.system_prompt),
            Message(
                role="user",
                content=[
                    ContentPart(type="text", text=bundle.user_prompt),
                    ContentPart(type="image_data_url", data_url=encoded_image.data_url),
                ],
            ),
        ]
        try:
            run_result = self._run_llm_task_detailed(
                "analysis",
                messages=messages,
                temperature=0.3,
                timeout=self._timeout,
            )
        except TaskExecutionError as exc:
            self._analysis_stats = AnalysisRunStats(
                provider_id=exc.reference.provider_id,
                provider_name=exc.reference.provider_name,
                model_id=exc.reference.model_id,
                model_name=exc.reference.model_name,
                latency_ms=round((time.perf_counter() - started_at) * 1000),
                llm_latency_ms=exc.latency_ms,
                preprocess_ms=encoded_image.preprocess_ms,
                attempts=exc.attempts,
                image_count=1,
                input_bytes=encoded_image.byte_size,
            )
            raise
        self._analysis_stats = self._build_analysis_stats(
            run_result=run_result,
            preprocess_ms=encoded_image.preprocess_ms,
            input_bytes=encoded_image.byte_size,
            image_count=1,
            latency_ms=round((time.perf_counter() - started_at) * 1000),
        )
        return run_result.text, [encoded_image]


class MultiCaptureAIWorker(_BaseVisionWorker):
    def __init__(self, images: list[QPixmap], llm_service: LLMService, model_label: str,
                 timeout: int = 30,
                 scenario: str = "连续步骤截图",
                 analysis_intent: AnalysisIntent | None = None,
                 context_text: str | ContextSummaryRequest = "",
                 max_image_bytes: int = 4 * 1024 * 1024,
                 parent=None):
        super().__init__(parent)
        self._images = images
        self._feedback_image_base64 = self._pixmap_to_base64(self._build_combined_preview(images))
        self._llm_service = llm_service
        self._model = model_label
        self._timeout = timeout
        self._max_image_bytes = max_image_bytes
        self._scenario = scenario
        self._analysis_intent = analysis_intent or build_analysis_intent("step_sequence", capture_count=len(images))
        self._context_request = context_text if isinstance(context_text, ContextSummaryRequest) else None
        self._context_text = context_text.strip() if isinstance(context_text, str) else ""
        self._context_summary_service = ContextSummaryService(llm_service)

    def run(self) -> None:
        encoded_images: list[EncodedImage] = []
        try:
            raw_text, encoded_images = self._call_api()
            try:
                result = ResultParser.parse(raw_text)
                self._record_prompt_trace(status="success", raw_response=raw_text, image_payloads=encoded_images)
                self.show_result.emit(result, self._scenario, self._model)
                self.finished.emit(result)
            except (ValueError, KeyError, TypeError):
                self._record_prompt_trace(status="parse_error", raw_response=raw_text, image_payloads=encoded_images)
                self.parse_error.emit(raw_text)
        except LLMServiceError as exc:
            self._record_prompt_trace(status="error", error_message=str(exc), image_payloads=encoded_images)
            self.error.emit(f"模型调用失败: {exc}")
        except Exception as exc:
            self._record_prompt_trace(status="error", error_message=str(exc), image_payloads=encoded_images)
            self.error.emit(f"未知错误: {exc}")

    def _call_api(self) -> tuple[str, list[EncodedImage]]:
        started_at = time.perf_counter()
        self._context_text = self._resolve_context_text()
        bundle = self._build_prompt_bundle(image_count=len(self._images))
        content: list[ContentPart] = [
            ContentPart(type="text", text=bundle.user_prompt)
        ]
        encoded_images: list[EncodedImage] = []
        for index, pixmap in enumerate(self._images, 1):
            encoded_image = self._encode_for_api(pixmap, image_count=len(self._images))
            encoded_images.append(encoded_image)
            content.append(ContentPart(type="text", text=f"第 {index} 张截图"))
            content.append(ContentPart(type="image_data_url", data_url=encoded_image.data_url))

        preprocess_ms = sum(item.preprocess_ms for item in encoded_images)
        input_bytes = sum(item.byte_size for item in encoded_images)
        try:
            run_result = self._run_llm_task_detailed(
                "analysis",
                messages=[
                    Message(role="system", content=bundle.system_prompt),
                    Message(role="user", content=content),
                ],
                temperature=0.3,
                timeout=self._timeout,
            )
        except TaskExecutionError as exc:
            self._analysis_stats = AnalysisRunStats(
                provider_id=exc.reference.provider_id,
                provider_name=exc.reference.provider_name,
                model_id=exc.reference.model_id,
                model_name=exc.reference.model_name,
                latency_ms=round((time.perf_counter() - started_at) * 1000),
                llm_latency_ms=exc.latency_ms,
                preprocess_ms=preprocess_ms,
                attempts=exc.attempts,
                image_count=max(1, len(self._images)),
                input_bytes=input_bytes,
            )
            raise
        self._analysis_stats = self._build_analysis_stats(
            run_result=run_result,
            preprocess_ms=preprocess_ms,
            input_bytes=input_bytes,
            image_count=max(1, len(self._images)),
            latency_ms=round((time.perf_counter() - started_at) * 1000),
        )
        return run_result.text, encoded_images

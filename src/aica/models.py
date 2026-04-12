"""Domain models for ticket-oriented Todo workflows."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

from .ticket_field_resolver import (
    normalize_ticket_type,
    resolve_product_line,
)
from .text_sanitize import sanitize_text, strip_invalid_surrogates


UNKNOWN_TEXT = "未知"
UNCLASSIFIED_TASK = "未分类任务"
PENDING_TEXT = "待补充"

_TITLE_PREFIXES = (
    "客户反馈",
    "客户表示",
    "客户反映",
    "客户需要",
    "客户要求",
    "用户反馈",
    "用户表示",
    "用户反映",
    "用户需要",
    "用户要求",
    "目前",
    "当前",
    "现象",
    "问题",
    "出现",
    "现需",
)

_STRONG_ISSUE_KEYWORDS = (
    "失败",
    "异常",
    "报错",
    "错误",
    "卡顿",
    "超时",
    "中断",
    "无法",
    "不能",
    "不生效",
    "不显示",
    "不通过",
    "丢失",
    "缺失",
    "失效",
    "变成",
    "变为",
    "显示为",
    "显示成",
    "乱码",
    "错位",
    "变q",
)

_WEAK_ISSUE_KEYWORDS = (
    "定制",
    "适配",
    "整改",
    "优化",
    "补充",
    "新增",
    "处理",
    "排查",
    "修复",
    "完善",
    "支持",
    "同步",
    "搭建",
    "实现",
)

_FOLLOW_UP_PREFIXES = (
    "需要",
    "需",
    "待",
    "排查",
    "确认",
    "检查",
    "查看",
    "分析",
    "定位",
    "截图显示",
    "当前截图",
    "当前使用",
)

_OBJECT_HINTS = (
    "勾选框",
    "复选框",
    "登录",
    "接口",
    "按钮",
    "二维码",
    "字体",
    "样张",
    "文件",
    "附件",
    "字段",
    "列表",
    "表单",
    "文档",
    "页面",
)

_TRIGGER_HINTS = (
    "重新打开",
    "打开后",
    "提交后",
    "保存后",
    "上传后",
    "勾选后",
    "点击后",
    "刷新后",
    "切换后",
    "线上",
)

_SINGLE_CHAR_CHANGE_RE = re.compile(r"变(?:为|成)?([A-Za-z0-9])(?:了)?")
_DISPLAY_CHAR_RE = re.compile(r"显示(?:为|成)?([A-Za-z0-9])")


def _clean(value: Any, fallback: str = UNKNOWN_TEXT) -> str:
    text = sanitize_text(value)
    return text or fallback


def _clean_free_text(value: Any) -> str:
    return sanitize_text(value)


def is_unknown_text(value: Any) -> bool:
    return not str(value or "").strip() or str(value).strip() == UNKNOWN_TEXT


def _normalize_title_candidate(text: str) -> str:
    candidate = str(text or "").strip()
    if not candidate:
        return ""

    candidate = re.sub(r"^(?:但|并且|且|并|然后|目前|当前|现象为?)", "", candidate)
    candidate = re.sub(r"^(?:用户|客户)(?:反馈|表示|反映|提到)?", "", candidate)
    candidate = re.sub(r"^在", "", candidate)
    candidate = re.sub(r"^遇到", "", candidate)
    candidate = re.sub(r"(?:的问题|问题现象|异常现象|的异常|问题)$", "", candidate)
    candidate = candidate.strip("：:，,。.；; ")

    if candidate.startswith("需要"):
        candidate = candidate[2:]
    elif candidate.startswith("需"):
        candidate = candidate[1:]
    if candidate.startswith("进一步") and len(candidate) > 3:
        candidate = candidate[3:]
    if candidate.startswith(("对", "将", "把")) and len(candidate) > 1:
        candidate = candidate[1:]

    candidate = _SINGLE_CHAR_CHANGE_RE.sub(r"变成字符\1", candidate)
    candidate = _DISPLAY_CHAR_RE.sub(r"显示为字符\1", candidate)
    candidate = candidate.replace("就变成字符", "变成字符")
    candidate = candidate.replace("就变", "变")
    candidate = candidate.rstrip("了")
    return candidate.strip("：:，,。.；; ")


def _score_title_fragment(fragment: str) -> int:
    candidate = _normalize_title_candidate(fragment)
    if not candidate:
        return -10**6

    lowered = candidate.lower()
    score = min(len(candidate), 30)
    score += sum(12 for keyword in _STRONG_ISSUE_KEYWORDS if keyword in lowered or keyword in candidate)
    score += sum(4 for keyword in _WEAK_ISSUE_KEYWORDS if keyword in candidate)
    score += sum(5 for keyword in _OBJECT_HINTS if keyword in candidate)
    score += sum(6 for keyword in _TRIGGER_HINTS if keyword in candidate)

    if any(candidate.startswith(prefix) for prefix in _FOLLOW_UP_PREFIXES):
        score -= 18
    if "未勾选" in candidate and not any(keyword in candidate for keyword in ("变成", "变为", "显示为", "异常", "报错", "错误")):
        score -= 14
    if any(keyword in candidate for keyword in ("服务器", "字体可用性", "可用性")) and "异常" not in candidate:
        score -= 8
    return score


def _extract_object_hint(text: str) -> str:
    matches = [hint for hint in _OBJECT_HINTS if hint in text]
    if "文档" in text and "勾选框" in text:
        return "文档勾选框"
    if "页面" in text and "按钮" in text:
        return "页面按钮"
    return matches[0] if matches else ""


def summarize_issue_title(text: Any, fallback: str = UNCLASSIFIED_TASK, max_length: int = 20) -> str:
    cleaned = re.sub(r"\s+", "", str(text or ""))
    if not cleaned:
        return fallback[:max_length]

    sentences = [part.strip() for part in re.split(r"[。！？；;\n]+", cleaned) if part.strip()]
    if not sentences:
        sentences = [cleaned]

    sentence = max(sentences, key=_score_title_fragment)
    fragments = [part.strip() for part in re.split(r"[，,、]+", sentence) if part.strip()]
    if not fragments:
        fragments = [sentence]

    candidate = max(fragments, key=_score_title_fragment)
    normalized_candidate = _normalize_title_candidate(candidate)
    object_hint = _extract_object_hint(sentence)

    if (
        object_hint
        and object_hint not in normalized_candidate
        and any(keyword in normalized_candidate for keyword in _TRIGGER_HINTS + ("变成", "变为", "显示为", "异常", "报错", "错误"))
    ):
        normalized_candidate = f"{object_hint}{normalized_candidate}"

    if len(fragments) > 1:
        richer_fragment = max(
            (
                fragment
                for fragment in fragments
                if any(keyword in fragment for keyword in _TRIGGER_HINTS + ("变成", "变为", "显示为", "异常", "报错", "错误"))
            ),
            key=_score_title_fragment,
            default="",
        )
        normalized_richer = _normalize_title_candidate(richer_fragment)
        if object_hint and normalized_richer and object_hint not in normalized_richer:
            combined = f"{object_hint}{normalized_richer}"
            if _score_title_fragment(combined) >= _score_title_fragment(normalized_candidate):
                normalized_candidate = combined

    candidate = normalized_candidate

    for prefix in _TITLE_PREFIXES:
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):]
            break

    candidate = candidate or cleaned
    return candidate[:max_length]


@dataclass
class TicketSummaryFields:
    group_name: str = UNKNOWN_TEXT
    environment: str = UNKNOWN_TEXT
    product_line: str = UNKNOWN_TEXT
    ticket_type: str = UNKNOWN_TEXT
    ticket_version: str = ""

    def __post_init__(self) -> None:
        self.group_name = _clean(self.group_name)
        self.environment = _clean(self.environment)
        self.product_line = resolve_product_line(raw_value=self.product_line)
        self.ticket_type = normalize_ticket_type(self.ticket_type)
        self.ticket_version = _clean_free_text(self.ticket_version)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "TicketSummaryFields":
        payload = payload or {}
        return cls(
            group_name=_clean(payload.get("group_name")),
            environment=_clean(payload.get("environment")),
            product_line=payload.get("product_line"),
            ticket_type=payload.get("ticket_type"),
            ticket_version=payload.get("ticket_version"),
        )


@dataclass(frozen=True)
class EvidenceItem:
    type: str
    label: str
    value: str
    source_image_index: int = 1
    scene_type: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", _clean_free_text(self.type))
        object.__setattr__(self, "label", _clean_free_text(self.label))
        object.__setattr__(self, "value", _clean_free_text(self.value))
        try:
            index = int(self.source_image_index)
        except (TypeError, ValueError):
            index = 1
        object.__setattr__(self, "source_image_index", max(1, index))
        object.__setattr__(self, "scene_type", _clean_free_text(self.scene_type))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "EvidenceItem | None":
        if not isinstance(payload, dict):
            return None
        evidence = cls(
            type=payload.get("type", ""),
            label=payload.get("label", ""),
            value=payload.get("value", ""),
            source_image_index=payload.get("source_image_index", 1),
            scene_type=payload.get("scene_type", ""),
        )
        if not (evidence.type and evidence.value):
            return None
        if not evidence.label:
            object.__setattr__(evidence, "label", evidence.type)
        return evidence


def _evidence_key(item: EvidenceItem) -> tuple[str, str, str]:
    return (
        item.type.strip().lower(),
        item.label.strip().lower(),
        re.sub(r"\s+", " ", item.value.strip()).lower(),
    )


def merge_evidence_items(*groups: list[EvidenceItem]) -> list[EvidenceItem]:
    merged: list[EvidenceItem] = []
    seen: set[tuple[str, str, str]] = set()
    for group in groups:
        for item in group:
            key = _evidence_key(item)
            if not item.value or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def format_evidence_items_for_timeline(items: list[EvidenceItem]) -> str:
    merged_items = merge_evidence_items(items)
    if not merged_items:
        return ""
    return "\n".join(
        f"- {item.label or item.type}: {item.value}"
        for item in merged_items
        if item.value.strip()
    )


def merge_timeline_with_evidence(timeline_entry: str, evidence_items: list[EvidenceItem]) -> str:
    base_text = str(timeline_entry or "").strip()
    evidence_text = format_evidence_items_for_timeline(evidence_items)
    if not evidence_text:
        return base_text[:600]
    if not base_text:
        return evidence_text[:600]
    return f"{base_text}\n补充信息:\n{evidence_text}"[:600]


def merge_summary_fields_for_append(
    existing: TicketSummaryFields,
    incoming: TicketSummaryFields,
) -> TicketSummaryFields:
    def _merge_value(current: str, candidate: str) -> str:
        return candidate if is_unknown_text(current) and not is_unknown_text(candidate) else current

    return TicketSummaryFields(
        group_name=_merge_value(existing.group_name, incoming.group_name),
        environment=_merge_value(existing.environment, incoming.environment),
        product_line=_merge_value(existing.product_line, incoming.product_line),
        ticket_type=_merge_value(existing.ticket_type, incoming.ticket_type),
        ticket_version=_merge_value(existing.ticket_version, incoming.ticket_version),
    )


@dataclass
class TicketSnapshot:
    title: str
    fields: TicketSummaryFields
    current_summary: str
    timeline_entry: str
    evidence_items: list[EvidenceItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "group_name": self.fields.group_name,
            "environment": self.fields.environment,
            "product_line": self.fields.product_line,
            "ticket_type": self.fields.ticket_type,
            "ticket_version": self.fields.ticket_version,
            "current_summary": self.current_summary,
            "timeline_entry": self.timeline_entry,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TicketSnapshot":
        raw_summary = payload.get("current_summary") or payload.get("summary") or payload.get("task_desc")
        raw_title = sanitize_text(payload.get("title"))
        if raw_title:
            title = raw_title
        else:
            title_source = raw_summary or raw_title
            title = summarize_issue_title(title_source, fallback=UNCLASSIFIED_TASK)
        current_summary = _clean(raw_summary, fallback=PENDING_TEXT)
        timeline_entry = _clean(
            payload.get("timeline_entry") or payload.get("follow_up") or current_summary,
            fallback=current_summary,
        )
        ticket_context = "\n".join(
            str(part).strip()
            for part in (
                raw_title,
                raw_summary,
                payload.get("timeline_entry"),
                payload.get("follow_up"),
            )
            if str(part or "").strip()
        )
        fields = TicketSummaryFields.from_dict(
            {
                "group_name": payload.get("group_name"),
                "environment": payload.get("environment"),
                "product_line": payload.get("product_line") or payload.get("platform"),
                "ticket_type": normalize_ticket_type(
                    payload.get("ticket_type"),
                    summary_text=ticket_context,
                ),
                "ticket_version": payload.get("ticket_version"),
            }
        )
        evidence_payload = payload.get("evidence_items", [])
        evidence_items = []
        if isinstance(evidence_payload, list):
            for item in evidence_payload:
                evidence = EvidenceItem.from_dict(item)
                if evidence is not None:
                    evidence_items.append(evidence)
        merged_evidence_items = merge_evidence_items(evidence_items)
        return cls(
            title=title,
            fields=fields,
            current_summary=current_summary[:400],
            timeline_entry=merge_timeline_with_evidence(timeline_entry, merged_evidence_items),
            evidence_items=[],
        )

    @classmethod
    def from_text(cls, text: str) -> "TicketSnapshot":
        cleaned = sanitize_text(text)
        summary = cleaned or PENDING_TEXT
        title = summarize_issue_title(summary, fallback=UNCLASSIFIED_TASK)
        return cls(
            title=title,
            fields=TicketSummaryFields(ticket_type=normalize_ticket_type("", summary_text=summary)),
            current_summary=summary[:400],
            timeline_entry=summary[:600],
            evidence_items=[],
        )

    def __str__(self) -> str:
        evidence_lines = "\n".join(
            f"{index}. [{strip_invalid_surrogates(item.type)}] "
            f"{strip_invalid_surrogates(item.label)}: {strip_invalid_surrogates(item.value)}"
            for index, item in enumerate(self.evidence_items, 1)
        )
        evidence_text = evidence_lines or "无"
        return (
            f"标题: {strip_invalid_surrogates(self.title)}\n"
            f"群聊名称: {strip_invalid_surrogates(self.fields.group_name)}\n"
            f"环境: {strip_invalid_surrogates(self.fields.environment)}\n"
            f"产品线: {strip_invalid_surrogates(self.fields.product_line)}\n"
            f"工单类型: {strip_invalid_surrogates(self.fields.ticket_type)}\n"
            f"工单版本: {strip_invalid_surrogates(self.fields.ticket_version)}\n"
            f"当前摘要: {strip_invalid_surrogates(self.current_summary)}\n"
            f"跟进记录: {strip_invalid_surrogates(self.timeline_entry)}\n"
            f"关键证据:\n{evidence_text}"
        )

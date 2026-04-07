"""Helpers for ticket field enrichment and normalization."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


DEFAULT_PRODUCT_LINE = "文档中台"
TICKET_TYPE_OPTIONS = ("排查类", "咨询类", "操作类")
DEFAULT_TICKET_TYPE = TICKET_TYPE_OPTIONS[0]

_EXPLICIT_TICKET_TYPE_MAP = {
    "排查类": "排查类",
    "排查": "排查类",
    "问题排查": "排查类",
    "故障排查": "排查类",
    "异常排查": "排查类",
    "技术": "排查类",
    "技术类": "排查类",
    "问题处理": "排查类",
    "咨询类": "咨询类",
    "咨询": "咨询类",
    "业务咨询": "咨询类",
    "配置咨询": "咨询类",
    "答疑": "咨询类",
    "咨询答疑": "咨询类",
    "操作类": "操作类",
    "操作": "操作类",
    "执行": "操作类",
    "配置": "操作类",
    "变更": "操作类",
    "维护": "操作类",
}

_INVESTIGATE_KEYWORDS = (
    "报错",
    "错误",
    "异常",
    "失败",
    "故障",
    "无法",
    "不能",
    "不生效",
    "不显示",
    "超时",
    "卡顿",
    "白屏",
    "闪退",
    "丢失",
    "缺失",
    "中断",
    "告警",
    "排查",
    "定位",
    "恢复",
    "问题",
)

_CONSULT_KEYWORDS = (
    "咨询",
    "请问",
    "如何",
    "怎么",
    "怎样",
    "是否",
    "能否",
    "可以吗",
    "支持",
    "是什么",
    "说明",
    "文档",
    "教程",
    "指引",
    "介绍",
    "原因",
    "为什么",
    "规则",
    "口径",
)

_OPERATION_KEYWORDS = (
    "开通",
    "新增",
    "添加",
    "创建",
    "删除",
    "修改",
    "调整",
    "配置",
    "设置",
    "重置",
    "授权",
    "加白",
    "导入",
    "导出",
    "同步",
    "发布",
    "上线",
    "回滚",
    "变更",
    "绑定",
    "解绑",
    "关闭",
    "开启",
    "补录",
    "更新",
    "迁移",
)

_OPERATION_REQUEST_KEYWORDS = (
    "请帮忙",
    "帮忙",
    "麻烦",
    "协助",
    "处理下",
    "操作下",
)


def resolve_product_line(
    *,
    raw_value: Any = None,
    source_payload: Mapping[str, Any] | None = None,
) -> str:
    """Reserve a single extension point for future upstream field APIs."""
    _ = (raw_value, source_payload)
    return DEFAULT_PRODUCT_LINE


def normalize_ticket_type(raw_value: Any, *, summary_text: str = "") -> str:
    candidate = str(raw_value or "").strip()
    if candidate in TICKET_TYPE_OPTIONS:
        return candidate

    mapped = _map_explicit_ticket_type(candidate)
    if mapped:
        return mapped

    return infer_ticket_type(summary_text or candidate)


def infer_ticket_type(text: Any) -> str:
    content = str(text or "").strip().lower()
    if not content:
        return DEFAULT_TICKET_TYPE

    scores = {
        "排查类": _keyword_score(content, _INVESTIGATE_KEYWORDS, weight=3),
        "咨询类": _keyword_score(content, _CONSULT_KEYWORDS, weight=2),
        "操作类": _keyword_score(content, _OPERATION_KEYWORDS, weight=2),
    }

    if any(keyword in content for keyword in ("报错", "错误", "异常", "失败", "故障", "无法", "不能")):
        scores["排查类"] += 4
    if any(keyword in content for keyword in _OPERATION_REQUEST_KEYWORDS):
        scores["操作类"] += 3
    if any(keyword in content for keyword in ("请问", "如何", "怎么", "怎样", "是否", "能否")):
        scores["咨询类"] += 3
    if "？" in content or "?" in content:
        scores["咨询类"] += 1

    return max(TICKET_TYPE_OPTIONS, key=lambda option: (scores[option], -TICKET_TYPE_OPTIONS.index(option)))


def _map_explicit_ticket_type(candidate: str) -> str | None:
    normalized = candidate.strip()
    if not normalized:
        return None
    if normalized in _EXPLICIT_TICKET_TYPE_MAP:
        return _EXPLICIT_TICKET_TYPE_MAP[normalized]
    for alias, target in _EXPLICIT_TICKET_TYPE_MAP.items():
        if alias and alias in normalized:
            return target
    return None


def _keyword_score(text: str, keywords: tuple[str, ...], *, weight: int) -> int:
    return sum(weight for keyword in keywords if keyword in text)

"""Ticket field enrichment services and external feature point providers."""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Protocol

import requests

from aica.config import FeaturePointProviderConfig
from aica.llm.service import LLMService
from aica.llm.types import Message
from aica.models import TicketSummaryFields
from aica.text_sanitize import sanitize_text


ROOT_CAUSE_OPTIONS: tuple[str, ...] = (
    "常规咨询/功能操作指引",
    "常规咨询/其他常规咨询",
    "集成问题/集成对接指导",
    "集成问题/接口规范未遵循",
    "集成问题/其他集成问题",
    "集成问题/内部接口异常",
    "产品设计如此/体验与交互类",
    "产品设计如此/功能与逻辑类",
    "产品设计如此/功能不支持",
    "授权与许可问题/授权到期/失效",
    "授权与许可问题/授权权限不足",
    "授权与许可问题/授权证书异常",
    "版本与兼容性问题/版本不兼容/低版本问题",
    "版本与兼容性问题/微软不兼容问题",
    "版本与兼容性问题/其他版本与兼容性问题",
    "字体与渲染问题/服务端缺少字体",
    "字体与渲染问题/客户端字体缺失",
    "字体与渲染问题/字体渲染异常（跑版、模糊、多页）",
    "字体与渲染问题/其他字体与渲染问题",
    "环境问题/网络异常",
    "环境问题/服务器宕机",
    "环境问题/机房断电",
    "环境问题/DNS解析失败",
    "环境问题/时区不一致",
    "环境问题/版本不兼容",
    "环境问题/其他环境问题",
    "资源问题/内存不足",
    "资源问题/CPU占用过高",
    "资源问题/并发冲突",
    "资源问题/磁盘I/O瓶颈",
    "资源问题/网络带宽耗尽",
    "资源问题/连接池耗尽",
    "资源问题/线程池阻塞",
    "资源问题/其他资源问题",
    "数据问题/特殊样张",
    "数据问题/脏数据",
    "数据问题/索引问题",
    "数据问题/数据格式错误",
    "数据问题/特殊字符",
    "数据问题/数据缺失",
    "数据问题/数据重复",
    "数据问题/数据类型不匹配",
    "数据问题/其他数据问题",
    "配置问题/部署错误",
    "配置问题/插件冲突",
    "配置问题/版本不匹配",
    "配置问题/配置项修改",
    "配置问题/配置项缺失",
    "配置问题/配置值错误",
    "配置问题/动态配置未生效",
    "配置问题/证书过期",
    "配置问题/其他配置问题",
    "外部干扰问题/第三方软件冲突",
    "外部干扰问题/杀毒软件拦截",
    "外部干扰问题/防火墙限制",
    "外部干扰问题/第三方接口故障",
    "外部干扰问题/依赖服务不可用",
    "外部干扰问题/其他外部干扰问题",
    "代码BUG/逻辑错误",
    "代码BUG/内存泄漏",
    "代码BUG/其他代码BUG",
    "硬件故障问题/服务器硬盘损坏",
    "硬件故障问题/内存条故障",
    "硬件故障问题/网卡故障",
    "硬件故障问题/交换机故障",
    "硬件故障问题/存储设备故障",
    "硬件故障问题/其他硬件故障问题",
    "质量类其他问题",
    "体验类其他问题",
)


@dataclass(frozen=True)
class FeaturePointResult:
    value: str = ""
    matched: bool = False
    provider_name: str = ""
    raw_status: str = ""
    error_message: str = ""


class FeaturePointProvider(Protocol):
    def resolve(self, *, product_line: str, problem_desc: str) -> FeaturePointResult:
        """Return a normalized feature point result for the given ticket context."""


class NullFeaturePointProvider:
    def resolve(self, *, product_line: str, problem_desc: str) -> FeaturePointResult:
        return FeaturePointResult()


class HttpFeaturePointProvider:
    def __init__(self, config: FeaturePointProviderConfig) -> None:
        self._base_url = str(config.base_url or "").strip()
        self._api_key = str(config.api_key or "").strip()
        self._timeout_seconds = max(1, int(config.timeout_seconds))

    def resolve(self, *, product_line: str, problem_desc: str) -> FeaturePointResult:
        if not self._base_url:
            return FeaturePointResult(error_message="feature point provider not configured")

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["X-API-Key"] = self._api_key

        payload = {
            "product_line": sanitize_text(product_line),
            "problem_desc": sanitize_text(problem_desc),
            "use_keywords_recall": False
        }
        try:
            response = requests.post(
                self._base_url,
                json=payload,
                headers=headers,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return FeaturePointResult(
                provider_name="http",
                raw_status="request_failed",
                error_message=str(exc),
            )

        try:
            body = response.json()
        except ValueError:
            return FeaturePointResult(
                provider_name="http",
                raw_status="invalid_json",
                error_message="response is not valid JSON",
            )

        value = _extract_feature_point_value(body)
        return FeaturePointResult(
            value=value,
            matched=bool(value),
            provider_name="http",
            raw_status=_extract_status(body, response.status_code),
        )


def build_feature_point_provider(config: FeaturePointProviderConfig) -> FeaturePointProvider:
    if not config.enabled:
        return NullFeaturePointProvider()
    if str(config.provider or "").strip().lower() == "http":
        return HttpFeaturePointProvider(config)
    return NullFeaturePointProvider()


@dataclass
class EnrichmentOutcome:
    summary_fields: TicketSummaryFields
    errors: list[str]


@dataclass(frozen=True)
class GenerationResult:
    value: str = ""
    error_message: str = ""


@dataclass(frozen=True)
class TicketEnrichmentJob:
    todo_id: str
    previous_fields: TicketSummaryFields
    current_fields: TicketSummaryFields
    previous_problem_desc: str
    current_problem_desc: str
    previous_conclusion: str
    current_conclusion: str


class TicketEnrichmentService:
    def __init__(
        self,
        *,
        feature_point_provider: FeaturePointProvider | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self._feature_point_provider = feature_point_provider or NullFeaturePointProvider()
        self._llm_service = llm_service

    def enrich_for_update(
        self,
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
        previous_conclusion: str,
        current_conclusion: str,
    ) -> EnrichmentOutcome:
        fields = TicketSummaryFields.from_dict(current_fields.to_dict())
        errors: list[str] = []

        if self._should_refresh_feature_point(
            previous_fields=previous_fields,
            current_fields=fields,
            previous_problem_desc=previous_problem_desc,
            current_problem_desc=current_problem_desc,
        ):
            result = self._feature_point_provider.resolve(
                product_line=fields.product_line,
                problem_desc=current_problem_desc,
            )
            if result.value:
                fields.feature_point = result.value
                fields.feature_point_source = "auto"
            elif result.error_message:
                errors.append(f"功能点生成失败: {result.error_message}")

        if self._should_refresh_root_cause_desc(
            previous_fields=previous_fields,
            current_fields=fields,
            previous_problem_desc=previous_problem_desc,
            current_problem_desc=current_problem_desc,
            previous_conclusion=previous_conclusion,
            current_conclusion=current_conclusion,
        ):
            generated_desc = self._generate_root_cause_desc(
                problem_desc=current_problem_desc,
                conclusion=current_conclusion,
            )
            if generated_desc.value:
                fields.root_cause_desc = generated_desc.value
                fields.root_cause_desc_source = "auto"
            else:
                errors.append("根因描述生成失败")

        if self._should_refresh_root_cause(
            previous_fields=previous_fields,
            current_fields=fields,
            previous_problem_desc=previous_problem_desc,
            current_problem_desc=current_problem_desc,
            previous_conclusion=previous_conclusion,
            current_conclusion=current_conclusion,
        ):
            generated_root_cause = self._classify_root_cause(
                problem_desc=current_problem_desc,
                conclusion=current_conclusion,
                root_cause_desc=fields.root_cause_desc,
            )
            if generated_root_cause.value:
                fields.root_cause = generated_root_cause.value
                fields.root_cause_source = "auto"
            else:
                errors.append("问题根因生成失败")

        return EnrichmentOutcome(summary_fields=fields, errors=errors)

    @staticmethod
    def _should_refresh_feature_point(
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
    ) -> bool:
        if not current_fields.product_line.strip() or not current_problem_desc.strip():
            return False
        if not current_fields.feature_point.strip():
            return True
        if current_fields.feature_point_source != "auto":
            return False
        return (
            sanitize_text(previous_fields.product_line) != sanitize_text(current_fields.product_line)
            or sanitize_text(previous_problem_desc) != sanitize_text(current_problem_desc)
        )

    @staticmethod
    def _should_refresh_root_cause_desc(
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
        previous_conclusion: str,
        current_conclusion: str,
    ) -> bool:
        if not current_problem_desc.strip() or not current_conclusion.strip():
            return False
        if sanitize_text(previous_conclusion) != sanitize_text(current_conclusion):
            return True
        if not current_fields.root_cause_desc.strip():
            return True
        if current_fields.root_cause_desc_source != "auto":
            return False
        return (
            sanitize_text(previous_problem_desc) != sanitize_text(current_problem_desc)
            or sanitize_text(previous_conclusion) != sanitize_text(current_conclusion)
            or sanitize_text(previous_fields.root_cause_desc) != sanitize_text(current_fields.root_cause_desc)
        )

    @staticmethod
    def _should_refresh_root_cause(
        *,
        previous_fields: TicketSummaryFields,
        current_fields: TicketSummaryFields,
        previous_problem_desc: str,
        current_problem_desc: str,
        previous_conclusion: str,
        current_conclusion: str,
    ) -> bool:
        if not current_problem_desc.strip() or not current_conclusion.strip():
            return False
        if sanitize_text(previous_conclusion) != sanitize_text(current_conclusion):
            return True
        if not current_fields.root_cause.strip():
            return True
        if current_fields.root_cause_source != "auto":
            return False
        return (
            sanitize_text(previous_problem_desc) != sanitize_text(current_problem_desc)
            or sanitize_text(previous_conclusion) != sanitize_text(current_conclusion)
            or sanitize_text(previous_fields.root_cause_desc) != sanitize_text(current_fields.root_cause_desc)
            or sanitize_text(previous_fields.root_cause) != sanitize_text(current_fields.root_cause)
        )

    def _generate_root_cause_desc(self, *, problem_desc: str, conclusion: str) -> GenerationResult:
        if self._llm_service is None:
            return GenerationResult(error_message="根因描述生成失败: 未配置 LLM")
        prompt = (
            "请根据问题描述和当前结论，总结一句简洁的根因描述。"
            "只输出根因描述本身，不要输出标题、编号、解释。"
        )
        try:
            result = self._llm_service.run_task(
                "analysis",
                messages=[
                    Message(role="system", content=prompt),
                    Message(
                        role="user",
                        content=f"问题描述：{problem_desc}\n当前结论：{conclusion}",
                    ),
                ],
                temperature=0.1,
            )
        except Exception as exc:  # noqa: BLE001
            return GenerationResult(error_message=f"根因描述生成失败: {exc}")
        normalized = _normalize_llm_text(result, limit=120)
        if normalized:
            return GenerationResult(value=normalized)
        return GenerationResult(error_message="根因描述生成失败")

    def _classify_root_cause(
        self,
        *,
        problem_desc: str,
        conclusion: str,
        root_cause_desc: str,
    ) -> GenerationResult:
        if self._llm_service is None:
            return GenerationResult(error_message="问题根因生成失败: 未配置 LLM")
        options = "\n".join(f"- {option}" for option in ROOT_CAUSE_OPTIONS)
        prompt = (
            "你是根因分类助手。请根据“根因描述”从以下固定可选根因分类中选择唯一一个最匹配的结果。\n\n"
            "规则：\n"
            "1. 只能从下面的固定可选根因分类中选择，禁止新增、改写、合并、拆分分类。\n"
            "2. 输出必须与候选项完全一致。\n"
            "3. 部分分类名称本身包含多个“/”，这也是分类名称的一部分，必须原样输出，例如“版本与兼容性问题/版本不兼容/低版本问题”。\n"
            "4. 优先判断直接根因，不要按现象、影响或责任方分类。\n"
            "5. 如果根因描述体现为配置未添加、漏配、缺少必要配置项、配置项不存在、未初始化、未下发，则优先输出“配置问题/配置项缺失”。\n"
            "6. 如果信息不足无法准确判断，只能输出“质量类其他问题”或“体验类其他问题”中更合适的一项。\n"
            "7. 只输出分类名称，不要输出解释、分析过程或其他内容。\n"
            "固定可选根因分类：\n"
            f"{options}"
        )
        try:
            result = self._llm_service.run_task(
                "analysis",
                messages=[
                    Message(role="system", content=prompt),
                    Message(
                        role="user",
                        content=(
                            f"问题描述：{problem_desc}\n"
                            f"当前结论：{conclusion}\n"
                            f"根因描述：{root_cause_desc}"
                        ),
                    ),
                ],
                temperature=0.0,
            )
        except Exception as exc:  # noqa: BLE001
            return GenerationResult(error_message=f"问题根因生成失败: {exc}")
        normalized = _normalize_llm_text(result, limit=120)
        matched = _match_root_cause_option(normalized)
        if matched:
            return GenerationResult(value=matched)
        return GenerationResult(error_message="问题根因生成失败")


def build_ticket_enrichment_job(*, previous_todo, current_todo) -> TicketEnrichmentJob:
    return TicketEnrichmentJob(
        todo_id=sanitize_text(getattr(current_todo, "id", "")),
        previous_fields=TicketSummaryFields.from_dict(getattr(previous_todo, "summary_fields").to_dict()),
        current_fields=TicketSummaryFields.from_dict(getattr(current_todo, "summary_fields").to_dict()),
        previous_problem_desc=sanitize_text(getattr(previous_todo, "current_summary", "")),
        current_problem_desc=sanitize_text(getattr(current_todo, "current_summary", "")),
        previous_conclusion=sanitize_text(getattr(getattr(previous_todo, "conclusion", None), "content", "")),
        current_conclusion=sanitize_text(getattr(getattr(current_todo, "conclusion", None), "content", "")),
    )


def is_ticket_enrichment_job_still_current(todo, job: TicketEnrichmentJob) -> bool:
    if sanitize_text(getattr(todo, "id", "")) != sanitize_text(job.todo_id):
        return False
    current_fields = getattr(todo, "summary_fields", TicketSummaryFields())
    current_product_line = sanitize_text(getattr(current_fields, "product_line", ""))
    return (
        sanitize_text(getattr(todo, "current_summary", "")) == sanitize_text(job.current_problem_desc)
        and sanitize_text(getattr(getattr(todo, "conclusion", None), "content", "")) == sanitize_text(job.current_conclusion)
        and current_product_line == sanitize_text(job.current_fields.product_line)
    )


def merge_async_enrichment_fields(
    *,
    current_fields: TicketSummaryFields,
    enriched_fields: TicketSummaryFields,
    conclusion_changed: bool = False,
) -> TicketSummaryFields:
    merged = TicketSummaryFields.from_dict(current_fields.to_dict())
    if merged.feature_point_source != "manual":
        merged.feature_point = enriched_fields.feature_point
        merged.feature_point_source = enriched_fields.feature_point_source
    if conclusion_changed or merged.root_cause_desc_source != "manual":
        merged.root_cause_desc = enriched_fields.root_cause_desc
        merged.root_cause_desc_source = enriched_fields.root_cause_desc_source
    if conclusion_changed or (merged.root_cause_source != "manual" and merged.root_cause_desc_source != "manual"):
        merged.root_cause = enriched_fields.root_cause
        merged.root_cause_source = enriched_fields.root_cause_source
    return merged


def summarize_enrichment_errors(errors: list[str]) -> str:
    messages: list[str] = []
    seen: set[str] = set()
    for item in errors:
        normalized = sanitize_text(item).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        messages.append(normalized)
    return "；".join(messages)


def _extract_feature_point_value(payload: object) -> str:
    if isinstance(payload, dict):
        direct = sanitize_text(payload.get("feature_point") or payload.get("featurePoint"))
        if direct:
            return direct
        data = payload.get("data")
        if isinstance(data, dict):
            nested = sanitize_text(data.get("feature_point") or data.get("featurePoint"))
            if nested:
                return nested
        candidates = payload.get("candidates")
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict):
                    candidate = sanitize_text(item.get("feature_point") or item.get("featurePoint") or item.get("name"))
                else:
                    candidate = sanitize_text(item)
                if candidate:
                    return candidate
    if isinstance(payload, list):
        for item in payload:
            candidate = _extract_feature_point_value(item)
            if candidate:
                return candidate
    return ""


def _extract_status(payload: object, status_code: int) -> str:
    if isinstance(payload, dict):
        value = sanitize_text(payload.get("status") or payload.get("code") or payload.get("message"))
        if value:
            return value
    return str(status_code)


def _normalize_llm_text(value: str, *, limit: int) -> str:
    text = sanitize_text(value).strip()
    if text.startswith("```"):
        text = text.strip("`")
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            text = sanitize_text(parsed.get("result") or parsed.get("value") or "")
    text = text.splitlines()[0].strip() if text else ""
    text = text.lstrip("-0123456789.、:： ").strip()
    return text[:limit]


def _match_root_cause_option(value: str) -> str:
    normalized_value = sanitize_text(value).strip()
    if not normalized_value:
        return ""
    if normalized_value in ROOT_CAUSE_OPTIONS:
        return normalized_value
    value_compact = normalized_value.replace("/", "").replace(" ", "")
    value_tail = normalized_value.split("/")[-1]
    if value in ROOT_CAUSE_OPTIONS:
        return value
    for option in ROOT_CAUSE_OPTIONS:
        if option in normalized_value or normalized_value in option:
            return option
        option_tail = option.split("/")[-1]
        option_compact = option.replace("/", "").replace(" ", "")
        if option_tail and option_tail in normalized_value:
            return option
        if value_tail and value_tail in option:
            return option
        if value_compact and value_compact in option_compact:
            return option
    return "质量类其他问题"

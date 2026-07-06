"""Chattodo server API client."""
from __future__ import annotations

import ast
import json
import mimetypes
import base64
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import requests

from aica.config import ServerConfig
from aica.text_sanitize import sanitize_text


class ChattodoServerError(ValueError):
    """Raised when the Chattodo server cannot complete a request."""


class ChattodoServerClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = sanitize_text(base_url).rstrip("/")
        self._api_key = sanitize_text(api_key)
        self._timeout_seconds = max(1, int(timeout_seconds or 30))
        self._session = session or requests.Session()

    @classmethod
    def from_config(
        cls,
        config: ServerConfig,
        *,
        session: requests.Session | None = None,
    ) -> "ChattodoServerClient":
        if not bool(getattr(config, "enabled", False)):
            raise ChattodoServerError("服务端集成未启用，请先在控制面板启用服务端配置。")
        base_url = sanitize_text(getattr(config, "base_url", ""))
        if not base_url:
            raise ChattodoServerError("服务端地址不能为空。")
        api_key = sanitize_text(getattr(config, "api_key", ""))
        if not api_key:
            raise ChattodoServerError("服务端 API Key 不能为空。")
        try:
            timeout_seconds = int(getattr(config, "timeout_seconds", 30) or 30)
        except (TypeError, ValueError) as exc:
            raise ChattodoServerError("服务端超时时间必须是整数。") from exc
        if timeout_seconds <= 0:
            raise ChattodoServerError("服务端超时时间必须大于 0。")
        return cls(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            session=session,
        )

    def fetch_my_latest_projects(
        self,
        *,
        page_size: int = 200,
        max_pages: int = 100,
    ) -> list[dict[str, Any]]:
        payload = self._request_json(
            "GET",
            "/api/open/v1/workbench/projects/my/latest",
            params={
                "page_size": max(1, int(page_size or 200)),
                "max_pages": max(1, int(max_pages or 100)),
            },
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ChattodoServerError("服务端返回格式错误：缺少 data。")
        items = data.get("items")
        if not isinstance(items, list):
            raise ChattodoServerError("服务端返回格式错误：缺少 data.items。")
        return [dict(item) for item in items if isinstance(item, dict)]

    def fetch_identity_me(self) -> dict[str, Any]:
        payload = self._request_json(
            "GET",
            "/api/open/v1/identity/me",
            headers={"Accept": "application/json"},
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ChattodoServerError("服务端返回格式错误：缺少 data。")
        return dict(data)

    def fetch_function_point_options(
        self,
        *,
        product_line: str = "",
        q: str = "",
        page: int = 1,
        page_size: int = 20,
        active_only: bool = True,
    ) -> list[dict[str, str]]:
        payload = self._request_json(
            "GET",
            "/api/open/v1/workbench/function-points/options",
            params={
                "product_line": sanitize_text(product_line).strip(),
                "q": sanitize_text(q).strip(),
                "page": max(1, int(page or 1)),
                "page_size": min(100, max(1, int(page_size or 20))),
                "active_only": bool(active_only),
            },
            headers={"Accept": "application/json"},
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ChattodoServerError("服务端返回格式错误：缺少 data。")
        items = data.get("items")
        if not isinstance(items, list):
            raise ChattodoServerError("服务端返回格式错误：缺少 data.items。")
        normalized_items: list[dict[str, str]] = []
        for item in items:
            normalized_item = self._normalize_function_point_option_item(item)
            if normalized_item is not None:
                normalized_items.append(normalized_item)
        return normalized_items

    def fetch_dictionary_options(self, type_code: str) -> list[dict[str, Any]]:
        normalized_type_code = sanitize_text(type_code).strip()
        if not normalized_type_code:
            raise ChattodoServerError("字典类型编码不能为空。")

        payload = self._request_json(
            "GET",
            f"/api/open/v1/basic-data/dictionaries/{quote(normalized_type_code, safe='')}/options",
            headers={"Accept": "application/json"},
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ChattodoServerError("服务端返回格式错误：缺少 data。")
        items = data.get("items")
        if not isinstance(items, list):
            raise ChattodoServerError("服务端返回格式错误：缺少 data.items。")
        normalized_items: list[dict[str, Any]] = []
        for item in items:
            normalized_item = self._normalize_dictionary_option_item(item)
            if normalized_item is not None:
                normalized_items.append(normalized_item)
        return normalized_items

    def fetch_custom_field_options(self, field_ids: list[str]) -> list[dict[str, Any]]:
        normalized_field_ids = [
            sanitize_text(field_id).strip()
            for field_id in list(field_ids or [])
            if sanitize_text(field_id).strip()
        ]
        if not normalized_field_ids:
            raise ChattodoServerError("自定义字段编码不能为空。")

        payload = self._request_json(
            "POST",
            "/api/open/v1/workbench/ach/custom-field-options",
            json={"field_ids": normalized_field_ids},
            headers={"Accept": "application/json"},
        )
        items = self._extract_custom_field_option_items(payload)
        normalized_items: list[dict[str, Any]] = []
        for item in items:
            normalized_item = self._normalize_custom_field_option_item(item)
            if normalized_item is not None:
                normalized_items.append(normalized_item)
        return normalized_items

    def fetch_customer_environment_options(self) -> list[dict[str, Any]]:
        return self.fetch_ach_custom_field_options_by_label("客户环境")

    def fetch_issue_product_options(self) -> list[dict[str, Any]]:
        return self.fetch_ach_custom_field_options_by_label("问题所属产品")

    def fetch_ach_custom_field_options_by_label(self, field_label: str) -> list[dict[str, Any]]:
        ach_field_options = self.fetch_dictionary_options("ach-field")
        normalized_field_label = sanitize_text(field_label).strip()
        customer_environment_field_code = ""
        for item in ach_field_options:
            if sanitize_text(item.get("value")).strip() == normalized_field_label:
                customer_environment_field_code = sanitize_text(item.get("code")).strip()
                if customer_environment_field_code:
                    break
        if not customer_environment_field_code:
            raise ChattodoServerError(f"ACH 自定义字段字典里未找到“{normalized_field_label}”对应编码。")
        return self.fetch_custom_field_options([customer_environment_field_code])

    def bind_chat_groups_by_task_order_no(self, *, task_order_no: str, group_names: list[str]) -> None:
        normalized_task_order = sanitize_text(task_order_no)
        normalized_group_names = [sanitize_text(item) for item in group_names if sanitize_text(item)]
        if not normalized_task_order:
            raise ChattodoServerError("任务单号不能为空。")
        if not normalized_group_names:
            return
        self._request_json(
            "POST",
            "/api/open/v1/workbench/chat-groups/by-task-order-no",
            json={
                "task_order_no": normalized_task_order,
                "group_names": normalized_group_names,
            },
        )

    def update_project_by_task_order_no(self, payload: dict[str, object]) -> None:
        normalized_payload = {
            str(key).strip(): value
            for key, value in dict(payload or {}).items()
            if str(key).strip()
        }
        task_order_no = sanitize_text(normalized_payload.get("task_order_no"))
        if not task_order_no:
            raise ChattodoServerError("任务书单号不能为空。")
        normalized_payload["task_order_no"] = task_order_no
        self._request_json(
            "PUT",
            "/api/open/v1/workbench/projects/by-task-order-no",
            json=normalized_payload,
        )

    def upsert_work_order(self, payload: dict[str, object]) -> dict[str, Any]:
        normalized_payload = {
            str(key).strip(): value
            for key, value in dict(payload or {}).items()
            if str(key).strip()
        }
        external_order_no = sanitize_text(normalized_payload.get("external_order_no"))
        title = sanitize_text(normalized_payload.get("title"))
        if not external_order_no:
            raise ChattodoServerError("外部工单号不能为空。")
        if not title:
            raise ChattodoServerError("工单标题不能为空。")
        normalized_payload["external_order_no"] = external_order_no
        normalized_payload["title"] = title
        return self._request_json(
            "POST",
            "/api/open/v1/workbench/work-orders",
            json=normalized_payload,
        )

    def sync_my_work_orders(self, items: list[dict[str, object]]) -> dict[str, Any]:
        normalized_items = [
            {
                str(key).strip(): value
                for key, value in dict(item or {}).items()
                if str(key).strip()
            }
            for item in list(items or [])
            if isinstance(item, dict)
        ]
        if not normalized_items:
            raise ChattodoServerError("同步工单列表不能为空。")
        return self._request_json(
            "POST",
            "/api/open/v1/workbench/work-orders/sync-my",
            json={"items": normalized_items},
        )

    def pull_my_in_progress_work_orders(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        source_system: str = "",
        existing_external_order_nos: list[str] | None = None,
        existing_external_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        normalized_page = max(1, int(page or 1))
        normalized_page_size = min(500, max(1, int(page_size or 100)))
        payload: dict[str, object] = {
            "page": normalized_page,
            "page_size": normalized_page_size,
        }
        normalized_source = sanitize_text(source_system).strip()
        if normalized_source:
            payload["source_system"] = normalized_source
        order_nos = [
            sanitize_text(item).strip()
            for item in list(existing_external_order_nos or [])[:500]
            if sanitize_text(item).strip()
        ]
        external_ids = [
            sanitize_text(item).strip()
            for item in list(existing_external_ids or [])[:500]
            if sanitize_text(item).strip()
        ]
        if order_nos:
            payload["existing_external_order_nos"] = order_nos
        if external_ids:
            payload["existing_external_ids"] = external_ids
        return self._request_json(
            "POST",
            "/api/open/v1/workbench/work-orders/pull-my-in-progress",
            json=payload,
        )

    def get_work_order_ach_statuses(
        self,
        external_order_nos: list[str],
        *,
        source_system: str = "",
    ) -> dict[str, Any]:
        order_nos = [
            sanitize_text(item).strip()
            for item in list(external_order_nos or [])[:500]
            if sanitize_text(item).strip()
        ]
        if not order_nos:
            raise ChattodoServerError("工单号列表不能为空。")
        payload: dict[str, object] = {"external_order_nos": order_nos}
        normalized_source = sanitize_text(source_system).strip()
        if normalized_source:
            payload["source_system"] = normalized_source
        return self._request_json(
            "POST",
            "/api/open/v1/workbench/work-orders/ach-status/batch",
            json=payload,
        )

    def upload_workbench_file(
        self,
        file_path: str | Path,
        *,
        file_name: str = "",
        content_type: str = "",
        source_system: str = "",
        external_order_no: str = "",
        external_timeline_id: str = "",
        external_attachment_id: str = "",
    ) -> dict[str, Any]:
        path = Path(file_path).expanduser()
        if not path.is_file():
            raise ChattodoServerError(f"附件文件不存在：{path}")
        upload_name = sanitize_text(file_name).strip() or path.name
        upload_type = sanitize_text(content_type).strip() or mimetypes.guess_type(upload_name)[0] or "application/octet-stream"
        return self._request_file_upload(
            "/api/open/v1/workbench/files/upload",
            file_path=path,
            file_name=upload_name,
            content_type=upload_type,
            data={
                "source_system": sanitize_text(source_system).strip(),
                "external_order_no": sanitize_text(external_order_no).strip(),
                "external_timeline_id": sanitize_text(external_timeline_id).strip(),
                "external_attachment_id": sanitize_text(external_attachment_id).strip(),
            },
        )

    def download_workbench_file(self, file_url_or_id: str, target_path: str | Path) -> Path:
        normalized_url = sanitize_text(file_url_or_id).strip()
        if not normalized_url:
            raise ChattodoServerError("附件下载地址不能为空。")
        target = Path(target_path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        url = self._resolve_file_download_url(normalized_url)
        try:
            response = self._session.request(
                "GET",
                url,
                headers={"X-API-Key": self._api_key},
                timeout=self._timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ChattodoServerError(f"服务端请求超时：{self._timeout_seconds} 秒。") from exc
        except requests.RequestException as exc:
            raise ChattodoServerError(f"服务端请求失败：{exc}") from exc
        if response.status_code >= 400:
            detail = sanitize_text(getattr(response, "text", ""))
            suffix = f"：{detail[:200]}" if detail else ""
            raise ChattodoServerError(f"服务端返回 HTTP {response.status_code}{suffix}")
        target.write_bytes(bytes(getattr(response, "content", b"") or b""))
        return target

    def match_feature_point(self, *, product_line: str, desc: str) -> str:
        payload = self._request_json(
            "POST",
            "/api/runtime/apps/workflow-mphzwo1h/run",
            json={
                "variables": {
                    "product_line": sanitize_text(product_line),
                    "desc": sanitize_text(desc),
                },
            },
            require_success_envelope=False,
        )
        answer = sanitize_text(payload.get("answer")).strip()
        if not answer:
            raise ChattodoServerError("服务端功能点匹配未返回有效结果。")
        return answer

    def search_assist_cases(self, *, question: str, function_point: str = "") -> dict[str, Any]:
        normalized_question = sanitize_text(question).strip()
        if not normalized_question:
            raise ChattodoServerError("辅助排查案例检索问题描述不能为空。")
        payload = self._request_json(
            "POST",
            "/api/runtime/apps/workflow-mq63n60i/run",
            json={
                "variables": {
                    "question": normalized_question,
                    "function_point": sanitize_text(function_point).strip(),
                }
            },
            require_success_envelope=False,
        )
        raw_answer = sanitize_text(self._runtime_answer(payload)).strip()
        if not raw_answer:
            raise ChattodoServerError("服务端辅助排查案例检索未返回有效结果。")
        try:
            parsed = json.loads(raw_answer)
        except ValueError as exc:
            raise ChattodoServerError("服务端辅助排查案例结果不是有效 JSON。") from exc
        if not isinstance(parsed, list):
            raise ChattodoServerError("服务端辅助排查案例结果格式错误。")
        normalized_items: list[dict[str, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            normalized_items.append(
                {
                    "title": sanitize_text(item.get("title")).strip(),
                    "description": sanitize_text(item.get("description")).strip(),
                    "match_confidence": sanitize_text(item.get("match_confidence")).strip(),
                    "match_reason": sanitize_text(item.get("match_reason")).strip(),
                    "solution": sanitize_text(item.get("solution")).strip(),
                    "detail_url": sanitize_text(item.get("detail_url") or item.get("detailUrl")).strip(),
                }
            )
        return {
            "items": normalized_items,
            "trace_id": sanitize_text(payload.get("trace_id")).strip(),
            "usage": dict(payload.get("usage")) if isinstance(payload.get("usage"), dict) else {},
        }

    def lookup_error_codes(self, *, describe: str) -> dict[str, Any]:
        normalized_describe = sanitize_text(describe).strip()
        if not normalized_describe:
            raise ChattodoServerError("错误码查询描述不能为空。")
        payload = self._request_json(
            "POST",
            "/api/runtime/apps/workflow-mquntp53/run",
            json={
                "variables": {
                    "describe": normalized_describe,
                }
            },
            require_success_envelope=False,
        )
        raw_answer = sanitize_text(self._runtime_answer(payload)).strip()
        if not raw_answer:
            raise ChattodoServerError("服务端错误码查询未返回有效结果。")
        try:
            parsed = json.loads(raw_answer)
        except ValueError as exc:
            try:
                parsed = ast.literal_eval(raw_answer)
            except (ValueError, SyntaxError) as inner_exc:
                raise ChattodoServerError("服务端错误码结果不是有效 JSON。") from inner_exc
        if not isinstance(parsed, list):
            raise ChattodoServerError("服务端错误码结果格式错误。")
        normalized_items: list[dict[str, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            normalized_items.append(
                {
                    "code": sanitize_text(item.get("code")).strip(),
                    "value": sanitize_text(item.get("value")).strip(),
                    "description": sanitize_text(item.get("description")).strip(),
                }
            )
        return {
            "items": normalized_items,
            "trace_id": sanitize_text(payload.get("trace_id")).strip(),
            "usage": dict(payload.get("usage")) if isinstance(payload.get("usage"), dict) else {},
        }

    def generate_root_cause(self, *, task_desc: str, answer: str) -> dict[str, str]:
        payload = self._request_json(
            "POST",
            "/api/runtime/apps/single-turn-mpkqa7ch/run",
            json={
                "variables": {
                    "task_desc": sanitize_text(task_desc),
                    "answer": sanitize_text(answer),
                },
            },
            require_success_envelope=False,
        )
        raw_answer = sanitize_text(self._runtime_answer(payload)).strip()
        if not raw_answer:
            raise ChattodoServerError("服务端根因生成未返回有效结果。")
        try:
            parsed = json.loads(raw_answer)
        except ValueError as exc:
            raise ChattodoServerError("服务端根因生成结果不是有效 JSON。") from exc
        if not isinstance(parsed, dict):
            raise ChattodoServerError("服务端根因生成结果格式错误。")
        description = sanitize_text(parsed.get("root_cause_description")).strip()
        category = sanitize_text(parsed.get("root_cause_category")).strip()
        if not description and not category:
            raise ChattodoServerError("服务端根因生成未返回有效字段。")
        return {
            "root_cause_description": description,
            "root_cause_category": category,
        }

    def analyze_screenshot(
        self,
        *,
        image_data_url: str | list[str],
        summary: str = "",
        summary_type: str = "",
    ) -> dict[str, Any]:
        image_values = image_data_url if isinstance(image_data_url, list) else [image_data_url]
        image_payload = [
            self._image_variable_payload(item, index)
            for index, item in enumerate(image_values, 1)
            if sanitize_text(item).strip()
        ]
        if not image_payload:
            raise ChattodoServerError("截图内容不能为空。")
        payload = self._request_json(
            "POST",
            "/api/runtime/apps/single-turn-mpmfi35y/run",
            json={
                "variables": {
                    "imags": image_payload,
                    "summary": sanitize_text(summary).strip(),
                    "summary_type": sanitize_text(summary_type).strip(),
                },
            },
            require_success_envelope=False,
        )
        raw_answer = sanitize_text(self._runtime_answer(payload)).strip()
        if not raw_answer:
            raise ChattodoServerError("服务端截图分析未返回有效结果。")
        try:
            parsed = json.loads(raw_answer)
        except ValueError as exc:
            raise ChattodoServerError("服务端截图分析结果不是有效 JSON。") from exc
        if not isinstance(parsed, dict):
            raise ChattodoServerError("服务端截图分析结果格式错误。")
        return {
            "answer": raw_answer,
            "result": dict(parsed),
            "trace_id": sanitize_text(payload.get("trace_id")).strip(),
            "usage": dict(payload.get("usage")) if isinstance(payload.get("usage"), dict) else {},
        }

    def generate_stage_summary(
        self,
        *,
        current_markdown: str,
        stage_materials: str,
        task_title: str,
        stage_name: str,
        stage_goal: str,
    ) -> str:
        payload = self._request_json(
            "POST",
            "/api/runtime/apps/single-turn-mpmrkccz/run",
            json={
                "variables": {
                    "current_markdown": sanitize_text(current_markdown).strip(),
                    "stage_materials": sanitize_text(stage_materials).strip(),
                    "task_title": sanitize_text(task_title).strip(),
                    "stage_name": sanitize_text(stage_name).strip(),
                    "stage_goal": sanitize_text(stage_goal).strip(),
                },
            },
            require_success_envelope=False,
        )
        raw_answer = sanitize_text(self._runtime_answer(payload)).strip()
        if not raw_answer:
            raise ChattodoServerError("服务端阶段总结未返回有效结果。")
        return raw_answer

    def polish_timeline_content(self, *, content: str) -> dict[str, str]:
        normalized_content = sanitize_text(content).strip()
        if not normalized_content:
            raise ChattodoServerError("时间线内容不能为空。")
        payload = self._request_json(
            "POST",
            "/api/runtime/apps/single-turn-mqck3wdm/run",
            json={
                "variables": {
                    "content": normalized_content,
                },
            },
            require_success_envelope=False,
        )
        raw_answer = sanitize_text(self._runtime_answer(payload)).strip()
        if not raw_answer:
            raise ChattodoServerError("服务端时间线润色未返回有效结果。")
        try:
            parsed = json.loads(raw_answer)
        except ValueError as exc:
            raise ChattodoServerError("服务端时间线润色结果不是有效 JSON。") from exc
        if not isinstance(parsed, dict):
            raise ChattodoServerError("服务端时间线润色结果格式错误。")
        summary = sanitize_text(parsed.get("summary")).strip()
        detail = sanitize_text(parsed.get("detail")).strip()
        if not summary and not detail:
            raise ChattodoServerError("服务端时间线润色未返回摘要或详情。")
        return {
            "summary": summary,
            "detail": detail,
        }

    def translate_image_text_blocks(self, *, source_lang: str, target_lang: str, texts: list[str]) -> dict[str, Any]:
        normalized_source = sanitize_text(source_lang).strip().lower()
        normalized_target = sanitize_text(target_lang).strip().lower()
        normalized_texts = [sanitize_text(item).strip() for item in list(texts or [])]
        normalized_texts = [item for item in normalized_texts if item]
        if normalized_source not in {"zh", "en"}:
            raise ChattodoServerError("图片翻译源语言仅支持 zh 或 en。")
        if normalized_target not in {"zh", "en"}:
            raise ChattodoServerError("图片翻译目标语言仅支持 zh 或 en。")
        if not normalized_texts:
            raise ChattodoServerError("图片翻译文本不能为空。")
        payload = self._request_json(
            "POST",
            "/api/runtime/apps/single-turn-mqd7ce05/run",
            json={
                "variables": {
                    "text": json.dumps(
                        {
                            "source_lang": normalized_source,
                            "target_lang": normalized_target,
                            "texts": normalized_texts,
                        },
                        ensure_ascii=False,
                    ),
                },
            },
            require_success_envelope=False,
        )
        raw_answer = sanitize_text(self._runtime_answer(payload)).strip()
        if not raw_answer:
            raise ChattodoServerError("服务端图片翻译未返回有效结果。")
        try:
            parsed = json.loads(raw_answer)
        except ValueError as exc:
            raise ChattodoServerError("服务端图片翻译结果不是有效 JSON。") from exc
        if not isinstance(parsed, dict):
            raise ChattodoServerError("服务端图片翻译结果格式错误。")
        translations = parsed.get("translations")
        if not isinstance(translations, list):
            raise ChattodoServerError("服务端图片翻译结果缺少 translations。")
        normalized_translations = [sanitize_text(item).strip() for item in translations]
        if len(normalized_translations) != len(normalized_texts):
            raise ChattodoServerError("服务端图片翻译结果数量与请求文本数量不一致。")
        return {
            "translations": normalized_translations,
            "trace_id": sanitize_text(payload.get("trace_id")).strip(),
            "usage": dict(payload.get("usage")) if isinstance(payload.get("usage"), dict) else {},
        }

    @staticmethod
    def _runtime_answer(payload: dict[str, Any]) -> object:
        answer = payload.get("answer")
        if answer:
            return answer
        data = payload.get("data")
        if isinstance(data, dict):
            answer = data.get("answer")
            if answer:
                return answer
            outputs = data.get("outputs")
            if isinstance(outputs, dict):
                answer = outputs.get("answer") or outputs.get("text") or outputs.get("markdown")
                if answer:
                    return answer
            result = data.get("result")
            if isinstance(result, dict):
                answer = result.get("answer") or result.get("text") or result.get("markdown")
                if answer:
                    return answer
            if isinstance(result, str):
                return result
        outputs = payload.get("outputs")
        if isinstance(outputs, dict):
            return outputs.get("answer") or outputs.get("text") or outputs.get("markdown") or ""
        return ""

    @staticmethod
    def _image_variable_payload(data_url: str, index: int) -> dict[str, object]:
        normalized = sanitize_text(data_url).strip()
        mime_type = "image/png"
        encoded = ""
        if normalized.startswith("data:") and "," in normalized:
            prefix, encoded = normalized.split(",", 1)
            mime_type = prefix.split(";", 1)[0].removeprefix("data:") or mime_type
        extension = "jpg" if mime_type == "image/jpeg" else "png"
        size = 0
        if encoded:
            try:
                size = len(base64.b64decode(encoded, validate=False))
            except Exception:
                size = 0
        return {
            "type": "image",
            "name": f"image-{max(1, int(index))}.{extension}",
            "mime_type": mime_type,
            "size": size,
            "data_url": normalized,
        }

    @staticmethod
    def _normalize_dictionary_option_item(item: object) -> dict[str, Any] | None:
        if isinstance(item, dict):
            raw_item = item.get("item")
            nested_item = raw_item if isinstance(raw_item, dict) else {}
            value = sanitize_text(item.get("value") or nested_item.get("value") or item.get("code") or nested_item.get("code"))
            label = sanitize_text(item.get("label") or value or nested_item.get("label") or nested_item.get("value"))
            code = sanitize_text(item.get("code") or nested_item.get("code") or value)
            sort_order = ChattodoServerClient._coerce_dictionary_sort_order(
                item.get("sort_order"),
                nested_item.get("sort_order"),
            )
            if not label and not value and not code:
                return None
            return {
                "label": label,
                "value": value or code or label,
                "code": code or value or label,
                "sort_order": sort_order,
                "item": dict(raw_item) if isinstance(raw_item, dict) else raw_item,
            }
        text = sanitize_text(item).strip()
        if not text:
            return None
        return {
            "label": text,
            "value": text,
            "code": text,
            "sort_order": None,
            "item": item,
        }

    @staticmethod
    def _normalize_function_point_option_item(item: object) -> dict[str, str] | None:
        if not isinstance(item, dict):
            return None
        full_name = sanitize_text(item.get("full_name")).strip()
        if not full_name:
            return None
        return {
            "value": full_name,
            "text": full_name,
        }

    @staticmethod
    def _extract_custom_field_option_items(payload: dict[str, Any]) -> list[object]:
        data = payload.get("data")
        container_items: list[object] = []
        if isinstance(data, list):
            container_items = list(data)
        elif isinstance(data, dict):
            direct_items = data.get("items")
            if isinstance(direct_items, list):
                container_items = list(direct_items)
            else:
                for key in ("list", "options"):
                    value = data.get(key)
                    if isinstance(value, list):
                        container_items = list(value)
                        break
                if not container_items:
                    for value in data.values():
                        if isinstance(value, list):
                            container_items = list(value)
                            break

        flattened: list[object] = []
        for item in container_items:
            if isinstance(item, dict):
                related_options = item.get("related_options")
                if isinstance(related_options, dict):
                    related_list = related_options.get("list")
                    if isinstance(related_list, list):
                        flattened.extend(
                            ChattodoServerClient._flatten_related_field_options(related_list)
                        )
                        continue
                nested_options = item.get("options")
                if isinstance(nested_options, list) and nested_options:
                    flattened.extend(nested_options)
                    continue
            flattened.append(item)
        if flattened:
            return flattened
        raise ChattodoServerError("服务端返回格式错误：缺少自定义字段选项。")

    @staticmethod
    def _flatten_related_field_options(
        nodes: list[object],
        *,
        parent_parts: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        parent_parts = list(parent_parts or [])
        flattened: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            value = sanitize_text(node.get("value") or node.get("label")).strip()
            label = sanitize_text(node.get("label") or node.get("value")).strip()
            if not value and not label:
                continue
            current_part = value or label
            current_parts = [*parent_parts, current_part]
            children = node.get("children")
            if isinstance(children, list) and children:
                flattened.extend(
                    ChattodoServerClient._flatten_related_field_options(
                        children,
                        parent_parts=current_parts,
                    )
                )
                continue
            path_value = "/".join(part for part in current_parts if part)
            if not path_value:
                continue
            flattened.append(
                {
                    "code": path_value,
                    "value": path_value,
                    "label": path_value,
                    "sort_order": None,
                    "item": dict(node),
                }
            )
        return flattened

    @staticmethod
    def _normalize_custom_field_option_item(item: object) -> dict[str, Any] | None:
        if isinstance(item, dict):
            raw_item = item.get("item")
            nested_item = raw_item if isinstance(raw_item, dict) else {}
            code = sanitize_text(
                item.get("code")
                or item.get("option_code")
                or item.get("id")
                or nested_item.get("code")
                or nested_item.get("option_code")
                or nested_item.get("id")
            )
            value = sanitize_text(
                item.get("value")
                or item.get("label")
                or item.get("name")
                or nested_item.get("value")
                or nested_item.get("label")
                or nested_item.get("name")
                or code
            )
            label = sanitize_text(item.get("label") or item.get("name") or nested_item.get("label") or value)
            sort_order = ChattodoServerClient._coerce_dictionary_sort_order(
                item.get("sort_order"),
                item.get("sortOrder"),
                nested_item.get("sort_order"),
                nested_item.get("sortOrder"),
            )
            if not code and not value and not label:
                return None
            return {
                "label": label or value or code,
                "value": value or label or code,
                "code": code or value or label,
                "sort_order": sort_order,
                "item": dict(raw_item) if isinstance(raw_item, dict) else raw_item,
            }
        text = sanitize_text(item).strip()
        if not text:
            return None
        return {
            "label": text,
            "value": text,
            "code": text,
            "sort_order": None,
            "item": item,
        }

    @staticmethod
    def _coerce_dictionary_sort_order(*values: object) -> int | None:
        for value in values:
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                return value
            if isinstance(value, float) and value.is_integer():
                return int(value)
            text = sanitize_text(value)
            if not text:
                continue
            try:
                return int(text)
            except (TypeError, ValueError):
                continue
        return None

    def _request_file_upload(
        self,
        path: str,
        *,
        file_path: Path,
        file_name: str,
        content_type: str,
        data: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        if not self._base_url:
            raise ChattodoServerError("服务端地址不能为空。")
        if not self._api_key:
            raise ChattodoServerError("服务端 API Key 不能为空。")

        url = f"{self._base_url}{path}"
        try:
            with file_path.open("rb") as handle:
                response = self._session.request(
                    "POST",
                    url,
                    files={"upload": (file_name, handle, content_type)},
                    data={
                        key: value
                        for key, value in dict(data or {}).items()
                        if sanitize_text(value).strip()
                    },
                    headers={"X-API-Key": self._api_key},
                    timeout=self._timeout_seconds,
                )
        except requests.Timeout as exc:
            raise ChattodoServerError(f"服务端请求超时：{self._timeout_seconds} 秒。") from exc
        except OSError as exc:
            raise ChattodoServerError(f"附件文件读取失败：{file_path}") from exc
        except requests.RequestException as exc:
            raise ChattodoServerError(f"服务端请求失败：{exc}") from exc

        return self._parse_response_json(response, require_success_envelope=True)

    def _resolve_file_download_url(self, file_url_or_id: str) -> str:
        parsed = urlparse(file_url_or_id)
        if parsed.scheme in {"http", "https"}:
            return file_url_or_id
        if not self._base_url:
            raise ChattodoServerError("服务端地址不能为空。")
        if file_url_or_id.startswith("/"):
            base = urlparse(self._base_url)
            return f"{base.scheme}://{base.netloc}{file_url_or_id}"
        if "/" not in file_url_or_id:
            return f"{self._base_url}/api/open/v1/files/{quote(file_url_or_id, safe='')}/download"
        return urljoin(f"{self._base_url}/", file_url_or_id.lstrip("/"))

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
        require_success_envelope: bool = True,
    ) -> dict[str, Any]:
        if not self._base_url:
            raise ChattodoServerError("服务端地址不能为空。")
        if not self._api_key:
            raise ChattodoServerError("服务端 API Key 不能为空。")

        url = f"{self._base_url}{path}"
        try:
            request_headers = {"X-API-Key": self._api_key}
            if json is not None:
                request_headers["Content-Type"] = "application/json"
            if headers:
                request_headers.update(
                    {
                        str(key).strip(): str(value)
                        for key, value in headers.items()
                        if str(key).strip() and value is not None
                    }
                )
            response = self._session.request(
                method,
                url,
                params=params,
                json=json,
                headers=request_headers,
                timeout=self._timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ChattodoServerError(f"服务端请求超时：{self._timeout_seconds} 秒。") from exc
        except requests.RequestException as exc:
            raise ChattodoServerError(f"服务端请求失败：{exc}") from exc

        return self._parse_response_json(response, require_success_envelope=require_success_envelope)

    @staticmethod
    def _parse_response_json(response: requests.Response, *, require_success_envelope: bool) -> dict[str, Any]:
        if response.status_code >= 400:
            detail = sanitize_text(getattr(response, "text", ""))
            suffix = f"：{detail[:200]}" if detail else ""
            raise ChattodoServerError(f"服务端返回 HTTP {response.status_code}{suffix}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ChattodoServerError("服务端返回不是有效 JSON。") from exc
        if not isinstance(payload, dict):
            raise ChattodoServerError("服务端返回格式错误：根节点不是对象。")

        if require_success_envelope and payload.get("success") is not True:
            code = sanitize_text(payload.get("code"))
            message = sanitize_text(payload.get("message")) or "服务端返回失败。"
            prefix = f"{code}: " if code else ""
            raise ChattodoServerError(f"{prefix}{message}")
        return dict(payload)

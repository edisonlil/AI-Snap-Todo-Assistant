"""Chattodo server API client."""
from __future__ import annotations

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

    def analyze_screenshot(self, *, image_data_url: str | list[str], summary: str = "") -> dict[str, Any]:
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
        require_success_envelope: bool = True,
    ) -> dict[str, Any]:
        if not self._base_url:
            raise ChattodoServerError("服务端地址不能为空。")
        if not self._api_key:
            raise ChattodoServerError("服务端 API Key 不能为空。")

        url = f"{self._base_url}{path}"
        try:
            headers = {"X-API-Key": self._api_key}
            if json is not None:
                headers["Content-Type"] = "application/json"
            response = self._session.request(
                method,
                url,
                params=params,
                json=json,
                headers=headers,
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

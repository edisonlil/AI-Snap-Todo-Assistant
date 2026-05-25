"""Chattodo server API client."""
from __future__ import annotations

from typing import Any

import json
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
        raw_answer = sanitize_text(payload.get("answer")).strip()
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

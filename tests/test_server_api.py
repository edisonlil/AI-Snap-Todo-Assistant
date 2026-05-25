from __future__ import annotations

from pathlib import Path
import sys

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import ServerConfig  # noqa: E402
from aica.server_api import ChattodoServerClient, ChattodoServerError  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, payload: object = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> object:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


class _FakeSession:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> object:
        self.calls.append({"method": method, "url": url, **kwargs})
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def test_fetch_my_latest_projects_sends_expected_request() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "task_order_no": "TASK-001",
                            "project_name": "project a",
                        }
                    ]
                },
            },
        )
    )
    client = ChattodoServerClient.from_config(
        ServerConfig(
            enabled=True,
            base_url="https://server.example.com/",
            api_key="server-key",
            timeout_seconds=45,
        ),
        session=session,  # type: ignore[arg-type]
    )

    items = client.fetch_my_latest_projects(page_size=200, max_pages=100)

    assert items == [{"task_order_no": "TASK-001", "project_name": "project a"}]
    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/projects/my/latest"
    assert session.calls[0]["params"] == {"page_size": 200, "max_pages": 100}
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key"}
    assert session.calls[0]["timeout"] == 45


def test_bind_chat_groups_by_task_order_no_sends_expected_request() -> None:
    session = _FakeSession(_FakeResponse(200, {"success": True, "data": {}}))
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    client.bind_chat_groups_by_task_order_no(
        task_order_no="TASK-001",
        group_names=["group-a", "", "group-b"],
    )

    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/chat-groups/by-task-order-no"
    assert session.calls[0]["json"] == {
        "task_order_no": "TASK-001",
        "group_names": ["group-a", "group-b"],
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_update_project_by_task_order_no_sends_expected_request() -> None:
    session = _FakeSession(_FakeResponse(200, {"success": True, "data": {}}))
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    client.update_project_by_task_order_no(
        {
            "task_order_no": "TASK-001",
            "project_name": "project a",
            "customer_name": "customer a",
            "product_line": "line",
            "product_version": "V2.0",
            "project_manager": "Alice",
            "project_level": "normal",
            "follow_up_started_at": "2026-05-23",
            "support_ended_at": "2026-12-31",
        }
    )

    assert session.calls[0]["method"] == "PUT"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/projects/by-task-order-no"
    assert session.calls[0]["json"] == {
        "task_order_no": "TASK-001",
        "project_name": "project a",
        "customer_name": "customer a",
        "product_line": "line",
        "product_version": "V2.0",
        "project_manager": "Alice",
        "project_level": "normal",
        "follow_up_started_at": "2026-05-23",
        "support_ended_at": "2026-12-31",
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_match_feature_point_sends_workflow_request_and_returns_answer() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": "协作设置/权限配置",
                "trace_id": "trace_xxx",
                "usage": {
                    "prompt_tokens": 128,
                    "completion_tokens": 256,
                    "total_tokens": 384,
                },
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    answer = client.match_feature_point(product_line="产品线", desc="工单描述")

    assert answer == "协作设置/权限配置"
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/workflow-mphzwo1h/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "product_line": "产品线",
            "desc": "工单描述",
        }
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_generate_root_cause_sends_single_turn_request_and_parses_answer() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": (
                    "{\n"
                    '  "root_cause_description": "测试环境服务节点下线导致文档创建报错15041",\n'
                    '  "root_cause_category": "环境问题/服务器宕机"\n'
                    "}"
                ),
                "trace_id": "trace_795bbd2f6da04c9f8f5806b83878d90c",
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    payload = client.generate_root_cause(task_desc="问题描述", answer="问题结论")

    assert payload == {
        "root_cause_description": "测试环境服务节点下线导致文档创建报错15041",
        "root_cause_category": "环境问题/服务器宕机",
    }
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/single-turn-mpkqa7ch/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "task_desc": "问题描述",
            "answer": "问题结论",
        }
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_client_rejects_missing_config() -> None:
    with pytest.raises(ChattodoServerError):
        ChattodoServerClient.from_config(ServerConfig())


def test_fetch_my_latest_projects_wraps_server_failures() -> None:
    client = ChattodoServerClient(
        base_url="https://server.example.com",
        api_key="server-key",
        session=_FakeSession(
            _FakeResponse(
                200,
                {
                    "success": False,
                    "code": "BAD_KEY",
                    "message": "invalid key",
                },
            )
        ),  # type: ignore[arg-type]
    )

    with pytest.raises(ChattodoServerError, match="BAD_KEY: invalid key"):
        client.fetch_my_latest_projects()


def test_fetch_my_latest_projects_wraps_http_and_json_errors() -> None:
    http_client = ChattodoServerClient(
        base_url="https://server.example.com",
        api_key="server-key",
        session=_FakeSession(_FakeResponse(500, text="boom")),  # type: ignore[arg-type]
    )
    with pytest.raises(ChattodoServerError, match="HTTP 500"):
        http_client.fetch_my_latest_projects()

    json_client = ChattodoServerClient(
        base_url="https://server.example.com",
        api_key="server-key",
        session=_FakeSession(_FakeResponse(200, ValueError("bad json"))),  # type: ignore[arg-type]
    )
    with pytest.raises(ChattodoServerError):
        json_client.fetch_my_latest_projects()

    timeout_client = ChattodoServerClient(
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=3,
        session=_FakeSession(requests.Timeout("slow")),  # type: ignore[arg-type]
    )
    with pytest.raises(ChattodoServerError):
        timeout_client.fetch_my_latest_projects()

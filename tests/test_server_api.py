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
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key"}
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

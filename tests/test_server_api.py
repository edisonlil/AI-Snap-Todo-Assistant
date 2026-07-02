from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.config import ServerConfig  # noqa: E402
from aica.server_api import ChattodoServerClient, ChattodoServerError  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, payload: object = None, text: str = "", content: bytes = b"") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.content = content

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
        if isinstance(self.response, list):
            if not self.response:
                raise AssertionError("No fake response left for request")
            next_response = self.response.pop(0)
            if isinstance(next_response, BaseException):
                raise next_response
            return next_response
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


def test_fetch_identity_me_sends_expected_request() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "code": "OK",
                "message": "success",
                "data": {
                    "id": 1,
                    "username": "admin",
                    "full_name": "平台管理员",
                    "email": "admin@example.com",
                    "phone": "",
                    "is_active": True,
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

    identity = client.fetch_identity_me()

    assert identity == {
        "id": 1,
        "username": "admin",
        "full_name": "平台管理员",
        "email": "admin@example.com",
        "phone": "",
        "is_active": True,
    }
    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/identity/me"
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Accept": "application/json"}
    assert session.calls[0]["timeout"] == 45


def test_fetch_function_point_options_sends_expected_request() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "label": "文档中台-运维平台-页面跑版-兼容问题",
                            "value": 1096,
                            "id": 1096,
                            "full_name": "文档中台-运维平台-页面跑版-兼容问题",
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

    items = client.fetch_function_point_options(q="页面跑版", page=2, page_size=50, active_only=False)

    assert items == [
        {
            "value": "文档中台-运维平台-页面跑版-兼容问题",
            "text": "文档中台-运维平台-页面跑版-兼容问题",
        }
    ]
    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/function-points/options"
    assert session.calls[0]["params"] == {
        "q": "页面跑版",
        "page": 2,
        "page_size": 50,
        "active_only": False,
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Accept": "application/json"}
    assert session.calls[0]["timeout"] == 45


def test_fetch_function_point_options_filters_items_without_full_name() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        {"full_name": "有效功能点"},
                        {"label": "缺少 full_name"},
                        "invalid",
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

    items = client.fetch_function_point_options()

    assert items == [{"value": "有效功能点", "text": "有效功能点"}]


def test_fetch_function_point_options_validates_response_shape() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": "not-a-list",
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

    with pytest.raises(ChattodoServerError, match="缺少 data.items"):
        client.fetch_function_point_options()


def test_fetch_dictionary_options_sends_expected_request() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "code": "paid",
                            "value": "已支付",
                            "sort_order": 1,
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

    items = client.fetch_dictionary_options("状态 类型")

    assert items == [
        {
            "label": "已支付",
            "value": "已支付",
            "code": "paid",
            "sort_order": 1,
            "item": None,
        }
    ]
    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/basic-data/dictionaries/%E7%8A%B6%E6%80%81%20%E7%B1%BB%E5%9E%8B/options"
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Accept": "application/json"}
    assert session.calls[0]["timeout"] == 45


def test_fetch_dictionary_options_supports_legacy_nested_item_payload() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "label": "已支付",
                            "value": "paid",
                            "code": "paid",
                            "sort_order": 1,
                            "item": {
                                "id": 12,
                                "type_id": 3,
                                "code": "paid",
                                "value": "已支付",
                                "status": "active",
                                "sort_order": 1,
                            },
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

    items = client.fetch_dictionary_options("状态 类型")

    assert items == [
        {
            "label": "已支付",
            "value": "paid",
            "code": "paid",
            "sort_order": 1,
            "item": {
                "id": 12,
                "type_id": 3,
                "code": "paid",
                "value": "已支付",
                "status": "active",
                "sort_order": 1,
            },
        }
    ]


def test_fetch_dictionary_options_validates_and_normalizes_bad_inputs() -> None:
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        session=_FakeSession(_FakeResponse(200, {"success": True})) ,  # type: ignore[arg-type]
    )

    with pytest.raises(ChattodoServerError, match="字典类型编码不能为空"):
        client.fetch_dictionary_options("   ")

    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        "paid",
                        {
                            "label": "",
                            "value": "",
                            "code": "",
                            "item": {"id": 12},
                        },
                    ]
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

    items = client.fetch_dictionary_options("status")

    assert items == [
        {
            "label": "paid",
            "value": "paid",
            "code": "paid",
            "sort_order": None,
            "item": "paid",
        }
    ]


def test_fetch_custom_field_options_sends_expected_request() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "code": "env-prod",
                            "value": "生产环境",
                            "sort_order": 1,
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

    items = client.fetch_custom_field_options(["select_field_123"])

    assert items == [
        {
            "label": "生产环境",
            "value": "生产环境",
            "code": "env-prod",
            "sort_order": 1,
            "item": None,
        }
    ]
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/ach/custom-field-options"
    assert session.calls[0]["json"] == {"field_ids": ["select_field_123"]}
    assert session.calls[0]["headers"] == {
        "X-API-Key": "server-key",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    assert session.calls[0]["timeout"] == 45


def test_fetch_customer_environment_options_resolves_ach_field_by_value() -> None:
    session = _FakeSession(
        [
            _FakeResponse(
                200,
                {
                    "success": True,
                    "data": {
                        "items": [
                            {
                                "code": "select_field_1964892725260812289",
                                "value": "客户环境",
                            }
                        ]
                    },
                },
            ),
            _FakeResponse(
                200,
                {
                    "success": True,
                    "data": {
                        "items": [
                            {
                                "code": "env-uat",
                                "value": "预发环境",
                            }
                        ]
                    },
                },
            ),
        ]
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

    items = client.fetch_customer_environment_options()

    assert items == [
        {
            "label": "预发环境",
            "value": "预发环境",
            "code": "env-uat",
            "sort_order": None,
            "item": None,
        }
    ]
    assert session.calls[0]["method"] == "GET"
    assert session.calls[1]["method"] == "POST"
    assert session.calls[1]["json"] == {"field_ids": ["select_field_1964892725260812289"]}


def test_fetch_issue_product_options_resolves_ach_field_by_value() -> None:
    session = _FakeSession(
        [
            _FakeResponse(
                200,
                {
                    "success": True,
                    "data": {
                        "items": [
                            {
                                "code": "related_field_1988864485569003521",
                                "value": "问题所属产品",
                            }
                        ]
                    },
                },
            ),
            _FakeResponse(
                200,
                {
                    "success": True,
                    "data": {
                        "items": [
                            {
                                "field_id": "related_field_1988864485569003521",
                                "field_type": "related_field",
                                "field_name": "问题所属产品",
                                "options": [],
                                "related_options": {
                                    "level": 2,
                                    "list": [
                                        {
                                            "value": "产品A",
                                            "label": "产品A",
                                            "children": [
                                                {
                                                    "value": "模块B",
                                                    "label": "模块B",
                                                    "children": [
                                                        {
                                                            "value": "功能C",
                                                            "label": "功能C",
                                                        }
                                                    ],
                                                }
                                            ],
                                        }
                                    ],
                                },
                            }
                        ]
                    },
                },
            ),
        ]
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

    items = client.fetch_issue_product_options()

    assert items == [
        {
            "label": "产品A/模块B/功能C",
            "value": "产品A/模块B/功能C",
            "code": "产品A/模块B/功能C",
            "sort_order": None,
            "item": {
                "value": "功能C",
                "label": "功能C",
            },
        }
    ]
    assert session.calls[1]["json"] == {"field_ids": ["related_field_1988864485569003521"]}


def test_fetch_custom_field_options_flattens_related_field_options() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [
                        {
                            "field_id": "related_field_x",
                            "field_type": "related_field",
                            "field_name": "问题所属产品",
                            "options": [],
                            "related_options": {
                                "level": 2,
                                "list": [
                                    {
                                        "value": "文档中心",
                                        "label": "文档中心",
                                        "children": [
                                            {"value": "V7", "label": "V7"},
                                            {"value": "V6", "label": "V6"},
                                        ],
                                    },
                                    {
                                        "value": "统一平台",
                                        "label": "统一平台",
                                    },
                                ],
                            },
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

    items = client.fetch_custom_field_options(["related_field_x"])

    assert items == [
        {
            "label": "文档中心/V7",
            "value": "文档中心/V7",
            "code": "文档中心/V7",
            "sort_order": None,
            "item": {"value": "V7", "label": "V7"},
        },
        {
            "label": "文档中心/V6",
            "value": "文档中心/V6",
            "code": "文档中心/V6",
            "sort_order": None,
            "item": {"value": "V6", "label": "V6"},
        },
        {
            "label": "统一平台",
            "value": "统一平台",
            "code": "统一平台",
            "sort_order": None,
            "item": {"value": "统一平台", "label": "统一平台"},
        },
    ]


def test_lookup_error_codes_sends_expected_request_and_parses_python_list_answer() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": "[{'code': '10001', 'value': 'InvalidArgument', 'description': '参数无效'}]",
                "trace_id": "trace_xxx",
                "usage": {
                    "prompt_tokens": 128,
                    "completion_tokens": 256,
                    "total_tokens": 384,
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

    payload = client.lookup_error_codes(describe="描述")

    assert payload["items"] == [
        {"code": "10001", "value": "InvalidArgument", "description": "参数无效"}
    ]
    assert payload["trace_id"] == "trace_xxx"
    assert payload["usage"]["total_tokens"] == 384
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/workflow-mquntp53/run"
    assert session.calls[0]["json"] == {"variables": {"describe": "描述"}}
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
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
            "project_manager": "Alice",
            "project_level": "normal",
            "follow_up_started_at": "2026-05-23",
            "support_ended_at": "2026-12-31",
            "versions": [
                {
                    "product_line": "文档中台",
                    "environment": "测试环境",
                    "version": "003",
                }
            ],
        }
    )

    assert session.calls[0]["method"] == "PUT"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/projects/by-task-order-no"
    assert session.calls[0]["json"] == {
        "task_order_no": "TASK-001",
        "project_name": "project a",
        "customer_name": "customer a",
        "product_line": "line",
        "project_manager": "Alice",
        "project_level": "normal",
        "follow_up_started_at": "2026-05-23",
        "support_ended_at": "2026-12-31",
        "versions": [
            {
                "product_line": "文档中台",
                "environment": "测试环境",
                "version": "003",
            }
        ],
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_upsert_work_order_sends_expected_request() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "item": {
                        "id": 1001,
                        "external_order_no": "todo-1",
                    }
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

    payload = client.upsert_work_order(
        {
            "source_system": "Chattodo",
            "external_order_no": "todo-1",
            "title": "测试工单",
            "status": "in_progress",
        }
    )

    assert payload["data"]["item"]["id"] == 1001
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/work-orders"
    assert session.calls[0]["json"] == {
        "source_system": "Chattodo",
        "external_order_no": "todo-1",
        "title": "测试工单",
        "status": "in_progress",
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_upsert_work_order_validates_required_fields() -> None:
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        session=_FakeSession(_FakeResponse(200, {"success": True})),  # type: ignore[arg-type]
    )

    with pytest.raises(ChattodoServerError, match="外部工单号不能为空"):
        client.upsert_work_order({"title": "测试工单"})

    with pytest.raises(ChattodoServerError, match="工单标题不能为空"):
        client.upsert_work_order({"external_order_no": "todo-1"})


def test_sync_my_work_orders_sends_expected_request() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "created_count": 1,
                    "updated_count": 0,
                    "skipped_count": 0,
                    "total_count": 1,
                    "results": [],
                },
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    payload = client.sync_my_work_orders(
        [
            {
                "source_system": "Chattodo",
                "external_order_no": "todo-1",
                "title": "上传失败",
            }
        ]
    )

    assert payload["data"]["created_count"] == 1
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/work-orders/sync-my"
    assert session.calls[0]["json"] == {
        "items": [
            {
                "source_system": "Chattodo",
                "external_order_no": "todo-1",
                "title": "上传失败",
            }
        ]
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}


def test_pull_my_in_progress_work_orders_sends_existing_ids() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "items": [],
                    "pagination": {"page": 1, "page_size": 100, "total": 0},
                },
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    client.pull_my_in_progress_work_orders(
        page=2,
        page_size=600,
        source_system="Chattodo",
        existing_external_order_nos=["todo-1", ""],
        existing_external_ids=["local-1"],
    )

    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/work-orders/pull-my-in-progress"
    assert session.calls[0]["json"] == {
        "page": 2,
        "page_size": 500,
        "source_system": "Chattodo",
        "existing_external_order_nos": ["todo-1"],
        "existing_external_ids": ["local-1"],
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}


def test_get_work_order_ach_statuses_sends_batch_order_numbers() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {"items": []},
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    client.get_work_order_ach_statuses(["todo-1", "", "todo-2"], source_system="Chattodo")

    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/work-orders/ach-status/batch"
    assert session.calls[0]["json"] == {
        "external_order_nos": ["todo-1", "todo-2"],
        "source_system": "Chattodo",
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}


def test_upload_workbench_file_sends_multipart_request(tmp_path: Path) -> None:
    file_path = tmp_path / "xiezuo.png"
    file_path.write_bytes(b"png")
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "file_object_id": "123",
                    "url": "/api/files/123/download",
                    "preview_url": "/api/files/123/preview",
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

    payload = client.upload_workbench_file(
        file_path,
        source_system="Chattodo",
        external_order_no="todo-1",
        external_timeline_id="timeline-1",
        external_attachment_id="att-1",
    )

    assert payload["data"]["file_object_id"] == "123"
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/open/v1/workbench/files/upload"
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key"}
    assert session.calls[0]["timeout"] == 12
    assert session.calls[0]["data"] == {
        "source_system": "Chattodo",
        "external_order_no": "todo-1",
        "external_timeline_id": "timeline-1",
        "external_attachment_id": "att-1",
    }
    file_tuple = session.calls[0]["files"]["upload"]  # type: ignore[index]
    assert file_tuple[0] == "xiezuo.png"
    assert file_tuple[2] == "image/png"


def test_download_workbench_file_writes_relative_url_with_api_key(tmp_path: Path) -> None:
    session = _FakeSession(_FakeResponse(200, content=b"file-content"))
    client = ChattodoServerClient(
        base_url="https://server.example.com/root/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )
    target = tmp_path / "downloaded.docx"

    saved = client.download_workbench_file("/api/files/123/download", target)

    assert saved == target
    assert target.read_bytes() == b"file-content"
    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == "https://server.example.com/api/files/123/download"
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key"}


def test_download_workbench_file_accepts_file_id(tmp_path: Path) -> None:
    session = _FakeSession(_FakeResponse(200, content=b"file-content"))
    client = ChattodoServerClient(
        base_url="https://server.example.com/root/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    client.download_workbench_file("123", tmp_path / "downloaded.docx")

    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == "https://server.example.com/root/api/open/v1/files/123/download"
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key"}


def test_download_workbench_file_accepts_non_numeric_file_id(tmp_path: Path) -> None:
    session = _FakeSession(_FakeResponse(200, content=b"file-content"))
    client = ChattodoServerClient(
        base_url="https://server.example.com/root/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    client.download_workbench_file("file-123", tmp_path / "downloaded.docx")

    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == "https://server.example.com/root/api/open/v1/files/file-123/download"
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key"}


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


def test_search_assist_cases_sends_workflow_request_and_parses_answer() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": json.dumps(
                    [
                        {
                            "title": "历史工单 A",
                            "description": "原始问题描述",
                            "match_confidence": "High",
                            "match_reason": "共同报错 20022",
                            "solution": "检查参数并修复返回类型",
                        }
                    ],
                    ensure_ascii=False,
                ),
                "trace_id": "trace_xxx",
                "usage": {"total_tokens": 384},
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    payload = client.search_assist_cases(question="问题描述", function_point="功能点")

    assert payload == {
        "items": [
            {
                "title": "历史工单 A",
                "description": "原始问题描述",
                "match_confidence": "High",
                "match_reason": "共同报错 20022",
                "solution": "检查参数并修复返回类型",
                "detail_url": "",
            }
        ],
        "trace_id": "trace_xxx",
        "usage": {"total_tokens": 384},
    }
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/workflow-mq63n60i/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "question": "问题描述",
            "function_point": "功能点",
        }
    }


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


def test_analyze_screenshot_sends_runtime_request_and_parses_answer() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": (
                    "{\n"
                    '  "title": "在线编辑跑版",\n'
                    '  "group_name": "在线编辑群",\n'
                    '  "environment": "未知",\n'
                    '  "product_line": "",\n'
                    '  "ticket_type": "排查类",\n'
                    '  "current_summary": "传参后仍跑版",\n'
                    '  "timeline_entry": "待确认 previewMode 参数"\n'
                    "}"
                ),
                "trace_id": "trace_xxx",
                "usage": {"total_tokens": 384},
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    payload = client.analyze_screenshot(
        image_data_url=["data:image/png;base64,YWFh", "data:image/png;base64,YmJi"],
        summary="待办标题: 在线编辑跑版\n压缩上下文:\n问题概述: 传参后仍跑版",
        summary_type="problem_conclusion",
    )

    assert payload["result"]["title"] == "在线编辑跑版"
    assert payload["trace_id"] == "trace_xxx"
    assert payload["usage"] == {"total_tokens": 384}
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/single-turn-mpmfi35y/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "imags": [
                {
                    "type": "image",
                    "name": "image-1.png",
                    "mime_type": "image/png",
                    "size": 3,
                    "data_url": "data:image/png;base64,YWFh",
                },
                {
                    "type": "image",
                    "name": "image-2.png",
                    "mime_type": "image/png",
                    "size": 3,
                    "data_url": "data:image/png;base64,YmJi",
                },
            ],
            "summary": "待办标题: 在线编辑跑版\n压缩上下文:\n问题概述: 传参后仍跑版",
            "summary_type": "problem_conclusion",
        }
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_generate_stage_summary_sends_single_turn_request_and_returns_answer() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": "### 阶段现状\n- 已收集客户反馈",
                "trace_id": "trace_stage",
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    answer = client.generate_stage_summary(
        current_markdown="已有总结",
        stage_materials="阶段材料",
        task_title="测试待办",
        stage_name="当前阶段",
        stage_goal="整理客户反馈",
    )

    assert answer == "### 阶段现状\n- 已收集客户反馈"
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/single-turn-mpmrkccz/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "current_markdown": "已有总结",
            "stage_materials": "阶段材料",
            "task_title": "测试待办",
            "stage_name": "当前阶段",
            "stage_goal": "整理客户反馈",
        }
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_generate_stage_summary_accepts_nested_runtime_answer() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "data": {
                    "outputs": {
                        "answer": "### 嵌套结果\n- 服务端已返回",
                    }
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

    answer = client.generate_stage_summary(
        current_markdown="",
        stage_materials="阶段材料",
        task_title="测试待办",
        stage_name="当前阶段",
        stage_goal="整理客户反馈",
    )

    assert answer == "### 嵌套结果\n- 服务端已返回"


def test_polish_timeline_content_sends_single_turn_request_and_returns_summary_detail() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": json.dumps(
                    {
                        "summary": "整理后的摘要",
                        "detail": "整理后的详情",
                    },
                    ensure_ascii=False,
                ),
                "trace_id": "trace_polish",
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    result = client.polish_timeline_content(content="零碎内容")

    assert result == {"summary": "整理后的摘要", "detail": "整理后的详情"}
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/single-turn-mqck3wdm/run"
    assert session.calls[0]["json"] == {"variables": {"content": "零碎内容"}}
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_polish_timeline_content_rejects_empty_result() -> None:
    session = _FakeSession(_FakeResponse(200, {"answer": json.dumps({}, ensure_ascii=False)}))
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(ChattodoServerError, match="摘要或详情"):
        client.polish_timeline_content(content="零碎内容")


def test_translate_image_text_blocks_sends_single_turn_request_and_parses_answer() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": json.dumps(
                    {
                        "translations": [
                            "Server Connection",
                            "Save the server address and API key first",
                        ]
                    },
                    ensure_ascii=False,
                ),
                "trace_id": "trace_translate",
                "usage": {"total_tokens": 384},
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    result = client.translate_image_text_blocks(
        source_lang="zh",
        target_lang="en",
        texts=["服务端连接", "先保存服务端地址和 API Key"],
    )

    assert result == {
        "translations": [
            "Server Connection",
            "Save the server address and API key first",
        ],
        "trace_id": "trace_translate",
        "usage": {"total_tokens": 384},
    }
    assert session.calls[0]["method"] == "POST"
    assert session.calls[0]["url"] == "https://server.example.com/api/runtime/apps/single-turn-mqd7ce05/run"
    assert session.calls[0]["json"] == {
        "variables": {
            "text": json.dumps(
                {
                    "source_lang": "zh",
                    "target_lang": "en",
                    "texts": ["服务端连接", "先保存服务端地址和 API Key"],
                },
                ensure_ascii=False,
            )
        }
    }
    assert session.calls[0]["headers"] == {"X-API-Key": "server-key", "Content-Type": "application/json"}
    assert session.calls[0]["timeout"] == 12


def test_translate_image_text_blocks_rejects_count_mismatch() -> None:
    session = _FakeSession(
        _FakeResponse(
            200,
            {
                "answer": json.dumps({"translations": ["only one"]}, ensure_ascii=False),
            },
        )
    )
    client = ChattodoServerClient(
        base_url="https://server.example.com/",
        api_key="server-key",
        timeout_seconds=12,
        session=session,  # type: ignore[arg-type]
    )

    with pytest.raises(ChattodoServerError, match="数量与请求文本数量不一致"):
        client.translate_image_text_blocks(
            source_lang="zh",
            target_lang="en",
            texts=["a", "b"],
        )


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

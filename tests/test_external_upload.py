import importlib.util
from pathlib import Path


def _load_external_upload_module():
    module_path = Path(__file__).resolve().parents[1] / "ext_script" / "external_upload.py"
    spec = importlib.util.spec_from_file_location("external_upload", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_event(event_type: str = "created") -> dict:
    return {
        "event_type": event_type,
        "todo_id": "26182fc3-0b8b-451b-aec9-a01152b08eb8",
        "todo_snapshot": {
            "id": "26182fc3-0b8b-451b-aec9-a01152b08eb8",
            "title": "上传失败",
            "current_summary": "客户反馈上传失败，需要排查",
            "summary_fields": {"group_name": "客户群-A"},
            "timeline": [
                {
                    "id": "evt-1",
                    "timestamp": "2026-04-10T14:52:59",
                    "kind": "analysis",
                    "scenario": "工单待办助手",
                    "content": "检查日志后定位到接口超时",
                    "attachments": [],
                },
                {
                    "id": "evt-2",
                    "timestamp": "2026-04-10T15:10:00",
                    "kind": "analysis",
                    "scenario": "工单待办助手",
                    "content": "调整配置后重新验证通过",
                    "attachments": [],
                },
            ],
        },
        "delta": {
            "timeline_event": {
                "id": "evt-2",
                "timestamp": "2026-04-10T15:10:00",
                "kind": "analysis",
                "scenario": "工单待办助手",
                "content": "调整配置后重新验证通过",
                "attachments": [],
            }
        },
        "bindings": [
            {
                "integration_id": "company-platform",
                "external_id": "uuid_timestamp",
                "external_url": "http://127.0.0.1:5000/",
            }
        ],
    }


def test_extract_raw_data_supports_current_todo_domain_event():
    module = _load_external_upload_module()

    raw_data = module._extract_raw_data(_build_event())

    assert raw_data == {
        "客户群": "客户群-A",
        "描述": "上传失败",
        "解决过程": "调整配置后重新验证通过",
    }


def test_process_event_created_only_pushes_description_and_group(monkeypatch):
    module = _load_external_upload_module()
    captured = {}

    def fake_add_data(data):
        captured["payload"] = data
        return {"status": "success", "message": "添加成功", "id": "uuid_timestamp"}

    monkeypatch.setattr(module, "add_data", fake_add_data)

    result = module.process_event(_build_event("created"))

    assert result["ok"] is True
    assert result["action"] == "created"
    assert result["external_id"] == "uuid_timestamp"
    assert captured["payload"] == {
        "描述": "上传失败",
        "客户群": "客户群-A",
        "备注": "[AICA同步]",
    }


def test_process_event_completed_updates_with_ai_summary(monkeypatch):
    module = _load_external_upload_module()
    captured = {}

    def fake_summary(raw_data, timeline_contents):
        captured["summary_inputs"] = {
            "raw_data": raw_data,
            "timeline_contents": timeline_contents,
        }
        return "已根据时间线完成排查并调整配置，验证后问题解决。"

    def fake_update_data(data):
        captured["payload"] = data
        return {"status": "success", "message": "修改成功"}

    monkeypatch.setattr(module, "summarize_timeline_with_ai", fake_summary)
    monkeypatch.setattr(module, "update_data", fake_update_data)

    result = module.process_event(_build_event("completed"))

    assert result["ok"] is True
    assert result["action"] == "updated"
    assert result["external_id"] == "uuid_timestamp"
    assert captured["summary_inputs"]["timeline_contents"] == [
        "检查日志后定位到接口超时",
        "调整配置后重新验证通过",
    ]
    assert captured["payload"] == {
        "id": "uuid_timestamp",
        "描述": "上传失败",
        "解决过程": "已根据时间线完成排查并调整配置，验证后问题解决。",
        "具体工作内容": "已根据时间线完成排查并调整配置，验证后问题解决。",
        "客户群": "客户群-A",
        "结果/进展": "已完成",
        "备注": "[AICA同步]",
    }


def test_process_event_deleted_uses_external_id(monkeypatch):
    module = _load_external_upload_module()
    captured = {}

    def fake_delete_data(data):
        captured["payload"] = data
        return {"status": "success", "message": "删除成功"}

    monkeypatch.setattr(module, "delete_data", fake_delete_data)

    result = module.process_event(_build_event("deleted"))

    assert result["ok"] is True
    assert result["action"] == "deleted"
    assert result["external_id"] == "uuid_timestamp"
    assert captured["payload"] == {"id": "uuid_timestamp"}

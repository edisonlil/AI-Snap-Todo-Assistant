"""AICA 外部集成脚本示例。

这个脚本专门作为“模板 + 演示”使用，目标是让别人一眼看懂：
1. AICA 会以什么格式把事件传给外部脚本
2. 外部脚本应该如何回传结果
3. external_id 是怎么来的、为什么后续事件还能继续用

调用方式：
- AICA 会把一个 TodoDomainEvent JSON 写到 stdin
- 脚本处理完成后，可向 stdout 输出一段 JSON 回执
- stderr 只会被 AICA 当作日志，不会当成回执

external_id 说明：
- external_id 表示“外部系统里的那条记录 ID”
- 真实接入时，通常在 created 事件里调用外部平台创建工单/任务
- 外部平台返回的工单 ID，就是这里要回传给 AICA 的 external_id
- AICA 收到后会把它保存到 ~/.aica/todo_bindings.json
- 后续 appended / completed / deleted 事件里，AICA 会把这个绑定信息放到 event["bindings"] 里再传回来

这个示例脚本的行为：
- 不接第三方平台，只把收到的事件写入脚本目录下的 logs/ 文件夹
- created 事件会生成一个演示用的 external_id，方便观察完整绑定流程
- 后续事件如果已经有 binding，就直接复用已有的 external_id
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


INTEGRATION_ID = os.environ.get("AICA_INTEGRATION_ID", "")
EVENT_TYPE = os.environ.get("AICA_TODO_EVENT_TYPE", "")
DEFAULT_LOG_DIR = Path(__file__).resolve().parent / "logs"


def resolve_log_dir() -> Path:
    """日志目录固定为脚本同级的 logs/，避免让用户额外配置环境变量。"""
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_LOG_DIR


def current_binding(event: dict[str, Any]) -> dict[str, Any] | None:
    """从事件里找出当前 integration 对应的 binding。"""
    for item in event.get("bindings", []):
        if item.get("integration_id") == INTEGRATION_ID:
            return item
    return None


def write_event_log(log_dir: Path, event: dict[str, Any]) -> Path:
    """把收到的事件完整写入日志文件，便于排查和演示。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    todo_id = str(event.get("todo_id") or "unknown")
    event_type = str(event.get("event_type") or "unknown")
    file_path = log_dir / f"{timestamp}_{event_type}_{todo_id}.json"
    payload = {
        "received_at": datetime.now().isoformat(),
        "integration_id": INTEGRATION_ID,
        "env_event_type": EVENT_TYPE,
        "event": event,
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path


def build_demo_external_id(event: dict[str, Any]) -> str:
    """构造一个演示用 external_id，方便观察绑定流程。"""
    todo_id = str(event.get("todo_id") or "").replace("-", "").upper()
    suffix = todo_id[:8] or datetime.now().strftime("%H%M%S")
    return f"DEMO-{suffix}"


def main() -> int:
    event = json.load(sys.stdin)
    event_type = str(event.get("event_type") or "")
    binding = current_binding(event)
    log_dir = resolve_log_dir()
    log_file = write_event_log(log_dir, event)

    ack: dict[str, Any] = {
        "ok": True,
        "integration_id": INTEGRATION_ID,
        "metadata": {
            "log_dir": str(log_dir),
            "log_file": str(log_file),
            "demo_script": True,
        },
    }

    if event_type == "created":
        # 演示模式下没有真实外部平台，这里手工生成一个 external_id。
        # AICA 收到后会把它保存下来，后续事件就能通过 bindings 再拿到它。
        demo_external_id = build_demo_external_id(event)
        ack.update(
            {
                "action": "created",
                "external_id": demo_external_id,
                "external_url": f"file:///{log_file.as_posix()}",
                "message": "已写入日志，并回传演示 external_id",
            }
        )
    else:
        # 后续事件通常会带上之前保存过的 binding。
        # 如果已经有 external_id，这里继续原样带回，方便别人理解整条链路。
        ack.update(
            {
                "action": "logged",
                "message": "已写入日志",
            }
        )
        if binding and binding.get("external_id"):
            ack["external_id"] = str(binding["external_id"])
            if binding.get("external_url"):
                ack["external_url"] = str(binding["external_url"])

    print(json.dumps(ack, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.app_notifications import AppNotificationBridge


def _build_bridge() -> AppNotificationBridge:
    return AppNotificationBridge(auto_dismiss_scheduler=lambda _ms, _callback: None)


def test_notify_exposes_notification_payload() -> None:
    bridge = _build_bridge()

    bridge.notify("success", "保存完成")

    notifications = bridge.notifications
    assert len(notifications) == 1
    assert notifications[0]["level"] == "success"
    assert notifications[0]["message"] == "保存完成"
    assert notifications[0]["durationMs"] == 2200
    assert notifications[0]["id"]


def test_notify_keeps_only_latest_three_notifications() -> None:
    bridge = _build_bridge()

    bridge.notify("info", "第1条")
    bridge.notify("info", "第2条")
    bridge.notify("info", "第3条")
    bridge.notify("info", "第4条")

    assert [item["message"] for item in bridge.notifications] == ["第2条", "第3条", "第4条"]


def test_notify_uses_level_default_durations() -> None:
    bridge = _build_bridge()

    bridge.notify("info", "普通通知")
    bridge.notify("warning", "风险提醒")
    bridge.notify("error", "出错了")

    durations = [item["durationMs"] for item in bridge.notifications]
    assert durations == [2200, 3200, 4200]


def test_dismiss_and_clear_remove_notifications() -> None:
    bridge = _build_bridge()
    first_id = bridge.notify("info", "第一条")
    bridge.notify("success", "第二条")

    bridge.dismiss(first_id)
    assert [item["message"] for item in bridge.notifications] == ["第二条"]

    bridge.clear()
    assert bridge.notifications == []

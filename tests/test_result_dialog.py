from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.result_dialog import _ResultDialogBridge
from aica.storage.contracts import ProjectMatchResult


def _build_snapshot() -> TicketSnapshot:
    return TicketSnapshot(
        title="\u6d4b\u8bd5\u5f85\u529e",
        fields=TicketSummaryFields(),
        current_summary="\u5f53\u524d\u63cf\u8ff0",
        timeline_entry="\u521d\u59cb\u7ed3\u8bba",
    )


def test_result_dialog_edit_keeps_trailing_space_until_save() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
    )

    bridge.updateField("timeline_entry", "\u521d\u59cb\u7ed3\u8bba ")

    assert bridge.recognitionConclusion == "\u521d\u59cb\u7ed3\u8bba "
    assert bridge.build_snapshot().timeline_entry == "\u521d\u59cb\u7ed3\u8bba"


def test_result_dialog_saves_without_product_line_requirement() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
    )
    saved: list[bool] = []
    bridge.saveRequested.connect(lambda: saved.append(True))

    bridge.saveDialog()

    assert saved == [True]
    assert bridge.productLineError == ""


def test_result_dialog_keeps_existing_product_line_in_snapshot() -> None:
    bridge = _ResultDialogBridge(
        result=TicketSnapshot(
            title="\u6d4b\u8bd5\u5f85\u529e",
            fields=TicketSummaryFields(product_line="协作套件"),
            current_summary="\u5f53\u524d\u63cf\u8ff0",
            timeline_entry="\u521d\u59cb\u7ed3\u8bba",
        ),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
    )

    assert bridge.build_snapshot().fields.product_line == "协作套件"


def test_result_dialog_saves_issue_product() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
    )
    saved: list[bool] = []
    bridge.saveRequested.connect(lambda: saved.append(True))

    bridge.updateField("issue_product", "产品A/模块B/功能C")
    bridge.saveDialog()

    assert saved == [True]
    assert bridge.issueProduct == "产品A/模块B/功能C"
    assert bridge.build_snapshot().fields.issue_product == "产品A/模块B/功能C"


def test_result_dialog_normalizes_issue_product_path_segments() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
    )

    bridge.updateField("issue_product", "产品A / 模块B ／ 功能C")

    assert bridge.issueProduct == "产品A/模块B/功能C"
    assert bridge.build_snapshot().fields.issue_product == "产品A/模块B/功能C"


def test_result_dialog_does_not_require_product_line_when_group_has_no_project_match() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
    )
    saved: list[bool] = []
    bridge.saveRequested.connect(lambda: saved.append(True))

    bridge.saveDialog()

    assert saved == [True]
    assert bridge.productLineError == ""


def test_result_dialog_defaults_issue_product_from_matched_project_history() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_match_provider=lambda group_name: ProjectMatchResult(status="matched", project_id="project-1") if group_name == "测试群" else ProjectMatchResult(status="unmatched"),
        latest_issue_product_provider=lambda project_id: "产品A/模块B/功能C" if project_id == "project-1" else "",
    )

    bridge.updateField("group_name", "测试群")

    assert bridge.issueProduct == "产品A/模块B/功能C"


def test_result_dialog_defaults_environment_from_matched_project_history() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_match_provider=lambda group_name: ProjectMatchResult(status="matched", project_id="project-1") if group_name == "测试群" else ProjectMatchResult(status="unmatched"),
        latest_environment_provider=lambda project_id: "正式环境" if project_id == "project-1" else "",
    )

    bridge.updateField("group_name", "测试群")

    assert bridge.environment == "正式环境"


def test_result_dialog_initial_group_name_applies_issue_product_default() -> None:
    bridge = _ResultDialogBridge(
        result=TicketSnapshot(
            title="\u6d4b\u8bd5\u5f85\u529e",
            fields=TicketSummaryFields(group_name="测试群"),
            current_summary="\u5f53\u524d\u63cf\u8ff0",
            timeline_entry="\u521d\u59cb\u7ed3\u8bba",
        ),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_match_provider=lambda group_name: ProjectMatchResult(status="matched", project_id="project-1") if group_name == "测试群" else ProjectMatchResult(status="unmatched"),
        latest_issue_product_provider=lambda project_id: "产品A/模块B/功能C" if project_id == "project-1" else "",
    )

    assert bridge.issueProduct == "产品A/模块B/功能C"


def test_result_dialog_manual_environment_is_not_overwritten_by_default() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_match_provider=lambda group_name: ProjectMatchResult(status="matched", project_id="project-1") if group_name == "测试群" else ProjectMatchResult(status="unmatched"),
        latest_environment_provider=lambda project_id: "正式环境" if project_id == "project-1" else "",
    )

    bridge.updateField("environment", "测试环境")
    bridge.updateField("group_name", "测试群")

    assert bridge.environment == "测试环境"


def test_result_dialog_single_candidate_applies_issue_product_default() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_match_provider=lambda _group_name: ProjectMatchResult(status="conflict", reason="multiple_active_projects"),
        project_candidate_provider=lambda group_name: [
            {
                "projectId": "project-1",
                "projectName": "Demo Project",
                "taskOrderNo": "WO-001",
                "customerName": "Demo Customer",
                "matchedAlias": "测试群",
                "matchReason": "alias_exact",
                "matchScore": 320,
                "isExpired": False,
                "projectSnapshot": {"project_name": "Demo Project"},
            }
        ] if group_name == "测试群" else [],
        latest_issue_product_provider=lambda project_id: "产品A/模块B/功能C" if project_id == "project-1" else "",
    )

    bridge.updateField("group_name", "测试群")

    assert bridge.issueProduct == "产品A/模块B/功能C"


def test_result_dialog_single_candidate_applies_environment_default() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_match_provider=lambda _group_name: ProjectMatchResult(status="conflict", reason="multiple_active_projects"),
        project_candidate_provider=lambda group_name: [
            {
                "projectId": "project-1",
                "projectName": "Demo Project",
                "taskOrderNo": "WO-001",
                "customerName": "Demo Customer",
                "matchedAlias": "测试群",
                "matchReason": "alias_exact",
                "matchScore": 320,
                "isExpired": False,
                "projectSnapshot": {"project_name": "Demo Project"},
            }
        ] if group_name == "测试群" else [],
        latest_environment_provider=lambda project_id: "正式环境" if project_id == "project-1" else "",
    )

    bridge.updateField("group_name", "测试群")

    assert bridge.environment == "正式环境"


def test_result_dialog_group_name_without_unique_match_keeps_issue_product_empty() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_match_provider=lambda _group_name: ProjectMatchResult(status="conflict", reason="multiple_active_projects"),
        latest_issue_product_provider=lambda _project_id: "产品A/模块B/功能C",
    )

    bridge.updateField("group_name", "匹配群")

    assert bridge.issueProduct == ""


def test_result_dialog_manual_issue_product_is_not_overwritten_by_default() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_match_provider=lambda group_name: ProjectMatchResult(status="matched", project_id="project-1") if group_name == "测试群" else ProjectMatchResult(status="unmatched"),
        latest_issue_product_provider=lambda project_id: "产品A/模块B/功能C" if project_id == "project-1" else "",
    )

    bridge.updateField("issue_product", "手工填写值")
    bridge.updateField("group_name", "测试群")

    assert bridge.issueProduct == "手工填写值"


def test_result_dialog_selecting_project_candidate_persists_project_link() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_candidate_provider=lambda group_name: [
            {
                "projectId": "project-1",
                "projectName": "Demo Project",
                "taskOrderNo": "WO-001",
                "customerName": "Demo Customer",
                "matchedAlias": "测试群",
                "matchReason": "project_name_match",
                "matchScore": 320,
                "isExpired": False,
                "projectSnapshot": {
                    "project_name": "Demo Project",
                    "task_order_no": "WO-001",
                    "customer_name": "Demo Customer",
                    "product_line": "WPS协作",
                    "product_version": "v1",
                },
            }
        ] if group_name == "测试群" else [],
        latest_issue_product_provider=lambda project_id: "产品A/模块B/功能C" if project_id == "project-1" else "",
    )

    bridge.updateField("group_name", "测试群")
    bridge.chooseProjectCandidate(
        {
            "projectId": "project-1",
        }
    )

    snapshot = bridge.build_snapshot()

    assert bridge.hasProjectCandidateSelection is True
    assert bridge.groupName == "测试群"
    assert bridge.projectCandidates[0]["projectId"] == "project-1"
    assert bridge.environment == "未知"
    assert bridge.issueProduct == "产品A/模块B/功能C"
    assert snapshot.project_link["project_id"] == "project-1"
    assert snapshot.project_link["match_status"] == "manual"
    assert snapshot.project_link["project_snapshot"]["project_name"] == "Demo Project"


def test_result_dialog_selecting_project_candidate_falls_back_to_project_name() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        project_candidate_provider=lambda group_name: [
            {
                "projectId": "project-2",
                "projectName": "广州项目",
                "taskOrderNo": "WO-002",
                "customerName": "Demo Customer",
                "matchedAlias": "",
                "matchReason": "project_name_match",
                "matchScore": 280,
                "isExpired": False,
                "projectSnapshot": {
                    "project_name": "广州项目",
                    "task_order_no": "WO-002",
                    "customer_name": "Demo Customer",
                    "product_line": "WPS协作",
                },
            }
        ] if group_name == "广州" else [],
    )

    bridge.updateField("group_name", "广州")
    bridge.chooseProjectCandidate(
        {
            "projectId": "project-2",
        }
    )

    assert bridge.groupName == "广州项目"


def test_result_dialog_issue_product_field_uses_text_input() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "ResultDialog.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "import QtQuick.Controls" in qml_text
    assert "id: issueProductEdit" in qml_text
    assert "issueProductEdit.text = resultDialogBridge.issueProduct" in qml_text
    assert 'text: "\\u95ee\\u9898\\u6240\\u5c5e\\u4ea7\\u54c1"' in qml_text
    assert 'onTextChanged: root.pushField("issue_product", text)' in qml_text
    assert "selectByMouse: true" in qml_text
    assert "id: productLineEdit" not in qml_text
    assert "&& !resultDialogBridge.hasProjectCandidateSelection" in qml_text
    assert "反馈修正" not in qml_text
    assert r"\u53cd\u9988\u4fee\u6b63" not in qml_text
    assert "feedbackDialog" not in qml_text

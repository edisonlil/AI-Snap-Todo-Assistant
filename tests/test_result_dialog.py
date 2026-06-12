from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.models import TicketSnapshot, TicketSummaryFields
from aica.result_dialog import _ResultDialogBridge


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


def test_result_dialog_defaults_and_saves_when_multiple_product_lines_exist() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        product_line_options_provider=lambda group_name: ["文档中台, 协作套件"] if group_name == "测试群" else [],
    )
    bridge.updateField("group_name", "测试群")
    saved: list[bool] = []
    bridge.saveRequested.connect(lambda: saved.append(True))

    bridge.saveDialog()

    assert saved == [True]
    assert bridge.productLineOptions == ["文档中台", "协作套件"]
    assert bridge.productLine == "文档中台"
    assert bridge.productLineError == ""


def test_result_dialog_saves_selected_product_line() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        product_line_options_provider=lambda group_name: ["文档中台, 协作套件"] if group_name == "测试群" else [],
    )
    bridge.updateField("group_name", "测试群")
    saved: list[bool] = []
    bridge.saveRequested.connect(lambda: saved.append(True))

    bridge.updateField("product_line", "协作套件")
    bridge.saveDialog()

    assert saved == [True]
    assert bridge.build_snapshot().fields.product_line == "协作套件"
    assert bridge.productLineError == ""


def test_result_dialog_does_not_require_product_line_when_group_has_no_project_match() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        product_line_options_provider=lambda group_name: [],
    )
    saved: list[bool] = []
    bridge.saveRequested.connect(lambda: saved.append(True))

    bridge.saveDialog()

    assert saved == [True]
    assert bridge.productLineOptions == []
    assert bridge.productLineError == ""


def test_result_dialog_defaults_single_product_line() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        product_line_options_provider=lambda group_name: ["私网文档中台"],
    )

    assert bridge.productLine == "私网文档中台"


def test_result_dialog_rematches_product_lines_after_group_name_edit() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        product_line_options_provider=lambda group_name: ["私网WPS协作, 私网文档中台"] if group_name == "匹配群" else [],
        default_product_line_provider=lambda group_name, options: "私网文档中台",
    )

    assert bridge.productLineOptions == []
    assert bridge.productLine == ""

    bridge.updateField("group_name", "匹配群")

    assert bridge.productLineOptions == ["私网WPS协作", "私网文档中台"]
    assert bridge.productLine == "私网文档中台"


def test_result_dialog_defaults_most_used_product_line() -> None:
    bridge = _ResultDialogBridge(
        result=_build_snapshot(),
        scenario="\u5de5\u5355\u8ddf\u8fdb",
        model="test-model",
        product_line_options_provider=lambda group_name: ["私网WPS协作, 私网文档中台, 私网文档中台"],
        default_product_line_provider=lambda group_name, options: "私网文档中台",
    )

    assert bridge.productLine == "私网文档中台"


def test_result_dialog_product_line_field_uses_combo_box() -> None:
    qml_path = Path(__file__).resolve().parents[1] / "src" / "aica" / "qml" / "ResultDialog.qml"
    qml_text = qml_path.read_text(encoding="utf-8")

    assert "import QtQuick.Controls" in qml_text
    assert "id: productLineEdit" in qml_text
    assert "productLineEdit.currentIndex = root.optionIndex" in qml_text
    assert "model: resultDialogBridge.productLineOptions" in qml_text
    assert "请选择产品线" in qml_text
    assert "delegate: ItemDelegate" in qml_text
    assert "popup: Popup" in qml_text
    assert "enabled: resultDialogBridge.productLineOptions.length > 1" in qml_text
    assert "未匹配项目" in qml_text
    assert "反馈修正" not in qml_text
    assert r"\u53cd\u9988\u4fee\u6b63" not in qml_text
    assert "feedbackDialog" not in qml_text

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
        show_feedback=False,
    )

    bridge.updateField("timeline_entry", "\u521d\u59cb\u7ed3\u8bba ")

    assert bridge.recognitionConclusion == "\u521d\u59cb\u7ed3\u8bba "
    assert bridge.build_snapshot().timeline_entry == "\u521d\u59cb\u7ed3\u8bba"


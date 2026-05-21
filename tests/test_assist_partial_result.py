from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_todo_detail_panel import _build_bridge, _build_todo  # noqa: E402


def test_apply_assist_analysis_partial_result_keeps_loading_until_final() -> None:
    bridge = _build_bridge(Path("unused"))
    bridge.set_todo(_build_todo())
    bridge._assist_analysis_pending_request_id = "req-partial"  # noqa: SLF001
    bridge._assist_analysis_pending_cache_key = "cache-partial"  # noqa: SLF001
    bridge._assist_analysis_busy = True  # noqa: SLF001

    assert bridge.apply_assist_analysis_result(
        "todo-1",
        "req-partial",
        {
            "summary": "partial summary",
            "caseResults": {"status": "loading", "items": []},
            "isFinal": False,
        },
    ) is True
    assert bridge.assistAnalysisBusy is True
    assert bridge.assistAnalysisSummary == "partial summary"
    assert bridge._assist_analysis_pending_request_id == "req-partial"  # noqa: SLF001

    assert bridge.apply_assist_analysis_result(
        "todo-1",
        "req-partial",
        {
            "summary": "final summary",
            "caseResults": {"status": "success", "items": [{"title": "Case A", "score": 81}]},
            "isFinal": True,
        },
    ) is True
    assert bridge.assistAnalysisBusy is False
    assert bridge.assistAnalysisSummary == "final summary"
    assert bridge._assist_analysis_pending_request_id == ""  # noqa: SLF001

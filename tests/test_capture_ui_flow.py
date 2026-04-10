from aica.capture_session import CaptureSession
from aica.capture_ui_flow import CaptureUiFlow


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class _Overlay:
    def __init__(self, name: str):
        self.name = name
        self.selection_complete = _Signal()
        self.selection_changed = _Signal()
        self.cancelled = _Signal()
        self.visible = False
        self.actions: list[str] = []
        self.selection = "rect"
        self.capture = _Pixmap()

    def hide(self):
        self.actions.append("hide")

    def deleteLater(self):
        self.actions.append("delete")

    def show_overlay(self):
        self.visible = True
        self.actions.append("show_overlay")

    def suspend_overlay(self):
        self.actions.append("suspend")

    def dismiss_overlay(self):
        self.visible = False
        self.actions.append("dismiss")

    def lock_selection(self):
        self.actions.append("lock")

    def raise_(self):
        self.actions.append("raise")

    def resume_overlay(self):
        self.actions.append("resume")

    def set_edit_mode(self, mode: str):
        self.actions.append(f"mode:{mode}")

    def isVisible(self):
        return self.visible

    def has_selection(self):
        return True

    def current_global_selection(self):
        return self.selection

    def export_selection_pixmap(self):
        return self.capture


class _Pixmap:
    def isNull(self):
        return False


class _Panel:
    def __init__(self):
        self.hidden = 0

    def hide(self):
        self.hidden += 1


class _Toolbar:
    def __init__(self):
        self.attached_overlay = None
        self.edit_modes: list[str] = []
        self.multi_modes: list[int] = []
        self.single_mode_calls = 0
        self.reset_analysis_inputs_calls = 0
        self.hidden = 0
        self.shown_at = []
        self.loading = False

    def attach_to_overlay(self, overlay):
        self.attached_overlay = overlay

    def set_edit_mode(self, mode: str):
        self.edit_modes.append(mode)

    def set_multi_capture_mode(self, count: int):
        self.multi_modes.append(count)

    def set_single_capture_mode(self):
        self.single_mode_calls += 1

    def reset_analysis_inputs(self):
        self.reset_analysis_inputs_calls += 1

    def hide(self):
        self.hidden += 1

    def show_at(self, rect):
        self.shown_at.append(rect)

    def is_loading(self):
        return self.loading


def _build_flow():
    toolbar = _Toolbar()
    session = CaptureSession()
    flow = CaptureUiFlow(
        toolbar=toolbar,
        todo_panel=_Panel(),
        todo_detail_panel=_Panel(),
        capture_session=session,
    )
    return flow, toolbar, session


def test_rebuild_overlays_wires_callbacks_and_replaces_previous():
    flow, _, _ = _build_flow()
    old_overlay = _Overlay("old")
    flow._overlays = [old_overlay]

    flow.rebuild_overlays(
        ["screen-1", "screen-2"],
        overlay_factory=_Overlay,
        on_selection_complete=lambda *args: None,
        on_selection_changed=lambda *args: None,
        on_cancel=lambda: None,
    )

    assert old_overlay.actions == ["hide", "delete"]
    assert len(flow.overlays) == 2
    assert len(flow.overlays[0].selection_complete.callbacks) == 1


def test_handle_selection_complete_switches_active_overlay_and_toolbar():
    flow, toolbar, session = _build_flow()
    first = _Overlay("first")
    second = _Overlay("second")
    flow._overlays = [first, second]

    flow.handle_selection_complete(second, "rect-2", "capture-2")

    assert session.active_overlay is second
    assert session.current_selection == "rect-2"
    assert session.current_capture == "capture-2"
    assert toolbar.attached_overlay is second
    assert second.actions[:2] == ["lock", "raise"]
    assert "dismiss" in first.actions


def test_restore_toolbar_uses_multi_capture_mode_when_queue_exists():
    flow, toolbar, session = _build_flow()
    overlay = _Overlay("active")
    overlay.selection = "rect-2"

    session.active_overlay = overlay
    session.queued_captures = ["capture-1"]
    session.current_selection = "rect-2"
    session.current_capture = "capture-2"

    flow.restore_toolbar_for_current_capture()

    assert overlay.actions[:2] == ["resume", "mode:move"]
    assert toolbar.multi_modes == [2]
    assert toolbar.shown_at == ["rect-2"]


def test_clear_capture_state_resets_session_and_hides_toolbar():
    flow, toolbar, session = _build_flow()
    flow._overlays = [_Overlay("active")]
    refreshed = {"count": 0}

    session.current_selection = "rect"
    session.current_capture = "capture"
    session.active_overlay = flow._overlays[0]
    session.queued_captures = ["queued"]

    flow.clear_capture_state(lambda: refreshed.__setitem__("count", refreshed["count"] + 1))

    assert session.current_selection is None
    assert session.current_capture is None
    assert session.active_overlay is None
    assert session.queued_captures == []
    assert toolbar.single_mode_calls == 1
    assert toolbar.reset_analysis_inputs_calls == 1
    assert toolbar.hidden == 1
    assert refreshed["count"] == 1


def test_release_capture_mode_preserves_queue_and_waits_for_next_hotkey():
    flow, toolbar, session = _build_flow()
    overlay = _Overlay("active")
    flow._overlays = [overlay]
    refreshed = {"count": 0}

    session.current_selection = "rect"
    session.current_capture = None
    session.active_overlay = overlay
    session.queued_captures = ["queued"]

    flow.release_capture_mode(lambda: refreshed.__setitem__("count", refreshed["count"] + 1))

    assert session.current_selection is None
    assert session.current_capture is None
    assert session.active_overlay is None
    assert session.queued_captures == ["queued"]
    assert toolbar.attached_overlay is None
    assert toolbar.hidden == 1
    assert overlay.actions == ["dismiss"]
    assert refreshed["count"] == 1

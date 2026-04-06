from aica.capture_session import CaptureSession


class _FakePixmap:
    def __init__(self, *, is_null: bool = False):
        self._is_null = is_null

    def isNull(self) -> bool:  # noqa: N802
        return self._is_null


class _FakeOverlay:
    def __init__(self, *, has_selection: bool, selection=None, capture=None):
        self._has_selection = has_selection
        self._selection = selection
        self._capture = capture or _FakePixmap()

    def has_selection(self) -> bool:
        return self._has_selection

    def current_global_selection(self):
        return self._selection

    def export_selection_pixmap(self):
        return self._capture


def test_sync_from_active_overlay_updates_selection_and_capture():
    session = CaptureSession(active_overlay=_FakeOverlay(has_selection=True, selection="rect-1"))

    assert session.sync_from_active_overlay()
    assert session.current_selection == "rect-1"
    assert session.current_capture is not None


def test_sync_from_active_overlay_returns_false_for_null_capture():
    session = CaptureSession(
        active_overlay=_FakeOverlay(
            has_selection=True,
            selection="rect-1",
            capture=_FakePixmap(is_null=True),
        )
    )

    assert not session.sync_from_active_overlay()


def test_queue_current_capture_moves_capture_into_session():
    session = CaptureSession(
        active_overlay=_FakeOverlay(has_selection=True, selection="rect-1", capture=_FakePixmap())
    )

    assert session.queue_current_capture()
    assert session.current_selection is None
    assert session.current_capture is None
    assert session.active_overlay is None
    assert len(session.queued_captures) == 1


def test_images_for_analysis_preserves_capture_order():
    session = CaptureSession(
        current_capture="capture-2",
        queued_captures=["capture-0", "capture-1"],
    )

    assert session.images_for_analysis() == ["capture-0", "capture-1", "capture-2"]


def test_clear_resets_all_capture_state():
    session = CaptureSession(
        current_selection="rect-1",
        current_capture="capture-1",
        active_overlay=object(),
        queued_captures=["capture-0"],
    )

    session.clear()

    assert session.current_selection is None
    assert session.current_capture is None
    assert session.active_overlay is None
    assert session.queued_captures == []

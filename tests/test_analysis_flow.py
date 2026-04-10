from types import SimpleNamespace

from aica.analysis_flow import AnalysisFlowCoordinator
from aica.analysis_intent import build_analysis_intent


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class _Worker:
    def __init__(self, payload, **kwargs):
        self.payload = payload
        self.kwargs = kwargs
        self.finished = _Signal()
        self.error = _Signal()
        self.parse_error = _Signal()
        self.started = False
        self._feedback_image_base64 = "img-b64"
        self._analysis_stats = "analysis-stats"

    def start(self):
        self.started = True


class _Toolbar:
    def __init__(self):
        self.hidden = 0
        self.loading_states = []

    def hide(self):
        self.hidden += 1

    def set_loading(self, value: bool):
        self.loading_states.append(value)


class _CaptureSession:
    def __init__(self, *, sync_result=True, images=None):
        self.sync_result = sync_result
        self.images = images or []

    def sync_from_active_overlay(self):
        return self.sync_result

    def images_for_analysis(self):
        return list(self.images)


def _config():
    class _LLMService:
        def describe_task_model(self, task_name):
            return f"provider/{task_name}"

    return SimpleNamespace(
        llm_service=_LLMService(),
        app_config=SimpleNamespace(max_image_bytes=3 * 1024 * 1024),
        analysis_timeout_seconds=18,
    )


def test_build_worker_uses_single_factory_for_one_image():
    coordinator = AnalysisFlowCoordinator(
        capture_session=_CaptureSession(images=["img-1"]),
        toolbar=_Toolbar(),
        prompt_manager="prompt-manager",
        get_scenario=lambda: "工单跟进",
        get_analysis_intent=lambda count: build_analysis_intent("chat_feedback", capture_count=count),
        get_analysis_context=lambda: "existing context",
        ensure_api_key_configured=_config,
        hide_overlays=lambda **kwargs: None,
        restore_toolbar_for_current_capture=lambda: None,
        on_finished=lambda result, feedback, stats: None,
        single_worker_factory=_Worker,
        multi_worker_factory=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
    )

    worker = coordinator.build_worker(["img-1"], _config())

    assert isinstance(worker, _Worker)
    assert worker.payload == "img-1"
    assert worker.kwargs["scenario"] == "工单跟进"
    assert worker.kwargs["context_text"] == "existing context"
    assert worker.kwargs["model_label"] == "provider/analysis"
    assert worker.kwargs["timeout"] == 18
    assert worker.kwargs["max_image_bytes"] == 3 * 1024 * 1024
    assert worker.kwargs["analysis_intent"].scene_type == "chat_feedback"


def test_build_worker_uses_multi_factory_for_multiple_images():
    coordinator = AnalysisFlowCoordinator(
        capture_session=_CaptureSession(images=["img-1", "img-2"]),
        toolbar=_Toolbar(),
        prompt_manager="prompt-manager",
        get_scenario=lambda: "连续步骤截图",
        get_analysis_intent=lambda count: build_analysis_intent("step_sequence", capture_count=count),
        get_analysis_context=lambda: "",
        ensure_api_key_configured=_config,
        hide_overlays=lambda **kwargs: None,
        restore_toolbar_for_current_capture=lambda: None,
        on_finished=lambda result, feedback, stats: None,
        single_worker_factory=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
        multi_worker_factory=_Worker,
    )

    worker = coordinator.build_worker(["img-1", "img-2"], _config())

    assert isinstance(worker, _Worker)
    assert worker.payload == ["img-1", "img-2"]
    assert worker.kwargs["analysis_intent"].capture_group_mode == "sequence"


def test_start_analysis_restores_toolbar_when_api_key_missing():
    toolbar = _Toolbar()
    restored = {"count": 0}
    coordinator = AnalysisFlowCoordinator(
        capture_session=_CaptureSession(images=["img-1"]),
        toolbar=toolbar,
        prompt_manager="prompt-manager",
        get_scenario=lambda: "工单跟进",
        get_analysis_intent=lambda count: build_analysis_intent("chat_feedback", capture_count=count),
        get_analysis_context=lambda: "",
        ensure_api_key_configured=lambda: None,
        hide_overlays=lambda **kwargs: None,
        restore_toolbar_for_current_capture=lambda: restored.__setitem__("count", restored["count"] + 1),
        on_finished=lambda result, feedback, stats: None,
        single_worker_factory=_Worker,
        multi_worker_factory=_Worker,
    )

    started = coordinator.start_analysis()

    assert not started
    assert coordinator.capture_locked is False
    assert restored["count"] == 1


def test_start_analysis_requires_selected_intent():
    warnings = []
    coordinator = AnalysisFlowCoordinator(
        capture_session=_CaptureSession(images=["img-1"]),
        toolbar=_Toolbar(),
        prompt_manager="prompt-manager",
        get_scenario=lambda: "",
        get_analysis_intent=lambda count: None,
        get_analysis_context=lambda: "",
        ensure_api_key_configured=_config,
        hide_overlays=lambda **kwargs: (_ for _ in ()).throw(AssertionError()),
        restore_toolbar_for_current_capture=lambda: None,
        on_finished=lambda result, feedback, stats: None,
        single_worker_factory=_Worker,
        multi_worker_factory=_Worker,
        show_warning=lambda title, message: warnings.append((title, message)),
    )

    started = coordinator.start_analysis()

    assert not started
    assert warnings == [("缺少场景", "请先选择本次截图的分析场景")]


def test_start_analysis_wires_and_starts_worker():
    toolbar = _Toolbar()
    hidden = {"count": 0}
    coordinator = AnalysisFlowCoordinator(
        capture_session=_CaptureSession(images=["img-1"]),
        toolbar=toolbar,
        prompt_manager="prompt-manager",
        get_scenario=lambda: "工单跟进",
        get_analysis_intent=lambda count: build_analysis_intent("chat_feedback", capture_count=count),
        get_analysis_context=lambda: "",
        ensure_api_key_configured=_config,
        hide_overlays=lambda **kwargs: hidden.__setitem__("count", hidden["count"] + 1),
        restore_toolbar_for_current_capture=lambda: None,
        on_finished=lambda result, feedback, stats: None,
        single_worker_factory=_Worker,
        multi_worker_factory=_Worker,
    )

    started = coordinator.start_analysis()

    assert started
    assert coordinator.current_worker is not None
    assert coordinator.current_worker.started is True
    assert len(coordinator.current_worker.finished.callbacks) == 1
    assert toolbar.hidden == 1
    assert toolbar.loading_states == [True]
    assert hidden["count"] == 1


def test_handle_finished_unlocks_forwards_and_records_metrics():
    seen = []
    recorded = []
    coordinator = AnalysisFlowCoordinator(
        capture_session=_CaptureSession(images=["img-1"]),
        toolbar=_Toolbar(),
        prompt_manager="prompt-manager",
        get_scenario=lambda: "工单跟进",
        get_analysis_intent=lambda count: build_analysis_intent("chat_feedback", capture_count=count),
        get_analysis_context=lambda: "",
        ensure_api_key_configured=_config,
        hide_overlays=lambda **kwargs: None,
        restore_toolbar_for_current_capture=lambda: None,
        on_finished=lambda result, feedback, stats: seen.append((result, feedback, stats)),
        single_worker_factory=_Worker,
        multi_worker_factory=_Worker,
        record_analysis_metrics=lambda stats, success: recorded.append((stats, success)),
    )
    coordinator._current_worker = _Worker("img-1")
    coordinator._capture_locked = True

    coordinator._handle_finished("done")

    assert coordinator.capture_locked is False
    assert seen == [("done", "img-b64", "analysis-stats")]
    assert recorded == [("analysis-stats", True)]


def test_handle_parse_error_copies_restores_and_records_failure():
    copied = []
    warnings = []
    restored = {"count": 0}
    recorded = []
    coordinator = AnalysisFlowCoordinator(
        capture_session=_CaptureSession(images=["img-1"]),
        toolbar=_Toolbar(),
        prompt_manager="prompt-manager",
        get_scenario=lambda: "工单跟进",
        get_analysis_intent=lambda count: build_analysis_intent("chat_feedback", capture_count=count),
        get_analysis_context=lambda: "",
        ensure_api_key_configured=_config,
        hide_overlays=lambda **kwargs: None,
        restore_toolbar_for_current_capture=lambda: restored.__setitem__("count", restored["count"] + 1),
        on_finished=lambda result, feedback, stats: None,
        single_worker_factory=_Worker,
        multi_worker_factory=_Worker,
        show_warning=lambda title, message: warnings.append((title, message)),
        copy_to_clipboard=lambda text: copied.append(text),
        record_analysis_metrics=lambda stats, success: recorded.append((stats, success)),
    )
    coordinator._current_worker = _Worker("img-1")
    coordinator._capture_locked = True

    coordinator._handle_parse_error("raw-text")

    assert coordinator.capture_locked is False
    assert copied == ["raw-text"]
    assert warnings == [("格式异常", "AI 返回格式异常，已将原始内容写入剪贴板")]
    assert restored["count"] == 1
    assert recorded == [("analysis-stats", False)]

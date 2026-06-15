from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aica.analysis.flow import _resolve_analysis_image_limit
from aica.analysis.strategy import AnalysisPromptBundle
from aica.config import ServerConfig
from aica.image_utils import EncodedImage
from aica.llm.types import ModelReference, TaskRunResult
from aica.worker import AIWorker, MultiCaptureAIWorker, QPixmap


def _bundle() -> AnalysisPromptBundle:
    return AnalysisPromptBundle(
        system_prompt="system",
        user_prompt="user",
        scene_type="chat_feedback",
        scene_label="聊天反馈",
        context_text="",
        image_count=1,
        applied_rule_snapshot={},
        prompt_version="test",
        trace_id="trace",
    )


def _encoded(index: int = 1) -> EncodedImage:
    return EncodedImage(
        data_url=f"data:image/png;base64,dGVzdC0{index}",
        mime_type="image/png",
        byte_size=100 + index,
        preprocess_ms=index,
    )


def _run_result(text: str) -> TaskRunResult:
    return TaskRunResult(
        text=text,
        attempts=1,
        latency_ms=12,
        reference=ModelReference(
            provider_id="local",
            provider_kind="openai_compatible",
            provider_name="本地模型",
            model_id="vision",
            model_name="Vision",
            timeout_seconds=30,
            api_key="key",
            base_url="https://example.com",
            capabilities=("vision_chat",),
        ),
    )


def _server_config() -> ServerConfig:
    return ServerConfig(
        enabled=True,
        base_url="https://server.example.com",
        api_key="server-key",
        timeout_seconds=5,
    )


def _patch_worker_common(monkeypatch, worker, *, local_text: str = "local answer"):  # noqa: ANN001
    local_calls: list[object] = []

    monkeypatch.setattr(worker, "_resolve_context_text", lambda: "context")
    monkeypatch.setattr(worker, "_build_prompt_bundle", lambda image_count: _bundle())
    monkeypatch.setattr(worker, "_encode_for_api", lambda _pixmap, image_count: _encoded(image_count))

    def _run_local(*_args, **kwargs):  # noqa: ANN001
        local_calls.append(kwargs)
        return _run_result(local_text)

    monkeypatch.setattr(worker, "_run_llm_task_detailed", _run_local)
    return local_calls


def test_ai_worker_prefers_server_analysis(monkeypatch) -> None:  # noqa: ANN001
    server_calls: list[object] = []

    class _Client:
        def analyze_screenshot(self, **kwargs):  # noqa: ANN001
            server_calls.append(kwargs)
            return {"answer": '{"title":"服务端结果","current_summary":"ok","timeline_entry":"ok"}'}

    monkeypatch.setattr("aica.worker.ChattodoServerClient.from_config", lambda _config: _Client())
    worker = AIWorker(QPixmap(), object(), "initial", server_config=_server_config())
    local_calls = _patch_worker_common(monkeypatch, worker)

    raw_text, encoded_images = worker._call_api()

    assert "服务端结果" in raw_text
    assert encoded_images == [_encoded(1)]
    assert server_calls == [{"image_data_url": _encoded(1).data_url, "summary": "context"}]
    assert local_calls == []
    assert worker._analysis_stats.provider_id == "chattodo_server"
    assert worker._model == "Chattodo 服务端 / 截图分析"


def test_ai_worker_falls_back_to_local_analysis_when_server_fails(monkeypatch) -> None:  # noqa: ANN001
    class _Client:
        def analyze_screenshot(self, **_kwargs):  # noqa: ANN001
            raise RuntimeError("server down")

    monkeypatch.setattr("aica.worker.ChattodoServerClient.from_config", lambda _config: _Client())
    worker = AIWorker(QPixmap(), object(), "initial", server_config=_server_config())
    local_calls = _patch_worker_common(monkeypatch, worker, local_text="local fallback")

    raw_text, encoded_images = worker._call_api()

    assert raw_text == "local fallback"
    assert encoded_images == [_encoded(1)]
    assert len(local_calls) == 1
    assert local_calls[0]["temperature"] == 0.1
    assert worker._analysis_stats.provider_id == "local"
    assert worker._model == "本地模型 / Vision"
    assert worker._last_server_analysis_error == "server down"


def test_ai_worker_uses_local_analysis_when_server_is_not_configured(monkeypatch) -> None:  # noqa: ANN001
    def _unexpected_server(_config):  # noqa: ANN001
        raise AssertionError("server should not be called")

    monkeypatch.setattr("aica.worker.ChattodoServerClient.from_config", _unexpected_server)
    worker = AIWorker(QPixmap(), object(), "initial", server_config=ServerConfig())
    local_calls = _patch_worker_common(monkeypatch, worker, local_text="local only")

    raw_text, encoded_images = worker._call_api()

    assert raw_text == "local only"
    assert encoded_images == [_encoded(1)]
    assert len(local_calls) == 1
    assert worker._analysis_stats.provider_id == "local"


def test_multi_capture_worker_sends_image_list_to_server(monkeypatch) -> None:  # noqa: ANN001
    server_calls: list[object] = []
    encoded_by_call = [_encoded(1), _encoded(2)]

    class _Client:
        def analyze_screenshot(self, **kwargs):  # noqa: ANN001
            server_calls.append(kwargs)
            return {"answer": '{"title":"连续截图","current_summary":"ok","timeline_entry":"ok"}'}

    monkeypatch.setattr("aica.worker.ChattodoServerClient.from_config", lambda _config: _Client())
    worker = MultiCaptureAIWorker([QPixmap(), QPixmap()], object(), "initial", server_config=_server_config())
    monkeypatch.setattr(worker, "_resolve_context_text", lambda: "context")
    monkeypatch.setattr(worker, "_build_prompt_bundle", lambda image_count: _bundle())
    monkeypatch.setattr(worker, "_encode_for_api", lambda _pixmap, image_count: encoded_by_call.pop(0))
    monkeypatch.setattr(worker, "_run_llm_task_detailed", lambda *_args, **_kwargs: _run_result("local"))

    raw_text, encoded_images = worker._call_api()

    assert "连续截图" in raw_text
    assert encoded_images == [_encoded(1), _encoded(2)]
    assert server_calls == [
        {
            "image_data_url": [_encoded(1).data_url, _encoded(2).data_url],
            "summary": "context",
        }
    ]


def test_analysis_image_limit_respects_local_fallback_provider() -> None:
    class _LLMService:
        def resolve_task_model(self, _task_name: str):  # noqa: ANN001
            return SimpleNamespace(reference=SimpleNamespace(provider_id="dashscope"))

    config = SimpleNamespace(
        app_config=SimpleNamespace(max_image_bytes=4 * 1024 * 1024),
        server_config=_server_config(),
        llm_service=_LLMService(),
    )

    assert _resolve_analysis_image_limit(config) == 768 * 1024

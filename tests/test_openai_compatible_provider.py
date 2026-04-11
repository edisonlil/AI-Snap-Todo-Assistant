from aica.llm.providers.openai_compatible import OpenAICompatibleProvider
from aica.llm.types import Message, ModelReference


class _Response:
    def __init__(self, status_code: int, payload: dict[str, object] | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict[str, object]:
        return self._payload


def _dashscope_model(model_name: str = "qwen-vl-max-latest", base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
    return ModelReference(
        provider_id="dashscope",
        provider_kind="openai_compatible",
        provider_name="阿里云百炼",
        model_id=model_name,
        model_name=model_name,
        timeout_seconds=30,
        api_key="test-key",
        base_url=base_url,
        capabilities=("vision_chat", "text_chat"),
    )


def test_dashscope_request_normalizes_model_name_and_base_url(monkeypatch):
    captured: list[tuple[str, str]] = []

    def _fake_post(url, json, headers, timeout):  # noqa: ANN001
        captured.append((url, json["model"]))
        return _Response(200, payload={"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("aica.llm.providers.openai_compatible.requests.post", _fake_post)
    provider = OpenAICompatibleProvider()

    result = provider.generate(
        model=_dashscope_model(),
        messages=[Message(role="user", content="ping")],
        temperature=0.2,
        timeout=12,
        max_attempts=1,
    )

    assert result.text == "ok"
    assert captured == [("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "qwen-vl-max")]


def test_dashscope_404_error_includes_region_hint(monkeypatch):
    def _fake_post(url, json, headers, timeout):  # noqa: ANN001
        return _Response(404, text='{"message":"Not Found"}')

    monkeypatch.setattr("aica.llm.providers.openai_compatible.requests.post", _fake_post)
    provider = OpenAICompatibleProvider()

    try:
        provider.generate(
            model=_dashscope_model(model_name="qwen-vl-max"),
            messages=[Message(role="user", content="ping")],
            temperature=0.2,
            timeout=12,
            max_attempts=1,
        )
    except Exception as exc:  # noqa: BLE001
        message = str(exc)
        assert "HTTP 404" in message
        assert "dashscope-intl.aliyuncs.com" in message
    else:
        raise AssertionError("expected provider error")

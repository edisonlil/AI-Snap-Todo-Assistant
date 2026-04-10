"""OpenAI-compatible provider implementation."""
from __future__ import annotations

import time

import requests

from aica.llm.types import ContentPart, Message, ModelReference, ProviderInvocationError, ProviderResponse


class OpenAICompatibleProvider:
    _RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    _DASHSCOPE_MODEL_FALLBACKS = {
        "qwen-vl-max-latest": "qwen-vl-max",
        "qwen-plus-latest": "qwen-plus",
    }

    def generate(
        self,
        *,
        model: ModelReference,
        messages: list[Message],
        temperature: float,
        timeout: int,
        max_attempts: int,
    ) -> ProviderResponse:
        headers = {
            "Authorization": f"Bearer {model.api_key}",
            "Content-Type": "application/json",
        }
        request_model_name = self._normalize_model_name(model)
        payload = {
            "model": request_model_name,
            "messages": [self._message_to_payload(message) for message in messages],
            "temperature": temperature,
        }
        response = None
        actual_attempts = 0
        request_url = self._normalize_base_url(model.base_url)
        for attempt in range(max(1, int(max_attempts))):
            actual_attempts = attempt + 1
            response = requests.post(
                request_url,
                json=payload,
                headers=headers,
                timeout=timeout,
            )
            if response.status_code == 200:
                data = response.json()
                return ProviderResponse(
                    text=str(data["choices"][0]["message"]["content"]),
                    attempts=actual_attempts,
                )
            fallback_model_name = self._fallback_model_name(model, payload["model"])
            if fallback_model_name and response.status_code == 404:
                payload["model"] = fallback_model_name
                response = requests.post(
                    request_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                )
                if response.status_code == 200:
                    data = response.json()
                    return ProviderResponse(
                        text=str(data["choices"][0]["message"]["content"]),
                        attempts=actual_attempts,
                    )
            if response.status_code not in self._RETRYABLE_STATUS_CODES or attempt == max_attempts - 1:
                break
            time.sleep(1.2 * (attempt + 1))

        response_text = ""
        if response is not None:
            response_text = response.text.strip()
        detail = f"HTTP {response.status_code}" if response is not None else "HTTP unknown"
        if response_text:
            detail = f"{detail}: {response_text[:400]}"
        if response is not None and response.status_code == 404 and model.provider_id == "dashscope":
            detail = (
                f"{detail}. 请检查百炼接入点是否与账号地域匹配，"
                "中国站使用 https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions，"
                "国际站使用 https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions。"
            )
        raise ProviderInvocationError(detail, attempts=actual_attempts or 1)

    def _message_to_payload(self, message: Message) -> dict[str, object]:
        if isinstance(message.content, str):
            return {"role": message.role, "content": message.content}
        return {
            "role": message.role,
            "content": [self._part_to_payload(part) for part in message.content],
        }

    @staticmethod
    def _part_to_payload(part: ContentPart) -> dict[str, object]:
        if part.type == "text":
            return {"type": "text", "text": part.text}
        return {"type": "image_url", "image_url": {"url": part.data_url}}

    def _normalize_model_name(self, model: ModelReference) -> str:
        if model.provider_id != "dashscope":
            return model.model_name
        return self._DASHSCOPE_MODEL_FALLBACKS.get(model.model_name, model.model_name)

    def _fallback_model_name(self, model: ModelReference, current_model_name: str) -> str:
        if model.provider_id != "dashscope":
            return ""
        for source_name, target_name in self._DASHSCOPE_MODEL_FALLBACKS.items():
            if current_model_name == source_name:
                return target_name
        return ""

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        normalized = str(base_url or "").strip().rstrip("/")
        if normalized.endswith("/compatible-mode/v1"):
            return f"{normalized}/chat/completions"
        return normalized

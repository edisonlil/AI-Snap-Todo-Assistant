"""OpenAI-compatible provider implementation."""
from __future__ import annotations

import time

import requests

from aica.llm.types import ContentPart, Message, ModelReference, ProviderInvocationError, ProviderResponse


class OpenAICompatibleProvider:
    _RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

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
        payload = {
            "model": model.model_name,
            "messages": [self._message_to_payload(message) for message in messages],
            "temperature": temperature,
        }
        response = None
        actual_attempts = 0
        for attempt in range(max(1, int(max_attempts))):
            actual_attempts = attempt + 1
            response = requests.post(
                model.base_url,
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

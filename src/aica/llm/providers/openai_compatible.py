"""OpenAI-compatible provider implementation."""
from __future__ import annotations

import requests

from aica.llm.types import ContentPart, Message, ModelReference


class OpenAICompatibleProvider:
    def generate(
        self,
        *,
        model: ModelReference,
        messages: list[Message],
        temperature: float,
        timeout: int,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {model.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model.model_name,
            "messages": [self._message_to_payload(message) for message in messages],
            "temperature": temperature,
        }
        response = requests.post(
            model.base_url,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        if response.status_code != 200:
            raise requests.RequestException(f"HTTP {response.status_code}")
        data = response.json()
        return str(data["choices"][0]["message"]["content"])

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

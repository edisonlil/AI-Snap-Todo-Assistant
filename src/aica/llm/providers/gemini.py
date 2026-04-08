"""Gemini provider implementation."""
from __future__ import annotations

import time

import requests

from aica.llm.types import ContentPart, Message, ModelReference


class GeminiProvider:
    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    _RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def generate(
        self,
        *,
        model: ModelReference,
        messages: list[Message],
        temperature: float,
        timeout: int,
    ) -> str:
        url = self._BASE_URL.format(model=model.model_name)
        params = {"key": model.api_key}
        payload = {
            "contents": [self._message_to_payload(message) for message in messages if message.role != "system"],
            "generationConfig": {"temperature": temperature},
        }
        system_instruction = self._build_system_instruction(messages)
        if system_instruction is not None:
            payload["systemInstruction"] = system_instruction

        response = None
        for attempt in range(3):
            response = requests.post(url, json=payload, params=params, timeout=timeout)
            if response.status_code == 200:
                break
            if response.status_code not in self._RETRYABLE_STATUS_CODES or attempt == 2:
                break
            time.sleep(1.2 * (attempt + 1))

        if response is None:
            raise requests.RequestException("HTTP unknown")
        if response.status_code != 200:
            response_text = response.text.strip()
            detail = f"HTTP {response.status_code}"
            if response_text:
                detail = f"{detail}: {response_text[:400]}"
            raise requests.RequestException(detail)
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Missing Gemini candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [str(part.get("text", "")).strip() for part in parts if str(part.get("text", "")).strip()]
        if not texts:
            raise ValueError("Missing Gemini text response")
        return "\n".join(texts)

    def _build_system_instruction(self, messages: list[Message]) -> dict[str, object] | None:
        system_text = "\n".join(
            str(message.content).strip()
            for message in messages
            if message.role == "system" and isinstance(message.content, str) and str(message.content).strip()
        )
        if not system_text:
            return None
        return {"parts": [{"text": system_text}]}

    def _message_to_payload(self, message: Message) -> dict[str, object]:
        role = "model" if message.role == "assistant" else "user"
        if isinstance(message.content, str):
            return {"role": role, "parts": [{"text": message.content}]}
        return {"role": role, "parts": [self._part_to_payload(part) for part in message.content]}

    @staticmethod
    def _part_to_payload(part: ContentPart) -> dict[str, object]:
        if part.type == "text":
            return {"text": part.text}
        prefix, encoded = part.data_url.split(",", 1)
        mime_type = prefix.split(";")[0].split(":", 1)[1]
        return {"inlineData": {"mimeType": mime_type, "data": encoded}}

"""Base LLM provider interface."""
from __future__ import annotations

from typing import Protocol

from .types import Message, ModelReference


class LLMProvider(Protocol):
    def generate(
        self,
        *,
        model: ModelReference,
        messages: list[Message],
        temperature: float,
        timeout: int,
    ) -> str: ...

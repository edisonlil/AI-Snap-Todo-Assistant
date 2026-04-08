"""Provider registry."""
from __future__ import annotations

from .providers.gemini import GeminiProvider
from .providers.openai_compatible import OpenAICompatibleProvider


def create_provider(kind: str):
    if kind == "openai_compatible":
        return OpenAICompatibleProvider()
    if kind == "gemini":
        return GeminiProvider()
    raise ValueError(f"Unsupported provider kind: {kind}")

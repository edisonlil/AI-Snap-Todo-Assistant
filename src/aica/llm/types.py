"""Shared LLM provider types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ContentPartType = Literal["text", "image_data_url"]
TaskName = Literal["analysis", "plan_export", "prompt_optimization"]


@dataclass(frozen=True)
class ContentPart:
    type: ContentPartType
    text: str = ""
    data_url: str = ""


@dataclass(frozen=True)
class Message:
    role: str
    content: str | list[ContentPart]


@dataclass(frozen=True)
class ModelReference:
    provider_id: str
    provider_kind: str
    provider_name: str
    model_id: str
    model_name: str
    timeout_seconds: int
    api_key: str
    base_url: str
    capabilities: tuple[str, ...]

    @property
    def display_name(self) -> str:
        return f"{self.provider_name} / {self.model_name}"


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    attempts: int


@dataclass(frozen=True)
class TaskRunResult:
    text: str
    attempts: int
    latency_ms: int
    reference: ModelReference


class ProviderInvocationError(RuntimeError):
    def __init__(self, message: str, *, attempts: int):
        super().__init__(message)
        self.attempts = max(1, int(attempts))

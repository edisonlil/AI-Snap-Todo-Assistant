"""Task-oriented LLM service."""
from __future__ import annotations

import time
from dataclasses import dataclass

from aica.config import AppConfig, ProviderConfig, ProviderModelConfig, TaskModelBinding

from .registry import create_provider
from .types import Message, ModelReference, TaskName, TaskRunResult


class LLMServiceError(RuntimeError):
    """Provider invocation failed."""


class ModelResolutionError(LLMServiceError):
    """Task model binding is invalid."""


class TaskExecutionError(LLMServiceError):
    """Provider invocation failed with execution metadata."""

    def __init__(
        self,
        message: str,
        *,
        reference: ModelReference,
        attempts: int,
        latency_ms: int,
    ) -> None:
        super().__init__(message)
        self.reference = reference
        self.attempts = max(1, int(attempts))
        self.latency_ms = max(0, int(latency_ms))


@dataclass
class ResolvedTaskModel:
    reference: ModelReference
    task_name: TaskName
    fallback_used: bool = False


class LLMService:
    def __init__(self, config: AppConfig):
        self._config = config

    def run_task(
        self,
        task_name: TaskName,
        *,
        messages: list[Message],
        temperature: float = 0.3,
        timeout: int | None = None,
    ) -> str:
        return self.run_task_detailed(
            task_name,
            messages=messages,
            temperature=temperature,
            timeout=timeout,
        ).text

    def run_task_detailed(
        self,
        task_name: TaskName,
        *,
        messages: list[Message],
        temperature: float = 0.3,
        timeout: int | None = None,
    ) -> TaskRunResult:
        resolved = self.resolve_task_model(task_name)
        provider = create_provider(resolved.reference.provider_kind)
        request_timeout = timeout or resolved.reference.timeout_seconds
        started_at = time.perf_counter()
        max_attempts = self._max_attempts(task_name)
        try:
            provider_result = provider.generate(
                model=resolved.reference,
                messages=messages,
                temperature=temperature,
                timeout=request_timeout,
                max_attempts=max_attempts,
            )
            latency_ms = round((time.perf_counter() - started_at) * 1000)
            return TaskRunResult(
                text=provider_result.text,
                attempts=provider_result.attempts,
                latency_ms=latency_ms,
                reference=resolved.reference,
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.perf_counter() - started_at) * 1000)
            attempts = getattr(exc, "attempts", max_attempts)
            raise TaskExecutionError(
                f"{resolved.reference.provider_name} / {resolved.reference.model_name}: {exc}",
                reference=resolved.reference,
                attempts=attempts,
                latency_ms=latency_ms,
            ) from exc

    def resolve_task_model(self, task_name: TaskName) -> ResolvedTaskModel:
        if task_name == "log_analysis":
            try:
                return self._resolve_task_model_without_fallback(task_name)
            except ModelResolutionError:
                resolved = self._resolve_task_model_without_fallback("analysis")
                return ResolvedTaskModel(
                    reference=resolved.reference,
                    task_name="analysis",
                    fallback_used=True,
                )
        return self._resolve_task_model_without_fallback(task_name)

    def _resolve_task_model_without_fallback(self, task_name: TaskName) -> ResolvedTaskModel:
        binding = getattr(self._config.task_model_bindings, task_name, None)
        if not isinstance(binding, TaskModelBinding):
            raise ModelResolutionError(f"Task binding missing: {task_name}")

        provider = next((item for item in self._config.providers if item.id == binding.provider_id), None)
        if provider is None:
            raise ModelResolutionError(f"Provider not found: {binding.provider_id}")
        if not provider.api_key:
            raise ModelResolutionError(f"Provider API key missing: {provider.name}")

        model = next((item for item in provider.models if item.id == binding.model_id), None)
        if model is None:
            raise ModelResolutionError(f"Model not found: {binding.model_id}")

        required_capability = self._required_capability(task_name)
        if required_capability not in model.capabilities:
            raise ModelResolutionError(
                f"Model capability mismatch: {provider.name} / {model.name} lacks {required_capability}"
            )

        return ResolvedTaskModel(reference=self._build_reference(provider, model), task_name=task_name)

    def describe_task_model(self, task_name: TaskName) -> str:
        return self.resolve_task_model(task_name).reference.display_name

    def _build_reference(self, provider: ProviderConfig, model: ProviderModelConfig) -> ModelReference:
        return ModelReference(
            provider_id=provider.id,
            provider_kind=provider.kind,
            provider_name=provider.name,
            model_id=model.id,
            model_name=model.name,
            timeout_seconds=provider.timeout_seconds,
            api_key=provider.api_key,
            base_url=provider.base_url,
            capabilities=tuple(model.capabilities),
        )

    @staticmethod
    def _required_capability(task_name: TaskName) -> str:
        return "vision_chat"

    @staticmethod
    def _max_attempts(task_name: TaskName) -> int:
        return 1 if task_name in {"analysis", "log_analysis"} else 3

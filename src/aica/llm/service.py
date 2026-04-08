"""Task-oriented LLM service."""
from __future__ import annotations

from dataclasses import dataclass

from aica.config import AppConfig, ProviderConfig, ProviderModelConfig, TaskModelBinding

from .registry import create_provider
from .types import Message, ModelReference, TaskName


class LLMServiceError(RuntimeError):
    """Provider invocation failed."""


class ModelResolutionError(LLMServiceError):
    """Task model binding is invalid."""


@dataclass
class ResolvedTaskModel:
    reference: ModelReference


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
        resolved = self.resolve_task_model(task_name)
        provider = create_provider(resolved.reference.provider_kind)
        request_timeout = timeout or resolved.reference.timeout_seconds
        try:
            return provider.generate(
                model=resolved.reference,
                messages=messages,
                temperature=temperature,
                timeout=request_timeout,
            )
        except Exception as exc:  # noqa: BLE001
            raise LLMServiceError(str(exc)) from exc

    def resolve_task_model(self, task_name: TaskName) -> ResolvedTaskModel:
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

        return ResolvedTaskModel(reference=self._build_reference(provider, model))

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
        if task_name == "title_generation":
            return "text_chat"
        return "vision_chat"

from __future__ import annotations

from design_dataset.domain.errors import ConfigurationError
from design_dataset.infrastructure.model_clients.fake import FakeModelClient
from design_dataset.infrastructure.model_clients.gemini import GeminiClient
from design_dataset.settings import AppSettings


def build_model_client(settings: AppSettings):
    provider = settings.model_provider.lower().strip()
    if provider == "fake":
        return FakeModelClient(model_name=settings.model_name or "fake-model-v1")
    if provider in {"gemini", "google"}:
        return GeminiClient(
            api_key=settings.gemini_api_key,
            model_name=settings.model_name,
            timeout_seconds=settings.inference.timeout_seconds,
            max_attempts=settings.inference.max_attempts,
            temperature=settings.inference.temperature,
        )
    raise ConfigurationError(f"Unsupported MODEL_PROVIDER: {settings.model_provider}")

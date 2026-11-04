from vision_engine.domain.errors import ConfigurationError
from vision_engine.infrastructure.multimodal_clients.fake import FakeMultimodalClient
from vision_engine.infrastructure.multimodal_clients.gemini_client import GeminiConceptClient


def build_concept_client(
    *,
    provider: str,
    api_key: str | None,
    model_name: str,
    timeout_seconds: int = 120,
    max_attempts: int = 3,
    temperature: float = 0.2,
):
    provider = (provider or "fake").lower()
    if provider == "fake":
        return FakeMultimodalClient(model_name=model_name or "fake-concept-v1")
    if provider in {"gemini", "google"}:
        return GeminiConceptClient(
            api_key=api_key,
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            temperature=temperature,
        )
    raise ConfigurationError(f"Unsupported MODEL_PROVIDER: {provider}")

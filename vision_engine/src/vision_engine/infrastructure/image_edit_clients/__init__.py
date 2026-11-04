from vision_engine.domain.errors import ConfigurationError
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.image_edit_clients.fake import FakeImageEditClient
from vision_engine.infrastructure.image_edit_clients.gemini_image_client import (
    GeminiImageEditClient,
)


def build_image_edit_client(
    *,
    provider: str,
    api_key: str | None,
    model_name: str,
    file_store: FileStore,
    timeout_seconds: int = 180,
    max_attempts: int = 3,
    temperature: float = 0.4,
):
    provider = (provider or "fake").lower()
    if provider == "fake":
        return FakeImageEditClient(file_store=file_store, model_name=model_name or "fake-image-edit-v1")
    if provider in {"gemini", "google"}:
        return GeminiImageEditClient(
            api_key=api_key,
            model_name=model_name,
            file_store=file_store,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            temperature=temperature,
        )
    raise ConfigurationError(f"Unsupported image edit provider: {provider}")

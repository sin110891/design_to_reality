from __future__ import annotations

from pathlib import Path

from vision_engine.domain.errors import ConfigurationError, ProviderError
from vision_engine.infrastructure.embedding_clients.base import EmbeddingClient
from vision_engine.infrastructure.embedding_clients.fake import FakeEmbeddingClient

# text-embedding-004 was removed from the Gemini v1beta embed API.
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
_LOCAL_PROVIDERS = {"local", "clip", "local-clip"}


class LocalOrApiEmbeddingClient:
    """
    Embedding adapter.

    - fake: deterministic hash embeddings
    - local / clip: joint CLIP image and text embeddings
    - gemini: text embeddings via Gemini; images fall back to a path hash
      blended with a lightweight image byte embedding (prototype-grade)
    """

    def __init__(
        self,
        *,
        provider: str,
        api_key: str | None = None,
        model_name: str = GEMINI_EMBEDDING_MODEL,
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.model_name = model_name
        self._fake = FakeEmbeddingClient()
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ConfigurationError("GEMINI_API_KEY required for gemini embeddings")
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def embed_text(self, text: str) -> list[float]:
        if self.provider == "fake":
            return self._fake.embed_text(text)
        try:
            client = self._get_client()
            result = client.models.embed_content(model=self.model_name, contents=text)
            embedding = result.embeddings[0].values
            return list(embedding)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc), transient=True) from exc

    def embed_image(self, image_path: Path) -> list[float]:
        # Prototype: use deterministic image embedding locally; optional text path cue.
        base = self._fake.embed_image(image_path)
        if self.provider == "fake":
            return base
        # Blend a text embedding of the filename/path for mild semantic signal.
        try:
            text_vec = self.embed_text(f"interior design reference image {image_path.stem}")
            # Truncate/pad to match fake dim for index consistency when mixed — prefer API dim.
            if len(text_vec) == len(base):
                return [(a + b) / 2 for a, b in zip(base, text_vec)]
            return text_vec
        except ProviderError:
            return base

    def embed_images(self, image_paths: list[Path]) -> list[list[float]]:
        return [self.embed_image(p) for p in image_paths]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


def build_embedding_client(
    *,
    provider: str,
    api_key: str | None,
    model_name: str | None = None,
) -> EmbeddingClient:
    provider = (provider or "fake").lower()
    if provider == "fake":
        return FakeEmbeddingClient()
    if provider in _LOCAL_PROVIDERS:
        from vision_engine.infrastructure.embedding_clients.joint import (
            build_joint_embedding_client,
        )

        return build_joint_embedding_client(provider=provider, model_name=model_name)
    resolved_model = model_name or GEMINI_EMBEDDING_MODEL
    if resolved_model == "text-embedding-004" or resolved_model.startswith("clip-"):
        resolved_model = GEMINI_EMBEDDING_MODEL
    return LocalOrApiEmbeddingClient(
        provider=provider, api_key=api_key, model_name=resolved_model
    )

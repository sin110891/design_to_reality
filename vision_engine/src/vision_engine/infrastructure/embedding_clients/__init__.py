from vision_engine.infrastructure.embedding_clients.base import EmbeddingClient
from vision_engine.infrastructure.embedding_clients.fake import FakeEmbeddingClient
from vision_engine.infrastructure.embedding_clients.local_or_api import (
    LocalOrApiEmbeddingClient,
    build_embedding_client,
)

__all__ = [
    "EmbeddingClient",
    "FakeEmbeddingClient",
    "LocalOrApiEmbeddingClient",
    "build_embedding_client",
]

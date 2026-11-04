from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

import numpy as np

from vision_engine.domain.errors import ConfigurationError
from vision_engine.infrastructure.embedding_clients.fake import _hash_to_vec

if TYPE_CHECKING:
    from vision_engine.infrastructure.embedding_clients.local_clip_joint import (
        LocalClipJointEmbeddingClient,
    )


JOINT_FAKE_DIM = 128
JOINT_FAKE_CONTRACT = "joint_image_text_v1"
JOINT_FAKE_FINGERPRINT = f"fake-joint:{JOINT_FAKE_CONTRACT}:{JOINT_FAKE_DIM}:cosine:l2"
_LOCAL_CLIENT_BUILD_LOCK = Lock()
_LOCAL_CLIENTS: dict[str, "LocalClipJointEmbeddingClient"] = {}


@dataclass(frozen=True)
class JointSpaceContract:
    provider: str
    model_name: str
    model_revision: str
    modality_contract: str
    dimension: int
    distance_metric: str
    normalisation: str
    space_fingerprint: str
    preprocessing_config: dict[str, str]


DEFAULT_JOINT_FAKE_CONTRACT = JointSpaceContract(
    provider="fake",
    model_name="joint-fake-v1",
    model_revision="2026.07.21",
    modality_contract=JOINT_FAKE_CONTRACT,
    dimension=JOINT_FAKE_DIM,
    distance_metric="cosine",
    normalisation="l2",
    space_fingerprint=JOINT_FAKE_FINGERPRINT,
    preprocessing_config={"image_prefix": "joint_img:", "text_prefix": "joint_txt:"},
)


def normalize_vector(vector: list[float]) -> list[float]:
    arr = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(arr)) or 1.0
    return (arr / norm).tolist()


class JointEmbeddingClient:
    """
    Joint image-text embedding client with an explicit vector-space contract.

    Uses deterministic local vectors for tests/offline demos. Image and text
    embeddings share dimension and normalisation so they are index-compatible.
    """

    def __init__(self, contract: JointSpaceContract | None = None):
        self.contract = contract or DEFAULT_JOINT_FAKE_CONTRACT

    @property
    def dimension(self) -> int:
        return self.contract.dimension

    def embed_image(self, image_path: Path) -> list[float]:
        data = image_path.read_bytes() if image_path.exists() else image_path.name.encode()
        prefix = self.contract.preprocessing_config["image_prefix"].encode()
        vec = _hash_to_vec(prefix + data[:8192] + image_path.name.encode(), self.contract.dimension)
        return normalize_vector(vec)

    def embed_text(self, text: str) -> list[float]:
        prefix = self.contract.preprocessing_config["text_prefix"].encode()
        vec = _hash_to_vec(prefix + text.encode("utf-8"), self.contract.dimension)
        return normalize_vector(vec)

    def embed_images(self, image_paths: list[Path]) -> list[list[float]]:
        return [self.embed_image(p) for p in image_paths]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]

    def assert_compatible(self, vector: list[float]) -> None:
        if len(vector) != self.contract.dimension:
            raise ValueError(
                f"Vector dimension {len(vector)} != contract dimension {self.contract.dimension}"
            )

    def vector_sha256(self, vector: list[float]) -> str:
        payload = np.asarray(vector, dtype=np.float32).tobytes()
        return hashlib.sha256(payload).hexdigest()


def build_joint_embedding_client(
    *,
    provider: str,
    model_name: str | None = None,
) -> JointEmbeddingClient | LocalClipJointEmbeddingClient:
    provider = (provider or "fake").lower()
    if provider in {"fake", "joint", "joint-fake"}:
        return JointEmbeddingClient()
    if provider in {"local", "clip", "local-clip"}:
        from vision_engine.infrastructure.embedding_clients.local_clip_joint import (
            DEFAULT_CLIP_MODEL,
            LocalClipJointEmbeddingClient,
        )

        resolved_model_name = model_name or DEFAULT_CLIP_MODEL
        # Controlled evaluations run arm jobs concurrently. Initialising multiple
        # SentenceTransformer instances on MPS concurrently can crash the native
        # runtime, so one process owns one model instance per model name.
        with _LOCAL_CLIENT_BUILD_LOCK:
            client = _LOCAL_CLIENTS.get(resolved_model_name)
            if client is None:
                client = LocalClipJointEmbeddingClient(model_name=resolved_model_name)
                _LOCAL_CLIENTS[resolved_model_name] = client
            return client
    raise ConfigurationError(
        f"Unknown embedding provider {provider!r}. "
        "Use fake (deterministic) or local (CLIP joint embeddings)."
    )

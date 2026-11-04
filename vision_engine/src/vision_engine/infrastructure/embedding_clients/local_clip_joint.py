from __future__ import annotations

from threading import RLock
from pathlib import Path

from PIL import Image

from vision_engine.domain.errors import ConfigurationError
from vision_engine.infrastructure.embedding_clients.joint import (
    JointSpaceContract,
    normalize_vector,
)


DEFAULT_CLIP_MODEL = "clip-ViT-B-32"


def clip_space_contract(model_name: str, dimension: int) -> JointSpaceContract:
    return JointSpaceContract(
        provider="local",
        model_name=model_name,
        model_revision="sentence-transformers",
        modality_contract="joint_image_text_v1",
        dimension=dimension,
        distance_metric="cosine",
        normalisation="l2",
        space_fingerprint=f"local-clip:{model_name}:{dimension}:cosine:l2",
        preprocessing_config={"library": "sentence-transformers", "model": model_name},
    )


class LocalClipJointEmbeddingClient:
    """Real joint image-text embeddings via a local CLIP model (same vector space)."""

    def __init__(self, model_name: str = DEFAULT_CLIP_MODEL):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ConfigurationError(
                "Local CLIP embeddings require sentence-transformers. "
                "Install with: pip install -e '.[embeddings]'"
            ) from exc

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._encode_lock = RLock()
        dim_fn = getattr(self._model, "get_embedding_dimension", None)
        dim = int(dim_fn() if dim_fn else self._model.get_sentence_embedding_dimension())
        self.contract = clip_space_contract(model_name, dim)

    @property
    def dimension(self) -> int:
        return self.contract.dimension

    def embed_image(self, image_path: Path) -> list[float]:
        with Image.open(image_path) as img:
            rgb = img.convert("RGB")
            with self._encode_lock:
                vector = self._model.encode(rgb, convert_to_numpy=True)
        return normalize_vector(vector.tolist())

    def embed_text(self, text: str) -> list[float]:
        with self._encode_lock:
            vector = self._model.encode(text or " ", convert_to_numpy=True)
        return normalize_vector(vector.tolist())

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
        import hashlib

        import numpy as np

        payload = np.asarray(vector, dtype=np.float32).tobytes()
        return hashlib.sha256(payload).hexdigest()

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np


DIM = 64


def _hash_to_vec(payload: bytes, dim: int = DIM) -> list[float]:
    digest = hashlib.sha256(payload).digest()
    # Expand deterministically
    rng_seed = int.from_bytes(digest[:8], "big") % (2**32 - 1)
    rng = np.random.default_rng(rng_seed)
    vec = rng.standard_normal(dim).astype(np.float32)
    # Mix in more digest bytes for slight differentiation
    for i, b in enumerate(digest):
        vec[i % dim] += (b / 255.0) - 0.5
    norm = float(np.linalg.norm(vec)) or 1.0
    return (vec / norm).tolist()


class FakeEmbeddingClient:
    """Deterministic local embeddings for tests and offline demos."""

    def __init__(self, *, dim: int = DIM):
        self.dim = dim

    def embed_image(self, image_path: Path) -> list[float]:
        data = image_path.read_bytes() if image_path.exists() else image_path.name.encode()
        return _hash_to_vec(b"img:" + data[:4096] + image_path.name.encode(), self.dim)

    def embed_text(self, text: str) -> list[float]:
        return _hash_to_vec(b"txt:" + text.encode("utf-8"), self.dim)

    def embed_images(self, image_paths: list[Path]) -> list[list[float]]:
        return [self.embed_image(p) for p in image_paths]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np

from vision_engine.domain.models import DatasetRecord


class VectorStore(Protocol):
    def build(
        self,
        records: list[DatasetRecord],
        image_embeddings: dict[str, list[float]],
        text_embeddings: dict[str, list[float]],
    ) -> None: ...

    def save(self, path: Path) -> None: ...

    def load(self, path: Path) -> None: ...

    @property
    def records(self) -> list[DatasetRecord]: ...

    def image_matrix(self) -> np.ndarray: ...

    def text_matrix(self) -> np.ndarray: ...

    def search_image(self, query: list[float], top_k: int) -> list[tuple[int, float]]: ...

    def search_text(self, query: list[float], top_k: int) -> list[tuple[int, float]]: ...


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


class NumpyVectorStore:
    """Simple NumPy cosine index — sufficient for ~60 curated records."""

    def __init__(self) -> None:
        self._records: list[DatasetRecord] = []
        self._image: np.ndarray | None = None
        self._text: np.ndarray | None = None
        self._ids: list[str] = []

    @property
    def records(self) -> list[DatasetRecord]:
        return self._records

    def build(
        self,
        records: list[DatasetRecord],
        image_embeddings: dict[str, list[float]],
        text_embeddings: dict[str, list[float]],
    ) -> None:
        if not records:
            raise ValueError("Cannot build index from empty record set")
        self._records = list(records)
        self._ids = [r.image_id for r in records]
        image_rows = [image_embeddings[r.image_id] for r in records]
        text_rows = [text_embeddings[r.image_id] for r in records]
        self._image = _normalize_rows(np.asarray(image_rows, dtype=np.float32))
        self._text = _normalize_rows(np.asarray(text_rows, dtype=np.float32))

    def save(self, path: Path) -> None:
        if self._image is None or self._text is None:
            raise ValueError("Index has not been built")
        path.parent.mkdir(parents=True, exist_ok=True)
        meta_path = path.with_suffix(".jsonl")
        import json

        with meta_path.open("w", encoding="utf-8") as handle:
            for record in self._records:
                handle.write(record.model_dump_json() + "\n")
        np.savez_compressed(
            path,
            image=self._image,
            text=self._text,
            ids=np.asarray(self._ids),
        )

    def load(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Index not found: {path}")
        data = np.load(path, allow_pickle=False)
        self._image = data["image"]
        self._text = data["text"]
        self._ids = [str(x) for x in data["ids"].tolist()]
        meta_path = path.with_suffix(".jsonl")
        if not meta_path.exists():
            raise FileNotFoundError(f"Index metadata not found: {meta_path}")
        records: list[DatasetRecord] = []
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(DatasetRecord.model_validate_json(line))
        by_id = {r.image_id: r for r in records}
        self._records = [by_id[i] for i in self._ids if i in by_id]

    def image_matrix(self) -> np.ndarray:
        if self._image is None:
            raise ValueError("Index not loaded")
        return self._image

    def text_matrix(self) -> np.ndarray:
        if self._text is None:
            raise ValueError("Index not loaded")
        return self._text

    def _search(self, matrix: np.ndarray, query: list[float], top_k: int) -> list[tuple[int, float]]:
        q = np.asarray(query, dtype=np.float32)
        norm = np.linalg.norm(q)
        if norm == 0:
            return [(i, 0.0) for i in range(min(top_k, len(self._records)))]
        q = q / norm
        scores = matrix @ q
        top_k = min(top_k, len(scores))
        idx = np.argpartition(-scores, top_k - 1)[:top_k]
        ordered = sorted(idx.tolist(), key=lambda i: float(scores[i]), reverse=True)
        return [(i, float(scores[i])) for i in ordered]

    def search_image(self, query: list[float], top_k: int) -> list[tuple[int, float]]:
        return self._search(self.image_matrix(), query, top_k)

    def search_text(self, query: list[float], top_k: int) -> list[tuple[int, float]]:
        return self._search(self.text_matrix(), query, top_k)

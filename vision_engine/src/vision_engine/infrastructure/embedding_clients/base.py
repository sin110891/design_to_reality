from __future__ import annotations

from pathlib import Path
from typing import Protocol


class EmbeddingClient(Protocol):
    def embed_image(self, image_path: Path) -> list[float]: ...

    def embed_text(self, text: str) -> list[float]: ...

    def embed_images(self, image_paths: list[Path]) -> list[list[float]]: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from vision_engine.domain.models import ModelCallMetadata


class MultimodalConceptClient(Protocol):
    def generate_concept(
        self,
        *,
        room_image_path: Path,
        reference_image_paths: list[Path],
        prompt: str,
        response_schema: dict,
    ) -> tuple[dict, ModelCallMetadata]: ...

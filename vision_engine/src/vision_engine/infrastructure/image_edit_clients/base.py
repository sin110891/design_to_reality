from __future__ import annotations

from pathlib import Path
from typing import Protocol

from vision_engine.domain.models import DesignDirection, ModelCallMetadata


class ImageEditClient(Protocol):
    def edit_room(
        self,
        room_image_path: str | Path,
        reference_image_paths: list[str | Path],
        design_direction: dict | DesignDirection,
        output_count: int = 3,
        *,
        prompts: list[str] | None = None,
    ) -> tuple[list[str], ModelCallMetadata]:
        """Return local file paths for generated variants plus call metadata."""
        ...

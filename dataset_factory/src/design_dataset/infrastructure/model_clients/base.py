from __future__ import annotations

from pathlib import Path
from typing import Protocol

from design_dataset.domain.models import ModelCallMetadata


class MultimodalLabelClient(Protocol):
    def label_image(
        self,
        *,
        image_path: Path,
        prompt: str,
        response_schema: dict,
    ) -> tuple[dict, ModelCallMetadata]:
        ...

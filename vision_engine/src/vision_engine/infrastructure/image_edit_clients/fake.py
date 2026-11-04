from __future__ import annotations

import io
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

from vision_engine.domain.enums import VariantKind
from vision_engine.domain.models import DesignDirection, ModelCallMetadata
from vision_engine.infrastructure.file_store import FileStore


VARIANT_KINDS = [
    VariantKind.CLOSEST,
    VariantKind.CONSERVATIVE,
    VariantKind.EXPRESSIVE,
]


class FakeImageEditClient:
    """
    Creates deterministic placeholder edits by lightly transforming the room image
    and stamping variant labels — no API calls.
    """

    def __init__(self, *, file_store: FileStore, model_name: str = "fake-image-edit-v1"):
        self.file_store = file_store
        self.model_name = model_name

    def edit_room(
        self,
        room_image_path: str | Path,
        reference_image_paths: list[str | Path],
        design_direction: dict | DesignDirection,
        output_count: int = 3,
        *,
        prompts: list[str] | None = None,
        project_id: str = "proj_local",
    ) -> tuple[list[str], ModelCallMetadata]:
        started = time.perf_counter()
        room = Path(room_image_path)
        with Image.open(room) as img:
            base = img.convert("RGB")

        paths: list[str] = []
        count = min(output_count, 3)
        enhancements = [
            (1.05, 1.08, 1.02),  # closest
            (0.98, 0.95, 1.0),  # conservative
            (1.12, 1.15, 1.08),  # expressive
        ]
        labels = ["Variant A — closest", "Variant B — conservative", "Variant C — expressive"]
        for i in range(count):
            color, contrast, brightness = enhancements[i]
            frame = base.copy()
            frame = ImageEnhance.Color(frame).enhance(color)
            frame = ImageEnhance.Contrast(frame).enhance(contrast)
            frame = ImageEnhance.Brightness(frame).enhance(brightness)
            draw = ImageDraw.Draw(frame)
            draw.rectangle((12, 12, 520, 56), fill=(20, 20, 20))
            draw.text((24, 24), f"{labels[i]} · {project_id[-8:]}", fill=(245, 245, 245))
            buf = io.BytesIO()
            frame.save(buf, format="PNG")
            dest = self.file_store.store_generated(
                project_id=project_id,
                variant_key=f"variant_{chr(ord('a') + i)}_{VARIANT_KINDS[i].value}",
                image_bytes=buf.getvalue(),
                extension=".png",
            )
            paths.append(str(dest))

        _ = (reference_image_paths, design_direction, prompts)
        meta = ModelCallMetadata(
            provider="fake",
            model_name=self.model_name,
            request_id=f"fake-edit-{room.stem}",
            latency_ms=max(1, int((time.perf_counter() - started) * 1000)),
            attempt=1,
        )
        return paths, meta

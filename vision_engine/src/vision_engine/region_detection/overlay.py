from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from vision_engine.region_detection.models import DetectedRegionProposal
from vision_engine.virtual_staging.application.masks import bbox_to_pixel_rect


REGION_COLOURS = {
    "detected": (255, 180, 40),
    "proposed": (120, 180, 255),
}


def render_detection_overlay(
    *,
    image_path: Path,
    regions: list[DetectedRegionProposal],
    dest: Path,
) -> Path:
    with Image.open(image_path) as img:
        frame = img.convert("RGB")
    draw = ImageDraw.Draw(frame)
    for proposal in regions:
        colour = REGION_COLOURS.get(proposal.detection_kind, (255, 180, 40))
        left, top, right, bottom = bbox_to_pixel_rect(frame.size, proposal.geometry_json)
        draw.rectangle((left, top, right, bottom), outline=colour, width=3)
        label = f"{proposal.region_code} ({proposal.confidence:.2f})"
        banner_top = max(0, top - 22)
        draw.rectangle((left, banner_top, min(frame.size[0], left + 220), top), fill=(20, 20, 20))
        draw.text((left + 4, banner_top + 4), label[:34], fill=(255, 255, 255))
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame.save(dest, format="PNG")
    return dest

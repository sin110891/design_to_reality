from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from vision_engine.virtual_staging.application.masks import (
    bbox_to_pixel_rect,
    clamp_normalised_bbox,
    normalised_bbox,
    write_region_mask_png,
)


def test_normalised_bbox_defaults():
    x, y, width, height = normalised_bbox({})
    assert (x, y, width, height) == (0.2, 0.2, 0.3, 0.3)


def test_bbox_to_pixel_rect():
    rect = bbox_to_pixel_rect((1000, 800), {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.25})
    assert rect == (100, 160, 600, 360)


def test_clamp_normalised_bbox_clips_overflow_to_image_frame():
    clipped = clamp_normalised_bbox(
        {"x": -0.1, "y": 0.75, "width": 0.4, "height": 0.5}
    )

    assert clipped == pytest.approx({"x": 0.0, "y": 0.75, "width": 0.3, "height": 0.25})
    assert bbox_to_pixel_rect((1000, 800), clipped) == (0, 600, 300, 800)


@pytest.mark.parametrize(
    "geometry",
    [
        {"x": 1.1, "y": 0.2, "width": 0.1, "height": 0.2},
        {"x": 0.2, "y": 0.2, "width": -0.1, "height": 0.2},
        {"x": 0.2, "y": 0.2, "width": 0.0, "height": 0.2},
    ],
)
def test_clamp_normalised_bbox_rejects_non_visible_or_inverted_boxes(geometry):
    with pytest.raises(ValueError):
        clamp_normalised_bbox(geometry)


def test_write_region_mask_png(tmp_path: Path):
    mask_path = tmp_path / "mask.png"
    write_region_mask_png(
        image_size=(200, 100),
        geometry_json={"x": 0.0, "y": 0.0, "width": 0.5, "height": 1.0},
        dest=mask_path,
    )
    assert mask_path.exists()
    with Image.open(mask_path) as mask:
        assert mask.size == (200, 100)
        assert mask.getpixel((50, 50)) == 255
        assert mask.getpixel((150, 50)) == 0

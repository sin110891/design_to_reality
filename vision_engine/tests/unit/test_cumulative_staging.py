from __future__ import annotations

from pathlib import Path

from PIL import Image

from vision_engine.settings import AppSettings
from vision_engine.virtual_staging.application.cumulative_staging import resolve_cumulative_preview_mode
from vision_engine.virtual_staging.application.masks import composite_product_into_region


def test_resolve_cumulative_preview_mode_defaults_to_single_when_disabled():
    settings = AppSettings()
    settings.virtual_staging.cumulative_preview_mode = "gemini_chain"
    assert (
        resolve_cumulative_preview_mode(
            settings=settings,
            cumulative_enabled=False,
            ui_mode="Chain Gemini edits",
        )
        == "single"
    )


def test_resolve_cumulative_preview_mode_uses_ui_override():
    settings = AppSettings()
    settings.virtual_staging.cumulative_preview_mode = "local_composite"
    assert (
        resolve_cumulative_preview_mode(
            settings=settings,
            cumulative_enabled=True,
            ui_mode="Chain Gemini edits",
        )
        == "gemini_chain"
    )


def test_resolve_cumulative_preview_mode_uses_config_when_ui_default():
    settings = AppSettings()
    settings.virtual_staging.cumulative_preview_mode = "local_composite"
    assert (
        resolve_cumulative_preview_mode(
            settings=settings,
            cumulative_enabled=True,
            ui_mode="Use config default",
        )
        == "local_composite"
    )


def test_composite_product_into_region_pastes_product(tmp_path: Path):
    room = tmp_path / "room.png"
    product = tmp_path / "product.png"
    out = tmp_path / "out.png"
    Image.new("RGB", (400, 300), (200, 200, 200)).save(room)
    Image.new("RGB", (120, 80), (120, 40, 10)).save(product)

    composite_product_into_region(
        room_image_path=room,
        product_image_path=product,
        geometry_json={"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5},
        dest=out,
    )

    assert out.exists()
    with Image.open(out) as frame:
        assert frame.size == (400, 300)

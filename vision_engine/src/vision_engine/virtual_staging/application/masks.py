from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps


def clamp_normalised_bbox(geometry_json: dict[str, Any]) -> dict[str, float]:
    """Clip a normalised bounding box to the image frame.

    Bounding boxes from vision providers can extend slightly beyond the frame.
    Those are safely clipped. Boxes with no visible area after clipping are
    rejected so callers can skip the bad detection instead of drawing an
    inverted rectangle.
    """
    try:
        x = float(geometry_json["x"])
        y = float(geometry_json["y"])
        width = float(geometry_json["width"])
        height = float(geometry_json["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Bounding box must contain numeric x, y, width, and height") from exc

    if not all(math.isfinite(value) for value in (x, y, width, height)):
        raise ValueError("Bounding box values must be finite")
    if width <= 0 or height <= 0:
        raise ValueError("Bounding box width and height must be greater than zero")

    left = min(1.0, max(0.0, x))
    top = min(1.0, max(0.0, y))
    right = min(1.0, max(0.0, x + width))
    bottom = min(1.0, max(0.0, y + height))
    if right <= left or bottom <= top:
        raise ValueError("Bounding box does not overlap the image frame")

    return {
        "x": left,
        "y": top,
        "width": right - left,
        "height": bottom - top,
    }


def normalised_bbox(geometry_json: dict[str, Any]) -> tuple[float, float, float, float]:
    x = float(geometry_json.get("x", 0.2))
    y = float(geometry_json.get("y", 0.2))
    width = float(geometry_json.get("width", 0.3))
    height = float(geometry_json.get("height", 0.3))
    return x, y, width, height


def bbox_to_pixel_rect(
    image_size: tuple[int, int], geometry_json: dict[str, Any]
) -> tuple[int, int, int, int]:
    width, height = image_size
    x, y, box_w, box_h = normalised_bbox(clamp_normalised_bbox(geometry_json))
    left = int(x * width)
    top = int(y * height)
    right = int(min(width, (x + box_w) * width))
    bottom = int(min(height, (y + box_h) * height))
    return left, top, right, bottom


def write_region_mask_png(
    *,
    image_size: tuple[int, int],
    geometry_json: dict[str, Any],
    dest: Path,
) -> Path:
    width, height = image_size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle(bbox_to_pixel_rect(image_size, geometry_json), fill=255)
    dest.parent.mkdir(parents=True, exist_ok=True)
    mask.save(dest, format="PNG")
    return dest


def write_product_reference_card(
    *,
    product_name: str,
    brand_name: str | None,
    dimensions_text: str | None,
    dest: Path,
) -> Path:
    card = Image.new("RGB", (640, 480), (245, 245, 240))
    draw = ImageDraw.Draw(card)
    draw.rectangle((24, 24, 616, 456), outline=(120, 120, 120), width=3)
    draw.text((40, 40), "PRODUCT REFERENCE", fill=(80, 80, 80))
    draw.text((40, 90), product_name[:70], fill=(20, 20, 20))
    if brand_name:
        draw.text((40, 140), brand_name[:50], fill=(60, 60, 60))
    if dimensions_text:
        draw.text((40, 190), dimensions_text, fill=(60, 60, 60))
    draw.text(
        (40, 400),
        "Catalogue metadata reference — not construction geometry.",
        fill=(120, 80, 20),
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    card.save(dest, format="PNG")
    return dest


def composite_product_into_region(
    *,
    room_image_path: Path,
    product_image_path: Path,
    geometry_json: dict[str, Any],
    dest: Path,
) -> Path:
    with Image.open(room_image_path) as room:
        frame = room.convert("RGBA")
    with Image.open(product_image_path) as product:
        product_rgba = product.convert("RGBA")
        left, top, right, bottom = bbox_to_pixel_rect(frame.size, geometry_json)
        target_w = max(1, right - left)
        target_h = max(1, bottom - top)
        fitted = ImageOps.contain(product_rgba, (target_w, target_h))
        paste_x = left + (target_w - fitted.width) // 2
        paste_y = top + (target_h - fitted.height) // 2
        frame.paste(fitted, (paste_x, paste_y), fitted)
    rgb = frame.convert("RGB")
    dest.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(dest, format="PNG")
    return dest


def apply_fake_product_staging(
    *,
    room_image_path: Path,
    geometry_json: dict[str, Any],
    product_name: str,
    dest: Path,
    disclaimer: str,
) -> Path:
    with Image.open(room_image_path) as img:
        frame = img.convert("RGB")
    draw = ImageDraw.Draw(frame)
    left, top, right, bottom = bbox_to_pixel_rect(frame.size, geometry_json)
    draw.rectangle((left, top, right, bottom), outline=(255, 180, 40), width=4)
    draw.rectangle((left, max(0, top - 28), min(frame.size[0], right), top), fill=(20, 20, 20))
    draw.text((left + 6, max(0, top - 24)), product_name[:48], fill=(255, 255, 255))
    draw.rectangle((12, frame.size[1] - 48, frame.size[0] - 12, frame.size[1] - 12), fill=(20, 20, 20))
    draw.text((24, frame.size[1] - 40), disclaimer[:120], fill=(255, 230, 180))
    dest.parent.mkdir(parents=True, exist_ok=True)
    frame.save(dest, format="PNG")
    return dest

from __future__ import annotations

from pathlib import Path

from PIL import Image

from design_dataset.domain.errors import DesignDatasetError


SUPPORTED_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def discover_images(
    root: Path,
    *,
    allowed_extensions: list[str],
    max_file_mb: int,
) -> list[Path]:
    if not root.exists():
        raise DesignDatasetError(f"Input path does not exist: {root}")
    allowed = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in allowed_extensions}
    max_bytes = max_file_mb * 1024 * 1024
    discovered: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in allowed:
            continue
        if path.stat().st_size > max_bytes:
            continue
        discovered.append(path.resolve())
    return discovered


def read_image_metadata(path: Path) -> tuple[str | None, int | None, int | None]:
    mime = SUPPORTED_MIME.get(path.suffix.lower())
    try:
        with Image.open(path) as img:
            width, height = img.size
            return mime, width, height
    except OSError:
        return mime, None, None

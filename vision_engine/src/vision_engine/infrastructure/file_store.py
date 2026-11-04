from __future__ import annotations

import hashlib
import shutil
import uuid
from pathlib import Path

from PIL import Image

from vision_engine.domain.errors import ImageError


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_image(path: Path, *, allowed: set[str] | None = None, max_mb: int = 25) -> tuple[str | None, int | None, int | None]:
    allowed = allowed or ALLOWED_EXTENSIONS
    if not path.exists():
        raise ImageError(f"Image not found: {path}")
    if path.suffix.lower() not in allowed:
        raise ImageError(f"Unsupported image format: {path.suffix}")
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > max_mb:
        raise ImageError(f"Image exceeds {max_mb}MB limit: {path}")
    try:
        with Image.open(path) as img:
            width, height = img.size
            mime = Image.MIME.get(img.format or "", None)
    except Exception as exc:  # noqa: BLE001
        raise ImageError(
            f"Invalid image file: {path} ({type(exc).__name__}: {exc})"
        ) from exc
    return mime, width, height


class FileStore:
    """Local filesystem store for uploads, generated images, and raw responses."""

    def __init__(self, *, uploads_dir: Path, generated_dir: Path, root: Path):
        self.root = root
        self.uploads_dir = uploads_dir
        self.generated_dir = generated_dir
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        (self.generated_dir / "raw").mkdir(parents=True, exist_ok=True)

    def relative(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(path)

    def store_upload(
        self,
        source: Path,
        *,
        project_id: str,
        role: str,
        allowed: set[str] | None = None,
        max_mb: int = 25,
    ) -> tuple[Path, str, str | None, int | None, int | None]:
        mime, width, height = validate_image(source, allowed=allowed, max_mb=max_mb)
        digest = sha256_file(source)
        dest_dir = self.uploads_dir / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{role}_{digest[:12]}{source.suffix.lower()}"
        if not dest.exists():
            # Uploads are content-addressed; preserving source xattrs is
            # unnecessary and can fail for macOS Downloads files.
            shutil.copyfile(source, dest)
        return dest, digest, mime, width, height

    def store_generated(
        self,
        *,
        project_id: str,
        variant_key: str,
        image_bytes: bytes,
        extension: str = ".png",
    ) -> Path:
        dest_dir = self.generated_dir / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{variant_key}{extension}"
        dest.write_bytes(image_bytes)
        return dest

    def store_raw_json(self, *, project_id: str, name: str, payload: str) -> Path:
        dest_dir = self.generated_dir / "raw" / project_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{name}.json"
        dest.write_text(payload, encoding="utf-8")
        return dest

    def delete_project_files(self, project_id: str) -> None:
        for base in (self.uploads_dir / project_id, self.generated_dir / project_id):
            if base.exists():
                shutil.rmtree(base, ignore_errors=True)
        raw = self.generated_dir / "raw" / project_id
        if raw.exists():
            shutil.rmtree(raw, ignore_errors=True)

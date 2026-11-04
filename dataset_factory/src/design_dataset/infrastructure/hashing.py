from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def request_fingerprint(
    *,
    image_sha256: str,
    rulebook_version: str,
    prompt_version: str,
    provider: str,
    model_name: str,
    generation_settings: dict[str, Any] | None = None,
) -> str:
    payload = {
        "image_sha256": image_sha256,
        "rulebook_version": rulebook_version,
        "prompt_version": prompt_version,
        "provider": provider,
        "model_name": model_name,
        "generation_settings": generation_settings or {},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

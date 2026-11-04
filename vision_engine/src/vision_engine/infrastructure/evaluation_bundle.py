from __future__ import annotations

import json
import shutil
from pathlib import Path

from vision_engine.infrastructure.content_hash import sha256_file, sha256_json


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def copy_verified_image(source: Path, dest: Path, expected_sha256: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Evaluation bundles care about verified bytes, not source filesystem
    # metadata. copy2 can fail on macOS when Downloads files carry protected
    # com.apple.macl or quarantine attributes.
    shutil.copyfile(source, dest)
    actual = sha256_file(dest)
    if actual != expected_sha256:
        raise ValueError(
            f"Copied image hash mismatch for {dest.name}: expected {expected_sha256}, got {actual}"
        )


def manifest_sha256(manifest: dict) -> str:
    return sha256_json(manifest)

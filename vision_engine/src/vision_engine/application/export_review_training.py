from __future__ import annotations

from pathlib import Path

from vision_engine.infrastructure.exporters import export_review_training_rows
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


def export_review_training_dataset(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    output: Path,
    fmt: str = "jsonl",
) -> tuple[Path, int]:
    rows = repo.list_review_training_export()
    dest = output if output.is_absolute() else settings.resolve(output)
    return export_review_training_rows(rows, dest, fmt=fmt)


def export_approved_concepts(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    output: Path,
    fmt: str = "jsonl",
) -> tuple[Path, int]:
    manifests = repo.list_approved_manifests(include_withdrawn=False)
    rows = [m.manifest_json for m in manifests]
    dest = output if output.is_absolute() else settings.resolve(output)
    return export_review_training_rows(rows, dest, fmt=fmt)

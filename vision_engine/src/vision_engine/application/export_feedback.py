from __future__ import annotations

from pathlib import Path

from vision_engine.infrastructure.exporters import export_feedback
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


def export_feedback_dataset(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    output: Path,
    fmt: str = "jsonl",
    project_id: str | None = None,
) -> tuple[Path, int]:
    events = repo.list_feedback(project_id=project_id)
    dest = output if output.is_absolute() else settings.resolve(output)
    return export_feedback(events, dest, fmt=fmt)

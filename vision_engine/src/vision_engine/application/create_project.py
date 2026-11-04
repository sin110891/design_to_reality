from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from vision_engine.domain.enums import ProjectStatus
from vision_engine.domain.models import ProjectInput, ProjectRecord, UploadRecord
from vision_engine.infrastructure.file_store import FileStore, new_id
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_project(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore,
    payload: ProjectInput,
) -> ProjectRecord:
    project_id = new_id("proj")
    now = utcnow()

    room_src = Path(payload.room_image_path)
    if not room_src.is_absolute():
        room_src = settings.resolve(room_src)

    allowed = set(settings.images.allowed_extensions)
    room_dest, room_sha, mime, width, height = file_store.store_upload(
        room_src,
        project_id=project_id,
        role="room",
        allowed=allowed,
        max_mb=settings.images.max_file_mb,
    )

    inspiration_paths: list[str] = []
    inspiration_uploads: list[tuple[str, str, str | None, int | None, int | None]] = []
    for idx, insp in enumerate(payload.inspiration_image_paths):
        insp_src = Path(insp)
        if not insp_src.is_absolute():
            insp_src = settings.resolve(insp_src)
        dest, sha, mime_i, w, h = file_store.store_upload(
            insp_src,
            project_id=project_id,
            role=f"inspiration_{idx + 1}",
            allowed=allowed,
            max_mb=settings.images.max_file_mb,
        )
        inspiration_paths.append(file_store.relative(dest))
        inspiration_uploads.append((f"inspiration_{idx + 1}", sha, mime_i, w, h))

    project = ProjectRecord(
        project_id=project_id,
        room_image_path=file_store.relative(room_dest),
        inspiration_image_paths=inspiration_paths,
        room_type=payload.room_type,
        style_family=payload.style_family,
        brief=payload.brief.strip(),
        budget_band=payload.budget_band,
        constraints=list(payload.constraints),
        project_type=payload.project_type,
        status=ProjectStatus.CREATED,
        created_at=now,
        updated_at=now,
    )
    # Persist project first so upload foreign keys succeed.
    repo.save_project(project)
    repo.save_upload(
        UploadRecord(
            upload_id=new_id("up"),
            project_id=project_id,
            role="room",
            relative_path=file_store.relative(room_dest),
            sha256=room_sha,
            mime_type=mime,
            width=width,
            height=height,
            created_at=now,
        )
    )
    for role, sha, mime_i, w, h in inspiration_uploads:
        # relative path already recorded on the project; re-derive from role slot
        idx = int(role.rsplit("_", 1)[-1]) - 1
        repo.save_upload(
            UploadRecord(
                upload_id=new_id("up"),
                project_id=project_id,
                role=role,
                relative_path=inspiration_paths[idx],
                sha256=sha,
                mime_type=mime_i,
                width=w,
                height=h,
                created_at=now,
            )
        )
    return project

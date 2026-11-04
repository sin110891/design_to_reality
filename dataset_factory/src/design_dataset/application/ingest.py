from __future__ import annotations

from pathlib import Path

from design_dataset.domain.enums import ReviewStatus, SourceType, UsageRightsStatus
from design_dataset.domain.models import BatchReport, ImageRecord
from design_dataset.infrastructure.filesystem import discover_images, read_image_metadata
from design_dataset.infrastructure.hashing import sha256_file
from design_dataset.infrastructure.sqlite_repository import SqliteRepository, new_id, utcnow
from design_dataset.settings import AppSettings


def ingest_images(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    input_dir: Path,
    source_type: SourceType = SourceType.LOCAL_FOLDER,
    usage_rights_status: UsageRightsStatus = UsageRightsStatus.UNKNOWN,
) -> BatchReport:
    report = BatchReport()
    paths = discover_images(
        input_dir,
        allowed_extensions=settings.images.allowed_extensions,
        max_file_mb=settings.images.max_file_mb,
    )
    report.discovered = len(paths)
    root = settings.project_root

    for path in paths:
        digest = sha256_file(path)
        existing = repo.get_image_by_sha(digest)
        if existing:
            report.duplicates_skipped += 1
            continue
        mime, width, height = read_image_metadata(path)
        try:
            relative = str(path.relative_to(root))
        except ValueError:
            relative = str(path)
        image = ImageRecord(
            image_id=new_id("img"),
            relative_path=relative,
            sha256=digest,
            mime_type=mime,
            width=width,
            height=height,
            source_type=source_type,
            source_url=None,
            usage_rights_status=usage_rights_status,
            created_at=utcnow(),
        )
        _, created = repo.upsert_image(image)
        if created:
            report.ingested += 1
        else:
            report.duplicates_skipped += 1
    return report


# Re-export for callers that want the ingested placeholder status concept.
INGESTED_STATUS = ReviewStatus.INGESTED

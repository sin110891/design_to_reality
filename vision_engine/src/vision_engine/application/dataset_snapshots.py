from __future__ import annotations

import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from vision_engine.domain.enums import (
    AnnotationRevisionStatus,
    DatasetSnapshotStatus,
    RetentionConsentStatus,
    ReviewStatus,
    RightsStatus,
)
from vision_engine.domain.models import DatasetRecord
from vision_engine.domain.retrieval_models import (
    CuratedDatasetSnapshot,
    ReferenceAnnotationRevision,
    ReferenceImageAsset,
    SnapshotReferenceRecord,
)
from vision_engine.infrastructure.content_hash import sha256_file, sha256_json
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _rights_for_record(record: DatasetRecord) -> RightsStatus:
    if record.usage_rights_status == "restricted":
        return RightsStatus.RESTRICTED
    if record.usage_rights_status == "licensed_for_internal_review":
        return RightsStatus.LICENSED_FOR_INTERNAL_REVIEW
    return RightsStatus.LICENSED_FOR_INTERNAL_REVIEW


def backfill_reference_asset(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    record: DatasetRecord,
    image_path: Path,
) -> ReferenceImageAsset:
    existing = repo.get_reference_asset_by_image(record.image_id)
    image_sha = sha256_file(image_path)
    if existing and existing.image_sha256 == image_sha:
        return existing

    width = height = None
    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except OSError:
        pass
    mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
    asset = ReferenceImageAsset(
        reference_asset_id=existing.reference_asset_id if existing else new_id("rasset"),
        image_id=record.image_id,
        image_sha256=image_sha,
        storage_uri=str(image_path.resolve()),
        mime_type=mime_type,
        width=width,
        height=height,
        file_size_bytes=image_path.stat().st_size,
        rights_status=_rights_for_record(record),
        retention_consent_status=RetentionConsentStatus.INTERNAL_REVIEW_ONLY,
        created_at=existing.created_at if existing else utcnow(),
    )
    repo.save_reference_asset(asset)
    return asset


def backfill_annotation_revision(
    *,
    repo: SqliteRepository,
    record: DatasetRecord,
    reviewer: str = "system",
) -> ReferenceAnnotationRevision:
    existing = repo.get_latest_annotation_revision(record.image_id)
    annotation_json = record.model_dump_json()
    annotation_sha = sha256_json(json.loads(annotation_json))
    if existing and existing.annotation_sha256 == annotation_sha:
        return existing

    revision_number = (existing.revision_number + 1) if existing else 1
    revision = ReferenceAnnotationRevision(
        annotation_revision_id=new_id("ann"),
        image_id=record.image_id,
        revision_number=revision_number,
        annotation_json=annotation_json,
        annotation_sha256=annotation_sha,
        reviewer=reviewer,
        status=AnnotationRevisionStatus.APPROVED,
        created_at=utcnow(),
    )
    repo.save_annotation_revision(revision)
    return revision


def create_sealed_snapshot_from_records(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    records: list[DatasetRecord],
    snapshot_name: str,
    resolve_image_path,
) -> CuratedDatasetSnapshot:
    """Create and seal an immutable snapshot from approved curated records."""
    eligible = [
        r
        for r in records
        if r.review_status == ReviewStatus.APPROVED and _rights_for_record(r) != RightsStatus.RESTRICTED
    ]
    if not eligible:
        raise ValueError("No approved, non-restricted records available for snapshot")

    manifest_entries: list[dict[str, str]] = []
    snapshot_id = new_id("snap")
    pending_refs: list[SnapshotReferenceRecord] = []
    for record in eligible:
        image_path = resolve_image_path(record)
        if image_path is None or not image_path.exists():
            continue
        asset = backfill_reference_asset(
            repo=repo, settings=settings, record=record, image_path=image_path
        )
        revision = backfill_annotation_revision(repo=repo, record=record)
        record_sha = sha256_json(
            {
                "image_id": record.image_id,
                "image_sha256": asset.image_sha256,
                "annotation_sha256": revision.annotation_sha256,
            }
        )
        snap_ref = SnapshotReferenceRecord(
            snapshot_reference_record_id=new_id("sref"),
            dataset_snapshot_id=snapshot_id,
            image_id=record.image_id,
            reference_asset_id=asset.reference_asset_id,
            annotation_revision_id=revision.annotation_revision_id,
            record_sha256=record_sha,
        )
        pending_refs.append(snap_ref)
        manifest_entries.append(
            {
                "snapshot_reference_record_id": snap_ref.snapshot_reference_record_id,
                "image_id": record.image_id,
                "record_sha256": record_sha,
            }
        )

    if not manifest_entries:
        raise ValueError("No resolvable records for snapshot")

    manifest_dir = settings.resolve(Path("data/snapshots"))
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{snapshot_name}.manifest.json"
    manifest_path.write_text(json.dumps(manifest_entries, indent=2), encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    now = utcnow()
    snapshot = CuratedDatasetSnapshot(
        dataset_snapshot_id=snapshot_id,
        snapshot_name=snapshot_name,
        manifest_uri=str(manifest_path),
        manifest_sha256=manifest_sha,
        record_count=len(manifest_entries),
        status=DatasetSnapshotStatus.SEALED,
        created_at=now,
        sealed_at=now,
    )
    repo.save_dataset_snapshot(snapshot)
    for snap_ref in pending_refs:
        repo.save_snapshot_reference_record(snap_ref)
    return snapshot

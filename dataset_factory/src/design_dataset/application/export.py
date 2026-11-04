from __future__ import annotations

from pathlib import Path

from design_dataset.domain.enums import ReviewStatus, UsageRightsStatus
from design_dataset.domain.models import CurationRecord
from design_dataset.infrastructure.exporters import export_gold
from design_dataset.infrastructure.sqlite_repository import SqliteRepository


def _canonical_record_per_image(
    records: list[CurationRecord],
) -> list[CurationRecord]:
    """Keep one approved record per content-addressed image for downstream indexes."""
    selected = {}
    for record in records:
        current = selected.get(record.image_id)
        if current is None:
            selected[record.image_id] = record
            continue
        record_key = (
            record.provider != "fake",
            record.final_label is not None,
            record.approved_at.isoformat() if record.approved_at else "",
        )
        current_key = (
            current.provider != "fake",
            current.final_label is not None,
            current.approved_at.isoformat() if current.approved_at else "",
        )
        if record_key > current_key:
            selected[record.image_id] = record
    return list(selected.values())


def export_gold_dataset(
    *,
    repo: SqliteRepository,
    output: Path,
    fmt: str,
    include_restricted: bool = False,
) -> tuple[Path, int]:
    records = repo.list_curation_records(statuses=[ReviewStatus.APPROVED])
    if not include_restricted:
        records = [
            r
            for r in records
            if r.usage_rights_status != UsageRightsStatus.RESTRICTED
        ]
    records = _canonical_record_per_image(records)
    path = export_gold(records, output, fmt=fmt)
    return path, len(records)

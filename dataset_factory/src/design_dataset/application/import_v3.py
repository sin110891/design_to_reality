from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from design_dataset.domain.enums import UsageRightsStatus
from design_dataset.domain.errors import ReviewImportError
from design_dataset.domain.models import ExpertReferenceMetadata, ReviewEvent
from design_dataset.infrastructure.hashing import sha256_file
from design_dataset.infrastructure.sqlite_repository import SqliteRepository, new_id, utcnow
from design_dataset.settings import AppSettings


DEFAULT_SHEET = "Collection Example"

_COLUMN_MAP = {
    "project_id": "project_id",
    "room_id": "room_id",
    "source_name": "source_name",
    "source_url_or_path": "source_url_or_path",
    "license_status": "license_status",
    "project_type": "project_type",
    "Typology": "typology",
    "image_type": "image_type",
    "geography": "geography",
    "Colour Scheme (Des)": "colour_scheme",
    "budget_band": "budget_band",
    "build_complexity": "build_complexity",
    "maintenance_level": "maintenance_level",
    "primary_trade": "primary_trade",
    "notes_on_why (descriptive)": "notes_on_why",
}

_LIST_COLUMN_MAP = {
    "style_family (Des)": "style_family",
    "mood (Des)": "mood",
    "colour_palette (Obs)": "colour_palette",
    "Material-Floor (Obs)": "material_floor",
    "Material-Wall (Obs)": "material_wall",
    "Material-Furniture (Obs)": "material_furniture",
    "Material-Ceiling (Obs)": "material_ceiling",
    "lighting_type (Obs)": "lighting_type",
    "furniture_style (Obs)": "furniture_style",
    "spatial_feel (Des)": "spatial_feel",
    "likely_trades_required": "likely_trades_required",
    "secondary_trades": "secondary_trades",
}

_SCORE_COLUMN_MAP = {
    "architect_quality_score": "architect_quality_score",
    "buildability_score": "buildability_score",
    "relevance_score": "relevance_score",
}

_RIGHTS_MAP = {
    "owned": UsageRightsStatus.STUDIO_OWNED,
    "licensed": UsageRightsStatus.LICENSED_FOR_ANALYSIS,
    "fair use review needed": UsageRightsStatus.INTERNAL_REFERENCE_ONLY,
    "public domain": UsageRightsStatus.PERMISSION_GRANTED,
    "unknown": UsageRightsStatus.UNKNOWN,
}


def import_v3_annotations(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    input_path: Path,
    sheet_name: str = DEFAULT_SHEET,
) -> dict[str, Any]:
    """Import human V3 annotations without replacing model/audit provenance."""
    if not input_path.exists():
        raise ReviewImportError(f"V3 workbook not found: {input_path}")

    try:
        frame = pd.read_excel(input_path, sheet_name=sheet_name, header=1)
    except ValueError as exc:
        raise ReviewImportError(
            f"Missing V3 sheet {sheet_name!r} in {input_path.name}"
        ) from exc

    required = {"image_id", "project_id", "Typology"}
    missing = required - set(frame.columns)
    if missing:
        raise ReviewImportError(f"Missing V3 columns: {sorted(missing)}")

    records = repo.list_curation_records()
    records_by_image: dict[str, list] = {}
    records_by_sha: dict[str, list] = {}
    records_by_filename: dict[str, list] = {}
    for record in records:
        records_by_image.setdefault(record.image_id, []).append(record)
        records_by_sha.setdefault(record.sha256, []).append(record)
        records_by_filename.setdefault(_filename_key(record.file_path), []).append(record)

    source_dirs = {
        settings.resolve(Path(record.file_path).parent)
        for record in records
        if record.file_path
    }
    annotations_by_image: dict[str, ExpertReferenceMetadata] = {}
    counts: dict[str, Any] = {
        "workbook_rows": 0,
        "matched_rows": 0,
        "unique_images": 0,
        "records_updated": 0,
        "duplicate_rows_skipped": 0,
        "non_image_rows_skipped": 0,
        "unmatched_image_ids": [],
    }

    for frame_index, row in frame.iterrows():
        source_image_id = _clean(row.get("image_id"))
        if not source_image_id:
            continue
        counts["workbook_rows"] += 1
        matched_records = records_by_filename.get(_filename_key(source_image_id), [])
        if not matched_records:
            source_path = _find_source_path(source_dirs, source_image_id)
            if source_path:
                matched_records = records_by_sha.get(sha256_file(source_path), [])
        if not matched_records:
            counts["non_image_rows_skipped"] += 1
            counts["unmatched_image_ids"].append(source_image_id)
            continue

        source_row = int(frame_index) + 3
        metadata = _row_to_metadata(
            row,
            source_image_id=source_image_id,
            source_workbook=input_path.name,
            source_sheet=sheet_name,
            source_row=source_row,
        )
        target_image_id = matched_records[0].image_id
        existing = annotations_by_image.get(target_image_id)
        if existing:
            if _semantic_payload(existing) != _semantic_payload(metadata):
                raise ReviewImportError(
                    f"Conflicting V3 rows map to image {target_image_id}: "
                    f"{existing.source_row} and {metadata.source_row}"
                )
            counts["duplicate_rows_skipped"] += 1
            continue

        annotations_by_image[target_image_id] = metadata
        counts["matched_rows"] += 1

    for image_id, metadata in annotations_by_image.items():
        for record in records_by_image[image_id]:
            old_metadata = record.expert_metadata
            old_json = (
                old_metadata.model_dump_json()
                if old_metadata is not None
                else None
            )
            new_json = metadata.model_dump_json()
            if old_json == new_json:
                continue
            record.expert_metadata = metadata
            source_url = _clean(metadata.source_url_or_path)
            if source_url:
                record.source_url = source_url
            rights = _RIGHTS_MAP.get((metadata.license_status or "").lower())
            if rights is not None:
                record.usage_rights_status = rights
            record.updated_at = utcnow()
            repo.update_curation_record(record)
            repo.add_review_events(
                [
                    ReviewEvent(
                        event_id=new_id("evt"),
                        record_id=record.record_id,
                        field_name="expert_metadata",
                        old_value=old_json,
                        new_value=new_json,
                        actor=settings.review.curator_name,
                        created_at=record.updated_at,
                    )
                ]
            )
            counts["records_updated"] += 1

    counts["unique_images"] = len(annotations_by_image)
    counts["unmatched_image_ids"] = sorted(set(counts["unmatched_image_ids"]))
    return counts


def _row_to_metadata(
    row: pd.Series,
    *,
    source_image_id: str,
    source_workbook: str,
    source_sheet: str,
    source_row: int,
) -> ExpertReferenceMetadata:
    payload: dict[str, Any] = {
        "source_image_id": source_image_id,
        "source_workbook": source_workbook,
        "source_sheet": source_sheet,
        "source_row": source_row,
    }
    for source, target in _COLUMN_MAP.items():
        payload[target] = _clean(row.get(source))
    for source, target in _LIST_COLUMN_MAP.items():
        payload[target] = _split_list(row.get(source))
    payload["material_palette"] = _parse_tagged_materials(
        row.get("material_palette (Obs) - tag elements as well.")
    )
    for source, target in _SCORE_COLUMN_MAP.items():
        payload[target] = _score(row.get(source), source_image_id, source)
    return ExpertReferenceMetadata.model_validate(payload)


def _find_source_path(source_dirs: set[Path], source_image_id: str) -> Path | None:
    for directory in source_dirs:
        candidate = directory / source_image_id
        if candidate.exists():
            return candidate
    return None


def _filename_key(value: str) -> str:
    stem = Path(value).name.lower()
    if stem.endswith(".jpg"):
        stem = stem[:-4]
    if stem.endswith(".pg"):
        stem = stem[:-3]
    return re.sub(r"[^a-z0-9]+", "", stem)


def _clean(value: Any) -> str | None:
    if value is None or bool(pd.isna(value)):
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    return text


def _split_list(value: Any) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _parse_tagged_materials(value: Any) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    tagged = [
        re.sub(r"\s+", " ", part.replace(":", ": ", 1)).strip()
        for part in re.findall(r"\{([^{}]+)\}", text)
    ]
    return tagged or _split_list(text)


def _score(value: Any, image_id: str, column: str) -> float | None:
    text = _clean(value)
    if text is None:
        return None
    try:
        score = float(text)
    except ValueError as exc:
        raise ReviewImportError(
            f"Invalid {column} for {image_id}: {text!r}"
        ) from exc
    if not 1.0 <= score <= 5.0:
        raise ReviewImportError(
            f"{column} for {image_id} must be between 1 and 5"
        )
    return score


def _semantic_payload(metadata: ExpertReferenceMetadata) -> str:
    payload = metadata.model_dump(
        exclude={"source_image_id", "source_row"},
        exclude_none=True,
    )
    return json.dumps(payload, sort_keys=True)

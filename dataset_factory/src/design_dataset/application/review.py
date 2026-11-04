from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from design_dataset.domain.enums import ReviewStatus
from design_dataset.domain.errors import ReviewImportError
from design_dataset.domain.models import DesignLabelDraft, ReviewEvent
from design_dataset.domain.policies import validate_against_rulebook
from design_dataset.domain.rulebook import load_rulebook
from design_dataset.infrastructure.exporters import export_review_xlsx
from design_dataset.infrastructure.sqlite_repository import SqliteRepository, new_id, utcnow
from design_dataset.settings import AppSettings


REVIEWABLE = {
    ReviewStatus.DRAFT,
    ReviewStatus.VALIDATION_FAILED,
    ReviewStatus.REVIEWED,
    ReviewStatus.APPROVED,
    ReviewStatus.REJECTED,
}


def export_for_review(
    *,
    repo: SqliteRepository,
    output: Path,
    statuses: list[ReviewStatus] | None = None,
) -> Path:
    selected = statuses or [ReviewStatus.DRAFT, ReviewStatus.VALIDATION_FAILED, ReviewStatus.REVIEWED]
    records = repo.list_curation_records(statuses=selected)
    return export_review_xlsx(records, output)


def import_reviewed(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    input_path: Path,
) -> dict[str, int]:
    if not input_path.exists():
        raise ReviewImportError(f"Review file not found: {input_path}")
    rulebook = load_rulebook(settings.rulebook_path)
    df = pd.read_excel(input_path)
    if df.empty:
        return {"updated": 0, "approved": 0, "rejected": 0, "reviewed": 0}

    required = {"record_id", "review_status"}
    missing = required - set(df.columns)
    if missing:
        raise ReviewImportError(f"Missing required columns: {sorted(missing)}")

    counts = {"updated": 0, "approved": 0, "rejected": 0, "reviewed": 0}
    actor = settings.review.curator_name

    for _, row in df.iterrows():
        record_id = str(row["record_id"]).strip()
        record = repo.get_curation_record(record_id)
        if record is None:
            raise ReviewImportError(f"Unknown record_id: {record_id}")

        status_raw = str(row["review_status"]).strip().lower()
        try:
            new_status = ReviewStatus(status_raw)
        except ValueError as exc:
            raise ReviewImportError(f"Invalid review_status for {record_id}: {status_raw}") from exc

        if new_status not in REVIEWABLE:
            raise ReviewImportError(f"Unsupported review_status for {record_id}: {status_raw}")

        label_payload = _row_to_label_payload(row)
        # Prefer edited fields; fall back to existing draft.
        if record.draft_label is not None:
            base = record.draft_label.model_dump()
            merged = _deep_merge(base, label_payload)
        else:
            merged = label_payload

        try:
            candidate = DesignLabelDraft.model_validate(merged)
        except Exception as exc:  # noqa: BLE001
            raise ReviewImportError(f"Invalid label for {record_id}: {exc}") from exc

        validation = validate_against_rulebook(candidate, rulebook)
        if not validation.ok:
            raise ReviewImportError(
                f"Rulebook validation failed for {record_id}: {'; '.join(validation.errors)}"
            )
        assert validation.label is not None

        events = _diff_events(
            record_id=record.record_id,
            old_label=record.final_label or record.draft_label,
            new_label=validation.label,
            old_status=record.status,
            new_status=new_status,
            actor=actor,
            curator_notes=str(row.get("curator_notes") or "") or None,
            old_notes=record.curator_notes,
        )

        now = utcnow()
        record.final_label = validation.label
        record.status = new_status
        record.curator_name = actor
        record.curator_notes = str(row.get("curator_notes") or "") or None
        record.review_warnings = validation.warnings
        record.updated_at = now
        record.reviewed_at = now
        record.approved_at = now if new_status == ReviewStatus.APPROVED else None
        repo.update_curation_record(record)
        repo.add_review_events(events)

        counts["updated"] += 1
        if new_status == ReviewStatus.APPROVED:
            counts["approved"] += 1
        elif new_status == ReviewStatus.REJECTED:
            counts["rejected"] += 1
        elif new_status == ReviewStatus.REVIEWED:
            counts["reviewed"] += 1

    return counts


def _row_to_label_payload(row: pd.Series) -> dict[str, Any]:
    mapping = {
        "style_family": "style_family",
        "mood": "mood",
        "material_palette": "material_palette",
        "budget_band": "budget_band",
        "primary_trade": "primary_trade",
        "likely_trades_required": "likely_trades_required",
        "room_type": "room_type",
        "confidence_notes": "confidence_notes",
        "visible_uncertainties": "visible_uncertainties",
    }
    positive_fields = [
        "design_move",
        "why_it_works",
        "focal_point",
        "material_relationship",
        "lighting_strategy",
        "proportion_rule",
        "circulation_strategy",
        "visual_hierarchy",
        "appropriate_room_conditions",
    ]
    negative_fields = [
        "design_failure",
        "why_it_fails",
        "scale_problem",
        "material_conflict",
        "lighting_problem",
        "impractical_detail",
        "generic_ai_artifact",
        "structural_violation",
    ]
    payload: dict[str, Any] = {}
    for col, key in mapping.items():
        if col in row and not _is_nan(row[col]):
            payload[key] = _parse_maybe_list(row[col], is_list=key in {
                "mood",
                "material_palette",
                "likely_trades_required",
                "visible_uncertainties",
            })
    positive: dict[str, Any] = {}
    for field in positive_fields:
        col = f"positive.{field}"
        if col in row and not _is_nan(row[col]):
            positive[field] = _parse_maybe_list(
                row[col], is_list=field == "appropriate_room_conditions"
            )
    negative: dict[str, Any] = {}
    for field in negative_fields:
        col = f"negative.{field}"
        if col in row and not _is_nan(row[col]):
            negative[field] = row[col]
    if positive:
        payload["positive"] = positive
    if negative:
        payload["negative"] = negative
    return payload


def _parse_maybe_list(value: Any, *, is_list: bool) -> Any:
    if not is_list:
        return value
    if isinstance(value, list):
        return value
    text = str(value).strip()
    if not text:
        return []
    if "|" in text:
        return [part.strip() for part in text.split("|") if part.strip()]
    if text.startswith("["):
        return json.loads(text)
    return [part.strip() for part in text.split(",") if part.strip()]


def _is_nan(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except Exception:  # noqa: BLE001
        return False


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _diff_events(
    *,
    record_id: str,
    old_label: DesignLabelDraft | None,
    new_label: DesignLabelDraft,
    old_status: ReviewStatus,
    new_status: ReviewStatus,
    actor: str,
    curator_notes: str | None,
    old_notes: str | None,
) -> list[ReviewEvent]:
    events: list[ReviewEvent] = []
    now = utcnow()
    if old_status != new_status:
        events.append(
            ReviewEvent(
                event_id=new_id("evt"),
                record_id=record_id,
                field_name="review_status",
                old_value=old_status.value,
                new_value=new_status.value,
                actor=actor,
                created_at=now,
            )
        )
    if (old_notes or "") != (curator_notes or ""):
        events.append(
            ReviewEvent(
                event_id=new_id("evt"),
                record_id=record_id,
                field_name="curator_notes",
                old_value=old_notes,
                new_value=curator_notes,
                actor=actor,
                created_at=now,
            )
        )
    old_flat = _flatten(old_label.model_dump()) if old_label else {}
    new_flat = _flatten(new_label.model_dump())
    for key, new_value in new_flat.items():
        old_value = old_flat.get(key)
        if old_value != new_value:
            events.append(
                ReviewEvent(
                    event_id=new_id("evt"),
                    record_id=record_id,
                    field_name=key,
                    old_value=None if old_value is None else str(old_value),
                    new_value=None if new_value is None else str(new_value),
                    actor=actor,
                    created_at=now,
                )
            )
    return events


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        full = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            out.update(_flatten(value, full))
        else:
            out[full] = value
    return out

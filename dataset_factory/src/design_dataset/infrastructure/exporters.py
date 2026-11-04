from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from design_dataset.domain.models import CurationRecord


def records_to_rows(records: list[CurationRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        label = record.final_label or record.draft_label
        draft = record.draft_label
        row: dict[str, Any] = {
            "record_id": record.record_id,
            "image_id": record.image_id,
            "file_path": record.file_path,
            "sha256": record.sha256,
            "review_status": record.status.value,
            "curator_name": record.curator_name or "",
            "curator_notes": record.curator_notes or "",
            "rulebook_version": record.rulebook_version,
            "prompt_version": record.prompt_version,
            "provider": record.provider,
            "model_name": record.model_name,
            "review_warnings": "; ".join(record.review_warnings),
            "validation_errors": "; ".join(record.validation_errors),
        }
        if record.expert_metadata:
            expert = _flatten_label(
                record.expert_metadata.model_dump(),
                prefix="expert.",
            )
            row.update(expert)
        if label:
            flat = _flatten_label(label.model_dump())
            for key, value in flat.items():
                row[key] = value
        if draft:
            flat_draft = _flatten_label(draft.model_dump(), prefix="draft_")
            for key, value in flat_draft.items():
                row[key] = value
        rows.append(row)
    return rows


def export_review_xlsx(records: list[CurationRecord], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records_to_rows(records))
    if "review_status" in df.columns:
        # Ensure curator can edit status freely in spreadsheet.
        pass
    df.to_excel(output, index=False)
    return output


def export_gold(
    records: list[CurationRecord],
    output: Path,
    *,
    fmt: str,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for record in records:
        label = record.final_label or record.draft_label
        payload.append(
            {
                "record_id": record.record_id,
                "image_id": record.image_id,
                "file_path": record.file_path,
                "sha256": record.sha256,
                "source_type": record.source_type.value,
                "source_url": record.source_url,
                "usage_rights_status": record.usage_rights_status.value,
                "rulebook_version": record.rulebook_version,
                "prompt_version": record.prompt_version,
                "provider": record.provider,
                "model_name": record.model_name,
                "status": record.status.value,
                "curator_name": record.curator_name,
                "curator_notes": record.curator_notes,
                "expert_metadata": (
                    record.expert_metadata.model_dump()
                    if record.expert_metadata
                    else None
                ),
                "draft_label": record.draft_label.model_dump() if record.draft_label else None,
                "final_label": label.model_dump() if label else None,
                "approved_at": record.approved_at.isoformat() if record.approved_at else None,
            }
        )

    fmt = fmt.lower()
    if fmt == "jsonl":
        with output.open("w", encoding="utf-8") as handle:
            for item in payload:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        return output
    if fmt == "csv":
        df = pd.json_normalize(payload)
        df.to_csv(output, index=False)
        return output
    if fmt == "parquet":
        df = pd.json_normalize(payload)
        df.to_parquet(output, index=False)
        return output
    raise ValueError(f"Unsupported export format: {fmt}")


def _flatten_label(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in data.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                out[f"{full}.{nested_key}"] = _serialize_cell(nested_value)
        else:
            out[full] = _serialize_cell(value)
    return out


def _serialize_cell(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return value

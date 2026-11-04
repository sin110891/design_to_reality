from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vision_engine.domain.enums import ReviewStatus
from vision_engine.domain.models import DatasetRecord
from vision_engine.domain.services import build_text_blob


def _compose_negative(label: dict[str, Any]) -> str | None:
    negative = label.get("negative") or {}
    parts: list[str] = []
    for key in (
        "why_it_fails",
        "design_failure",
        "scale_problem",
        "material_conflict",
        "lighting_problem",
        "impractical_detail",
        "generic_ai_artifact",
        "structural_violation",
    ):
        value = negative.get(key)
        if value:
            parts.append(str(value))
    return " | ".join(parts) if parts else None


def _derive_furniture_style(label: dict[str, Any]) -> str:
    positive = label.get("positive") or {}
    move = (positive.get("design_move") or "").lower()
    hierarchy = (positive.get("visual_hierarchy") or "").lower()
    blob = f"{move} {hierarchy}"
    if "sculptural" in blob:
        return "sculptural_minimal"
    if "organic" in blob or "soft" in blob:
        return "soft_organic"
    if "classic" in blob:
        return "warm_classic_modern"
    if "low" in blob or "restrained" in blob or "minimal" in blob:
        return "low_profile_contemporary"
    return "low_profile_contemporary"


def _derive_quality_scores(label: dict[str, Any], status: str) -> tuple[float, float]:
    """Heuristic scores until Lloyd rates quality explicitly in the factory."""
    positive = label.get("positive") or {}
    negative = label.get("negative") or {}
    architect = 3.5
    buildability = 3.5
    if positive.get("why_it_works") and len(str(positive["why_it_works"])) > 80:
        architect += 0.4
    if positive.get("proportion_rule"):
        architect += 0.2
    if negative.get("structural_violation"):
        buildability -= 0.8
    if negative.get("impractical_detail"):
        buildability -= 0.4
    if negative.get("generic_ai_artifact"):
        architect -= 0.5
    if status == "approved":
        architect += 0.3
        buildability += 0.2
    return (
        float(max(1.0, min(5.0, round(architect, 1)))),
        float(max(1.0, min(5.0, round(buildability, 1)))),
    )


def _string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _merge_unique(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            key = item.casefold()
            if key not in seen:
                seen.add(key)
                merged.append(item)
    return merged


def _normalise_project_type(value: str | None, fallback: str) -> str:
    key = (value or "").strip().lower()
    if key in {"domestic", "residential", "house", "apartment"}:
        return "residential"
    if key in {"hotel", "hospitality", "cafe", "restaurant"}:
        return "hospitality"
    if key in {"retail", "office"}:
        return key
    return fallback


def _normalise_room_type(typology: str | None, fallback: str | None) -> str | None:
    key = (typology or "").strip().lower()
    mappings = (
        ("living room", "living_room"),
        ("lounge", "living_room"),
        ("dining room", "dining_room"),
        ("kitchen", "kitchen"),
        ("bedroom", "bedroom"),
        ("bathroom", "bathroom"),
        ("spa", "bathroom"),
        ("corridor", "hallway"),
        ("hallway", "hallway"),
        ("lobby", "lobby"),
    )
    for needle, canonical in mappings:
        if needle in key:
            return canonical
    return fallback


def _normalise_style(expert_styles: list[str], fallback: str) -> str:
    joined = " ".join(expert_styles).lower()
    if "european" in joined and "contemporary" in joined:
        return "Contemporary Europe"
    return fallback


def gold_row_to_dataset_record(
    row: dict[str, Any],
    *,
    image_root: Path | None = None,
    default_project_type: str = "residential",
) -> DatasetRecord | None:
    """
    Adapt a dataset_factory gold JSONL row into a vision-engine DatasetRecord.

    Only approved (or explicitly draft-marked) rows are accepted. Restricted
    rights imagery is skipped.
    """
    status = str(row.get("status") or "").lower()
    if status not in {ReviewStatus.APPROVED.value, ReviewStatus.DRAFT.value, ReviewStatus.REVIEWED.value}:
        return None
    if str(row.get("usage_rights_status") or "").lower() == "restricted":
        return None

    label = row.get("final_label") or row.get("draft_label") or {}
    if not isinstance(label, dict):
        return None
    expert = row.get("expert_metadata") or {}
    if not isinstance(expert, dict):
        expert = {}

    positive = label.get("positive") or {}
    negative = label.get("negative") or {}
    file_path = str(row.get("file_path") or "")
    if image_root and file_path and not Path(file_path).is_absolute():
        # Prefer resolving relative to provided image root when only a basename is present.
        candidate = image_root / Path(file_path).name
        if candidate.exists():
            file_path = str(candidate)

    architect_quality, buildability = _derive_quality_scores(label, status)
    architect_quality = float(
        expert.get("architect_quality_score") or architect_quality
    )
    buildability = float(expert.get("buildability_score") or buildability)
    expert_styles = _string_list(expert.get("style_family"))
    expert_mood = _string_list(expert.get("mood"))
    expert_materials = _merge_unique(
        _string_list(expert.get("material_palette")),
        _string_list(expert.get("material_floor")),
        _string_list(expert.get("material_wall")),
        _string_list(expert.get("material_furniture")),
        _string_list(expert.get("material_ceiling")),
    )
    lighting_observations = _string_list(expert.get("lighting_type"))
    model_lighting = positive.get("lighting_strategy")
    lighting_strategy = " | ".join(
        part
        for part in (
            str(model_lighting).strip() if model_lighting else None,
            ", ".join(lighting_observations) if lighting_observations else None,
        )
        if part
    ) or None
    label_style = str(label.get("style_family") or "Contemporary Europe")
    record = DatasetRecord(
        image_id=str(row.get("image_id") or row.get("record_id")),
        image_path=file_path,
        source_project_id=expert.get("project_id"),
        source_room_id=expert.get("room_id"),
        source_name=expert.get("source_name"),
        source_url=expert.get("source_url_or_path") or row.get("source_url"),
        project_type=_normalise_project_type(
            expert.get("project_type"),
            default_project_type,
        ),
        room_type=_normalise_room_type(
            expert.get("typology"),
            label.get("room_type"),
        ),
        image_type=expert.get("image_type"),
        geography=expert.get("geography"),
        style_family=_normalise_style(expert_styles, label_style),
        expert_style_family=expert_styles,
        mood=_merge_unique(list(label.get("mood") or []), expert_mood),
        colour_palette=_string_list(expert.get("colour_palette")),
        material_palette=_merge_unique(
            list(label.get("material_palette") or []),
            expert_materials,
        ),
        material_floor=_string_list(expert.get("material_floor")),
        material_wall=_string_list(expert.get("material_wall")),
        material_furniture=_string_list(expert.get("material_furniture")),
        material_ceiling=_string_list(expert.get("material_ceiling")),
        colour_scheme=expert.get("colour_scheme"),
        lighting_strategy=lighting_strategy,
        furniture_style=(
            ", ".join(_string_list(expert.get("furniture_style")))
            or _derive_furniture_style(label)
        ),
        spatial_feel=_string_list(expert.get("spatial_feel")),
        budget_band=expert.get("budget_band") or label.get("budget_band"),
        build_complexity=expert.get("build_complexity"),
        maintenance_level=expert.get("maintenance_level"),
        architect_quality_score=architect_quality,
        buildability_score=buildability,
        relevance_score=expert.get("relevance_score"),
        positive_why_it_works=(
            expert.get("notes_on_why") or positive.get("why_it_works")
        ),
        negative_common_pitfalls=_compose_negative(label),
        primary_trade=expert.get("primary_trade") or label.get("primary_trade"),
        likely_trades_required=_merge_unique(
            list(label.get("likely_trades_required") or []),
            _string_list(expert.get("likely_trades_required")),
        ),
        secondary_trades=_string_list(expert.get("secondary_trades")),
        review_status=ReviewStatus(status) if status in ReviewStatus._value2member_map_ else ReviewStatus.DRAFT,
        focal_point=positive.get("focal_point"),
        circulation_strategy=positive.get("circulation_strategy"),
        visual_hierarchy=positive.get("visual_hierarchy"),
        proportion_rule=positive.get("proportion_rule"),
        material_relationship=positive.get("material_relationship"),
        appropriate_room_conditions=list(positive.get("appropriate_room_conditions") or []),
        design_failure=negative.get("design_failure"),
        why_it_fails=negative.get("why_it_fails"),
        scale_problem=negative.get("scale_problem"),
        material_conflict=negative.get("material_conflict"),
        lighting_problem=negative.get("lighting_problem"),
        impractical_detail=negative.get("impractical_detail"),
        generic_ai_artifact=negative.get("generic_ai_artifact"),
        structural_violation=negative.get("structural_violation"),
        source_record_id=row.get("record_id"),
        sha256=row.get("sha256"),
        usage_rights_status=row.get("usage_rights_status"),
        metadata={
            "rulebook_version": row.get("rulebook_version"),
            "prompt_version": row.get("prompt_version"),
            "provider": row.get("provider"),
            "model_name": row.get("model_name"),
            "curator_name": row.get("curator_name"),
            "expert_metadata": expert,
        },
    )
    record.text_blob = build_text_blob(record)
    return record


def load_gold_jsonl(
    path: Path,
    *,
    image_root: Path | None = None,
    approved_only: bool = True,
) -> list[DatasetRecord]:
    records: list[DatasetRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if approved_only and str(row.get("status") or "").lower() != ReviewStatus.APPROVED.value:
            continue
        record = gold_row_to_dataset_record(row, image_root=image_root)
        if record is not None:
            records.append(record)
    return records


def load_metadata_csv(path: Path, *, images_dir: Path) -> list[DatasetRecord]:
    """Load flat curated metadata CSV (vision-engine native format)."""
    import pandas as pd

    df = pd.read_csv(path)
    records: list[DatasetRecord] = []
    for _, row in df.iterrows():
        image_name = str(row.get("image_path") or row.get("file_name") or "")
        image_path = image_name
        if image_name and not Path(image_name).is_absolute():
            candidate = images_dir / Path(image_name).name
            image_path = str(candidate if candidate.exists() else images_dir / image_name)

        def split_list(value: Any) -> list[str]:
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return []
            text = str(value)
            if "|" in text:
                return [p.strip() for p in text.split("|") if p.strip()]
            if "," in text:
                return [p.strip() for p in text.split(",") if p.strip()]
            return [text.strip()] if text.strip() else []

        status = str(row.get("review_status") or ReviewStatus.APPROVED.value)
        record = DatasetRecord(
            image_id=str(row.get("image_id")),
            image_path=image_path,
            project_type=str(row.get("project_type") or "residential"),
            room_type=_maybe_str(row.get("room_type")),
            style_family=str(row.get("style_family") or "Contemporary Europe"),
            mood=split_list(row.get("mood")),
            material_palette=split_list(row.get("material_palette")),
            lighting_strategy=_maybe_str(row.get("lighting_strategy")),
            furniture_style=_maybe_str(row.get("furniture_style")),
            budget_band=_maybe_str(row.get("budget_band")),
            architect_quality_score=float(row.get("architect_quality_score") or 3.5),
            buildability_score=float(row.get("buildability_score") or 3.5),
            positive_why_it_works=_maybe_str(row.get("positive_why_it_works")),
            negative_common_pitfalls=_maybe_str(row.get("negative_common_pitfalls")),
            primary_trade=_maybe_str(row.get("primary_trade")),
            likely_trades_required=split_list(row.get("likely_trades_required")),
            review_status=ReviewStatus(status),
            focal_point=_maybe_str(row.get("focal_point")),
            circulation_strategy=_maybe_str(row.get("circulation_strategy")),
            visual_hierarchy=_maybe_str(row.get("visual_hierarchy")),
            proportion_rule=_maybe_str(row.get("proportion_rule")),
            material_relationship=_maybe_str(row.get("material_relationship")),
        )
        record.text_blob = build_text_blob(record)
        records.append(record)
    return records


def _maybe_str(value: Any) -> str | None:
    import pandas as pd

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None

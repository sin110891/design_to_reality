from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from design_dataset.domain.enums import (
    LabelRunStatus,
    ReviewStatus,
    SourceType,
    UsageRightsStatus,
)


class PositiveDesignKnowledge(BaseModel):
    design_move: str | None = None
    why_it_works: str = Field(min_length=5, max_length=800)
    focal_point: str | None = None
    material_relationship: str | None = None
    lighting_strategy: str | None = None
    proportion_rule: str | None = None
    circulation_strategy: str | None = None
    visual_hierarchy: str | None = None
    appropriate_room_conditions: list[str] = Field(default_factory=list, max_length=8)


class NegativeDesignKnowledge(BaseModel):
    design_failure: str | None = None
    why_it_fails: str = Field(min_length=5, max_length=800)
    scale_problem: str | None = None
    material_conflict: str | None = None
    lighting_problem: str | None = None
    impractical_detail: str | None = None
    generic_ai_artifact: str | None = None
    structural_violation: str | None = None


class ExpertReferenceMetadata(BaseModel):
    """Human-authored reference metadata imported from the Lloyd V3 workbook."""

    project_id: str | None = None
    room_id: str | None = None
    source_image_id: str | None = None
    source_name: str | None = None
    source_url_or_path: str | None = None
    license_status: str | None = None
    project_type: str | None = None
    typology: str | None = None
    image_type: str | None = None
    geography: str | None = None
    style_family: list[str] = Field(default_factory=list)
    mood: list[str] = Field(default_factory=list)
    colour_palette: list[str] = Field(default_factory=list)
    material_floor: list[str] = Field(default_factory=list)
    material_wall: list[str] = Field(default_factory=list)
    material_furniture: list[str] = Field(default_factory=list)
    material_ceiling: list[str] = Field(default_factory=list)
    colour_scheme: str | None = None
    material_palette: list[str] = Field(default_factory=list)
    lighting_type: list[str] = Field(default_factory=list)
    furniture_style: list[str] = Field(default_factory=list)
    spatial_feel: list[str] = Field(default_factory=list)
    budget_band: str | None = None
    build_complexity: str | None = None
    maintenance_level: str | None = None
    likely_trades_required: list[str] = Field(default_factory=list)
    primary_trade: str | None = None
    secondary_trades: list[str] = Field(default_factory=list)
    architect_quality_score: float | None = Field(default=None, ge=1.0, le=5.0)
    buildability_score: float | None = Field(default=None, ge=1.0, le=5.0)
    relevance_score: float | None = Field(default=None, ge=1.0, le=5.0)
    notes_on_why: str | None = None
    source_workbook: str
    source_sheet: str
    source_row: int = Field(ge=1)

    @field_validator(
        "style_family",
        "mood",
        "colour_palette",
        "material_floor",
        "material_wall",
        "material_furniture",
        "material_ceiling",
        "material_palette",
        "lighting_type",
        "furniture_style",
        "spatial_feel",
        "likely_trades_required",
        "secondary_trades",
        mode="before",
    )
    @classmethod
    def _strip_empty_lists(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return value


class DesignLabelDraft(BaseModel):
    style_family: str
    mood: list[str] = Field(min_length=1, max_length=5)
    material_palette: list[str] = Field(min_length=1, max_length=8)
    budget_band: str
    primary_trade: str
    likely_trades_required: list[str] = Field(min_length=1, max_length=8)
    room_type: str | None = None
    positive: PositiveDesignKnowledge
    negative: NegativeDesignKnowledge
    confidence_notes: str = Field(max_length=500)
    visible_uncertainties: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("mood", "material_palette", "likely_trades_required", "visible_uncertainties", mode="before")
    @classmethod
    def _strip_empty(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [item for item in value if item not in (None, "")]
        return value


class ModelCallMetadata(BaseModel):
    provider: str
    model_name: str
    request_id: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    attempt: int = 1


class ImageRecord(BaseModel):
    image_id: str
    relative_path: str
    sha256: str
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    source_type: SourceType = SourceType.LOCAL_FOLDER
    source_url: str | None = None
    usage_rights_status: UsageRightsStatus = UsageRightsStatus.UNKNOWN
    created_at: datetime


class LabelRunRecord(BaseModel):
    run_id: str
    image_id: str
    rulebook_version: str
    prompt_version: str
    provider: str
    model_name: str
    request_fingerprint: str
    raw_response_json: str | None = None
    parsed_response_json: dict[str, Any] | None = None
    status: LabelRunStatus
    error_type: str | None = None
    error_message: str | None = None
    created_at: datetime


class CurationRecord(BaseModel):
    record_id: str
    run_id: str
    image_id: str
    file_path: str
    sha256: str
    source_type: SourceType
    source_url: str | None
    usage_rights_status: UsageRightsStatus
    rulebook_version: str
    prompt_version: str
    provider: str
    model_name: str
    model_request_id: str | None
    draft_label: DesignLabelDraft | None
    final_label: DesignLabelDraft | None = None
    raw_response_json: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    review_warnings: list[str] = Field(default_factory=list)
    status: ReviewStatus
    curator_name: str | None = None
    curator_notes: str | None = None
    expert_metadata: ExpertReferenceMetadata | None = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None


class ReviewEvent(BaseModel):
    event_id: str
    record_id: str
    field_name: str
    old_value: str | None
    new_value: str | None
    actor: str
    created_at: datetime


class BatchReport(BaseModel):
    discovered: int = 0
    ingested: int = 0
    duplicates_skipped: int = 0
    labelled: int = 0
    validation_failed: int = 0
    provider_failed: int = 0
    skipped_idempotent: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    average_latency_ms: float | None = None

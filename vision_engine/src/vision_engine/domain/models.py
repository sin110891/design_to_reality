from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from vision_engine.domain.enums import (
    ApprovedConceptExportStatus,
    BenchmarkArm,
    BuildabilityAssessment,
    FailureTag,
    GenerationMode,
    GenerationReviewSetStatus,
    LabelPolarity,
    ProjectStatus,
    RetentionConsentStatus,
    ReviewDecision,
    ReviewStatus,
    RightsStatus,
    VariantKind,
    VariantReviewStatus,
)


class DesignDirection(BaseModel):
    """Structured design direction returned by the concept generator."""

    concept_title: str = Field(min_length=3, max_length=120)
    design_intent: str = Field(min_length=10, max_length=1200)
    mood: list[str] = Field(min_length=1, max_length=5)
    colour_direction: list[str] = Field(default_factory=list, max_length=8)
    material_palette: list[str] = Field(min_length=1, max_length=8)
    lighting_strategy: list[str] = Field(min_length=1, max_length=8)
    furniture_direction: list[str] = Field(min_length=1, max_length=8)
    focal_point: str = Field(min_length=3, max_length=400)
    spatial_hierarchy: str = Field(min_length=3, max_length=400)
    preserve: list[str] = Field(min_length=1, max_length=12)
    allowed_changes: list[str] = Field(min_length=1, max_length=12)
    likely_trades: list[str] = Field(min_length=1, max_length=8)
    positive_rules: list[str] = Field(min_length=1, max_length=8)
    negative_warnings: list[str] = Field(min_length=1, max_length=8)

    @field_validator(
        "mood",
        "colour_direction",
        "material_palette",
        "lighting_strategy",
        "furniture_direction",
        "preserve",
        "allowed_changes",
        "likely_trades",
        "positive_rules",
        "negative_warnings",
        mode="before",
    )
    @classmethod
    def _strip_empty(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [item for item in value if item not in (None, "")]
        return value


class DatasetRecord(BaseModel):
    """Flattened curated reference consumed by retrieval."""

    image_id: str
    image_path: str
    source_project_id: str | None = None
    source_room_id: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    project_type: str = "residential"
    room_type: str | None = None
    image_type: str | None = None
    geography: str | None = None
    style_family: str
    expert_style_family: list[str] = Field(default_factory=list)
    mood: list[str] = Field(default_factory=list)
    colour_palette: list[str] = Field(default_factory=list)
    material_palette: list[str] = Field(default_factory=list)
    material_floor: list[str] = Field(default_factory=list)
    material_wall: list[str] = Field(default_factory=list)
    material_furniture: list[str] = Field(default_factory=list)
    material_ceiling: list[str] = Field(default_factory=list)
    colour_scheme: str | None = None
    lighting_strategy: str | None = None
    furniture_style: str | None = None
    spatial_feel: list[str] = Field(default_factory=list)
    budget_band: str | None = None
    build_complexity: str | None = None
    maintenance_level: str | None = None
    architect_quality_score: float = Field(default=3.5, ge=1.0, le=5.0)
    buildability_score: float = Field(default=3.5, ge=1.0, le=5.0)
    relevance_score: float | None = Field(default=None, ge=1.0, le=5.0)
    positive_why_it_works: str | None = None
    negative_common_pitfalls: str | None = None
    primary_trade: str | None = None
    likely_trades_required: list[str] = Field(default_factory=list)
    secondary_trades: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.APPROVED
    focal_point: str | None = None
    circulation_strategy: str | None = None
    visual_hierarchy: str | None = None
    proportion_rule: str | None = None
    material_relationship: str | None = None
    appropriate_room_conditions: list[str] = Field(default_factory=list)
    design_failure: str | None = None
    why_it_fails: str | None = None
    scale_problem: str | None = None
    material_conflict: str | None = None
    lighting_problem: str | None = None
    impractical_detail: str | None = None
    generic_ai_artifact: str | None = None
    structural_violation: str | None = None
    source_record_id: str | None = None
    sha256: str | None = None
    usage_rights_status: str | None = None
    text_blob: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedReference(BaseModel):
    image_id: str
    image_path: str
    score: float
    image_similarity: float = 0.0
    text_similarity: float = 0.0
    metadata_match: float = 0.0
    architect_quality: float = 0.0
    match_rationale: str
    record: DatasetRecord
    diversity_role: str | None = None


class ModelCallMetadata(BaseModel):
    provider: str
    model_name: str
    request_id: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    attempt: int = 1


class ProjectInput(BaseModel):
    room_image_path: str
    inspiration_image_paths: list[str] = Field(default_factory=list)
    room_type: str
    style_family: str = "Contemporary Europe"
    brief: str = Field(min_length=5, max_length=2000)
    budget_band: str | None = None
    constraints: list[str] = Field(default_factory=list)
    project_type: str = "residential"


class ProjectRecord(BaseModel):
    project_id: str
    room_image_path: str
    inspiration_image_paths: list[str] = Field(default_factory=list)
    room_type: str
    style_family: str
    brief: str
    budget_band: str | None = None
    constraints: list[str] = Field(default_factory=list)
    project_type: str = "residential"
    status: ProjectStatus = ProjectStatus.CREATED
    created_at: datetime
    updated_at: datetime


class UploadRecord(BaseModel):
    upload_id: str
    project_id: str
    role: str  # room | inspiration
    relative_path: str
    sha256: str
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    rights_status: RightsStatus = RightsStatus.USER_OWNED
    retention_consent_status: RetentionConsentStatus = RetentionConsentStatus.PENDING
    consented_by: str | None = None
    consent_version: str | None = None
    consented_at: datetime | None = None
    consent_source: str | None = None
    withdrawn_at: datetime | None = None
    created_at: datetime


class RetrievalRunRecord(BaseModel):
    run_id: str
    project_id: str
    mode: GenerationMode
    query_text: str
    top_k: int
    final_k: int
    reference_ids: list[str]
    scores_json: list[dict[str, Any]]
    dataset_version: str | None = None
    created_at: datetime


class ConceptRunRecord(BaseModel):
    run_id: str
    project_id: str
    retrieval_run_id: str | None
    mode: GenerationMode
    prompt_version: str
    provider: str
    model_name: str
    design_direction: DesignDirection | None
    raw_response_json: str | None = None
    status: str
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime


class GenerationRunRecord(BaseModel):
    run_id: str
    project_id: str
    concept_run_id: str | None
    mode: GenerationMode
    prompt_version: str
    provider: str
    model_name: str
    reference_ids: list[str] = Field(default_factory=list)
    status: str
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime


class GeneratedImageAsset(BaseModel):
    asset_id: str
    variant_id: str
    storage_path: str
    image_sha256: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    file_size_bytes: int | None = None
    rights_status: RightsStatus = RightsStatus.USER_OWNED
    retention_consent_status: RetentionConsentStatus = RetentionConsentStatus.PENDING
    consented_by: str | None = None
    consent_version: str | None = None
    consented_at: datetime | None = None
    consent_source: str | None = None
    created_at: datetime
    deleted_at: datetime | None = None


class GeneratedVariant(BaseModel):
    variant_id: str
    generation_run_id: str
    project_id: str
    mode: GenerationMode
    kind: VariantKind
    image_path: str
    rank_hint: int
    review_status: VariantReviewStatus = VariantReviewStatus.UNREVIEWED
    reviewed_at: datetime | None = None
    image_asset_id: str | None = None
    created_at: datetime


class ReviewLabel(BaseModel):
    label_code: str
    label_group: str
    description: str
    active: bool = True
    default_polarity: LabelPolarity


class VariantReviewInput(BaseModel):
    variant_id: str
    decision: ReviewDecision
    rank_in_set: int | None = Field(default=None, ge=1, le=3)
    reference_relevance_score: int | None = Field(default=None, ge=1, le=5)
    taste_quality_score: int | None = Field(default=None, ge=1, le=5)
    geometry_preservation_score: int | None = Field(default=None, ge=1, le=5)
    material_coherence_score: int | None = Field(default=None, ge=1, le=5)
    buildability_assessment: BuildabilityAssessment = (
        BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL
    )
    buildability_score: int | None = Field(default=None, ge=1, le=5)
    labels: list[str] = Field(default_factory=list)
    positive_notes: str | None = Field(default=None, max_length=2000)
    negative_notes: str | None = Field(default=None, max_length=2000)


class GenerationReviewSetInput(BaseModel):
    generation_run_id: str
    project_id: str
    reviewer: str
    status: GenerationReviewSetStatus
    winner_variant_id: str | None = None
    overall_notes: str | None = Field(default=None, max_length=4000)
    variants: list[VariantReviewInput]


class VariantReview(BaseModel):
    variant_review_id: str
    review_set_id: str
    variant_id: str
    decision: ReviewDecision
    rank_in_set: int | None = None
    reference_relevance_score: int | None = None
    taste_quality_score: int | None = None
    geometry_preservation_score: int | None = None
    material_coherence_score: int | None = None
    buildability_assessment: BuildabilityAssessment
    buildability_score: int | None = None
    positive_notes: str | None = None
    negative_notes: str | None = None
    labels: list[str] = Field(default_factory=list)
    reviewed_at: datetime


class GenerationReviewSet(BaseModel):
    review_set_id: str
    generation_run_id: str
    project_id: str
    reviewer: str
    status: GenerationReviewSetStatus
    winner_variant_id: str | None = None
    overall_notes: str | None = None
    revision_number: int = 1
    supersedes_id: str | None = None
    created_at: datetime
    submitted_at: datetime | None = None
    variant_reviews: list[VariantReview] = Field(default_factory=list)


class ApprovedConceptManifest(BaseModel):
    manifest_id: str
    variant_review_id: str
    variant_id: str
    manifest_sha256: str
    manifest_schema_version: str
    export_status: ApprovedConceptExportStatus
    retention_consent_status: RetentionConsentStatus
    manifest_json: dict[str, Any]
    approved_at: datetime
    exported_at: datetime | None = None
    withdrawn_at: datetime | None = None
    withdrawal_reason: str | None = None


class BenchmarkCase(BaseModel):
    benchmark_case_id: str
    canonical_input_sha256: str
    canonical_brief: str
    status: str
    created_at: datetime


class BenchmarkCaseProject(BaseModel):
    benchmark_case_project_id: str
    benchmark_case_id: str
    project_id: str
    generation_run_id: str
    arm: BenchmarkArm


class FeedbackEvent(BaseModel):
    feedback_id: str
    project_id: str
    variant_id: str | None = None
    reviewer: str
    decision: ReviewDecision
    rank: int | None = Field(default=None, ge=1, le=3)
    reference_relevance_score: int | None = Field(default=None, ge=1, le=5)
    taste_quality_score: int | None = Field(default=None, ge=1, le=5)
    geometry_preservation_score: int | None = Field(default=None, ge=1, le=5)
    buildability_score: int | None = Field(default=None, ge=1, le=5)
    material_coherence_score: int | None = Field(default=None, ge=1, le=5)
    positive_notes: str | None = Field(default=None, max_length=2000)
    negative_notes: str | None = Field(default=None, max_length=2000)
    failure_tags: list[FailureTag] = Field(default_factory=list)
    edited_concept_json: dict[str, Any] | None = None
    created_at: datetime


class PromptVersionRecord(BaseModel):
    version_id: str
    name: str
    content_hash: str
    created_at: datetime


class ModelVersionRecord(BaseModel):
    version_id: str
    provider: str
    model_name: str
    role: str
    created_at: datetime


class PipelineResult(BaseModel):
    """End-to-end result for UI / CLI / evaluation."""

    project: ProjectRecord
    references: list[RetrievedReference] = Field(default_factory=list)
    design_direction: DesignDirection | None = None
    variants: list[GeneratedVariant] = Field(default_factory=list)
    mode: GenerationMode = GenerationMode.CURATED
    concept_run_id: str | None = None
    generation_run_id: str | None = None
    retrieval_run_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Concept visual only — not a technical design, BoQ, or compliance guarantee."
    )

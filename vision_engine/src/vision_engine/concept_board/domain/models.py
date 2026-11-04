from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from vision_engine.concept_board.domain.enums import (
    ApprovalType,
    CandidateSource,
    CandidateStatus,
    CatalogueSnapshotStatus,
    ConceptAssetType,
    ConceptBoardStatus,
    ConceptDirectionStatus,
    ConceptVersionStatus,
    DesignRegionLifecycle,
    IntegrationExportStatus,
    IntegrationExportType,
    ProcurementItemStatus,
    ProcurementScheduleStatus,
    RegionGeometryType,
    RequirementSeverity,
    ReviewDecisionType,
    ScoreType,
    SelectionStatus,
    SubstitutionPolicy,
    SubstitutionPreviewStatus,
)


class ConceptBoardRecord(BaseModel):
    concept_board_id: str
    project_id: str
    board_name: str
    status: ConceptBoardStatus = ConceptBoardStatus.ACTIVE
    version: int = 1
    created_at: datetime
    updated_at: datetime


class ConceptDirectionRecord(BaseModel):
    concept_direction_id: str
    concept_board_id: str
    direction_name: str
    design_intent_json: dict[str, Any]
    status: ConceptDirectionStatus = ConceptDirectionStatus.ACTIVE
    created_at: datetime
    archived_at: datetime | None = None


class ConceptVersionRecord(BaseModel):
    concept_version_id: str
    concept_direction_id: str
    parent_concept_version_id: str | None = None
    version_number: int
    version_reason: str
    generation_provider: str | None = None
    generation_model: str | None = None
    prompt_version: str | None = None
    status: ConceptVersionStatus
    content_sha256: str
    created_at: datetime
    approved_at: datetime | None = None


class ConceptAssetRecord(BaseModel):
    concept_asset_id: str
    concept_version_id: str
    asset_type: ConceptAssetType
    storage_uri: str
    mime_type: str
    asset_sha256: str
    width: int | None = None
    height: int | None = None
    rights_status: str = "user_owned"
    created_at: datetime


class ConceptVersionProvenanceRecord(BaseModel):
    provenance_id: str
    concept_version_id: str
    source_vision_project_id: str
    generation_run_id: str | None = None
    concept_run_id: str | None = None
    retrieval_run_id: str | None = None
    source_variant_id: str | None = None
    approved_manifest_id: str | None = None
    design_direction_json: dict[str, Any] = Field(default_factory=dict)
    reference_ids_json: list[str] = Field(default_factory=list)
    created_at: datetime


class DesignRegionRecord(BaseModel):
    design_region_id: str
    concept_direction_id: str
    region_code: str
    region_type: str
    display_name: str
    lifecycle_status: DesignRegionLifecycle = DesignRegionLifecycle.PROPOSED
    is_fixed: bool = False
    created_at: datetime
    retired_at: datetime | None = None


class RegionGeometryRecord(BaseModel):
    region_geometry_id: str
    design_region_id: str
    concept_version_id: str
    geometry_type: RegionGeometryType
    geometry_json: dict[str, Any]
    mask_uri: str | None = None
    mask_sha256: str | None = None
    confidence: float | None = None
    source: str = "manual"
    created_at: datetime


class RegionRequirementRecord(BaseModel):
    region_requirement_id: str
    design_region_id: str
    requirement_type: str
    operator: str
    value_json: dict[str, Any]
    severity: RequirementSeverity = RequirementSeverity.SOFT
    source: str = "design_intent"
    created_at: datetime


class ProductRecord(BaseModel):
    product_id: str
    canonical_name: str
    brand_name: str | None = None
    product_type: str
    description: str | None = None
    manufacturer_sku: str | None = None
    lifecycle_status: str = "active"
    external_provider: str | None = None
    external_product_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ProductVariantRecord(BaseModel):
    product_variant_id: str
    product_id: str
    variant_sku: str
    colour: str | None = None
    finish: str | None = None
    material: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    depth_mm: float | None = None
    weight_kg: float | None = None
    attributes_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MaterialRecord(BaseModel):
    material_id: str
    canonical_name: str
    material_category: str
    description: str | None = None
    application_type: str | None = None
    lifecycle_status: str = "active"
    created_at: datetime
    updated_at: datetime


class MaterialVariantRecord(BaseModel):
    material_variant_id: str
    material_id: str
    finish: str | None = None
    colour: str | None = None
    format: str | None = None
    unit_of_measure: str = "sqm"
    technical_properties_json: dict[str, Any] = Field(default_factory=dict)
    compliance_data_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SupplierRecord(BaseModel):
    supplier_id: str
    supplier_name: str
    supplier_type: str = "retailer"
    website_url: str | None = None
    country_code: str = "GB"
    coverage_json: dict[str, Any] = Field(default_factory=dict)
    verification_status: str = "unverified"
    created_at: datetime
    updated_at: datetime


class SupplierOfferRecord(BaseModel):
    supplier_offer_id: str
    supplier_id: str
    product_variant_id: str | None = None
    material_variant_id: str | None = None
    supplier_sku: str
    unit_price: float
    currency_code: str = "GBP"
    price_basis: str = "unit"
    stock_status: str = "in_stock"
    stock_quantity: int | None = None
    lead_time_days_min: int | None = None
    lead_time_days_max: int | None = None
    delivery_coverage_json: dict[str, Any] = Field(default_factory=dict)
    price_checked_at: datetime
    valid_until: datetime | None = None
    external_provider: str | None = None
    buy_url: str | None = None

    @model_validator(mode="after")
    def _xor_variant(self) -> SupplierOfferRecord:
        has_product = self.product_variant_id is not None
        has_material = self.material_variant_id is not None
        if has_product == has_material:
            raise ValueError("supplier offer must reference exactly one variant type")
        return self


class CatalogueSnapshotRecord(BaseModel):
    catalogue_snapshot_id: str
    snapshot_name: str
    manifest_uri: str
    manifest_sha256: str
    item_count: int
    status: CatalogueSnapshotStatus
    created_at: datetime
    sealed_at: datetime | None = None


class ProductRetrievalRunRecord(BaseModel):
    product_retrieval_run_id: str
    design_region_id: str
    concept_version_id: str
    catalogue_snapshot_id: str
    query_context_json: dict[str, Any]
    top_k: int
    created_at: datetime


class RegionCandidateRecord(BaseModel):
    region_candidate_id: str
    design_region_id: str
    product_retrieval_run_id: str
    product_variant_id: str | None = None
    material_variant_id: str | None = None
    catalogue_snapshot_id: str
    candidate_source: CandidateSource
    candidate_status: CandidateStatus = CandidateStatus.DRAFT
    match_rationale_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    @model_validator(mode="after")
    def _xor_variant(self) -> RegionCandidateRecord:
        has_product = self.product_variant_id is not None
        has_material = self.material_variant_id is not None
        if has_product == has_material:
            raise ValueError("region candidate must reference exactly one variant type")
        return self


class CandidateScoreRecord(BaseModel):
    candidate_score_id: str
    region_candidate_id: str
    score_type: ScoreType
    raw_score: float
    normalised_score: float
    model_version: str = "rule-v1"
    explanation_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SubstitutionPreviewRecord(BaseModel):
    substitution_preview_id: str
    concept_version_id: str
    region_candidate_id: str
    preview_asset_uri: str
    preview_asset_sha256: str
    generation_provider: str
    generation_model: str
    prompt_version: str
    status: SubstitutionPreviewStatus
    virtual_staging_output_id: str | None = None
    evidence_grade: str | None = None
    disclaimer: str | None = None
    created_at: datetime


class ReviewDecisionRecord(BaseModel):
    review_decision_id: str
    substitution_preview_id: str
    reviewer_user_id: str
    decision: ReviewDecisionType
    preference_rank: int | None = None
    taste_score: int | None = Field(default=None, ge=1, le=5)
    realism_score: int | None = Field(default=None, ge=1, le=5)
    fit_score: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    rejection_reason_json: dict[str, Any] | None = None
    created_at: datetime


class RegionSelectionRecord(BaseModel):
    region_selection_id: str
    design_region_id: str
    region_candidate_id: str
    concept_version_id: str
    selected_by_user_id: str
    selection_status: SelectionStatus
    quantity: int = 1
    quantity_basis: str = "unit"
    approval_state: str = "draft"
    selected_at: datetime
    approved_at: datetime | None = None
    selected_product_image_uri: str | None = None


class ApprovalEventRecord(BaseModel):
    approval_event_id: str
    concept_version_id: str
    user_id: str
    approval_type: ApprovalType
    decision: str
    comments: str | None = None
    created_at: datetime


class ProcurementScheduleRecord(BaseModel):
    procurement_schedule_id: str
    project_id: str
    catalogue_snapshot_id: str
    schedule_name: str
    status: ProcurementScheduleStatus
    currency_code: str = "GBP"
    version_number: int = 1
    created_at: datetime
    approved_at: datetime | None = None


class ProcurementItemRecord(BaseModel):
    procurement_item_id: str
    procurement_schedule_id: str
    region_selection_id: str
    supplier_offer_id: str
    item_name: str
    required_quantity: float
    unit_of_measure: str
    unit_price_snapshot: float
    estimated_total: float
    procurement_status: ProcurementItemStatus = ProcurementItemStatus.DRAFT
    substitution_policy: SubstitutionPolicy = SubstitutionPolicy.ARCHITECT_APPROVAL
    required_by: datetime | None = None
    created_at: datetime


class ScopeItemRecord(BaseModel):
    scope_item_id: str
    project_id: str
    region_selection_id: str
    procurement_item_id: str
    work_package_code: str
    scope_description: str
    inclusion_json: dict[str, Any] = Field(default_factory=dict)
    exclusion_json: dict[str, Any] = Field(default_factory=dict)
    assumption_json: dict[str, Any] = Field(default_factory=dict)
    approval_status: str = "draft"
    created_at: datetime
    updated_at: datetime


class IntegrationExportRecord(BaseModel):
    export_id: str
    project_id: str
    procurement_schedule_id: str
    catalogue_snapshot_id: str
    export_type: IntegrationExportType
    manifest_uri: str
    manifest_sha256: str
    status: IntegrationExportStatus
    created_at: datetime
    delivered_at: datetime | None = None


class CatalogueImportRow(BaseModel):
    """One catalogue import row from CSV or an external provider."""

    product_id: str
    canonical_name: str
    brand_name: str | None = None
    product_type: str
    description: str | None = None
    variant_sku: str
    colour: str | None = None
    finish: str | None = None
    material: str | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    depth_mm: float | None = None
    supplier_name: str
    supplier_sku: str
    unit_price: float
    currency_code: str = "GBP"
    stock_status: str = "in_stock"
    lead_time_days_min: int | None = None
    lead_time_days_max: int | None = None
    region_types: list[str] = Field(default_factory=list)
    external_provider: str | None = None
    external_product_id: str | None = None
    reference_image_uri: str | None = None
    buy_url: str | None = None
    attributes_json: dict[str, Any] = Field(default_factory=dict)


class ConceptBoardWorkspaceView(BaseModel):
    """Read model for CLI/UI summaries."""

    concept_board: ConceptBoardRecord
    concept_direction: ConceptDirectionRecord
    latest_version: ConceptVersionRecord
    regions: list[DesignRegionRecord] = Field(default_factory=list)
    selections: list[RegionSelectionRecord] = Field(default_factory=list)
    procurement_schedule: ProcurementScheduleRecord | None = None

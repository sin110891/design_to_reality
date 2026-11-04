from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from vision_engine.infrastructure.database_base import Base, utcnow


class ConceptBoardRow(Base):
    __tablename__ = "concept_boards"

    concept_board_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.project_id"), index=True, nullable=False
    )
    board_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="active", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConceptDirectionRow(Base):
    __tablename__ = "concept_directions"

    concept_direction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_board_id: Mapped[str] = mapped_column(
        ForeignKey("concept_boards.concept_board_id"), index=True, nullable=False
    )
    direction_name: Mapped[str] = mapped_column(String(256), nullable=False)
    design_intent_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(64), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConceptVersionRow(Base):
    __tablename__ = "concept_versions"
    __table_args__ = (
        UniqueConstraint(
            "concept_direction_id",
            "version_number",
            name="uq_concept_version_number",
        ),
    )

    concept_version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_direction_id: Mapped[str] = mapped_column(
        ForeignKey("concept_directions.concept_direction_id"), index=True, nullable=False
    )
    parent_concept_version_id: Mapped[str | None] = mapped_column(String(64))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_reason: Mapped[str] = mapped_column(String(256), nullable=False)
    generation_provider: Mapped[str | None] = mapped_column(String(64))
    generation_model: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConceptAssetRow(Base):
    __tablename__ = "concept_assets"

    concept_asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_version_id: Mapped[str] = mapped_column(
        ForeignKey("concept_versions.concept_version_id"), index=True, nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    rights_status: Mapped[str] = mapped_column(String(64), default="user_owned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConceptVersionProvenanceRow(Base):
    __tablename__ = "concept_version_provenance"

    provenance_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_version_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("concept_versions.concept_version_id"), unique=True, nullable=False
    )
    source_vision_project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    generation_run_id: Mapped[str | None] = mapped_column(String(64))
    concept_run_id: Mapped[str | None] = mapped_column(String(64))
    retrieval_run_id: Mapped[str | None] = mapped_column(String(64))
    source_variant_id: Mapped[str | None] = mapped_column(String(64))
    approved_manifest_id: Mapped[str | None] = mapped_column(String(64))
    design_direction_json: Mapped[str] = mapped_column(Text, default="{}")
    reference_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DesignRegionRow(Base):
    __tablename__ = "design_regions"
    __table_args__ = (
        UniqueConstraint(
            "concept_direction_id",
            "region_code",
            name="uq_design_region_code",
        ),
    )

    design_region_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_direction_id: Mapped[str] = mapped_column(
        ForeignKey("concept_directions.concept_direction_id"), index=True, nullable=False
    )
    region_code: Mapped[str] = mapped_column(String(128), nullable=False)
    region_type: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(64), default="proposed", index=True)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RegionGeometryRow(Base):
    __tablename__ = "region_geometries"

    region_geometry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    design_region_id: Mapped[str] = mapped_column(
        ForeignKey("design_regions.design_region_id"), index=True, nullable=False
    )
    concept_version_id: Mapped[str] = mapped_column(
        ForeignKey("concept_versions.concept_version_id"), index=True, nullable=False
    )
    geometry_type: Mapped[str] = mapped_column(String(64), nullable=False)
    geometry_json: Mapped[str] = mapped_column(Text, default="{}")
    mask_uri: Mapped[str | None] = mapped_column(Text)
    mask_sha256: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RegionRequirementRow(Base):
    __tablename__ = "region_requirements"

    region_requirement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    design_region_id: Mapped[str] = mapped_column(
        ForeignKey("design_regions.design_region_id"), index=True, nullable=False
    )
    requirement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(32), nullable=False)
    value_json: Mapped[str] = mapped_column(Text, default="{}")
    severity: Mapped[str] = mapped_column(String(32), default="soft")
    source: Mapped[str] = mapped_column(String(64), default="design_intent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CbProductRow(Base):
    __tablename__ = "cb_products"

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False)
    brand_name: Mapped[str | None] = mapped_column(String(256))
    product_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    manufacturer_sku: Mapped[str | None] = mapped_column(String(128))
    lifecycle_status: Mapped[str] = mapped_column(String(64), default="active")
    external_provider: Mapped[str | None] = mapped_column(String(64), index=True)
    external_product_id: Mapped[str | None] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CbProductVariantRow(Base):
    __tablename__ = "cb_product_variants"

    product_variant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("cb_products.product_id"), index=True, nullable=False
    )
    variant_sku: Mapped[str] = mapped_column(String(128), nullable=False)
    colour: Mapped[str | None] = mapped_column(String(128))
    finish: Mapped[str | None] = mapped_column(String(128))
    material: Mapped[str | None] = mapped_column(String(128))
    width_mm: Mapped[float | None] = mapped_column(Float)
    height_mm: Mapped[float | None] = mapped_column(Float)
    depth_mm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    attributes_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CbMaterialRow(Base):
    __tablename__ = "cb_materials"

    material_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False)
    material_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    application_type: Mapped[str | None] = mapped_column(String(64))
    lifecycle_status: Mapped[str] = mapped_column(String(64), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CbMaterialVariantRow(Base):
    __tablename__ = "cb_material_variants"

    material_variant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    material_id: Mapped[str] = mapped_column(
        ForeignKey("cb_materials.material_id"), index=True, nullable=False
    )
    finish: Mapped[str | None] = mapped_column(String(128))
    colour: Mapped[str | None] = mapped_column(String(128))
    format: Mapped[str | None] = mapped_column(String(64))
    unit_of_measure: Mapped[str] = mapped_column(String(32), default="sqm")
    technical_properties_json: Mapped[str] = mapped_column(Text, default="{}")
    compliance_data_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CbSupplierRow(Base):
    __tablename__ = "cb_suppliers"

    supplier_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    supplier_name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    supplier_type: Mapped[str] = mapped_column(String(64), default="retailer")
    website_url: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str] = mapped_column(String(8), default="GB")
    coverage_json: Mapped[str] = mapped_column(Text, default="{}")
    verification_status: Mapped[str] = mapped_column(String(64), default="unverified")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CbSupplierOfferRow(Base):
    __tablename__ = "cb_supplier_offers"

    supplier_offer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    supplier_id: Mapped[str] = mapped_column(
        ForeignKey("cb_suppliers.supplier_id"), index=True, nullable=False
    )
    product_variant_id: Mapped[str | None] = mapped_column(
        ForeignKey("cb_product_variants.product_variant_id"), index=True
    )
    material_variant_id: Mapped[str | None] = mapped_column(
        ForeignKey("cb_material_variants.material_variant_id"), index=True
    )
    supplier_sku: Mapped[str] = mapped_column(String(128), nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(8), default="GBP")
    price_basis: Mapped[str] = mapped_column(String(32), default="unit")
    stock_status: Mapped[str] = mapped_column(String(64), default="in_stock")
    stock_quantity: Mapped[int | None] = mapped_column(Integer)
    lead_time_days_min: Mapped[int | None] = mapped_column(Integer)
    lead_time_days_max: Mapped[int | None] = mapped_column(Integer)
    delivery_coverage_json: Mapped[str] = mapped_column(Text, default="{}")
    price_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_provider: Mapped[str | None] = mapped_column(String(64))
    buy_url: Mapped[str | None] = mapped_column(Text)


class CatalogueSnapshotRow(Base):
    __tablename__ = "catalogue_snapshots"

    catalogue_snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    manifest_uri: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CatalogueSnapshotItemRow(Base):
    __tablename__ = "catalogue_snapshot_items"

    snapshot_item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    catalogue_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("catalogue_snapshots.catalogue_snapshot_id"), index=True, nullable=False
    )
    product_id: Mapped[str | None] = mapped_column(ForeignKey("cb_products.product_id"), index=True)
    material_id: Mapped[str | None] = mapped_column(ForeignKey("cb_materials.material_id"), index=True)
    product_variant_id: Mapped[str | None] = mapped_column(
        ForeignKey("cb_product_variants.product_variant_id"), index=True
    )
    material_variant_id: Mapped[str | None] = mapped_column(
        ForeignKey("cb_material_variants.material_variant_id"), index=True
    )
    item_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class ProductRetrievalRunRow(Base):
    __tablename__ = "product_retrieval_runs"

    product_retrieval_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    design_region_id: Mapped[str] = mapped_column(
        ForeignKey("design_regions.design_region_id"), index=True, nullable=False
    )
    concept_version_id: Mapped[str] = mapped_column(
        ForeignKey("concept_versions.concept_version_id"), index=True, nullable=False
    )
    catalogue_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("catalogue_snapshots.catalogue_snapshot_id"), index=True, nullable=False
    )
    query_context_json: Mapped[str] = mapped_column(Text, default="{}")
    top_k: Mapped[int] = mapped_column(Integer, default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RegionCandidateRow(Base):
    __tablename__ = "region_candidates"

    region_candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    design_region_id: Mapped[str] = mapped_column(
        ForeignKey("design_regions.design_region_id"), index=True, nullable=False
    )
    product_retrieval_run_id: Mapped[str] = mapped_column(
        ForeignKey("product_retrieval_runs.product_retrieval_run_id"), index=True, nullable=False
    )
    product_variant_id: Mapped[str | None] = mapped_column(
        ForeignKey("cb_product_variants.product_variant_id"), index=True
    )
    material_variant_id: Mapped[str | None] = mapped_column(
        ForeignKey("cb_material_variants.material_variant_id"), index=True
    )
    catalogue_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("catalogue_snapshots.catalogue_snapshot_id"), index=True, nullable=False
    )
    candidate_source: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_status: Mapped[str] = mapped_column(String(64), default="draft", index=True)
    match_rationale_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CandidateScoreRow(Base):
    __tablename__ = "candidate_scores"

    candidate_score_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    region_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("region_candidates.region_candidate_id"), index=True, nullable=False
    )
    score_type: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    normalised_score: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), default="rule-v1")
    explanation_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SubstitutionPreviewRow(Base):
    __tablename__ = "substitution_previews"

    substitution_preview_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_version_id: Mapped[str] = mapped_column(
        ForeignKey("concept_versions.concept_version_id"), index=True, nullable=False
    )
    region_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("region_candidates.region_candidate_id"), index=True, nullable=False
    )
    preview_asset_uri: Mapped[str] = mapped_column(Text, nullable=False)
    preview_asset_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    generation_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    generation_model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    virtual_staging_output_id: Mapped[str | None] = mapped_column(String(64), index=True)
    evidence_grade: Mapped[str | None] = mapped_column(String(64))
    disclaimer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CbReviewDecisionRow(Base):
    __tablename__ = "cb_review_decisions"

    review_decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    substitution_preview_id: Mapped[str] = mapped_column(
        ForeignKey("substitution_previews.substitution_preview_id"), index=True, nullable=False
    )
    reviewer_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    preference_rank: Mapped[int | None] = mapped_column(Integer)
    taste_score: Mapped[int | None] = mapped_column(Integer)
    realism_score: Mapped[int | None] = mapped_column(Integer)
    fit_score: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    rejection_reason_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RegionSelectionRow(Base):
    __tablename__ = "region_selections"

    region_selection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    design_region_id: Mapped[str] = mapped_column(
        ForeignKey("design_regions.design_region_id"), index=True, nullable=False
    )
    region_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("region_candidates.region_candidate_id"), index=True, nullable=False
    )
    concept_version_id: Mapped[str] = mapped_column(
        ForeignKey("concept_versions.concept_version_id"), index=True, nullable=False
    )
    selected_by_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    selection_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    quantity_basis: Mapped[str] = mapped_column(String(32), default="unit")
    approval_state: Mapped[str] = mapped_column(String(64), default="draft")
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selected_product_image_uri: Mapped[str | None] = mapped_column(Text)


class CbApprovalEventRow(Base):
    __tablename__ = "cb_approval_events"

    approval_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_version_id: Mapped[str] = mapped_column(
        ForeignKey("concept_versions.concept_version_id"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    approval_type: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProcurementScheduleRow(Base):
    __tablename__ = "procurement_schedules"

    procurement_schedule_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.project_id"), index=True, nullable=False
    )
    catalogue_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("catalogue_snapshots.catalogue_snapshot_id"), index=True, nullable=False
    )
    schedule_name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    currency_code: Mapped[str] = mapped_column(String(8), default="GBP")
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcurementItemRow(Base):
    __tablename__ = "procurement_items"

    procurement_item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    procurement_schedule_id: Mapped[str] = mapped_column(
        ForeignKey("procurement_schedules.procurement_schedule_id"), index=True, nullable=False
    )
    region_selection_id: Mapped[str] = mapped_column(
        ForeignKey("region_selections.region_selection_id"), index=True, nullable=False
    )
    supplier_offer_id: Mapped[str] = mapped_column(
        ForeignKey("cb_supplier_offers.supplier_offer_id"), index=True, nullable=False
    )
    item_name: Mapped[str] = mapped_column(String(512), nullable=False)
    required_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(32), default="unit")
    unit_price_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_total: Mapped[float] = mapped_column(Float, nullable=False)
    procurement_status: Mapped[str] = mapped_column(String(64), default="draft")
    substitution_policy: Mapped[str] = mapped_column(String(64), default="architect_approval_required")
    required_by: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScopeItemRow(Base):
    __tablename__ = "scope_items"

    scope_item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.project_id"), index=True, nullable=False
    )
    region_selection_id: Mapped[str] = mapped_column(
        ForeignKey("region_selections.region_selection_id"), index=True, nullable=False
    )
    procurement_item_id: Mapped[str] = mapped_column(
        ForeignKey("procurement_items.procurement_item_id"), index=True, nullable=False
    )
    work_package_code: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_description: Mapped[str] = mapped_column(Text, nullable=False)
    inclusion_json: Mapped[str] = mapped_column(Text, default="{}")
    exclusion_json: Mapped[str] = mapped_column(Text, default="{}")
    assumption_json: Mapped[str] = mapped_column(Text, default="{}")
    approval_status: Mapped[str] = mapped_column(String(64), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IntegrationExportRow(Base):
    __tablename__ = "integration_exports"

    export_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.project_id"), index=True, nullable=False
    )
    procurement_schedule_id: Mapped[str] = mapped_column(
        ForeignKey("procurement_schedules.procurement_schedule_id"), index=True, nullable=False
    )
    catalogue_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("catalogue_snapshots.catalogue_snapshot_id"), index=True, nullable=False
    )
    export_type: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_uri: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

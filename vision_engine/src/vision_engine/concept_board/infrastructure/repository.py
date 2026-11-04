from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select

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
from vision_engine.concept_board.domain.models import (
    ApprovalEventRecord,
    CandidateScoreRecord,
    CatalogueSnapshotRecord,
    ConceptAssetRecord,
    ConceptBoardRecord,
    ConceptDirectionRecord,
    ConceptVersionProvenanceRecord,
    ConceptVersionRecord,
    DesignRegionRecord,
    IntegrationExportRecord,
    ProcurementItemRecord,
    ProcurementScheduleRecord,
    ProductRecord,
    ProductRetrievalRunRecord,
    ProductVariantRecord,
    RegionCandidateRecord,
    RegionGeometryRecord,
    RegionRequirementRecord,
    RegionSelectionRecord,
    ReviewDecisionRecord,
    ScopeItemRecord,
    SubstitutionPreviewRecord,
    SupplierOfferRecord,
    SupplierRecord,
)
from vision_engine.concept_board.infrastructure.schema import (
    CandidateScoreRow,
    CatalogueSnapshotItemRow,
    CatalogueSnapshotRow,
    CbApprovalEventRow,
    CbProductRow,
    CbProductVariantRow,
    CbReviewDecisionRow,
    CbSupplierOfferRow,
    CbSupplierRow,
    ConceptAssetRow,
    ConceptBoardRow,
    ConceptDirectionRow,
    ConceptVersionProvenanceRow,
    ConceptVersionRow,
    DesignRegionRow,
    IntegrationExportRow,
    ProcurementItemRow,
    ProcurementScheduleRow,
    ProductRetrievalRunRow,
    RegionCandidateRow,
    RegionGeometryRow,
    RegionRequirementRow,
    RegionSelectionRow,
    ScopeItemRow,
    SubstitutionPreviewRow,
)
from vision_engine.infrastructure.database_base import utcnow
from vision_engine.infrastructure.file_store import new_id


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


class ConceptBoardRepositoryMixin:
    """Persistence for concept board, catalogue, and procurement entities."""

    # --- concept workspace ---
    def save_concept_board(self, record: ConceptBoardRecord) -> None:
        with self.session() as session:
            session.merge(
                ConceptBoardRow(
                    concept_board_id=record.concept_board_id,
                    project_id=record.project_id,
                    board_name=record.board_name,
                    status=record.status.value,
                    version=record.version,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )

    def get_concept_board(self, concept_board_id: str) -> ConceptBoardRecord | None:
        with self.session() as session:
            row = session.get(ConceptBoardRow, concept_board_id)
            return self._to_concept_board(row) if row else None

    def get_concept_board_for_project(self, project_id: str) -> ConceptBoardRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(ConceptBoardRow)
                .where(ConceptBoardRow.project_id == project_id)
                .order_by(ConceptBoardRow.created_at.desc())
            ).first()
            return self._to_concept_board(row) if row else None

    def save_concept_direction(self, record: ConceptDirectionRecord) -> None:
        with self.session() as session:
            session.merge(
                ConceptDirectionRow(
                    concept_direction_id=record.concept_direction_id,
                    concept_board_id=record.concept_board_id,
                    direction_name=record.direction_name,
                    design_intent_json=_json_dumps(record.design_intent_json),
                    status=record.status.value,
                    created_at=record.created_at,
                    archived_at=record.archived_at,
                )
            )

    def get_concept_direction(self, concept_direction_id: str) -> ConceptDirectionRecord | None:
        with self.session() as session:
            row = session.get(ConceptDirectionRow, concept_direction_id)
            return self._to_concept_direction(row) if row else None

    def list_directions_for_board(self, concept_board_id: str) -> list[ConceptDirectionRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(ConceptDirectionRow).where(
                    ConceptDirectionRow.concept_board_id == concept_board_id
                )
            ).all()
            return [self._to_concept_direction(r) for r in rows]

    def save_concept_version(self, record: ConceptVersionRecord) -> None:
        with self.session() as session:
            session.merge(
                ConceptVersionRow(
                    concept_version_id=record.concept_version_id,
                    concept_direction_id=record.concept_direction_id,
                    parent_concept_version_id=record.parent_concept_version_id,
                    version_number=record.version_number,
                    version_reason=record.version_reason,
                    generation_provider=record.generation_provider,
                    generation_model=record.generation_model,
                    prompt_version=record.prompt_version,
                    status=record.status.value,
                    content_sha256=record.content_sha256,
                    created_at=record.created_at,
                    approved_at=record.approved_at,
                )
            )

    def get_concept_version(self, concept_version_id: str) -> ConceptVersionRecord | None:
        with self.session() as session:
            row = session.get(ConceptVersionRow, concept_version_id)
            return self._to_concept_version(row) if row else None

    def get_latest_concept_version(self, concept_direction_id: str) -> ConceptVersionRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(ConceptVersionRow)
                .where(ConceptVersionRow.concept_direction_id == concept_direction_id)
                .order_by(ConceptVersionRow.version_number.desc())
            ).first()
            return self._to_concept_version(row) if row else None

    def save_concept_asset(self, record: ConceptAssetRecord) -> None:
        with self.session() as session:
            session.merge(
                ConceptAssetRow(
                    concept_asset_id=record.concept_asset_id,
                    concept_version_id=record.concept_version_id,
                    asset_type=record.asset_type.value,
                    storage_uri=record.storage_uri,
                    mime_type=record.mime_type,
                    asset_sha256=record.asset_sha256,
                    width=record.width,
                    height=record.height,
                    rights_status=record.rights_status,
                    created_at=record.created_at,
                )
            )

    def get_primary_concept_asset(self, concept_version_id: str) -> ConceptAssetRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(ConceptAssetRow).where(
                    ConceptAssetRow.concept_version_id == concept_version_id,
                    ConceptAssetRow.asset_type == ConceptAssetType.PRIMARY_RENDER.value,
                )
            ).first()
            return self._to_concept_asset(row) if row else None

    def save_concept_version_provenance(self, record: ConceptVersionProvenanceRecord) -> None:
        with self.session() as session:
            session.merge(
                ConceptVersionProvenanceRow(
                    provenance_id=record.provenance_id,
                    concept_version_id=record.concept_version_id,
                    source_vision_project_id=record.source_vision_project_id,
                    generation_run_id=record.generation_run_id,
                    concept_run_id=record.concept_run_id,
                    retrieval_run_id=record.retrieval_run_id,
                    source_variant_id=record.source_variant_id,
                    approved_manifest_id=record.approved_manifest_id,
                    design_direction_json=_json_dumps(record.design_direction_json),
                    reference_ids_json=_json_dumps(record.reference_ids_json),
                    created_at=record.created_at,
                )
            )

    def save_design_region(self, record: DesignRegionRecord) -> None:
        with self.session() as session:
            session.merge(
                DesignRegionRow(
                    design_region_id=record.design_region_id,
                    concept_direction_id=record.concept_direction_id,
                    region_code=record.region_code,
                    region_type=record.region_type,
                    display_name=record.display_name,
                    lifecycle_status=record.lifecycle_status.value,
                    is_fixed=record.is_fixed,
                    created_at=record.created_at,
                    retired_at=record.retired_at,
                )
            )

    def get_design_region(self, design_region_id: str) -> DesignRegionRecord | None:
        with self.session() as session:
            row = session.get(DesignRegionRow, design_region_id)
            return self._to_design_region(row) if row else None

    def list_design_regions(self, concept_direction_id: str) -> list[DesignRegionRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(DesignRegionRow)
                .where(DesignRegionRow.concept_direction_id == concept_direction_id)
                .order_by(DesignRegionRow.region_code)
            ).all()
            return [self._to_design_region(r) for r in rows]

    def save_region_geometry(self, record: RegionGeometryRecord) -> None:
        with self.session() as session:
            session.merge(
                RegionGeometryRow(
                    region_geometry_id=record.region_geometry_id,
                    design_region_id=record.design_region_id,
                    concept_version_id=record.concept_version_id,
                    geometry_type=record.geometry_type.value,
                    geometry_json=_json_dumps(record.geometry_json),
                    mask_uri=record.mask_uri,
                    mask_sha256=record.mask_sha256,
                    confidence=record.confidence,
                    source=record.source,
                    created_at=record.created_at,
                )
            )

    def get_region_geometry_for_version(
        self, design_region_id: str, concept_version_id: str
    ) -> RegionGeometryRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(RegionGeometryRow)
                .where(RegionGeometryRow.design_region_id == design_region_id)
                .where(RegionGeometryRow.concept_version_id == concept_version_id)
                .order_by(RegionGeometryRow.created_at.desc())
            ).first()
            return self._to_region_geometry(row) if row else None

    def get_product_variant_details(
        self, product_variant_id: str
    ) -> tuple[ProductRecord, ProductVariantRecord] | None:
        with self.session() as session:
            variant_row = session.get(CbProductVariantRow, product_variant_id)
            if variant_row is None:
                return None
            product_row = session.get(CbProductRow, variant_row.product_id)
            if product_row is None:
                return None
            return self._to_product(product_row), self._to_product_variant(variant_row)

    def save_region_requirement(self, record: RegionRequirementRecord) -> None:
        with self.session() as session:
            session.merge(
                RegionRequirementRow(
                    region_requirement_id=record.region_requirement_id,
                    design_region_id=record.design_region_id,
                    requirement_type=record.requirement_type,
                    operator=record.operator,
                    value_json=_json_dumps(record.value_json),
                    severity=record.severity.value,
                    source=record.source,
                    created_at=record.created_at,
                )
            )

    def list_region_requirements(self, design_region_id: str) -> list[RegionRequirementRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(RegionRequirementRow).where(
                    RegionRequirementRow.design_region_id == design_region_id
                )
            ).all()
            return [self._to_region_requirement(r) for r in rows]

    # --- catalogue ---
    def save_product(self, record: ProductRecord) -> None:
        with self.session() as session:
            session.merge(
                CbProductRow(
                    product_id=record.product_id,
                    canonical_name=record.canonical_name,
                    brand_name=record.brand_name,
                    product_type=record.product_type,
                    description=record.description,
                    manufacturer_sku=record.manufacturer_sku,
                    lifecycle_status=record.lifecycle_status,
                    external_provider=record.external_provider,
                    external_product_id=record.external_product_id,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )

    def save_product_variant(self, record: ProductVariantRecord) -> None:
        with self.session() as session:
            session.merge(
                CbProductVariantRow(
                    product_variant_id=record.product_variant_id,
                    product_id=record.product_id,
                    variant_sku=record.variant_sku,
                    colour=record.colour,
                    finish=record.finish,
                    material=record.material,
                    width_mm=record.width_mm,
                    height_mm=record.height_mm,
                    depth_mm=record.depth_mm,
                    weight_kg=record.weight_kg,
                    attributes_json=_json_dumps(record.attributes_json),
                    created_at=record.created_at,
                )
            )

    def save_supplier(self, record: SupplierRecord) -> None:
        with self.session() as session:
            session.merge(
                CbSupplierRow(
                    supplier_id=record.supplier_id,
                    supplier_name=record.supplier_name,
                    supplier_type=record.supplier_type,
                    website_url=record.website_url,
                    country_code=record.country_code,
                    coverage_json=_json_dumps(record.coverage_json),
                    verification_status=record.verification_status,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )

    def get_supplier_by_name(self, supplier_name: str) -> SupplierRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(CbSupplierRow).where(CbSupplierRow.supplier_name == supplier_name)
            ).first()
            if not row:
                return None
            return SupplierRecord(
                supplier_id=row.supplier_id,
                supplier_name=row.supplier_name,
                supplier_type=row.supplier_type,
                website_url=row.website_url,
                country_code=row.country_code,
                coverage_json=json.loads(row.coverage_json or "{}"),
                verification_status=row.verification_status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    def save_supplier_offer(self, record: SupplierOfferRecord) -> None:
        with self.session() as session:
            session.merge(
                CbSupplierOfferRow(
                    supplier_offer_id=record.supplier_offer_id,
                    supplier_id=record.supplier_id,
                    product_variant_id=record.product_variant_id,
                    material_variant_id=record.material_variant_id,
                    supplier_sku=record.supplier_sku,
                    unit_price=record.unit_price,
                    currency_code=record.currency_code,
                    price_basis=record.price_basis,
                    stock_status=record.stock_status,
                    stock_quantity=record.stock_quantity,
                    lead_time_days_min=record.lead_time_days_min,
                    lead_time_days_max=record.lead_time_days_max,
                    delivery_coverage_json=_json_dumps(record.delivery_coverage_json),
                    price_checked_at=record.price_checked_at,
                    valid_until=record.valid_until,
                    external_provider=record.external_provider,
                    buy_url=record.buy_url,
                )
            )

    def get_supplier_offer_for_variant(
        self, product_variant_id: str
    ) -> SupplierOfferRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(CbSupplierOfferRow)
                .where(CbSupplierOfferRow.product_variant_id == product_variant_id)
                .order_by(CbSupplierOfferRow.price_checked_at.desc())
            ).first()
            return self._to_supplier_offer(row) if row else None

    def save_catalogue_snapshot(self, record: CatalogueSnapshotRecord) -> None:
        with self.session() as session:
            session.merge(
                CatalogueSnapshotRow(
                    catalogue_snapshot_id=record.catalogue_snapshot_id,
                    snapshot_name=record.snapshot_name,
                    manifest_uri=record.manifest_uri,
                    manifest_sha256=record.manifest_sha256,
                    item_count=record.item_count,
                    status=record.status.value,
                    created_at=record.created_at,
                    sealed_at=record.sealed_at,
                )
            )

    def get_catalogue_snapshot(self, catalogue_snapshot_id: str) -> CatalogueSnapshotRecord | None:
        with self.session() as session:
            row = session.get(CatalogueSnapshotRow, catalogue_snapshot_id)
            return self._to_catalogue_snapshot(row) if row else None

    def get_catalogue_snapshot_by_name(self, snapshot_name: str) -> CatalogueSnapshotRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(CatalogueSnapshotRow).where(
                    CatalogueSnapshotRow.snapshot_name == snapshot_name
                )
            ).first()
            return self._to_catalogue_snapshot(row) if row else None

    def get_active_sealed_snapshot(self) -> CatalogueSnapshotRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(CatalogueSnapshotRow)
                .where(CatalogueSnapshotRow.status == CatalogueSnapshotStatus.SEALED.value)
                .order_by(CatalogueSnapshotRow.sealed_at.desc())
            ).first()
            return self._to_catalogue_snapshot(row) if row else None

    def add_catalogue_snapshot_item(
        self,
        *,
        snapshot_item_id: str,
        catalogue_snapshot_id: str,
        product_id: str | None,
        material_id: str | None,
        product_variant_id: str | None,
        material_variant_id: str | None,
        item_sha256: str,
    ) -> None:
        with self.session() as session:
            session.merge(
                CatalogueSnapshotItemRow(
                    snapshot_item_id=snapshot_item_id,
                    catalogue_snapshot_id=catalogue_snapshot_id,
                    product_id=product_id,
                    material_id=material_id,
                    product_variant_id=product_variant_id,
                    material_variant_id=material_variant_id,
                    item_sha256=item_sha256,
                )
            )

    def list_snapshot_product_variants(
        self, catalogue_snapshot_id: str
    ) -> list[tuple[ProductRecord, ProductVariantRecord, SupplierOfferRecord, SupplierRecord]]:
        with self.session() as session:
            rows = session.execute(
                select(
                    CbProductRow,
                    CbProductVariantRow,
                    CbSupplierOfferRow,
                    CbSupplierRow,
                )
                .join(
                    CatalogueSnapshotItemRow,
                    CatalogueSnapshotItemRow.product_variant_id
                    == CbProductVariantRow.product_variant_id,
                )
                .join(CbProductRow, CbProductRow.product_id == CbProductVariantRow.product_id)
                .join(
                    CbSupplierOfferRow,
                    CbSupplierOfferRow.product_variant_id == CbProductVariantRow.product_variant_id,
                )
                .join(CbSupplierRow, CbSupplierRow.supplier_id == CbSupplierOfferRow.supplier_id)
                .where(CatalogueSnapshotItemRow.catalogue_snapshot_id == catalogue_snapshot_id)
            ).all()
            result: list[tuple[ProductRecord, ProductVariantRecord, SupplierOfferRecord, SupplierRecord]] = []
            for product_row, variant_row, offer_row, supplier_row in rows:
                result.append(
                    (
                        self._to_product(product_row),
                        self._to_product_variant(variant_row),
                        self._to_supplier_offer(offer_row),
                        SupplierRecord(
                            supplier_id=supplier_row.supplier_id,
                            supplier_name=supplier_row.supplier_name,
                            supplier_type=supplier_row.supplier_type,
                            website_url=supplier_row.website_url,
                            country_code=supplier_row.country_code,
                            coverage_json=json.loads(supplier_row.coverage_json or "{}"),
                            verification_status=supplier_row.verification_status,
                            created_at=supplier_row.created_at,
                            updated_at=supplier_row.updated_at,
                        ),
                    )
                )
            return result

    # --- retrieval / candidates ---
    def save_product_retrieval_run(self, record: ProductRetrievalRunRecord) -> None:
        with self.session() as session:
            session.merge(
                ProductRetrievalRunRow(
                    product_retrieval_run_id=record.product_retrieval_run_id,
                    design_region_id=record.design_region_id,
                    concept_version_id=record.concept_version_id,
                    catalogue_snapshot_id=record.catalogue_snapshot_id,
                    query_context_json=_json_dumps(record.query_context_json),
                    top_k=record.top_k,
                    created_at=record.created_at,
                )
            )

    def save_region_candidate(self, record: RegionCandidateRecord) -> None:
        with self.session() as session:
            session.merge(
                RegionCandidateRow(
                    region_candidate_id=record.region_candidate_id,
                    design_region_id=record.design_region_id,
                    product_retrieval_run_id=record.product_retrieval_run_id,
                    product_variant_id=record.product_variant_id,
                    material_variant_id=record.material_variant_id,
                    catalogue_snapshot_id=record.catalogue_snapshot_id,
                    candidate_source=record.candidate_source.value,
                    candidate_status=record.candidate_status.value,
                    match_rationale_json=_json_dumps(record.match_rationale_json),
                    created_at=record.created_at,
                )
            )

    def get_region_candidate(self, region_candidate_id: str) -> RegionCandidateRecord | None:
        with self.session() as session:
            row = session.get(RegionCandidateRow, region_candidate_id)
            return self._to_region_candidate(row) if row else None

    def list_region_candidates(self, design_region_id: str) -> list[RegionCandidateRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(RegionCandidateRow)
                .where(RegionCandidateRow.design_region_id == design_region_id)
                .order_by(RegionCandidateRow.created_at.desc())
            ).all()
            return [self._to_region_candidate(r) for r in rows]

    def save_candidate_score(self, record: CandidateScoreRecord) -> None:
        with self.session() as session:
            session.merge(
                CandidateScoreRow(
                    candidate_score_id=record.candidate_score_id,
                    region_candidate_id=record.region_candidate_id,
                    score_type=record.score_type.value,
                    raw_score=record.raw_score,
                    normalised_score=record.normalised_score,
                    model_version=record.model_version,
                    explanation_json=_json_dumps(record.explanation_json),
                    created_at=record.created_at,
                )
            )

    def save_substitution_preview(self, record: SubstitutionPreviewRecord) -> None:
        with self.session() as session:
            session.merge(
                SubstitutionPreviewRow(
                    substitution_preview_id=record.substitution_preview_id,
                    concept_version_id=record.concept_version_id,
                    region_candidate_id=record.region_candidate_id,
                    preview_asset_uri=record.preview_asset_uri,
                    preview_asset_sha256=record.preview_asset_sha256,
                    generation_provider=record.generation_provider,
                    generation_model=record.generation_model,
                    prompt_version=record.prompt_version,
                    status=record.status.value,
                    virtual_staging_output_id=record.virtual_staging_output_id,
                    evidence_grade=record.evidence_grade,
                    disclaimer=record.disclaimer,
                    created_at=record.created_at,
                )
            )

    def save_review_decision(self, record: ReviewDecisionRecord) -> None:
        with self.session() as session:
            session.merge(
                CbReviewDecisionRow(
                    review_decision_id=record.review_decision_id,
                    substitution_preview_id=record.substitution_preview_id,
                    reviewer_user_id=record.reviewer_user_id,
                    decision=record.decision.value,
                    preference_rank=record.preference_rank,
                    taste_score=record.taste_score,
                    realism_score=record.realism_score,
                    fit_score=record.fit_score,
                    notes=record.notes,
                    rejection_reason_json=(
                        _json_dumps(record.rejection_reason_json)
                        if record.rejection_reason_json
                        else None
                    ),
                    created_at=record.created_at,
                )
            )

    def save_region_selection(self, record: RegionSelectionRecord) -> None:
        with self.session() as session:
            session.merge(
                RegionSelectionRow(
                    region_selection_id=record.region_selection_id,
                    design_region_id=record.design_region_id,
                    region_candidate_id=record.region_candidate_id,
                    concept_version_id=record.concept_version_id,
                    selected_by_user_id=record.selected_by_user_id,
                    selection_status=record.selection_status.value,
                    quantity=record.quantity,
                    quantity_basis=record.quantity_basis,
                    approval_state=record.approval_state,
                    selected_at=record.selected_at,
                    approved_at=record.approved_at,
                    selected_product_image_uri=record.selected_product_image_uri,
                )
            )

    def list_region_selections(self, concept_version_id: str) -> list[RegionSelectionRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(RegionSelectionRow).where(
                    RegionSelectionRow.concept_version_id == concept_version_id
                )
            ).all()
            return [self._to_region_selection(r) for r in rows]

    def get_region_selection(self, region_selection_id: str) -> RegionSelectionRecord | None:
        with self.session() as session:
            row = session.get(RegionSelectionRow, region_selection_id)
            return self._to_region_selection(row) if row else None

    def save_approval_event(self, record: ApprovalEventRecord) -> None:
        with self.session() as session:
            session.merge(
                CbApprovalEventRow(
                    approval_event_id=record.approval_event_id,
                    concept_version_id=record.concept_version_id,
                    user_id=record.user_id,
                    approval_type=record.approval_type.value,
                    decision=record.decision,
                    comments=record.comments,
                    created_at=record.created_at,
                )
            )

    def save_procurement_schedule(self, record: ProcurementScheduleRecord) -> None:
        with self.session() as session:
            session.merge(
                ProcurementScheduleRow(
                    procurement_schedule_id=record.procurement_schedule_id,
                    project_id=record.project_id,
                    catalogue_snapshot_id=record.catalogue_snapshot_id,
                    schedule_name=record.schedule_name,
                    status=record.status.value,
                    currency_code=record.currency_code,
                    version_number=record.version_number,
                    created_at=record.created_at,
                    approved_at=record.approved_at,
                )
            )

    def get_procurement_schedule(self, procurement_schedule_id: str) -> ProcurementScheduleRecord | None:
        with self.session() as session:
            row = session.get(ProcurementScheduleRow, procurement_schedule_id)
            return self._to_procurement_schedule(row) if row else None

    def save_procurement_item(self, record: ProcurementItemRecord) -> None:
        with self.session() as session:
            session.merge(
                ProcurementItemRow(
                    procurement_item_id=record.procurement_item_id,
                    procurement_schedule_id=record.procurement_schedule_id,
                    region_selection_id=record.region_selection_id,
                    supplier_offer_id=record.supplier_offer_id,
                    item_name=record.item_name,
                    required_quantity=record.required_quantity,
                    unit_of_measure=record.unit_of_measure,
                    unit_price_snapshot=record.unit_price_snapshot,
                    estimated_total=record.estimated_total,
                    procurement_status=record.procurement_status.value,
                    substitution_policy=record.substitution_policy.value,
                    required_by=record.required_by,
                    created_at=record.created_at,
                )
            )

    def list_procurement_items(
        self, procurement_schedule_id: str
    ) -> list[ProcurementItemRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(ProcurementItemRow).where(
                    ProcurementItemRow.procurement_schedule_id == procurement_schedule_id
                )
            ).all()
            return [self._to_procurement_item(r) for r in rows]

    def save_scope_item(self, record: ScopeItemRecord) -> None:
        with self.session() as session:
            session.merge(
                ScopeItemRow(
                    scope_item_id=record.scope_item_id,
                    project_id=record.project_id,
                    region_selection_id=record.region_selection_id,
                    procurement_item_id=record.procurement_item_id,
                    work_package_code=record.work_package_code,
                    scope_description=record.scope_description,
                    inclusion_json=_json_dumps(record.inclusion_json),
                    exclusion_json=_json_dumps(record.exclusion_json),
                    assumption_json=_json_dumps(record.assumption_json),
                    approval_status=record.approval_status,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )

    def save_integration_export(self, record: IntegrationExportRecord) -> None:
        with self.session() as session:
            session.merge(
                IntegrationExportRow(
                    export_id=record.export_id,
                    project_id=record.project_id,
                    procurement_schedule_id=record.procurement_schedule_id,
                    catalogue_snapshot_id=record.catalogue_snapshot_id,
                    export_type=record.export_type.value,
                    manifest_uri=record.manifest_uri,
                    manifest_sha256=record.manifest_sha256,
                    status=record.status.value,
                    created_at=record.created_at,
                    delivered_at=record.delivered_at,
                )
            )

    def get_variant_by_id(self, variant_id: str):
        from vision_engine.infrastructure.sqlite_repository import GeneratedVariantRow

        with self.session() as session:
            row = session.get(GeneratedVariantRow, variant_id)
            if not row:
                return None
            return self._to_variant(row)

    # --- mappers ---
    @staticmethod
    def _to_concept_board(row: ConceptBoardRow) -> ConceptBoardRecord:
        return ConceptBoardRecord(
            concept_board_id=row.concept_board_id,
            project_id=row.project_id,
            board_name=row.board_name,
            status=ConceptBoardStatus(row.status),
            version=row.version,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_concept_direction(row: ConceptDirectionRow) -> ConceptDirectionRecord:
        return ConceptDirectionRecord(
            concept_direction_id=row.concept_direction_id,
            concept_board_id=row.concept_board_id,
            direction_name=row.direction_name,
            design_intent_json=json.loads(row.design_intent_json or "{}"),
            status=ConceptDirectionStatus(row.status),
            created_at=row.created_at,
            archived_at=row.archived_at,
        )

    @staticmethod
    def _to_concept_version(row: ConceptVersionRow) -> ConceptVersionRecord:
        return ConceptVersionRecord(
            concept_version_id=row.concept_version_id,
            concept_direction_id=row.concept_direction_id,
            parent_concept_version_id=row.parent_concept_version_id,
            version_number=row.version_number,
            version_reason=row.version_reason,
            generation_provider=row.generation_provider,
            generation_model=row.generation_model,
            prompt_version=row.prompt_version,
            status=ConceptVersionStatus(row.status),
            content_sha256=row.content_sha256,
            created_at=row.created_at,
            approved_at=row.approved_at,
        )

    @staticmethod
    def _to_concept_asset(row: ConceptAssetRow) -> ConceptAssetRecord:
        return ConceptAssetRecord(
            concept_asset_id=row.concept_asset_id,
            concept_version_id=row.concept_version_id,
            asset_type=ConceptAssetType(row.asset_type),
            storage_uri=row.storage_uri,
            mime_type=row.mime_type,
            asset_sha256=row.asset_sha256,
            width=row.width,
            height=row.height,
            rights_status=row.rights_status,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_design_region(row: DesignRegionRow) -> DesignRegionRecord:
        return DesignRegionRecord(
            design_region_id=row.design_region_id,
            concept_direction_id=row.concept_direction_id,
            region_code=row.region_code,
            region_type=row.region_type,
            display_name=row.display_name,
            lifecycle_status=DesignRegionLifecycle(row.lifecycle_status),
            is_fixed=row.is_fixed,
            created_at=row.created_at,
            retired_at=row.retired_at,
        )

    @staticmethod
    def _to_region_geometry(row: RegionGeometryRow) -> RegionGeometryRecord:
        return RegionGeometryRecord(
            region_geometry_id=row.region_geometry_id,
            design_region_id=row.design_region_id,
            concept_version_id=row.concept_version_id,
            geometry_type=RegionGeometryType(row.geometry_type),
            geometry_json=json.loads(row.geometry_json or "{}"),
            mask_uri=row.mask_uri,
            mask_sha256=row.mask_sha256,
            confidence=row.confidence,
            source=row.source,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_region_requirement(row: RegionRequirementRow) -> RegionRequirementRecord:
        return RegionRequirementRecord(
            region_requirement_id=row.region_requirement_id,
            design_region_id=row.design_region_id,
            requirement_type=row.requirement_type,
            operator=row.operator,
            value_json=json.loads(row.value_json or "{}"),
            severity=RequirementSeverity(row.severity),
            source=row.source,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_product(row: CbProductRow) -> ProductRecord:
        return ProductRecord(
            product_id=row.product_id,
            canonical_name=row.canonical_name,
            brand_name=row.brand_name,
            product_type=row.product_type,
            description=row.description,
            manufacturer_sku=row.manufacturer_sku,
            lifecycle_status=row.lifecycle_status,
            external_provider=row.external_provider,
            external_product_id=row.external_product_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_product_variant(row: CbProductVariantRow) -> ProductVariantRecord:
        return ProductVariantRecord(
            product_variant_id=row.product_variant_id,
            product_id=row.product_id,
            variant_sku=row.variant_sku,
            colour=row.colour,
            finish=row.finish,
            material=row.material,
            width_mm=row.width_mm,
            height_mm=row.height_mm,
            depth_mm=row.depth_mm,
            weight_kg=row.weight_kg,
            attributes_json=json.loads(row.attributes_json or "{}"),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_supplier_offer(row: CbSupplierOfferRow) -> SupplierOfferRecord:
        return SupplierOfferRecord(
            supplier_offer_id=row.supplier_offer_id,
            supplier_id=row.supplier_id,
            product_variant_id=row.product_variant_id,
            material_variant_id=row.material_variant_id,
            supplier_sku=row.supplier_sku,
            unit_price=row.unit_price,
            currency_code=row.currency_code,
            price_basis=row.price_basis,
            stock_status=row.stock_status,
            stock_quantity=row.stock_quantity,
            lead_time_days_min=row.lead_time_days_min,
            lead_time_days_max=row.lead_time_days_max,
            delivery_coverage_json=json.loads(row.delivery_coverage_json or "{}"),
            price_checked_at=row.price_checked_at,
            valid_until=row.valid_until,
            external_provider=row.external_provider,
            buy_url=row.buy_url,
        )

    @staticmethod
    def _to_catalogue_snapshot(row: CatalogueSnapshotRow) -> CatalogueSnapshotRecord:
        return CatalogueSnapshotRecord(
            catalogue_snapshot_id=row.catalogue_snapshot_id,
            snapshot_name=row.snapshot_name,
            manifest_uri=row.manifest_uri,
            manifest_sha256=row.manifest_sha256,
            item_count=row.item_count,
            status=CatalogueSnapshotStatus(row.status),
            created_at=row.created_at,
            sealed_at=row.sealed_at,
        )

    @staticmethod
    def _to_region_candidate(row: RegionCandidateRow) -> RegionCandidateRecord:
        return RegionCandidateRecord(
            region_candidate_id=row.region_candidate_id,
            design_region_id=row.design_region_id,
            product_retrieval_run_id=row.product_retrieval_run_id,
            product_variant_id=row.product_variant_id,
            material_variant_id=row.material_variant_id,
            catalogue_snapshot_id=row.catalogue_snapshot_id,
            candidate_source=CandidateSource(row.candidate_source),
            candidate_status=CandidateStatus(row.candidate_status),
            match_rationale_json=json.loads(row.match_rationale_json or "{}"),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_region_selection(row: RegionSelectionRow) -> RegionSelectionRecord:
        return RegionSelectionRecord(
            region_selection_id=row.region_selection_id,
            design_region_id=row.design_region_id,
            region_candidate_id=row.region_candidate_id,
            concept_version_id=row.concept_version_id,
            selected_by_user_id=row.selected_by_user_id,
            selection_status=SelectionStatus(row.selection_status),
            quantity=row.quantity,
            quantity_basis=row.quantity_basis,
            approval_state=row.approval_state,
            selected_at=row.selected_at,
            approved_at=row.approved_at,
            selected_product_image_uri=row.selected_product_image_uri,
        )

    @staticmethod
    def _to_procurement_schedule(row: ProcurementScheduleRow) -> ProcurementScheduleRecord:
        return ProcurementScheduleRecord(
            procurement_schedule_id=row.procurement_schedule_id,
            project_id=row.project_id,
            catalogue_snapshot_id=row.catalogue_snapshot_id,
            schedule_name=row.schedule_name,
            status=ProcurementScheduleStatus(row.status),
            currency_code=row.currency_code,
            version_number=row.version_number,
            created_at=row.created_at,
            approved_at=row.approved_at,
        )

    @staticmethod
    def _to_procurement_item(row: ProcurementItemRow) -> ProcurementItemRecord:
        return ProcurementItemRecord(
            procurement_item_id=row.procurement_item_id,
            procurement_schedule_id=row.procurement_schedule_id,
            region_selection_id=row.region_selection_id,
            supplier_offer_id=row.supplier_offer_id,
            item_name=row.item_name,
            required_quantity=row.required_quantity,
            unit_of_measure=row.unit_of_measure,
            unit_price_snapshot=row.unit_price_snapshot,
            estimated_total=row.estimated_total,
            procurement_status=ProcurementItemStatus(row.procurement_status),
            substitution_policy=SubstitutionPolicy(row.substitution_policy),
            required_by=row.required_by,
            created_at=row.created_at,
        )

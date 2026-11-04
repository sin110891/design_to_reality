from __future__ import annotations

from vision_engine.concept_board.application.product_retrieval import maybe_refresh_channel3_candidate
from vision_engine.concept_board.domain.enums import (
    ProcurementItemStatus,
    ProcurementScheduleStatus,
    SelectionStatus,
    SubstitutionPolicy,
)
from vision_engine.concept_board.domain.errors import ProcurementError
from vision_engine.concept_board.domain.models import (
    ProcurementItemRecord,
    ProcurementScheduleRecord,
    ScopeItemRecord,
)
from vision_engine.concept_board.domain.validation import assert_sealed_snapshot
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import utcnow
from vision_engine.settings import AppSettings


def create_procurement_schedule(
    *,
    repo: ConceptBoardRepositoryMixin,
    project_id: str,
    concept_version_id: str,
    schedule_name: str,
    catalogue_snapshot_id: str | None = None,
    currency_code: str = "GBP",
    settings: AppSettings | None = None,
    refresh_external_offers: bool = True,
) -> tuple[ProcurementScheduleRecord, list[ProcurementItemRecord]]:
    snapshot = (
        repo.get_catalogue_snapshot(catalogue_snapshot_id)
        if catalogue_snapshot_id
        else repo.get_active_sealed_snapshot()
    )
    if snapshot is None:
        raise ProcurementError("No sealed catalogue snapshot available")
    assert_sealed_snapshot(snapshot.status, "procurement schedule")

    selections = repo.list_region_selections(concept_version_id)
    approved = [
        s
        for s in selections
        if s.selection_status
        in {SelectionStatus.ARCHITECT_APPROVED, SelectionStatus.PROCUREMENT_APPROVED}
    ]
    if not approved:
        raise ProcurementError("No architect-approved selections on concept version")

    now = utcnow()
    schedule = ProcurementScheduleRecord(
        procurement_schedule_id=new_id("ps"),
        project_id=project_id,
        catalogue_snapshot_id=snapshot.catalogue_snapshot_id,
        schedule_name=schedule_name,
        status=ProcurementScheduleStatus.DRAFT,
        currency_code=currency_code,
        created_at=now,
    )
    repo.save_procurement_schedule(schedule)

    items: list[ProcurementItemRecord] = []
    for selection in approved:
        if refresh_external_offers and settings is not None:
            maybe_refresh_channel3_candidate(
                repo=repo,
                settings=settings,
                region_candidate_id=selection.region_candidate_id,
            )
        candidate = repo.get_region_candidate(selection.region_candidate_id)
        if candidate is None or candidate.product_variant_id is None:
            continue
        catalogue = repo.list_snapshot_product_variants(snapshot.catalogue_snapshot_id)
        offer = None
        product_name = "Unknown item"
        for product, variant, off, _supplier in catalogue:
            if variant.product_variant_id == candidate.product_variant_id:
                offer = off
                product_name = product.canonical_name
                break
        if offer is None:
            continue

        estimated_total = offer.unit_price * selection.quantity
        item = ProcurementItemRecord(
            procurement_item_id=new_id("pi"),
            procurement_schedule_id=schedule.procurement_schedule_id,
            region_selection_id=selection.region_selection_id,
            supplier_offer_id=offer.supplier_offer_id,
            item_name=product_name,
            required_quantity=float(selection.quantity),
            unit_of_measure=selection.quantity_basis,
            unit_price_snapshot=offer.unit_price,
            estimated_total=estimated_total,
            procurement_status=ProcurementItemStatus.DRAFT,
            substitution_policy=SubstitutionPolicy.ARCHITECT_APPROVAL,
            created_at=now,
        )
        repo.save_procurement_item(item)
        items.append(item)

        region = repo.get_design_region(selection.design_region_id)
        repo.save_scope_item(
            ScopeItemRecord(
                scope_item_id=new_id("si"),
                project_id=project_id,
                region_selection_id=selection.region_selection_id,
                procurement_item_id=item.procurement_item_id,
                work_package_code=region.region_type if region else "general",
                scope_description=f"Supply and install {product_name}",
                inclusion_json={"quantity": selection.quantity},
                created_at=now,
                updated_at=now,
            )
        )

    if not items:
        raise ProcurementError("Could not resolve procurement items from selections")
    return schedule, items


def approve_procurement_schedule(
    *,
    repo: ConceptBoardRepositoryMixin,
    procurement_schedule_id: str,
) -> ProcurementScheduleRecord:
    schedule = repo.get_procurement_schedule(procurement_schedule_id)
    if schedule is None:
        raise ProcurementError(f"Schedule not found: {procurement_schedule_id}")
    now = utcnow()
    approved = schedule.model_copy(
        update={"status": ProcurementScheduleStatus.APPROVED, "approved_at": now}
    )
    repo.save_procurement_schedule(approved)
    for item in repo.list_procurement_items(procurement_schedule_id):
        repo.save_procurement_item(
            item.model_copy(update={"procurement_status": ProcurementItemStatus.APPROVED})
        )
    return approved

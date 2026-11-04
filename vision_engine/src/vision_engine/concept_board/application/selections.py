from __future__ import annotations

import shutil
from pathlib import Path

from vision_engine.concept_board.application.product_retrieval import maybe_refresh_channel3_candidate
from vision_engine.concept_board.domain.enums import (
    ApprovalType,
    CandidateStatus,
    ConceptAssetType,
    ConceptVersionStatus,
    ReviewDecisionType,
    SelectionStatus,
)
from vision_engine.concept_board.domain.errors import SelectionError
from vision_engine.concept_board.domain.models import (
    ApprovalEventRecord,
    ConceptAssetRecord,
    ConceptVersionRecord,
    RegionSelectionRecord,
    ReviewDecisionRecord,
    SubstitutionPreviewRecord,
)
from vision_engine.concept_board.domain.validation import assert_not_fixed_region
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import new_id, sha256_file
from vision_engine.infrastructure.sqlite_repository import utcnow
from vision_engine.settings import AppSettings


def select_region_candidate(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings | None = None,
    region_candidate_id: str,
    concept_version_id: str,
    selected_by: str,
    quantity: int = 1,
    refresh_external_offer: bool = True,
    selected_product_image_uri: str | None = None,
) -> RegionSelectionRecord:
    candidate = repo.get_region_candidate(region_candidate_id)
    if candidate is None:
        raise SelectionError(f"Candidate not found: {region_candidate_id}")
    if refresh_external_offer and settings is not None and candidate.product_variant_id:
        maybe_refresh_channel3_candidate(
            repo=repo,
            settings=settings,
            region_candidate_id=region_candidate_id,
        )
    region = repo.get_design_region(candidate.design_region_id)
    if region is None:
        raise SelectionError("Design region not found")
    assert_not_fixed_region(region.is_fixed, "select candidate")

    now = utcnow()
    selection = RegionSelectionRecord(
        region_selection_id=new_id("rs"),
        design_region_id=candidate.design_region_id,
        region_candidate_id=region_candidate_id,
        concept_version_id=concept_version_id,
        selected_by_user_id=selected_by,
        selection_status=SelectionStatus.CLIENT_SELECTED,
        quantity=quantity,
        selected_at=now,
        selected_product_image_uri=selected_product_image_uri,
    )
    repo.save_region_selection(selection)

    updated_candidate = candidate.model_copy(update={"candidate_status": CandidateStatus.SELECTED})
    repo.save_region_candidate(updated_candidate)
    return selection


def approve_region_selection(
    *,
    repo: ConceptBoardRepositoryMixin,
    region_selection_id: str,
    approver: str,
    approval_type: ApprovalType = ApprovalType.ARCHITECT_DESIGN,
) -> RegionSelectionRecord:
    selection = repo.get_region_selection(region_selection_id)
    if selection is None:
        raise SelectionError(f"Selection not found: {region_selection_id}")
    now = utcnow()
    updated = selection.model_copy(
        update={
            "selection_status": SelectionStatus.ARCHITECT_APPROVED,
            "approval_state": "approved",
            "approved_at": now,
        }
    )
    repo.save_region_selection(updated)
    repo.save_approval_event(
        ApprovalEventRecord(
            approval_event_id=new_id("ae"),
            concept_version_id=selection.concept_version_id,
            user_id=approver,
            approval_type=approval_type,
            decision="approved",
            comments=f"Approved selection {region_selection_id}",
            created_at=now,
        )
    )
    return updated


def review_substitution_preview(
    *,
    repo: ConceptBoardRepositoryMixin,
    substitution_preview_id: str,
    reviewer: str,
    decision: ReviewDecisionType,
    notes: str | None = None,
    taste_score: int | None = None,
    realism_score: int | None = None,
    fit_score: int | None = None,
) -> ReviewDecisionRecord:
    record = ReviewDecisionRecord(
        review_decision_id=new_id("rd"),
        substitution_preview_id=substitution_preview_id,
        reviewer_user_id=reviewer,
        decision=decision,
        taste_score=taste_score,
        realism_score=realism_score,
        fit_score=fit_score,
        notes=notes,
        created_at=utcnow(),
    )
    repo.save_review_decision(record)
    return record


def create_concept_version_from_selections(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings,
    concept_direction_id: str,
    parent_concept_version_id: str,
    version_reason: str,
    approver: str,
) -> ConceptVersionRecord:
    parent = repo.get_concept_version(parent_concept_version_id)
    if parent is None:
        raise SelectionError(f"Parent version not found: {parent_concept_version_id}")

    selections = repo.list_region_selections(parent_concept_version_id)
    if not selections:
        raise SelectionError("No selections on parent version")

    parent_asset = repo.get_primary_concept_asset(parent_concept_version_id)
    if parent_asset is None:
        raise SelectionError("Parent primary asset missing")

    now = utcnow()
    version_number = parent.version_number + 1
    version_id = new_id("cv")
    versions_dir = (
        settings.resolve(settings.paths.concept_boards)
        / parent.concept_direction_id
        / "versions"
        / version_id
    )
    versions_dir.mkdir(parents=True, exist_ok=True)
    dest_path = versions_dir / "primary.png"
    shutil.copy2(settings.resolve(parent_asset.storage_uri), dest_path)
    content_sha256 = sha256_file(dest_path)

    version = ConceptVersionRecord(
        concept_version_id=version_id,
        concept_direction_id=concept_direction_id,
        parent_concept_version_id=parent_concept_version_id,
        version_number=version_number,
        version_reason=version_reason,
        generation_provider=parent.generation_provider,
        generation_model=parent.generation_model,
        prompt_version=parent.prompt_version,
        status=ConceptVersionStatus.ARCHITECT_APPROVED,
        content_sha256=content_sha256,
        created_at=now,
        approved_at=now,
    )
    asset = ConceptAssetRecord(
        concept_asset_id=new_id("ca"),
        concept_version_id=version_id,
        asset_type=ConceptAssetType.PRIMARY_RENDER,
        storage_uri=str(dest_path.relative_to(settings.project_root)),
        mime_type=parent_asset.mime_type,
        asset_sha256=content_sha256,
        width=parent_asset.width,
        height=parent_asset.height,
        rights_status=parent_asset.rights_status,
        created_at=now,
    )
    repo.save_concept_version(version)
    repo.save_concept_asset(asset)
    repo.save_approval_event(
        ApprovalEventRecord(
            approval_event_id=new_id("ae"),
            concept_version_id=version_id,
            user_id=approver,
            approval_type=ApprovalType.ARCHITECT_DESIGN,
            decision="approved",
            comments=version_reason,
            created_at=now,
        )
    )

    for selection in selections:
        if selection.selection_status not in {
            SelectionStatus.CLIENT_SELECTED,
            SelectionStatus.ARCHITECT_APPROVED,
        }:
            continue
        repo.save_region_selection(
            selection.model_copy(
                update={
                    "region_selection_id": new_id("rs"),
                    "concept_version_id": version_id,
                    "selection_status": SelectionStatus.ARCHITECT_APPROVED,
                    "approved_at": now,
                }
            )
        )
    return version

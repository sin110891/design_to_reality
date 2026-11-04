from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from vision_engine.domain.enums import (
    ApprovedConceptExportStatus,
    GenerationReviewSetStatus,
    ProjectStatus,
    RetentionConsentStatus,
    ReviewDecision,
    RightsStatus,
)
from vision_engine.domain.models import (
    ApprovedConceptManifest,
    GenerationReviewSet,
    GenerationReviewSetInput,
    VariantReview,
)
from vision_engine.domain.review_validation import ReviewValidationError, validate_review_submission
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import SqliteRepository

MANIFEST_SCHEMA_VERSION = "approved-concept.v1"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def save_generation_review(
    *,
    repo: SqliteRepository,
    payload: GenerationReviewSetInput,
) -> GenerationReviewSet:
    generation_run = repo.get_generation_run(payload.generation_run_id)
    if generation_run is None:
        raise ReviewValidationError("generation_run_id not found")
    if generation_run.project_id != payload.project_id:
        raise ReviewValidationError("project_id does not match generation run")

    variants = repo.list_variants_for_generation(payload.generation_run_id)
    if not variants:
        raise ReviewValidationError("generation run has no variants")

    submitted = payload.status in (
        GenerationReviewSetStatus.SUBMITTED,
        GenerationReviewSetStatus.FINALISED,
    )
    now = utcnow()
    existing = repo.get_latest_review_set(
        generation_run_id=payload.generation_run_id,
        reviewer=payload.reviewer,
    )

    if existing and existing.status == GenerationReviewSetStatus.DRAFT:
        review_set = GenerationReviewSet(
            review_set_id=existing.review_set_id,
            generation_run_id=payload.generation_run_id,
            project_id=payload.project_id,
            reviewer=payload.reviewer,
            status=payload.status,
            winner_variant_id=payload.winner_variant_id,
            overall_notes=payload.overall_notes,
            revision_number=existing.revision_number,
            supersedes_id=existing.supersedes_id,
            created_at=existing.created_at,
            submitted_at=existing.submitted_at if not submitted else now,
            variant_reviews=[],
        )
        repo.delete_variant_reviews_for_review_set(existing.review_set_id)
    else:
        review_set = GenerationReviewSet(
            review_set_id=new_id("grs"),
            generation_run_id=payload.generation_run_id,
            project_id=payload.project_id,
            reviewer=payload.reviewer,
            status=payload.status,
            winner_variant_id=payload.winner_variant_id,
            overall_notes=payload.overall_notes,
            revision_number=1,
            supersedes_id=None,
            created_at=now,
            submitted_at=now if submitted else None,
            variant_reviews=[],
        )
        if existing and existing.status in (
            GenerationReviewSetStatus.SUBMITTED,
            GenerationReviewSetStatus.FINALISED,
        ):
            review_set.revision_number = existing.revision_number + 1
            review_set.supersedes_id = existing.review_set_id
            existing.status = GenerationReviewSetStatus.SUPERSEDED
            repo.save_generation_review_set(existing)

    validate_review_submission(
        review_set=review_set,
        variant_inputs=payload.variants,
        variants=variants,
        submitted=submitted,
    )

    for item in payload.variants:
        review_set.variant_reviews.append(
            VariantReview(
                variant_review_id=new_id("vr"),
                review_set_id=review_set.review_set_id,
                variant_id=item.variant_id,
                decision=item.decision,
                rank_in_set=item.rank_in_set,
                reference_relevance_score=item.reference_relevance_score,
                taste_quality_score=item.taste_quality_score,
                geometry_preservation_score=item.geometry_preservation_score,
                material_coherence_score=item.material_coherence_score,
                buildability_assessment=item.buildability_assessment,
                buildability_score=item.buildability_score,
                positive_notes=item.positive_notes,
                negative_notes=item.negative_notes,
                labels=list(item.labels),
                reviewed_at=now,
            )
        )

    repo.save_generation_review_set(review_set)

    project = repo.get_project(payload.project_id)
    if project and submitted:
        project.status = ProjectStatus.REVIEWED
        project.updated_at = utcnow()
        repo.save_project(project)

    return review_set


def _consent_allows(purpose: RetentionConsentStatus, asset_status: RetentionConsentStatus) -> bool:
    order = {
        RetentionConsentStatus.PENDING: 0,
        RetentionConsentStatus.INTERNAL_REVIEW_ONLY: 1,
        RetentionConsentStatus.EVALUATION_ALLOWED: 2,
        RetentionConsentStatus.MODEL_TRAINING_ALLOWED: 3,
    }
    return order.get(asset_status, 0) >= order.get(purpose, 0)


def promote_approved_concept(
    *,
    repo: SqliteRepository,
    variant_review_id: str,
    purpose: RetentionConsentStatus,
    consented_by: str,
    consent_version: str,
) -> ApprovedConceptManifest:
    variant_review = repo.get_variant_review(variant_review_id)
    if variant_review is None:
        raise ReviewValidationError("variant_review_id not found")
    if variant_review.decision != ReviewDecision.APPROVED:
        raise ReviewValidationError("only approved variant reviews can be promoted")

    review_set = repo.get_review_set(variant_review.review_set_id)
    if review_set is None:
        raise ReviewValidationError("review set not found")
    if review_set.winner_variant_id != variant_review.variant_id:
        raise ReviewValidationError("variant must be the review-set winner")

    asset = repo.get_image_asset(variant_review.variant_id)
    if asset is None or not asset.image_sha256:
        raise ReviewValidationError("generated image asset hash is required")
    if asset.rights_status == RightsStatus.RESTRICTED:
        raise ReviewValidationError("generated image rights are restricted")

    repo.update_image_asset_consent(
        variant_review.variant_id,
        retention_consent_status=purpose,
        consented_by=consented_by,
        consent_version=consent_version,
    )
    asset = repo.get_image_asset(variant_review.variant_id)
    if asset is None:
        raise ReviewValidationError("generated image asset hash is required")

    if not _consent_allows(purpose, asset.retention_consent_status):
        raise ReviewValidationError("retention consent does not permit the requested purpose")

    project = repo.get_project(review_set.project_id)
    if project is None:
        raise ReviewValidationError("project not found")

    generation_run = repo.get_generation_run(review_set.generation_run_id)
    concept_run = (
        repo.get_concept_run(generation_run.concept_run_id)
        if generation_run and generation_run.concept_run_id
        else None
    )
    room_upload = repo.get_room_upload(review_set.project_id)

    export_status = (
        ApprovedConceptExportStatus.APPROVED_FOR_TRAINING
        if purpose == RetentionConsentStatus.MODEL_TRAINING_ALLOWED
        else ApprovedConceptExportStatus.APPROVED_FOR_EVALUATION
    )

    manifest_id = new_id("acm")
    manifest_body = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_id": manifest_id,
        "approved_at": utcnow().isoformat(),
        "review": {
            "review_set_id": review_set.review_set_id,
            "variant_review_id": variant_review.variant_review_id,
            "reviewer": review_set.reviewer,
            "decision": variant_review.decision.value,
            "rank_in_set": variant_review.rank_in_set,
            "scores": {
                "reference_relevance": variant_review.reference_relevance_score,
                "taste_quality": variant_review.taste_quality_score,
                "geometry_preservation": variant_review.geometry_preservation_score,
                "material_coherence": variant_review.material_coherence_score,
                "buildability_assessment": variant_review.buildability_assessment.value,
                "buildability_score": variant_review.buildability_score,
            },
            "labels": variant_review.labels,
        },
        "input": {
            "project_id": project.project_id,
            "room_image_sha256": room_upload.sha256 if room_upload else None,
            "brief": project.brief,
            "constraints": project.constraints,
        },
        "output": {
            "variant_id": variant_review.variant_id,
            "image_sha256": asset.image_sha256,
            "storage_path": asset.storage_path,
            "retention_consent_status": purpose.value,
        },
        "generation": {
            "generation_run_id": review_set.generation_run_id,
            "mode": generation_run.mode.value if generation_run else None,
            "provider": generation_run.provider if generation_run else None,
            "model_name": generation_run.model_name if generation_run else None,
            "prompt_version": generation_run.prompt_version if generation_run else None,
            "concept_direction": (
                concept_run.design_direction.model_dump() if concept_run and concept_run.design_direction else {}
            ),
            "retrieved_reference_ids": generation_run.reference_ids if generation_run else [],
        },
        "consent": {
            "consented_by": consented_by,
            "consent_version": consent_version,
            "purpose": purpose.value,
        },
    }
    manifest_sha256 = hashlib.sha256(
        json.dumps(manifest_body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    manifest = ApprovedConceptManifest(
        manifest_id=manifest_id,
        variant_review_id=variant_review_id,
        variant_id=variant_review.variant_id,
        manifest_sha256=manifest_sha256,
        manifest_schema_version=MANIFEST_SCHEMA_VERSION,
        export_status=export_status,
        retention_consent_status=purpose,
        manifest_json=manifest_body,
        approved_at=utcnow(),
    )
    repo.save_approved_manifest(manifest)
    return manifest

from __future__ import annotations

from vision_engine.domain.enums import (
    BuildabilityAssessment,
    ReviewDecision,
    VariantReviewStatus,
)
from vision_engine.domain.models import (
    GenerationReviewSet,
    GeneratedVariant,
    VariantReviewInput,
)


class ReviewValidationError(ValueError):
    """Raised when a review submission violates ERD constraints."""


def validate_buildability(
    *,
    assessment: BuildabilityAssessment,
    score: int | None,
) -> None:
    if assessment == BuildabilityAssessment.ASSESSABLE:
        if score is None or not 1 <= score <= 5:
            raise ReviewValidationError(
                "buildability_score is required (1-5) when assessment is assessable"
            )
    elif score is not None:
        raise ReviewValidationError(
            "buildability_score must be null when assessment is not assessable"
        )


def validate_variant_review_input(payload: VariantReviewInput) -> None:
    validate_buildability(
        assessment=payload.buildability_assessment,
        score=payload.buildability_score,
    )
    for field_name in (
        "reference_relevance_score",
        "taste_quality_score",
        "geometry_preservation_score",
        "material_coherence_score",
    ):
        value = getattr(payload, field_name)
        if value is not None and not 1 <= value <= 5:
            raise ReviewValidationError(f"{field_name} must be between 1 and 5")


def validate_review_submission(
    *,
    review_set: GenerationReviewSet,
    variant_inputs: list[VariantReviewInput],
    variants: list[GeneratedVariant],
    submitted: bool,
) -> None:
    variant_ids = {v.variant_id for v in variants}
    input_ids = {v.variant_id for v in variant_inputs}

    for payload in variant_inputs:
        if payload.variant_id not in variant_ids:
            raise ReviewValidationError(
                f"variant {payload.variant_id} does not belong to this generation run"
            )
        validate_variant_review_input(payload)

    if review_set.winner_variant_id is not None:
        if review_set.winner_variant_id not in variant_ids:
            raise ReviewValidationError("winner_variant_id must belong to the generation run")
        winner_review = next(
            (v for v in variant_inputs if v.variant_id == review_set.winner_variant_id),
            None,
        )
        if winner_review is None:
            raise ReviewValidationError("winner variant must have a variant review")
        if winner_review.decision != ReviewDecision.APPROVED:
            raise ReviewValidationError("winner variant must have decision approved")

    approved_ids = [v.variant_id for v in variant_inputs if v.decision == ReviewDecision.APPROVED]
    if review_set.winner_variant_id is None and approved_ids and submitted:
        raise ReviewValidationError(
            "approved variants require a winner selection on submit"
        )
    if review_set.winner_variant_id and review_set.winner_variant_id not in approved_ids:
        raise ReviewValidationError("winner must have decision approved")

    ranks = [v.rank_in_set for v in variant_inputs if v.rank_in_set is not None]
    if ranks:
        if len(ranks) != len(set(ranks)):
            raise ReviewValidationError("rank_in_set values must be unique within a review set")
        for rank in ranks:
            if rank < 1 or rank > len(variants):
                raise ReviewValidationError(
                    f"rank_in_set must be between 1 and {len(variants)}"
                )
        if submitted and len(ranks) != len(variant_inputs):
            raise ReviewValidationError(
                "either every variant has a distinct rank or no ranks are provided"
            )

    if submitted and input_ids != variant_ids:
        raise ReviewValidationError("submitted review must include every generated variant")

from __future__ import annotations

import pytest

from vision_engine.domain.enums import (
    BuildabilityAssessment,
    GenerationMode,
    GenerationReviewSetStatus,
    ReviewDecision,
    VariantKind,
)
from vision_engine.domain.models import GeneratedVariant, GenerationReviewSet, VariantReviewInput
from vision_engine.domain.review_validation import (
    ReviewValidationError,
    validate_buildability,
    validate_review_submission,
)


def _variants() -> list[GeneratedVariant]:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return [
        GeneratedVariant(
            variant_id="var_a",
            generation_run_id="gen_1",
            project_id="proj_1",
            mode=GenerationMode.CURATED,
            kind=VariantKind.CLOSEST,
            image_path="generated/a.png",
            rank_hint=1,
            created_at=now,
        ),
        GeneratedVariant(
            variant_id="var_b",
            generation_run_id="gen_1",
            project_id="proj_1",
            mode=GenerationMode.CURATED,
            kind=VariantKind.CONSERVATIVE,
            image_path="generated/b.png",
            rank_hint=2,
            created_at=now,
        ),
    ]


def _review_set(**kwargs) -> GenerationReviewSet:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    defaults = dict(
        review_set_id="grs_1",
        generation_run_id="gen_1",
        project_id="proj_1",
        reviewer="Lloyd Lee",
        status=GenerationReviewSetStatus.SUBMITTED,
        winner_variant_id="var_a",
        overall_notes=None,
        revision_number=1,
        supersedes_id=None,
        created_at=now,
        submitted_at=now,
        variant_reviews=[],
    )
    defaults.update(kwargs)
    return GenerationReviewSet(**defaults)


def test_winner_must_belong_to_generation_run():
    review_set = _review_set(winner_variant_id="var_other")
    inputs = [
        VariantReviewInput(
            variant_id="var_a",
            decision=ReviewDecision.APPROVED,
            rank_in_set=1,
            buildability_assessment=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL,
        )
    ]
    with pytest.raises(ReviewValidationError, match="belong"):
        validate_review_submission(
            review_set=review_set,
            variant_inputs=inputs,
            variants=_variants(),
            submitted=True,
        )


def test_duplicate_rank_rejected():
    review_set = _review_set(winner_variant_id="var_a")
    inputs = [
        VariantReviewInput(
            variant_id="var_a",
            decision=ReviewDecision.APPROVED,
            rank_in_set=1,
            buildability_assessment=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL,
        ),
        VariantReviewInput(
            variant_id="var_b",
            decision=ReviewDecision.REJECTED,
            rank_in_set=1,
            buildability_assessment=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL,
        ),
    ]
    with pytest.raises(ReviewValidationError, match="unique"):
        validate_review_submission(
            review_set=review_set,
            variant_inputs=inputs,
            variants=_variants(),
            submitted=True,
        )


def test_winner_must_be_approved():
    review_set = _review_set(winner_variant_id="var_a")
    inputs = [
        VariantReviewInput(
            variant_id="var_a",
            decision=ReviewDecision.REJECTED,
            rank_in_set=1,
            buildability_assessment=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL,
        ),
        VariantReviewInput(
            variant_id="var_b",
            decision=ReviewDecision.REJECTED,
            rank_in_set=2,
            buildability_assessment=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL,
        ),
    ]
    with pytest.raises(ReviewValidationError, match="approved"):
        validate_review_submission(
            review_set=review_set,
            variant_inputs=inputs,
            variants=_variants(),
            submitted=True,
        )


def test_buildability_score_required_when_assessable():
    with pytest.raises(ReviewValidationError, match="buildability_score"):
        validate_buildability(
            assessment=BuildabilityAssessment.ASSESSABLE,
            score=None,
        )


def test_buildability_score_forbidden_when_not_assessable():
    with pytest.raises(ReviewValidationError, match="must be null"):
        validate_buildability(
            assessment=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL,
            score=4,
        )

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from vision_engine.application.export_review_training import (
    export_approved_concepts,
    export_review_training_dataset,
)
from vision_engine.application.review_feedback import promote_approved_concept, save_generation_review
from vision_engine.application.run_pipeline import run_pipeline
from vision_engine.domain.enums import (
    BuildabilityAssessment,
    GenerationMode,
    GenerationReviewSetStatus,
    RetentionConsentStatus,
    ReviewDecision,
)
from vision_engine.domain.models import GenerationReviewSetInput, ProjectInput, VariantReviewInput
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings, clear_settings_cache


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT.parent / "dataset_factory"
SOURCE_IMAGES = FACTORY / "tests" / "fixtures" / "sample_data" / "raw_images" / "contemporary_europe"
GOLD = FACTORY / "tests" / "fixtures" / "sample_data" / "exports" / "gemini_demo_gold.jsonl"


def _settings(tmp_path: Path) -> AppSettings:
    clear_settings_cache()
    for name in ("configs", "src"):
        src = ROOT / name
        dest = tmp_path / name
        if not dest.exists():
            shutil.copytree(src, dest)
    settings = AppSettings(
        model_provider="fake",
        model_name="fake-concept-v1",
        image_edit_model="fake-image-edit-v1",
        embedding_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "configs" / "rulebook.v1.yaml",
        app_config_path=tmp_path / "configs" / "app.local.yaml",
        prompts_config_path=tmp_path / "configs" / "prompts.v1.yaml",
        concept_prompt_version="concept_direction",
        image_edit_prompt_version="image_edit",
        project_root=tmp_path,
    )
    settings.paths.uploads = tmp_path / "uploads"
    settings.paths.generated = tmp_path / "generated"
    settings.paths.exports = tmp_path / "exports"
    settings.paths.index_path = tmp_path / "indexes" / "curated.npz"
    settings.paths.curated_images = SOURCE_IMAGES
    return settings


@pytest.mark.skipif(not SOURCE_IMAGES.exists(), reason="dataset_factory sample images required")
def test_review_submit_promote_export(tmp_path: Path):
    from vision_engine.application.build_index import build_index

    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )
    build_index(
        repo=repo,
        settings=settings,
        gold_jsonl=GOLD,
        images_dir=SOURCE_IMAGES,
        output=settings.paths.index_path,
    )

    room = sorted(SOURCE_IMAGES.glob("*.jpg"))[0]
    result = run_pipeline(
        repo=repo,
        settings=settings,
        file_store=file_store,
        payload=ProjectInput(
            room_image_path=str(room),
            room_type="living_room",
            style_family="Contemporary Europe",
            brief="warm contemporary European, calmer lighting, retain windows and fireplace",
            constraints=["do not move walls, doors, windows, radiators, or fireplace"],
        ),
        mode=GenerationMode.CURATED,
    )
    assert result.generation_run_id
    assert len(result.variants) == 3
    winner = result.variants[0]

    for variant in result.variants:
        asset = repo.get_image_asset(variant.variant_id)
        assert asset is not None
        assert len(asset.image_sha256) == 64

    review_set = save_generation_review(
        repo=repo,
        payload=GenerationReviewSetInput(
            generation_run_id=result.generation_run_id,
            project_id=result.project.project_id,
            reviewer="Lloyd Lee",
            status=GenerationReviewSetStatus.SUBMITTED,
            winner_variant_id=winner.variant_id,
            overall_notes="A is closest.",
            variants=[
                VariantReviewInput(
                    variant_id=winner.variant_id,
                    decision=ReviewDecision.APPROVED,
                    rank_in_set=1,
                    reference_relevance_score=5,
                    taste_quality_score=5,
                    geometry_preservation_score=4,
                    material_coherence_score=5,
                    buildability_assessment=BuildabilityAssessment.REQUIRES_SITE_VERIFICATION,
                    labels=["good_material_coherence"],
                    positive_notes="Strong palette.",
                ),
                *[
                    VariantReviewInput(
                        variant_id=v.variant_id,
                        decision=ReviewDecision.REJECTED,
                        rank_in_set=idx + 2,
                        buildability_assessment=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL,
                        labels=["material_conflict"] if idx == 0 else [],
                        negative_notes="Not preferred.",
                    )
                    for idx, v in enumerate(result.variants[1:])
                ],
            ],
        ),
    )
    assert review_set.review_set_id.startswith("grs_")

    winner_review = next(
        v for v in review_set.variant_reviews if v.variant_id == winner.variant_id
    )
    manifest = promote_approved_concept(
        repo=repo,
        variant_review_id=winner_review.variant_review_id,
        purpose=RetentionConsentStatus.EVALUATION_ALLOWED,
        consented_by="Lloyd Lee",
        consent_version="review-consent.v1",
    )
    assert manifest.manifest_id.startswith("acm_")
    assert manifest.manifest_sha256
    assert manifest.manifest_json["output"]["image_sha256"]

    training_out = tmp_path / "review_training.jsonl"
    path, count = export_review_training_dataset(
        repo=repo, settings=settings, output=training_out, fmt="jsonl"
    )
    assert count >= 3
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[0]["generation_run_id"] == result.generation_run_id

    approved_out = tmp_path / "approved_concepts.jsonl"
    _, manifest_count = export_approved_concepts(
        repo=repo, settings=settings, output=approved_out, fmt="jsonl"
    )
    assert manifest_count == 1

    counts = repo.counts()
    assert counts["review_sets"] >= 1
    assert counts["approved_manifests"] == 1


@pytest.mark.skipif(not SOURCE_IMAGES.exists(), reason="dataset_factory sample images required")
def test_draft_then_submit_updates_same_review_set(tmp_path: Path):
    from vision_engine.application.build_index import build_index

    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )
    build_index(
        repo=repo,
        settings=settings,
        gold_jsonl=GOLD,
        images_dir=SOURCE_IMAGES,
        output=settings.paths.index_path,
    )

    room = sorted(SOURCE_IMAGES.glob("*.jpg"))[0]
    result = run_pipeline(
        repo=repo,
        settings=settings,
        file_store=file_store,
        payload=ProjectInput(
            room_image_path=str(room),
            room_type="living_room",
            style_family="Contemporary Europe",
            brief="warm contemporary European living room refresh",
        ),
        mode=GenerationMode.CURATED,
    )
    winner = result.variants[0]

    def _payload(status: GenerationReviewSetStatus) -> GenerationReviewSetInput:
        return GenerationReviewSetInput(
            generation_run_id=result.generation_run_id,
            project_id=result.project.project_id,
            reviewer="Lloyd Lee",
            status=status,
            winner_variant_id=winner.variant_id,
            overall_notes="Draft then submit",
            variants=[
                VariantReviewInput(
                    variant_id=v.variant_id,
                    decision=ReviewDecision.APPROVED if v.variant_id == winner.variant_id else ReviewDecision.REJECTED,
                    rank_in_set=idx + 1,
                    buildability_assessment=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL,
                )
                for idx, v in enumerate(result.variants)
            ],
        )

    draft = save_generation_review(repo=repo, payload=_payload(GenerationReviewSetStatus.DRAFT))
    submitted = save_generation_review(
        repo=repo, payload=_payload(GenerationReviewSetStatus.SUBMITTED)
    )

    assert submitted.review_set_id == draft.review_set_id
    assert submitted.status == GenerationReviewSetStatus.SUBMITTED
    assert submitted.submitted_at is not None
    assert repo.counts()["review_sets"] == 1
    assert repo.counts()["variant_reviews"] == 3

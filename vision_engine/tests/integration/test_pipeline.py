from __future__ import annotations

import json
import shutil
from pathlib import Path

from vision_engine.application.build_index import build_index, load_index
from vision_engine.application.export_feedback import export_feedback_dataset
from vision_engine.application.record_feedback import record_feedback
from vision_engine.application.run_pipeline import run_pipeline
from vision_engine.domain.enums import GenerationMode, ReviewDecision
from vision_engine.domain.models import ProjectInput
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings, clear_settings_cache


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT.parent / "dataset_factory"
SOURCE_IMAGES = FACTORY / "data" / "raw_images" / "contemporary_europe"
GOLD = FACTORY / "data" / "exports" / "gemini_demo_gold.jsonl"


def _settings(tmp_path: Path) -> AppSettings:
    clear_settings_cache()
    # Copy prompt/config assets into the temp project root so resolve() stays consistent.
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


def test_index_retrieve_concept_variants_feedback(tmp_path: Path):
    assert SOURCE_IMAGES.exists(), "expected dataset_factory sample images"
    assert GOLD.exists(), "expected dataset_factory gold JSONL"

    settings = _settings(tmp_path)

    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )

    index_path, count = build_index(
        repo=repo,
        settings=settings,
        gold_jsonl=GOLD,
        images_dir=SOURCE_IMAGES,
        output=settings.paths.index_path,
    )
    assert count >= 1
    assert index_path.exists()
    store = load_index(settings)
    assert len(store.records) == count

    room = sorted(SOURCE_IMAGES.glob("*.jpg"))[0]
    # Use a different image as the "room" so retrieval is meaningful
    room_copy = tmp_path / "room.jpg"
    shutil.copy2(room, room_copy)

    payload = ProjectInput(
        room_image_path=str(room_copy),
        room_type="living_room",
        style_family="Contemporary Europe",
        brief="warm contemporary European, calmer lighting, retain windows and fireplace",
        budget_band="medium_high",
        constraints=["do not move walls, doors, windows, radiators, or fireplace"],
    )
    result = run_pipeline(
        repo=repo,
        settings=settings,
        file_store=file_store,
        payload=payload,
        mode=GenerationMode.CURATED,
    )
    assert result.design_direction is not None
    assert result.design_direction.concept_title
    assert len(result.references) >= 1
    assert len(result.variants) == 3
    for variant in result.variants:
        assert settings.resolve(variant.image_path).exists()

    event = record_feedback(
        repo=repo,
        project_id=result.project.project_id,
        reviewer="Lloyd Lee",
        decision=ReviewDecision.APPROVED,
        variant_id=result.variants[0].variant_id,
        rank=1,
        taste_quality_score=5,
        geometry_preservation_score=4,
        positive_notes="Strong restrained palette.",
        failure_tags=[],
    )
    assert event.feedback_id.startswith("fb_")

    out = tmp_path / "feedback.jsonl"
    path, n = export_feedback_dataset(repo=repo, settings=settings, output=out, fmt="jsonl")
    assert n == 1
    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["decision"] == "approved"
    assert payload["taste_quality_score"] == 5


def test_baseline_skips_references(tmp_path: Path):
    assert SOURCE_IMAGES.exists() and GOLD.exists()
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
            brief="generic bright living room refresh",
        ),
        mode=GenerationMode.BASELINE,
        skip_image_edit=True,
    )
    assert result.references == []
    assert result.design_direction is not None
    assert result.variants == []

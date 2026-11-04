from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from vision_engine.application.run_pipeline import run_pipeline
from vision_engine.concept_board.application.bootstrap import bootstrap_concept_board_from_variant
from vision_engine.concept_board.application.catalogue import import_catalogue_csv
from vision_engine.concept_board.application.integration_export import export_procurement_csv
from vision_engine.concept_board.application.procurement import (
    approve_procurement_schedule,
    create_procurement_schedule,
)
from vision_engine.concept_board.application.product_retrieval import retrieve_product_candidates
from vision_engine.concept_board.application.regions import (
    add_region_geometry,
    add_region_requirement,
    confirm_design_region,
    create_design_region,
)
from vision_engine.concept_board.application.selections import (
    approve_region_selection,
    create_concept_version_from_selections,
    select_region_candidate,
)
from vision_engine.concept_board.application.substitutions import generate_substitution_preview
from vision_engine.concept_board.domain.enums import RegionGeometryType, RequirementSeverity
from vision_engine.virtual_staging.domain.enums import EvidenceGrade
from vision_engine.domain.enums import GenerationMode
from vision_engine.domain.models import ProjectInput
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings, clear_settings_cache


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT.parent / "dataset_factory"
SOURCE_IMAGES = FACTORY / "data" / "raw_images" / "contemporary_europe"
GOLD = FACTORY / "data" / "exports" / "gemini_demo_gold.jsonl"
CATALOGUE = ROOT / "data" / "catalogue" / "sample_products.csv"


def _settings(tmp_path: Path) -> AppSettings:
    clear_settings_cache()
    for name in ("configs", "src", "data"):
        src = ROOT / name
        dest = tmp_path / name
        if src.exists() and not dest.exists():
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
    settings = AppSettings(
        model_provider="fake",
        model_name="fake-concept-v1",
        image_edit_model="fake-image-edit-v1",
        embedding_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "configs" / "rulebook.v1.yaml",
        app_config_path=tmp_path / "configs" / "app.local.yaml",
        prompts_config_path=tmp_path / "configs" / "prompts.v1.yaml",
        project_root=tmp_path,
    )
    settings.paths.uploads = tmp_path / "uploads"
    settings.paths.generated = tmp_path / "generated"
    settings.paths.exports = tmp_path / "exports"
    settings.paths.concept_boards = tmp_path / "concept_boards"
    settings.paths.catalogue = tmp_path / "data" / "catalogue"
    settings.paths.staging = tmp_path / "staging"
    settings.paths.index_path = tmp_path / "indexes" / "curated.npz"
    settings.paths.curated_images = SOURCE_IMAGES
    return settings


@pytest.mark.skipif(not SOURCE_IMAGES.exists(), reason="dataset_factory sample images required")
@pytest.mark.skipif(not CATALOGUE.exists(), reason="sample catalogue required")
def test_concept_board_end_to_end_workflow(tmp_path: Path):
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

    room = next(SOURCE_IMAGES.glob("*.jpg"))
    result = run_pipeline(
        repo=repo,
        settings=settings,
        file_store=file_store,
        payload=ProjectInput(
            room_image_path=str(room),
            room_type="living_room",
            style_family="Contemporary Europe",
            brief="warm contemporary European, retain windows",
        ),
        mode=GenerationMode.CURATED,
    )
    assert result.variants
    variant_id = result.variants[0].variant_id
    project_id = result.project.project_id

    import_catalogue_csv(repo=repo, csv_path=CATALOGUE, snapshot_name="test-v1", seal=True)
    board, direction, version = bootstrap_concept_board_from_variant(
        repo=repo,
        settings=settings,
        project_id=project_id,
        variant_id=variant_id,
    )
    assert board.concept_board_id.startswith("cb_")

    region = create_design_region(
        repo=repo,
        concept_direction_id=direction.concept_direction_id,
        region_code="sofa_01",
        region_type="sofa",
        display_name="Main Sofa",
    )
    add_region_geometry(
        repo=repo,
        design_region_id=region.design_region_id,
        concept_version_id=version.concept_version_id,
        geometry_type=RegionGeometryType.BOUNDING_BOX,
        geometry_json={"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.25},
    )
    add_region_requirement(
        repo=repo,
        design_region_id=region.design_region_id,
        requirement_type="budget",
        operator="<=",
        value_json={"amount": 3000, "currency": "GBP"},
        severity=RequirementSeverity.HARD,
    )
    confirm_design_region(
        repo=repo,
        design_region_id=region.design_region_id,
        reviewer="architect",
        concept_version_id=version.concept_version_id,
    )

    run, candidates = retrieve_product_candidates(
        repo=repo,
        design_region_id=region.design_region_id,
        concept_version_id=version.concept_version_id,
        top_k=3,
    )
    assert run.product_retrieval_run_id
    assert candidates

    preview = generate_substitution_preview(
        repo=repo,
        settings=settings,
        file_store=file_store,
        region_candidate_id=candidates[0].region_candidate_id,
        concept_version_id=version.concept_version_id,
    )
    assert preview.evidence_grade == EvidenceGrade.VISUAL_PREVIEW_ONLY.value
    assert preview.virtual_staging_output_id

    selection = select_region_candidate(
        repo=repo,
        region_candidate_id=candidates[0].region_candidate_id,
        concept_version_id=version.concept_version_id,
        selected_by="client",
    )
    approve_region_selection(
        repo=repo,
        region_selection_id=selection.region_selection_id,
        approver="architect",
    )
    new_version = create_concept_version_from_selections(
        repo=repo,
        settings=settings,
        concept_direction_id=direction.concept_direction_id,
        parent_concept_version_id=version.concept_version_id,
        version_reason="Applied sofa selection",
        approver="architect",
    )
    assert new_version.version_number == 2

    schedule, items = create_procurement_schedule(
        repo=repo,
        project_id=project_id,
        concept_version_id=new_version.concept_version_id,
        schedule_name="Test schedule",
    )
    assert items
    schedule = approve_procurement_schedule(
        repo=repo,
        procurement_schedule_id=schedule.procurement_schedule_id,
    )
    export = export_procurement_csv(
        repo=repo,
        settings=settings,
        procurement_schedule_id=schedule.procurement_schedule_id,
    )
    assert export.manifest_sha256
    manifest_path = settings.resolve(export.manifest_uri)
    assert manifest_path.exists()

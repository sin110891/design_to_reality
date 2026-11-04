from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from vision_engine.concept_board.application.catalogue import import_catalogue_csv
from vision_engine.concept_board.application.product_retrieval import retrieve_product_candidates
from vision_engine.concept_board.application.regions import (
    add_region_geometry,
    confirm_design_region,
    create_design_region,
)
from vision_engine.concept_board.application.selections import (
    approve_region_selection,
    select_region_candidate,
)
from vision_engine.concept_board.application.substitutions import generate_substitution_preview
from vision_engine.concept_board.domain.enums import (
    ConceptAssetType,
    ConceptBoardStatus,
    ConceptDirectionStatus,
    ConceptVersionStatus,
    RegionGeometryType,
)
from vision_engine.concept_board.domain.models import (
    ConceptAssetRecord,
    ConceptBoardRecord,
    ConceptDirectionRecord,
    ConceptVersionRecord,
)
from vision_engine.domain.enums import ProjectStatus
from vision_engine.domain.models import ProjectRecord
from vision_engine.infrastructure.file_store import FileStore, sha256_file
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, utcnow
from vision_engine.settings import AppSettings, clear_settings_cache


ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "tests" / "fixtures" / "catalogue" / "sample_products.csv"


def _settings(tmp_path: Path) -> AppSettings:
    clear_settings_cache()
    for name in ("configs", "src"):
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
        image_edit_model="fake-image-edit-v1",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "configs" / "rulebook.v1.yaml",
        app_config_path=tmp_path / "configs" / "app.local.yaml",
        prompts_config_path=tmp_path / "configs" / "prompts.v1.yaml",
        project_root=tmp_path,
    )
    settings.paths.concept_boards = tmp_path / "concept_boards"
    settings.paths.staging = tmp_path / "staging"
    settings.paths.catalogue = tmp_path / "data" / "catalogue"
    settings.paths.uploads = tmp_path / "uploads"
    settings.paths.generated = tmp_path / "generated"
    settings.virtual_staging.cumulative_preview_mode = "local_composite"
    return settings


@pytest.mark.skipif(not CATALOGUE.exists(), reason="sample catalogue required")
def test_cumulative_local_preview_composites_two_regions(tmp_path: Path):
    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )

    room_path = tmp_path / "room.png"
    Image.new("RGB", (800, 600), (220, 220, 220)).save(room_path)
    import_catalogue_csv(repo=repo, csv_path=CATALOGUE, snapshot_name="staging-test", seal=True)

    board_dir = settings.paths.concept_boards / "cd_test" / "versions" / "cv_test"
    board_dir.mkdir(parents=True)
    concept_path = board_dir / "primary.png"
    shutil.copy2(room_path, concept_path)

    now = utcnow()
    repo.save_project(
        ProjectRecord(
            project_id="proj_test",
            room_image_path=str(room_path),
            inspiration_paths=[],
            room_type="living_room",
            style_family="Contemporary",
            brief="test",
            budget_band=None,
            constraints=[],
            project_type="residential",
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now,
        )
    )
    repo.save_concept_board(
        ConceptBoardRecord(
            concept_board_id="cb_test",
            project_id="proj_test",
            board_name="Test",
            status=ConceptBoardStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
    )
    repo.save_concept_direction(
        ConceptDirectionRecord(
            concept_direction_id="cd_test",
            concept_board_id="cb_test",
            direction_name="Main",
            design_intent_json={},
            status=ConceptDirectionStatus.ACTIVE,
            created_at=now,
        )
    )
    repo.save_concept_version(
        ConceptVersionRecord(
            concept_version_id="cv_test",
            concept_direction_id="cd_test",
            parent_concept_version_id=None,
            version_number=1,
            version_reason="bootstrap",
            generation_provider="fake",
            generation_model="fake",
            prompt_version="test",
            status=ConceptVersionStatus.GENERATED,
            content_sha256=sha256_file(concept_path),
            created_at=now,
        )
    )
    repo.save_concept_asset(
        ConceptAssetRecord(
            concept_asset_id="ca_test",
            concept_version_id="cv_test",
            asset_type=ConceptAssetType.PRIMARY_RENDER,
            storage_uri=str(concept_path.relative_to(settings.project_root)),
            mime_type="image/png",
            asset_sha256=sha256_file(concept_path),
            width=800,
            height=600,
            rights_status="generated",
            created_at=now,
        )
    )

    sofa = create_design_region(
        repo=repo,
        concept_direction_id="cd_test",
        region_code="sofa_01",
        region_type="sofa",
        display_name="Sofa",
    )
    add_region_geometry(
        repo=repo,
        design_region_id=sofa.design_region_id,
        concept_version_id="cv_test",
        geometry_type=RegionGeometryType.BOUNDING_BOX,
        geometry_json={"x": 0.1, "y": 0.4, "width": 0.35, "height": 0.25},
    )
    confirm_design_region(
        repo=repo,
        design_region_id=sofa.design_region_id,
        reviewer="architect",
        concept_version_id="cv_test",
    )
    rug = create_design_region(
        repo=repo,
        concept_direction_id="cd_test",
        region_code="rug_01",
        region_type="rug",
        display_name="Rug",
    )
    add_region_geometry(
        repo=repo,
        design_region_id=rug.design_region_id,
        concept_version_id="cv_test",
        geometry_type=RegionGeometryType.BOUNDING_BOX,
        geometry_json={"x": 0.2, "y": 0.7, "width": 0.5, "height": 0.15},
    )
    confirm_design_region(
        repo=repo,
        design_region_id=rug.design_region_id,
        reviewer="architect",
        concept_version_id="cv_test",
    )

    _, sofa_candidates = retrieve_product_candidates(
        repo=repo,
        design_region_id=sofa.design_region_id,
        concept_version_id="cv_test",
        top_k=1,
    )
    _, rug_candidates = retrieve_product_candidates(
        repo=repo,
        design_region_id=rug.design_region_id,
        concept_version_id="cv_test",
        top_k=1,
    )
    assert sofa_candidates and rug_candidates

    sofa_selection = select_region_candidate(
        repo=repo,
        settings=settings,
        region_candidate_id=sofa_candidates[0].region_candidate_id,
        concept_version_id="cv_test",
        selected_by="client",
    )
    approve_region_selection(
        repo=repo,
        region_selection_id=sofa_selection.region_selection_id,
        approver="architect",
    )

    preview = generate_substitution_preview(
        repo=repo,
        settings=settings,
        file_store=file_store,
        region_candidate_id=rug_candidates[0].region_candidate_id,
        concept_version_id="cv_test",
        cumulative_enabled=True,
        cumulative_mode="Local multi-mask composite",
    )
    output = settings.resolve(preview.preview_asset_uri)
    assert output.exists()
    assert preview.generation_provider == "local_composite"

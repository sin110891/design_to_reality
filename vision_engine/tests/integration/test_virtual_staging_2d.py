from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from vision_engine.concept_board.application.catalogue import import_catalogue_csv
from vision_engine.concept_board.application.product_retrieval import retrieve_product_candidates
from vision_engine.concept_board.application.regions import (
    add_region_geometry,
    confirm_design_region,
    create_design_region,
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
from vision_engine.infrastructure.file_store import FileStore, sha256_file
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, utcnow
from vision_engine.settings import AppSettings, clear_settings_cache
from vision_engine.virtual_staging.domain.enums import EvidenceGrade, StagingMode


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
    return settings


@pytest.mark.skipif(not CATALOGUE.exists(), reason="sample catalogue required")
def test_2d_product_staging_creates_provenance(tmp_path: Path):
    from PIL import Image

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
    board = ConceptBoardRecord(
        concept_board_id="cb_test",
        project_id="proj_test",
        board_name="Test",
        status=ConceptBoardStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    direction = ConceptDirectionRecord(
        concept_direction_id="cd_test",
        concept_board_id="cb_test",
        direction_name="Main",
        design_intent_json={},
        status=ConceptDirectionStatus.ACTIVE,
        created_at=now,
    )
    version = ConceptVersionRecord(
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
    asset = ConceptAssetRecord(
        concept_asset_id="ca_test",
        concept_version_id="cv_test",
        asset_type=ConceptAssetType.PRIMARY_RENDER,
        storage_uri=str(concept_path.relative_to(settings.project_root)),
        mime_type="image/png",
        asset_sha256=sha256_file(concept_path),
        width=800,
        height=600,
        rights_status="user_owned",
        created_at=now,
    )
    from vision_engine.domain.enums import ProjectStatus
    from vision_engine.domain.models import ProjectRecord

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
    repo.save_concept_board(board)
    repo.save_concept_direction(direction)
    repo.save_concept_version(version)
    repo.save_concept_asset(asset)

    region = create_design_region(
        repo=repo,
        concept_direction_id="cd_test",
        region_code="sofa_01",
        region_type="sofa",
        display_name="Main sofa",
    )
    add_region_geometry(
        repo=repo,
        design_region_id=region.design_region_id,
        concept_version_id="cv_test",
        geometry_type=RegionGeometryType.BOUNDING_BOX,
        geometry_json={"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.25},
    )
    confirm_design_region(
        repo=repo,
        design_region_id=region.design_region_id,
        reviewer="architect",
        concept_version_id="cv_test",
    )

    _run, candidates = retrieve_product_candidates(
        repo=repo,
        design_region_id=region.design_region_id,
        concept_version_id="cv_test",
        top_k=1,
    )
    assert candidates

    preview = generate_substitution_preview(
        repo=repo,
        settings=settings,
        file_store=file_store,
        region_candidate_id=candidates[0].region_candidate_id,
        concept_version_id="cv_test",
    )

    assert preview.virtual_staging_output_id
    assert preview.evidence_grade == EvidenceGrade.VISUAL_PREVIEW_ONLY.value
    assert preview.disclaimer

    output = repo.get_virtual_staging_output(preview.virtual_staging_output_id)
    assert output is not None
    assert output.evidence_grade == EvidenceGrade.VISUAL_PREVIEW_ONLY

    request = repo.get_staging_request(output.staging_request_id)
    assert request is not None
    assert request.staging_mode == StagingMode.IMAGE_EDIT_2D

    preview_path = settings.resolve(preview.preview_asset_uri)
    assert preview_path.exists()

    manifest_path = settings.resolve(output.provenance_manifest_uri)
    assert manifest_path.exists()

    with Image.open(preview_path) as staged:
        assert staged.size == (800, 600)

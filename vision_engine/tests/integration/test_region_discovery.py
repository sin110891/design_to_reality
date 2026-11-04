from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from vision_engine.concept_board.application.region_discovery import (
    _validate_detected_regions,
    confirm_proposed_regions,
    detect_regions_for_concept_version,
)
from vision_engine.concept_board.domain.enums import DesignRegionLifecycle
from vision_engine.region_detection.models import DetectedRegionProposal, RegionDetectionResult
from vision_engine.region_detection.templates import normalise_room_type, template_regions
from vision_engine.settings import AppSettings, clear_settings_cache


ROOT = Path(__file__).resolve().parents[2]


def _settings(tmp_path: Path) -> AppSettings:
    clear_settings_cache()
    for name in ("configs", "src"):
        src = ROOT / name
        dest = tmp_path / name
        if src.exists() and not dest.exists():
            shutil.copytree(src, dest)

    settings = AppSettings(
        model_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "configs" / "rulebook.v1.yaml",
        app_config_path=tmp_path / "configs" / "app.local.yaml",
        prompts_config_path=tmp_path / "configs" / "prompts.v1.yaml",
        project_root=tmp_path,
    )
    settings.region_detection.provider = "fake"
    settings.paths.concept_boards = tmp_path / "concept_boards"
    settings.paths.staging = tmp_path / "staging"
    return settings


def test_normalise_room_type_aliases():
    assert normalise_room_type("master bedroom") == "bedroom"
    assert normalise_room_type("living room") == "living_room"


def test_bedroom_template_includes_wardrobe_and_bed():
    types = {item["region_type"] for item in template_regions("bedroom")}
    assert "bed" in types
    assert "fitted_wardrobe" in types


def test_invalid_detected_region_is_skipped_without_removing_valid_regions():
    detection = RegionDetectionResult(
        provider="gemini",
        model_name="test",
        room_type="bedroom",
        inferred_room_type=None,
        concept_version_id="cv_test",
        image_uri="room.png",
        regions=[
            DetectedRegionProposal(
                region_code="bed_01",
                region_type="bed",
                display_name="Bed",
                geometry_json={"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3},
                confidence=0.9,
            ),
            DetectedRegionProposal(
                region_code="invalid_01",
                region_type="wardrobe",
                display_name="Invalid wardrobe",
                geometry_json={"x": 1.2, "y": 0.2, "width": 0.2, "height": 0.3},
                confidence=0.8,
            ),
        ],
    )

    skipped = _validate_detected_regions(detection)

    assert [region.region_code for region in detection.regions] == ["bed_01"]
    assert skipped == [
        {
            "region_code": "invalid_01",
            "reason": "Bounding box does not overlap the image frame",
        }
    ]


def test_detect_regions_creates_proposed_regions(tmp_path: Path):
    from PIL import Image

    from vision_engine.concept_board.domain.enums import (
        ConceptAssetType,
        ConceptBoardStatus,
        ConceptDirectionStatus,
        ConceptVersionStatus,
    )
    from vision_engine.concept_board.domain.models import (
        ConceptAssetRecord,
        ConceptBoardRecord,
        ConceptDirectionRecord,
        ConceptVersionRecord,
    )
    from vision_engine.domain.enums import ProjectStatus
    from vision_engine.domain.models import ProjectRecord
    from vision_engine.infrastructure.file_store import sha256_file
    from vision_engine.infrastructure.sqlite_repository import SqliteRepository, utcnow

    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()

    board_dir = settings.paths.concept_boards / "cb_test" / "versions" / "cv_test"
    board_dir.mkdir(parents=True)
    concept_path = board_dir / "primary.png"
    Image.new("RGB", (800, 600), (230, 230, 230)).save(concept_path)
    now = utcnow()

    repo.save_project(
        ProjectRecord(
            project_id="proj_test",
            room_image_path=str(concept_path),
            inspiration_paths=[],
            room_type="bedroom",
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
            rights_status="user_owned",
            created_at=now,
        )
    )

    detection, created, overlay = detect_regions_for_concept_version(
        repo=repo,
        settings=settings,
        project_id="proj_test",
        concept_version_id="cv_test",
    )

    assert detection.provider == "fake"
    assert detection.room_type == "bedroom"
    assert len(detection.regions) >= 4
    assert created
    assert overlay is not None and overlay.exists()

    regions = repo.list_design_regions("cd_test")
    assert all(region.lifecycle_status == DesignRegionLifecycle.PROPOSED for region in regions)

    confirmed = confirm_proposed_regions(
        repo=repo,
        concept_direction_id="cd_test",
        concept_version_id="cv_test",
    )
    assert len(confirmed) == len(regions)
    geometry = repo.get_region_geometry_for_version(confirmed[0].design_region_id, "cv_test")
    assert geometry is not None
    assert geometry.source.startswith("vision:")
    assert geometry.confidence is not None

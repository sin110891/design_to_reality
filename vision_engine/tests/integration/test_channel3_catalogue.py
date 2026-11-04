from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from vision_engine.concept_board.application.channel3_catalogue import (
    import_channel3_snapshot_for_region,
    refresh_channel3_product_offer,
)
from vision_engine.concept_board.application.product_retrieval import retrieve_product_candidates
from vision_engine.concept_board.application.regions import (
    add_region_geometry,
    confirm_design_region,
    create_design_region,
)
from vision_engine.concept_board.domain.enums import (
    CandidateSource,
    CatalogueSnapshotStatus,
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
from vision_engine.infrastructure.file_store import sha256_file
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, utcnow
from vision_engine.settings import AppSettings, clear_settings_cache

SAMPLE_PRODUCT = {
    "id": "prod_abc123",
    "title": "Modern Grey Sofa",
    "description": "Three-seater fabric sofa",
    "categories": [{"slug": "sofas", "title": "Sofas"}],
    "brands": [{"name": "Acme Home"}],
    "materials": ["fabric"],
    "structured_attributes": {"color": "grey"},
    "images": [
        {"url": "https://cdn.example.com/raw.jpg", "is_cleaned_image": False},
        {"url": "https://cdn.example.com/clean.jpg", "is_cleaned_image": True},
    ],
    "offers": [
        {
            "availability": "InStock",
            "domain": "example-retailer.co.uk",
            "url": "https://example-retailer.co.uk/sofa",
            "price": {"price": 1299.0, "currency": "GBP"},
            "dimensions": {
                "width": {"number": 210, "unit": "cm"},
                "height": {"number": 85, "unit": "cm"},
                "length": {"number": 95, "unit": "cm"},
            },
        }
    ],
}


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
        model_name="fake-concept-v1",
        image_edit_model="fake-image-edit-v1",
        embedding_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "configs" / "rulebook.v1.yaml",
        app_config_path=tmp_path / "configs" / "app.local.yaml",
        prompts_config_path=tmp_path / "configs" / "prompts.v1.yaml",
        project_root=tmp_path,
        channel3_api_key="test-key",
        catalogue_provider="channel3",
    )
    settings.paths.concept_boards = tmp_path / "concept_boards"
    settings.paths.catalogue = tmp_path / "data" / "catalogue"
    return settings


def _mock_client():
    from unittest.mock import MagicMock

    from vision_engine.catalog_providers.channel3.client import Channel3Client

    client = MagicMock(spec=Channel3Client)
    client.search_products.return_value = {"products": [SAMPLE_PRODUCT]}
    client.get_product.return_value = SAMPLE_PRODUCT
    return client


def _seed_board(repo: SqliteRepository, settings: AppSettings, tmp_path: Path) -> tuple[str, str]:
    from PIL import Image

    board_dir = settings.paths.concept_boards / "cd_test" / "versions" / "cv_test"
    board_dir.mkdir(parents=True)
    concept_path = board_dir / "primary.png"
    Image.new("RGB", (800, 600), (220, 220, 220)).save(concept_path)

    now = utcnow()
    repo.save_project(
        ProjectRecord(
            project_id="proj_test",
            room_image_path=str(concept_path),
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
            rights_status="user_owned",
            created_at=now,
        )
    )
    return "cd_test", "cv_test"


def test_import_channel3_snapshot_seals_products(tmp_path: Path):
    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()

    snapshot, rows = import_channel3_snapshot_for_region(
        repo=repo,
        settings=settings,
        design_region_id="dr_test",
        region_type="sofa",
        display_name="Main Sofa",
        max_budget=3000,
        client=_mock_client(),
    )

    assert snapshot.status == CatalogueSnapshotStatus.SEALED
    assert snapshot.manifest_uri == "channel3://search/dr_test"
    assert len(rows) == 1
    assert rows[0].external_provider == "channel3"


def test_retrieve_with_channel3_uses_live_snapshot(tmp_path: Path):
    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    _seed_board(repo, settings, tmp_path)

    region = create_design_region(
        repo=repo,
        concept_direction_id="cd_test",
        region_code="sofa_01",
        region_type="sofa",
        display_name="Main Sofa",
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

    with patch(
        "vision_engine.concept_board.application.channel3_catalogue.build_channel3_client",
        return_value=_mock_client(),
    ):
        run, candidates = retrieve_product_candidates(
            repo=repo,
            settings=settings,
            design_region_id=region.design_region_id,
            concept_version_id="cv_test",
            use_channel3=True,
            top_k=3,
        )

    assert candidates
    assert candidates[0].candidate_source == CandidateSource.CHANNEL3_SEARCH
    assert candidates[0].match_rationale_json["external_provider"] == "channel3"
    assert run.catalogue_snapshot_id


def test_refresh_channel3_product_offer_updates_price(tmp_path: Path):
    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()

    snapshot, _rows = import_channel3_snapshot_for_region(
        repo=repo,
        settings=settings,
        design_region_id="dr_refresh",
        region_type="sofa",
        client=_mock_client(),
    )
    variant_id = repo.list_snapshot_product_variants(snapshot.catalogue_snapshot_id)[0][1].product_variant_id

    updated_product = dict(SAMPLE_PRODUCT)
    updated_product["offers"] = [
        {
            **SAMPLE_PRODUCT["offers"][0],
            "price": {"price": 999.0, "currency": "GBP"},
        }
    ]
    client = _mock_client()
    client.get_product.return_value = updated_product

    _product, _variant, offer = refresh_channel3_product_offer(
        repo=repo,
        settings=settings,
        product_variant_id=variant_id,
        client=client,
    )

    assert offer.unit_price == 999.0
    assert offer.external_provider == "channel3"

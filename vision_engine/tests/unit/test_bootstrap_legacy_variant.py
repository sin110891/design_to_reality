from __future__ import annotations

from pathlib import Path

from PIL import Image

from vision_engine.concept_board.application.bootstrap import bootstrap_concept_board_from_variant
from vision_engine.domain.enums import GenerationMode, ProjectStatus, VariantKind, VariantReviewStatus
from vision_engine.domain.models import GeneratedVariant, GenerationRunRecord, ProjectRecord
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, utcnow
from vision_engine.settings import AppSettings, clear_settings_cache


def test_bootstrap_falls_back_to_variant_image_path(tmp_path: Path):
    clear_settings_cache()
    settings = AppSettings(
        model_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "rulebook.yaml",
        app_config_path=tmp_path / "app.yaml",
        prompts_config_path=tmp_path / "prompts.yaml",
        project_root=tmp_path,
    )
    settings.paths.generated = tmp_path / "generated"
    settings.paths.concept_boards = tmp_path / "concept_boards"

    image_path = settings.paths.generated / "proj_test" / "variant_b_attempt2.png"
    image_path.parent.mkdir(parents=True)
    Image.new("RGB", (640, 480), (200, 200, 200)).save(image_path)

    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    now = utcnow()
    repo.save_project(
        ProjectRecord(
            project_id="proj_test",
            room_image_path=str(image_path),
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
    repo.save_generation_run(
        GenerationRunRecord(
            run_id="gen_test",
            project_id="proj_test",
            concept_run_id=None,
            mode=GenerationMode.CURATED,
            prompt_version="test",
            provider="fake",
            model_name="fake",
            status="completed",
            created_at=now,
        )
    )
    repo.save_variant(
        GeneratedVariant(
            variant_id="var_test",
            generation_run_id="gen_test",
            project_id="proj_test",
            mode=GenerationMode.CURATED,
            kind=VariantKind.CONSERVATIVE,
            image_path=str(image_path.relative_to(settings.project_root)),
            rank_hint=2,
            review_status=VariantReviewStatus.UNREVIEWED,
            created_at=now,
        )
    )

    board, direction, version = bootstrap_concept_board_from_variant(
        repo=repo,
        settings=settings,
        project_id="proj_test",
        variant_id="var_test",
    )

    assert board.concept_board_id.startswith("cb_")
    assert direction.concept_direction_id.startswith("cd_")
    assert version.concept_version_id.startswith("cv_")
    asset = repo.get_primary_concept_asset(version.concept_version_id)
    assert asset is not None
    assert asset.width == 640
    assert asset.height == 480

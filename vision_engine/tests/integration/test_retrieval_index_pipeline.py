from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from sqlalchemy import select

from vision_engine.application.build_retrieval_index import build_versioned_retrieval_index
from vision_engine.application.retrieve_references import retrieve_references_versioned
from vision_engine.application.versioned_index_build import load_active_versioned_index
from vision_engine.domain.models import ProjectRecord
from vision_engine.infrastructure.embedding_clients.joint import build_joint_embedding_client
from vision_engine.infrastructure.retrieval_schema import (
    RetrievalCandidateRow,
    RetrievalCandidateScoreRow,
    RetrievalQueryArtifactRow,
)
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
        embedding_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "configs" / "rulebook.v1.yaml",
        app_config_path=tmp_path / "configs" / "app.local.yaml",
        prompts_config_path=tmp_path / "configs" / "prompts.v1.yaml",
        project_root=tmp_path,
        app_env="local",
    )
    settings.paths.uploads = tmp_path / "uploads"
    settings.paths.generated = tmp_path / "generated"
    settings.paths.exports = tmp_path / "exports"
    settings.paths.index_path = tmp_path / "indexes" / "curated.npz"
    settings.paths.curated_images = SOURCE_IMAGES
    return settings


@pytest.mark.skipif(not GOLD.exists(), reason="dataset_factory gold export missing")
def test_versioned_index_build_retrieve_provenance(tmp_path: Path):
    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()

    index, count = build_versioned_retrieval_index(
        repo=repo,
        settings=settings,
        gold_jsonl=GOLD,
        images_dir=SOURCE_IMAGES,
        snapshot_name="test-snapshot",
        promote=True,
    )
    assert count >= 1
    assert index.status.value in {"validated", "active"}

    versioned = load_active_versioned_index(repo=repo, settings=settings)
    assert versioned is not None
    assert len(versioned.references) == count

    room = sorted(SOURCE_IMAGES.glob("*.jpg"))[0]
    project = ProjectRecord(
        project_id="proj_test",
        room_image_path=str(room),
        room_type="living_room",
        style_family="Contemporary Europe",
        brief="warm contemporary European living room refresh",
        created_at=index.created_at,
        updated_at=index.created_at,
    )
    repo.save_project(project)

    embedder = build_joint_embedding_client(provider="fake")
    refs, run = retrieve_references_versioned(
        repo=repo,
        settings=settings,
        embedder=embedder,
        versioned_store=versioned,
        project=project,
    )
    assert len(refs) == min(3, count)
    assert run.dataset_version == index.vector_index_version_id

    with repo.session() as session:
        candidates = session.scalars(
            select(RetrievalCandidateRow).where(
                RetrievalCandidateRow.retrieval_run_id == run.run_id
            )
        ).all()
        scores = session.scalars(
            select(RetrievalCandidateScoreRow).where(
                RetrievalCandidateScoreRow.retrieval_candidate_id.in_(
                    [c.retrieval_candidate_id for c in candidates]
                )
            )
        ).all()
        artifacts = session.scalars(
            select(RetrievalQueryArtifactRow).where(
                RetrievalQueryArtifactRow.retrieval_run_id == run.run_id
            )
        ).all()
    assert len(candidates) >= min(3, count)
    assert len(scores) >= len(candidates)
    assert len(artifacts) == 2

from __future__ import annotations

from pathlib import Path

from vision_engine.application.build_index import _resolve_record_image, load_curated_records
from vision_engine.application.dataset_snapshots import create_sealed_snapshot_from_records
from vision_engine.infrastructure.sqlite_repository import new_id
from vision_engine.application.embedding_build import run_embedding_build_job
from vision_engine.application.index_promotion import promote_index_version
from vision_engine.application.retrieval_experiments import (
    ensure_default_reranker_model,
    ensure_default_retrieval_experiment,
)
from vision_engine.application.versioned_index_build import build_vector_index_version
from vision_engine.domain.retrieval_models import VectorIndexVersion
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


def build_versioned_retrieval_index(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    metadata: Path | None = None,
    gold_jsonl: Path | None = None,
    images_dir: Path | None = None,
    snapshot_name: str = "curated-v1",
    promote: bool = True,
) -> tuple[VectorIndexVersion, int]:
    """
    Full ERD pipeline:
    records → sealed snapshot → embeddings → versioned index → optional promotion.
    """
    records = load_curated_records(
        settings=settings,
        metadata=metadata,
        gold_jsonl=gold_jsonl,
        images_dir=images_dir,
        approved_only=True,
    )
    if not records:
        raise FileNotFoundError("No approved curated records with resolvable images.")

    repo.upsert_dataset_records(records)
    snapshot = create_sealed_snapshot_from_records(
        repo=repo,
        settings=settings,
        records=records,
        snapshot_name=f"{snapshot_name}-{new_id('snap')[-8:]}",
        resolve_image_path=lambda r: _resolve_record_image(settings, r),
    )
    job = run_embedding_build_job(
        repo=repo,
        settings=settings,
        dataset_snapshot_id=snapshot.dataset_snapshot_id,
        provider=settings.embedding_provider,
    )
    index = build_vector_index_version(
        repo=repo,
        settings=settings,
        dataset_snapshot_id=snapshot.dataset_snapshot_id,
        embedding_job_id=job.embedding_job_id,
    )
    ensure_default_retrieval_experiment(repo)
    ensure_default_reranker_model(repo)
    if promote:
        promote_index_version(
            repo=repo,
            vector_index_version_id=index.vector_index_version_id,
            environment=settings.app_env,
        )
    return index, snapshot.record_count

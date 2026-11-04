from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from vision_engine.domain.enums import EmbeddingJobStatus, EmbeddingModality
from vision_engine.domain.retrieval_models import (
    EmbeddingBuildJob,
    EmbeddingModelVersion,
    EmbeddingSpace,
    ReferenceEmbedding,
)
from vision_engine.domain.retrieval_validation import assert_production_eligible_asset
from vision_engine.infrastructure.content_hash import sha256_file
from vision_engine.infrastructure.embedding_clients.joint import (
    JointEmbeddingClient,
    build_joint_embedding_client,
)
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_embedding_model_and_space(
    *,
    repo: SqliteRepository,
    provider: str,
    model_name: str | None = None,
) -> tuple[EmbeddingModelVersion, EmbeddingSpace, JointEmbeddingClient | object]:
    client = build_joint_embedding_client(provider=provider, model_name=model_name)
    contract = client.contract
    existing_space = repo.get_embedding_space_by_fingerprint(contract.space_fingerprint)
    if existing_space:
        model = repo.get_embedding_model(existing_space.embedding_model_version_id)
        assert model is not None
        return model, existing_space, client

    now = utcnow()
    model = EmbeddingModelVersion(
        embedding_model_version_id=new_id("emodel"),
        provider=contract.provider,
        model_name=contract.model_name,
        model_revision=contract.model_revision,
        supported_modalities_json=json.dumps(["image", "text"]),
        preprocessing_config_json=json.dumps(contract.preprocessing_config),
        model_card_uri=None,
        created_at=now,
    )
    space = EmbeddingSpace(
        embedding_space_id=new_id("espace"),
        embedding_model_version_id=model.embedding_model_version_id,
        modality_contract=contract.modality_contract,
        dimension=contract.dimension,
        distance_metric=contract.distance_metric,
        normalisation=contract.normalisation,
        space_fingerprint=contract.space_fingerprint,
        created_at=now,
    )
    repo.save_embedding_model(model)
    repo.save_embedding_space(space)
    return model, space, client


def run_embedding_build_job(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    dataset_snapshot_id: str,
    provider: str,
) -> EmbeddingBuildJob:
    snapshot = repo.get_dataset_snapshot(dataset_snapshot_id)
    if snapshot is None:
        raise ValueError(f"Snapshot not found: {dataset_snapshot_id}")

    _, space, client = ensure_embedding_model_and_space(
        repo=repo,
        provider=provider,
        model_name=getattr(settings, "embedding_model_name", None),
    )
    snap_records = repo.list_snapshot_reference_records(dataset_snapshot_id)
    manifest_sha = snapshot.manifest_sha256
    now = utcnow()
    job = EmbeddingBuildJob(
        embedding_job_id=new_id("ejob"),
        embedding_space_id=space.embedding_space_id,
        dataset_snapshot_id=dataset_snapshot_id,
        status=EmbeddingJobStatus.RUNNING,
        input_manifest_sha256=manifest_sha,
        started_at=now,
    )
    repo.save_embedding_job(job)

    vectors_dir = settings.resolve(Path("data/embeddings")) / job.embedding_job_id
    vectors_dir.mkdir(parents=True, exist_ok=True)

    try:
        for snap_ref in snap_records:
            record = snap_ref.record
            if record is None:
                continue
            asset = repo.get_reference_asset_by_image(record.image_id)
            if asset is None:
                raise ValueError(f"Missing asset for {record.image_id}")
            assert_production_eligible_asset(asset)
            image_path = Path(asset.storage_uri)
            image_vec = client.embed_image(image_path)
            text_vec = client.embed_text(record.text_blob or record.image_id)
            client.assert_compatible(image_vec)
            client.assert_compatible(text_vec)

            for modality, vector, source_sha in (
                (EmbeddingModality.IMAGE, image_vec, asset.image_sha256),
                (EmbeddingModality.TEXT, text_vec, asset.image_sha256),
            ):
                vector_path = vectors_dir / f"{snap_ref.snapshot_reference_record_id}_{modality.value}.npy"
                np.save(vector_path, np.asarray(vector, dtype=np.float32))
                embedding = ReferenceEmbedding(
                    reference_embedding_id=new_id("remb"),
                    reference_asset_id=asset.reference_asset_id,
                    annotation_revision_id=snap_ref.annotation_revision_id,
                    embedding_space_id=space.embedding_space_id,
                    embedding_job_id=job.embedding_job_id,
                    modality=modality,
                    vector_uri=str(vector_path),
                    vector_sha256=sha256_file(vector_path),
                    source_content_sha256=source_sha,
                    created_at=utcnow(),
                )
                repo.save_reference_embedding(embedding)

        job.status = EmbeddingJobStatus.COMPLETED
        job.completed_at = utcnow()
        repo.save_embedding_job(job)
        return job
    except Exception as exc:  # noqa: BLE001
        job.status = EmbeddingJobStatus.FAILED
        job.error_summary = str(exc)
        job.completed_at = utcnow()
        repo.save_embedding_job(job)
        raise

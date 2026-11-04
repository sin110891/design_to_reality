from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from vision_engine.domain.enums import EmbeddingModality, VectorIndexStatus
from vision_engine.domain.retrieval_models import VectorIndexMembership, VectorIndexVersion
from vision_engine.domain.retrieval_validation import assert_sealed_snapshot
from vision_engine.infrastructure.content_hash import sha256_file, sha256_json
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id
from vision_engine.infrastructure.versioned_vector_store import VersionedVectorStore
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_vector_index_version(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    dataset_snapshot_id: str,
    embedding_job_id: str,
) -> VectorIndexVersion:
    snapshot = repo.get_dataset_snapshot(dataset_snapshot_id)
    if snapshot is None:
        raise ValueError(f"Snapshot not found: {dataset_snapshot_id}")
    assert_sealed_snapshot(snapshot.status)

    embeddings = repo.list_reference_embeddings_for_job(embedding_job_id)
    if not embeddings:
        raise ValueError(f"No embeddings produced for job {embedding_job_id}")

    snap_records = repo.list_snapshot_reference_records(dataset_snapshot_id)
    snap_by_id = {r.snapshot_reference_record_id: r for r in snap_records}
    image_embeddings: dict[str, list[float]] = {}
    text_embeddings: dict[str, list[float]] = {}
    memberships: list[tuple[str, str, str]] = []

    grouped: dict[str, dict[str, str]] = {}
    for emb in embeddings:
        grouped.setdefault(emb.reference_asset_id, {})[emb.modality.value] = emb.vector_uri

    for snap_ref in snap_records:
        asset_id = snap_ref.reference_asset_id
        image_uri = grouped.get(asset_id, {}).get(EmbeddingModality.IMAGE.value)
        text_uri = grouped.get(asset_id, {}).get(EmbeddingModality.TEXT.value)
        if not image_uri or not text_uri:
            continue
        image_vec = np.load(image_uri).tolist()
        text_vec = np.load(text_uri).tolist()
        image_embeddings[snap_ref.image_id] = image_vec
        text_embeddings[snap_ref.image_id] = text_vec
        image_emb_id = next(
            e.reference_embedding_id
            for e in embeddings
            if e.reference_asset_id == asset_id and e.modality == EmbeddingModality.IMAGE
        )
        memberships.append(
            (snap_ref.snapshot_reference_record_id, image_emb_id, snap_ref.image_id)
        )

    if not memberships:
        raise ValueError("No complete image/text embedding pairs for index build")

    space_id = embeddings[0].embedding_space_id
    index_id = new_id("vidx")
    index_dir = settings.resolve(Path("data/indexes/versions")) / index_id
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "index.npz"

    index_version = VectorIndexVersion(
        vector_index_version_id=index_id,
        dataset_snapshot_id=dataset_snapshot_id,
        embedding_space_id=space_id,
        index_backend="numpy",
        index_config_json=json.dumps({"candidate_k": 30, "final_k": 3, "fusion": "rrf"}),
        index_uri=str(index_path),
        index_manifest_sha256="pending",
        vector_count=len(memberships),
        status=VectorIndexStatus.BUILDING,
        created_at=utcnow(),
    )
    from vision_engine.infrastructure.vector_store import NumpyVectorStore

    versioned = VersionedVectorStore(
        index_version=index_version,
        store=NumpyVectorStore(),
    )
    versioned.build(
        snapshot_records=snap_records,
        image_embeddings=image_embeddings,
        text_embeddings=text_embeddings,
        memberships=memberships,
    )
    versioned.save(index_path)

    manifest_sha = sha256_file(index_path.with_suffix(".manifest.json"))
    index_version.index_manifest_sha256 = manifest_sha
    index_version.status = VectorIndexStatus.VALIDATED
    index_version.validated_at = utcnow()
    repo.save_vector_index_version(index_version)

    now = utcnow()
    for snap_id, emb_id, image_id in memberships:
        repo.save_index_membership(
            VectorIndexMembership(
                index_membership_id=new_id("mem"),
                vector_index_version_id=index_id,
                snapshot_reference_record_id=snap_id,
                reference_embedding_id=emb_id,
                vector_key=image_id,
                added_at=now,
            )
        )

    return index_version


def load_active_versioned_index(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
) -> VersionedVectorStore | None:
    index_version = repo.get_active_index_for_environment(settings.app_env)
    if index_version is None:
        return None
    snap_records = repo.list_snapshot_reference_records(index_version.dataset_snapshot_id)
    index_path = Path(index_version.index_uri)
    if not index_path.is_absolute():
        index_path = settings.resolve(index_path)
    return VersionedVectorStore.load(
        index_version=index_version,
        index_path=index_path,
        snapshot_records=snap_records,
    )

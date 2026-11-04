from __future__ import annotations

from vision_engine.domain.errors import EmbeddingSpaceError, IndexBuildError, SnapshotError
from vision_engine.domain.enums import DatasetSnapshotStatus, RightsStatus, VectorIndexStatus
from vision_engine.domain.retrieval_models import (
    EmbeddingSpace,
    ReferenceEmbedding,
    ReferenceImageAsset,
    VectorIndexVersion,
)


def assert_sealed_snapshot(status: DatasetSnapshotStatus) -> None:
    if status != DatasetSnapshotStatus.SEALED:
        raise SnapshotError(
            f"Only sealed snapshots may build production indexes (got {status.value})"
        )


def assert_embedding_space_compatible(
    *,
    space: EmbeddingSpace,
    vector: list[float],
    expected_space_id: str | None = None,
) -> None:
    if expected_space_id and space.embedding_space_id != expected_space_id:
        raise EmbeddingSpaceError(
            f"Vector belongs to space {space.embedding_space_id}, expected {expected_space_id}"
        )
    if len(vector) != space.dimension:
        raise EmbeddingSpaceError(
            f"Vector dimension {len(vector)} != space dimension {space.dimension}"
        )


def assert_reference_embedding_integrity(
    *,
    embedding: ReferenceEmbedding,
    space: EmbeddingSpace,
    source_sha256: str,
) -> None:
    if embedding.embedding_space_id != space.embedding_space_id:
        raise EmbeddingSpaceError("Reference embedding space mismatch")
    if embedding.source_content_sha256 != source_sha256:
        raise IndexBuildError("Reference embedding source content hash mismatch")


def assert_production_eligible_asset(asset: ReferenceImageAsset) -> None:
    if asset.deleted_at is not None:
        raise IndexBuildError(f"Reference asset {asset.reference_asset_id} is deleted")
    if asset.rights_status == RightsStatus.RESTRICTED:
        raise IndexBuildError(f"Reference asset {asset.reference_asset_id} is restricted")


def assert_index_promotable(index: VectorIndexVersion) -> None:
    if index.status not in {VectorIndexStatus.VALIDATED, VectorIndexStatus.ACTIVE}:
        raise IndexBuildError(
            f"Index {index.vector_index_version_id} is not validated (status={index.status.value})"
        )

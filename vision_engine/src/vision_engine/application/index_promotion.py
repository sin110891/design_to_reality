from __future__ import annotations

from datetime import datetime, timezone

from vision_engine.domain.enums import VectorIndexStatus
from vision_engine.domain.retrieval_models import ActiveIndexAlias
from vision_engine.domain.retrieval_validation import assert_index_promotable
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def promote_index_version(
    *,
    repo: SqliteRepository,
    vector_index_version_id: str,
    environment: str = "local",
) -> ActiveIndexAlias:
    index = repo.get_vector_index_version(vector_index_version_id)
    if index is None:
        raise ValueError(f"Index version not found: {vector_index_version_id}")
    assert_index_promotable(index)

    if index.status != VectorIndexStatus.ACTIVE:
        index.status = VectorIndexStatus.ACTIVE
        index.promoted_at = utcnow()
        repo.save_vector_index_version(index)

    alias = ActiveIndexAlias(
        active_index_alias=new_id("alias"),
        vector_index_version_id=vector_index_version_id,
        environment=environment,
        activated_at=utcnow(),
    )
    repo.set_active_index_alias(alias)
    return alias

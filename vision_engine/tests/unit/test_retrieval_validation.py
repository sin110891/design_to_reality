from __future__ import annotations

import pytest

from vision_engine.domain.enums import DatasetSnapshotStatus, VectorIndexStatus
from vision_engine.domain.errors import EmbeddingSpaceError, SnapshotError
from vision_engine.domain.retrieval_models import EmbeddingSpace, ReferenceImageAsset, VectorIndexVersion
from vision_engine.domain.retrieval_validation import (
    assert_embedding_space_compatible,
    assert_index_promotable,
    assert_production_eligible_asset,
    assert_sealed_snapshot,
)
from vision_engine.domain.enums import RetentionConsentStatus, RightsStatus
from datetime import datetime, timezone


def _space(dim: int = 128) -> EmbeddingSpace:
    return EmbeddingSpace(
        embedding_space_id="espace_test",
        embedding_model_version_id="emodel_test",
        modality_contract="joint_image_text_v1",
        dimension=dim,
        distance_metric="cosine",
        normalisation="l2",
        space_fingerprint="test",
        created_at=datetime.now(timezone.utc),
    )


def test_assert_sealed_snapshot_rejects_draft():
    with pytest.raises(SnapshotError):
        assert_sealed_snapshot(DatasetSnapshotStatus.DRAFT)


def test_embedding_space_rejects_wrong_dimension():
    with pytest.raises(EmbeddingSpaceError):
        assert_embedding_space_compatible(space=_space(128), vector=[0.1] * 64)


def test_restricted_asset_not_production_eligible():
    asset = ReferenceImageAsset(
        reference_asset_id="rasset_test",
        image_id="img_test",
        image_sha256="abc",
        storage_uri="/tmp/x.jpg",
        mime_type="image/jpeg",
        rights_status=RightsStatus.RESTRICTED,
        retention_consent_status=RetentionConsentStatus.INTERNAL_REVIEW_ONLY,
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises(Exception):
        assert_production_eligible_asset(asset)


def test_index_promotion_requires_validated_status():
    index = VectorIndexVersion(
        vector_index_version_id="vidx_test",
        dataset_snapshot_id="snap_test",
        embedding_space_id="espace_test",
        index_backend="numpy",
        index_config_json="{}",
        index_uri="/tmp/index.npz",
        index_manifest_sha256="deadbeef",
        vector_count=1,
        status=VectorIndexStatus.BUILDING,
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises(Exception):
        assert_index_promotable(index)

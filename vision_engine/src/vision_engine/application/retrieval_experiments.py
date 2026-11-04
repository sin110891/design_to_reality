from __future__ import annotations

import json
from datetime import datetime, timezone

from vision_engine.domain.enums import RetrievalExperimentStatus, RerankerModelStatus
from vision_engine.domain.retrieval_models import RetrievalExperiment, RerankerModelVersion
from vision_engine.infrastructure.content_hash import sha256_json
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id
from vision_engine.settings import AppSettings


DEFAULT_RETRIEVAL_CONFIG = {
    "candidate_k": 30,
    "rerank_k": 12,
    "final_k": 3,
    "fusion": "reciprocal_rank_fusion",
    "hard_filters": ["review_status", "rights_status", "room_type"],
    "diversity": {"algorithm": "mmr", "lambda": 0.7},
    "reranker": "deterministic-multimodal.v1",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_default_retrieval_experiment(repo: SqliteRepository) -> RetrievalExperiment:
    existing = repo.get_active_retrieval_experiment()
    if existing:
        return existing
    config_json = json.dumps(DEFAULT_RETRIEVAL_CONFIG)
    experiment = RetrievalExperiment(
        retrieval_experiment_id=new_id("rexp"),
        name="default-curated-retrieval-v1",
        config_json=config_json,
        config_sha256=sha256_json(DEFAULT_RETRIEVAL_CONFIG),
        status=RetrievalExperimentStatus.ACTIVE,
        created_at=utcnow(),
    )
    repo.save_retrieval_experiment(experiment)
    return experiment


def ensure_default_reranker_model(repo: SqliteRepository) -> RerankerModelVersion:
    existing = repo.get_active_reranker_model()
    if existing:
        return existing
    model = RerankerModelVersion(
        reranker_model_version_id=new_id("rmod"),
        provider="local",
        model_name="deterministic-multimodal",
        model_revision="v1",
        input_contract="room_image+brief+reference_image+annotations",
        training_dataset_snapshot_id=None,
        status=RerankerModelStatus.ACTIVE,
        created_at=utcnow(),
    )
    repo.save_reranker_model(model)
    return model

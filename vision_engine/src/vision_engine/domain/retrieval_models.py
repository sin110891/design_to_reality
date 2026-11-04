from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from vision_engine.domain.enums import (
    AnnotationRevisionStatus,
    DatasetSnapshotStatus,
    EmbeddingJobStatus,
    EmbeddingModality,
    GenerationMode,
    RetrievalEvaluationRunStatus,
    RetrievalEvaluationSetStatus,
    RetrievalExperimentStatus,
    RetrievalScoreStage,
    RerankerModelStatus,
    RetentionConsentStatus,
    RightsStatus,
    VectorIndexStatus,
)
from vision_engine.domain.models import DatasetRecord


class ReferenceImageAsset(BaseModel):
    reference_asset_id: str
    image_id: str
    image_sha256: str
    storage_uri: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    file_size_bytes: int | None = None
    rights_status: RightsStatus
    retention_consent_status: RetentionConsentStatus
    created_at: datetime
    deleted_at: datetime | None = None


class ReferenceAnnotationRevision(BaseModel):
    annotation_revision_id: str
    image_id: str
    revision_number: int
    annotation_json: str
    annotation_sha256: str
    reviewer: str
    status: AnnotationRevisionStatus
    created_at: datetime


class CuratedDatasetSnapshot(BaseModel):
    dataset_snapshot_id: str
    snapshot_name: str
    manifest_uri: str
    manifest_sha256: str
    record_count: int
    status: DatasetSnapshotStatus
    created_at: datetime
    sealed_at: datetime | None = None


class SnapshotReferenceRecord(BaseModel):
    snapshot_reference_record_id: str
    dataset_snapshot_id: str
    image_id: str
    reference_asset_id: str
    annotation_revision_id: str
    record_sha256: str
    record: DatasetRecord | None = None


class EmbeddingModelVersion(BaseModel):
    embedding_model_version_id: str
    provider: str
    model_name: str
    model_revision: str
    supported_modalities_json: str
    preprocessing_config_json: str
    model_card_uri: str | None = None
    created_at: datetime


class EmbeddingSpace(BaseModel):
    embedding_space_id: str
    embedding_model_version_id: str
    modality_contract: str
    dimension: int
    distance_metric: str
    normalisation: str
    space_fingerprint: str
    created_at: datetime


class EmbeddingBuildJob(BaseModel):
    embedding_job_id: str
    embedding_space_id: str
    dataset_snapshot_id: str
    status: EmbeddingJobStatus
    input_manifest_sha256: str
    error_summary: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ReferenceEmbedding(BaseModel):
    reference_embedding_id: str
    reference_asset_id: str
    annotation_revision_id: str
    embedding_space_id: str
    embedding_job_id: str
    modality: EmbeddingModality
    vector_uri: str
    vector_sha256: str
    source_content_sha256: str
    created_at: datetime


class VectorIndexVersion(BaseModel):
    vector_index_version_id: str
    dataset_snapshot_id: str
    embedding_space_id: str
    index_backend: str
    index_config_json: str
    index_uri: str
    index_manifest_sha256: str
    vector_count: int
    status: VectorIndexStatus
    created_at: datetime
    validated_at: datetime | None = None
    promoted_at: datetime | None = None


class VectorIndexMembership(BaseModel):
    index_membership_id: str
    vector_index_version_id: str
    snapshot_reference_record_id: str
    reference_embedding_id: str
    vector_key: str
    added_at: datetime


class ActiveIndexAlias(BaseModel):
    active_index_alias: str
    vector_index_version_id: str
    environment: str
    activated_at: datetime
    deactivated_at: datetime | None = None


class RetrievalExperiment(BaseModel):
    retrieval_experiment_id: str
    name: str
    config_json: str
    config_sha256: str
    status: RetrievalExperimentStatus
    created_at: datetime


class RetrievalQueryArtifact(BaseModel):
    retrieval_query_artifact_id: str
    retrieval_run_id: str
    upload_id: str | None = None
    embedding_space_id: str
    modality: EmbeddingModality
    query_sha256: str
    vector_uri: str | None = None
    created_at: datetime


class RetrievalCandidate(BaseModel):
    retrieval_candidate_id: str
    retrieval_run_id: str
    snapshot_reference_record_id: str
    image_id: str
    initial_rank: int | None = None
    passed_hard_filters: bool
    filter_reason: str | None = None
    selected_for_rerank: bool = False
    selected_final: bool = False
    created_at: datetime


class RerankerModelVersion(BaseModel):
    reranker_model_version_id: str
    provider: str
    model_name: str
    model_revision: str
    input_contract: str
    training_dataset_snapshot_id: str | None = None
    status: RerankerModelStatus
    created_at: datetime


class RetrievalCandidateScore(BaseModel):
    retrieval_candidate_score_id: str
    retrieval_candidate_id: str
    reranker_model_version_id: str | None = None
    stage: RetrievalScoreStage
    score_name: str
    raw_score: float
    normalised_score: float
    rank_after_stage: int | None = None
    explanation_json: str | None = None
    created_at: datetime


class RetrievalEvaluationSet(BaseModel):
    retrieval_evaluation_set_id: str
    name: str
    split: str
    manifest_uri: str
    manifest_sha256: str
    status: RetrievalEvaluationSetStatus
    created_at: datetime


class RetrievalEvaluationCase(BaseModel):
    retrieval_evaluation_case_id: str
    retrieval_evaluation_set_id: str
    room_asset_sha256: str
    brief: str
    constraints_json: str
    room_type: str
    style_family: str
    created_at: datetime


class ReferenceRelevanceJudgment(BaseModel):
    relevance_judgment_id: str
    retrieval_evaluation_case_id: str
    snapshot_reference_record_id: str
    reviewer: str
    relevance_score: int = Field(ge=0, le=3)
    rationale: str | None = None
    judged_at: datetime


class RetrievalEvaluationRun(BaseModel):
    retrieval_evaluation_run_id: str
    retrieval_evaluation_set_id: str
    vector_index_version_id: str
    retrieval_experiment_id: str
    status: RetrievalEvaluationRunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None


class RetrievalEvaluationResult(BaseModel):
    retrieval_evaluation_result_id: str
    retrieval_evaluation_run_id: str
    retrieval_evaluation_case_id: str
    metrics_json: str
    retrieved_reference_ids_json: str
    created_at: datetime


class RetrievalRunContext(BaseModel):
    """Extended retrieval run metadata for versioned retrieval."""

    run_id: str
    project_id: str
    mode: GenerationMode
    query_text: str
    top_k: int
    final_k: int
    reference_ids: list[str]
    scores_json: list[dict[str, Any]]
    dataset_version: str | None = None
    retrieval_experiment_id: str | None = None
    vector_index_version_id: str | None = None
    created_at: datetime

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from vision_engine.infrastructure.database_base import Base, utcnow


class ReferenceImageAssetRow(Base):
    __tablename__ = "reference_image_assets"

    reference_asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    image_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_records.image_id"), index=True, nullable=False
    )
    image_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    rights_status: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_consent_status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReferenceAnnotationRevisionRow(Base):
    __tablename__ = "reference_annotation_revisions"
    __table_args__ = (
        UniqueConstraint("image_id", "revision_number", name="uq_annotation_revision"),
    )

    annotation_revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    image_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_records.image_id"), index=True, nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    annotation_json: Mapped[str] = mapped_column(Text, nullable=False)
    annotation_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReferenceTagRow(Base):
    __tablename__ = "reference_tags"

    tag_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    tag_group: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReferenceAnnotationTagRow(Base):
    __tablename__ = "reference_annotation_tags"

    annotation_revision_id: Mapped[str] = mapped_column(
        ForeignKey("reference_annotation_revisions.annotation_revision_id"), primary_key=True
    )
    tag_code: Mapped[str] = mapped_column(
        ForeignKey("reference_tags.tag_code"), primary_key=True
    )
    confidence_source: Mapped[str] = mapped_column(String(64), nullable=False)


class CuratedDatasetSnapshotRow(Base):
    __tablename__ = "curated_dataset_snapshots"

    dataset_snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    manifest_uri: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SnapshotReferenceRecordRow(Base):
    __tablename__ = "snapshot_reference_records"

    snapshot_reference_record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("curated_dataset_snapshots.dataset_snapshot_id"), index=True
    )
    image_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_records.image_id"), index=True, nullable=False
    )
    reference_asset_id: Mapped[str] = mapped_column(
        ForeignKey("reference_image_assets.reference_asset_id"), index=True
    )
    annotation_revision_id: Mapped[str] = mapped_column(
        ForeignKey("reference_annotation_revisions.annotation_revision_id"), index=True
    )
    record_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class EmbeddingModelRow(Base):
    __tablename__ = "embedding_models"

    embedding_model_version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    supported_modalities_json: Mapped[str] = mapped_column(Text, nullable=False)
    preprocessing_config_json: Mapped[str] = mapped_column(Text, nullable=False)
    model_card_uri: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmbeddingSpaceRow(Base):
    __tablename__ = "embedding_spaces"

    embedding_space_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    embedding_model_version_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_models.embedding_model_version_id"), index=True
    )
    modality_contract: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_metric: Mapped[str] = mapped_column(String(32), nullable=False)
    normalisation: Mapped[str] = mapped_column(String(32), nullable=False)
    space_fingerprint: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EmbeddingBuildJobRow(Base):
    __tablename__ = "embedding_build_jobs"

    embedding_job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    embedding_space_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_spaces.embedding_space_id"), index=True
    )
    dataset_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("curated_dataset_snapshots.dataset_snapshot_id"), index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    input_manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReferenceEmbeddingRow(Base):
    __tablename__ = "reference_embeddings"

    reference_embedding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reference_asset_id: Mapped[str] = mapped_column(
        ForeignKey("reference_image_assets.reference_asset_id"), index=True
    )
    annotation_revision_id: Mapped[str] = mapped_column(
        ForeignKey("reference_annotation_revisions.annotation_revision_id"), index=True
    )
    embedding_space_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_spaces.embedding_space_id"), index=True
    )
    embedding_job_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_build_jobs.embedding_job_id"), index=True
    )
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    vector_uri: Mapped[str] = mapped_column(Text, nullable=False)
    vector_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VectorIndexVersionRow(Base):
    __tablename__ = "vector_index_versions"

    vector_index_version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("curated_dataset_snapshots.dataset_snapshot_id"), index=True
    )
    embedding_space_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_spaces.embedding_space_id"), index=True
    )
    index_backend: Mapped[str] = mapped_column(String(32), nullable=False)
    index_config_json: Mapped[str] = mapped_column(Text, nullable=False)
    index_uri: Mapped[str] = mapped_column(Text, nullable=False)
    index_manifest_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    vector_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VectorIndexMembershipRow(Base):
    __tablename__ = "vector_index_memberships"
    __table_args__ = (
        UniqueConstraint(
            "vector_index_version_id",
            "snapshot_reference_record_id",
            name="uq_index_membership",
        ),
    )

    index_membership_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vector_index_version_id: Mapped[str] = mapped_column(
        ForeignKey("vector_index_versions.vector_index_version_id"), index=True
    )
    snapshot_reference_record_id: Mapped[str] = mapped_column(
        ForeignKey("snapshot_reference_records.snapshot_reference_record_id"), index=True
    )
    reference_embedding_id: Mapped[str] = mapped_column(
        ForeignKey("reference_embeddings.reference_embedding_id"), index=True
    )
    vector_key: Mapped[str] = mapped_column(String(128), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActiveIndexAliasRow(Base):
    __tablename__ = "active_index_aliases"

    active_index_alias: Mapped[str] = mapped_column(String(64), primary_key=True)
    vector_index_version_id: Mapped[str] = mapped_column(
        ForeignKey("vector_index_versions.vector_index_version_id"), index=True
    )
    environment: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalExperimentRow(Base):
    __tablename__ = "retrieval_experiments"

    retrieval_experiment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    config_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetrievalQueryArtifactRow(Base):
    __tablename__ = "retrieval_query_artifacts"

    retrieval_query_artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_run_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_runs.run_id"), index=True
    )
    upload_id: Mapped[str | None] = mapped_column(ForeignKey("uploads.upload_id"))
    embedding_space_id: Mapped[str] = mapped_column(
        ForeignKey("embedding_spaces.embedding_space_id"), index=True
    )
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    query_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    vector_uri: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetrievalCandidateRow(Base):
    __tablename__ = "retrieval_candidates"

    retrieval_candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_run_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_runs.run_id"), index=True
    )
    snapshot_reference_record_id: Mapped[str] = mapped_column(
        ForeignKey("snapshot_reference_records.snapshot_reference_record_id"), index=True
    )
    initial_rank: Mapped[int | None] = mapped_column(Integer)
    passed_hard_filters: Mapped[bool] = mapped_column(Boolean, default=True)
    filter_reason: Mapped[str | None] = mapped_column(Text)
    selected_for_rerank: Mapped[bool] = mapped_column(Boolean, default=False)
    selected_final: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RerankerModelRow(Base):
    __tablename__ = "reranker_models"

    reranker_model_version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    input_contract: Mapped[str] = mapped_column(String(128), nullable=False)
    training_dataset_snapshot_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetrievalCandidateScoreRow(Base):
    __tablename__ = "retrieval_candidate_scores"

    retrieval_candidate_score_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_candidates.retrieval_candidate_id"), index=True
    )
    reranker_model_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("reranker_models.reranker_model_version_id")
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    score_name: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    normalised_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank_after_stage: Mapped[int | None] = mapped_column(Integer)
    explanation_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetrievalEvaluationSetRow(Base):
    __tablename__ = "retrieval_evaluation_sets"

    retrieval_evaluation_set_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    split: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_uri: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetrievalEvaluationCaseRow(Base):
    __tablename__ = "retrieval_evaluation_cases"

    retrieval_evaluation_case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_evaluation_set_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_evaluation_sets.retrieval_evaluation_set_id"), index=True
    )
    room_asset_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    constraints_json: Mapped[str] = mapped_column(Text, default="[]")
    room_type: Mapped[str] = mapped_column(String(64), nullable=False)
    style_family: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReferenceRelevanceJudgmentRow(Base):
    __tablename__ = "reference_relevance_judgments"

    relevance_judgment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_evaluation_case_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_evaluation_cases.retrieval_evaluation_case_id"), index=True
    )
    snapshot_reference_record_id: Mapped[str] = mapped_column(
        ForeignKey("snapshot_reference_records.snapshot_reference_record_id"), index=True
    )
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    judged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetrievalEvaluationRunRow(Base):
    __tablename__ = "retrieval_evaluation_runs"

    retrieval_evaluation_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_evaluation_set_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_evaluation_sets.retrieval_evaluation_set_id"), index=True
    )
    vector_index_version_id: Mapped[str] = mapped_column(
        ForeignKey("vector_index_versions.vector_index_version_id"), index=True
    )
    retrieval_experiment_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_experiments.retrieval_experiment_id"), index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetrievalEvaluationResultRow(Base):
    __tablename__ = "retrieval_evaluation_results"

    retrieval_evaluation_result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_evaluation_run_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_evaluation_runs.retrieval_evaluation_run_id"), index=True
    )
    retrieval_evaluation_case_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_evaluation_cases.retrieval_evaluation_case_id"), index=True
    )
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_reference_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

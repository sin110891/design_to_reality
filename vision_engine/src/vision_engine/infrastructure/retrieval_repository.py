from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select

from vision_engine.domain.enums import (
    AnnotationRevisionStatus,
    DatasetSnapshotStatus,
    EmbeddingJobStatus,
    EmbeddingModality,
    RetrievalEvaluationRunStatus,
    RetrievalEvaluationSetStatus,
    RetrievalExperimentStatus,
    RetrievalScoreStage,
    RerankerModelStatus,
    VectorIndexStatus,
)
from vision_engine.domain.models import DatasetRecord
from vision_engine.domain.retrieval_models import (
    ActiveIndexAlias,
    CuratedDatasetSnapshot,
    EmbeddingBuildJob,
    EmbeddingModelVersion,
    EmbeddingSpace,
    ReferenceAnnotationRevision,
    ReferenceEmbedding,
    ReferenceImageAsset,
    ReferenceRelevanceJudgment,
    RetrievalCandidate,
    RetrievalCandidateScore,
    RetrievalEvaluationCase,
    RetrievalEvaluationResult,
    RetrievalEvaluationRun,
    RetrievalEvaluationSet,
    RetrievalExperiment,
    RetrievalQueryArtifact,
    RerankerModelVersion,
    SnapshotReferenceRecord,
    VectorIndexMembership,
    VectorIndexVersion,
)
from vision_engine.infrastructure.retrieval_schema import (
    ActiveIndexAliasRow,
    CuratedDatasetSnapshotRow,
    EmbeddingBuildJobRow,
    EmbeddingModelRow,
    EmbeddingSpaceRow,
    ReferenceAnnotationRevisionRow,
    ReferenceEmbeddingRow,
    ReferenceImageAssetRow,
    ReferenceRelevanceJudgmentRow,
    RetrievalCandidateRow,
    RetrievalCandidateScoreRow,
    RetrievalEvaluationCaseRow,
    RetrievalEvaluationResultRow,
    RetrievalEvaluationRunRow,
    RetrievalEvaluationSetRow,
    RetrievalExperimentRow,
    RetrievalQueryArtifactRow,
    RerankerModelRow,
    SnapshotReferenceRecordRow,
    VectorIndexMembershipRow,
    VectorIndexVersionRow,
)
from vision_engine.infrastructure.sqlite_repository import new_id, utcnow


class RetrievalRepositoryMixin:
    """Persistence for multimodal retrieval/index entities."""

    def save_reference_asset(self, asset: ReferenceImageAsset) -> None:
        with self.session() as session:
            session.merge(
                ReferenceImageAssetRow(
                    reference_asset_id=asset.reference_asset_id,
                    image_id=asset.image_id,
                    image_sha256=asset.image_sha256,
                    storage_uri=asset.storage_uri,
                    mime_type=asset.mime_type,
                    width=asset.width,
                    height=asset.height,
                    file_size_bytes=asset.file_size_bytes,
                    rights_status=asset.rights_status.value,
                    retention_consent_status=asset.retention_consent_status.value,
                    created_at=asset.created_at,
                    deleted_at=asset.deleted_at,
                )
            )

    def get_reference_asset_by_image(self, image_id: str) -> ReferenceImageAsset | None:
        with self.session() as session:
            row = session.scalars(
                select(ReferenceImageAssetRow)
                .where(ReferenceImageAssetRow.image_id == image_id)
                .order_by(ReferenceImageAssetRow.created_at.desc())
            ).first()
            return self._to_reference_asset(row) if row else None

    def save_annotation_revision(self, revision: ReferenceAnnotationRevision) -> None:
        with self.session() as session:
            session.merge(
                ReferenceAnnotationRevisionRow(
                    annotation_revision_id=revision.annotation_revision_id,
                    image_id=revision.image_id,
                    revision_number=revision.revision_number,
                    annotation_json=revision.annotation_json,
                    annotation_sha256=revision.annotation_sha256,
                    reviewer=revision.reviewer,
                    status=revision.status.value,
                    created_at=revision.created_at,
                )
            )

    def get_latest_annotation_revision(self, image_id: str) -> ReferenceAnnotationRevision | None:
        with self.session() as session:
            row = session.scalars(
                select(ReferenceAnnotationRevisionRow)
                .where(ReferenceAnnotationRevisionRow.image_id == image_id)
                .order_by(ReferenceAnnotationRevisionRow.revision_number.desc())
            ).first()
            return self._to_annotation_revision(row) if row else None

    def save_dataset_snapshot(self, snapshot: CuratedDatasetSnapshot) -> None:
        with self.session() as session:
            session.merge(
                CuratedDatasetSnapshotRow(
                    dataset_snapshot_id=snapshot.dataset_snapshot_id,
                    snapshot_name=snapshot.snapshot_name,
                    manifest_uri=snapshot.manifest_uri,
                    manifest_sha256=snapshot.manifest_sha256,
                    record_count=snapshot.record_count,
                    status=snapshot.status.value,
                    created_at=snapshot.created_at,
                    sealed_at=snapshot.sealed_at,
                )
            )

    def get_dataset_snapshot(self, dataset_snapshot_id: str) -> CuratedDatasetSnapshot | None:
        with self.session() as session:
            row = session.get(CuratedDatasetSnapshotRow, dataset_snapshot_id)
            return self._to_dataset_snapshot(row) if row else None

    def save_snapshot_reference_record(self, record: SnapshotReferenceRecord) -> None:
        with self.session() as session:
            session.merge(
                SnapshotReferenceRecordRow(
                    snapshot_reference_record_id=record.snapshot_reference_record_id,
                    dataset_snapshot_id=record.dataset_snapshot_id,
                    image_id=record.image_id,
                    reference_asset_id=record.reference_asset_id,
                    annotation_revision_id=record.annotation_revision_id,
                    record_sha256=record.record_sha256,
                )
            )

    def list_snapshot_reference_records(
        self, dataset_snapshot_id: str
    ) -> list[SnapshotReferenceRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(SnapshotReferenceRecordRow).where(
                    SnapshotReferenceRecordRow.dataset_snapshot_id == dataset_snapshot_id
                )
            ).all()
            records = [self._to_snapshot_reference_record(r) for r in rows]
            from vision_engine.infrastructure.sqlite_repository import DatasetRecordRow

            for rec in records:
                ds_row = session.get(DatasetRecordRow, rec.image_id)
                if ds_row:
                    rec.record = DatasetRecord.model_validate_json(ds_row.payload_json)
            return records

    def save_embedding_model(self, model: EmbeddingModelVersion) -> None:
        with self.session() as session:
            session.merge(
                EmbeddingModelRow(
                    embedding_model_version_id=model.embedding_model_version_id,
                    provider=model.provider,
                    model_name=model.model_name,
                    model_revision=model.model_revision,
                    supported_modalities_json=model.supported_modalities_json,
                    preprocessing_config_json=model.preprocessing_config_json,
                    model_card_uri=model.model_card_uri,
                    created_at=model.created_at,
                )
            )

    def get_embedding_model(self, embedding_model_version_id: str) -> EmbeddingModelVersion | None:
        with self.session() as session:
            row = session.get(EmbeddingModelRow, embedding_model_version_id)
            return self._to_embedding_model(row) if row else None

    def save_embedding_space(self, space: EmbeddingSpace) -> None:
        with self.session() as session:
            session.merge(
                EmbeddingSpaceRow(
                    embedding_space_id=space.embedding_space_id,
                    embedding_model_version_id=space.embedding_model_version_id,
                    modality_contract=space.modality_contract,
                    dimension=space.dimension,
                    distance_metric=space.distance_metric,
                    normalisation=space.normalisation,
                    space_fingerprint=space.space_fingerprint,
                    created_at=space.created_at,
                )
            )

    def get_embedding_space(self, embedding_space_id: str) -> EmbeddingSpace | None:
        with self.session() as session:
            row = session.get(EmbeddingSpaceRow, embedding_space_id)
            return self._to_embedding_space(row) if row else None

    def get_embedding_space_by_fingerprint(self, fingerprint: str) -> EmbeddingSpace | None:
        with self.session() as session:
            row = session.scalars(
                select(EmbeddingSpaceRow).where(
                    EmbeddingSpaceRow.space_fingerprint == fingerprint
                )
            ).first()
            return self._to_embedding_space(row) if row else None

    def save_embedding_job(self, job: EmbeddingBuildJob) -> None:
        with self.session() as session:
            session.merge(
                EmbeddingBuildJobRow(
                    embedding_job_id=job.embedding_job_id,
                    embedding_space_id=job.embedding_space_id,
                    dataset_snapshot_id=job.dataset_snapshot_id,
                    status=job.status.value,
                    input_manifest_sha256=job.input_manifest_sha256,
                    error_summary=job.error_summary,
                    started_at=job.started_at,
                    completed_at=job.completed_at,
                )
            )

    def save_reference_embedding(self, embedding: ReferenceEmbedding) -> None:
        with self.session() as session:
            session.merge(
                ReferenceEmbeddingRow(
                    reference_embedding_id=embedding.reference_embedding_id,
                    reference_asset_id=embedding.reference_asset_id,
                    annotation_revision_id=embedding.annotation_revision_id,
                    embedding_space_id=embedding.embedding_space_id,
                    embedding_job_id=embedding.embedding_job_id,
                    modality=embedding.modality.value,
                    vector_uri=embedding.vector_uri,
                    vector_sha256=embedding.vector_sha256,
                    source_content_sha256=embedding.source_content_sha256,
                    created_at=embedding.created_at,
                )
            )

    def list_reference_embeddings_for_job(self, embedding_job_id: str) -> list[ReferenceEmbedding]:
        with self.session() as session:
            rows = session.scalars(
                select(ReferenceEmbeddingRow).where(
                    ReferenceEmbeddingRow.embedding_job_id == embedding_job_id
                )
            ).all()
            return [self._to_reference_embedding(r) for r in rows]

    def save_vector_index_version(self, index: VectorIndexVersion) -> None:
        with self.session() as session:
            session.merge(
                VectorIndexVersionRow(
                    vector_index_version_id=index.vector_index_version_id,
                    dataset_snapshot_id=index.dataset_snapshot_id,
                    embedding_space_id=index.embedding_space_id,
                    index_backend=index.index_backend,
                    index_config_json=index.index_config_json,
                    index_uri=index.index_uri,
                    index_manifest_sha256=index.index_manifest_sha256,
                    vector_count=index.vector_count,
                    status=index.status.value,
                    created_at=index.created_at,
                    validated_at=index.validated_at,
                    promoted_at=index.promoted_at,
                )
            )

    def get_vector_index_version(self, vector_index_version_id: str) -> VectorIndexVersion | None:
        with self.session() as session:
            row = session.get(VectorIndexVersionRow, vector_index_version_id)
            return self._to_vector_index_version(row) if row else None

    def save_index_membership(self, membership: VectorIndexMembership) -> None:
        with self.session() as session:
            session.merge(
                VectorIndexMembershipRow(
                    index_membership_id=membership.index_membership_id,
                    vector_index_version_id=membership.vector_index_version_id,
                    snapshot_reference_record_id=membership.snapshot_reference_record_id,
                    reference_embedding_id=membership.reference_embedding_id,
                    vector_key=membership.vector_key,
                    added_at=membership.added_at,
                )
            )

    def list_index_memberships(self, vector_index_version_id: str) -> list[VectorIndexMembership]:
        with self.session() as session:
            rows = session.scalars(
                select(VectorIndexMembershipRow).where(
                    VectorIndexMembershipRow.vector_index_version_id == vector_index_version_id
                )
            ).all()
            return [self._to_index_membership(r) for r in rows]

    def set_active_index_alias(self, alias: ActiveIndexAlias) -> None:
        with self.session() as session:
            existing = session.scalars(
                select(ActiveIndexAliasRow).where(
                    ActiveIndexAliasRow.environment == alias.environment,
                    ActiveIndexAliasRow.deactivated_at.is_(None),
                )
            ).all()
            now = utcnow()
            for row in existing:
                row.deactivated_at = now
            session.merge(
                ActiveIndexAliasRow(
                    active_index_alias=alias.active_index_alias,
                    vector_index_version_id=alias.vector_index_version_id,
                    environment=alias.environment,
                    activated_at=alias.activated_at,
                    deactivated_at=alias.deactivated_at,
                )
            )

    def get_active_index_for_environment(self, environment: str) -> VectorIndexVersion | None:
        with self.session() as session:
            alias = session.scalars(
                select(ActiveIndexAliasRow).where(
                    ActiveIndexAliasRow.environment == environment,
                    ActiveIndexAliasRow.deactivated_at.is_(None),
                )
            ).first()
            if not alias:
                return None
            row = session.get(VectorIndexVersionRow, alias.vector_index_version_id)
            return self._to_vector_index_version(row) if row else None

    def save_retrieval_experiment(self, experiment: RetrievalExperiment) -> None:
        with self.session() as session:
            session.merge(
                RetrievalExperimentRow(
                    retrieval_experiment_id=experiment.retrieval_experiment_id,
                    name=experiment.name,
                    config_json=experiment.config_json,
                    config_sha256=experiment.config_sha256,
                    status=experiment.status.value,
                    created_at=experiment.created_at,
                )
            )

    def get_retrieval_experiment(self, retrieval_experiment_id: str) -> RetrievalExperiment | None:
        with self.session() as session:
            row = session.get(RetrievalExperimentRow, retrieval_experiment_id)
            return self._to_retrieval_experiment(row) if row else None

    def get_active_retrieval_experiment(self) -> RetrievalExperiment | None:
        with self.session() as session:
            row = session.scalars(
                select(RetrievalExperimentRow).where(
                    RetrievalExperimentRow.status == RetrievalExperimentStatus.ACTIVE.value
                )
            ).first()
            return self._to_retrieval_experiment(row) if row else None

    def save_retrieval_query_artifact(self, artifact: RetrievalQueryArtifact) -> None:
        with self.session() as session:
            session.merge(
                RetrievalQueryArtifactRow(
                    retrieval_query_artifact_id=artifact.retrieval_query_artifact_id,
                    retrieval_run_id=artifact.retrieval_run_id,
                    upload_id=artifact.upload_id,
                    embedding_space_id=artifact.embedding_space_id,
                    modality=artifact.modality.value,
                    query_sha256=artifact.query_sha256,
                    vector_uri=artifact.vector_uri,
                    created_at=artifact.created_at,
                )
            )

    def save_retrieval_candidate(self, candidate: RetrievalCandidate) -> None:
        with self.session() as session:
            session.merge(
                RetrievalCandidateRow(
                    retrieval_candidate_id=candidate.retrieval_candidate_id,
                    retrieval_run_id=candidate.retrieval_run_id,
                    snapshot_reference_record_id=candidate.snapshot_reference_record_id,
                    initial_rank=candidate.initial_rank,
                    passed_hard_filters=candidate.passed_hard_filters,
                    filter_reason=candidate.filter_reason,
                    selected_for_rerank=candidate.selected_for_rerank,
                    selected_final=candidate.selected_final,
                    created_at=candidate.created_at,
                )
            )

    def save_retrieval_candidate_score(self, score: RetrievalCandidateScore) -> None:
        with self.session() as session:
            session.merge(
                RetrievalCandidateScoreRow(
                    retrieval_candidate_score_id=score.retrieval_candidate_score_id,
                    retrieval_candidate_id=score.retrieval_candidate_id,
                    reranker_model_version_id=score.reranker_model_version_id,
                    stage=score.stage.value,
                    score_name=score.score_name,
                    raw_score=score.raw_score,
                    normalised_score=score.normalised_score,
                    rank_after_stage=score.rank_after_stage,
                    explanation_json=score.explanation_json,
                    created_at=score.created_at,
                )
            )

    def save_reranker_model(self, model: RerankerModelVersion) -> None:
        with self.session() as session:
            session.merge(
                RerankerModelRow(
                    reranker_model_version_id=model.reranker_model_version_id,
                    provider=model.provider,
                    model_name=model.model_name,
                    model_revision=model.model_revision,
                    input_contract=model.input_contract,
                    training_dataset_snapshot_id=model.training_dataset_snapshot_id,
                    status=model.status.value,
                    created_at=model.created_at,
                )
            )

    def get_active_reranker_model(self) -> RerankerModelVersion | None:
        with self.session() as session:
            row = session.scalars(
                select(RerankerModelRow).where(
                    RerankerModelRow.status == RerankerModelStatus.ACTIVE.value
                )
            ).first()
            return self._to_reranker_model(row) if row else None

    def save_retrieval_evaluation_set(self, eval_set: RetrievalEvaluationSet) -> None:
        with self.session() as session:
            session.merge(
                RetrievalEvaluationSetRow(
                    retrieval_evaluation_set_id=eval_set.retrieval_evaluation_set_id,
                    name=eval_set.name,
                    split=eval_set.split,
                    manifest_uri=eval_set.manifest_uri,
                    manifest_sha256=eval_set.manifest_sha256,
                    status=eval_set.status.value,
                    created_at=eval_set.created_at,
                )
            )

    def save_retrieval_evaluation_case(self, case: RetrievalEvaluationCase) -> None:
        with self.session() as session:
            session.merge(
                RetrievalEvaluationCaseRow(
                    retrieval_evaluation_case_id=case.retrieval_evaluation_case_id,
                    retrieval_evaluation_set_id=case.retrieval_evaluation_set_id,
                    room_asset_sha256=case.room_asset_sha256,
                    brief=case.brief,
                    constraints_json=case.constraints_json,
                    room_type=case.room_type,
                    style_family=case.style_family,
                    created_at=case.created_at,
                )
            )

    def list_retrieval_evaluation_cases(
        self, retrieval_evaluation_set_id: str
    ) -> list[RetrievalEvaluationCase]:
        with self.session() as session:
            rows = session.scalars(
                select(RetrievalEvaluationCaseRow).where(
                    RetrievalEvaluationCaseRow.retrieval_evaluation_set_id
                    == retrieval_evaluation_set_id
                )
            ).all()
            return [self._to_retrieval_evaluation_case(r) for r in rows]

    def save_relevance_judgment(self, judgment: ReferenceRelevanceJudgment) -> None:
        with self.session() as session:
            session.merge(
                ReferenceRelevanceJudgmentRow(
                    relevance_judgment_id=judgment.relevance_judgment_id,
                    retrieval_evaluation_case_id=judgment.retrieval_evaluation_case_id,
                    snapshot_reference_record_id=judgment.snapshot_reference_record_id,
                    reviewer=judgment.reviewer,
                    relevance_score=judgment.relevance_score,
                    rationale=judgment.rationale,
                    judged_at=judgment.judged_at,
                )
            )

    def list_relevance_judgments_for_case(
        self, retrieval_evaluation_case_id: str
    ) -> list[ReferenceRelevanceJudgment]:
        with self.session() as session:
            rows = session.scalars(
                select(ReferenceRelevanceJudgmentRow).where(
                    ReferenceRelevanceJudgmentRow.retrieval_evaluation_case_id
                    == retrieval_evaluation_case_id
                )
            ).all()
            return [self._to_relevance_judgment(r) for r in rows]

    def save_retrieval_evaluation_run(self, run: RetrievalEvaluationRun) -> None:
        with self.session() as session:
            session.merge(
                RetrievalEvaluationRunRow(
                    retrieval_evaluation_run_id=run.retrieval_evaluation_run_id,
                    retrieval_evaluation_set_id=run.retrieval_evaluation_set_id,
                    vector_index_version_id=run.vector_index_version_id,
                    retrieval_experiment_id=run.retrieval_experiment_id,
                    status=run.status.value,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                )
            )

    def save_retrieval_evaluation_result(self, result: RetrievalEvaluationResult) -> None:
        with self.session() as session:
            session.merge(
                RetrievalEvaluationResultRow(
                    retrieval_evaluation_result_id=result.retrieval_evaluation_result_id,
                    retrieval_evaluation_run_id=result.retrieval_evaluation_run_id,
                    retrieval_evaluation_case_id=result.retrieval_evaluation_case_id,
                    metrics_json=result.metrics_json,
                    retrieved_reference_ids_json=result.retrieved_reference_ids_json,
                    created_at=result.created_at,
                )
            )

    def save_retrieval_run_extended(
        self,
        *,
        run_id: str,
        project_id: str,
        mode: str,
        query_text: str,
        top_k: int,
        final_k: int,
        reference_ids: list[str],
        scores_json: list[dict[str, Any]],
        dataset_version: str | None,
        retrieval_experiment_id: str | None,
        vector_index_version_id: str | None,
        created_at: datetime,
        references: list[dict[str, Any]] | None = None,
    ) -> None:
        from vision_engine.infrastructure.sqlite_repository import RetrievalRunReferenceRow, RetrievalRunRow

        with self.session() as session:
            session.merge(
                RetrievalRunRow(
                    run_id=run_id,
                    project_id=project_id,
                    mode=mode,
                    query_text=query_text,
                    top_k=top_k,
                    final_k=final_k,
                    reference_ids_json=json.dumps(reference_ids),
                    scores_json=json.dumps(scores_json),
                    dataset_version=dataset_version,
                    retrieval_experiment_id=retrieval_experiment_id,
                    vector_index_version_id=vector_index_version_id,
                    created_at=created_at,
                )
            )
            if references:
                for idx, ref in enumerate(references, start=1):
                    session.merge(
                        RetrievalRunReferenceRow(
                            retrieval_run_reference_id=new_id("rrr"),
                            retrieval_run_id=run_id,
                            dataset_record_id=ref["image_id"],
                            retrieval_candidate_id=ref.get("retrieval_candidate_id"),
                            retrieval_rank=idx,
                            final_score=float(ref.get("score", 0.0)),
                            diversity_role=ref.get("diversity_role"),
                        )
                    )

    @staticmethod
    def _to_reference_asset(row: ReferenceImageAssetRow) -> ReferenceImageAsset:
        from vision_engine.domain.enums import RetentionConsentStatus, RightsStatus

        return ReferenceImageAsset(
            reference_asset_id=row.reference_asset_id,
            image_id=row.image_id,
            image_sha256=row.image_sha256,
            storage_uri=row.storage_uri,
            mime_type=row.mime_type,
            width=row.width,
            height=row.height,
            file_size_bytes=row.file_size_bytes,
            rights_status=RightsStatus(row.rights_status),
            retention_consent_status=RetentionConsentStatus(row.retention_consent_status),
            created_at=row.created_at,
            deleted_at=row.deleted_at,
        )

    @staticmethod
    def _to_annotation_revision(row: ReferenceAnnotationRevisionRow) -> ReferenceAnnotationRevision:
        return ReferenceAnnotationRevision(
            annotation_revision_id=row.annotation_revision_id,
            image_id=row.image_id,
            revision_number=row.revision_number,
            annotation_json=row.annotation_json,
            annotation_sha256=row.annotation_sha256,
            reviewer=row.reviewer,
            status=AnnotationRevisionStatus(row.status),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_dataset_snapshot(row: CuratedDatasetSnapshotRow) -> CuratedDatasetSnapshot:
        return CuratedDatasetSnapshot(
            dataset_snapshot_id=row.dataset_snapshot_id,
            snapshot_name=row.snapshot_name,
            manifest_uri=row.manifest_uri,
            manifest_sha256=row.manifest_sha256,
            record_count=row.record_count,
            status=DatasetSnapshotStatus(row.status),
            created_at=row.created_at,
            sealed_at=row.sealed_at,
        )

    @staticmethod
    def _to_snapshot_reference_record(row: SnapshotReferenceRecordRow) -> SnapshotReferenceRecord:
        return SnapshotReferenceRecord(
            snapshot_reference_record_id=row.snapshot_reference_record_id,
            dataset_snapshot_id=row.dataset_snapshot_id,
            image_id=row.image_id,
            reference_asset_id=row.reference_asset_id,
            annotation_revision_id=row.annotation_revision_id,
            record_sha256=row.record_sha256,
        )

    @staticmethod
    def _to_embedding_model(row: EmbeddingModelRow) -> EmbeddingModelVersion:
        return EmbeddingModelVersion(
            embedding_model_version_id=row.embedding_model_version_id,
            provider=row.provider,
            model_name=row.model_name,
            model_revision=row.model_revision,
            supported_modalities_json=row.supported_modalities_json,
            preprocessing_config_json=row.preprocessing_config_json,
            model_card_uri=row.model_card_uri,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_embedding_space(row: EmbeddingSpaceRow) -> EmbeddingSpace:
        return EmbeddingSpace(
            embedding_space_id=row.embedding_space_id,
            embedding_model_version_id=row.embedding_model_version_id,
            modality_contract=row.modality_contract,
            dimension=row.dimension,
            distance_metric=row.distance_metric,
            normalisation=row.normalisation,
            space_fingerprint=row.space_fingerprint,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_embedding_job(row: EmbeddingBuildJobRow) -> EmbeddingBuildJob:
        return EmbeddingBuildJob(
            embedding_job_id=row.embedding_job_id,
            embedding_space_id=row.embedding_space_id,
            dataset_snapshot_id=row.dataset_snapshot_id,
            status=EmbeddingJobStatus(row.status),
            input_manifest_sha256=row.input_manifest_sha256,
            error_summary=row.error_summary,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )

    @staticmethod
    def _to_reference_embedding(row: ReferenceEmbeddingRow) -> ReferenceEmbedding:
        return ReferenceEmbedding(
            reference_embedding_id=row.reference_embedding_id,
            reference_asset_id=row.reference_asset_id,
            annotation_revision_id=row.annotation_revision_id,
            embedding_space_id=row.embedding_space_id,
            embedding_job_id=row.embedding_job_id,
            modality=EmbeddingModality(row.modality),
            vector_uri=row.vector_uri,
            vector_sha256=row.vector_sha256,
            source_content_sha256=row.source_content_sha256,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_vector_index_version(row: VectorIndexVersionRow) -> VectorIndexVersion:
        return VectorIndexVersion(
            vector_index_version_id=row.vector_index_version_id,
            dataset_snapshot_id=row.dataset_snapshot_id,
            embedding_space_id=row.embedding_space_id,
            index_backend=row.index_backend,
            index_config_json=row.index_config_json,
            index_uri=row.index_uri,
            index_manifest_sha256=row.index_manifest_sha256,
            vector_count=row.vector_count,
            status=VectorIndexStatus(row.status),
            created_at=row.created_at,
            validated_at=row.validated_at,
            promoted_at=row.promoted_at,
        )

    @staticmethod
    def _to_index_membership(row: VectorIndexMembershipRow) -> VectorIndexMembership:
        return VectorIndexMembership(
            index_membership_id=row.index_membership_id,
            vector_index_version_id=row.vector_index_version_id,
            snapshot_reference_record_id=row.snapshot_reference_record_id,
            reference_embedding_id=row.reference_embedding_id,
            vector_key=row.vector_key,
            added_at=row.added_at,
        )

    @staticmethod
    def _to_retrieval_experiment(row: RetrievalExperimentRow) -> RetrievalExperiment:
        return RetrievalExperiment(
            retrieval_experiment_id=row.retrieval_experiment_id,
            name=row.name,
            config_json=row.config_json,
            config_sha256=row.config_sha256,
            status=RetrievalExperimentStatus(row.status),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_reranker_model(row: RerankerModelRow) -> RerankerModelVersion:
        return RerankerModelVersion(
            reranker_model_version_id=row.reranker_model_version_id,
            provider=row.provider,
            model_name=row.model_name,
            model_revision=row.model_revision,
            input_contract=row.input_contract,
            training_dataset_snapshot_id=row.training_dataset_snapshot_id,
            status=RerankerModelStatus(row.status),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_retrieval_evaluation_case(row: RetrievalEvaluationCaseRow) -> RetrievalEvaluationCase:
        return RetrievalEvaluationCase(
            retrieval_evaluation_case_id=row.retrieval_evaluation_case_id,
            retrieval_evaluation_set_id=row.retrieval_evaluation_set_id,
            room_asset_sha256=row.room_asset_sha256,
            brief=row.brief,
            constraints_json=row.constraints_json,
            room_type=row.room_type,
            style_family=row.style_family,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_relevance_judgment(row: ReferenceRelevanceJudgmentRow) -> ReferenceRelevanceJudgment:
        return ReferenceRelevanceJudgment(
            relevance_judgment_id=row.relevance_judgment_id,
            retrieval_evaluation_case_id=row.retrieval_evaluation_case_id,
            snapshot_reference_record_id=row.snapshot_reference_record_id,
            reviewer=row.reviewer,
            relevance_score=row.relevance_score,
            rationale=row.rationale,
            judged_at=row.judged_at,
        )

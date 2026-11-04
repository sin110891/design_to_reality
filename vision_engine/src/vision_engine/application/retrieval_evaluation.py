from __future__ import annotations

import json
from datetime import datetime, timezone

from vision_engine.application.retrieve_references import retrieve_references_versioned
from vision_engine.domain.enums import RetrievalEvaluationRunStatus
from vision_engine.domain.retrieval_models import RetrievalEvaluationResult, RetrievalEvaluationRun
from vision_engine.domain.retrieval_scoring import ndcg_at_k, recall_at_k
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_retrieval_evaluation(
    *,
    repo: SqliteRepository,
    retrieval_evaluation_set_id: str,
    vector_index_version_id: str,
    retrieval_experiment_id: str,
    room_image_resolver,
    settings,
    embedder,
    versioned_store,
) -> RetrievalEvaluationRun:
    eval_run = RetrievalEvaluationRun(
        retrieval_evaluation_run_id=new_id("revrun"),
        retrieval_evaluation_set_id=retrieval_evaluation_set_id,
        vector_index_version_id=vector_index_version_id,
        retrieval_experiment_id=retrieval_experiment_id,
        status=RetrievalEvaluationRunStatus.RUNNING,
        started_at=utcnow(),
    )
    repo.save_retrieval_evaluation_run(eval_run)

    cases = repo.list_retrieval_evaluation_cases(retrieval_evaluation_set_id)
    for case in cases:
        room_path = room_image_resolver(case.room_asset_sha256)
        if room_path is None:
            continue
        from vision_engine.domain.models import ProjectInput, ProjectRecord

        project = ProjectRecord(
            project_id=new_id("proj"),
            room_image_path=str(room_path),
            room_type=case.room_type,
            style_family=case.style_family,
            brief=case.brief,
            constraints=json.loads(case.constraints_json or "[]"),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        refs, _run = retrieve_references_versioned(
            repo=repo,
            settings=settings,
            embedder=embedder,
            versioned_store=versioned_store,
            project=project,
            experiment_id=retrieval_experiment_id,
            index_version_id=vector_index_version_id,
            persist_run=False,
        )
        retrieved_ids = [r.image_id for r in refs]
        judgments = repo.list_relevance_judgments_for_case(case.retrieval_evaluation_case_id)
        relevance_by_ref = {
            j.snapshot_reference_record_id: j.relevance_score for j in judgments
        }
        snap_records = repo.list_snapshot_reference_records(
            versioned_store.index_version.dataset_snapshot_id
        )
        snap_by_image = {s.image_id: s.snapshot_reference_record_id for s in snap_records}
        relevances = []
        for image_id in retrieved_ids:
            snap_id = snap_by_image.get(image_id)
            relevances.append(relevance_by_ref.get(snap_id or "", 0))
        relevant = {
            snap_id
            for snap_id, score in relevance_by_ref.items()
            if score >= 2
        }
        relevant_image_ids = {
            s.image_id for s in snap_records if s.snapshot_reference_record_id in relevant
        }
        metrics = {
            "recall_at_3": recall_at_k(relevant_image_ids, retrieved_ids, 3),
            "recall_at_10": recall_at_k(relevant_image_ids, retrieved_ids, 10),
            "ndcg_at_3": ndcg_at_k(relevances, 3),
            "ndcg_at_10": ndcg_at_k(relevances, 10),
        }
        repo.save_retrieval_evaluation_result(
            RetrievalEvaluationResult(
                retrieval_evaluation_result_id=new_id("reval"),
                retrieval_evaluation_run_id=eval_run.retrieval_evaluation_run_id,
                retrieval_evaluation_case_id=case.retrieval_evaluation_case_id,
                metrics_json=json.dumps(metrics),
                retrieved_reference_ids_json=json.dumps(retrieved_ids),
                created_at=utcnow(),
            )
        )

    eval_run.status = RetrievalEvaluationRunStatus.COMPLETED
    eval_run.completed_at = utcnow()
    repo.save_retrieval_evaluation_run(eval_run)
    return eval_run

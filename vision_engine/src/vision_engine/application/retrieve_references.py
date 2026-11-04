from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from vision_engine.application.retrieval_experiments import (
    ensure_default_reranker_model,
    ensure_default_retrieval_experiment,
)
from vision_engine.domain.enums import (
    EmbeddingModality,
    GenerationMode,
    ProjectStatus,
    RetrievalScoreStage,
)
from vision_engine.domain.errors import EmptyRetrievalError
from vision_engine.domain.models import (
    ProjectInput,
    ProjectRecord,
    RetrievalRunRecord,
    RetrievedReference,
)
from vision_engine.domain.retrieval_models import (
    RetrievalCandidate,
    RetrievalCandidateScore,
    RetrievalQueryArtifact,
)
from vision_engine.domain.retrieval_scoring import reciprocal_rank_fusion
from vision_engine.domain.services import (
    build_match_rationale,
    diversify_references,
    hybrid_score,
    metadata_match_score,
    passes_hard_filters,
    soft_filter_penalty,
)
from vision_engine.infrastructure.content_hash import sha256_text
from vision_engine.infrastructure.embedding_clients import EmbeddingClient
from vision_engine.infrastructure.embedding_clients.joint import JointEmbeddingClient
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.reranker import DeterministicMultimodalReranker
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.infrastructure.vector_store import NumpyVectorStore
from vision_engine.infrastructure.versioned_vector_store import IndexedReference, VersionedVectorStore
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_query_input(project: ProjectRecord) -> ProjectInput:
    return ProjectInput(
        room_image_path=project.room_image_path,
        inspiration_image_paths=project.inspiration_image_paths,
        room_type=project.room_type,
        style_family=project.style_family,
        brief=project.brief,
        budget_band=project.budget_band,
        constraints=project.constraints,
        project_type=project.project_type,
    )


def _legacy_retrieve(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    embedder: EmbeddingClient,
    store: NumpyVectorStore,
    project: ProjectRecord,
    mode: GenerationMode,
) -> tuple[list[RetrievedReference], RetrievalRunRecord]:
    query = _build_query_input(project)
    room_path = settings.resolve(project.room_image_path)
    room_emb = embedder.embed_image(room_path)
    text_parts = [project.brief, project.room_type, project.style_family or ""]
    if project.budget_band:
        text_parts.append(project.budget_band)
    text_parts.extend(project.constraints)
    for insp in project.inspiration_image_paths:
        text_parts.append(Path(insp).stem)
    text_emb = embedder.embed_text(" ".join(text_parts))

    cfg = settings.retrieval
    image_hits = {i: s for i, s in store.search_image(room_emb, top_k=cfg.top_k)}
    text_hits = {i: s for i, s in store.search_text(text_emb, top_k=cfg.top_k)}
    candidate_idxs = set(image_hits) | set(text_hits)
    if not candidate_idxs:
        candidate_idxs = set(range(min(cfg.top_k, len(store.records))))

    scored: list[RetrievedReference] = []
    for idx in candidate_idxs:
        record = store.records[idx]
        if not passes_hard_filters(query, record):
            continue
        image_sim = float(image_hits.get(idx, 0.0))
        text_sim = float(text_hits.get(idx, 0.0))
        meta = metadata_match_score(query, record)
        quality = record.architect_quality_score
        score = hybrid_score(
            image_similarity=image_sim,
            text_similarity=text_sim,
            metadata_match=meta,
            architect_quality=quality,
            image_weight=cfg.image_similarity_weight,
            text_weight=cfg.text_similarity_weight,
            metadata_weight=cfg.metadata_match_weight,
            quality_weight=cfg.architect_quality_weight,
        )
        score *= soft_filter_penalty(query, record)
        scored.append(
            RetrievedReference(
                image_id=record.image_id,
                image_path=record.image_path,
                score=score,
                image_similarity=image_sim,
                text_similarity=text_sim,
                metadata_match=meta,
                architect_quality=quality,
                match_rationale=build_match_rationale(
                    image_similarity=image_sim,
                    text_similarity=text_sim,
                    metadata_match=meta,
                    architect_quality=quality,
                    record=record,
                ),
                record=record,
            )
        )

    scored.sort(key=lambda r: r.score, reverse=True)
    top = scored[: cfg.top_k]
    final = diversify_references(top, final_k=cfg.final_k)
    if not final:
        raise EmptyRetrievalError(
            "No curated references matched filters — broaden room type / style / budget"
        )

    run = RetrievalRunRecord(
        run_id=new_id("ret"),
        project_id=project.project_id,
        mode=mode,
        query_text=project.brief,
        top_k=cfg.top_k,
        final_k=cfg.final_k,
        reference_ids=[r.image_id for r in final],
        scores_json=[
            {
                "image_id": r.image_id,
                "score": r.score,
                "image_similarity": r.image_similarity,
                "text_similarity": r.text_similarity,
                "metadata_match": r.metadata_match,
                "architect_quality": r.architect_quality,
                "diversity_role": r.diversity_role,
                "match_rationale": r.match_rationale,
            }
            for r in final
        ],
        dataset_version=str(settings.paths.index_path.name),
        created_at=utcnow(),
    )
    repo.save_retrieval_run(
        run,
        references=[
            {
                "image_id": r.image_id,
                "score": r.score,
                "diversity_role": r.diversity_role,
            }
            for r in final
        ],
    )
    project.status = ProjectStatus.RETRIEVED
    project.updated_at = utcnow()
    repo.save_project(project)
    return final, run


def retrieve_references_versioned(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    embedder: EmbeddingClient | JointEmbeddingClient,
    versioned_store: VersionedVectorStore,
    project: ProjectRecord,
    experiment_id: str | None = None,
    index_version_id: str | None = None,
    persist_run: bool = True,
) -> tuple[list[RetrievedReference], RetrievalRunRecord]:
    experiment = (
        repo.get_retrieval_experiment(experiment_id)
        if experiment_id
        else ensure_default_retrieval_experiment(repo)
    )
    if experiment is None:
        raise EmptyRetrievalError("No retrieval experiment configured")
    reranker_model = ensure_default_reranker_model(repo)
    config = json.loads(experiment.config_json)
    candidate_k = int(config.get("candidate_k", 30))
    rerank_k = int(config.get("rerank_k", 12))
    final_k = int(config.get("final_k", settings.retrieval.final_k))

    query = _build_query_input(project)
    room_path = settings.resolve(project.room_image_path)
    room_emb = embedder.embed_image(room_path)
    text_query = " ".join(
        [project.brief, project.room_type, project.style_family or "", project.budget_band or ""]
        + project.constraints
    )
    text_emb = embedder.embed_text(text_query)

    if isinstance(embedder, JointEmbeddingClient):
        embedder.assert_compatible(room_emb)
        embedder.assert_compatible(text_emb)

    image_hits = versioned_store.search_image(room_emb, top_k=candidate_k)
    text_hits = versioned_store.search_text(text_emb, top_k=candidate_k)
    image_ranking = [ref.image_id for ref, _ in image_hits]
    text_ranking = [ref.image_id for ref, _ in text_hits]
    fusion_scores = reciprocal_rank_fusion(
        {"image": image_ranking, "text": text_ranking},
        k=60,
    )

    image_sim_map = {ref.image_id: score for ref, score in image_hits}
    text_sim_map = {ref.image_id: score for ref, score in text_hits}
    indexed_by_image = versioned_store.membership_by_image_id

    run_id = new_id("ret")
    now = utcnow()
    space_id = versioned_store.index_version.embedding_space_id
    index_version_id = index_version_id or versioned_store.index_version.vector_index_version_id
    room_upload = repo.get_room_upload(project.project_id)

    if persist_run:
        repo.save_retrieval_run_extended(
            run_id=run_id,
            project_id=project.project_id,
            mode=GenerationMode.CURATED.value,
            query_text=project.brief,
            top_k=candidate_k,
            final_k=final_k,
            reference_ids=[],
            scores_json=[],
            dataset_version=index_version_id,
            retrieval_experiment_id=experiment.retrieval_experiment_id,
            vector_index_version_id=index_version_id,
            created_at=now,
        )
        repo.save_retrieval_query_artifact(
            RetrievalQueryArtifact(
                retrieval_query_artifact_id=new_id("rqa"),
                retrieval_run_id=run_id,
                upload_id=room_upload.upload_id if room_upload else None,
                embedding_space_id=space_id,
                modality=EmbeddingModality.IMAGE,
                query_sha256=sha256_text(str(room_path)),
                created_at=now,
            )
        )
        repo.save_retrieval_query_artifact(
            RetrievalQueryArtifact(
                retrieval_query_artifact_id=new_id("rqa"),
                retrieval_run_id=run_id,
                upload_id=None,
                embedding_space_id=space_id,
                modality=EmbeddingModality.TEXT,
                query_sha256=sha256_text(text_query),
                created_at=now,
            )
        )

    candidate_rows: list[tuple[RetrievalCandidate, IndexedReference, dict[str, float]]] = []
    reranker = DeterministicMultimodalReranker()

    for rank, image_id in enumerate(
        sorted(fusion_scores, key=lambda k: fusion_scores[k], reverse=True), start=1
    ):
        indexed = indexed_by_image.get(image_id)
        if indexed is None:
            continue
        record = indexed.record
        passed = passes_hard_filters(query, record)
        filter_reason = None if passed else "failed_hard_filter"
        candidate_id = new_id("rcand")
        candidate = RetrievalCandidate(
            retrieval_candidate_id=candidate_id,
            retrieval_run_id=run_id,
            snapshot_reference_record_id=indexed.snapshot_reference_record_id,
            image_id=image_id,
            initial_rank=rank,
            passed_hard_filters=passed,
            filter_reason=filter_reason,
            selected_for_rerank=False,
            selected_final=False,
            created_at=now,
        )
        image_sim = float(image_sim_map.get(image_id, 0.0))
        text_sim = float(text_sim_map.get(image_id, 0.0))
        meta = metadata_match_score(query, record)
        fusion = float(fusion_scores.get(image_id, 0.0))
        scores = {
            "image_sim": image_sim,
            "text_sim": text_sim,
            "metadata": meta,
            "fusion": fusion,
        }
        candidate_rows.append((candidate, indexed, scores))

        if persist_run:
            repo.save_retrieval_candidate(candidate)
            for stage, name, value in (
                (RetrievalScoreStage.VECTOR_IMAGE, "cosine", image_sim),
                (RetrievalScoreStage.VECTOR_TEXT, "cosine", text_sim),
                (RetrievalScoreStage.METADATA, "metadata_match", meta),
                (RetrievalScoreStage.FUSION, "rrf", fusion),
            ):
                repo.save_retrieval_candidate_score(
                    RetrievalCandidateScore(
                        retrieval_candidate_score_id=new_id("rscore"),
                        retrieval_candidate_id=candidate_id,
                        reranker_model_version_id=None,
                        stage=stage,
                        score_name=name,
                        raw_score=value,
                        normalised_score=max(0.0, min(1.0, value)),
                        created_at=now,
                    )
                )

    filtered = [
        (cand, idx, scores)
        for cand, idx, scores in candidate_rows
        if cand.passed_hard_filters
    ]
    rerank_scored: list[tuple[RetrievalCandidate, IndexedReference, float, dict[str, float]]] = []
    for cand, indexed, scores in filtered[:rerank_k]:
        cand.selected_for_rerank = True
        rerank_score = reranker.score(
            query=query,
            record=indexed.record,
            image_similarity=scores["image_sim"],
            text_similarity=scores["text_sim"],
            fusion_score=scores["fusion"],
        )
        rerank_scored.append((cand, indexed, rerank_score, scores))
        if persist_run:
            repo.save_retrieval_candidate(cand)
            repo.save_retrieval_candidate_score(
                RetrievalCandidateScore(
                    retrieval_candidate_score_id=new_id("rscore"),
                    retrieval_candidate_id=cand.retrieval_candidate_id,
                    reranker_model_version_id=reranker_model.reranker_model_version_id,
                    stage=RetrievalScoreStage.MULTIMODAL_RERANKER,
                    score_name="deterministic_multimodal",
                    raw_score=rerank_score,
                    normalised_score=max(0.0, min(1.0, rerank_score)),
                    created_at=now,
                )
            )

    rerank_scored.sort(key=lambda item: item[2], reverse=True)
    retrieved_candidates: list[RetrievedReference] = []
    for cand, indexed, rerank_score, scores in rerank_scored:
        record = indexed.record
        retrieved_candidates.append(
            RetrievedReference(
                image_id=record.image_id,
                image_path=record.image_path,
                score=rerank_score,
                image_similarity=scores["image_sim"],
                text_similarity=scores["text_sim"],
                metadata_match=scores["metadata"],
                architect_quality=record.architect_quality_score,
                match_rationale=build_match_rationale(
                    image_similarity=scores["image_sim"],
                    text_similarity=scores["text_sim"],
                    metadata_match=scores["metadata"],
                    architect_quality=record.architect_quality_score,
                    record=record,
                ),
                record=record,
            )
        )

    final_refs = diversify_references(retrieved_candidates, final_k=final_k)
    if not final_refs:
        raise EmptyRetrievalError("No curated references matched filters")

    final_by_image = {r.image_id: r for r in final_refs}
    for cand, indexed, _, _ in rerank_scored:
        if indexed.image_id in final_by_image:
            cand.selected_final = True
            if persist_run:
                repo.save_retrieval_candidate(cand)

    run = RetrievalRunRecord(
        run_id=run_id,
        project_id=project.project_id,
        mode=GenerationMode.CURATED,
        query_text=project.brief,
        top_k=candidate_k,
        final_k=final_k,
        reference_ids=[r.image_id for r in final_refs],
        scores_json=[
            {
                "image_id": r.image_id,
                "score": r.score,
                "retrieval_candidate_id": next(
                    c.retrieval_candidate_id
                    for c, idx, _, _ in rerank_scored
                    if idx.image_id == r.image_id
                ),
                "image_similarity": r.image_similarity,
                "text_similarity": r.text_similarity,
                "metadata_match": r.metadata_match,
                "architect_quality": r.architect_quality,
                "diversity_role": r.diversity_role,
                "match_rationale": r.match_rationale,
            }
            for r in final_refs
        ],
        dataset_version=index_version_id,
        created_at=now,
    )

    if persist_run:
        repo.save_retrieval_run_extended(
            run_id=run.run_id,
            project_id=run.project_id,
            mode=run.mode.value,
            query_text=run.query_text,
            top_k=run.top_k,
            final_k=run.final_k,
            reference_ids=run.reference_ids,
            scores_json=run.scores_json,
            dataset_version=run.dataset_version,
            retrieval_experiment_id=experiment.retrieval_experiment_id,
            vector_index_version_id=index_version_id,
            created_at=run.created_at,
            references=[
                {
                    "image_id": r.image_id,
                    "score": r.score,
                    "diversity_role": r.diversity_role,
                    "retrieval_candidate_id": item["retrieval_candidate_id"],
                }
                for r, item in zip(final_refs, run.scores_json)
            ],
        )
        project.status = ProjectStatus.RETRIEVED
        project.updated_at = utcnow()
        repo.save_project(project)

    return final_refs, run


def retrieve_references(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    embedder: EmbeddingClient,
    store: NumpyVectorStore,
    project: ProjectRecord,
    mode: GenerationMode = GenerationMode.CURATED,
    versioned_store: VersionedVectorStore | None = None,
) -> tuple[list[RetrievedReference], RetrievalRunRecord]:
    if mode == GenerationMode.BASELINE:
        run = RetrievalRunRecord(
            run_id=new_id("ret"),
            project_id=project.project_id,
            mode=mode,
            query_text=project.brief,
            top_k=0,
            final_k=0,
            reference_ids=[],
            scores_json=[],
            dataset_version=None,
            created_at=utcnow(),
        )
        experiment = ensure_default_retrieval_experiment(repo)
        repo.save_retrieval_run_extended(
            run_id=run.run_id,
            project_id=run.project_id,
            mode=run.mode.value,
            query_text=run.query_text,
            top_k=0,
            final_k=0,
            reference_ids=[],
            scores_json=[],
            dataset_version=None,
            retrieval_experiment_id=experiment.retrieval_experiment_id,
            vector_index_version_id=None,
            created_at=run.created_at,
        )
        return [], run

    if versioned_store is not None:
        from vision_engine.infrastructure.embedding_clients.joint import build_joint_embedding_client

        joint = build_joint_embedding_client(
            provider=settings.embedding_provider,
            model_name=settings.embedding_model_name,
        )
        return retrieve_references_versioned(
            repo=repo,
            settings=settings,
            embedder=joint,
            versioned_store=versioned_store,
            project=project,
        )

    if not store.records:
        raise EmptyRetrievalError("Curated index is empty — run build-index first")

    return _legacy_retrieve(
        repo=repo,
        settings=settings,
        embedder=embedder,
        store=store,
        project=project,
        mode=mode,
    )

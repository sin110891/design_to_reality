from __future__ import annotations

from vision_engine.application.build_index import load_index
from vision_engine.application.versioned_index_build import load_active_versioned_index
from vision_engine.application.benchmark_cases import create_benchmark_case_from_results
from vision_engine.application.create_project import create_project
from vision_engine.application.generate_concept import generate_concept
from vision_engine.application.generate_variants import generate_variants
from vision_engine.application.retrieve_references import retrieve_references
from vision_engine.domain.enums import GenerationMode
from vision_engine.domain.models import PipelineResult, ProjectInput
from vision_engine.infrastructure.embedding_clients import build_embedding_client
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.infrastructure.vector_store import NumpyVectorStore
from vision_engine.settings import AppSettings


def run_pipeline(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore,
    payload: ProjectInput,
    mode: GenerationMode = GenerationMode.CURATED,
    skip_image_edit: bool = False,
) -> PipelineResult:
    """Full flow: create → retrieve → concept → variants."""
    warnings: list[str] = []
    project = create_project(
        repo=repo, settings=settings, file_store=file_store, payload=payload
    )

    embedder = build_embedding_client(
        provider=settings.embedding_provider,
        api_key=settings.gemini_api_key,
        model_name=settings.embedding_model_name,
    )

    versioned_store = None
    store = NumpyVectorStore()
    if mode == GenerationMode.CURATED:
        versioned_store = load_active_versioned_index(repo=repo, settings=settings)
        if versioned_store is None:
            store = load_index(settings)

    references, retrieval_run = retrieve_references(
        repo=repo,
        settings=settings,
        embedder=embedder,
        store=store,
        project=project,
        mode=mode,
        versioned_store=versioned_store,
    )
    if mode == GenerationMode.BASELINE:
        warnings.append("Baseline mode: no curated references used")

    direction, concept_run = generate_concept(
        repo=repo,
        settings=settings,
        file_store=file_store,
        project=project,
        references=references,
        retrieval_run_id=retrieval_run.run_id,
        mode=mode,
    )

    variants = []
    generation_run_id = None
    if not skip_image_edit:
        variants, gen_run = generate_variants(
            repo=repo,
            settings=settings,
            file_store=file_store,
            project=project,
            direction=direction,
            references=references,
            concept_run_id=concept_run.run_id,
            mode=mode,
        )
        generation_run_id = gen_run.run_id
    else:
        warnings.append("Skipped image editing")

    project = repo.get_project(project.project_id) or project
    return PipelineResult(
        project=project,
        references=references,
        design_direction=direction,
        variants=variants,
        mode=mode,
        concept_run_id=concept_run.run_id,
        generation_run_id=generation_run_id,
        retrieval_run_id=retrieval_run.run_id,
        warnings=warnings,
        disclaimer=settings.generation.concept_disclaimer,
    )


def run_baseline_vs_curated(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore,
    payload: ProjectInput,
    skip_image_edit: bool = False,
) -> dict[str, PipelineResult]:
    """Run both modes for evaluation comparison."""
    curated = run_pipeline(
        repo=repo,
        settings=settings,
        file_store=file_store,
        payload=payload,
        mode=GenerationMode.CURATED,
        skip_image_edit=skip_image_edit,
    )
    baseline = run_pipeline(
        repo=repo,
        settings=settings,
        file_store=file_store,
        payload=payload,
        mode=GenerationMode.BASELINE,
        skip_image_edit=skip_image_edit,
    )
    room_upload = repo.get_room_upload(curated.project.project_id) or repo.get_room_upload(
        baseline.project.project_id
    )
    if room_upload and curated.generation_run_id and baseline.generation_run_id:
        create_benchmark_case_from_results(
            repo=repo,
            canonical_input_sha256=room_upload.sha256,
            canonical_brief=payload.brief,
            results={"curated": curated, "baseline": baseline},
        )
    return {"curated": curated, "baseline": baseline}

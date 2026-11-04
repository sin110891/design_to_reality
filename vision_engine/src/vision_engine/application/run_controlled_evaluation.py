from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

from vision_engine.application.evaluation_spec import case_to_project_input, load_evaluation_spec
from vision_engine.application.run_pipeline import run_pipeline
from vision_engine.domain.enums import (
    BenchmarkArm,
    EvaluationArmStatus,
    EvaluationCaseStatus,
    EvaluationRunStatus,
    GenerationMode,
)
from vision_engine.domain.evaluation_models import (
    EvaluationCase,
    EvaluationCaseArm,
    EvaluationRun,
    EvaluationRunSummary,
    EvaluationSpec,
)
from vision_engine.domain.models import PipelineResult, ProjectInput
from vision_engine.infrastructure.file_store import FileStore, new_id
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ArmJob:
    evaluation_case_arm_id: str
    evaluation_case_id: str
    arm: BenchmarkArm
    payload: ProjectInput


def _arm_mode(arm: BenchmarkArm) -> GenerationMode:
    if arm == BenchmarkArm.CURATED:
        return GenerationMode.CURATED
    if arm == BenchmarkArm.BASELINE:
        return GenerationMode.BASELINE
    raise ValueError(f"Unsupported evaluation arm: {arm}")


def _public_case_id(sequence: int) -> str:
    return f"case_{sequence:04d}"


def _rollup_case_status(
    *,
    arms: list[EvaluationCaseArm],
    expected_variants: int,
    repo: SqliteRepository,
) -> EvaluationCaseStatus:
    if not arms:
        return EvaluationCaseStatus.FAILED
    statuses = {arm.status for arm in arms}
    if EvaluationArmStatus.FAILED in statuses:
        if any(a.status == EvaluationArmStatus.COMPLETE for a in arms):
            return EvaluationCaseStatus.PARTIAL
        return EvaluationCaseStatus.FAILED
    if all(a.status == EvaluationArmStatus.COMPLETE for a in arms):
        for arm in arms:
            if not arm.generation_run_id:
                return EvaluationCaseStatus.PARTIAL
            variants = repo.list_variants_for_generation(arm.generation_run_id)
            if len(variants) < expected_variants:
                return EvaluationCaseStatus.PARTIAL
        return EvaluationCaseStatus.COMPLETE
    if EvaluationArmStatus.RUNNING in statuses:
        return EvaluationCaseStatus.RUNNING
    return EvaluationCaseStatus.PARTIAL


def _rollup_run_status(cases: list[EvaluationCase]) -> EvaluationRunStatus:
    if not cases:
        return EvaluationRunStatus.FAILED
    statuses = {case.status for case in cases}
    if statuses == {EvaluationCaseStatus.COMPLETE}:
        return EvaluationRunStatus.COMPLETED
    if EvaluationCaseStatus.COMPLETE in statuses:
        return EvaluationRunStatus.PARTIAL
    if EvaluationCaseStatus.FAILED in statuses and len(statuses) == 1:
        return EvaluationRunStatus.FAILED
    return EvaluationRunStatus.PARTIAL


def _execute_arm_job(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore,
    job: ArmJob,
    skip_image_edit: bool,
) -> tuple[str, EvaluationArmStatus, str | None, str | None, str | None]:
    started = utcnow()
    repo.save_evaluation_case_arm(
        EvaluationCaseArm(
            evaluation_case_arm_id=job.evaluation_case_arm_id,
            evaluation_case_id=job.evaluation_case_id,
            arm=job.arm,
            project_id=None,
            generation_run_id=None,
            status=EvaluationArmStatus.RUNNING,
            started_at=started,
            completed_at=None,
        )
    )
    try:
        result = run_pipeline(
            repo=repo,
            settings=settings,
            file_store=file_store,
            payload=job.payload,
            mode=_arm_mode(job.arm),
            skip_image_edit=skip_image_edit,
        )
        if not result.generation_run_id:
            raise RuntimeError("Generation run missing after pipeline")
        expected = settings.generation.variant_count
        if len(result.variants) < expected:
            raise RuntimeError(
                f"Expected {expected} variants, got {len(result.variants)} for arm {job.arm.value}"
            )
        repo.save_evaluation_case_arm(
            EvaluationCaseArm(
                evaluation_case_arm_id=job.evaluation_case_arm_id,
                evaluation_case_id=job.evaluation_case_id,
                arm=job.arm,
                project_id=result.project.project_id,
                generation_run_id=result.generation_run_id,
                status=EvaluationArmStatus.COMPLETE,
                started_at=started,
                completed_at=utcnow(),
            )
        )
        return (
            job.evaluation_case_arm_id,
            EvaluationArmStatus.COMPLETE,
            result.project.project_id,
            result.generation_run_id,
            None,
        )
    except Exception as exc:  # noqa: BLE001
        repo.save_evaluation_case_arm(
            EvaluationCaseArm(
                evaluation_case_arm_id=job.evaluation_case_arm_id,
                evaluation_case_id=job.evaluation_case_id,
                arm=job.arm,
                project_id=None,
                generation_run_id=None,
                status=EvaluationArmStatus.FAILED,
                error_message=str(exc),
                started_at=started,
                completed_at=utcnow(),
            )
        )
        return (job.evaluation_case_arm_id, EvaluationArmStatus.FAILED, None, None, str(exc))


def run_controlled_evaluation(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore,
    config_path,
    repetitions: int | None = None,
    workers: int = 4,
    skip_image_edit: bool = False,
) -> tuple[EvaluationRunSummary, EvaluationSpec]:
    spec = load_evaluation_spec(
        settings=settings,
        config_path=config_path,
        repetitions_override=repetitions,
    )
    run_id = new_id("eval")
    now = utcnow()
    repo.save_evaluation_run(
        EvaluationRun(
            evaluation_run_id=run_id,
            spec_sha256=spec.spec_sha256,
            spec_json={
                "name": spec.name,
                "repetitions": spec.repetitions,
                "full_output_dir": spec.full_output_dir,
                "blind_output_dir": spec.blind_output_dir,
                "cases": [c.model_dump(mode="json") for c in spec.case_specs],
            },
            requested_repetitions=spec.repetitions,
            status=EvaluationRunStatus.PLANNED,
            created_at=now,
            completed_at=None,
        )
    )
    repo.update_evaluation_run_status(run_id, EvaluationRunStatus.RUNNING)

    jobs: list[ArmJob] = []
    case_rows: list[EvaluationCase] = []
    sequence = 1
    for canonical in spec.case_specs:
        for replicate_index in range(1, spec.repetitions + 1):
            case_id = new_id("ecase")
            public_case_id = _public_case_id(sequence)
            sequence += 1
            case = EvaluationCase(
                evaluation_case_id=case_id,
                evaluation_run_id=run_id,
                case_input_sha256=canonical.case_input_sha256,
                replicate_index=replicate_index,
                public_case_id=public_case_id,
                input_spec_json=canonical.model_dump(mode="json"),
                status=EvaluationCaseStatus.PLANNED,
                created_at=now,
            )
            repo.save_evaluation_case(case)
            case_rows.append(case)
            payload = case_to_project_input(canonical)
            for arm in (BenchmarkArm.CURATED, BenchmarkArm.BASELINE):
                arm_id = new_id("ecarm")
                repo.save_evaluation_case_arm(
                    EvaluationCaseArm(
                        evaluation_case_arm_id=arm_id,
                        evaluation_case_id=case_id,
                        arm=arm,
                        project_id=None,
                        generation_run_id=None,
                        status=EvaluationArmStatus.PLANNED,
                    )
                )
                jobs.append(
                    ArmJob(
                        evaluation_case_arm_id=arm_id,
                        evaluation_case_id=case_id,
                        arm=arm,
                        payload=payload,
                    )
                )

    worker_count = max(1, min(workers, len(jobs)))
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = [
            pool.submit(
                _execute_arm_job,
                repo=repo,
                settings=settings,
                file_store=file_store,
                job=job,
                skip_image_edit=skip_image_edit,
            )
            for job in jobs
        ]
        for future in as_completed(futures):
            future.result()

    updated_cases: list[EvaluationCase] = []
    for case in case_rows:
        arms = repo.list_evaluation_case_arms(case.evaluation_case_id)
        status = _rollup_case_status(
            arms=arms,
            expected_variants=settings.generation.variant_count,
            repo=repo,
        )
        repo.update_evaluation_case_status(case.evaluation_case_id, status)
        updated_cases.append(
            EvaluationCase(
                **{**case.model_dump(), "status": status},
            )
        )

    run_status = _rollup_run_status(updated_cases)
    completed_at = utcnow()
    repo.update_evaluation_run_status(run_id, run_status, completed_at=completed_at)

    summary = EvaluationRunSummary(
        evaluation_run_id=run_id,
        status=run_status,
        total_cases=len(updated_cases),
        complete_cases=sum(
            1 for case in updated_cases if case.status == EvaluationCaseStatus.COMPLETE
        ),
        partial_cases=sum(
            1 for case in updated_cases if case.status == EvaluationCaseStatus.PARTIAL
        ),
        failed_cases=sum(
            1 for case in updated_cases if case.status == EvaluationCaseStatus.FAILED
        ),
    )
    return summary, spec

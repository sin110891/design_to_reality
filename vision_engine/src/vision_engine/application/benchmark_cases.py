from __future__ import annotations

from datetime import datetime, timezone

from vision_engine.domain.enums import BenchmarkArm, GenerationMode
from vision_engine.domain.models import BenchmarkCase, BenchmarkCaseProject, PipelineResult
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import SqliteRepository


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_benchmark_case_from_results(
    *,
    repo: SqliteRepository,
    canonical_input_sha256: str,
    canonical_brief: str,
    results: dict[str, PipelineResult],
) -> BenchmarkCase:
    case = BenchmarkCase(
        benchmark_case_id=new_id("bench"),
        canonical_input_sha256=canonical_input_sha256,
        canonical_brief=canonical_brief,
        status="active",
        created_at=utcnow(),
    )
    repo.save_benchmark_case(case)

    arm_map = {
        "curated": BenchmarkArm.CURATED,
        "baseline": BenchmarkArm.BASELINE,
    }
    for name, result in results.items():
        if not result.generation_run_id:
            continue
        arm = arm_map.get(name)
        if arm is None:
            if result.mode == GenerationMode.CURATED:
                arm = BenchmarkArm.CURATED
            elif result.mode == GenerationMode.BASELINE:
                arm = BenchmarkArm.BASELINE
            else:
                continue
        repo.save_benchmark_case_project(
            BenchmarkCaseProject(
                benchmark_case_project_id=new_id("bcp"),
                benchmark_case_id=case.benchmark_case_id,
                project_id=result.project.project_id,
                generation_run_id=result.generation_run_id,
                arm=arm,
            )
        )
    return case

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from vision_engine.domain.enums import BenchmarkArm, EvaluationArmStatus, EvaluationCaseStatus
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


def _complete_cases(repo: SqliteRepository, evaluation_run_id: str, settings: AppSettings):
    cases = repo.list_evaluation_cases(evaluation_run_id)
    complete = []
    for case in cases:
        if case.status != EvaluationCaseStatus.COMPLETE:
            continue
        arms = repo.list_evaluation_case_arms(case.evaluation_case_id)
        curated = next((a for a in arms if a.arm == BenchmarkArm.CURATED), None)
        baseline = next((a for a in arms if a.arm == BenchmarkArm.BASELINE), None)
        if (
            curated is None
            or baseline is None
            or curated.status != EvaluationArmStatus.COMPLETE
            or baseline.status != EvaluationArmStatus.COMPLETE
        ):
            continue
        curated_variants = repo.list_variants_for_generation(curated.generation_run_id or "")
        baseline_variants = repo.list_variants_for_generation(baseline.generation_run_id or "")
        if (
            len(curated_variants) < settings.generation.variant_count
            or len(baseline_variants) < settings.generation.variant_count
        ):
            continue
        complete.append((case, curated, baseline, curated_variants, baseline_variants))
    return complete


def build_evaluation_report(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    evaluation_run_id: str,
) -> dict[str, Any]:
    run = repo.get_evaluation_run(evaluation_run_id)
    if run is None:
        raise ValueError(f"Evaluation run not found: {evaluation_run_id}")

    cases = repo.list_evaluation_cases(evaluation_run_id)
    complete = _complete_cases(repo, evaluation_run_id, settings)
    rows: list[dict[str, Any]] = []
    for case, curated, baseline, curated_variants, baseline_variants in complete:
        rows.append(
            {
                "evaluation_case_id": case.evaluation_case_id,
                "public_case_id": case.public_case_id,
                "replicate_index": case.replicate_index,
                "case_input_sha256": case.case_input_sha256,
                "curated_project_id": curated.project_id,
                "baseline_project_id": baseline.project_id,
                "curated_generation_run_id": curated.generation_run_id,
                "baseline_generation_run_id": baseline.generation_run_id,
                "curated_variants": [
                    {
                        "variant_id": v.variant_id,
                        "kind": v.kind.value,
                        "image_path": v.image_path,
                    }
                    for v in curated_variants
                ],
                "baseline_variants": [
                    {
                        "variant_id": v.variant_id,
                        "kind": v.kind.value,
                        "image_path": v.image_path,
                    }
                    for v in baseline_variants
                ],
            }
        )

    return {
        "evaluation_run_id": evaluation_run_id,
        "status": run.status.value,
        "spec_sha256": run.spec_sha256,
        "requested_repetitions": run.requested_repetitions,
        "total_cases": len(cases),
        "complete_pairs": len(complete),
        "partial_or_failed_cases": len(cases) - len(complete),
        "cases": rows,
    }


def write_evaluation_report(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    evaluation_run_id: str,
    output_dir: Path | None = None,
) -> tuple[dict[str, Any], Path | None]:
    report = build_evaluation_report(
        repo=repo,
        settings=settings,
        evaluation_run_id=evaluation_run_id,
    )
    if output_dir is None:
        return report, None

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    csv_path = output_dir / "report.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "public_case_id",
                "replicate_index",
                "curated_project_id",
                "baseline_project_id",
                "curated_generation_run_id",
                "baseline_generation_run_id",
            ],
        )
        writer.writeheader()
        for row in report["cases"]:
            writer.writerow(
                {
                    "public_case_id": row["public_case_id"],
                    "replicate_index": row["replicate_index"],
                    "curated_project_id": row["curated_project_id"],
                    "baseline_project_id": row["baseline_project_id"],
                    "curated_generation_run_id": row["curated_generation_run_id"],
                    "baseline_generation_run_id": row["baseline_generation_run_id"],
                }
            )
    return report, output_dir

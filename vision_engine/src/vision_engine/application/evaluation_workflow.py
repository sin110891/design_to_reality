from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from vision_engine.application.blind_evaluation_export import export_blind_evaluation
from vision_engine.application.evaluation_export import export_full_evaluation
from vision_engine.application.evaluation_import_selections import (
    import_evaluation_selections,
    write_selection_report,
)
from vision_engine.application.run_controlled_evaluation import run_controlled_evaluation
from vision_engine.domain.enums import EvaluationExportType
from vision_engine.domain.evaluation_models import EvaluationExport, EvaluationRunSummary
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


@dataclass(frozen=True)
class EvaluationPackage:
    summary: EvaluationRunSummary
    full_export: EvaluationExport
    full_directory: Path
    blind_export: EvaluationExport
    blind_directory: Path


@dataclass(frozen=True)
class EvaluationScore:
    evaluation_export_id: str
    evaluation_run_id: str
    report: dict[str, object]
    report_path: Path


def _resolved_base(settings: AppSettings, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else settings.resolve(path)


def create_evaluation_package(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore,
    config_path: Path,
    repetitions: int | None = None,
    workers: int = 4,
    seed: int | None = None,
) -> EvaluationPackage:
    """Run, report, and export a controlled evaluation in one process."""
    summary, spec = run_controlled_evaluation(
        repo=repo,
        settings=settings,
        file_store=file_store,
        config_path=config_path,
        repetitions=repetitions,
        workers=workers,
    )

    full_base = _resolved_base(settings, spec.full_output_dir)
    full_export, full_directory = export_full_evaluation(
        repo=repo,
        settings=settings,
        evaluation_run_id=summary.evaluation_run_id,
        output_dir=full_base / summary.evaluation_run_id,
    )
    if summary.complete_cases == 0:
        raise RuntimeError(
            "Evaluation created no complete curated/baseline pairs; "
            f"full diagnostics are available at {full_directory}"
        )

    blind_base = _resolved_base(settings, spec.blind_output_dir)
    blind_export, blind_directory = export_blind_evaluation(
        repo=repo,
        settings=settings,
        evaluation_run_id=summary.evaluation_run_id,
        output_dir=blind_base,
        seed=seed,
    )
    return EvaluationPackage(
        summary=summary,
        full_export=full_export,
        full_directory=full_directory,
        blind_export=blind_export,
        blind_directory=blind_directory,
    )


def score_blind_evaluation(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    evaluation_export_id: str,
    csv_path: Path,
    evaluator_id: str = "default",
    output_path: Path | None = None,
) -> EvaluationScore:
    """Import evaluator selections and write the result internally by default."""
    blind_export = repo.get_evaluation_export(evaluation_export_id)
    if blind_export is None or blind_export.export_type != EvaluationExportType.BLIND:
        raise ValueError(f"Blind evaluation export not found: {evaluation_export_id}")

    _selections, report = import_evaluation_selections(
        repo=repo,
        evaluation_export_id=evaluation_export_id,
        csv_path=csv_path,
        evaluator_id=evaluator_id,
    )
    if output_path is None:
        full_exports = repo.list_evaluation_exports(
            blind_export.evaluation_run_id,
            export_type=EvaluationExportType.FULL,
        )
        base = (
            Path(full_exports[0].output_directory)
            if full_exports
            else settings.paths.evaluations / blind_export.evaluation_run_id
        )
        safe_evaluator = re.sub(r"[^A-Za-z0-9_.-]+", "_", evaluator_id)
        output_path = (
            base
            / "selection_reports"
            / f"{evaluation_export_id}_{safe_evaluator}.json"
        )
    else:
        output_path = (
            output_path if output_path.is_absolute() else settings.resolve(output_path)
        )
    report_path = write_selection_report(report, output_path)
    return EvaluationScore(
        evaluation_export_id=evaluation_export_id,
        evaluation_run_id=blind_export.evaluation_run_id,
        report=report,
        report_path=report_path,
    )

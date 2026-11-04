from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from vision_engine.application.build_index import build_index
from vision_engine.application.build_retrieval_index import build_versioned_retrieval_index
from vision_engine.application.blind_evaluation_export import export_blind_evaluation
from vision_engine.application.evaluation_export import export_full_evaluation
from vision_engine.application.evaluation_import_selections import (
    import_evaluation_selections,
    write_selection_report,
)
from vision_engine.application.evaluation_report import write_evaluation_report
from vision_engine.application.evaluation_workflow import (
    create_evaluation_package,
    score_blind_evaluation,
)
from vision_engine.application.index_promotion import promote_index_version
from vision_engine.application.run_controlled_evaluation import run_controlled_evaluation
from vision_engine.application.export_feedback import export_feedback_dataset
from vision_engine.application.export_review_training import (
    export_approved_concepts,
    export_review_training_dataset,
)
from vision_engine.application.record_feedback import record_feedback
from vision_engine.application.review_feedback import promote_approved_concept, save_generation_review
from vision_engine.application.run_pipeline import run_baseline_vs_curated, run_pipeline
from vision_engine.domain.enums import GenerationMode, GenerationReviewSetStatus, RetentionConsentStatus
from vision_engine.domain.models import GenerationReviewSetInput, ProjectInput, VariantReviewInput
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import clear_settings_cache, get_settings

app = typer.Typer(
    name="vision-engine",
    help="Curated retrieval + room redesign concept prototype",
    no_args_is_help=True,
)
console = Console()


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _boot() -> tuple[SqliteRepository, object, FileStore]:
    clear_settings_cache()
    settings = get_settings()
    _configure_logging(settings.log_level)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )
    return repo, settings, file_store


@app.command("init-db")
def init_db() -> None:
    """Create SQLite tables."""
    repo, settings, _ = _boot()
    console.print(f"[green]Initialized database[/green] at {settings.database_path}")


@app.command("build-index")
def build_index_cmd(
    metadata: Optional[Path] = typer.Option(
        None, "--metadata", help="Curated metadata CSV (vision-engine format)"
    ),
    gold: Optional[Path] = typer.Option(
        None, "--gold", help="dataset_factory gold JSONL export"
    ),
    images: Optional[Path] = typer.Option(
        None, "--images", help="Directory of curated reference images"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Index output path (.npz)"
    ),
) -> None:
    """Ingest approved curated records and build the local NumPy vector index."""
    repo, settings, _ = _boot()
    try:
        path, count = build_index(
            repo=repo,
            settings=settings,
            metadata=metadata,
            gold_jsonl=gold,
            images_dir=images,
            output=output,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Index build failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Indexed {count} approved records[/green] → {path}")


@app.command("build-retrieval-index")
def build_retrieval_index_cmd(
    metadata: Optional[Path] = typer.Option(None, "--metadata"),
    gold: Optional[Path] = typer.Option(None, "--gold"),
    images: Optional[Path] = typer.Option(None, "--images"),
    snapshot_name: str = typer.Option("curated-v1", "--snapshot-name"),
    no_promote: bool = typer.Option(False, "--no-promote"),
) -> None:
    """Build sealed snapshot, embeddings, and versioned retrieval index."""
    repo, settings, _ = _boot()
    try:
        index, count = build_versioned_retrieval_index(
            repo=repo,
            settings=settings,
            metadata=metadata,
            gold_jsonl=gold,
            images_dir=images,
            snapshot_name=snapshot_name,
            promote=not no_promote,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Versioned index build failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Built index[/green] {index.vector_index_version_id} "
        f"({count} records, status={index.status.value})"
    )


@app.command("promote-index")
def promote_index_cmd(
    index_id: str = typer.Option(..., "--index-id"),
    environment: Optional[str] = typer.Option(None, "--environment"),
) -> None:
    """Promote a validated index version to the active alias."""
    repo, settings, _ = _boot()
    alias = promote_index_version(
        repo=repo,
        vector_index_version_id=index_id,
        environment=environment or settings.app_env,
    )
    console.print(
        f"[green]Promoted[/green] {index_id} → alias {alias.active_index_alias} "
        f"({alias.environment})"
    )


@app.command("active-index")
def active_index_cmd() -> None:
    """Show the active retrieval index for this environment."""
    repo, settings, _ = _boot()
    index = repo.get_active_index_for_environment(settings.app_env)
    if index is None:
        console.print("[yellow]No active versioned index[/yellow] — using legacy npz if present")
        raise typer.Exit(code=0)
    table = Table(title=f"Active index ({settings.app_env})")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("vector_index_version_id", index.vector_index_version_id)
    table.add_row("dataset_snapshot_id", index.dataset_snapshot_id)
    table.add_row("embedding_space_id", index.embedding_space_id)
    table.add_row("vector_count", str(index.vector_count))
    table.add_row("status", index.status.value)
    table.add_row("index_uri", index.index_uri)
    console.print(table)


@app.command("run")
def run_cmd(
    room: Path = typer.Option(..., "--room", help="Room image path"),
    brief: str = typer.Option(..., "--brief", help="Short design brief"),
    room_type: str = typer.Option("living_room", "--room-type"),
    style_family: str = typer.Option("Contemporary Europe", "--style-family"),
    budget_band: Optional[str] = typer.Option(None, "--budget-band"),
    inspiration: Optional[list[Path]] = typer.Option(
        None, "--inspiration", help="Optional inspiration image(s)"
    ),
    constraint: Optional[list[str]] = typer.Option(
        None, "--constraint", help="Repeatable constraint"
    ),
    mode: str = typer.Option("curated", "--mode", help="curated | baseline"),
    skip_images: bool = typer.Option(
        False, "--skip-images", help="Stop after concept JSON (no image edit)"
    ),
) -> None:
    """Run the full redesign pipeline for one room."""
    repo, settings, file_store = _boot()
    try:
        gen_mode = GenerationMode(mode)
    except ValueError as exc:
        console.print(f"[red]Invalid mode:[/red] {mode}")
        raise typer.Exit(code=1) from exc

    payload = ProjectInput(
        room_image_path=str(room if room.is_absolute() else settings.resolve(room)),
        inspiration_image_paths=[
            str(p if p.is_absolute() else settings.resolve(p)) for p in (inspiration or [])
        ],
        room_type=room_type,
        style_family=style_family,
        brief=brief,
        budget_band=budget_band,
        constraints=list(constraint or []),
    )
    try:
        result = run_pipeline(
            repo=repo,
            settings=settings,
            file_store=file_store,
            payload=payload,
            mode=gen_mode,
            skip_image_edit=skip_images,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Pipeline failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Pipeline {result.project.project_id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("mode", result.mode.value)
    table.add_row("status", result.project.status.value)
    table.add_row("references", str(len(result.references)))
    if result.design_direction:
        table.add_row("concept", result.design_direction.concept_title)
        table.add_row("materials", ", ".join(result.design_direction.material_palette))
        table.add_row("trades", ", ".join(result.design_direction.likely_trades))
    table.add_row("variants", str(len(result.variants)))
    for warning in result.warnings:
        table.add_row("warning", warning)
    console.print(table)
    for ref in result.references:
        console.print(
            f"  ref {ref.image_id} score={ref.score:.3f} "
            f"role={ref.diversity_role} — {ref.match_rationale}"
        )
    for variant in result.variants:
        console.print(f"  variant {variant.variant_id} [{variant.kind.value}] → {variant.image_path}")


@app.command("compare")
def compare_cmd(
    room: Path = typer.Option(..., "--room"),
    brief: str = typer.Option(..., "--brief"),
    room_type: str = typer.Option("living_room", "--room-type"),
    skip_images: bool = typer.Option(False, "--skip-images"),
) -> None:
    """Run baseline vs curated for evaluation."""
    repo, settings, file_store = _boot()
    payload = ProjectInput(
        room_image_path=str(room if room.is_absolute() else settings.resolve(room)),
        room_type=room_type,
        brief=brief,
    )
    try:
        results = run_baseline_vs_curated(
            repo=repo,
            settings=settings,
            file_store=file_store,
            payload=payload,
            skip_image_edit=skip_images,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Compare failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    for name, result in results.items():
        title = result.design_direction.concept_title if result.design_direction else "(none)"
        console.print(
            f"[bold]{name}[/bold] project={result.project.project_id} "
            f"refs={len(result.references)} concept={title} variants={len(result.variants)}"
        )


@app.command("record-feedback")
def record_feedback_cmd(
    project_id: str = typer.Option(..., "--project-id"),
    decision: str = typer.Option(..., "--decision", help="approved | rejected | needs_edit"),
    variant_id: Optional[str] = typer.Option(None, "--variant-id"),
    rank: Optional[int] = typer.Option(None, "--rank"),
    reviewer: Optional[str] = typer.Option(None, "--reviewer"),
    taste: Optional[int] = typer.Option(None, "--taste", help="1-5"),
    geometry: Optional[int] = typer.Option(None, "--geometry", help="1-5"),
    notes: Optional[str] = typer.Option(None, "--notes"),
    failure_tag: Optional[list[str]] = typer.Option(None, "--failure-tag"),
) -> None:
    """Capture Lloyd review feedback for a project/variant."""
    repo, settings, _ = _boot()
    event = record_feedback(
        repo=repo,
        project_id=project_id,
        reviewer=reviewer or settings.review.curator_name,
        decision=decision,
        variant_id=variant_id,
        rank=rank,
        taste_quality_score=taste,
        geometry_preservation_score=geometry,
        positive_notes=notes,
        failure_tags=list(failure_tag or []),
    )
    console.print(f"[green]Saved feedback[/green] {event.feedback_id}")


@app.command("export-feedback")
def export_feedback_cmd(
    output: Path = typer.Option(..., "--output"),
    format: str = typer.Option("jsonl", "--format", help="jsonl | csv | parquet"),
    project_id: Optional[str] = typer.Option(None, "--project-id"),
) -> None:
    """Export stored review feedback."""
    repo, settings, _ = _boot()
    path, count = export_feedback_dataset(
        repo=repo,
        settings=settings,
        output=output,
        fmt=format,
        project_id=project_id,
    )
    console.print(f"[green]Exported {count} feedback events[/green] → {path}")


@app.command("save-review")
def save_review_cmd(
    generation_run_id: str = typer.Option(..., "--generation-run-id"),
    project_id: str = typer.Option(..., "--project-id"),
    reviewer: Optional[str] = typer.Option(None, "--reviewer"),
    submit: bool = typer.Option(False, "--submit", help="Submit instead of draft"),
    winner_variant_id: Optional[str] = typer.Option(None, "--winner-variant-id"),
    payload_file: Path = typer.Option(..., "--payload-file", help="JSON review payload"),
) -> None:
    """Save a generation review set from JSON."""
    repo, settings, _ = _boot()
    data = json.loads(payload_file.read_text(encoding="utf-8"))
    if "variants" not in data:
        data = {"variants": [data]}
    review_input = GenerationReviewSetInput(
        generation_run_id=generation_run_id,
        project_id=project_id,
        reviewer=reviewer or settings.review.curator_name,
        status=GenerationReviewSetStatus.SUBMITTED if submit else GenerationReviewSetStatus.DRAFT,
        winner_variant_id=winner_variant_id,
        overall_notes=data.get("overall_notes"),
        variants=[VariantReviewInput.model_validate(v) for v in data["variants"]],
    )
    try:
        review_set = save_generation_review(repo=repo, payload=review_input)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Review save failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Saved review set[/green] {review_set.review_set_id}")


@app.command("promote-concept")
def promote_concept_cmd(
    variant_review_id: str = typer.Option(..., "--variant-review-id"),
    purpose: str = typer.Option("evaluation_allowed", "--purpose"),
    reviewer: Optional[str] = typer.Option(None, "--reviewer"),
    consent_version: str = typer.Option("review-consent.v1", "--consent-version"),
) -> None:
    """Promote an approved winner to the evaluation dataset manifest."""
    repo, settings, _ = _boot()
    try:
        manifest = promote_approved_concept(
            repo=repo,
            variant_review_id=variant_review_id,
            purpose=RetentionConsentStatus(purpose),
            consented_by=reviewer or settings.review.curator_name,
            consent_version=consent_version,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Promotion failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Created manifest[/green] {manifest.manifest_id}")


@app.command("export-review-training")
def export_review_training_cmd(
    output: Path = typer.Option(..., "--output"),
    format: str = typer.Option("jsonl", "--format", help="jsonl | csv | parquet"),
) -> None:
    """Export joined review training rows."""
    repo, settings, _ = _boot()
    path, count = export_review_training_dataset(
        repo=repo, settings=settings, output=output, fmt=format
    )
    console.print(f"[green]Exported {count} review rows[/green] → {path}")


@app.command("export-approved-concepts")
def export_approved_concepts_cmd(
    output: Path = typer.Option(..., "--output"),
    format: str = typer.Option("jsonl", "--format", help="jsonl | csv | parquet"),
) -> None:
    """Export approved concept manifests."""
    repo, settings, _ = _boot()
    path, count = export_approved_concepts(
        repo=repo, settings=settings, output=output, fmt=format
    )
    console.print(f"[green]Exported {count} approved concepts[/green] → {path}")


@app.command("evaluate")
def evaluate_cmd(
    config: Path = typer.Option(..., "--config", help="Evaluation YAML spec"),
    repetitions: Optional[int] = typer.Option(None, "--repetitions", help="Override N"),
    workers: int = typer.Option(4, "--workers", help="Parallel arm workers"),
    skip_images: bool = typer.Option(False, "--skip-images"),
) -> None:
    """Run controlled curated/baseline evaluation from YAML spec."""
    repo, settings, file_store = _boot()
    try:
        summary, spec = run_controlled_evaluation(
            repo=repo,
            settings=settings,
            file_store=file_store,
            config_path=config,
            repetitions=repetitions,
            workers=workers,
            skip_image_edit=skip_images,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Evaluation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    table = Table(title=f"Evaluation {summary.evaluation_run_id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("spec", spec.name)
    table.add_row("status", summary.status.value)
    table.add_row("total_cases", str(summary.total_cases))
    table.add_row("complete_cases", str(summary.complete_cases))
    table.add_row("partial_cases", str(summary.partial_cases))
    table.add_row("failed_cases", str(summary.failed_cases))
    console.print(table)


@app.command("evaluation-package")
def evaluation_package_cmd(
    config: Path = typer.Option(..., "--config", help="Evaluation YAML spec"),
    repetitions: Optional[int] = typer.Option(None, "--repetitions", help="Override N"),
    workers: int = typer.Option(4, "--workers", help="Parallel arm workers"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Blind candidate shuffle seed"),
) -> None:
    """Run evaluation and create full and blinded packages."""
    repo, settings, file_store = _boot()
    try:
        package = create_evaluation_package(
            repo=repo,
            settings=settings,
            file_store=file_store,
            config_path=config,
            repetitions=repetitions,
            workers=workers,
            seed=seed,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Evaluation package failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Evaluation package {package.summary.evaluation_run_id}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("status", package.summary.status.value)
    table.add_row("complete_pairs", str(package.summary.complete_cases))
    table.add_row("full_export_id", package.full_export.evaluation_export_id)
    table.add_row("full_directory", str(package.full_directory))
    table.add_row("blind_export_id", package.blind_export.evaluation_export_id)
    table.add_row("blind_directory", str(package.blind_directory))
    console.print(table)


@app.command("evaluation-report")
def evaluation_report_cmd(
    eval_id: str = typer.Option(..., "--eval-id"),
    output: Optional[Path] = typer.Option(None, "--output"),
) -> None:
    """Read-only report for complete evaluation pairs."""
    repo, settings, _ = _boot()
    try:
        report, dest = write_evaluation_report(
            repo=repo,
            settings=settings,
            evaluation_run_id=eval_id,
            output_dir=output,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Report failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Evaluation report[/green] complete_pairs={report['complete_pairs']} "
        f"total_cases={report['total_cases']}"
    )
    if dest is not None:
        console.print(f"Wrote report to {dest}")


@app.command("evaluation-export")
def evaluation_export_cmd(
    eval_id: str = typer.Option(..., "--eval-id"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
) -> None:
    """Export full auditable evaluation bundle."""
    repo, settings, _ = _boot()
    try:
        export, dest = export_full_evaluation(
            repo=repo,
            settings=settings,
            evaluation_run_id=eval_id,
            output_dir=output_dir,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Exported evaluation[/green] {export.evaluation_export_id} → {dest}"
    )


@app.command("blind-evaluation-export")
def blind_evaluation_export_cmd(
    eval_id: str = typer.Option(..., "--eval-id"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
    seed: Optional[int] = typer.Option(None, "--seed"),
) -> None:
    """Export blinded evaluator package."""
    repo, settings, _ = _boot()
    try:
        export, dest = export_blind_evaluation(
            repo=repo,
            settings=settings,
            evaluation_run_id=eval_id,
            output_dir=output_dir,
            seed=seed,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Blind export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Exported blind evaluation[/green] {export.evaluation_export_id} → {dest}"
    )


@app.command("evaluation-import-selections")
def evaluation_import_selections_cmd(
    export_id: str = typer.Option(..., "--export-id"),
    csv: Path = typer.Option(..., "--csv"),
    evaluator_id: str = typer.Option("default", "--evaluator-id"),
    output: Optional[Path] = typer.Option(None, "--output"),
) -> None:
    """Import blind evaluation CSV selections and compute win rates."""
    repo, settings, _ = _boot()
    csv_path = csv if csv.is_absolute() else settings.resolve(csv)
    try:
        selections, report = import_evaluation_selections(
            repo=repo,
            evaluation_export_id=export_id,
            csv_path=csv_path,
            evaluator_id=evaluator_id,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Import failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    if output is not None:
        dest = output if output.is_absolute() else settings.resolve(output)
        write_selection_report(report, dest)
        console.print(f"Wrote selection report to {dest}")
    table = Table(title="Selection win rates")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("selections", str(len(selections)))
    table.add_row("curated_wins", str(report["curated_wins"]))
    table.add_row("baseline_wins", str(report["baseline_wins"]))
    table.add_row("curated_win_rate", f"{report['curated_win_rate']:.0%}")
    table.add_row("baseline_win_rate", f"{report['baseline_win_rate']:.0%}")
    console.print(table)


@app.command("evaluation-score")
def evaluation_score_cmd(
    export_id: str = typer.Option(..., "--export-id", help="Blind export ID"),
    csv: Path = typer.Option(..., "--csv", help="Completed evaluator CSV"),
    evaluator_id: str = typer.Option("default", "--evaluator-id"),
    output: Optional[Path] = typer.Option(None, "--output"),
) -> None:
    """Import evaluator CSV and write internal win-proportion report."""
    repo, settings, _ = _boot()
    csv_path = csv if csv.is_absolute() else settings.resolve(csv)
    try:
        score = score_blind_evaluation(
            repo=repo,
            settings=settings,
            evaluation_export_id=export_id,
            csv_path=csv_path,
            evaluator_id=evaluator_id,
            output_path=output,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Evaluation scoring failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Evaluation score {score.evaluation_run_id}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("curated_wins", str(score.report["curated_wins"]))
    table.add_row("baseline_wins", str(score.report["baseline_wins"]))
    table.add_row("curated_win_rate", f"{score.report['curated_win_rate']:.0%}")
    table.add_row("baseline_win_rate", f"{score.report['baseline_win_rate']:.0%}")
    table.add_row("report", str(score.report_path))
    console.print(table)


@app.command("report")
def report() -> None:
    """Show local persistence counts and feedback evaluation summary."""
    from vision_engine.application.evaluate import summarise_feedback

    repo, settings, _ = _boot()
    table = Table(title="Vision engine report")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("database", str(settings.database_path))
    table.add_row("provider", settings.model_provider)
    table.add_row("model", settings.model_name)
    table.add_row("index", str(settings.paths.index_path))
    for key, value in repo.counts().items():
        table.add_row(key, str(value))
    summary = summarise_feedback(repo)
    table.add_row("feedback_count", str(summary["feedback_count"]))
    if summary.get("approval_rate") is not None:
        table.add_row("approval_rate", f"{summary['approval_rate']:.0%}")
    if summary.get("avg_geometry") is not None:
        table.add_row("avg_geometry", f"{summary['avg_geometry']:.2f}")
    if summary.get("avg_taste") is not None:
        table.add_row("avg_taste", f"{summary['avg_taste']:.2f}")
    if summary.get("severe_geometry_rate") is not None:
        table.add_row("severe_geometry_rate", f"{summary['severe_geometry_rate']:.0%}")
    console.print(table)


@app.command("ui")
def ui_cmd(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(7860, "--port"),
    share: bool = typer.Option(False, "--share"),
) -> None:
    """Launch the Gradio prototype UI."""
    from vision_engine.ui.gradio_app import launch

    launch(host=host, port=port, share=share)


if __name__ == "__main__":
    app()

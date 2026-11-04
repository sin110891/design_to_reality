from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from design_dataset.application.export import export_gold_dataset
from design_dataset.application.import_v3 import import_v3_annotations
from design_dataset.application.ingest import ingest_images
from design_dataset.application.label import label_images, retry_failures
from design_dataset.application.review import export_for_review, import_reviewed
from design_dataset.domain.enums import UsageRightsStatus
from design_dataset.infrastructure.sqlite_repository import SqliteRepository
from design_dataset.settings import clear_settings_cache, get_settings

app = typer.Typer(
    name="design-data",
    help="Hybrid rulebook + multimodal design dataset builder",
    no_args_is_help=True,
)
console = Console()


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _repo() -> tuple[SqliteRepository, object]:
    clear_settings_cache()
    settings = get_settings()
    _configure_logging(settings.log_level)
    repo = SqliteRepository(settings.database_path)
    return repo, settings


@app.command("init-db")
def init_db() -> None:
    """Create SQLite tables and indexes."""
    repo, settings = _repo()
    repo.init_db()
    console.print(f"[green]Initialized database[/green] at {settings.database_path}")


@app.command("ingest")
def ingest(
    input: Path = typer.Option(..., "--input", help="Directory of source images"),
    usage_rights: str = typer.Option(
        UsageRightsStatus.UNKNOWN.value,
        "--usage-rights",
        help="Provenance / rights status for newly ingested images",
    ),
) -> None:
    """Hash and register images into the local registry."""
    repo, settings = _repo()
    repo.init_db()
    try:
        rights = UsageRightsStatus(usage_rights)
    except ValueError as exc:
        console.print(f"[red]Invalid usage rights:[/red] {usage_rights}")
        raise typer.Exit(code=1) from exc
    report = ingest_images(
        repo=repo,
        settings=settings,
        input_dir=input if input.is_absolute() else settings.resolve(input),
        usage_rights_status=rights,
    )
    _print_report("Ingest", report)


@app.command("label")
def label(
    limit: Optional[int] = typer.Option(None, "--limit", help="Max images to label"),
    force: bool = typer.Option(False, "--force", help="Ignore idempotent skip"),
) -> None:
    """Call the multimodal model and store draft curated records."""
    repo, settings = _repo()
    repo.init_db()
    report = label_images(repo=repo, settings=settings, limit=limit, force=force)
    _print_report("Label", report)
    if report.provider_failed and report.labelled == 0:
        raise typer.Exit(code=1)


@app.command("retry-failures")
def retry_failures_cmd(
    failure_type: str = typer.Option(
        ...,
        "--failure-type",
        help="Error category to retry, e.g. provider_transient",
    ),
    limit: Optional[int] = typer.Option(None, "--limit"),
) -> None:
    """Retry failed labelling runs of a given failure type."""
    repo, settings = _repo()
    report = retry_failures(
        repo=repo,
        settings=settings,
        failure_type=failure_type,
        limit=limit,
    )
    _print_report("Retry", report)


@app.command("export-review")
def export_review(
    output: Path = typer.Option(..., "--output", help="XLSX path for curator review"),
) -> None:
    """Export draft records to a spreadsheet for human review."""
    repo, settings = _repo()
    path = export_for_review(
        repo=repo,
        output=output if output.is_absolute() else settings.resolve(output),
    )
    console.print(f"[green]Wrote review workbook[/green] {path}")


@app.command("import-review")
def import_review(
    input: Path = typer.Option(..., "--input", help="Reviewed XLSX path"),
) -> None:
    """Import curator decisions and validate against the rulebook."""
    repo, settings = _repo()
    # Backup before bulk import
    if settings.database_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = settings.database_path.with_name(f"app_backup_{stamp}.db")
        shutil.copy2(settings.database_path, backup)
        console.print(f"[dim]Backup:[/dim] {backup}")
    try:
        counts = import_reviewed(
            repo=repo,
            settings=settings,
            input_path=input if input.is_absolute() else settings.resolve(input),
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Import failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Updated {counts['updated']}[/green] "
        f"(approved={counts['approved']}, reviewed={counts['reviewed']}, "
        f"rejected={counts['rejected']})"
    )


@app.command("import-v3")
def import_v3(
    input: Path = typer.Option(..., "--input", help="Lloyd V3 XLSX path"),
    sheet: str = typer.Option("Collection Example", "--sheet"),
) -> None:
    """Import human reference metadata from the Lloyd V3 workbook."""
    repo, settings = _repo()
    if settings.database_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = settings.database_path.with_name(f"app_backup_{stamp}.db")
        shutil.copy2(settings.database_path, backup)
        console.print(f"[dim]Backup:[/dim] {backup}")
    repo.init_db()
    try:
        counts = import_v3_annotations(
            repo=repo,
            settings=settings,
            input_path=input if input.is_absolute() else settings.resolve(input),
            sheet_name=sheet,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]V3 import failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Imported expert metadata for {counts['unique_images']} images[/green] "
        f"({counts['records_updated']} records updated, "
        f"{counts['duplicate_rows_skipped']} duplicate rows skipped)"
    )
    if counts["unmatched_image_ids"]:
        console.print(
            "[yellow]Unmatched workbook rows:[/yellow] "
            + ", ".join(counts["unmatched_image_ids"])
        )


@app.command("export-gold")
def export_gold_cmd(
    format: str = typer.Option("jsonl", "--format", help="jsonl | csv | parquet"),
    output: Path = typer.Option(..., "--output"),
    include_restricted: bool = typer.Option(
        False, "--include-restricted", help="Include restricted-rights imagery"
    ),
) -> None:
    """Export approved gold records only."""
    repo, settings = _repo()
    try:
        path, count = export_gold_dataset(
            repo=repo,
            output=output if output.is_absolute() else settings.resolve(output),
            fmt=format,
            include_restricted=include_restricted,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Exported {count} approved records[/green] → {path}")


@app.command("report")
def report() -> None:
    """Show registry and curation status counts."""
    repo, settings = _repo()
    repo.init_db()
    table = Table(title="Dataset report")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("database", str(settings.database_path))
    table.add_row("provider", settings.model_provider)
    table.add_row("model", settings.model_name)
    table.add_row("images", str(len(repo.list_images())))
    for status, count in sorted(repo.status_counts().items()):
        table.add_row(f"status:{status}", str(count))
    console.print(table)


def _print_report(title: str, report) -> None:
    table = Table(title=f"{title} report")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    for key, value in report.model_dump().items():
        if value is None:
            continue
        if isinstance(value, float):
            table.add_row(key, f"{value:.2f}")
        else:
            table.add_row(key, str(value))
    console.print(table)


if __name__ == "__main__":
    app()

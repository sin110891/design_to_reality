from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from vision_engine.concept_board.application.bootstrap import bootstrap_concept_board_from_variant
from vision_engine.concept_board.application.catalogue import import_catalogue_csv
from vision_engine.catalog_providers.errors import Channel3Error
from vision_engine.concept_board.application.channel3_catalogue import (
    import_channel3_snapshot_for_region,
    ping_channel3,
)
from vision_engine.concept_board.application.integration_export import export_procurement_csv
from vision_engine.concept_board.application.procurement import (
    approve_procurement_schedule,
    create_procurement_schedule,
)
from vision_engine.concept_board.application.region_discovery import (
    confirm_proposed_regions,
    detect_regions_for_concept_version,
)
from vision_engine.concept_board.application.product_retrieval import retrieve_product_candidates
from vision_engine.concept_board.application.regions import (
    add_region_geometry,
    add_region_requirement,
    confirm_design_region,
    create_design_region,
)
from vision_engine.concept_board.application.selections import (
    approve_region_selection,
    create_concept_version_from_selections,
    select_region_candidate,
)
from vision_engine.concept_board.application.substitutions import generate_substitution_preview
from vision_engine.concept_board.application.workspace import get_workspace_view
from vision_engine.concept_board.domain.enums import RegionGeometryType, RequirementSeverity
from vision_engine.concept_board.domain.errors import ConceptBoardError
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import clear_settings_cache, get_settings

app = typer.Typer(
    name="concept-board",
    help="Concept board, product matching, and procurement workflows",
    no_args_is_help=True,
)
console = Console()


def _boot() -> tuple[SqliteRepository, object, FileStore]:
    clear_settings_cache()
    settings = get_settings()
    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )
    return repo, settings, file_store


@app.command("bootstrap")
def bootstrap_cmd(
    project_id: str = typer.Option(..., "--project-id"),
    variant_id: str = typer.Option(..., "--variant-id"),
    board_name: Optional[str] = typer.Option(None, "--board-name"),
) -> None:
    """Create a concept board from an approved/generated variant."""
    repo, settings, file_store = _boot()
    try:
        board, direction, version = bootstrap_concept_board_from_variant(
            repo=repo,
            settings=settings,
            project_id=project_id,
            variant_id=variant_id,
            board_name=board_name,
        )
    except ConceptBoardError as exc:
        console.print(f"[red]Bootstrap failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Concept board[/green] {board.concept_board_id}")
    console.print(f"Direction: {direction.concept_direction_id}")
    console.print(f"Version:   {version.concept_version_id} (v{version.version_number})")


@app.command("ping-channel3")
def ping_channel3_cmd(
    query: str = typer.Option("sofa", "--query"),
) -> None:
    """Check Channel3 API key and connectivity with a minimal search."""
    clear_settings_cache()
    settings = get_settings()
    try:
        result = ping_channel3(settings=settings, query=query)
    except Channel3Error as exc:
        console.print(f"[red]Channel3 ping failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        "[green]Channel3 OK[/green] "
        f"— {result['product_count']} product(s) for query '{result['query']}' "
        f"({result['currency']}/{result['country']}/{result['language']})"
    )


@app.command("import-channel3")
def import_channel3_cmd(
    region_type: str = typer.Option(..., "--region-type"),
    display_name: str | None = typer.Option(None, "--display-name"),
    max_budget: float | None = typer.Option(None, "--max-budget"),
    design_region_id: str = typer.Option("cli-import", "--region-id"),
    snapshot_name: str | None = typer.Option(None, "--snapshot-name"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """Search Channel3 and import a sealed catalogue snapshot for a region type."""
    repo, settings, _ = _boot()
    try:
        snapshot, rows = import_channel3_snapshot_for_region(
            repo=repo,
            settings=settings,
            design_region_id=design_region_id,
            region_type=region_type,
            display_name=display_name,
            max_budget=max_budget,
            snapshot_name=snapshot_name,
            limit=limit,
        )
    except ConceptBoardError as exc:
        console.print(f"[red]Channel3 import failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Sealed Channel3 snapshot[/green] {snapshot.catalogue_snapshot_id} "
        f"({len(rows)} items, name={snapshot.snapshot_name})"
    )


@app.command("import-catalogue")
def import_catalogue_cmd(
    csv_path: Optional[Path] = typer.Option(None, "--csv"),
    snapshot_name: str = typer.Option("local-v1", "--snapshot-name"),
) -> None:
    """Import local product catalogue CSV and seal snapshot."""
    repo, settings, file_store = _boot()
    path = settings.resolve(csv_path or settings.paths.catalogue / "sample_products.csv")
    try:
        snapshot = import_catalogue_csv(
            repo=repo,
            csv_path=path,
            snapshot_name=snapshot_name,
            seal=True,
        )
    except ConceptBoardError as exc:
        console.print(f"[red]Import failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Sealed catalogue snapshot[/green] {snapshot.catalogue_snapshot_id} "
        f"({snapshot.item_count} items)"
    )


@app.command("detect-regions")
def detect_regions_cmd(
    project_id: str = typer.Option(..., "--project-id"),
    concept_version_id: str = typer.Option(..., "--concept-version-id"),
    reviewer: str = typer.Option("architect", "--reviewer"),
    auto_confirm: bool = typer.Option(False, "--auto-confirm/--proposed-only"),
) -> None:
    """Detect editable design regions from the active concept image."""
    repo, settings, _ = _boot()
    try:
        detection, created, overlay_path = detect_regions_for_concept_version(
            repo=repo,
            settings=settings,
            project_id=project_id,
            concept_version_id=concept_version_id,
            auto_confirm=auto_confirm,
            reviewer=reviewer,
        )
    except ConceptBoardError as exc:
        console.print(f"[red]Region detection failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Detected[/green] {len(detection.regions)} region(s) "
        f"via {detection.provider} ({detection.inferred_room_type or detection.room_type})"
    )
    console.print(f"Created/updated: {len(created)}")
    if overlay_path:
        console.print(f"Overlay: {overlay_path}")


@app.command("confirm-regions")
def confirm_regions_cmd(
    concept_direction_id: str = typer.Option(..., "--direction-id"),
    concept_version_id: str = typer.Option(..., "--concept-version-id"),
    reviewer: str = typer.Option("architect", "--reviewer"),
) -> None:
    """Confirm all proposed design regions for retrieval."""
    repo, _, _ = _boot()
    try:
        confirmed = confirm_proposed_regions(
            repo=repo,
            concept_direction_id=concept_direction_id,
            concept_version_id=concept_version_id,
            reviewer=reviewer,
        )
    except ConceptBoardError as exc:
        console.print(f"[red]Confirm failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Confirmed[/green] {len(confirmed)} region(s)")


@app.command("add-region")
def add_region_cmd(
    project_id: str = typer.Option(..., "--project-id"),
    region_code: str = typer.Option(..., "--region-code"),
    region_type: str = typer.Option(..., "--region-type"),
    display_name: str = typer.Option(..., "--display-name"),
    max_budget: Optional[float] = typer.Option(None, "--max-budget"),
    reviewer: str = typer.Option("operator", "--reviewer"),
) -> None:
    """Create and confirm a design region with optional budget requirement."""
    repo, settings, file_store = _boot()
    view = get_workspace_view(repo=repo, project_id=project_id)
    region = create_design_region(
        repo=repo,
        concept_direction_id=view.concept_direction.concept_direction_id,
        region_code=region_code,
        region_type=region_type,
        display_name=display_name,
    )
    add_region_geometry(
        repo=repo,
        design_region_id=region.design_region_id,
        concept_version_id=view.latest_version.concept_version_id,
        geometry_type=RegionGeometryType.BOUNDING_BOX,
        geometry_json={"x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3},
    )
    if max_budget is not None:
        add_region_requirement(
            repo=repo,
            design_region_id=region.design_region_id,
            requirement_type="budget",
            operator="<=",
            value_json={"amount": max_budget, "currency": "GBP"},
            severity=RequirementSeverity.HARD,
        )
    confirm_design_region(
        repo=repo,
        design_region_id=region.design_region_id,
        reviewer=reviewer,
        concept_version_id=view.latest_version.concept_version_id,
    )
    console.print(f"[green]Region[/green] {region.design_region_id} ({region.region_code})")


@app.command("retrieve")
def retrieve_cmd(
    design_region_id: str = typer.Option(..., "--region-id"),
    concept_version_id: str = typer.Option(..., "--concept-version-id"),
    top_k: int = typer.Option(5, "--top-k"),
    use_channel3: bool = typer.Option(False, "--channel3/--local"),
) -> None:
    """Retrieve product candidates for a region."""
    repo, settings, _ = _boot()
    try:
        run, candidates = retrieve_product_candidates(
            repo=repo,
            design_region_id=design_region_id,
            concept_version_id=concept_version_id,
            top_k=top_k,
            settings=settings,
            use_channel3=use_channel3 or settings.catalogue_provider == "channel3",
        )
    except ConceptBoardError as exc:
        console.print(f"[red]Retrieval failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Candidates ({run.product_retrieval_run_id})")
    table.add_column("Rank")
    table.add_column("Candidate ID")
    table.add_column("Rationale")
    for idx, candidate in enumerate(candidates, start=1):
        rationale = candidate.match_rationale_json.get("product_name", "")
        price = candidate.match_rationale_json.get("unit_price", "")
        table.add_row(str(idx), candidate.region_candidate_id, f"{rationale} (£{price})")
    console.print(table)


@app.command("preview")
def preview_cmd(
    region_candidate_id: str = typer.Option(..., "--candidate-id"),
    concept_version_id: str = typer.Option(..., "--concept-version-id"),
) -> None:
    """Generate a 2D visual product staging preview with provenance."""
    repo, settings, file_store = _boot()
    preview = generate_substitution_preview(
        repo=repo,
        settings=settings,
        file_store=file_store,
        region_candidate_id=region_candidate_id,
        concept_version_id=concept_version_id,
    )
    console.print(f"[green]Preview generated[/green] {preview.substitution_preview_id}")
    console.print(f"Evidence grade: {preview.evidence_grade}")
    console.print(f"Disclaimer: {preview.disclaimer}")
    console.print(f"Asset: {preview.preview_asset_uri}")


@app.command("select")
def select_cmd(
    region_candidate_id: str = typer.Option(..., "--candidate-id"),
    concept_version_id: str = typer.Option(..., "--concept-version-id"),
    selected_by: str = typer.Option("client", "--selected-by"),
    approver: str = typer.Option("architect", "--approver"),
    preview: bool = typer.Option(True, "--preview/--no-preview"),
) -> None:
    """Select a candidate, optionally preview, and architect-approve."""
    repo, settings, file_store = _boot()
    if preview:
        generate_substitution_preview(
            repo=repo,
            settings=settings,
            file_store=file_store,
            region_candidate_id=region_candidate_id,
            concept_version_id=concept_version_id,
        )
    selection = select_region_candidate(
        repo=repo,
        settings=settings,
        region_candidate_id=region_candidate_id,
        concept_version_id=concept_version_id,
        selected_by=selected_by,
    )
    approve_region_selection(
        repo=repo,
        region_selection_id=selection.region_selection_id,
        approver=approver,
    )
    console.print(f"[green]Selection approved[/green] {selection.region_selection_id}")


@app.command("procurement")
def procurement_cmd(
    project_id: str = typer.Option(..., "--project-id"),
    concept_version_id: str = typer.Option(..., "--concept-version-id"),
    schedule_name: str = typer.Option("Initial schedule", "--name"),
    approve: bool = typer.Option(True, "--approve/--draft"),
) -> None:
    """Build procurement schedule from approved selections."""
    repo, settings, _ = _boot()
    try:
        schedule, items = create_procurement_schedule(
            repo=repo,
            settings=settings,
            project_id=project_id,
            concept_version_id=concept_version_id,
            schedule_name=schedule_name,
        )
        if approve:
            schedule = approve_procurement_schedule(
                repo=repo,
                procurement_schedule_id=schedule.procurement_schedule_id,
            )
    except ConceptBoardError as exc:
        console.print(f"[red]Procurement failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]Schedule[/green] {schedule.procurement_schedule_id} "
        f"({len(items)} items, status={schedule.status.value})"
    )


@app.command("export")
def export_cmd(
    procurement_schedule_id: str = typer.Option(..., "--schedule-id"),
) -> None:
    """Export procurement schedule CSV + integration manifest."""
    repo, settings, file_store = _boot()
    try:
        export = export_procurement_csv(
            repo=repo,
            settings=settings,
            procurement_schedule_id=procurement_schedule_id,
        )
    except ConceptBoardError as exc:
        console.print(f"[red]Export failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Export[/green] {export.export_id}")
    console.print(f"Manifest: {export.manifest_uri}")


@app.command("status")
def status_cmd(
    project_id: str = typer.Option(..., "--project-id"),
) -> None:
    """Show concept board workspace summary."""
    repo, _, _ = _boot()
    try:
        view = get_workspace_view(repo=repo, project_id=project_id)
    except ConceptBoardError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    console.print(f"Board:   {view.concept_board.concept_board_id}")
    console.print(f"Version: {view.latest_version.concept_version_id} v{view.latest_version.version_number}")
    console.print(f"Regions: {len(view.regions)}")
    console.print(f"Selections: {len(view.selections)}")


@app.command("run-workflow")
def run_workflow_cmd(
    project_id: str = typer.Option(..., "--project-id"),
    variant_id: str = typer.Option(..., "--variant-id"),
    region_code: str = typer.Option("sofa_01", "--region-code"),
    region_type: str = typer.Option("sofa", "--region-type"),
    max_budget: float = typer.Option(3000.0, "--max-budget"),
) -> None:
    """End-to-end MVP workflow: bootstrap → region → retrieve → select → procure → export."""
    repo, settings, file_store = _boot()

    import_catalogue_csv(
        repo=repo,
        csv_path=settings.resolve(settings.paths.catalogue / "sample_products.csv"),
        snapshot_name="local-v1",
        seal=True,
    )
    board, direction, version = bootstrap_concept_board_from_variant(
        repo=repo,
        settings=settings,
        project_id=project_id,
        variant_id=variant_id,
    )
    region = create_design_region(
        repo=repo,
        concept_direction_id=direction.concept_direction_id,
        region_code=region_code,
        region_type=region_type,
        display_name=region_code.replace("_", " ").title(),
    )
    add_region_geometry(
        repo=repo,
        design_region_id=region.design_region_id,
        concept_version_id=version.concept_version_id,
        geometry_type=RegionGeometryType.BOUNDING_BOX,
        geometry_json={"x": 0.2, "y": 0.4, "width": 0.35, "height": 0.25},
    )
    add_region_requirement(
        repo=repo,
        design_region_id=region.design_region_id,
        requirement_type="budget",
        operator="<=",
        value_json={"amount": max_budget, "currency": "GBP"},
        severity=RequirementSeverity.HARD,
    )
    confirm_design_region(
        repo=repo,
        design_region_id=region.design_region_id,
        reviewer="architect",
        concept_version_id=version.concept_version_id,
    )
    _run, candidates = retrieve_product_candidates(
        repo=repo,
        design_region_id=region.design_region_id,
        concept_version_id=version.concept_version_id,
        top_k=3,
    )
    if not candidates:
        console.print("[red]No candidates found[/red]")
        raise typer.Exit(code=1)
    top = candidates[0]
    generate_substitution_preview(
        repo=repo,
        settings=settings,
        file_store=file_store,
        region_candidate_id=top.region_candidate_id,
        concept_version_id=version.concept_version_id,
    )
    selection = select_region_candidate(
        repo=repo,
        settings=settings,
        region_candidate_id=top.region_candidate_id,
        concept_version_id=version.concept_version_id,
        selected_by="client",
    )
    approve_region_selection(
        repo=repo,
        region_selection_id=selection.region_selection_id,
        approver="architect",
    )
    new_version = create_concept_version_from_selections(
        repo=repo,
        settings=settings,
        concept_direction_id=direction.concept_direction_id,
        parent_concept_version_id=version.concept_version_id,
        version_reason="Applied approved product selections",
        approver="architect",
    )
    schedule, items = create_procurement_schedule(
        repo=repo,
        settings=settings,
        project_id=project_id,
        concept_version_id=new_version.concept_version_id,
        schedule_name="MVP procurement schedule",
    )
    schedule = approve_procurement_schedule(
        repo=repo,
        procurement_schedule_id=schedule.procurement_schedule_id,
    )
    export = export_procurement_csv(
        repo=repo,
        settings=settings,
        procurement_schedule_id=schedule.procurement_schedule_id,
    )
    console.print("[green]Workflow complete[/green]")
    console.print(f"Board:    {board.concept_board_id}")
    console.print(f"Version:  {new_version.concept_version_id} v{new_version.version_number}")
    console.print(f"Schedule: {schedule.procurement_schedule_id} ({len(items)} items)")
    console.print(f"Export:   {export.export_id}")

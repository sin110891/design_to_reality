from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gradio as gr

from vision_engine.concept_board.application.bootstrap import bootstrap_concept_board_from_variant
from vision_engine.concept_board.application.catalogue import import_catalogue_csv
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
from vision_engine.virtual_staging.domain.errors import StagingError
from vision_engine.virtual_staging.application.cumulative_staging import resolve_cumulative_preview_mode


REGION_TYPES = [
    "sofa",
    "bed",
    "nightstand",
    "dresser",
    "fitted_wardrobe",
    "freestanding_wardrobe",
    "ceiling_pendant_light",
    "armchair",
    "coffee_table",
    "side_table",
    "dining_table",
    "chair",
    "floor_finish",
    "wall_finish",
    "pendant_light",
    "floor_lamp",
    "table_lamp",
    "curtains",
    "rug",
    "joinery",
    "artwork",
    "mirror",
]


def _boot() -> tuple[SqliteRepository, Any, FileStore]:
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


def _parse_choice(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(" | ", maxsplit=1)[0].strip() or None


def _parse_image_choice(value: str | None) -> str | None:
    if not value:
        return None
    parts = value.split(" | ", maxsplit=1)
    if len(parts) == 2 and parts[1].strip().startswith(("http://", "https://")):
        return parts[1].strip()
    if value.strip().startswith(("http://", "https://")):
        return value.strip()
    return None


def _candidate_images_from_rationale(rationale: dict[str, Any]) -> list[dict[str, Any]]:
    images = rationale.get("product_images") or []
    if images:
        return images
    reference = rationale.get("reference_image_uri")
    if reference:
        return [{"url": reference, "is_cleaned_image": True}]
    return []


def _build_candidate_catalog(candidates: list[Any]) -> tuple[dict[str, Any], list[tuple[str, str]], str | None]:
    catalog: dict[str, Any] = {"candidates": {}, "order": []}
    gallery: list[tuple[str, str]] = []
    first_choice: str | None = None

    for candidate in candidates:
        rationale = candidate.match_rationale_json
        product = rationale.get("product_name", "Unknown product")
        price = rationale.get("unit_price", "—")
        images = _candidate_images_from_rationale(rationale)
        catalog["candidates"][candidate.region_candidate_id] = {
            "product_name": product,
            "unit_price": price,
            "reference_image_uri": rationale.get("reference_image_uri"),
            "product_images": images,
        }
        catalog["order"].append(candidate.region_candidate_id)
        choice = f"{candidate.region_candidate_id} | {product} (£{price})"
        if first_choice is None:
            first_choice = choice
        hero = images[0]["url"] if images else rationale.get("reference_image_uri")
        if hero:
            gallery.append((hero, f"{product} (£{price})"))
    return catalog, gallery, first_choice


def _image_choice_updates(images: list[dict[str, Any]]) -> tuple[Any, str | None]:
    choices: list[str] = []
    for index, image in enumerate(images, start=1):
        url = image.get("url")
        if not url:
            continue
        label = "cleaned" if image.get("is_cleaned_image") else "photo"
        choices.append(f"{index} | {label} | {url}")
    default = choices[0] if choices else None
    hero = _parse_image_choice(default)
    return gr.update(choices=choices, value=default), hero


def _sync_candidate_panels(
    catalog_json: str,
    candidate_choice: str | None,
) -> tuple[Any, Any, str | None]:
    try:
        catalog = json.loads(catalog_json or "{}")
    except json.JSONDecodeError:
        catalog = {}
    candidate_id = _parse_choice(candidate_choice)
    if candidate_id is None:
        candidate_ids = catalog.get("order") or []
        candidate_id = candidate_ids[0] if candidate_ids else None
    entry = (catalog.get("candidates") or {}).get(candidate_id or "", {})
    images = entry.get("product_images") or []
    image_dropdown, hero = _image_choice_updates(images)
    product_images = [(img["url"], f"Image {index}") for index, img in enumerate(images, start=1) if img.get("url")]
    return (
        gr.update(value=product_images),
        image_dropdown,
        hero,
    )


def _resolve_staging_image_uri(catalog_json: str, candidate_choice: str | None, image_choice: str | None) -> str | None:
    explicit = _parse_image_choice(image_choice)
    if explicit:
        return explicit
    try:
        catalog = json.loads(catalog_json or "{}")
    except json.JSONDecodeError:
        catalog = {}
    candidate_id = _parse_choice(candidate_choice)
    if not candidate_id:
        return None
    entry = (catalog.get("candidates") or {}).get(candidate_id, {})
    images = entry.get("product_images") or []
    if images:
        return images[0].get("url")
    return entry.get("reference_image_uri")


def _region_confidence(
    repo: SqliteRepository,
    region_id: str,
    concept_version_id: str,
) -> str:
    geometry = repo.get_region_geometry_for_version(region_id, concept_version_id)
    if geometry is None or geometry.confidence is None:
        return "—"
    return f"{geometry.confidence:.2f}"


def _workspace_payload(project_id: str) -> tuple[dict[str, str], str | None, list[list[Any]], list[list[Any]]]:
    repo, settings, _ = _boot()
    workspace = get_workspace_view(repo=repo, project_id=project_id)
    asset = repo.get_primary_concept_asset(workspace.latest_version.concept_version_id)
    asset_path = settings.resolve(asset.storage_uri) if asset else None
    base_image = str(asset_path) if asset_path and asset_path.exists() else None
    version_id = workspace.latest_version.concept_version_id

    region_rows = [
        [
            region.design_region_id,
            region.region_code,
            region.region_type,
            region.lifecycle_status.value,
            _region_confidence(repo, region.design_region_id, version_id),
            "fixed" if region.is_fixed else "editable",
        ]
        for region in workspace.regions
    ]
    selection_rows = [
        [
            selection.region_selection_id,
            selection.design_region_id,
            selection.selection_status.value,
            selection.quantity,
            selection.approval_state,
        ]
        for selection in workspace.selections
    ]
    state = {
        "project_id": project_id,
        "concept_board_id": workspace.concept_board.concept_board_id,
        "concept_direction_id": workspace.concept_direction.concept_direction_id,
        "concept_version_id": workspace.latest_version.concept_version_id,
        "version_number": str(workspace.latest_version.version_number),
    }
    return state, base_image, region_rows, selection_rows


def _workspace_markdown(state: dict[str, str]) -> str:
    return (
        f"**Board:** `{state['concept_board_id']}`  \n"
        f"**Direction:** `{state['concept_direction_id']}`  \n"
        f"**Active version:** `v{state['version_number']}` — `{state['concept_version_id']}`"
    )


def _workspace_updates(project_id: str) -> tuple[Any, ...]:
    state, image, regions, selections = _workspace_payload(project_id)
    region_choices = [
        f"{row[0]} | {row[1]} ({row[2]})"
        for row in regions
        if row[3] == "confirmed" and row[5] == "editable"
    ]
    return (
        json.dumps(state),
        _workspace_markdown(state),
        image,
        regions,
        selections,
        gr.update(choices=region_choices, value=region_choices[0] if region_choices else None),
    )


def open_concept_board(
    project_id: str,
    variant_id: str | None,
    board_name: str | None,
) -> tuple[Any, ...]:
    if not project_id or not project_id.strip():
        raise gr.Error("Project ID is required.")

    repo, _settings, _ = _boot()
    existing = repo.get_concept_board_for_project(project_id.strip())
    if existing is not None:
        return load_existing_board(project_id)

    if not variant_id or not variant_id.strip():
        raise gr.Error(
            "No concept board exists for this project yet. "
            "Enter a variant ID, then click Open concept board."
        )
    return bootstrap_board(project_id, variant_id, board_name)


def load_existing_board(project_id: str) -> tuple[Any, ...]:
    if not project_id or not project_id.strip():
        raise gr.Error("Enter a Vision Engine project ID.")
    try:
        updates = _workspace_updates(project_id.strip())
    except ConceptBoardError as exc:
        raise gr.Error(
            f"{exc}. Bootstrap a concept board from a variant first, or check the project ID."
        ) from exc
    state = json.loads(updates[0])
    return (
        f"Loaded existing concept board `{state['concept_board_id']}` "
        f"(v{state['version_number']}).",
        *updates,
    )


def fill_ids_from_pipeline(
    pipeline_state_json: str,
    variant_choice: str | None,
) -> tuple[str, str, str]:
    try:
        pipeline = json.loads(pipeline_state_json or "{}")
    except json.JSONDecodeError:
        pipeline = {}
    project_id = (pipeline.get("project_id") or "").strip()
    if not project_id:
        raise gr.Error("Generate concepts in Tab 1 first, or enter IDs manually.")

    variant_id = _parse_choice(variant_choice)
    if variant_id is None:
        variant_ids = pipeline.get("variant_ids") or []
        variant_id = variant_ids[0] if variant_ids else ""

    status = f"Filled project `{project_id}`"
    if variant_id:
        status += f" and variant `{variant_id}` from the current session."
    else:
        status += " from the current session. Add a variant ID to bootstrap a new board."
    return project_id, variant_id, status


def pipeline_variant_choices(pipeline_state_json: str) -> Any:
    try:
        pipeline = json.loads(pipeline_state_json or "{}")
    except json.JSONDecodeError:
        pipeline = {}
    choices: list[str] = []
    for variant_id, kind in zip(
        pipeline.get("variant_ids") or [],
        pipeline.get("variant_kinds") or [],
        strict=False,
    ):
        choices.append(f"{variant_id} | {kind}")
    return gr.update(choices=choices, value=choices[0] if choices else None)


def bootstrap_board(project_id: str, variant_id: str, board_name: str | None) -> tuple[Any, ...]:
    if not project_id or not project_id.strip():
        raise gr.Error("Project ID is required.")
    if not variant_id or not variant_id.strip():
        raise gr.Error(
            "Variant ID is required to bootstrap a new concept board. "
            "Use **Load existing board** if the board was already created."
        )
    repo, settings, _ = _boot()
    try:
        board, _direction, _version = bootstrap_concept_board_from_variant(
            repo=repo,
            settings=settings,
            project_id=project_id.strip(),
            variant_id=variant_id.strip(),
            board_name=board_name.strip() if board_name else None,
        )
        updates = _workspace_updates(project_id.strip())
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc
    return (f"Concept board ready `{board.concept_board_id}`.", *updates)


def load_catalogue(snapshot_name: str) -> str:
    repo, settings, _ = _boot()
    name = snapshot_name.strip() or "local-v1"
    existing = repo.get_catalogue_snapshot_by_name(name)
    if existing and existing.status.value == "sealed":
        return (
            f"Using sealed catalogue snapshot `{existing.catalogue_snapshot_id}` "
            f"with {existing.item_count} items."
        )
    try:
        snapshot = import_catalogue_csv(
            repo=repo,
            csv_path=settings.resolve(settings.paths.catalogue / "sample_products.csv"),
            snapshot_name=name,
            seal=True,
        )
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc
    return (
        f"Imported and sealed `{snapshot.snapshot_name}` "
        f"(`{snapshot.catalogue_snapshot_id}`, {snapshot.item_count} items)."
    )


def create_region(
    state_json: str,
    region_code: str,
    region_type: str,
    display_name: str,
    max_budget: float | None,
    reviewer: str,
) -> tuple[Any, ...]:
    try:
        state = json.loads(state_json or "{}")
        project_id = state["project_id"]
        direction_id = state["concept_direction_id"]
        version_id = state["concept_version_id"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise gr.Error("Load a concept board before adding regions.") from exc
    if not region_code or not display_name:
        raise gr.Error("Region code and display name are required.")

    repo, _settings, _ = _boot()
    try:
        region = create_design_region(
            repo=repo,
            concept_direction_id=direction_id,
            region_code=region_code.strip(),
            region_type=region_type,
            display_name=display_name.strip(),
        )
        add_region_geometry(
            repo=repo,
            design_region_id=region.design_region_id,
            concept_version_id=version_id,
            geometry_type=RegionGeometryType.BOUNDING_BOX,
            geometry_json={"x": 0.2, "y": 0.2, "width": 0.35, "height": 0.3},
            source="gradio_manual_placeholder",
        )
        if max_budget:
            add_region_requirement(
                repo=repo,
                design_region_id=region.design_region_id,
                requirement_type="budget",
                operator="<=",
                value_json={"amount": max_budget, "currency": "GBP"},
                severity=RequirementSeverity.HARD,
                source="gradio",
            )
        confirm_design_region(
            repo=repo,
            design_region_id=region.design_region_id,
            reviewer=reviewer.strip() or "architect",
            concept_version_id=version_id,
        )
        updates = _workspace_updates(project_id)
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc
    return (f"Added and confirmed `{region.region_code}`.", *updates)


def detect_regions(
    state_json: str,
    reviewer: str,
    auto_confirm: bool,
) -> tuple[Any, ...]:
    try:
        state = json.loads(state_json or "{}")
        project_id = state["project_id"]
        version_id = state["concept_version_id"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise gr.Error("Load a concept board before detecting regions.") from exc

    repo, settings, _ = _boot()
    try:
        detection, created, overlay_path = detect_regions_for_concept_version(
            repo=repo,
            settings=settings,
            project_id=project_id,
            concept_version_id=version_id,
            auto_confirm=auto_confirm,
            reviewer=reviewer.strip() or "architect",
        )
        updates = _workspace_updates(project_id)
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc

    overlay_image = str(overlay_path) if overlay_path and overlay_path.exists() else updates[2]
    status = (
        f"Detected {len(detection.regions)} region(s) via `{detection.provider}` "
        f"for `{detection.inferred_room_type or detection.room_type}`. "
        f"Created/updated {len(created)} proposed region(s)."
    )
    skipped = detection.metadata.get("skipped_invalid_regions", [])
    if skipped:
        region_codes = ", ".join(
            str(item.get("region_code", "unnamed region")) for item in skipped
        )
        status += (
            f" Skipped {len(skipped)} invalid out-of-frame region(s): {region_codes}."
        )
    if auto_confirm:
        status += " Editable regions were auto-confirmed."
    else:
        status += " Review proposed regions, then confirm before retrieval."
    return (
        status,
        overlay_image,
        updates[0],
        updates[1],
        updates[3],
        updates[4],
        updates[5],
    )


def confirm_detected_regions(state_json: str, reviewer: str) -> tuple[Any, ...]:
    try:
        state = json.loads(state_json or "{}")
        project_id = state["project_id"]
        direction_id = state["concept_direction_id"]
        version_id = state["concept_version_id"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise gr.Error("Load a concept board before confirming regions.") from exc

    repo, _settings, _ = _boot()
    try:
        confirmed = confirm_proposed_regions(
            repo=repo,
            concept_direction_id=direction_id,
            concept_version_id=version_id,
            reviewer=reviewer.strip() or "architect",
        )
        updates = _workspace_updates(project_id)
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc
    return (
        f"Confirmed {len(confirmed)} proposed region(s) for product retrieval.",
        *updates,
    )


def retrieve_candidates(
    state_json: str,
    region_choice: str | None,
    top_k: int,
    use_channel3: bool,
) -> tuple[str, list[list[Any]], Any, str, Any, Any, str | None]:
    try:
        state = json.loads(state_json or "{}")
        version_id = state["concept_version_id"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise gr.Error("Load a concept board before retrieving products.") from exc
    region_id = _parse_choice(region_choice)
    if region_id is None:
        raise gr.Error("Select a confirmed editable region.")

    repo, settings, _ = _boot()
    try:
        run, candidates = retrieve_product_candidates(
            repo=repo,
            design_region_id=region_id,
            concept_version_id=version_id,
            top_k=int(top_k),
            settings=settings,
            use_channel3=use_channel3 or settings.catalogue_provider == "channel3",
        )
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc

    catalog, gallery, first_choice = _build_candidate_catalog(candidates)
    first_entry = (catalog.get("candidates") or {}).get(_parse_choice(first_choice) or "", {})
    image_dropdown, hero = _image_choice_updates(first_entry.get("product_images") or [])

    rows: list[list[Any]] = []
    choices: list[str] = []
    for candidate in candidates:
        rationale = candidate.match_rationale_json
        product = rationale.get("product_name", "Unknown product")
        supplier = rationale.get("supplier_name", "Unknown supplier")
        price = rationale.get("unit_price", "—")
        explanation = rationale.get("explanation", {})
        score = explanation.get("type_score", 0) * 0.5 + explanation.get("region_match", 0) * 0.3 + explanation.get("budget_score", 0) * 0.2
        rows.append(
            [
                candidate.region_candidate_id,
                product,
                supplier,
                f"£{price}",
                f"{score:.2f}",
                candidate.candidate_status.value,
            ]
        )
        choices.append(f"{candidate.region_candidate_id} | {product} (£{price})")
    return (
        f"Retrieved {len(candidates)} candidates in run `{run.product_retrieval_run_id}`.",
        rows,
        gr.update(choices=choices, value=first_choice or (choices[0] if choices else None)),
        json.dumps(catalog),
        gallery,
        image_dropdown,
        hero,
    )


def preview_in_room(
    state_json: str,
    catalog_json: str,
    candidate_choice: str | None,
    product_image_choice: str | None,
    cumulative_stack: bool,
    cumulative_mode: str | None,
) -> tuple[str, str | None]:
    try:
        state = json.loads(state_json or "{}")
        version_id = state["concept_version_id"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise gr.Error("Load a concept board before previewing.") from exc
    candidate_id = _parse_choice(candidate_choice)
    if candidate_id is None:
        raise gr.Error("Choose a candidate first.")
    product_image_uri = _resolve_staging_image_uri(catalog_json, candidate_choice, product_image_choice)

    repo, settings, file_store = _boot()
    try:
        preview = generate_substitution_preview(
            repo=repo,
            settings=settings,
            file_store=file_store,
            region_candidate_id=candidate_id,
            concept_version_id=version_id,
            product_image_uri=product_image_uri,
            cumulative_enabled=cumulative_stack,
            cumulative_mode=cumulative_mode,
        )
    except (ConceptBoardError, StagingError) as exc:
        raise gr.Error(str(exc)) from exc

    preview_path = settings.resolve(preview.preview_asset_uri)
    preview_image = str(preview_path) if preview_path.exists() else None
    disclaimer = preview.disclaimer or settings.virtual_staging.visual_preview_disclaimer
    mode = resolve_cumulative_preview_mode(
        settings=settings,
        cumulative_enabled=cumulative_stack,
        ui_mode=cumulative_mode,
    )
    mode_label = {
        "single": "single region",
        "local_composite": "local cumulative composite",
        "gemini_chain": "chained Gemini edits",
    }.get(mode, mode)
    return (
        f"Generated in-room preview ({mode_label}). {disclaimer} Approve when ready to record procurement.",
        preview_image,
    )


def approve_candidate_selection(
    state_json: str,
    catalog_json: str,
    candidate_choice: str | None,
    product_image_choice: str | None,
    selected_by: str,
    approver: str,
) -> tuple[str, Any, Any]:
    try:
        state = json.loads(state_json or "{}")
        project_id = state["project_id"]
        version_id = state["concept_version_id"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise gr.Error("Load a concept board before approving a selection.") from exc
    candidate_id = _parse_choice(candidate_choice)
    if candidate_id is None:
        raise gr.Error("Choose a candidate first.")
    product_image_uri = _resolve_staging_image_uri(catalog_json, candidate_choice, product_image_choice)

    repo, settings, _ = _boot()
    try:
        selection = select_region_candidate(
            repo=repo,
            settings=settings,
            region_candidate_id=candidate_id,
            concept_version_id=version_id,
            selected_by=selected_by.strip() or "client",
            selected_product_image_uri=product_image_uri,
        )
        approve_region_selection(
            repo=repo,
            region_selection_id=selection.region_selection_id,
            approver=approver.strip() or "architect",
        )
        updates = _workspace_updates(project_id)
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc
    return (
        f"Candidate approved for procurement as `{selection.region_selection_id}`. "
        "Add more regions or commit a new concept version.",
        updates[4],
        updates[0],
    )


def preview_select_and_approve(
    state_json: str,
    catalog_json: str,
    candidate_choice: str | None,
    product_image_choice: str | None,
    cumulative_stack: bool,
    cumulative_mode: str | None,
    selected_by: str,
    approver: str,
) -> tuple[str, str | None, Any, Any]:
    preview_status, preview_image = preview_in_room(
        state_json,
        catalog_json,
        candidate_choice,
        product_image_choice,
        cumulative_stack,
        cumulative_mode,
    )
    approve_status, selections_table, board_state = approve_candidate_selection(
        state_json,
        catalog_json,
        candidate_choice,
        product_image_choice,
        selected_by,
        approver,
    )
    return (
        f"{preview_status} {approve_status}",
        preview_image,
        selections_table,
        board_state,
    )


def commit_version(state_json: str, reason: str, approver: str) -> tuple[Any, ...]:
    try:
        state = json.loads(state_json or "{}")
        project_id = state["project_id"]
        direction_id = state["concept_direction_id"]
        parent_version_id = state["concept_version_id"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise gr.Error("Load a concept board before committing a version.") from exc

    repo, settings, _ = _boot()
    try:
        version = create_concept_version_from_selections(
            repo=repo,
            settings=settings,
            concept_direction_id=direction_id,
            parent_concept_version_id=parent_version_id,
            version_reason=reason.strip() or "Applied approved selections",
            approver=approver.strip() or "architect",
        )
        updates = _workspace_updates(project_id)
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc
    return (f"Created immutable concept version `v{version.version_number}`.", *updates)


def create_and_export_procurement(state_json: str, schedule_name: str) -> tuple[str, str | None]:
    try:
        state = json.loads(state_json or "{}")
        project_id = state["project_id"]
        version_id = state["concept_version_id"]
    except (json.JSONDecodeError, KeyError) as exc:
        raise gr.Error("Load a concept board before creating procurement.") from exc

    repo, settings, _ = _boot()
    try:
        schedule, items = create_procurement_schedule(
            repo=repo,
            settings=settings,
            project_id=project_id,
            concept_version_id=version_id,
            schedule_name=schedule_name.strip() or "Procurement schedule",
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
    except ConceptBoardError as exc:
        raise gr.Error(str(exc)) from exc

    csv_path = settings.resolve(settings.paths.exports) / "procurement" / f"{schedule.procurement_schedule_id}.csv"
    return (
        f"Approved schedule `{schedule.procurement_schedule_id}` with {len(items)} item(s). "
        f"Export manifest: `{export.export_id}`.",
        str(csv_path) if csv_path.exists() else None,
    )


def build_concept_board_tab(*, pipeline_state: gr.State | None = None) -> None:
    """Build the visual MVP workflow over the concept-board application layer."""
    board_state = gr.State("{}")
    candidate_catalog_state = gr.State("{}")

    gr.Markdown(
        "## Concept Board\n"
        "Visualize a generated concept, define editable regions, compare real products, "
        "approve a selection, and export its procurement schedule. "
        "Use **Open concept board** with a project ID (and variant ID on first open). "
        "2D product staging generates a **visual preview only** — not construction-accurate "
        "and not proof of fit."
    )

    with gr.Row():
        project_id = gr.Textbox(
            label="Vision Engine project ID",
            placeholder="proj_... from Tab 1/4 or a previous run",
        )
        variant_id = gr.Textbox(
            label="Variant ID (required on first open)",
            placeholder="var_... from Tab 1/4 or a previous run",
        )
        board_name = gr.Textbox(label="Board name (optional)")
    with gr.Row():
        open_board_button = gr.Button("Open concept board", variant="primary")
        if pipeline_state is not None:
            session_variant_choice = gr.Dropdown(
                label="Session variant",
                choices=[],
                value=None,
            )
            use_session_button = gr.Button("Use current session IDs")
        else:
            session_variant_choice = None
            use_session_button = None
    with gr.Row():
        catalogue_name = gr.Textbox(label="Catalogue snapshot", value="local-v1")
        catalogue_button = gr.Button("Load sample catalogue")
    bootstrap_status = gr.Markdown()
    catalogue_status = gr.Markdown()

    workspace_context = gr.Markdown("_Load a concept board to begin._")
    with gr.Row():
        concept_image = gr.Image(label="Active concept version", height=380)
        preview_image = gr.Image(
            label="Selected-product preview (visual preview only — not for ordering)",
            height=380,
        )

    with gr.Row():
        regions_table = gr.Dataframe(
            headers=["region_id", "code", "type", "status", "confidence", "editability"],
            label="Design regions",
            interactive=False,
        )
        selections_table = gr.Dataframe(
            headers=["selection_id", "region_id", "status", "quantity", "approval"],
            label="Approved selections",
            interactive=False,
        )

    gr.Markdown("### 1. Detect regions from concept")
    with gr.Row():
        detect_reviewer = gr.Textbox(label="Detection reviewer", value="architect")
        auto_confirm_regions = gr.Checkbox(
            label="Auto-confirm editable detected regions",
            value=False,
        )
    with gr.Row():
        detect_regions_button = gr.Button("Detect regions from concept", variant="primary")
        confirm_regions_button = gr.Button("Confirm all proposed regions")
    detection_status = gr.Markdown()

    gr.Markdown("### 2. Define an editable region (manual fallback)")
    with gr.Row():
        region_code = gr.Textbox(label="Region code", placeholder="sofa_01")
        region_type = gr.Dropdown(REGION_TYPES, value="sofa", label="Region type")
        region_name = gr.Textbox(label="Display name", placeholder="Main sofa")
        region_budget = gr.Number(label="Maximum budget (GBP)", value=3000, precision=2)
    reviewer = gr.Textbox(label="Architect / operator", value="architect")
    add_region_button = gr.Button("Add and confirm region")
    region_status = gr.Markdown()

    gr.Markdown("### 3. Compare real product candidates")
    with gr.Row():
        region_choice = gr.Dropdown(label="Confirmed editable region", choices=[])
        top_k = gr.Slider(1, 10, value=5, step=1, label="Candidates")
        use_channel3 = gr.Checkbox(
            label="Search live Channel3 catalogue",
            value=False,
        )
        retrieve_button = gr.Button("Retrieve products")
    retrieval_status = gr.Markdown()
    candidate_gallery = gr.Gallery(
        label="Candidate catalogue images",
        columns=5,
        height=220,
        object_fit="contain",
    )
    candidates_table = gr.Dataframe(
        headers=["candidate_id", "product", "supplier", "price", "fit score", "status"],
        label="Candidate comparison",
        interactive=False,
    )
    candidate_choice = gr.Dropdown(label="Selected candidate", choices=[])
    product_image_gallery = gr.Gallery(
        label="Product images for selected candidate",
        columns=4,
        height=180,
        object_fit="contain",
    )
    product_image_choice = gr.Dropdown(
        label="Image used for in-room preview",
        choices=[],
    )
    product_catalog_image = gr.Image(
        label="Selected catalogue image",
        height=240,
        interactive=False,
    )
    _, default_settings, _ = _boot()
    with gr.Row():
        cumulative_stack = gr.Checkbox(
            label="Stack approved selections in preview",
            value=default_settings.virtual_staging.cumulative_preview_enabled_default,
        )
        cumulative_mode = gr.Dropdown(
            label="Cumulative preview mode",
            choices=[
                "Use config default",
                "Single region only",
                "Local multi-mask composite",
                "Chain Gemini edits",
            ],
            value="Use config default",
        )
    with gr.Row():
        selected_by = gr.Textbox(label="Client / selector", value="client")
        selection_approver = gr.Textbox(label="Architect approver", value="architect")
    with gr.Row():
        preview_candidate_button = gr.Button("Preview in room", variant="primary")
        approve_candidate_button = gr.Button("Approve selection")
        approve_preview_button = gr.Button("Preview, select, and approve")
    selection_status = gr.Markdown()

    gr.Markdown("### 4. Commit an immutable concept version")
    with gr.Row():
        version_reason = gr.Textbox(
            label="Version reason",
            value="Applied approved product selections",
        )
        commit_approver = gr.Textbox(label="Approver", value="architect")
        commit_button = gr.Button("Create next concept version")
    version_status = gr.Markdown()

    gr.Markdown("### 5. Procurement and export")
    with gr.Row():
        schedule_name = gr.Textbox(label="Schedule name", value="Concept board procurement")
        schedule_button = gr.Button("Approve schedule and export CSV", variant="primary")
    procurement_status = gr.Markdown()
    procurement_file = gr.File(label="Procurement CSV")

    open_board_button.click(
        open_concept_board,
        inputs=[project_id, variant_id, board_name],
        outputs=[
            bootstrap_status,
            board_state,
            workspace_context,
            concept_image,
            regions_table,
            selections_table,
            region_choice,
        ],
    )
    if pipeline_state is not None and use_session_button is not None and session_variant_choice is not None:
        use_session_button.click(
            fill_ids_from_pipeline,
            inputs=[pipeline_state, session_variant_choice],
            outputs=[project_id, variant_id, bootstrap_status],
        )
        pipeline_state.change(
            pipeline_variant_choices,
            inputs=[pipeline_state],
            outputs=[session_variant_choice],
        )
    detect_regions_button.click(
        detect_regions,
        inputs=[board_state, detect_reviewer, auto_confirm_regions],
        outputs=[
            detection_status,
            concept_image,
            board_state,
            workspace_context,
            regions_table,
            selections_table,
            region_choice,
        ],
    )
    confirm_regions_button.click(
        confirm_detected_regions,
        inputs=[board_state, detect_reviewer],
        outputs=[
            detection_status,
            board_state,
            workspace_context,
            concept_image,
            regions_table,
            selections_table,
            region_choice,
        ],
    )
    catalogue_button.click(load_catalogue, inputs=[catalogue_name], outputs=[catalogue_status])
    add_region_button.click(
        create_region,
        inputs=[board_state, region_code, region_type, region_name, region_budget, reviewer],
        outputs=[
            region_status,
            board_state,
            workspace_context,
            concept_image,
            regions_table,
            selections_table,
            region_choice,
        ],
    )
    retrieve_button.click(
        retrieve_candidates,
        inputs=[board_state, region_choice, top_k, use_channel3],
        outputs=[
            retrieval_status,
            candidates_table,
            candidate_choice,
            candidate_catalog_state,
            candidate_gallery,
            product_image_choice,
            product_catalog_image,
        ],
    )
    candidate_choice.change(
        _sync_candidate_panels,
        inputs=[candidate_catalog_state, candidate_choice],
        outputs=[product_image_gallery, product_image_choice, product_catalog_image],
    )
    product_image_choice.change(
        lambda image_choice: _parse_image_choice(image_choice),
        inputs=[product_image_choice],
        outputs=[product_catalog_image],
    )
    preview_candidate_button.click(
        preview_in_room,
        inputs=[
            board_state,
            candidate_catalog_state,
            candidate_choice,
            product_image_choice,
            cumulative_stack,
            cumulative_mode,
        ],
        outputs=[selection_status, preview_image],
    )
    approve_candidate_button.click(
        approve_candidate_selection,
        inputs=[
            board_state,
            candidate_catalog_state,
            candidate_choice,
            product_image_choice,
            selected_by,
            selection_approver,
        ],
        outputs=[selection_status, selections_table, board_state],
    )
    approve_preview_button.click(
        preview_select_and_approve,
        inputs=[
            board_state,
            candidate_catalog_state,
            candidate_choice,
            product_image_choice,
            cumulative_stack,
            cumulative_mode,
            selected_by,
            selection_approver,
        ],
        outputs=[selection_status, preview_image, selections_table, board_state],
    )
    commit_button.click(
        commit_version,
        inputs=[board_state, version_reason, commit_approver],
        outputs=[
            version_status,
            board_state,
            workspace_context,
            concept_image,
            regions_table,
            selections_table,
            region_choice,
        ],
    )
    schedule_button.click(
        create_and_export_procurement,
        inputs=[board_state, schedule_name],
        outputs=[procurement_status, procurement_file],
    )

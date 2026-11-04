from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vision_engine.concept_board.domain.enums import SelectionStatus
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import FileStore, sha256_file
from vision_engine.settings import AppSettings
from vision_engine.virtual_staging.application.masks import composite_product_into_region
from vision_engine.virtual_staging.application.staging_2d import (
    ProductStagingResult,
    StagingRepository,
    _resolve_product_reference,
    persist_cumulative_local_preview,
    run_2d_product_staging,
)
from vision_engine.virtual_staging.domain.errors import StagingError

CUMULATIVE_PREVIEW_MODES = {
    "single",
    "local_composite",
    "gemini_chain",
}


@dataclass(frozen=True)
class StagingLayer:
    region_candidate_id: str
    design_region_id: str
    region_code: str
    product_name: str
    geometry_json: dict
    product_image_uri: str | None


def resolve_cumulative_preview_mode(
    *,
    settings: AppSettings,
    cumulative_enabled: bool,
    ui_mode: str | None,
) -> str:
    if not cumulative_enabled:
        return "single"
    if ui_mode and ui_mode not in {"", "Use config default", "config default"}:
        mapping = {
            "Single region only": "single",
            "Local multi-mask composite": "local_composite",
            "Chain Gemini edits": "gemini_chain",
            "local_composite": "local_composite",
            "gemini_chain": "gemini_chain",
            "single": "single",
        }
        resolved = mapping.get(ui_mode.strip())
        if resolved:
            return resolved
    mode = settings.virtual_staging.cumulative_preview_mode.lower().strip()
    if mode not in CUMULATIVE_PREVIEW_MODES:
        return "local_composite"
    return mode


def _image_uri_for_candidate(
    candidate,
    *,
    override_uri: str | None = None,
) -> str | None:
    if override_uri:
        return override_uri
    rationale = candidate.match_rationale_json or {}
    images = rationale.get("product_images") or []
    if images:
        return images[0].get("url")
    return rationale.get("reference_image_uri")


def collect_staging_layers(
    *,
    repo: ConceptBoardRepositoryMixin,
    concept_version_id: str,
    current_region_candidate_id: str,
    current_product_image_uri: str | None,
) -> list[StagingLayer]:
    current = repo.get_region_candidate(current_region_candidate_id)
    if current is None:
        raise StagingError(f"Candidate not found: {current_region_candidate_id}")

    current_region = repo.get_design_region(current.design_region_id)
    if current_region is None:
        raise StagingError("Current design region not found")

    layers: list[StagingLayer] = []
    selections = repo.list_region_selections(concept_version_id)
    approved = sorted(
        [
            selection
            for selection in selections
            if selection.selection_status
            in {SelectionStatus.CLIENT_SELECTED, SelectionStatus.ARCHITECT_APPROVED}
        ],
        key=lambda item: item.selected_at,
    )

    for selection in approved:
        if selection.design_region_id == current.design_region_id:
            continue
        candidate = repo.get_region_candidate(selection.region_candidate_id)
        if candidate is None:
            continue
        region = repo.get_design_region(candidate.design_region_id)
        geometry = repo.get_region_geometry_for_version(
            candidate.design_region_id, concept_version_id
        )
        if region is None or geometry is None:
            continue
        rationale = candidate.match_rationale_json or {}
        layers.append(
            StagingLayer(
                region_candidate_id=candidate.region_candidate_id,
                design_region_id=candidate.design_region_id,
                region_code=region.region_code,
                product_name=str(rationale.get("product_name") or region.display_name),
                geometry_json=geometry.geometry_json,
                product_image_uri=selection.selected_product_image_uri
                or _image_uri_for_candidate(candidate),
            )
        )

    current_geometry = repo.get_region_geometry_for_version(
        current.design_region_id, concept_version_id
    )
    if current_geometry is None:
        raise StagingError("Region geometry is required for cumulative staging")
    current_rationale = current.match_rationale_json or {}
    layers.append(
        StagingLayer(
            region_candidate_id=current.region_candidate_id,
            design_region_id=current.design_region_id,
            region_code=current_region.region_code,
            product_name=str(current_rationale.get("product_name") or current_region.display_name),
            geometry_json=current_geometry.geometry_json,
            product_image_uri=current_product_image_uri
            or _image_uri_for_candidate(current),
        )
    )
    return layers


def _resolve_layer_product_path(
    *,
    settings: AppSettings,
    staging_dir: Path,
    layer: StagingLayer,
    repo: ConceptBoardRepositoryMixin,
) -> Path:
    candidate = repo.get_region_candidate(layer.region_candidate_id)
    if candidate is None or not candidate.product_variant_id:
        raise StagingError(f"Candidate details missing for {layer.region_candidate_id}")
    product_details = repo.get_product_variant_details(candidate.product_variant_id)
    if product_details is None:
        raise StagingError("Product variant details are required for cumulative staging")
    product, variant = product_details
    layer_dir = staging_dir / layer.region_candidate_id
    reference_path, _, _ = _resolve_product_reference(
        settings=settings,
        staging_dir=layer_dir,
        product=product,
        variant=variant,
        attributes=variant.attributes_json,
        product_image_uri=layer.product_image_uri,
    )
    return reference_path


def run_local_composite_staging(
    *,
    repo: StagingRepository,
    settings: AppSettings,
    file_store: FileStore,
    region_candidate_id: str,
    concept_version_id: str,
    layers: list[StagingLayer],
    provider: str | None = None,
    model_name: str | None = None,
    prompt_version: str | None = None,
) -> ProductStagingResult:
    version = repo.get_concept_version(concept_version_id)
    if version is None:
        raise StagingError(f"Concept version not found: {concept_version_id}")
    asset = repo.get_primary_concept_asset(concept_version_id)
    if asset is None:
        raise StagingError("Primary concept asset not found")

    staging_dir = (
        settings.resolve(settings.paths.staging)
        / version.concept_direction_id
        / region_candidate_id
        / "cumulative_local"
    )
    staging_dir.mkdir(parents=True, exist_ok=True)
    working_path = settings.resolve(asset.storage_uri)
    for index, layer in enumerate(layers):
        product_path = _resolve_layer_product_path(
            settings=settings,
            staging_dir=staging_dir,
            layer=layer,
            repo=repo,
        )
        step_path = staging_dir / f"composite_step_{index:02d}.png"
        composite_product_into_region(
            room_image_path=working_path,
            product_image_path=product_path,
            geometry_json=layer.geometry_json,
            dest=step_path,
        )
        working_path = step_path

    final_output = staging_dir / "cumulative_preview.png"
    final_output.write_bytes(working_path.read_bytes())
    return persist_cumulative_local_preview(
        repo=repo,
        settings=settings,
        region_candidate_id=region_candidate_id,
        concept_version_id=concept_version_id,
        output_path=final_output,
        cumulative_layer_count=len(layers),
    )


def run_gemini_chain_staging(
    *,
    repo: StagingRepository,
    settings: AppSettings,
    file_store: FileStore,
    region_candidate_id: str,
    concept_version_id: str,
    layers: list[StagingLayer],
    provider: str | None = None,
    model_name: str | None = None,
    prompt_version: str | None = None,
) -> ProductStagingResult:
    if not layers:
        raise StagingError("No staging layers supplied for cumulative preview")

    version = repo.get_concept_version(concept_version_id)
    if version is None:
        raise StagingError(f"Concept version not found: {concept_version_id}")
    asset = repo.get_primary_concept_asset(concept_version_id)
    if asset is None:
        raise StagingError("Primary concept asset not found")

    working_path = settings.resolve(asset.storage_uri)
    result: ProductStagingResult | None = None
    for index, layer in enumerate(layers):
        result = run_2d_product_staging(
            repo=repo,
            settings=settings,
            file_store=file_store,
            region_candidate_id=layer.region_candidate_id,
            concept_version_id=concept_version_id,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
            product_image_uri=layer.product_image_uri,
            source_image_path=working_path,
            chain_step=index,
            cumulative_mode="gemini_chain",
            cumulative_layer_count=len(layers),
            preview_candidate_id=region_candidate_id if index == len(layers) - 1 else None,
        )
        working_path = settings.resolve(result.substitution_preview.preview_asset_uri)

    if result is None:
        raise StagingError("Gemini chain staging produced no output")
    return result


def run_cumulative_product_staging(
    *,
    repo: StagingRepository,
    settings: AppSettings,
    file_store: FileStore,
    region_candidate_id: str,
    concept_version_id: str,
    cumulative_mode: str,
    current_product_image_uri: str | None = None,
    provider: str | None = None,
    model_name: str | None = None,
    prompt_version: str | None = None,
) -> ProductStagingResult:
    if cumulative_mode == "single":
        return run_2d_product_staging(
            repo=repo,
            settings=settings,
            file_store=file_store,
            region_candidate_id=region_candidate_id,
            concept_version_id=concept_version_id,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
            product_image_uri=current_product_image_uri,
            cumulative_mode="single",
        )

    layers = collect_staging_layers(
        repo=repo,
        concept_version_id=concept_version_id,
        current_region_candidate_id=region_candidate_id,
        current_product_image_uri=current_product_image_uri,
    )
    if cumulative_mode == "local_composite":
        return run_local_composite_staging(
            repo=repo,
            settings=settings,
            file_store=file_store,
            region_candidate_id=region_candidate_id,
            concept_version_id=concept_version_id,
            layers=layers,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )
    if cumulative_mode == "gemini_chain":
        return run_gemini_chain_staging(
            repo=repo,
            settings=settings,
            file_store=file_store,
            region_candidate_id=region_candidate_id,
            concept_version_id=concept_version_id,
            layers=layers,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )
    raise StagingError(f"Unsupported cumulative preview mode: {cumulative_mode}")

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from vision_engine.concept_board.application.regions import (
    add_region_geometry,
    confirm_design_region,
    create_design_region,
)
from vision_engine.concept_board.domain.enums import DesignRegionLifecycle, RegionGeometryType
from vision_engine.concept_board.domain.errors import RegionError
from vision_engine.concept_board.domain.models import DesignRegionRecord
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import new_id, sha256_file
from vision_engine.infrastructure.sqlite_repository import utcnow
from vision_engine.region_detection.factory import build_region_detector
from vision_engine.region_detection.models import RegionDetectionResult
from vision_engine.region_detection.overlay import render_detection_overlay
from vision_engine.settings import AppSettings
from vision_engine.virtual_staging.application.masks import (
    clamp_normalised_bbox,
    write_region_mask_png,
)


def _existing_region_codes(
    repo: ConceptBoardRepositoryMixin,
    concept_direction_id: str,
) -> dict[str, DesignRegionRecord]:
    return {
        region.region_code: region
        for region in repo.list_design_regions(concept_direction_id)
        if region.lifecycle_status != DesignRegionLifecycle.RETIRED
    }


def _write_detection_manifest(
    *,
    settings: AppSettings,
    concept_board_id: str,
    detection: RegionDetectionResult,
) -> Path:
    run_id = new_id("rdr")
    dest_dir = settings.resolve(settings.paths.concept_boards) / concept_board_id / "detections"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{run_id}.json"
    payload = {
        "detection_run_id": run_id,
        "provider": detection.provider,
        "model_name": detection.model_name,
        "room_type": detection.room_type,
        "inferred_room_type": detection.inferred_room_type,
        "concept_version_id": detection.concept_version_id,
        "image_uri": detection.image_uri,
        "metadata": detection.metadata,
        "regions": [
            {
                "region_code": region.region_code,
                "region_type": region.region_type,
                "display_name": region.display_name,
                "geometry_json": region.geometry_json,
                "confidence": region.confidence,
                "detection_kind": region.detection_kind,
                "is_fixed": region.is_fixed,
                "rationale": region.rationale,
            }
            for region in detection.regions
        ],
    }
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return dest


def _validate_detected_regions(detection: RegionDetectionResult) -> list[dict[str, str]]:
    """Keep drawable detections and record malformed AI proposals for the UI."""
    valid_regions = []
    skipped: list[dict[str, str]] = []
    for proposal in detection.regions:
        try:
            geometry_json = clamp_normalised_bbox(proposal.geometry_json)
        except ValueError as exc:
            skipped.append(
                {
                    "region_code": proposal.region_code,
                    "reason": str(exc),
                }
            )
            continue
        valid_regions.append(replace(proposal, geometry_json=geometry_json))

    detection.regions = valid_regions
    if skipped:
        detection.metadata = {
            **detection.metadata,
            "skipped_invalid_regions": skipped,
        }
    return skipped


def detect_regions_for_concept_version(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings,
    project_id: str,
    concept_version_id: str,
    auto_confirm: bool = False,
    reviewer: str = "architect",
    max_budget: float | None = None,
) -> tuple[RegionDetectionResult, list[DesignRegionRecord], Path | None]:
    project = repo.get_project(project_id)
    if project is None:
        raise RegionError(f"Project not found: {project_id}")

    board = repo.get_concept_board_for_project(project_id)
    if board is None:
        raise RegionError(f"No concept board for project: {project_id}")

    version = repo.get_concept_version(concept_version_id)
    if version is None:
        raise RegionError(f"Concept version not found: {concept_version_id}")

    directions = repo.list_directions_for_board(board.concept_board_id)
    if not directions:
        raise RegionError("Concept board has no directions")
    direction = directions[0]

    asset = repo.get_primary_concept_asset(concept_version_id)
    if asset is None:
        raise RegionError("Concept version has no primary render asset")

    image_path = settings.resolve(asset.storage_uri)
    if not image_path.exists():
        raise RegionError(f"Concept image not found: {image_path}")

    detector = build_region_detector(settings)
    detection = detector.detect_regions(
        image_path=str(image_path),
        room_type=project.room_type,
        concept_version_id=concept_version_id,
        image_uri=asset.storage_uri,
    )
    _validate_detected_regions(detection)
    _write_detection_manifest(
        settings=settings,
        concept_board_id=board.concept_board_id,
        detection=detection,
    )

    existing = _existing_region_codes(repo, direction.concept_direction_id)
    created: list[DesignRegionRecord] = []
    overlay_path: Path | None = None

    for proposal in detection.regions:
        if proposal.region_code in existing:
            region = existing[proposal.region_code]
            if region.lifecycle_status == DesignRegionLifecycle.CONFIRMED:
                continue
        else:
            region = create_design_region(
                repo=repo,
                concept_direction_id=direction.concept_direction_id,
                region_code=proposal.region_code,
                region_type=proposal.region_type,
                display_name=proposal.display_name,
                is_fixed=proposal.is_fixed,
            )
            existing[proposal.region_code] = region
            created.append(region)

        mask_dir = (
            settings.resolve(settings.paths.concept_boards)
            / board.concept_board_id
            / "regions"
            / region.design_region_id
            / concept_version_id
        )
        mask_path = mask_dir / "mask.png"
        write_region_mask_png(
            image_size=(asset.width or 1024, asset.height or 768),
            geometry_json=proposal.geometry_json,
            dest=mask_path,
        )
        add_region_geometry(
            repo=repo,
            design_region_id=region.design_region_id,
            concept_version_id=concept_version_id,
            geometry_type=RegionGeometryType.BOUNDING_BOX,
            geometry_json=proposal.geometry_json,
            mask_uri=str(mask_path.relative_to(settings.project_root)),
            mask_sha256=sha256_file(mask_path),
            confidence=proposal.confidence,
            source=f"vision:{detection.provider}",
        )

        if auto_confirm and not region.is_fixed:
            region = confirm_design_region(
                repo=repo,
                design_region_id=region.design_region_id,
                reviewer=reviewer,
                concept_version_id=concept_version_id,
            )

    overlay_dest = (
        settings.resolve(settings.paths.concept_boards)
        / board.concept_board_id
        / "detections"
        / f"{concept_version_id}_overlay.png"
    )
    overlay_path = render_detection_overlay(
        image_path=image_path,
        regions=detection.regions,
        dest=overlay_dest,
    )

    return detection, created, overlay_path


def confirm_proposed_regions(
    *,
    repo: ConceptBoardRepositoryMixin,
    concept_direction_id: str,
    concept_version_id: str,
    reviewer: str = "architect",
    region_ids: list[str] | None = None,
) -> list[DesignRegionRecord]:
    confirmed: list[DesignRegionRecord] = []
    for region in repo.list_design_regions(concept_direction_id):
        if region.lifecycle_status != DesignRegionLifecycle.PROPOSED:
            continue
        if region_ids and region.design_region_id not in region_ids:
            continue
        if repo.get_region_geometry_for_version(region.design_region_id, concept_version_id) is None:
            continue
        confirmed.append(
            confirm_design_region(
                repo=repo,
                design_region_id=region.design_region_id,
                reviewer=reviewer,
                concept_version_id=concept_version_id,
            )
        )
    if region_ids and not confirmed:
        raise RegionError("No matching proposed regions with geometry to confirm")
    if not region_ids and not confirmed:
        raise RegionError("No proposed regions with geometry available to confirm")
    return confirmed

from __future__ import annotations

from vision_engine.concept_board.domain.enums import (
    ApprovalType,
    DesignRegionLifecycle,
    RegionGeometryType,
    RequirementSeverity,
)
from vision_engine.concept_board.domain.errors import RegionError
from vision_engine.concept_board.domain.models import (
    ApprovalEventRecord,
    DesignRegionRecord,
    RegionGeometryRecord,
    RegionRequirementRecord,
)
from vision_engine.concept_board.domain.validation import assert_not_fixed_region
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import utcnow


def create_design_region(
    *,
    repo: ConceptBoardRepositoryMixin,
    concept_direction_id: str,
    region_code: str,
    region_type: str,
    display_name: str,
    is_fixed: bool = False,
) -> DesignRegionRecord:
    now = utcnow()
    record = DesignRegionRecord(
        design_region_id=new_id("dr"),
        concept_direction_id=concept_direction_id,
        region_code=region_code,
        region_type=region_type,
        display_name=display_name,
        lifecycle_status=DesignRegionLifecycle.PROPOSED,
        is_fixed=is_fixed,
        created_at=now,
    )
    repo.save_design_region(record)
    return record


def confirm_design_region(
    *,
    repo: ConceptBoardRepositoryMixin,
    design_region_id: str,
    reviewer: str,
    concept_version_id: str,
) -> DesignRegionRecord:
    region = repo.get_design_region(design_region_id)
    if region is None:
        raise RegionError(f"Region not found: {design_region_id}")
    updated = region.model_copy(update={"lifecycle_status": DesignRegionLifecycle.CONFIRMED})
    repo.save_design_region(updated)
    repo.save_approval_event(
        ApprovalEventRecord(
            approval_event_id=new_id("ae"),
            concept_version_id=concept_version_id,
            user_id=reviewer,
            approval_type=ApprovalType.REGION_GEOMETRY,
            decision="approved",
            comments=f"Confirmed region {region.region_code}",
            created_at=utcnow(),
        )
    )
    return updated


def add_region_geometry(
    *,
    repo: ConceptBoardRepositoryMixin,
    design_region_id: str,
    concept_version_id: str,
    geometry_type: RegionGeometryType,
    geometry_json: dict,
    mask_uri: str | None = None,
    mask_sha256: str | None = None,
    confidence: float | None = None,
    source: str = "manual",
) -> RegionGeometryRecord:
    region = repo.get_design_region(design_region_id)
    if region is None:
        raise RegionError(f"Region not found: {design_region_id}")
    record = RegionGeometryRecord(
        region_geometry_id=new_id("rg"),
        design_region_id=design_region_id,
        concept_version_id=concept_version_id,
        geometry_type=geometry_type,
        geometry_json=geometry_json,
        mask_uri=mask_uri,
        mask_sha256=mask_sha256,
        confidence=confidence,
        source=source,
        created_at=utcnow(),
    )
    repo.save_region_geometry(record)
    return record


def add_region_requirement(
    *,
    repo: ConceptBoardRepositoryMixin,
    design_region_id: str,
    requirement_type: str,
    operator: str,
    value_json: dict,
    severity: RequirementSeverity = RequirementSeverity.SOFT,
    source: str = "manual",
) -> RegionRequirementRecord:
    region = repo.get_design_region(design_region_id)
    if region is None:
        raise RegionError(f"Region not found: {design_region_id}")
    assert_not_fixed_region(region.is_fixed, "add requirement")
    record = RegionRequirementRecord(
        region_requirement_id=new_id("rr"),
        design_region_id=design_region_id,
        requirement_type=requirement_type,
        operator=operator,
        value_json=value_json,
        severity=severity,
        source=source,
        created_at=utcnow(),
    )
    repo.save_region_requirement(record)
    return record

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from vision_engine.virtual_staging.domain.enums import (
    EvidenceGrade,
    ImageEditRunStatus,
    StagingConditionType,
    StagingMode,
    StagingRequestStatus,
    VirtualStagingOutputType,
)


class StagingRequestRecord(BaseModel):
    staging_request_id: str
    concept_version_id: str
    design_region_id: str
    region_candidate_id: str
    staging_mode: StagingMode
    requested_quality_level: str = "mvp"
    status: StagingRequestStatus
    disclaimer: str
    created_at: datetime


class StagingConditionRecord(BaseModel):
    staging_condition_id: str
    staging_request_id: str
    condition_type: StagingConditionType
    artifact_reference_json: dict[str, Any] = Field(default_factory=dict)
    content_sha256: str
    created_at: datetime


class ImageEditRunRecord(BaseModel):
    image_edit_run_id: str
    staging_request_id: str
    provider: str
    model_name: str
    model_version: str
    prompt_version: str
    request_manifest_sha256: str
    status: ImageEditRunStatus
    latency_ms: int | None = None
    created_at: datetime


class VirtualStagingOutputRecord(BaseModel):
    virtual_staging_output_id: str
    staging_request_id: str
    image_edit_run_id: str
    output_type: VirtualStagingOutputType
    storage_uri: str
    output_sha256: str
    provenance_manifest_uri: str
    provenance_manifest_sha256: str
    evidence_grade: EvidenceGrade
    status: str = "generated"
    created_at: datetime

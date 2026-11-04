from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from vision_engine.domain.enums import (
    BenchmarkArm,
    EvaluationArmStatus,
    EvaluationCaseStatus,
    EvaluationExportStatus,
    EvaluationExportType,
    EvaluationRunStatus,
    EvaluationSelectionMethod,
)


class EvaluationCaseSpec(BaseModel):
    """One structured input scenario from YAML."""

    room_image_path: str
    inspiration_image_paths: list[str] = Field(default_factory=list)
    room_type: str
    style_family: str = "Contemporary Europe"
    brief: str = Field(min_length=5, max_length=2000)
    budget_band: str | None = None
    constraints: list[str] = Field(default_factory=list)
    project_type: str = "residential"


class EvaluationSpec(BaseModel):
    """Validated, canonical evaluation specification."""

    name: str
    repetitions: int = Field(default=1, ge=1, le=100)
    cases: list[EvaluationCaseSpec] = Field(min_length=1)
    full_output_dir: str = "data/evaluations"
    blind_output_dir: str = "~/Downloads/vision-engine-blind-evaluations"
    spec_sha256: str
    case_specs: list[CanonicalEvaluationCaseSpec] = Field(default_factory=list)


class CanonicalEvaluationCaseSpec(BaseModel):
    """Normalized case input with content hashes."""

    case_input_sha256: str
    room_sha256: str
    inspiration_shas: list[str] = Field(default_factory=list)
    room_image_path: str
    inspiration_image_paths: list[str] = Field(default_factory=list)
    room_type: str
    style_family: str
    brief: str
    budget_band: str | None = None
    constraints: list[str] = Field(default_factory=list)
    project_type: str = "residential"


class EvaluationRun(BaseModel):
    evaluation_run_id: str
    spec_sha256: str
    spec_json: dict[str, Any]
    requested_repetitions: int
    status: EvaluationRunStatus
    created_at: datetime
    completed_at: datetime | None = None


class EvaluationCase(BaseModel):
    evaluation_case_id: str
    evaluation_run_id: str
    case_input_sha256: str
    replicate_index: int
    public_case_id: str
    input_spec_json: dict[str, Any]
    status: EvaluationCaseStatus
    created_at: datetime


class EvaluationCaseArm(BaseModel):
    evaluation_case_arm_id: str
    evaluation_case_id: str
    arm: BenchmarkArm
    project_id: str | None = None
    generation_run_id: str | None = None
    status: EvaluationArmStatus
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class EvaluationExport(BaseModel):
    evaluation_export_id: str
    evaluation_run_id: str
    export_type: EvaluationExportType
    output_directory: str
    manifest_sha256: str
    status: EvaluationExportStatus
    created_at: datetime


class BlindExportCandidate(BaseModel):
    blind_candidate_id: str
    evaluation_export_id: str
    evaluation_case_id: str
    public_case_id: str
    variant_id: str
    arm: BenchmarkArm
    image_sha256: str
    display_order: int


class EvaluationSelection(BaseModel):
    selection_id: str
    evaluation_export_id: str
    evaluation_case_id: str
    public_case_id: str
    evaluator_id: str
    winner_candidate_id: str | None = None
    winner_arm: BenchmarkArm | None = None
    selection_method: EvaluationSelectionMethod
    submitted_at: datetime


class EvaluationRunSummary(BaseModel):
    evaluation_run_id: str
    status: EvaluationRunStatus
    total_cases: int
    complete_cases: int
    partial_cases: int
    failed_cases: int

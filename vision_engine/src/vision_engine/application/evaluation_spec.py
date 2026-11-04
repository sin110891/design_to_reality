from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from vision_engine.domain.errors import ConfigurationError
from vision_engine.domain.evaluation_models import (
    CanonicalEvaluationCaseSpec,
    EvaluationCaseSpec,
    EvaluationSpec,
)
from vision_engine.infrastructure.content_hash import sha256_file, sha256_json
from vision_engine.infrastructure.evaluation_bundle import copy_verified_image
from vision_engine.settings import AppSettings


class EvaluationYamlRoot(BaseModel):
    evaluation: dict[str, Any] = Field(default_factory=dict)
    cases: list[dict[str, Any]] = Field(default_factory=list)
    exports: dict[str, Any] = Field(default_factory=dict)


def _normalize_brief(brief: str) -> str:
    return " ".join(brief.strip().split()).lower()


def _normalize_constraints(constraints: list[str]) -> list[str]:
    return sorted(c.strip() for c in constraints if c.strip())


def canonical_case_input_payload(
    *,
    room_sha256: str,
    inspiration_shas: list[str],
    room_type: str,
    style_family: str,
    brief: str,
    budget_band: str | None,
    constraints: list[str],
    project_type: str,
) -> dict[str, Any]:
    return {
        "room_sha256": room_sha256,
        "inspiration_shas": sorted(inspiration_shas),
        "room_type": room_type.strip().lower(),
        "style_family": style_family.strip(),
        "brief": _normalize_brief(brief),
        "budget_band": budget_band.strip().lower() if budget_band else None,
        "constraints": _normalize_constraints(constraints),
        "project_type": project_type.strip().lower(),
    }


def _stage_evaluation_image(
    *,
    settings: AppSettings,
    source: Path,
    sha256: str,
) -> Path:
    """Copy external inputs into stable project storage without source xattrs."""
    suffix = source.suffix.lower() or ".img"
    stage_dir = settings.resolve(settings.paths.evaluations) / "_inputs"
    staged = stage_dir / f"{sha256}{suffix}"
    if source.resolve() == staged.resolve():
        return staged
    if staged.exists() and sha256_file(staged) == sha256:
        return staged
    copy_verified_image(source, staged, sha256)
    return staged


def build_canonical_case_spec(
    *,
    settings: AppSettings,
    case: EvaluationCaseSpec,
) -> CanonicalEvaluationCaseSpec:
    room_path = settings.resolve(case.room_image_path)
    if not room_path.exists():
        raise ConfigurationError(f"Room image not found: {room_path}")
    room_sha = sha256_file(room_path)
    room_path = _stage_evaluation_image(
        settings=settings,
        source=room_path,
        sha256=room_sha,
    )

    inspiration_paths: list[str] = []
    inspiration_shas: list[str] = []
    for raw in case.inspiration_image_paths:
        path = settings.resolve(raw)
        if not path.exists():
            raise ConfigurationError(f"Inspiration image not found: {path}")
        inspiration_sha = sha256_file(path)
        staged_path = _stage_evaluation_image(
            settings=settings,
            source=path,
            sha256=inspiration_sha,
        )
        inspiration_paths.append(str(staged_path))
        inspiration_shas.append(inspiration_sha)

    canonical = canonical_case_input_payload(
        room_sha256=room_sha,
        inspiration_shas=inspiration_shas,
        room_type=case.room_type,
        style_family=case.style_family,
        brief=case.brief,
        budget_band=case.budget_band,
        constraints=case.constraints,
        project_type=case.project_type,
    )
    return CanonicalEvaluationCaseSpec(
        case_input_sha256=sha256_json(canonical),
        room_sha256=room_sha,
        inspiration_shas=inspiration_shas,
        room_image_path=str(room_path),
        inspiration_image_paths=inspiration_paths,
        room_type=case.room_type,
        style_family=case.style_family,
        brief=case.brief.strip(),
        budget_band=case.budget_band,
        constraints=list(case.constraints),
        project_type=case.project_type,
    )


def load_evaluation_spec(
    *,
    settings: AppSettings,
    config_path: Path,
    repetitions_override: int | None = None,
) -> EvaluationSpec:
    resolved = settings.resolve(config_path)
    if not resolved.exists():
        raise ConfigurationError(f"Evaluation config not found: {resolved}")

    raw = yaml.safe_load(resolved.read_text(encoding="utf-8")) or {}
    try:
        root = EvaluationYamlRoot.model_validate(raw)
    except ValidationError as exc:
        raise ConfigurationError(f"Invalid evaluation YAML: {exc}") from exc

    eval_meta = root.evaluation or {}
    name = str(eval_meta.get("name") or resolved.stem)
    repetitions = int(repetitions_override or eval_meta.get("repetitions") or 1)
    if repetitions < 1:
        raise ConfigurationError("repetitions must be >= 1")

    if not root.cases:
        raise ConfigurationError("At least one case is required")

    case_specs: list[EvaluationCaseSpec] = []
    for idx, item in enumerate(root.cases):
        try:
            case_specs.append(EvaluationCaseSpec.model_validate(item))
        except ValidationError as exc:
            raise ConfigurationError(f"Invalid case at index {idx}: {exc}") from exc

    exports = root.exports or {}
    full_output_dir = str(exports.get("full_output_dir") or "data/evaluations")
    blind_output_dir = str(
        exports.get("blind_output_dir") or "~/Downloads/vision-engine-blind-evaluations"
    )

    canonical_cases = [
        build_canonical_case_spec(settings=settings, case=case) for case in case_specs
    ]
    spec_payload = {
        "name": name,
        "repetitions": repetitions,
        "full_output_dir": full_output_dir,
        "blind_output_dir": blind_output_dir,
        "cases": [case.model_dump(mode="json") for case in canonical_cases],
    }
    return EvaluationSpec(
        name=name,
        repetitions=repetitions,
        cases=case_specs,
        full_output_dir=full_output_dir,
        blind_output_dir=blind_output_dir,
        spec_sha256=sha256_json(spec_payload),
        case_specs=canonical_cases,
    )


def case_to_project_input(case: CanonicalEvaluationCaseSpec):
    from vision_engine.domain.models import ProjectInput

    return ProjectInput(
        room_image_path=case.room_image_path,
        inspiration_image_paths=case.inspiration_image_paths,
        room_type=case.room_type,
        style_family=case.style_family,
        brief=case.brief,
        budget_band=case.budget_band,
        constraints=list(case.constraints),
        project_type=case.project_type,
    )

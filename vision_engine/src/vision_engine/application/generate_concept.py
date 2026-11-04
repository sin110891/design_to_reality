from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template

from vision_engine.domain.enums import GenerationMode, ProjectStatus
from vision_engine.domain.errors import ProviderError, ValidationError
from vision_engine.domain.models import (
    ConceptRunRecord,
    DesignDirection,
    ProjectRecord,
    RetrievedReference,
)
from vision_engine.domain.rulebook import load_rulebook
from vision_engine.infrastructure.file_store import FileStore, new_id
from vision_engine.infrastructure.multimodal_clients import build_concept_client
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def resolve_reference_path(settings: AppSettings, image_path: str | Path) -> Path:
    path = Path(image_path)
    if path.is_absolute() and path.exists():
        return path
    resolved = settings.resolve(path)
    if resolved.exists():
        return resolved
    # Gold exports often use paths relative to dataset_factory/
    alt = settings.project_root.parent / "dataset_factory" / path
    if alt.exists():
        return alt
    return resolved


def _render_prompt(
    *,
    settings: AppSettings,
    project: ProjectRecord,
    references: list[RetrievedReference],
    mode: GenerationMode,
) -> str:
    template = Template(settings.concept_prompt_path.read_text(encoding="utf-8"))
    rulebook = load_rulebook(settings.rulebook_path)
    prompts_cfg: dict = {}
    if settings.prompts_config_path.exists():
        import yaml

        prompts_cfg = yaml.safe_load(settings.prompts_config_path.read_text(encoding="utf-8")) or {}

    ref_payload = []
    for ref in references:
        ref_payload.append(
            {
                "image_id": ref.image_id,
                "score": ref.score,
                "diversity_role": ref.diversity_role,
                "style_family": ref.record.style_family,
                "room_type": ref.record.room_type,
                "source_project_id": ref.record.source_project_id,
                "geography": ref.record.geography,
                "mood": ref.record.mood,
                "colour_palette": ref.record.colour_palette,
                "material_palette": ref.record.material_palette,
                "material_floor": ref.record.material_floor,
                "material_wall": ref.record.material_wall,
                "material_furniture": ref.record.material_furniture,
                "material_ceiling": ref.record.material_ceiling,
                "lighting_strategy": ref.record.lighting_strategy,
                "furniture_style": ref.record.furniture_style,
                "spatial_feel": ref.record.spatial_feel,
                "budget_band": ref.record.budget_band,
                "build_complexity": ref.record.build_complexity,
                "maintenance_level": ref.record.maintenance_level,
                "positive_why_it_works": ref.record.positive_why_it_works,
                "negative_common_pitfalls": ref.record.negative_common_pitfalls,
                "focal_point": ref.record.focal_point,
                "likely_trades_required": ref.record.likely_trades_required,
                "secondary_trades": ref.record.secondary_trades,
                "architect_quality_score": ref.record.architect_quality_score,
                "buildability_score": ref.record.buildability_score,
                "relevance_score": ref.record.relevance_score,
            }
        )

    return template.render(
        mode=mode.value,
        subset_name=rulebook.subset_name,
        rulebook_json=json.dumps(rulebook.to_prompt_dict(), indent=2),
        room_type=project.room_type,
        style_family=project.style_family,
        brief=project.brief,
        budget_band=project.budget_band,
        constraints=project.constraints,
        project_type=project.project_type,
        references=ref_payload,
        geometry_lock=prompts_cfg.get("geometry_lock", ""),
        negative_constraints=prompts_cfg.get("negative_constraints", []),
        response_schema=json.dumps(DesignDirection.model_json_schema(), indent=2),
    )


def generate_concept(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore,
    project: ProjectRecord,
    references: list[RetrievedReference],
    retrieval_run_id: str | None,
    mode: GenerationMode = GenerationMode.CURATED,
) -> tuple[DesignDirection, ConceptRunRecord]:
    prompt = _render_prompt(
        settings=settings, project=project, references=references, mode=mode
    )
    content_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    repo.ensure_prompt_version(settings.concept_prompt_version, content_hash)

    client = build_concept_client(
        provider=settings.model_provider,
        api_key=settings.gemini_api_key,
        model_name=settings.model_name,
        timeout_seconds=settings.inference.timeout_seconds,
        max_attempts=settings.inference.max_attempts,
        temperature=settings.inference.temperature,
    )
    repo.ensure_model_version(settings.model_provider, settings.model_name, "concept")

    room_path = settings.resolve(project.room_image_path)
    ref_paths = [
        resolve_reference_path(settings, ref.image_path)
        for ref in references[:3]
        if resolve_reference_path(settings, ref.image_path).exists()
    ]

    try:
        payload, meta = client.generate_concept(
            room_image_path=room_path,
            reference_image_paths=ref_paths,
            prompt=prompt,
            response_schema=DesignDirection.model_json_schema(),
        )
    except ProviderError as exc:
        run = ConceptRunRecord(
            run_id=new_id("concept"),
            project_id=project.project_id,
            retrieval_run_id=retrieval_run_id,
            mode=mode,
            prompt_version=settings.concept_prompt_version,
            provider=settings.model_provider,
            model_name=settings.model_name,
            design_direction=None,
            raw_response_json=None,
            status="provider_failed",
            error_message=str(exc),
            latency_ms=None,
            created_at=utcnow(),
        )
        repo.save_concept_run(run)
        project.status = ProjectStatus.FAILED
        project.updated_at = utcnow()
        repo.save_project(project)
        raise

    try:
        direction = DesignDirection.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        run = ConceptRunRecord(
            run_id=new_id("concept"),
            project_id=project.project_id,
            retrieval_run_id=retrieval_run_id,
            mode=mode,
            prompt_version=settings.concept_prompt_version,
            provider=meta.provider,
            model_name=meta.model_name,
            design_direction=None,
            raw_response_json=json.dumps(payload),
            status="validation_failed",
            error_message=str(exc),
            latency_ms=meta.latency_ms,
            created_at=utcnow(),
        )
        repo.save_concept_run(run)
        file_store.store_raw_json(
            project_id=project.project_id,
            name=run.run_id,
            payload=json.dumps(payload, indent=2),
        )
        raise ValidationError(f"Concept JSON failed validation: {exc}") from exc

    run = ConceptRunRecord(
        run_id=new_id("concept"),
        project_id=project.project_id,
        retrieval_run_id=retrieval_run_id,
        mode=mode,
        prompt_version=settings.concept_prompt_version,
        provider=meta.provider,
        model_name=meta.model_name,
        design_direction=direction,
        raw_response_json=json.dumps(payload),
        status="succeeded",
        error_message=None,
        latency_ms=meta.latency_ms,
        created_at=utcnow(),
    )
    repo.save_concept_run(run)
    file_store.store_raw_json(
        project_id=project.project_id,
        name=run.run_id,
        payload=json.dumps(payload, indent=2),
    )
    project.status = ProjectStatus.CONCEPT_READY
    project.updated_at = utcnow()
    repo.save_project(project)
    return direction, run

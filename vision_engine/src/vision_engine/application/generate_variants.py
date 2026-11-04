from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template

from vision_engine.application.generate_concept import resolve_reference_path
from vision_engine.domain.enums import GenerationMode, ProjectStatus, RightsStatus, RetentionConsentStatus, VariantKind
from vision_engine.domain.errors import ProviderError
from vision_engine.domain.models import (
    DesignDirection,
    GeneratedImageAsset,
    GeneratedVariant,
    GenerationRunRecord,
    ProjectRecord,
    RetrievedReference,
)
from vision_engine.infrastructure.file_store import FileStore, new_id, sha256_file, validate_image
from vision_engine.infrastructure.image_edit_clients import build_image_edit_client
from vision_engine.infrastructure.image_edit_clients.fake import VARIANT_KINDS
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _variant_prompts(
    *,
    settings: AppSettings,
    project: ProjectRecord,
    direction: DesignDirection,
    references: list[RetrievedReference],
    mode: GenerationMode,
) -> list[str]:
    template = Template(settings.image_edit_prompt_path.read_text(encoding="utf-8"))
    import yaml

    prompts_cfg = {}
    if settings.prompts_config_path.exists():
        prompts_cfg = yaml.safe_load(settings.prompts_config_path.read_text(encoding="utf-8")) or {}

    kinds = [
        ("A", VariantKind.CLOSEST, "Stay closest to the curated references and material cues."),
        ("B", VariantKind.CONSERVATIVE, "Prefer lower intervention; subtler finish and furniture changes."),
        ("C", VariantKind.EXPRESSIVE, "Stronger design expression while still obeying geometry locks."),
    ]
    rendered: list[str] = []
    for label, kind, guidance in kinds:
        rendered.append(
            template.render(
                variant_label=label,
                variant_kind=kind.value,
                variant_guidance=guidance,
                mode=mode.value,
                brief=project.brief,
                room_type=project.room_type,
                style_family=project.style_family,
                budget_band=project.budget_band,
                constraints=project.constraints,
                design_direction=direction.model_dump(),
                references=[
                    {
                        "image_id": r.image_id,
                        "materials": r.record.material_palette,
                        "mood": r.record.mood,
                        "colours": r.record.colour_palette,
                        "surface_materials": {
                            "floor": r.record.material_floor,
                            "wall": r.record.material_wall,
                            "furniture": r.record.material_furniture,
                            "ceiling": r.record.material_ceiling,
                        },
                        "lighting": r.record.lighting_strategy,
                        "spatial_feel": r.record.spatial_feel,
                        "why": r.record.positive_why_it_works,
                    }
                    for r in references[:3]
                ],
                geometry_lock=prompts_cfg.get("geometry_lock", ""),
                negative_constraints=prompts_cfg.get("negative_constraints", []),
            )
        )
    return rendered


def generate_variants(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore,
    project: ProjectRecord,
    direction: DesignDirection,
    references: list[RetrievedReference],
    concept_run_id: str | None,
    mode: GenerationMode = GenerationMode.CURATED,
    output_count: int | None = None,
) -> tuple[list[GeneratedVariant], GenerationRunRecord]:
    count = output_count or settings.generation.variant_count
    prompts = _variant_prompts(
        settings=settings,
        project=project,
        direction=direction,
        references=references,
        mode=mode,
    )
    content_hash = hashlib.sha256("\n".join(prompts).encode("utf-8")).hexdigest()
    repo.ensure_prompt_version(settings.image_edit_prompt_version, content_hash)

    client = build_image_edit_client(
        provider=settings.model_provider,
        api_key=settings.gemini_api_key,
        model_name=settings.image_edit_model,
        file_store=file_store,
        timeout_seconds=settings.inference.timeout_seconds,
        max_attempts=settings.inference.max_attempts,
        temperature=settings.inference.image_edit_temperature,
    )
    repo.ensure_model_version(settings.model_provider, settings.image_edit_model, "image_edit")

    room_path = settings.resolve(project.room_image_path)
    ref_paths = [
        str(resolve_reference_path(settings, r.image_path))
        for r in references[:3]
        if resolve_reference_path(settings, r.image_path).exists()
    ]

    run_id = new_id("gen")
    try:
        # Fake client accepts project_id kwarg; gemini client does too.
        paths, meta = client.edit_room(
            room_image_path=str(room_path),
            reference_image_paths=ref_paths if mode == GenerationMode.CURATED else [],
            design_direction=direction,
            output_count=count,
            prompts=prompts[:count],
            project_id=project.project_id,  # type: ignore[call-arg]
        )
    except TypeError:
        # Protocol-compatible clients without project_id
        paths, meta = client.edit_room(
            room_image_path=str(room_path),
            reference_image_paths=ref_paths if mode == GenerationMode.CURATED else [],
            design_direction=direction,
            output_count=count,
            prompts=prompts[:count],
        )
    except ProviderError as exc:
        run = GenerationRunRecord(
            run_id=run_id,
            project_id=project.project_id,
            concept_run_id=concept_run_id,
            mode=mode,
            prompt_version=settings.image_edit_prompt_version,
            provider=settings.model_provider,
            model_name=settings.image_edit_model,
            reference_ids=[r.image_id for r in references],
            status="provider_failed",
            error_message=str(exc),
            latency_ms=None,
            created_at=utcnow(),
        )
        repo.save_generation_run(run)
        project.status = ProjectStatus.FAILED
        project.updated_at = utcnow()
        repo.save_project(project)
        raise

    if not paths:
        run = GenerationRunRecord(
            run_id=run_id,
            project_id=project.project_id,
            concept_run_id=concept_run_id,
            mode=mode,
            prompt_version=settings.image_edit_prompt_version,
            provider=meta.provider,
            model_name=meta.model_name,
            reference_ids=[r.image_id for r in references],
            status="failed",
            error_message="Image model returned no variants",
            latency_ms=meta.latency_ms,
            created_at=utcnow(),
        )
        repo.save_generation_run(run)
        raise ProviderError("Generated image missing", transient=False)

    run = GenerationRunRecord(
        run_id=run_id,
        project_id=project.project_id,
        concept_run_id=concept_run_id,
        mode=mode,
        prompt_version=settings.image_edit_prompt_version,
        provider=meta.provider,
        model_name=meta.model_name,
        reference_ids=[r.image_id for r in references],
        status="succeeded",
        error_message=None,
        latency_ms=meta.latency_ms,
        created_at=utcnow(),
    )
    repo.save_generation_run(run)

    variants: list[GeneratedVariant] = []
    for i, path in enumerate(paths[:count]):
        kind = VARIANT_KINDS[i] if i < len(VARIANT_KINDS) else VariantKind.CLOSEST
        rel_path = file_store.relative(Path(path))
        abs_path = settings.resolve(rel_path)
        digest = sha256_file(abs_path)
        mime, width, height = validate_image(abs_path)
        asset_id = new_id("asset")
        variant_id = new_id("var")
        asset = GeneratedImageAsset(
            asset_id=asset_id,
            variant_id=variant_id,
            storage_path=rel_path,
            image_sha256=digest,
            mime_type=mime or "image/png",
            width=width,
            height=height,
            file_size_bytes=abs_path.stat().st_size,
            rights_status=RightsStatus.USER_OWNED,
            retention_consent_status=RetentionConsentStatus.PENDING,
            created_at=utcnow(),
        )
        variant = GeneratedVariant(
            variant_id=variant_id,
            generation_run_id=run_id,
            project_id=project.project_id,
            mode=mode,
            kind=kind,
            image_path=rel_path,
            rank_hint=i + 1,
            image_asset_id=asset_id,
            created_at=utcnow(),
        )
        repo.save_variant(variant)
        repo.save_image_asset(asset)
        variants.append(variant)

    project.status = ProjectStatus.GENERATED
    project.updated_at = utcnow()
    repo.save_project(project)
    return variants, run

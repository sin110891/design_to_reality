from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from vision_engine.concept_board.domain.enums import (
    ConceptAssetType,
    ConceptBoardStatus,
    ConceptDirectionStatus,
    ConceptVersionStatus,
)
from vision_engine.concept_board.domain.errors import BootstrapError
from vision_engine.concept_board.domain.models import (
    ConceptAssetRecord,
    ConceptBoardRecord,
    ConceptDirectionRecord,
    ConceptVersionProvenanceRecord,
    ConceptVersionRecord,
)
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.domain.models import GeneratedVariant
from vision_engine.infrastructure.file_store import new_id, sha256_file
from vision_engine.infrastructure.sqlite_repository import utcnow
from vision_engine.settings import AppSettings


def _resolve_variant_image(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings,
    variant: GeneratedVariant,
) -> tuple[Path, str, int | None, int | None, str]:
    image_asset = repo.get_image_asset(variant.variant_id)
    if image_asset is not None:
        source_path = Path(image_asset.storage_path)
        if not source_path.is_absolute():
            source_path = settings.resolve(source_path)
        if source_path.exists():
            return (
                source_path,
                image_asset.mime_type,
                image_asset.width,
                image_asset.height,
                image_asset.rights_status.value,
            )

    source_path = Path(variant.image_path)
    if not source_path.is_absolute():
        source_path = settings.resolve(source_path)
    if not source_path.exists():
        raise BootstrapError(
            f"No image found for variant {variant.variant_id}. "
            f"Expected file at {source_path}"
        )

    width: int | None = None
    height: int | None = None
    mime_type = "image/png"
    try:
        from PIL import Image

        with Image.open(source_path) as img:
            width, height = img.size
            if img.format:
                mime_type = Image.MIME.get(img.format, mime_type)
    except OSError:
        pass

    return source_path, mime_type, width, height, "user_owned"


def bootstrap_concept_board_from_variant(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings,
    project_id: str,
    variant_id: str,
    board_name: str | None = None,
    direction_name: str | None = None,
) -> tuple[ConceptBoardRecord, ConceptDirectionRecord, ConceptVersionRecord]:
    project = repo.get_project(project_id)
    if project is None:
        raise BootstrapError(f"Project not found: {project_id}")

    variant = repo.get_variant_by_id(variant_id)
    if variant is None or variant.project_id != project_id:
        raise BootstrapError(f"Variant not found for project: {variant_id}")

    existing = repo.get_concept_board_for_project(project_id)
    if existing is not None:
        direction = repo.list_directions_for_board(existing.concept_board_id)[0]
        version = repo.get_latest_concept_version(direction.concept_direction_id)
        if version is None:
            raise BootstrapError("Concept board exists but has no versions")
        return existing, direction, version

    source_path, mime_type, width, height, rights_status = _resolve_variant_image(
        repo=repo,
        settings=settings,
        variant=variant,
    )

    generation_run = repo.get_generation_run(variant.generation_run_id)
    concept_run = (
        repo.get_concept_run(generation_run.concept_run_id)
        if generation_run and generation_run.concept_run_id
        else None
    )
    design_direction: dict = {}
    if concept_run and concept_run.design_direction:
        design_direction = concept_run.design_direction.model_dump()

    now = utcnow()
    board_id = new_id("cb")
    direction_id = new_id("cd")
    version_id = new_id("cv")

    concept_root = settings.resolve(settings.paths.concept_boards) / project_id / board_id
    versions_dir = concept_root / "versions" / version_id
    versions_dir.mkdir(parents=True, exist_ok=True)

    dest_path = versions_dir / "primary.png"
    shutil.copy2(source_path, dest_path)
    content_sha256 = sha256_file(dest_path)

    board = ConceptBoardRecord(
        concept_board_id=board_id,
        project_id=project_id,
        board_name=board_name or f"Concept board — {project.room_type}",
        status=ConceptBoardStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    direction = ConceptDirectionRecord(
        concept_direction_id=direction_id,
        concept_board_id=board_id,
        direction_name=direction_name or project.style_family,
        design_intent_json=design_direction,
        status=ConceptDirectionStatus.ACTIVE,
        created_at=now,
    )
    version = ConceptVersionRecord(
        concept_version_id=version_id,
        concept_direction_id=direction_id,
        version_number=1,
        version_reason="Bootstrapped from Vision Engine variant",
        generation_provider=generation_run.provider if generation_run else None,
        generation_model=generation_run.model_name if generation_run else None,
        prompt_version=generation_run.prompt_version if generation_run else None,
        status=ConceptVersionStatus.GENERATED,
        content_sha256=content_sha256,
        created_at=now,
    )
    asset = ConceptAssetRecord(
        concept_asset_id=new_id("ca"),
        concept_version_id=version_id,
        asset_type=ConceptAssetType.PRIMARY_RENDER,
        storage_uri=str(dest_path.relative_to(settings.project_root)),
        mime_type=mime_type,
        asset_sha256=content_sha256,
        width=width,
        height=height,
        rights_status=rights_status,
        created_at=now,
    )
    provenance = ConceptVersionProvenanceRecord(
        provenance_id=new_id("cvp"),
        concept_version_id=version_id,
        source_vision_project_id=project_id,
        generation_run_id=variant.generation_run_id,
        concept_run_id=generation_run.concept_run_id if generation_run else None,
        retrieval_run_id=concept_run.retrieval_run_id if concept_run else None,
        source_variant_id=variant_id,
        design_direction_json=design_direction,
        reference_ids_json=generation_run.reference_ids if generation_run else [],
        created_at=now,
    )

    repo.save_concept_board(board)
    repo.save_concept_direction(direction)
    repo.save_concept_version(version)
    repo.save_concept_asset(asset)
    repo.save_concept_version_provenance(provenance)
    return board, direction, version

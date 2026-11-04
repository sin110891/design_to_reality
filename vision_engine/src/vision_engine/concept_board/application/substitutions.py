from __future__ import annotations

from vision_engine.concept_board.domain.models import SubstitutionPreviewRecord
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings
from vision_engine.virtual_staging.application.cumulative_staging import (
    resolve_cumulative_preview_mode,
    run_cumulative_product_staging,
)
from vision_engine.virtual_staging.application.staging_2d import (
    ProductStagingResult,
    run_2d_product_staging,
)


def generate_substitution_preview(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    file_store: FileStore | None = None,
    region_candidate_id: str,
    concept_version_id: str,
    provider: str | None = None,
    model_name: str | None = None,
    prompt_version: str | None = None,
    product_image_uri: str | None = None,
    cumulative_enabled: bool = False,
    cumulative_mode: str | None = None,
) -> SubstitutionPreviewRecord:
    store = file_store or FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )
    resolved_mode = resolve_cumulative_preview_mode(
        settings=settings,
        cumulative_enabled=cumulative_enabled,
        ui_mode=cumulative_mode,
    )
    result: ProductStagingResult
    if resolved_mode == "single":
        result = run_2d_product_staging(
            repo=repo,
            settings=settings,
            file_store=store,
            region_candidate_id=region_candidate_id,
            concept_version_id=concept_version_id,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
            product_image_uri=product_image_uri,
            cumulative_mode="single",
        )
    else:
        result = run_cumulative_product_staging(
            repo=repo,
            settings=settings,
            file_store=store,
            region_candidate_id=region_candidate_id,
            concept_version_id=concept_version_id,
            cumulative_mode=resolved_mode,
            current_product_image_uri=product_image_uri,
            provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )
    return result.substitution_preview

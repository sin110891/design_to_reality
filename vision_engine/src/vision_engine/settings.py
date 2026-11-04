from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from vision_engine.domain.errors import ConfigurationError


ROOT = Path(__file__).resolve().parents[2]


class InferenceConfig(BaseSettings):
    timeout_seconds: int = 120
    max_attempts: int = 3
    temperature: float = 0.2
    image_edit_temperature: float = 0.4


class ImagesConfig(BaseSettings):
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp"]
    )
    max_file_mb: int = 25


class RetrievalConfig(BaseSettings):
    image_similarity_weight: float = 0.35
    text_similarity_weight: float = 0.25
    metadata_match_weight: float = 0.25
    architect_quality_weight: float = 0.15
    top_k: int = 8
    final_k: int = 3
    min_diversity: int = 3


class ReviewConfig(BaseSettings):
    curator_name: str = "Lloyd Lee"


class GenerationConfig(BaseSettings):
    variant_count: int = 3
    concept_disclaimer: str = (
        "Concept visual only — not a technical design, BoQ, or compliance guarantee."
    )


class VirtualStagingConfig(BaseSettings):
    visual_preview_disclaimer: str = (
        "Visual preview only — not construction-accurate, not for ordering or installation."
    )
    cumulative_preview_enabled_default: bool = False
    cumulative_preview_mode: str = "local_composite"


class PathsConfig(BaseSettings):
    curated_metadata: Path = Path("data/curated/metadata.csv")
    curated_images: Path = Path("data/curated/images")
    index_path: Path = Path("data/indexes/curated.npz")
    uploads: Path = Path("data/uploads")
    generated: Path = Path("data/generated")
    exports: Path = Path("data/exports")
    evaluations: Path = Path("data/evaluations")
    concept_boards: Path = Path("data/concept_boards")
    catalogue: Path = Path("data/catalogue")
    staging: Path = Path("data/staging")
    blind_evaluations: Path = Path("~/Downloads/vision-engine-blind-evaluations")


class RegionDetectionConfig(BaseSettings):
    provider: str = "fake"
    model_name: str = "gemini-2.0-flash"
    fake_model_name: str = "fake-region-detector-v1"
    temperature: float = 0.1
    min_confidence: float = 0.35


class Channel3Config(BaseSettings):
    country: str = "GB"
    currency: str = "GBP"
    language: str = "en"
    timeout_seconds: int = 30


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str | None = None
    channel3_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CHANNEL3_API_KEY", "CHANNEL3_CATALOG_APU_KEY"),
    )
    catalogue_provider: str = "local"
    region_detection_provider: str = "fake"
    model_provider: str = "fake"
    model_name: str = "gemini-2.0-flash"
    image_edit_model: str = "gemini-2.0-flash-preview-image-generation"
    embedding_provider: str = "fake"
    embedding_model_name: str = "clip-ViT-B-32"
    app_env: str = "local"
    log_level: str = "INFO"
    database_path: Path = Path("data/database/vision_engine.db")
    rulebook_path: Path = Path("configs/rulebook.v1.yaml")
    app_config_path: Path = Path("configs/app.local.yaml")
    prompts_config_path: Path = Path("configs/prompts.v1.yaml")
    concept_prompt_version: str = "concept_direction"
    image_edit_prompt_version: str = "image_edit"
    product_staging_prompt_version: str = "product_staging"
    project_root: Path = ROOT

    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    virtual_staging: VirtualStagingConfig = Field(default_factory=VirtualStagingConfig)
    region_detection: RegionDetectionConfig = Field(default_factory=RegionDetectionConfig)
    channel3: Channel3Config = Field(default_factory=Channel3Config)
    paths: PathsConfig = Field(default_factory=PathsConfig)

    def resolve(self, path: Path | str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return (self.project_root / candidate).resolve()

    @property
    def concept_prompt_path(self) -> Path:
        return self.resolve(
            Path("src/vision_engine/prompts") / f"{self.concept_prompt_version}.jinja2"
        )

    @property
    def image_edit_prompt_path(self) -> Path:
        return self.resolve(
            Path("src/vision_engine/prompts") / f"{self.image_edit_prompt_version}.jinja2"
        )

    @property
    def product_staging_prompt_path(self) -> Path:
        return self.resolve(
            Path("src/vision_engine/prompts") / f"{self.product_staging_prompt_version}.jinja2"
        )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigurationError(f"Config root must be a mapping: {path}")
    return data


@lru_cache
def get_settings() -> AppSettings:
    base = AppSettings()
    yaml_path = base.resolve(base.app_config_path)
    raw = _load_yaml(yaml_path)

    inference = InferenceConfig(**(raw.get("inference") or {}))
    images = ImagesConfig(**(raw.get("images") or {}))
    retrieval = RetrievalConfig(**(raw.get("retrieval") or {}))
    review = ReviewConfig(**(raw.get("review") or {}))
    generation = GenerationConfig(**(raw.get("generation") or {}))
    virtual_staging = VirtualStagingConfig(**(raw.get("virtual_staging") or {}))
    region_detection = RegionDetectionConfig(
        **{
            **(raw.get("region_detection") or {}),
            "provider": base.region_detection_provider,
        }
    )
    channel3 = Channel3Config(**(raw.get("channel3") or {}))
    paths_raw = raw.get("paths") or {}
    paths = PathsConfig(**paths_raw)

    return AppSettings(
        gemini_api_key=base.gemini_api_key,
        channel3_api_key=base.channel3_api_key,
        catalogue_provider=base.catalogue_provider,
        region_detection_provider=base.region_detection_provider,
        model_provider=base.model_provider,
        model_name=base.model_name,
        image_edit_model=base.image_edit_model,
        embedding_provider=base.embedding_provider,
        embedding_model_name=base.embedding_model_name,
        app_env=base.app_env,
        log_level=base.log_level,
        database_path=base.resolve(base.database_path),
        rulebook_path=base.resolve(base.rulebook_path),
        app_config_path=yaml_path,
        prompts_config_path=base.resolve(base.prompts_config_path),
        concept_prompt_version=base.concept_prompt_version,
        image_edit_prompt_version=base.image_edit_prompt_version,
        product_staging_prompt_version=base.product_staging_prompt_version,
        project_root=base.project_root,
        inference=inference,
        images=images,
        retrieval=retrieval,
        review=review,
        generation=generation,
        virtual_staging=virtual_staging,
        region_detection=region_detection,
        channel3=channel3,
        paths=PathsConfig(
            curated_metadata=base.resolve(paths.curated_metadata),
            curated_images=base.resolve(paths.curated_images),
            index_path=base.resolve(paths.index_path),
            uploads=base.resolve(paths.uploads),
            generated=base.resolve(paths.generated),
            exports=base.resolve(paths.exports),
            evaluations=base.resolve(paths.evaluations),
            concept_boards=base.resolve(paths.concept_boards),
            catalogue=base.resolve(paths.catalogue),
            staging=base.resolve(paths.staging),
            blind_evaluations=Path(paths.blind_evaluations).expanduser().resolve(),
        ),
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()

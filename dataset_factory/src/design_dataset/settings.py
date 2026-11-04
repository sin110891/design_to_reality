from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from design_dataset.domain.errors import ConfigurationError


ROOT = Path(__file__).resolve().parents[2]


class InferenceConfig(BaseSettings):
    timeout_seconds: int = 90
    max_attempts: int = 3
    concurrency: int = 2
    temperature: float = 0.1


class ImagesConfig(BaseSettings):
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp"]
    )
    max_file_mb: int = 20


class ReviewConfig(BaseSettings):
    curator_name: str = "Lloyd Lee"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str | None = None
    model_provider: str = "fake"
    model_name: str = "gemini-2.0-flash"
    app_env: str = "local"
    log_level: str = "INFO"
    database_path: Path = Path("data/app.db")
    rulebook_path: Path = Path("configs/rulebook.v1.yaml")
    app_config_path: Path = Path("configs/app.local.yaml")
    prompt_version: str = "label_image_v1"
    project_root: Path = ROOT

    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)

    def resolve(self, path: Path | str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        return (self.project_root / candidate).resolve()

    @property
    def prompt_template_path(self) -> Path:
        return self.resolve(
            Path("src/design_dataset/prompts") / f"{self.prompt_version}.jinja2"
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
    review = ReviewConfig(**(raw.get("review") or {}))
    return AppSettings(
        gemini_api_key=base.gemini_api_key,
        model_provider=base.model_provider,
        model_name=base.model_name,
        app_env=base.app_env,
        log_level=base.log_level,
        database_path=base.resolve(base.database_path),
        rulebook_path=base.resolve(base.rulebook_path),
        app_config_path=yaml_path,
        prompt_version=base.prompt_version,
        project_root=base.project_root,
        inference=inference,
        images=images,
        review=review,
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()

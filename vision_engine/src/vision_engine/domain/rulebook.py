from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from vision_engine.domain.errors import ConfigurationError


class RulebookField(BaseModel):
    type: str
    allowed_values: list[str] = Field(default_factory=list)
    min_items: int | None = None
    max_items: int | None = None
    optional: bool = False
    guidance: str | None = None
    definitions: dict[str, str] = Field(default_factory=dict)


class Rulebook(BaseModel):
    version: str
    subset_name: str
    fields: dict[str, RulebookField]

    def allowed(self, field_name: str) -> list[str]:
        field = self.fields.get(field_name)
        return list(field.allowed_values) if field else []

    def to_prompt_dict(self) -> dict[str, Any]:
        return self.model_dump()


def load_rulebook(path: Path) -> Rulebook:
    if not path.exists():
        raise ConfigurationError(f"Rulebook not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ConfigurationError(f"Rulebook root must be a mapping: {path}")
    return Rulebook.model_validate(raw)

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from design_dataset.domain.errors import RulebookError


class RulebookField(BaseModel):
    type: str
    allowed_values: list[str]
    guidance: str | None = None
    min_items: int | None = None
    max_items: int | None = None
    optional: bool = False
    definitions: dict[str, str] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        if value not in {"single", "multiple"}:
            raise ValueError("field type must be 'single' or 'multiple'")
        return value


class Rulebook(BaseModel):
    version: str
    subset_name: str
    fields: dict[str, RulebookField]

    def allowed(self, field_name: str) -> set[str]:
        if field_name not in self.fields:
            raise RulebookError(f"Unknown rulebook field: {field_name}")
        return set(self.fields[field_name].allowed_values)

    def to_prompt_dict(self) -> dict[str, Any]:
        return self.model_dump()


def load_rulebook(path: Path) -> Rulebook:
    if not path.exists():
        raise RulebookError(f"Rulebook not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RulebookError(f"Invalid YAML in rulebook: {exc}") from exc
    if not isinstance(raw, dict):
        raise RulebookError("Rulebook root must be a mapping")
    try:
        rulebook = Rulebook.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 - surface schema issues clearly
        raise RulebookError(f"Rulebook schema invalid: {exc}") from exc
    if not rulebook.version:
        raise RulebookError("Rulebook version is required")
    return rulebook

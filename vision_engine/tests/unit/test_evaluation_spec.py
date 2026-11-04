from __future__ import annotations

from pathlib import Path

import pytest

from vision_engine.application.evaluation_spec import (
    build_canonical_case_spec,
    canonical_case_input_payload,
    load_evaluation_spec,
)
from vision_engine.domain.evaluation_models import EvaluationCaseSpec
from vision_engine.domain.errors import ConfigurationError
from vision_engine.settings import AppSettings, clear_settings_cache


def _settings(tmp_path: Path) -> AppSettings:
    clear_settings_cache()
    return AppSettings(
        model_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        project_root=tmp_path,
    )


def test_canonical_case_hash_is_stable(tmp_path: Path):
    payload_a = canonical_case_input_payload(
        room_sha256="abc123",
        inspiration_shas=["def456"],
        room_type="Mixed",
        style_family="Contemporary Europe",
        brief="  Dark Contemporary   European ",
        budget_band="High",
        constraints=["keep fireplace", "keep windows"],
        project_type="residential",
    )
    payload_b = canonical_case_input_payload(
        room_sha256="abc123",
        inspiration_shas=["def456"],
        room_type="mixed",
        style_family="Contemporary Europe",
        brief="dark contemporary european",
        budget_band="high",
        constraints=["keep windows", "keep fireplace"],
        project_type="residential",
    )
    assert payload_a == payload_b


def test_load_evaluation_spec_requires_existing_room(tmp_path: Path):
    settings = _settings(tmp_path)
    config = tmp_path / "eval.yaml"
    config.write_text(
        """
evaluation:
  name: test
  repetitions: 1
cases:
  - room_image_path: missing.jpg
    brief: warm contemporary European living room
    room_type: living_room
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="Room image not found"):
        load_evaluation_spec(settings=settings, config_path=config)


def test_build_canonical_case_spec_hashes_room(tmp_path: Path):
    settings = _settings(tmp_path)
    room = tmp_path / "room.jpg"
    room.write_bytes(b"fake-room-image")
    case = EvaluationCaseSpec(
        room_image_path=str(room),
        brief="warm contemporary European living room",
        room_type="living_room",
    )
    canonical = build_canonical_case_spec(settings=settings, case=case)
    assert canonical.room_sha256
    assert canonical.case_input_sha256
    staged = Path(canonical.room_image_path)
    assert staged.parent == settings.resolve(settings.paths.evaluations) / "_inputs"
    assert staged.read_bytes() == room.read_bytes()

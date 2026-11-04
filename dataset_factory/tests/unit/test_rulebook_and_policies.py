from pathlib import Path

import pytest

from design_dataset.domain.models import DesignLabelDraft
from design_dataset.domain.policies import normalize_label, validate_against_rulebook
from design_dataset.domain.rulebook import load_rulebook
from design_dataset.infrastructure.hashing import request_fingerprint

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def rulebook():
    return load_rulebook(ROOT / "configs" / "rulebook.v1.yaml")


@pytest.fixture
def sample_label() -> DesignLabelDraft:
    return DesignLabelDraft.model_validate_json(
        (ROOT / "tests" / "fixtures" / "sample_label.json").read_text(encoding="utf-8")
    )


def test_rulebook_loads(rulebook):
    assert rulebook.version == "1.0.0"
    assert "Contemporary Europe" in rulebook.allowed("style_family")


def test_fingerprint_stable():
    a = request_fingerprint(
        image_sha256="abc",
        rulebook_version="1.0.0",
        prompt_version="label_image_v1",
        provider="fake",
        model_name="fake-model",
        generation_settings={"temperature": 0.1},
    )
    b = request_fingerprint(
        image_sha256="abc",
        rulebook_version="1.0.0",
        prompt_version="label_image_v1",
        provider="fake",
        model_name="fake-model",
        generation_settings={"temperature": 0.1},
    )
    assert a == b
    assert len(a) == 64


def test_normalize_and_validate(rulebook, sample_label):
    result = validate_against_rulebook(sample_label, rulebook)
    assert result.ok
    assert result.label is not None
    assert result.label.budget_band == "medium_high"


def test_primary_trade_must_be_in_likely(rulebook, sample_label):
    data = sample_label.model_dump()
    data["primary_trade"] = "plumber"
    draft = DesignLabelDraft.model_validate(data)
    result = validate_against_rulebook(draft, rulebook)
    assert not result.ok
    assert any("primary_trade" in err for err in result.errors)


def test_rejects_unknown_mood(rulebook, sample_label):
    data = sample_label.model_dump()
    data["mood"] = ["cozy"]
    draft = DesignLabelDraft.model_validate(data)
    result = validate_against_rulebook(draft, rulebook)
    assert not result.ok


def test_normalize_dedupes():
    draft = DesignLabelDraft.model_validate(
        {
            "style_family": " Contemporary Europe ",
            "mood": ["Warm", "warm", "calm"],
            "material_palette": ["Oak", "oak", "plaster"],
            "budget_band": "Medium",
            "primary_trade": "Joiner",
            "likely_trades_required": ["Joiner", "decorator"],
            "positive": {"why_it_works": "Clear hierarchy from limited materials."},
            "negative": {"why_it_fails": "Some junctions look unresolved and generic."},
            "confidence_notes": "ok",
        }
    )
    normalized = normalize_label(draft)
    assert normalized.mood == ["warm", "calm"]
    assert normalized.material_palette == ["oak", "plaster"]

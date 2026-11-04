from __future__ import annotations

from pathlib import Path

from vision_engine.domain.models import DesignDirection, ProjectInput
from vision_engine.domain.rulebook import load_rulebook
from vision_engine.domain.services import (
    diversify_references,
    hybrid_score,
    metadata_match_score,
)
from vision_engine.domain.enums import ReviewStatus
from vision_engine.domain.models import DatasetRecord, RetrievedReference


ROOT = Path(__file__).resolve().parents[2]


def test_rulebook_loads():
    rb = load_rulebook(ROOT / "configs" / "rulebook.v1.yaml")
    assert rb.version == "1.0.0"
    assert "Contemporary Europe" in rb.allowed("style_family")
    assert "oak" in rb.allowed("material_palette")


def test_design_direction_validation():
    direction = DesignDirection(
        concept_title="Warm Contemporary European",
        design_intent="Create a calm, tactile living room with restrained materials.",
        mood=["warm", "calm"],
        material_palette=["oak", "limewash"],
        lighting_strategy=["retain natural light"],
        furniture_direction=["low-profile sofa"],
        focal_point="Seating axis to the window",
        spatial_hierarchy="One dominant calm plane",
        preserve=["windows", "fireplace"],
        allowed_changes=["wall finish", "furniture"],
        likely_trades=["decorator"],
        positive_rules=["restrained palette"],
        negative_warnings=["avoid oversized furniture"],
    )
    assert direction.concept_title.startswith("Warm")


def test_hybrid_score_and_metadata():
    query = ProjectInput(
        room_image_path="x.jpg",
        room_type="living_room",
        style_family="Contemporary Europe",
        brief="warm oak calm lighting",
        budget_band="medium_high",
    )
    record = DatasetRecord(
        image_id="img_1",
        image_path="a.jpg",
        style_family="Contemporary Europe",
        room_type="living_room",
        mood=["warm", "calm"],
        material_palette=["oak", "linen"],
        lighting_strategy="layered ambient light",
        budget_band="medium_high",
        architect_quality_score=4.5,
        review_status=ReviewStatus.APPROVED,
    )
    meta = metadata_match_score(query, record)
    assert meta > 0.7
    score = hybrid_score(
        image_similarity=0.8,
        text_similarity=0.7,
        metadata_match=meta,
        architect_quality=4.5,
        image_weight=0.35,
        text_weight=0.25,
        metadata_weight=0.25,
        quality_weight=0.15,
    )
    assert 0.5 < score <= 1.0


def test_diversify_references():
    def make_ref(i: int, materials: list[str], focal: str, score: float) -> RetrievedReference:
        record = DatasetRecord(
            image_id=f"img_{i}",
            image_path=f"{i}.jpg",
            style_family="Contemporary Europe",
            material_palette=materials,
            focal_point=focal,
            review_status=ReviewStatus.APPROVED,
            architect_quality_score=4.0,
        )
        return RetrievedReference(
            image_id=record.image_id,
            image_path=record.image_path,
            score=score,
            image_similarity=score,
            text_similarity=0.5,
            metadata_match=0.5,
            architect_quality=4.0,
            match_rationale="test",
            record=record,
        )

    candidates = [
        make_ref(1, ["oak", "linen"], "sofa", 0.9),
        make_ref(2, ["oak", "brass"], "sofa", 0.85),
        make_ref(3, ["marble"], "fireplace", 0.7),
        make_ref(4, ["glass"], "window wall", 0.65),
    ]
    selected = diversify_references(candidates, final_k=3)
    assert len(selected) == 3
    roles = {r.diversity_role for r in selected}
    assert "direct_match" in roles

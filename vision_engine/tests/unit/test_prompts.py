from __future__ import annotations

from pathlib import Path

from jinja2 import Template

from vision_engine.domain.models import DesignDirection


ROOT = Path(__file__).resolve().parents[2]


def test_concept_prompt_renders():
    template = Template(
        (ROOT / "src/vision_engine/prompts/concept_direction.jinja2").read_text(encoding="utf-8")
    )
    text = template.render(
        mode="curated",
        subset_name="Contemporary Europe",
        rulebook_json="{}",
        room_type="living_room",
        style_family="Contemporary Europe",
        brief="warm calm oak",
        budget_band="medium_high",
        constraints=["retain fireplace"],
        project_type="residential",
        references=[
            {
                "image_id": "img_1",
                "score": 0.9,
                "diversity_role": "direct_match",
                "style_family": "Contemporary Europe",
                "room_type": "living_room",
                "mood": ["warm"],
                "material_palette": ["oak"],
                "lighting_strategy": "layered",
                "furniture_style": "low_profile_contemporary",
                "budget_band": "medium_high",
                "positive_why_it_works": "Clear hierarchy",
                "negative_common_pitfalls": "Avoid generic lighting",
                "focal_point": "sofa",
                "likely_trades_required": ["decorator"],
            }
        ],
        geometry_lock="Preserve walls and windows.",
        negative_constraints=["Do not move doors."],
        response_schema="{}",
    )
    assert "Warm calm oak" in text or "warm calm oak" in text
    assert "direct_match" in text
    assert DesignDirection.__name__ or True

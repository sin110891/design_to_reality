from __future__ import annotations

import json
from pathlib import Path

from vision_engine.infrastructure.gold_adapter import gold_row_to_dataset_record, load_gold_jsonl
from vision_engine.domain.enums import ReviewStatus


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT.parent / "dataset_factory"
GOLD = FACTORY / "data" / "exports" / "gemini_demo_gold.jsonl"


def test_gold_adapter_maps_final_label():
    row = {
        "record_id": "rec_1",
        "image_id": "img_1",
        "file_path": "data/raw_images/contemporary_europe/01.jpg",
        "status": "approved",
        "usage_rights_status": "unknown",
        "expert_metadata": {
            "project_id": "P-001",
            "room_id": "R-001",
            "source_name": "Lloyd Studio",
            "source_url_or_path": "/refs/01.jpg",
            "project_type": "Domestic",
            "typology": "House-Living Room",
            "image_type": "Reference",
            "geography": "London, UK",
            "style_family": ["European Contemporary", "Traditional"],
            "mood": ["Warm", "Refined"],
            "colour_palette": ["Cream", "Brown"],
            "material_floor": ["Oak"],
            "material_wall": ["Limewash"],
            "material_furniture": ["Linen"],
            "material_ceiling": ["Plaster"],
            "material_palette": ["Floor: Oak", "Wall: Limewash"],
            "lighting_type": ["Natural Light", "Pendant"],
            "furniture_style": ["Italian Contemporary"],
            "spatial_feel": ["Airy"],
            "architect_quality_score": 5,
            "buildability_score": 4,
            "source_workbook": "v3.xlsx",
            "source_sheet": "Collection Example",
            "source_row": 20,
        },
        "final_label": {
            "style_family": "Contemporary Europe",
            "mood": ["calm", "warm"],
            "material_palette": ["oak", "linen"],
            "budget_band": "high",
            "primary_trade": "decorator",
            "likely_trades_required": ["decorator", "electrician"],
            "room_type": "living_room",
            "positive": {
                "why_it_works": "Restrained palette with clear hierarchy and calm daylight.",
                "lighting_strategy": "Layered ambient with soft highlights",
                "focal_point": "Seating axis",
                "design_move": "Low-profile contemporary furniture",
            },
            "negative": {
                "why_it_fails": "Risk of catalogue-generic detailing if junctions are unresolved.",
                "scale_problem": None,
            },
        },
    }
    record = gold_row_to_dataset_record(row)
    assert record is not None
    assert record.review_status == ReviewStatus.APPROVED
    assert record.room_type == "living_room"
    assert "oak" in record.material_palette
    assert record.lighting_strategy is not None
    assert record.positive_why_it_works
    assert record.negative_common_pitfalls
    assert record.furniture_style
    assert record.source_project_id == "P-001"
    assert record.project_type == "residential"
    assert record.geography == "London, UK"
    assert "Cream" in record.colour_palette
    assert "Oak" in record.material_floor
    assert "Floor: Oak" in record.material_palette
    assert record.architect_quality_score == 5
    assert record.buildability_score == 4
    assert "London, UK" in record.text_blob


def test_load_real_gold_if_present():
    if not GOLD.exists():
        return
    records = load_gold_jsonl(GOLD, approved_only=True)
    assert len(records) >= 1
    assert all(r.review_status == ReviewStatus.APPROVED for r in records)
    line = json.loads(GOLD.read_text(encoding="utf-8").splitlines()[0])
    assert line["status"] == "approved"

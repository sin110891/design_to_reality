from __future__ import annotations

import hashlib
import time
from pathlib import Path

from design_dataset.domain.models import ModelCallMetadata


class FakeModelClient:
    """Deterministic local client for dry-runs and tests."""

    def __init__(self, *, model_name: str = "fake-model-v1"):
        self.model_name = model_name

    def label_image(
        self,
        *,
        image_path: Path,
        prompt: str,
        response_schema: dict,
    ) -> tuple[dict, ModelCallMetadata]:
        started = time.perf_counter()
        digest = hashlib.sha256(image_path.name.encode("utf-8")).hexdigest()
        mood_cycle = ["warm", "calm", "restrained", "tactile", "premium"]
        material_cycle = ["oak", "plaster", "brass", "linen", "glass", "limewash"]
        idx = int(digest[:8], 16)
        payload = {
            "style_family": "Contemporary Europe",
            "mood": [mood_cycle[idx % len(mood_cycle)], mood_cycle[(idx + 1) % len(mood_cycle)]],
            "material_palette": [
                material_cycle[idx % len(material_cycle)],
                material_cycle[(idx + 2) % len(material_cycle)],
                material_cycle[(idx + 4) % len(material_cycle)],
            ],
            "budget_band": ["medium", "medium_high", "high"][idx % 3],
            "primary_trade": "joiner",
            "likely_trades_required": ["joiner", "decorator", "flooring_installer"],
            "room_type": ["living_room", "kitchen", "bedroom", "mixed"][idx % 4],
            "positive": {
                "design_move": "Restrained material pairing with a clear visual hierarchy",
                "why_it_works": (
                    "Visible finishes are limited and coordinated, creating calm hierarchy "
                    "without competing focal elements."
                ),
                "focal_point": "Primary seating or joinery mass",
                "material_relationship": "Warm timber against matte mineral surfaces",
                "lighting_strategy": "Layered ambient light with soft highlights",
                "proportion_rule": "Furniture and openings appear balanced to room scale",
                "circulation_strategy": "Clear path around primary furniture mass",
                "visual_hierarchy": "One dominant plane supported by quieter secondary planes",
                "appropriate_room_conditions": ["daylit interiors", "residential scale"],
            },
            "negative": {
                "design_failure": "Possible over-reliance on generic styling cues",
                "why_it_fails": (
                    "Some detailing may read as catalogue-generic if material junctions "
                    "are not carefully resolved."
                ),
                "scale_problem": None,
                "material_conflict": None,
                "lighting_problem": None,
                "impractical_detail": None,
                "generic_ai_artifact": None,
                "structural_violation": None,
            },
            "confidence_notes": f"Draft from fake client for {image_path.name}",
            "visible_uncertainties": [
                "Exact timber species cannot be confirmed from the image alone",
                "Budget band is an estimate from visible finish quality only",
            ],
        }
        # Keep schema reference used so unused-arg linters stay quiet in strict setups.
        _ = (prompt, response_schema)
        latency_ms = int((time.perf_counter() - started) * 1000)
        meta = ModelCallMetadata(
            provider="fake",
            model_name=self.model_name,
            request_id=f"fake-{digest[:12]}",
            latency_ms=max(latency_ms, 1),
            input_tokens=120,
            output_tokens=220,
            total_tokens=340,
            attempt=1,
        )
        return payload, meta

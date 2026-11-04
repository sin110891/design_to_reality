from __future__ import annotations

import hashlib
import time
from pathlib import Path

from vision_engine.domain.models import ModelCallMetadata


class FakeMultimodalClient:
    """Deterministic concept JSON for offline tests and demos."""

    def __init__(self, *, model_name: str = "fake-concept-v1"):
        self.model_name = model_name

    def generate_concept(
        self,
        *,
        room_image_path: Path,
        reference_image_paths: list[Path],
        prompt: str,
        response_schema: dict,
    ) -> tuple[dict, ModelCallMetadata]:
        started = time.perf_counter()
        digest = hashlib.sha256(room_image_path.name.encode()).hexdigest()
        idx = int(digest[:6], 16)
        materials = ["oak", "limewash", "linen", "brass"]
        moods = ["warm", "calm", "restrained"]
        payload = {
            "concept_title": "Warm Contemporary European",
            "design_intent": (
                "Create a calm, tactile living room that respects the existing geometry "
                "while introducing a restrained Contemporary Europe material language."
            ),
            "mood": moods,
            "colour_direction": ["warm neutrals", "soft mineral whites", "muted timber tones"],
            "material_palette": materials[(idx % 2) :] + materials[: (idx % 2)] ,
            "lighting_strategy": [
                "retain natural light",
                "add layered low-level lighting",
                "avoid flat overhead-only illumination",
            ],
            "furniture_direction": [
                "low-profile sofa",
                "natural upholstery",
                "simple sculptural side table",
            ],
            "focal_point": "Primary seating mass aligned to the daylight axis",
            "spatial_hierarchy": "One dominant calm plane with quieter secondary surfaces",
            "preserve": ["windows", "fireplace", "door positions", "room proportions"],
            "allowed_changes": ["wall finish", "floor finish", "lighting", "furniture", "joinery"],
            "likely_trades": ["decorator", "electrician", "joiner"],
            "positive_rules": [
                "maintain restrained palette",
                "use tonal material contrast",
            ],
            "negative_warnings": [
                "avoid oversized furniture",
                "avoid excessive decorative lighting",
            ],
        }
        # Ensure material_palette length stays in schema bounds
        payload["material_palette"] = payload["material_palette"][:4] or materials[:3]
        _ = (reference_image_paths, prompt, response_schema)
        meta = ModelCallMetadata(
            provider="fake",
            model_name=self.model_name,
            request_id=f"fake-concept-{digest[:10]}",
            latency_ms=max(1, int((time.perf_counter() - started) * 1000)),
            input_tokens=200,
            output_tokens=350,
            total_tokens=550,
            attempt=1,
        )
        return payload, meta

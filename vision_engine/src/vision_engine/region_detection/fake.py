from __future__ import annotations

import hashlib

from vision_engine.region_detection.models import DetectedRegionProposal, RegionDetectionResult
from vision_engine.region_detection.templates import normalise_room_type, template_regions


class FakeRegionDetector:
    """Deterministic region proposals for offline tests and UI demos."""

    def __init__(self, *, model_name: str = "fake-region-detector-v1"):
        self.model_name = model_name

    def detect_regions(
        self,
        *,
        image_path: str,
        room_type: str | None,
        concept_version_id: str,
        image_uri: str,
    ) -> RegionDetectionResult:
        normalised = normalise_room_type(room_type)
        template = template_regions(room_type)
        digest = hashlib.sha256(f"{image_path}:{normalised}".encode()).hexdigest()
        seed = int(digest[:8], 16)

        proposals: list[DetectedRegionProposal] = []
        for index, item in enumerate(template):
            row = (seed + index * 17) % 5
            col = index % 3
            width = 0.22 + (row % 3) * 0.04
            height = 0.18 + (col % 2) * 0.05
            x = 0.08 + col * 0.28
            y = 0.12 + row * 0.14
            confidence = round(0.55 + ((seed >> (index % 8)) & 0xF) / 40.0, 2)
            kind = "detected" if index < max(2, len(template) - 1) else "proposed"
            if kind == "proposed":
                confidence = round(confidence * 0.65, 2)
            proposals.append(
                DetectedRegionProposal(
                    region_code=item["region_code"],
                    region_type=item["region_type"],
                    display_name=item["display_name"],
                    geometry_json={
                        "x": min(0.75, x),
                        "y": min(0.72, y),
                        "width": min(0.35, width),
                        "height": min(0.32, height),
                    },
                    confidence=confidence,
                    detection_kind=kind,
                    is_fixed=item["region_type"] in {"floor_finish", "wall_finish", "ceiling_finish"},
                    rationale=f"Fake detector layout for {normalised} ({kind})",
                )
            )

        return RegionDetectionResult(
            provider="fake",
            model_name=self.model_name,
            room_type=normalised,
            inferred_room_type=normalised,
            concept_version_id=concept_version_id,
            image_uri=image_uri,
            regions=proposals,
            metadata={"deterministic_seed": seed},
        )

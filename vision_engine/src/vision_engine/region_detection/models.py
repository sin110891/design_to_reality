from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


DetectionKind = Literal["detected", "proposed"]


@dataclass
class DetectedRegionProposal:
    region_code: str
    region_type: str
    display_name: str
    geometry_json: dict[str, float]
    confidence: float
    detection_kind: DetectionKind = "detected"
    is_fixed: bool = False
    rationale: str | None = None


@dataclass
class RegionDetectionResult:
    provider: str
    model_name: str
    room_type: str
    inferred_room_type: str | None
    concept_version_id: str
    image_uri: str
    regions: list[DetectedRegionProposal] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

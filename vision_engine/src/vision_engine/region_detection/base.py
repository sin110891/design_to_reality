from __future__ import annotations

from typing import Protocol

from vision_engine.region_detection.models import RegionDetectionResult


class RegionDetectionProvider(Protocol):
    def detect_regions(
        self,
        *,
        image_path: str,
        room_type: str | None,
        concept_version_id: str,
        image_uri: str,
    ) -> RegionDetectionResult: ...

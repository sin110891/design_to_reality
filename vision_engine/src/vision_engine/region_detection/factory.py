from __future__ import annotations

from vision_engine.region_detection.base import RegionDetectionProvider
from vision_engine.region_detection.fake import FakeRegionDetector
from vision_engine.region_detection.gemini import GeminiRegionDetector
from vision_engine.settings import AppSettings


def build_region_detector(settings: AppSettings) -> RegionDetectionProvider:
    provider = settings.region_detection.provider.lower().strip()
    if provider == "gemini" and settings.gemini_api_key:
        return GeminiRegionDetector(
            api_key=settings.gemini_api_key,
            model_name=settings.region_detection.model_name,
            timeout_seconds=settings.inference.timeout_seconds,
            max_attempts=settings.inference.max_attempts,
            temperature=settings.region_detection.temperature,
            min_confidence=settings.region_detection.min_confidence,
        )
    return FakeRegionDetector(model_name=settings.region_detection.fake_model_name)

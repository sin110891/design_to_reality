from __future__ import annotations

from vision_engine.region_detection.fake import FakeRegionDetector
from vision_engine.region_detection.templates import normalise_room_type


def test_fake_detector_returns_bedroom_regions(tmp_path):
    image = tmp_path / "bedroom.png"
    image.write_bytes(b"fake-image")
    detector = FakeRegionDetector()
    result = detector.detect_regions(
        image_path=str(image),
        room_type="bedroom",
        concept_version_id="cv_test",
        image_uri="data/concept.png",
    )
    assert result.provider == "fake"
    assert result.room_type == normalise_room_type("bedroom")
    assert len(result.regions) >= 4
    assert any(region.region_type == "bed" for region in result.regions)
    assert any(region.detection_kind == "proposed" for region in result.regions)

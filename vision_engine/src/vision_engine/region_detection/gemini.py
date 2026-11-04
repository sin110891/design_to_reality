from __future__ import annotations

import json
import mimetypes
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from vision_engine.domain.errors import ConfigurationError, ProviderError
from vision_engine.region_detection.fake import FakeRegionDetector
from vision_engine.region_detection.models import DetectedRegionProposal, RegionDetectionResult
from vision_engine.region_detection.templates import allowed_region_types, normalise_room_type

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

REGION_DETECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "inferred_room_type": {"type": "string"},
        "regions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "region_code": {"type": "string"},
                    "region_type": {"type": "string"},
                    "display_name": {"type": "string"},
                    "bbox": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "width": {"type": "number"},
                            "height": {"type": "number"},
                        },
                        "required": ["x", "y", "width", "height"],
                    },
                    "confidence": {"type": "number"},
                    "detection_kind": {"type": "string"},
                    "is_fixed": {"type": "boolean"},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "region_code",
                    "region_type",
                    "display_name",
                    "bbox",
                    "confidence",
                ],
            },
        },
    },
    "required": ["inferred_room_type", "regions"],
}


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, ProviderError) and exc.transient


class GeminiRegionDetector:
    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        timeout_seconds: int = 120,
        max_attempts: int = 3,
        temperature: float = 0.1,
        min_confidence: float = 0.35,
    ):
        if not api_key:
            raise ConfigurationError("GEMINI_API_KEY is required for gemini region detection")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.temperature = temperature
        self.min_confidence = min_confidence
        self._client = None
        self._env = Environment(
            loader=FileSystemLoader(PROMPTS_DIR),
            autoescape=select_autoescape(enabled_extensions=()),
        )

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def detect_regions(
        self,
        *,
        image_path: str,
        room_type: str | None,
        concept_version_id: str,
        image_uri: str,
    ) -> RegionDetectionResult:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential_jitter(initial=1, max=20),
            retry=retry_if_exception(_is_transient),
        )
        def _call() -> RegionDetectionResult:
            return self._once(
                image_path=image_path,
                room_type=room_type,
                concept_version_id=concept_version_id,
                image_uri=image_uri,
            )

        return _call()

    def _once(
        self,
        *,
        image_path: str,
        room_type: str | None,
        concept_version_id: str,
        image_uri: str,
    ) -> RegionDetectionResult:
        from google.genai import types

        path = Path(image_path)
        prompt = self._env.get_template("region_detection.jinja2").render(
            room_type=normalise_room_type(room_type),
            allowed_region_types=allowed_region_types(room_type),
        )
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        parts = [
            types.Part.from_text(text="CONCEPT IMAGE:"),
            types.Part.from_bytes(data=path.read_bytes(), mime_type=mime),
            types.Part.from_text(text=prompt),
        ]
        started = time.perf_counter()
        try:
            response = self._get_client().models.generate_content(
                model=self.model_name,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    response_mime_type="application/json",
                    response_schema=REGION_DETECTION_SCHEMA,
                    http_options=types.HttpOptions(timeout=self.timeout_seconds * 1000),
                ),
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            transient = any(
                token in message.lower()
                for token in ("timeout", "429", "503", "unavailable", "temporar", "rate")
            )
            raise ProviderError(message, transient=transient) from exc

        text = getattr(response, "text", None)
        if not text:
            raise ProviderError("Gemini returned empty region detection response", transient=False)
        payload = json.loads(text)
        proposals = self._parse_regions(payload)
        if not proposals:
            fallback = FakeRegionDetector(model_name="fake-region-fallback")
            return fallback.detect_regions(
                image_path=image_path,
                room_type=room_type,
                concept_version_id=concept_version_id,
                image_uri=image_uri,
            )

        return RegionDetectionResult(
            provider="gemini",
            model_name=self.model_name,
            room_type=normalise_room_type(room_type),
            inferred_room_type=payload.get("inferred_room_type"),
            concept_version_id=concept_version_id,
            image_uri=image_uri,
            regions=proposals,
            metadata={
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "response_id": getattr(response, "response_id", None),
            },
        )

    def _parse_regions(self, payload: dict) -> list[DetectedRegionProposal]:
        proposals: list[DetectedRegionProposal] = []
        for raw in payload.get("regions") or []:
            confidence = float(raw.get("confidence", 0))
            if confidence < self.min_confidence:
                continue
            bbox = raw.get("bbox") or {}
            kind = raw.get("detection_kind", "detected")
            if kind not in {"detected", "proposed"}:
                kind = "detected"
            proposals.append(
                DetectedRegionProposal(
                    region_code=str(raw["region_code"]).strip(),
                    region_type=str(raw["region_type"]).strip(),
                    display_name=str(raw["display_name"]).strip(),
                    geometry_json={
                        "x": float(bbox.get("x", 0.2)),
                        "y": float(bbox.get("y", 0.2)),
                        "width": float(bbox.get("width", 0.25)),
                        "height": float(bbox.get("height", 0.25)),
                    },
                    confidence=confidence,
                    detection_kind=kind,
                    is_fixed=bool(raw.get("is_fixed", False)),
                    rationale=raw.get("rationale"),
                )
            )
        return proposals

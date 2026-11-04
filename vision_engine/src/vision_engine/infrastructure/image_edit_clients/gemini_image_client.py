from __future__ import annotations

import io
import mimetypes
import time
from pathlib import Path

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from vision_engine.domain.errors import ConfigurationError, ProviderError
from vision_engine.domain.models import DesignDirection, ModelCallMetadata
from vision_engine.infrastructure.file_store import FileStore


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, ProviderError) and exc.transient


class GeminiImageEditClient:
    """
    Pluggable Gemini image-editing client.

    Uses generate_content with the room image + references + edit prompt.
    Falls back to raising ProviderError when the model returns no image parts.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        file_store: FileStore,
        timeout_seconds: int = 180,
        max_attempts: int = 3,
        temperature: float = 0.4,
    ):
        if not api_key:
            raise ConfigurationError("GEMINI_API_KEY is required for Gemini image editing")
        self.api_key = api_key
        self.model_name = model_name
        self.file_store = file_store
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.temperature = temperature
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def edit_room(
        self,
        room_image_path: str | Path,
        reference_image_paths: list[str | Path],
        design_direction: dict | DesignDirection,
        output_count: int = 3,
        *,
        prompts: list[str] | None = None,
        project_id: str = "proj_local",
    ) -> tuple[list[str], ModelCallMetadata]:
        if not prompts or len(prompts) < output_count:
            raise ProviderError("Image edit prompts are required for each variant", transient=False)

        attempt_holder = {"n": 0}
        started = time.perf_counter()
        paths: list[str] = []

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential_jitter(initial=1, max=20),
            retry=retry_if_exception(_is_transient),
        )
        def _one(prompt: str, key: str) -> str:
            attempt_holder["n"] += 1
            return self._edit_once(
                room_image_path=Path(room_image_path),
                reference_image_paths=[Path(p) for p in reference_image_paths],
                prompt=prompt,
                project_id=project_id,
                variant_key=key,
                attempt=attempt_holder["n"],
            )

        for i in range(output_count):
            key = f"variant_{chr(ord('a') + i)}"
            paths.append(_one(prompts[i], key))

        direction = (
            design_direction.model_dump()
            if isinstance(design_direction, DesignDirection)
            else design_direction
        )
        _ = direction
        meta = ModelCallMetadata(
            provider="gemini",
            model_name=self.model_name,
            latency_ms=int((time.perf_counter() - started) * 1000),
            attempt=attempt_holder["n"],
        )
        return paths, meta

    def _edit_once(
        self,
        *,
        room_image_path: Path,
        reference_image_paths: list[Path],
        prompt: str,
        project_id: str,
        variant_key: str,
        attempt: int,
    ) -> str:
        from google.genai import types

        parts: list = []
        mime = mimetypes.guess_type(str(room_image_path))[0] or "image/jpeg"
        parts.append(types.Part.from_text(text="ORIGINAL ROOM (edit this image):"))
        parts.append(types.Part.from_bytes(data=room_image_path.read_bytes(), mime_type=mime))
        for i, ref in enumerate(reference_image_paths[:3], start=1):
            ref_mime = mimetypes.guess_type(str(ref))[0] or "image/jpeg"
            parts.append(types.Part.from_text(text=f"REFERENCE {i} (taste/material cue only):"))
            parts.append(types.Part.from_bytes(data=ref.read_bytes(), mime_type=ref_mime))
        parts.append(types.Part.from_text(text=prompt))

        try:
            response = self._get_client().models.generate_content(
                model=self.model_name,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    response_modalities=["TEXT", "IMAGE"],
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

        image_bytes = _extract_image_bytes(response)
        if not image_bytes:
            raise ProviderError("Gemini image edit returned no image bytes", transient=False)

        dest = self.file_store.store_generated(
            project_id=project_id,
            variant_key=f"{variant_key}_attempt{attempt}",
            image_bytes=image_bytes,
            extension=".png",
        )
        return str(dest)


def _extract_image_bytes(response) -> bytes | None:
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                data = inline.data
                if isinstance(data, bytes):
                    return data
                import base64

                return base64.b64decode(data)
    return None

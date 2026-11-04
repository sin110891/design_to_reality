from __future__ import annotations

import json
import mimetypes
import time
from pathlib import Path

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from vision_engine.domain.errors import ConfigurationError, ProviderError
from vision_engine.domain.models import ModelCallMetadata


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, ProviderError) and exc.transient


class GeminiConceptClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        timeout_seconds: int = 120,
        max_attempts: int = 3,
        temperature: float = 0.2,
    ):
        if not api_key:
            raise ConfigurationError("GEMINI_API_KEY is required when MODEL_PROVIDER=gemini")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.temperature = temperature
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate_concept(
        self,
        *,
        room_image_path: Path,
        reference_image_paths: list[Path],
        prompt: str,
        response_schema: dict,
    ) -> tuple[dict, ModelCallMetadata]:
        attempt_holder = {"n": 0}

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential_jitter(initial=1, max=20),
            retry=retry_if_exception(_is_transient),
        )
        def _call() -> tuple[dict, ModelCallMetadata]:
            attempt_holder["n"] += 1
            return self._once(
                room_image_path=room_image_path,
                reference_image_paths=reference_image_paths,
                prompt=prompt,
                response_schema=response_schema,
                attempt=attempt_holder["n"],
            )

        return _call()

    def _once(
        self,
        *,
        room_image_path: Path,
        reference_image_paths: list[Path],
        prompt: str,
        response_schema: dict,
        attempt: int,
    ) -> tuple[dict, ModelCallMetadata]:
        from google.genai import types

        started = time.perf_counter()
        parts: list = []

        def add_image(path: Path, label: str) -> None:
            mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
            parts.append(types.Part.from_text(text=label))
            parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=mime))

        add_image(room_image_path, "ORIGINAL ROOM IMAGE:")
        for i, ref in enumerate(reference_image_paths[:3], start=1):
            add_image(ref, f"CURATED REFERENCE {i}:")
        parts.append(types.Part.from_text(text=prompt))

        try:
            response = self._get_client().models.generate_content(
                model=self.model_name,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=self.temperature,
                    response_mime_type="application/json",
                    response_schema=response_schema,
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
            raise ProviderError("Gemini returned empty response text", transient=False)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Gemini returned non-JSON text: {exc}", transient=False) from exc

        usage = getattr(response, "usage_metadata", None)
        meta = ModelCallMetadata(
            provider="gemini",
            model_name=self.model_name,
            request_id=getattr(response, "response_id", None),
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=getattr(usage, "prompt_token_count", None) if usage else None,
            output_tokens=getattr(usage, "candidates_token_count", None) if usage else None,
            total_tokens=getattr(usage, "total_token_count", None) if usage else None,
            attempt=attempt,
        )
        return payload, meta

from __future__ import annotations

import json
import mimetypes
import time
from pathlib import Path

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from design_dataset.domain.errors import ConfigurationError, ProviderError
from design_dataset.domain.models import ModelCallMetadata


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, ProviderError) and exc.transient


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        model_name: str,
        timeout_seconds: int = 90,
        max_attempts: int = 3,
        temperature: float = 0.1,
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

    def label_image(
        self,
        *,
        image_path: Path,
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
            return self._label_once(
                image_path=image_path,
                prompt=prompt,
                response_schema=response_schema,
                attempt=attempt_holder["n"],
            )

        return _call()

    def _label_once(
        self,
        *,
        image_path: Path,
        prompt: str,
        response_schema: dict,
        attempt: int,
    ) -> tuple[dict, ModelCallMetadata]:
        from google.genai import types

        started = time.perf_counter()
        mime_type = mimetypes.guess_type(str(image_path))[0] or "image/jpeg"
        image_bytes = image_path.read_bytes()
        client = self._get_client()

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            types.Part.from_text(text=prompt),
                        ],
                    )
                ],
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
        input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        total_tokens = getattr(usage, "total_token_count", None) if usage else None
        request_id = None
        if hasattr(response, "response_id"):
            request_id = getattr(response, "response_id")
        elif hasattr(response, "sdk_http_response"):
            headers = getattr(response.sdk_http_response, "headers", None) or {}
            request_id = headers.get("x-request-id") or headers.get("x-goog-request-id")

        meta = ModelCallMetadata(
            provider="gemini",
            model_name=self.model_name,
            request_id=request_id,
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            attempt=attempt,
        )
        return payload, meta

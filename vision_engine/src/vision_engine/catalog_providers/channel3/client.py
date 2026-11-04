from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from vision_engine.catalog_providers.errors import Channel3Error


class Channel3Client:
    BASE_URL = "https://api.trychannel3.com"

    def __init__(
        self,
        *,
        api_key: str,
        country: str = "GB",
        currency: str = "GBP",
        language: str = "en",
        timeout_seconds: int = 30,
    ):
        if not api_key:
            raise Channel3Error("CHANNEL3_API_KEY is required")
        self.api_key = api_key
        self.country = country
        self.currency = currency
        self.language = language
        self.timeout_seconds = timeout_seconds

    def search_products(
        self,
        *,
        query: str | None = None,
        image_url: str | None = None,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "limit": min(max(limit, 1), 30),
            "filters": filters or {},
            "config": {
                "country": self.country,
                "currency": self.currency,
                "language": self.language,
            },
        }
        if query:
            payload["query"] = query
        if image_url:
            payload["image_url"] = image_url
        if page_token:
            payload["page_token"] = page_token
        return self._request("POST", "/v1/search", payload=payload)

    def get_product(
        self,
        product_id: str,
        *,
        length_unit: str = "mm",
        weight_unit: str = "kg",
    ) -> dict[str, Any]:
        params = urllib.parse.urlencode(
            {
                "country": self.country,
                "currency": self.currency,
                "language": self.language,
                "length_unit": length_unit,
                "weight_unit": weight_unit,
            }
        )
        path = f"/v1/products/{urllib.parse.quote(product_id)}?{params}"
        return self._request("GET", path)

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        data = None
        headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise Channel3Error(f"Channel3 HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise Channel3Error(f"Channel3 request failed: {exc.reason}") from exc
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise Channel3Error("Channel3 returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise Channel3Error("Channel3 returned unexpected payload")
        return parsed


def stable_internal_product_id(external_product_id: str) -> str:
    digest = hashlib.sha256(external_product_id.encode("utf-8")).hexdigest()[:16]
    return f"c3_{digest}"

from __future__ import annotations

from typing import Any, Protocol

from vision_engine.concept_board.domain.models import CatalogueImportRow


class CatalogSearchRequest(Protocol):
    query: str
    limit: int
    country: str
    currency: str
    language: str
    max_price: float | None
    image_url: str | None
    region_type: str


class CatalogProvider(Protocol):
    def search_products(self, request: dict[str, Any]) -> list[dict[str, Any]]:
        """Return raw provider product payloads."""

    def get_product(self, external_product_id: str, **params: Any) -> dict[str, Any]:
        """Return raw provider product payload."""

    def map_products(
        self,
        products: list[dict[str, Any]],
        *,
        region_type: str,
        region_types: list[str] | None = None,
    ) -> list[CatalogueImportRow]:
        """Map provider payloads to internal import rows."""

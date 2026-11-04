from __future__ import annotations

from typing import Any

from vision_engine.catalog_providers.channel3.client import Channel3Client
from vision_engine.catalog_providers.channel3.mapper import map_channel3_products
from vision_engine.catalog_providers.channel3.queries import build_search_query
from vision_engine.catalog_providers.errors import Channel3Error
from vision_engine.concept_board.application.catalogue_import import import_catalogue_rows
from vision_engine.concept_board.domain.errors import CatalogueError
from vision_engine.concept_board.domain.models import (
    CatalogueImportRow,
    CatalogueSnapshotRecord,
    ProductRecord,
    ProductVariantRecord,
    SupplierOfferRecord,
)
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import utcnow
from vision_engine.settings import AppSettings


def build_channel3_client(settings: AppSettings) -> Channel3Client:
    api_key = settings.channel3_api_key
    if not api_key:
        raise Channel3Error(
            "CHANNEL3_API_KEY is not configured. Set CHANNEL3_API_KEY in vision_engine/.env"
        )
    return Channel3Client(
        api_key=api_key,
        country=settings.channel3.country,
        currency=settings.channel3.currency,
        language=settings.channel3.language,
        timeout_seconds=settings.channel3.timeout_seconds,
    )


def ping_channel3(
    *,
    settings: AppSettings,
    query: str = "sofa",
    client: Channel3Client | None = None,
) -> dict[str, str | int]:
    """Lightweight live API check — search with limit 1, no catalogue import."""
    channel3 = client or build_channel3_client(settings)
    response = channel3.search_products(
        query=query,
        limit=1,
        filters={"availability": ["InStock", "LimitedAvailability"]},
    )
    products = response.get("products") or []
    return {
        "ok": True,
        "product_count": len(products),
        "country": settings.channel3.country,
        "currency": settings.channel3.currency,
        "language": settings.channel3.language,
        "query": query,
    }


def search_channel3_for_region(
    *,
    settings: AppSettings,
    region_type: str,
    display_name: str | None = None,
    max_budget: float | None = None,
    image_url: str | None = None,
    limit: int = 20,
    client: Channel3Client | None = None,
) -> list[CatalogueImportRow]:
    channel3 = client or build_channel3_client(settings)
    query = build_search_query(region_type=region_type, display_name=display_name)
    filters: dict[str, Any] = {
        "availability": ["InStock", "LimitedAvailability"],
    }
    if max_budget is not None:
        filters["price"] = {"max_price": max_budget}

    response = channel3.search_products(
        query=query if not image_url else None,
        image_url=image_url,
        limit=limit,
        filters=filters,
    )
    products = response.get("products") or []
    rows = map_channel3_products(products, region_type=region_type, region_types=[region_type])
    if not rows:
        raise CatalogueError(f"Channel3 returned no usable products for region type '{region_type}'")
    return rows


def import_channel3_snapshot_for_region(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings,
    design_region_id: str,
    region_type: str,
    display_name: str | None = None,
    max_budget: float | None = None,
    image_url: str | None = None,
    snapshot_name: str | None = None,
    limit: int = 20,
    client: Channel3Client | None = None,
) -> tuple[CatalogueSnapshotRecord, list[CatalogueImportRow]]:
    rows = search_channel3_for_region(
        settings=settings,
        region_type=region_type,
        display_name=display_name,
        max_budget=max_budget,
        image_url=image_url,
        limit=limit,
        client=client,
    )
    name = snapshot_name or f"channel3-{design_region_id}-{new_id('snap')}"
    snapshot = import_catalogue_rows(
        repo=repo,
        import_rows=rows,
        snapshot_name=name,
        manifest_source=f"channel3://search/{design_region_id}",
        seal=True,
    )
    return snapshot, rows


def refresh_channel3_product_offer(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings,
    product_variant_id: str,
    client: Channel3Client | None = None,
) -> tuple[ProductRecord, ProductVariantRecord, SupplierOfferRecord]:
    details = repo.get_product_variant_details(product_variant_id)
    if details is None:
        raise CatalogueError(f"Product variant not found: {product_variant_id}")
    product, variant = details
    external_id = product.external_product_id or variant.attributes_json.get("external_product_id")
    if product.external_provider != "channel3" or not external_id:
        raise CatalogueError("Variant is not linked to a Channel3 product")

    channel3 = client or build_channel3_client(settings)
    payload = channel3.get_product(external_id)
    rows = map_channel3_products([payload], region_type=product.product_type)
    if not rows:
        raise CatalogueError(f"Could not refresh Channel3 product: {external_id}")
    row = rows[0]
    now = utcnow()

    updated_product = product.model_copy(
        update={
            "canonical_name": row.canonical_name,
            "brand_name": row.brand_name,
            "description": row.description,
            "updated_at": now,
        }
    )
    updated_variant = variant.model_copy(
        update={
            "colour": row.colour,
            "material": row.material,
            "width_mm": row.width_mm,
            "height_mm": row.height_mm,
            "depth_mm": row.depth_mm,
            "attributes_json": row.attributes_json,
        }
    )
    repo.save_product(updated_product)
    repo.save_product_variant(updated_variant)

    offer = repo.get_supplier_offer_for_variant(product_variant_id)
    if offer is None:
        raise CatalogueError(f"No supplier offer for variant: {product_variant_id}")

    updated_offer = offer.model_copy(
        update={
            "unit_price": row.unit_price,
            "currency_code": row.currency_code,
            "stock_status": row.stock_status,
            "buy_url": row.buy_url,
            "external_provider": "channel3",
            "price_checked_at": now,
        }
    )
    repo.save_supplier_offer(updated_offer)
    return updated_product, updated_variant, updated_offer

from __future__ import annotations

from typing import Any

from vision_engine.catalog_providers.channel3.client import stable_internal_product_id
from vision_engine.concept_board.domain.models import CatalogueImportRow


LENGTH_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
    "ft": 304.8,
}


def _length_to_mm(value: dict[str, Any] | None) -> float | None:
    if not value:
        return None
    number = value.get("number")
    unit = value.get("unit")
    if number is None or unit is None:
        return None
    factor = LENGTH_TO_MM.get(str(unit), None)
    if factor is None:
        return None
    return float(number) * factor


def _pick_offer(product: dict[str, Any]) -> dict[str, Any] | None:
    offers = product.get("offers") or []
    if not offers:
        return None
    in_stock = [offer for offer in offers if offer.get("availability") == "InStock"]
    return (in_stock or offers)[0]


def _pick_image(product: dict[str, Any]) -> dict[str, Any] | None:
    images = _normalise_product_images(product)
    if not images:
        return None
    cleaned = [img for img in images if img.get("is_cleaned_image")]
    return (cleaned or images)[0]


def _normalise_product_images(product: dict[str, Any]) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    for raw in product.get("images") or []:
        if isinstance(raw, str):
            url = raw.strip()
            if url:
                images.append({"url": url, "is_cleaned_image": False})
            continue
        if not isinstance(raw, dict):
            continue
        url = raw.get("url")
        if not url:
            continue
        images.append(
            {
                "url": str(url),
                "is_cleaned_image": bool(raw.get("is_cleaned_image", False)),
            }
        )
    return images


def _category_slug_title(category: Any) -> tuple[str, str]:
    if isinstance(category, str):
        text = category.lower()
        return text, text
    if isinstance(category, dict):
        slug = str(category.get("slug") or "").lower()
        title = str(category.get("title") or "").lower()
        return slug, title
    return "", ""


def _brand_name(brand: Any) -> str | None:
    if isinstance(brand, str):
        return brand or None
    if isinstance(brand, dict):
        name = brand.get("name")
        return str(name) if name else None
    return None


def _infer_product_type(product: dict[str, Any], region_type: str) -> str:
    categories = product.get("categories") or []
    if categories:
        slug, title = _category_slug_title(categories[0])
        if "sofa" in slug or "sofa" in title:
            return "sofa"
        if "light" in slug or "light" in title or "lamp" in title:
            return "pendant_light"
        if "wardrobe" in slug or "wardrobe" in title:
            return "joinery"
        if "rug" in slug or "rug" in title:
            return "rug"
        if "table" in slug or "table" in title:
            return "coffee_table"
    return region_type


def _availability_to_stock(status: str | None) -> str:
    if status == "InStock":
        return "in_stock"
    if status == "LimitedAvailability":
        return "limited"
    return "out_of_stock"


def map_channel3_product(
    product: dict[str, Any],
    *,
    region_type: str,
    region_types: list[str] | None = None,
) -> CatalogueImportRow | None:
    external_id = product.get("id")
    title = product.get("title")
    if not external_id or not title:
        return None

    offer = _pick_offer(product)
    if offer is None:
        return None

    price_obj = offer.get("price") or {}
    unit_price = price_obj.get("price")
    currency_code = price_obj.get("currency") or "GBP"
    if unit_price is None:
        return None

    image = _pick_image(product)
    product_images = _normalise_product_images(product)
    dimensions = offer.get("dimensions") or {}
    brands = product.get("brands") or []
    brand_name = _brand_name(brands[0]) if brands else None
    materials = product.get("materials") or []
    material = materials[0] if materials else None

    mapped_region_types = region_types or [region_type]
    attributes = {
        "external_provider": "channel3",
        "external_product_id": external_id,
        "reference_image_uri": image.get("url") if image else None,
        "image_uri": image.get("url") if image else None,
        "product_images": product_images,
        "buy_url": offer.get("url"),
        "merchant_domain": offer.get("domain"),
        "availability": offer.get("availability"),
        "region_types": mapped_region_types,
    }

    return CatalogueImportRow(
        product_id=stable_internal_product_id(external_id),
        canonical_name=title,
        brand_name=brand_name,
        product_type=_infer_product_type(product, region_type),
        description=product.get("description"),
        variant_sku=f"{external_id}:{offer.get('domain', 'offer')}",
        colour=(product.get("structured_attributes") or {}).get("color"),
        finish=None,
        material=material,
        width_mm=_length_to_mm(dimensions.get("width")),
        height_mm=_length_to_mm(dimensions.get("height")),
        depth_mm=_length_to_mm(dimensions.get("length")),
        supplier_name=offer.get("domain") or "channel3_merchant",
        supplier_sku=offer.get("url") or external_id,
        unit_price=float(unit_price),
        currency_code=str(currency_code),
        stock_status=_availability_to_stock(offer.get("availability")),
        lead_time_days_min=None,
        lead_time_days_max=None,
        region_types=mapped_region_types,
        external_provider="channel3",
        external_product_id=external_id,
        reference_image_uri=image.get("url") if image else None,
        buy_url=offer.get("url"),
        attributes_json=attributes,
    )


def map_channel3_products(
    products: list[dict[str, Any]],
    *,
    region_type: str,
    region_types: list[str] | None = None,
) -> list[CatalogueImportRow]:
    rows: list[CatalogueImportRow] = []
    for product in products:
        row = map_channel3_product(
            product,
            region_type=region_type,
            region_types=region_types,
        )
        if row is not None:
            rows.append(row)
    return rows

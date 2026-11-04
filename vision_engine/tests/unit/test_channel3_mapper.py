from __future__ import annotations

from vision_engine.catalog_providers.channel3.mapper import map_channel3_product, map_channel3_products

SAMPLE_PRODUCT = {
    "id": "prod_abc123",
    "title": "Modern Grey Sofa",
    "description": "Three-seater fabric sofa",
    "categories": [{"slug": "sofas", "title": "Sofas"}],
    "brands": [{"name": "Acme Home"}],
    "materials": ["fabric"],
    "structured_attributes": {"color": "grey"},
    "images": [
        {"url": "https://cdn.example.com/raw.jpg", "is_cleaned_image": False},
        {"url": "https://cdn.example.com/clean.jpg", "is_cleaned_image": True},
    ],
    "offers": [
        {
            "availability": "InStock",
            "domain": "example-retailer.co.uk",
            "url": "https://example-retailer.co.uk/sofa",
            "price": {"price": 1299.0, "currency": "GBP"},
            "dimensions": {
                "width": {"number": 210, "unit": "cm"},
                "height": {"number": 85, "unit": "cm"},
                "length": {"number": 95, "unit": "cm"},
            },
        }
    ],
}


def test_map_channel3_product_prefers_clean_image_and_in_stock_offer():
    row = map_channel3_product(SAMPLE_PRODUCT, region_type="sofa")
    assert row is not None
    assert row.external_provider == "channel3"
    assert row.external_product_id == "prod_abc123"
    assert row.product_type == "sofa"
    assert row.unit_price == 1299.0
    assert row.currency_code == "GBP"
    assert row.stock_status == "in_stock"
    assert row.reference_image_uri == "https://cdn.example.com/clean.jpg"
    assert row.buy_url == "https://example-retailer.co.uk/sofa"
    assert row.width_mm == 2100.0
    assert row.height_mm == 850.0
    assert row.depth_mm == 950.0
    assert row.colour == "grey"
    assert row.region_types == ["sofa"]


def test_map_channel3_product_skips_products_without_offers():
    payload = dict(SAMPLE_PRODUCT)
    payload["offers"] = []
    assert map_channel3_product(payload, region_type="sofa") is None


def test_map_channel3_products_filters_invalid_rows():
    rows = map_channel3_products(
        [SAMPLE_PRODUCT, {"id": "missing-title", "offers": []}],
        region_type="sofa",
    )
    assert len(rows) == 1
    assert rows[0].canonical_name == "Modern Grey Sofa"


def test_map_channel3_product_accepts_string_categories_and_brands():
    payload = dict(SAMPLE_PRODUCT)
    payload["categories"] = ["sofas"]
    payload["brands"] = ["Acme Home"]
    row = map_channel3_product(payload, region_type="coffee_table")
    assert row is not None
    assert row.product_type == "sofa"
    assert row.brand_name == "Acme Home"


def test_map_channel3_product_stores_all_product_images():
    row = map_channel3_product(SAMPLE_PRODUCT, region_type="sofa")
    assert row is not None
    images = row.attributes_json["product_images"]
    assert len(images) == 2
    assert images[0]["url"] == "https://cdn.example.com/raw.jpg"
    assert images[1]["url"] == "https://cdn.example.com/clean.jpg"
    assert images[1]["is_cleaned_image"] is True

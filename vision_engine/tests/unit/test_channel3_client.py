from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from vision_engine.catalog_providers.channel3.client import Channel3Client, stable_internal_product_id
from vision_engine.catalog_providers.errors import Channel3Error


def test_stable_internal_product_id_is_deterministic():
    assert stable_internal_product_id("prod_abc123") == stable_internal_product_id("prod_abc123")
    assert stable_internal_product_id("prod_abc123").startswith("c3_")


def test_search_products_posts_payload():
    client = Channel3Client(api_key="test-key", country="GB", currency="GBP", language="en")
    response_body = json.dumps({"products": []}).encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = response_body
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as urlopen:
        result = client.search_products(query="sofa", limit=5, filters={"availability": ["InStock"]})

    assert result == {"products": []}
    request = urlopen.call_args.args[0]
    assert request.get_method() == "POST"
    assert request.full_url.endswith("/v1/search")
    header_map = {key.lower(): value for key, value in request.header_items()}
    assert header_map["x-api-key"] == "test-key"
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["query"] == "sofa"
    assert payload["limit"] == 5
    assert payload["config"]["currency"] == "GBP"


def test_get_product_builds_query_params():
    client = Channel3Client(api_key="test-key")
    response_body = json.dumps({"id": "prod_1", "title": "Sofa"}).encode("utf-8")
    mock_response = MagicMock()
    mock_response.read.return_value = response_body
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response) as urlopen:
        result = client.get_product("prod_1")

    assert result["id"] == "prod_1"
    request = urlopen.call_args.args[0]
    assert request.get_method() == "GET"
    assert "/v1/products/prod_1?" in request.full_url
    assert "currency=GBP" in request.full_url


def test_client_requires_api_key():
    with pytest.raises(Channel3Error):
        Channel3Client(api_key="")

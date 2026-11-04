from __future__ import annotations

from unittest.mock import MagicMock

from vision_engine.concept_board.application.channel3_catalogue import ping_channel3
from vision_engine.settings import AppSettings, clear_settings_cache


def test_ping_channel3_returns_search_summary(tmp_path):
    clear_settings_cache()
    settings = AppSettings(
        model_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "rulebook.yaml",
        app_config_path=tmp_path / "app.yaml",
        prompts_config_path=tmp_path / "prompts.yaml",
        project_root=tmp_path,
        channel3_api_key="test-key",
    )
    client = MagicMock()
    client.search_products.return_value = {"products": [{"id": "prod_1", "title": "Sofa"}]}

    result = ping_channel3(settings=settings, query="sofa", client=client)

    assert result["ok"] is True
    assert result["product_count"] == 1
    assert result["query"] == "sofa"
    client.search_products.assert_called_once_with(
        query="sofa",
        limit=1,
        filters={"availability": ["InStock", "LimitedAvailability"]},
    )

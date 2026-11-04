from __future__ import annotations

import json

import pytest

from vision_engine.ui.concept_board import fill_ids_from_pipeline


def test_fill_ids_from_pipeline_uses_selected_variant():
    pipeline = json.dumps(
        {
            "project_id": "proj_123",
            "variant_ids": ["var_a", "var_b"],
            "variant_kinds": ["closest", "conservative"],
        }
    )
    project_id, variant_id, status = fill_ids_from_pipeline(
        pipeline,
        "var_b | conservative",
    )
    assert project_id == "proj_123"
    assert variant_id == "var_b"
    assert "proj_123" in status


def test_fill_ids_from_pipeline_falls_back_to_first_variant():
    pipeline = json.dumps(
        {
            "project_id": "proj_123",
            "variant_ids": ["var_a"],
            "variant_kinds": ["closest"],
        }
    )
    project_id, variant_id, _status = fill_ids_from_pipeline(pipeline, None)
    assert project_id == "proj_123"
    assert variant_id == "var_a"


def test_fill_ids_from_pipeline_requires_session():
    with pytest.raises(Exception, match="Generate concepts"):
        fill_ids_from_pipeline("{}", None)

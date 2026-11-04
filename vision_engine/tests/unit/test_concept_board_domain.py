from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vision_engine.concept_board.domain.enums import (
    CandidateSource,
    CatalogueSnapshotStatus,
)
from vision_engine.concept_board.domain.errors import InvariantError
from datetime import datetime, timezone

from vision_engine.concept_board.domain.models import RegionCandidateRecord, SupplierOfferRecord
from vision_engine.concept_board.domain.validation import (
    assert_sealed_snapshot,
    product_types_for_region,
)


def test_product_types_for_region_sofa():
    types = product_types_for_region("sofa")
    assert "sofa" in types


def test_sealed_snapshot_invariant():
    assert_sealed_snapshot(CatalogueSnapshotStatus.SEALED, "test")
    with pytest.raises(InvariantError):
        assert_sealed_snapshot(CatalogueSnapshotStatus.DRAFT, "test")


def test_region_candidate_xor_variant():
    with pytest.raises(ValueError):
        RegionCandidateRecord(
            region_candidate_id="rc_1",
            design_region_id="dr_1",
            product_retrieval_run_id="prr_1",
            product_variant_id="pv_1",
            material_variant_id="mv_1",
            catalogue_snapshot_id="cs_1",
            candidate_source=CandidateSource.RULE_MATCH,
            created_at=datetime.now(timezone.utc),
        )


def test_supplier_offer_xor_variant():
    with pytest.raises(ValueError):
        SupplierOfferRecord(
            supplier_offer_id="off_1",
            supplier_id="sup_1",
            product_variant_id="pv_1",
            material_variant_id="mv_1",
            supplier_sku="SKU",
            unit_price=10.0,
            price_checked_at=datetime.now(timezone.utc),
        )

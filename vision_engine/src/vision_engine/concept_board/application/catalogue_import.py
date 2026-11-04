from __future__ import annotations

import hashlib
import json
from pathlib import Path

from vision_engine.concept_board.domain.enums import CatalogueSnapshotStatus
from vision_engine.concept_board.domain.errors import CatalogueError
from vision_engine.concept_board.domain.models import (
    CatalogueImportRow,
    CatalogueSnapshotRecord,
    ProductRecord,
    ProductVariantRecord,
    SupplierOfferRecord,
    SupplierRecord,
)
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import utcnow


def import_catalogue_rows(
    *,
    repo: ConceptBoardRepositoryMixin,
    import_rows: list[CatalogueImportRow],
    snapshot_name: str,
    manifest_source: str,
    seal: bool = True,
) -> CatalogueSnapshotRecord:
    if not import_rows:
        raise CatalogueError("Catalogue import rows are empty")

    now = utcnow()
    existing = repo.get_catalogue_snapshot_by_name(snapshot_name)
    if existing and existing.status == CatalogueSnapshotStatus.SEALED:
        raise CatalogueError(f"Snapshot already sealed: {snapshot_name}")

    snapshot_id = new_id("cs")
    manifest_payload = {
        "rows": [row.model_dump(mode="json") for row in import_rows],
        "source": manifest_source,
    }
    manifest_bytes = json.dumps(manifest_payload, sort_keys=True, default=str).encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    snapshot = CatalogueSnapshotRecord(
        catalogue_snapshot_id=snapshot_id,
        snapshot_name=snapshot_name,
        manifest_uri=manifest_source,
        manifest_sha256=manifest_sha256,
        item_count=len(import_rows),
        status=CatalogueSnapshotStatus.SEALED if seal else CatalogueSnapshotStatus.DRAFT,
        created_at=now,
        sealed_at=now if seal else None,
    )
    repo.save_catalogue_snapshot(snapshot)

    for row in import_rows:
        attributes = dict(row.attributes_json)
        attributes.setdefault("region_types", row.region_types)
        if row.reference_image_uri:
            attributes["reference_image_uri"] = row.reference_image_uri
            attributes["image_uri"] = row.reference_image_uri
        if row.buy_url:
            attributes["buy_url"] = row.buy_url
        if row.external_provider:
            attributes["external_provider"] = row.external_provider
        if row.external_product_id:
            attributes["external_product_id"] = row.external_product_id

        product = ProductRecord(
            product_id=row.product_id,
            canonical_name=row.canonical_name,
            brand_name=row.brand_name,
            product_type=row.product_type,
            description=row.description,
            manufacturer_sku=row.variant_sku,
            lifecycle_status="active",
            external_provider=row.external_provider,
            external_product_id=row.external_product_id,
            created_at=now,
            updated_at=now,
        )
        repo.save_product(product)

        variant_id = new_id("pv")
        variant = ProductVariantRecord(
            product_variant_id=variant_id,
            product_id=row.product_id,
            variant_sku=row.variant_sku,
            colour=row.colour,
            finish=row.finish,
            material=row.material,
            width_mm=row.width_mm,
            height_mm=row.height_mm,
            depth_mm=row.depth_mm,
            attributes_json=attributes,
            created_at=now,
        )
        repo.save_product_variant(variant)

        supplier = repo.get_supplier_by_name(row.supplier_name)
        if supplier is None:
            supplier = SupplierRecord(
                supplier_id=new_id("sup"),
                supplier_name=row.supplier_name,
                created_at=now,
                updated_at=now,
            )
            repo.save_supplier(supplier)

        offer = SupplierOfferRecord(
            supplier_offer_id=new_id("off"),
            supplier_id=supplier.supplier_id,
            product_variant_id=variant_id,
            supplier_sku=row.supplier_sku,
            unit_price=row.unit_price,
            currency_code=row.currency_code,
            stock_status=row.stock_status,
            lead_time_days_min=row.lead_time_days_min,
            lead_time_days_max=row.lead_time_days_max,
            price_checked_at=now,
            external_provider=row.external_provider,
            buy_url=row.buy_url,
        )
        repo.save_supplier_offer(offer)

        item_sha256 = hashlib.sha256(
            f"{row.product_id}:{variant_id}:{offer.supplier_offer_id}".encode()
        ).hexdigest()
        repo.add_catalogue_snapshot_item(
            snapshot_item_id=new_id("csi"),
            catalogue_snapshot_id=snapshot_id,
            product_id=row.product_id,
            material_id=None,
            product_variant_id=variant_id,
            material_variant_id=None,
            item_sha256=item_sha256,
        )

    return snapshot

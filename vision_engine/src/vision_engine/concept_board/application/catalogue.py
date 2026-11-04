from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from vision_engine.concept_board.application.catalogue_import import import_catalogue_rows
from vision_engine.concept_board.domain.enums import CatalogueSnapshotStatus
from vision_engine.concept_board.domain.errors import CatalogueError
from vision_engine.concept_board.domain.models import CatalogueImportRow, CatalogueSnapshotRecord
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.sqlite_repository import utcnow


def _parse_region_types(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split("|") if part.strip()]


def load_catalogue_csv(path: Path) -> list[CatalogueImportRow]:
    if not path.exists():
        raise CatalogueError(f"Catalogue CSV not found: {path}")
    rows: list[CatalogueImportRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line in reader:
            rows.append(
                CatalogueImportRow(
                    product_id=line["product_id"].strip(),
                    canonical_name=line["canonical_name"].strip(),
                    brand_name=(line.get("brand_name") or "").strip() or None,
                    product_type=line["product_type"].strip(),
                    description=(line.get("description") or "").strip() or None,
                    variant_sku=line["variant_sku"].strip(),
                    colour=(line.get("colour") or "").strip() or None,
                    finish=(line.get("finish") or "").strip() or None,
                    material=(line.get("material") or "").strip() or None,
                    width_mm=_float_or_none(line.get("width_mm")),
                    height_mm=_float_or_none(line.get("height_mm")),
                    depth_mm=_float_or_none(line.get("depth_mm")),
                    supplier_name=line["supplier_name"].strip(),
                    supplier_sku=line["supplier_sku"].strip(),
                    unit_price=float(line["unit_price"]),
                    currency_code=(line.get("currency_code") or "GBP").strip(),
                    stock_status=(line.get("stock_status") or "in_stock").strip(),
                    lead_time_days_min=_int_or_none(line.get("lead_time_days_min")),
                    lead_time_days_max=_int_or_none(line.get("lead_time_days_max")),
                    region_types=_parse_region_types(line.get("region_types")),
                )
            )
    if not rows:
        raise CatalogueError("Catalogue CSV is empty")
    return rows


def _float_or_none(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _int_or_none(value: str | None) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(value)


def import_catalogue_csv(
    *,
    repo: ConceptBoardRepositoryMixin,
    csv_path: Path,
    snapshot_name: str = "local-v1",
    seal: bool = True,
) -> CatalogueSnapshotRecord:
    import_rows = load_catalogue_csv(csv_path)
    return import_catalogue_rows(
        repo=repo,
        import_rows=import_rows,
        snapshot_name=snapshot_name,
        manifest_source=str(csv_path),
        seal=seal,
    )


def seal_catalogue_snapshot(
    *,
    repo: ConceptBoardRepositoryMixin,
    snapshot_name: str,
) -> CatalogueSnapshotRecord:
    snapshot = repo.get_catalogue_snapshot_by_name(snapshot_name)
    if snapshot is None:
        raise CatalogueError(f"Snapshot not found: {snapshot_name}")
    if snapshot.status == CatalogueSnapshotStatus.SEALED:
        return snapshot
    now = utcnow()
    sealed = snapshot.model_copy(
        update={"status": CatalogueSnapshotStatus.SEALED, "sealed_at": now}
    )
    repo.save_catalogue_snapshot(sealed)
    return sealed

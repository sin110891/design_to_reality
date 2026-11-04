from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from vision_engine.concept_board.domain.enums import IntegrationExportStatus, IntegrationExportType
from vision_engine.concept_board.domain.errors import ProcurementError
from vision_engine.concept_board.domain.models import IntegrationExportRecord
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import utcnow
from vision_engine.settings import AppSettings


def export_procurement_csv(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings,
    procurement_schedule_id: str,
) -> IntegrationExportRecord:
    schedule = repo.get_procurement_schedule(procurement_schedule_id)
    if schedule is None:
        raise ProcurementError(f"Schedule not found: {procurement_schedule_id}")

    items = repo.list_procurement_items(procurement_schedule_id)
    export_dir = settings.resolve(settings.paths.exports) / "procurement"
    export_dir.mkdir(parents=True, exist_ok=True)
    csv_path = export_dir / f"{procurement_schedule_id}.csv"

    rows: list[dict] = []
    for item in items:
        selection = repo.get_region_selection(item.region_selection_id)
        region = (
            repo.get_design_region(selection.design_region_id) if selection else None
        )
        rows.append(
            {
                "procurement_item_id": item.procurement_item_id,
                "region_code": region.region_code if region else "",
                "item_name": item.item_name,
                "quantity": item.required_quantity,
                "unit_of_measure": item.unit_of_measure,
                "unit_price_snapshot": item.unit_price_snapshot,
                "estimated_total": item.estimated_total,
                "currency_code": schedule.currency_code,
                "substitution_policy": item.substitution_policy.value,
            }
        )

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        if rows:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    manifest = {
        "export_schema_version": "procurement-scope.v1",
        "procurement_schedule_id": procurement_schedule_id,
        "catalogue_snapshot_id": schedule.catalogue_snapshot_id,
        "items": rows,
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    json_path = export_dir / f"{procurement_schedule_id}.json"
    json_path.write_bytes(manifest_bytes)

    now = utcnow()
    export = IntegrationExportRecord(
        export_id=new_id("exp"),
        project_id=schedule.project_id,
        procurement_schedule_id=procurement_schedule_id,
        catalogue_snapshot_id=schedule.catalogue_snapshot_id,
        export_type=IntegrationExportType.PROCUREMENT_CSV,
        manifest_uri=str(json_path.relative_to(settings.project_root)),
        manifest_sha256=manifest_sha256,
        status=IntegrationExportStatus.COMPLETED,
        created_at=now,
        delivered_at=now,
    )
    repo.save_integration_export(export)
    return export

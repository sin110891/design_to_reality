from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from vision_engine.virtual_staging.domain.enums import (
    EvidenceGrade,
    ImageEditRunStatus,
    StagingConditionType,
    StagingMode,
    StagingRequestStatus,
    VirtualStagingOutputType,
)
from vision_engine.virtual_staging.domain.models import (
    ImageEditRunRecord,
    StagingConditionRecord,
    StagingRequestRecord,
    VirtualStagingOutputRecord,
)
from vision_engine.virtual_staging.infrastructure.schema import (
    ImageEditRunRow,
    StagingConditionRow,
    StagingRequestRow,
    VirtualStagingOutputRow,
)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


class VirtualStagingRepositoryMixin:
    def save_staging_request(self, record: StagingRequestRecord) -> None:
        with self.session() as session:
            session.merge(
                StagingRequestRow(
                    staging_request_id=record.staging_request_id,
                    concept_version_id=record.concept_version_id,
                    design_region_id=record.design_region_id,
                    region_candidate_id=record.region_candidate_id,
                    staging_mode=record.staging_mode.value,
                    requested_quality_level=record.requested_quality_level,
                    status=record.status.value,
                    disclaimer=record.disclaimer,
                    created_at=record.created_at,
                )
            )

    def get_staging_request(self, staging_request_id: str) -> StagingRequestRecord | None:
        with self.session() as session:
            row = session.get(StagingRequestRow, staging_request_id)
            return self._to_staging_request(row) if row else None

    def save_staging_condition(self, record: StagingConditionRecord) -> None:
        with self.session() as session:
            session.merge(
                StagingConditionRow(
                    staging_condition_id=record.staging_condition_id,
                    staging_request_id=record.staging_request_id,
                    condition_type=record.condition_type.value,
                    artifact_reference_json=_json_dumps(record.artifact_reference_json),
                    content_sha256=record.content_sha256,
                    created_at=record.created_at,
                )
            )

    def save_image_edit_run(self, record: ImageEditRunRecord) -> None:
        with self.session() as session:
            session.merge(
                ImageEditRunRow(
                    image_edit_run_id=record.image_edit_run_id,
                    staging_request_id=record.staging_request_id,
                    provider=record.provider,
                    model_name=record.model_name,
                    model_version=record.model_version,
                    prompt_version=record.prompt_version,
                    request_manifest_sha256=record.request_manifest_sha256,
                    status=record.status.value,
                    latency_ms=record.latency_ms,
                    created_at=record.created_at,
                )
            )

    def save_virtual_staging_output(self, record: VirtualStagingOutputRecord) -> None:
        with self.session() as session:
            session.merge(
                VirtualStagingOutputRow(
                    virtual_staging_output_id=record.virtual_staging_output_id,
                    staging_request_id=record.staging_request_id,
                    image_edit_run_id=record.image_edit_run_id,
                    output_type=record.output_type.value,
                    storage_uri=record.storage_uri,
                    output_sha256=record.output_sha256,
                    provenance_manifest_uri=record.provenance_manifest_uri,
                    provenance_manifest_sha256=record.provenance_manifest_sha256,
                    evidence_grade=record.evidence_grade.value,
                    status=record.status,
                    created_at=record.created_at,
                )
            )

    def get_virtual_staging_output(
        self, virtual_staging_output_id: str
    ) -> VirtualStagingOutputRecord | None:
        with self.session() as session:
            row = session.get(VirtualStagingOutputRow, virtual_staging_output_id)
            return self._to_virtual_staging_output(row) if row else None

    def list_staging_conditions(self, staging_request_id: str) -> list[StagingConditionRecord]:
        with self.session() as session:
            rows = session.scalars(
                select(StagingConditionRow).where(
                    StagingConditionRow.staging_request_id == staging_request_id
                )
            ).all()
            return [self._to_staging_condition(r) for r in rows]

    @staticmethod
    def _to_staging_request(row: StagingRequestRow) -> StagingRequestRecord:
        return StagingRequestRecord(
            staging_request_id=row.staging_request_id,
            concept_version_id=row.concept_version_id,
            design_region_id=row.design_region_id,
            region_candidate_id=row.region_candidate_id,
            staging_mode=StagingMode(row.staging_mode),
            requested_quality_level=row.requested_quality_level,
            status=StagingRequestStatus(row.status),
            disclaimer=row.disclaimer,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_staging_condition(row: StagingConditionRow) -> StagingConditionRecord:
        return StagingConditionRecord(
            staging_condition_id=row.staging_condition_id,
            staging_request_id=row.staging_request_id,
            condition_type=StagingConditionType(row.condition_type),
            artifact_reference_json=json.loads(row.artifact_reference_json or "{}"),
            content_sha256=row.content_sha256,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_virtual_staging_output(row: VirtualStagingOutputRow) -> VirtualStagingOutputRecord:
        return VirtualStagingOutputRecord(
            virtual_staging_output_id=row.virtual_staging_output_id,
            staging_request_id=row.staging_request_id,
            image_edit_run_id=row.image_edit_run_id,
            output_type=VirtualStagingOutputType(row.output_type),
            storage_uri=row.storage_uri,
            output_sha256=row.output_sha256,
            provenance_manifest_uri=row.provenance_manifest_uri,
            provenance_manifest_sha256=row.provenance_manifest_sha256,
            evidence_grade=EvidenceGrade(row.evidence_grade),
            status=row.status,
            created_at=row.created_at,
        )

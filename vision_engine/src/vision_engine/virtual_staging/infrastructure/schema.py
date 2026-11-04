from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vision_engine.infrastructure.database_base import Base, utcnow


class StagingRequestRow(Base):
    __tablename__ = "staging_requests"

    staging_request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_version_id: Mapped[str] = mapped_column(
        ForeignKey("concept_versions.concept_version_id"), index=True, nullable=False
    )
    design_region_id: Mapped[str] = mapped_column(
        ForeignKey("design_regions.design_region_id"), index=True, nullable=False
    )
    region_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("region_candidates.region_candidate_id"), index=True, nullable=False
    )
    staging_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_quality_level: Mapped[str] = mapped_column(String(64), default="mvp")
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StagingConditionRow(Base):
    __tablename__ = "staging_conditions"

    staging_condition_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    staging_request_id: Mapped[str] = mapped_column(
        ForeignKey("staging_requests.staging_request_id"), index=True, nullable=False
    )
    condition_type: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_reference_json: Mapped[str] = mapped_column(Text, default="{}")
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ImageEditRunRow(Base):
    __tablename__ = "image_edit_runs"

    image_edit_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    staging_request_id: Mapped[str] = mapped_column(
        ForeignKey("staging_requests.staging_request_id"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), default="")
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    request_manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VirtualStagingOutputRow(Base):
    __tablename__ = "virtual_staging_outputs"

    virtual_staging_output_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    staging_request_id: Mapped[str] = mapped_column(
        ForeignKey("staging_requests.staging_request_id"), index=True, nullable=False
    )
    image_edit_run_id: Mapped[str] = mapped_column(
        ForeignKey("image_edit_runs.image_edit_run_id"), index=True, nullable=False
    )
    output_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    output_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provenance_manifest_uri: Mapped[str] = mapped_column(Text, nullable=False)
    provenance_manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

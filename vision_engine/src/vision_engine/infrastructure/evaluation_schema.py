from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vision_engine.infrastructure.database_base import Base, utcnow


class EvaluationRunRow(Base):
    __tablename__ = "evaluation_runs"

    evaluation_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    spec_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    spec_json: Mapped[str] = mapped_column(Text, nullable=False)
    requested_repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvaluationCaseRow(Base):
    __tablename__ = "evaluation_cases"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "case_input_sha256",
            "replicate_index",
            name="uq_evaluation_case_replicate",
        ),
    )

    evaluation_case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evaluation_run_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.evaluation_run_id"), index=True
    )
    case_input_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    replicate_index: Mapped[int] = mapped_column(Integer, nullable=False)
    public_case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    input_spec_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvaluationCaseArmRow(Base):
    __tablename__ = "evaluation_case_arms"
    __table_args__ = (
        UniqueConstraint("evaluation_case_id", "arm", name="uq_evaluation_case_arm"),
    )

    evaluation_case_arm_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evaluation_case_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_cases.evaluation_case_id"), index=True
    )
    arm: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.project_id"), index=True
    )
    generation_run_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EvaluationExportRow(Base):
    __tablename__ = "evaluation_exports"

    evaluation_export_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evaluation_run_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.evaluation_run_id"), index=True
    )
    export_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_directory: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BlindExportCandidateRow(Base):
    __tablename__ = "blind_export_candidates"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_export_id",
            "evaluation_case_id",
            "display_order",
            name="uq_blind_candidate_order",
        ),
    )

    blind_candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evaluation_export_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_exports.evaluation_export_id"), index=True
    )
    evaluation_case_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_cases.evaluation_case_id"), index=True
    )
    public_case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    variant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    arm: Mapped[str] = mapped_column(String(64), nullable=False)
    image_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)


class EvaluationSelectionRow(Base):
    __tablename__ = "evaluation_selections"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_export_id",
            "evaluation_case_id",
            "evaluator_id",
            name="uq_evaluation_selection",
        ),
    )

    selection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evaluation_export_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_exports.evaluation_export_id"), index=True
    )
    evaluation_case_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_cases.evaluation_case_id"), index=True
    )
    public_case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    winner_candidate_id: Mapped[str | None] = mapped_column(String(64))
    winner_arm: Mapped[str | None] = mapped_column(String(64))
    selection_method: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

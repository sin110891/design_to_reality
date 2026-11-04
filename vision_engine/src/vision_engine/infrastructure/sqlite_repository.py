from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    select,
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from vision_engine.domain.enums import (
    ApprovedConceptExportStatus,
    BenchmarkArm,
    BuildabilityAssessment,
    FailureTag,
    GenerationMode,
    GenerationReviewSetStatus,
    LabelPolarity,
    ProjectStatus,
    RetentionConsentStatus,
    ReviewDecision,
    ReviewStatus,
    RightsStatus,
    VariantKind,
    VariantReviewStatus,
)
from vision_engine.domain.models import (
    ApprovedConceptManifest,
    BenchmarkCase,
    BenchmarkCaseProject,
    ConceptRunRecord,
    DatasetRecord,
    DesignDirection,
    FeedbackEvent,
    GeneratedImageAsset,
    GeneratedVariant,
    GenerationReviewSet,
    GenerationRunRecord,
    ProjectRecord,
    RetrievalRunRecord,
    ReviewLabel,
    UploadRecord,
    VariantReview,
)
from vision_engine.infrastructure.database_base import Base, utcnow


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


DEFAULT_REVIEW_LABELS: list[tuple[str, str, str, LabelPolarity]] = [
    ("geometry_failure", "failure", "Geometry changed from input room", LabelPolarity.NEGATIVE),
    ("window_changed", "failure", "Window opening changed", LabelPolarity.NEGATIVE),
    ("door_changed", "failure", "Door opening changed", LabelPolarity.NEGATIVE),
    ("fireplace_changed", "failure", "Fireplace changed", LabelPolarity.NEGATIVE),
    ("lighting_problem", "failure", "Lighting strategy problem", LabelPolarity.NEGATIVE),
    ("material_conflict", "failure", "Material palette conflict", LabelPolarity.NEGATIVE),
    ("generic_ai_artifact", "failure", "Generic AI artifact", LabelPolarity.NEGATIVE),
    ("reference_mismatch", "failure", "Reference mismatch", LabelPolarity.NEGATIVE),
    ("good_material_coherence", "strength", "Good material coherence", LabelPolarity.POSITIVE),
    ("good_lighting_strategy", "strength", "Good lighting strategy", LabelPolarity.POSITIVE),
    ("good_geometry_preservation", "strength", "Good geometry preservation", LabelPolarity.POSITIVE),
    ("clear_focal_point", "strength", "Clear focal point", LabelPolarity.POSITIVE),
]


class ProjectRow(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    room_image_path: Mapped[str] = mapped_column(Text, nullable=False)
    inspiration_paths_json: Mapped[str] = mapped_column(Text, default="[]")
    room_type: Mapped[str] = mapped_column(String(64), nullable=False)
    style_family: Mapped[str] = mapped_column(String(128), nullable=False)
    brief: Mapped[str] = mapped_column(Text, nullable=False)
    budget_band: Mapped[str | None] = mapped_column(String(64))
    constraints_json: Mapped[str] = mapped_column(Text, default="[]")
    project_type: Mapped[str] = mapped_column(String(64), default="residential")
    status: Mapped[str] = mapped_column(String(64), default=ProjectStatus.CREATED.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UploadRow(Base):
    __tablename__ = "uploads"

    upload_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str | None] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    rights_status: Mapped[str] = mapped_column(String(64), default=RightsStatus.USER_OWNED.value)
    retention_consent_status: Mapped[str] = mapped_column(
        String(64), default=RetentionConsentStatus.PENDING.value
    )
    consented_by: Mapped[str | None] = mapped_column(String(128))
    consent_version: Mapped[str | None] = mapped_column(String(64))
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_source: Mapped[str | None] = mapped_column(String(128))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DatasetRecordRow(Base):
    __tablename__ = "dataset_records"

    image_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(64), index=True)
    style_family: Mapped[str | None] = mapped_column(String(128))
    room_type: Mapped[str | None] = mapped_column(String(64))
    architect_quality_score: Mapped[float] = mapped_column(Float, default=3.5)


class RetrievalRunRow(Base):
    __tablename__ = "retrieval_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    retrieval_experiment_id: Mapped[str | None] = mapped_column(String(64))
    vector_index_version_id: Mapped[str | None] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=8)
    final_k: Mapped[int] = mapped_column(Integer, default=3)
    reference_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    scores_json: Mapped[str] = mapped_column(Text, default="[]")
    dataset_version: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RetrievalRunReferenceRow(Base):
    __tablename__ = "retrieval_run_references"

    retrieval_run_reference_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    retrieval_run_id: Mapped[str] = mapped_column(
        ForeignKey("retrieval_runs.run_id"), index=True
    )
    retrieval_candidate_id: Mapped[str | None] = mapped_column(String(64))
    dataset_record_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_records.image_id"), index=True
    )
    retrieval_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    diversity_role: Mapped[str | None] = mapped_column(String(64))


class ConceptRunRow(Base):
    __tablename__ = "concept_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    retrieval_run_id: Mapped[str | None] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    design_direction_json: Mapped[str | None] = mapped_column(Text)
    raw_response_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GenerationRunRow(Base):
    __tablename__ = "generation_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    concept_run_id: Mapped[str | None] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GeneratedVariantRow(Base):
    __tablename__ = "generated_variants"

    variant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    generation_run_id: Mapped[str] = mapped_column(
        ForeignKey("generation_runs.run_id"), index=True
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    image_path: Mapped[str] = mapped_column(Text, nullable=False)
    rank_hint: Mapped[int] = mapped_column(Integer, default=1)
    review_status: Mapped[str] = mapped_column(
        String(64), default=VariantReviewStatus.UNREVIEWED.value, index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    image_asset_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GeneratedImageAssetRow(Base):
    __tablename__ = "generated_image_assets"

    asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    variant_id: Mapped[str] = mapped_column(
        ForeignKey("generated_variants.variant_id"), unique=True, nullable=False, index=True
    )
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    image_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    rights_status: Mapped[str] = mapped_column(String(64), default=RightsStatus.USER_OWNED.value)
    retention_consent_status: Mapped[str] = mapped_column(
        String(64), default=RetentionConsentStatus.PENDING.value
    )
    consented_by: Mapped[str | None] = mapped_column(String(128))
    consent_version: Mapped[str | None] = mapped_column(String(64))
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_source: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GenerationReviewSetRow(Base):
    __tablename__ = "generation_review_sets"
    __table_args__ = (
        UniqueConstraint(
            "generation_run_id",
            "reviewer",
            "revision_number",
            name="uq_review_set_revision",
        ),
    )

    review_set_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    generation_run_id: Mapped[str] = mapped_column(
        ForeignKey("generation_runs.run_id"), index=True
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    winner_variant_id: Mapped[str | None] = mapped_column(String(64))
    overall_notes: Mapped[str | None] = mapped_column(Text)
    revision_number: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VariantReviewRow(Base):
    __tablename__ = "variant_reviews"
    __table_args__ = (
        UniqueConstraint("review_set_id", "variant_id", name="uq_variant_review"),
    )

    variant_review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    review_set_id: Mapped[str] = mapped_column(
        ForeignKey("generation_review_sets.review_set_id"), index=True
    )
    variant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rank_in_set: Mapped[int | None] = mapped_column(Integer)
    reference_relevance_score: Mapped[int | None] = mapped_column(Integer)
    taste_quality_score: Mapped[int | None] = mapped_column(Integer)
    geometry_preservation_score: Mapped[int | None] = mapped_column(Integer)
    material_coherence_score: Mapped[int | None] = mapped_column(Integer)
    buildability_assessment: Mapped[str] = mapped_column(String(64), nullable=False)
    buildability_score: Mapped[int | None] = mapped_column(Integer)
    positive_notes: Mapped[str | None] = mapped_column(Text)
    negative_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewLabelRow(Base):
    __tablename__ = "review_labels"

    label_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    label_group: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    default_polarity: Mapped[str] = mapped_column(String(16), nullable=False)


class VariantReviewLabelRow(Base):
    __tablename__ = "variant_review_labels"

    variant_review_id: Mapped[str] = mapped_column(
        ForeignKey("variant_reviews.variant_review_id"), primary_key=True
    )
    label_code: Mapped[str] = mapped_column(
        ForeignKey("review_labels.label_code"), primary_key=True
    )
    polarity: Mapped[str] = mapped_column(String(16), nullable=False)


class ApprovedConceptManifestRow(Base):
    __tablename__ = "approved_concept_manifests"

    manifest_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    variant_review_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    variant_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    manifest_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    export_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    retention_consent_status: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawal_reason: Mapped[str | None] = mapped_column(Text)


class BenchmarkCaseRow(Base):
    __tablename__ = "benchmark_cases"

    benchmark_case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_input_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    canonical_brief: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BenchmarkCaseProjectRow(Base):
    __tablename__ = "benchmark_case_projects"

    benchmark_case_project_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    benchmark_case_id: Mapped[str] = mapped_column(
        ForeignKey("benchmark_cases.benchmark_case_id"), index=True
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    generation_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    arm: Mapped[str] = mapped_column(String(64), nullable=False)


class ReviewEventRow(Base):
    __tablename__ = "review_events"

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    variant_id: Mapped[str | None] = mapped_column(String(64))
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)
    reference_relevance_score: Mapped[int | None] = mapped_column(Integer)
    taste_quality_score: Mapped[int | None] = mapped_column(Integer)
    geometry_preservation_score: Mapped[int | None] = mapped_column(Integer)
    buildability_score: Mapped[int | None] = mapped_column(Integer)
    material_coherence_score: Mapped[int | None] = mapped_column(Integer)
    positive_notes: Mapped[str | None] = mapped_column(Text)
    negative_notes: Mapped[str | None] = mapped_column(Text)
    failure_tags_json: Mapped[str] = mapped_column(Text, default="[]")
    edited_concept_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PromptVersionRow(Base):
    __tablename__ = "prompt_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelVersionRow(Base):
    __tablename__ = "model_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


from vision_engine.infrastructure import evaluation_schema  # noqa: F401
from vision_engine.infrastructure import retrieval_schema  # noqa: F401
from vision_engine.concept_board.infrastructure import schema as concept_board_schema  # noqa: F401
from vision_engine.virtual_staging.infrastructure import schema as virtual_staging_schema  # noqa: F401
from vision_engine.infrastructure.evaluation_repository import EvaluationRepositoryMixin
from vision_engine.infrastructure.retrieval_repository import RetrievalRepositoryMixin
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.virtual_staging.infrastructure.repository import VirtualStagingRepositoryMixin


class SqliteRepository(
    EvaluationRepositoryMixin,
    RetrievalRepositoryMixin,
    ConceptBoardRepositoryMixin,
    VirtualStagingRepositoryMixin,
):
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.database_path}",
            future=True,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self._session_factory = sessionmaker(
            bind=self.engine, expire_on_commit=False, future=True
        )

    def init_db(self) -> None:
        Base.metadata.create_all(self.engine)
        self._migrate_schema()
        self.seed_review_labels()

    def _migrate_schema(self) -> None:
        migrations: list[tuple[str, str, str]] = [
            ("uploads", "rights_status", "rights_status TEXT DEFAULT 'user_owned'"),
            ("uploads", "retention_consent_status", "retention_consent_status TEXT DEFAULT 'pending'"),
            ("uploads", "consented_by", "consented_by TEXT"),
            ("uploads", "consent_version", "consent_version TEXT"),
            ("uploads", "consented_at", "consented_at DATETIME"),
            ("uploads", "consent_source", "consent_source TEXT"),
            ("uploads", "withdrawn_at", "withdrawn_at DATETIME"),
            (
                "generated_variants",
                "review_status",
                "review_status TEXT DEFAULT 'unreviewed'",
            ),
            ("generated_variants", "reviewed_at", "reviewed_at DATETIME"),
            ("generated_variants", "image_asset_id", "image_asset_id TEXT"),
            ("retrieval_runs", "retrieval_experiment_id", "retrieval_experiment_id TEXT"),
            ("retrieval_runs", "vector_index_version_id", "vector_index_version_id TEXT"),
            (
                "retrieval_run_references",
                "retrieval_candidate_id",
                "retrieval_candidate_id TEXT",
            ),
            (
                "substitution_previews",
                "virtual_staging_output_id",
                "virtual_staging_output_id TEXT",
            ),
            (
                "substitution_previews",
                "evidence_grade",
                "evidence_grade TEXT",
            ),
            (
                "substitution_previews",
                "disclaimer",
                "disclaimer TEXT",
            ),
            ("cb_products", "external_provider", "external_provider TEXT"),
            ("cb_products", "external_product_id", "external_product_id TEXT"),
            ("cb_supplier_offers", "external_provider", "external_provider TEXT"),
            ("cb_supplier_offers", "buy_url", "buy_url TEXT"),
            (
                "region_selections",
                "selected_product_image_uri",
                "selected_product_image_uri TEXT",
            ),
        ]
        with self.engine.begin() as conn:
            for table, column, ddl in migrations:
                cols = {
                    row[1]
                    for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                }
                if column not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))

    def seed_review_labels(self) -> None:
        with self.session() as session:
            for code, group, description, polarity in DEFAULT_REVIEW_LABELS:
                existing = session.get(ReviewLabelRow, code)
                if existing is None:
                    session.add(
                        ReviewLabelRow(
                            label_code=code,
                            label_group=group,
                            description=description,
                            active=True,
                            default_polarity=polarity.value,
                        )
                    )

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # --- projects ---
    def save_project(self, project: ProjectRecord) -> None:
        with self.session() as session:
            row = session.get(ProjectRow, project.project_id)
            if row is None:
                row = ProjectRow(project_id=project.project_id)
                session.add(row)
            row.room_image_path = project.room_image_path
            row.inspiration_paths_json = json.dumps(project.inspiration_image_paths)
            row.room_type = project.room_type
            row.style_family = project.style_family
            row.brief = project.brief
            row.budget_band = project.budget_band
            row.constraints_json = json.dumps(project.constraints)
            row.project_type = project.project_type
            row.status = project.status.value
            row.created_at = project.created_at
            row.updated_at = project.updated_at

    def get_project(self, project_id: str) -> ProjectRecord | None:
        with self.session() as session:
            row = session.get(ProjectRow, project_id)
            return self._to_project(row) if row else None

    def list_projects(self) -> list[ProjectRecord]:
        with self.session() as session:
            rows = session.scalars(select(ProjectRow).order_by(ProjectRow.created_at.desc())).all()
            return [self._to_project(r) for r in rows]

    def delete_project(self, project_id: str) -> None:
        with self.session() as session:
            review_sets = session.scalars(
                select(GenerationReviewSetRow).where(
                    GenerationReviewSetRow.project_id == project_id
                )
            ).all()
            review_set_ids = [r.review_set_id for r in review_sets]
            if review_set_ids:
                variant_reviews = session.scalars(
                    select(VariantReviewRow).where(
                        VariantReviewRow.review_set_id.in_(review_set_ids)
                    )
                ).all()
                vr_ids = [v.variant_review_id for v in variant_reviews]
                if vr_ids:
                    for label in session.scalars(
                        select(VariantReviewLabelRow).where(
                            VariantReviewLabelRow.variant_review_id.in_(vr_ids)
                        )
                    ).all():
                        session.delete(label)
                    for manifest in session.scalars(
                        select(ApprovedConceptManifestRow).where(
                            ApprovedConceptManifestRow.variant_review_id.in_(vr_ids)
                        )
                    ).all():
                        session.delete(manifest)
                    for vr in variant_reviews:
                        session.delete(vr)
                for rs in review_sets:
                    session.delete(rs)

            variants = session.scalars(
                select(GeneratedVariantRow).where(
                    GeneratedVariantRow.project_id == project_id
                )
            ).all()
            variant_ids = [v.variant_id for v in variants]
            if variant_ids:
                for asset in session.scalars(
                    select(GeneratedImageAssetRow).where(
                        GeneratedImageAssetRow.variant_id.in_(variant_ids)
                    )
                ).all():
                    session.delete(asset)

            for model in (
                BenchmarkCaseProjectRow,
                ReviewEventRow,
                GeneratedVariantRow,
                GenerationRunRow,
                ConceptRunRow,
                RetrievalRunReferenceRow,
                RetrievalRunRow,
                UploadRow,
            ):
                if hasattr(model, "project_id"):
                    rows = session.scalars(
                        select(model).where(model.project_id == project_id)  # type: ignore[attr-defined]
                    ).all()
                    for row in rows:
                        session.delete(row)
            project = session.get(ProjectRow, project_id)
            if project:
                session.delete(project)

    def save_upload(self, upload: UploadRecord) -> None:
        with self.session() as session:
            session.merge(
                UploadRow(
                    upload_id=upload.upload_id,
                    project_id=upload.project_id,
                    role=upload.role,
                    relative_path=upload.relative_path,
                    sha256=upload.sha256,
                    mime_type=upload.mime_type,
                    width=upload.width,
                    height=upload.height,
                    rights_status=upload.rights_status.value,
                    retention_consent_status=upload.retention_consent_status.value,
                    consented_by=upload.consented_by,
                    consent_version=upload.consent_version,
                    consented_at=upload.consented_at,
                    consent_source=upload.consent_source,
                    withdrawn_at=upload.withdrawn_at,
                    created_at=upload.created_at,
                )
            )

    def upsert_dataset_records(self, records: list[DatasetRecord]) -> int:
        with self.session() as session:
            for record in records:
                session.merge(
                    DatasetRecordRow(
                        image_id=record.image_id,
                        image_path=record.image_path,
                        payload_json=record.model_dump_json(),
                        review_status=record.review_status.value,
                        style_family=record.style_family,
                        room_type=record.room_type,
                        architect_quality_score=record.architect_quality_score,
                    )
                )
        return len(records)

    def list_dataset_records(
        self, *, approved_only: bool = True
    ) -> list[DatasetRecord]:
        with self.session() as session:
            stmt = select(DatasetRecordRow)
            if approved_only:
                stmt = stmt.where(DatasetRecordRow.review_status == ReviewStatus.APPROVED.value)
            rows = session.scalars(stmt).all()
            return [DatasetRecord.model_validate_json(r.payload_json) for r in rows]

    def save_retrieval_run(
        self,
        run: RetrievalRunRecord,
        *,
        references: list[dict[str, Any]] | None = None,
    ) -> None:
        with self.session() as session:
            session.merge(
                RetrievalRunRow(
                    run_id=run.run_id,
                    project_id=run.project_id,
                    mode=run.mode.value,
                    query_text=run.query_text,
                    top_k=run.top_k,
                    final_k=run.final_k,
                    reference_ids_json=json.dumps(run.reference_ids),
                    scores_json=json.dumps(run.scores_json),
                    dataset_version=run.dataset_version,
                    created_at=run.created_at,
                )
            )
            if references:
                for idx, ref in enumerate(references, start=1):
                    session.merge(
                        RetrievalRunReferenceRow(
                            retrieval_run_reference_id=new_id("rrr"),
                            retrieval_run_id=run.run_id,
                            dataset_record_id=ref["image_id"],
                            retrieval_rank=idx,
                            final_score=float(ref.get("score", 0.0)),
                            diversity_role=ref.get("diversity_role"),
                        )
                    )

    def save_concept_run(self, run: ConceptRunRecord) -> None:
        with self.session() as session:
            session.merge(
                ConceptRunRow(
                    run_id=run.run_id,
                    project_id=run.project_id,
                    retrieval_run_id=run.retrieval_run_id,
                    mode=run.mode.value,
                    prompt_version=run.prompt_version,
                    provider=run.provider,
                    model_name=run.model_name,
                    design_direction_json=(
                        run.design_direction.model_dump_json() if run.design_direction else None
                    ),
                    raw_response_json=run.raw_response_json,
                    status=run.status,
                    error_message=run.error_message,
                    latency_ms=run.latency_ms,
                    created_at=run.created_at,
                )
            )

    def save_generation_run(self, run: GenerationRunRecord) -> None:
        with self.session() as session:
            session.merge(
                GenerationRunRow(
                    run_id=run.run_id,
                    project_id=run.project_id,
                    concept_run_id=run.concept_run_id,
                    mode=run.mode.value,
                    prompt_version=run.prompt_version,
                    provider=run.provider,
                    model_name=run.model_name,
                    reference_ids_json=json.dumps(run.reference_ids),
                    status=run.status,
                    error_message=run.error_message,
                    latency_ms=run.latency_ms,
                    created_at=run.created_at,
                )
            )

    def save_variant(self, variant: GeneratedVariant) -> None:
        with self.session() as session:
            session.merge(
                GeneratedVariantRow(
                    variant_id=variant.variant_id,
                    generation_run_id=variant.generation_run_id,
                    project_id=variant.project_id,
                    mode=variant.mode.value,
                    kind=variant.kind.value,
                    image_path=variant.image_path,
                    rank_hint=variant.rank_hint,
                    review_status=variant.review_status.value,
                    reviewed_at=variant.reviewed_at,
                    image_asset_id=variant.image_asset_id,
                    created_at=variant.created_at,
                )
            )

    def save_image_asset(self, asset: GeneratedImageAsset) -> None:
        with self.session() as session:
            session.merge(
                GeneratedImageAssetRow(
                    asset_id=asset.asset_id,
                    variant_id=asset.variant_id,
                    storage_path=asset.storage_path,
                    image_sha256=asset.image_sha256,
                    mime_type=asset.mime_type,
                    width=asset.width,
                    height=asset.height,
                    file_size_bytes=asset.file_size_bytes,
                    rights_status=asset.rights_status.value,
                    retention_consent_status=asset.retention_consent_status.value,
                    consented_by=asset.consented_by,
                    consent_version=asset.consent_version,
                    consented_at=asset.consented_at,
                    consent_source=asset.consent_source,
                    created_at=asset.created_at,
                    deleted_at=asset.deleted_at,
                )
            )

    def get_image_asset(self, variant_id: str) -> GeneratedImageAsset | None:
        with self.session() as session:
            row = session.scalars(
                select(GeneratedImageAssetRow).where(
                    GeneratedImageAssetRow.variant_id == variant_id
                )
            ).first()
            return self._to_image_asset(row) if row else None

    def update_image_asset_consent(
        self,
        variant_id: str,
        *,
        retention_consent_status: RetentionConsentStatus,
        consented_by: str,
        consent_version: str,
        consent_source: str = "architect_review_promote",
    ) -> None:
        with self.session() as session:
            row = session.scalars(
                select(GeneratedImageAssetRow).where(
                    GeneratedImageAssetRow.variant_id == variant_id
                )
            ).first()
            if row is None:
                raise ValueError(f"image asset not found for variant {variant_id}")
            row.retention_consent_status = retention_consent_status.value
            row.consented_by = consented_by
            row.consent_version = consent_version
            row.consent_source = consent_source
            row.consented_at = utcnow()

    def get_generation_run(self, generation_run_id: str) -> GenerationRunRecord | None:
        with self.session() as session:
            row = session.get(GenerationRunRow, generation_run_id)
            if not row:
                return None
            return GenerationRunRecord(
                run_id=row.run_id,
                project_id=row.project_id,
                concept_run_id=row.concept_run_id,
                mode=GenerationMode(row.mode),
                prompt_version=row.prompt_version,
                provider=row.provider,
                model_name=row.model_name,
                reference_ids=json.loads(row.reference_ids_json or "[]"),
                status=row.status,
                error_message=row.error_message,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
            )

    def list_variants_for_generation(self, generation_run_id: str) -> list[GeneratedVariant]:
        with self.session() as session:
            rows = session.scalars(
                select(GeneratedVariantRow)
                .where(GeneratedVariantRow.generation_run_id == generation_run_id)
                .order_by(GeneratedVariantRow.rank_hint)
            ).all()
            return [self._to_variant(r) for r in rows]

    def get_room_upload(self, project_id: str) -> UploadRecord | None:
        with self.session() as session:
            row = session.scalars(
                select(UploadRow).where(
                    UploadRow.project_id == project_id,
                    UploadRow.role == "room",
                )
            ).first()
            return self._to_upload(row) if row else None

    def get_concept_run(self, concept_run_id: str) -> ConceptRunRecord | None:
        with self.session() as session:
            row = session.get(ConceptRunRow, concept_run_id)
            if not row:
                return None
            direction = (
                DesignDirection.model_validate_json(row.design_direction_json)
                if row.design_direction_json
                else None
            )
            return ConceptRunRecord(
                run_id=row.run_id,
                project_id=row.project_id,
                retrieval_run_id=row.retrieval_run_id,
                mode=GenerationMode(row.mode),
                prompt_version=row.prompt_version,
                provider=row.provider,
                model_name=row.model_name,
                design_direction=direction,
                raw_response_json=row.raw_response_json,
                status=row.status,
                error_message=row.error_message,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
            )

    def list_review_labels(self, *, active_only: bool = True) -> list[ReviewLabel]:
        with self.session() as session:
            stmt = select(ReviewLabelRow)
            if active_only:
                stmt = stmt.where(ReviewLabelRow.active.is_(True))
            rows = session.scalars(stmt.order_by(ReviewLabelRow.label_group, ReviewLabelRow.label_code)).all()
            return [self._to_review_label(r) for r in rows]

    def get_latest_review_set(
        self,
        *,
        generation_run_id: str,
        reviewer: str,
    ) -> GenerationReviewSet | None:
        with self.session() as session:
            row = session.scalars(
                select(GenerationReviewSetRow)
                .where(
                    GenerationReviewSetRow.generation_run_id == generation_run_id,
                    GenerationReviewSetRow.reviewer == reviewer,
                )
                .order_by(GenerationReviewSetRow.revision_number.desc())
            ).first()
            return self._to_review_set(session, row) if row else None

    def delete_variant_reviews_for_review_set(self, review_set_id: str) -> None:
        with self.session() as session:
            variant_reviews = session.scalars(
                select(VariantReviewRow).where(VariantReviewRow.review_set_id == review_set_id)
            ).all()
            vr_ids = [vr.variant_review_id for vr in variant_reviews]
            if vr_ids:
                for label in session.scalars(
                    select(VariantReviewLabelRow).where(
                        VariantReviewLabelRow.variant_review_id.in_(vr_ids)
                    )
                ).all():
                    session.delete(label)
                for manifest in session.scalars(
                    select(ApprovedConceptManifestRow).where(
                        ApprovedConceptManifestRow.variant_review_id.in_(vr_ids)
                    )
                ).all():
                    session.delete(manifest)
                for vr in variant_reviews:
                    session.delete(vr)

    def save_generation_review_set(self, review_set: GenerationReviewSet) -> None:
        with self.session() as session:
            session.merge(
                GenerationReviewSetRow(
                    review_set_id=review_set.review_set_id,
                    generation_run_id=review_set.generation_run_id,
                    project_id=review_set.project_id,
                    reviewer=review_set.reviewer,
                    status=review_set.status.value,
                    winner_variant_id=review_set.winner_variant_id,
                    overall_notes=review_set.overall_notes,
                    revision_number=review_set.revision_number,
                    supersedes_id=review_set.supersedes_id,
                    created_at=review_set.created_at,
                    submitted_at=review_set.submitted_at,
                )
            )
            for vr in review_set.variant_reviews:
                session.merge(
                    VariantReviewRow(
                        variant_review_id=vr.variant_review_id,
                        review_set_id=review_set.review_set_id,
                        variant_id=vr.variant_id,
                        decision=vr.decision.value,
                        rank_in_set=vr.rank_in_set,
                        reference_relevance_score=vr.reference_relevance_score,
                        taste_quality_score=vr.taste_quality_score,
                        geometry_preservation_score=vr.geometry_preservation_score,
                        material_coherence_score=vr.material_coherence_score,
                        buildability_assessment=vr.buildability_assessment.value,
                        buildability_score=vr.buildability_score,
                        positive_notes=vr.positive_notes,
                        negative_notes=vr.negative_notes,
                        reviewed_at=vr.reviewed_at,
                    )
                )
                existing_labels = session.scalars(
                    select(VariantReviewLabelRow).where(
                        VariantReviewLabelRow.variant_review_id == vr.variant_review_id
                    )
                ).all()
                for label in existing_labels:
                    session.delete(label)
                label_rows = session.scalars(select(ReviewLabelRow)).all()
                label_polarity = {r.label_code: r.default_polarity for r in label_rows}
                for code in vr.labels:
                    session.add(
                        VariantReviewLabelRow(
                            variant_review_id=vr.variant_review_id,
                            label_code=code,
                            polarity=label_polarity.get(code, LabelPolarity.NEGATIVE.value),
                        )
                    )
                variant_row = session.get(GeneratedVariantRow, vr.variant_id)
                if variant_row:
                    if vr.decision == ReviewDecision.APPROVED:
                        variant_row.review_status = VariantReviewStatus.APPROVED.value
                    elif vr.decision == ReviewDecision.REJECTED:
                        variant_row.review_status = VariantReviewStatus.REJECTED.value
                    elif vr.decision == ReviewDecision.NEEDS_EDIT:
                        variant_row.review_status = VariantReviewStatus.NEEDS_EDIT.value
                    elif vr.decision == ReviewDecision.NOT_ASSESSABLE:
                        variant_row.review_status = VariantReviewStatus.IN_REVIEW.value
                    variant_row.reviewed_at = vr.reviewed_at

    def get_variant_review(self, variant_review_id: str) -> VariantReview | None:
        with self.session() as session:
            row = session.get(VariantReviewRow, variant_review_id)
            if not row:
                return None
            labels = [
                r.label_code
                for r in session.scalars(
                    select(VariantReviewLabelRow).where(
                        VariantReviewLabelRow.variant_review_id == variant_review_id
                    )
                ).all()
            ]
            return VariantReview(
                variant_review_id=row.variant_review_id,
                review_set_id=row.review_set_id,
                variant_id=row.variant_id,
                decision=ReviewDecision(row.decision),
                rank_in_set=row.rank_in_set,
                reference_relevance_score=row.reference_relevance_score,
                taste_quality_score=row.taste_quality_score,
                geometry_preservation_score=row.geometry_preservation_score,
                material_coherence_score=row.material_coherence_score,
                buildability_assessment=BuildabilityAssessment(row.buildability_assessment),
                buildability_score=row.buildability_score,
                positive_notes=row.positive_notes,
                negative_notes=row.negative_notes,
                labels=labels,
                reviewed_at=row.reviewed_at,
            )

    def get_review_set(self, review_set_id: str) -> GenerationReviewSet | None:
        with self.session() as session:
            row = session.get(GenerationReviewSetRow, review_set_id)
            return self._to_review_set(session, row) if row else None

    def save_approved_manifest(self, manifest: ApprovedConceptManifest) -> None:
        with self.session() as session:
            session.merge(
                ApprovedConceptManifestRow(
                    manifest_id=manifest.manifest_id,
                    variant_review_id=manifest.variant_review_id,
                    variant_id=manifest.variant_id,
                    manifest_sha256=manifest.manifest_sha256,
                    manifest_schema_version=manifest.manifest_schema_version,
                    export_status=manifest.export_status.value,
                    retention_consent_status=manifest.retention_consent_status.value,
                    manifest_json=json.dumps(manifest.manifest_json, ensure_ascii=False),
                    approved_at=manifest.approved_at,
                    exported_at=manifest.exported_at,
                    withdrawn_at=manifest.withdrawn_at,
                    withdrawal_reason=manifest.withdrawal_reason,
                )
            )

    def list_approved_manifests(
        self, *, include_withdrawn: bool = False
    ) -> list[ApprovedConceptManifest]:
        with self.session() as session:
            stmt = select(ApprovedConceptManifestRow)
            if not include_withdrawn:
                stmt = stmt.where(ApprovedConceptManifestRow.withdrawn_at.is_(None))
            rows = session.scalars(stmt.order_by(ApprovedConceptManifestRow.approved_at.desc())).all()
            return [self._to_manifest(r) for r in rows]

    def save_benchmark_case(self, case: BenchmarkCase) -> None:
        with self.session() as session:
            session.merge(
                BenchmarkCaseRow(
                    benchmark_case_id=case.benchmark_case_id,
                    canonical_input_sha256=case.canonical_input_sha256,
                    canonical_brief=case.canonical_brief,
                    status=case.status,
                    created_at=case.created_at,
                )
            )

    def save_benchmark_case_project(self, link: BenchmarkCaseProject) -> None:
        with self.session() as session:
            session.merge(
                BenchmarkCaseProjectRow(
                    benchmark_case_project_id=link.benchmark_case_project_id,
                    benchmark_case_id=link.benchmark_case_id,
                    project_id=link.project_id,
                    generation_run_id=link.generation_run_id,
                    arm=link.arm.value,
                )
            )

    def list_review_training_export(self) -> list[dict[str, Any]]:
        with self.session() as session:
            rows = session.execute(
                text(
                    """
                    SELECT
                        p.project_id,
                        gv.generation_run_id,
                        gv.mode AS generation_mode,
                        gv.variant_id,
                        gv.kind AS variant_kind,
                        u.relative_path AS room_image_path,
                        u.sha256 AS room_image_sha256,
                        gia.storage_path AS generated_image_path,
                        gia.image_sha256 AS generated_image_sha256,
                        p.brief,
                        p.constraints_json,
                        gen.reference_ids_json AS retrieved_reference_ids_json,
                        rr.scores_json AS retrieved_reference_scores_json,
                        cr.design_direction_json,
                        cr.prompt_version AS concept_prompt_version,
                        gen.prompt_version AS image_prompt_version,
                        gen.provider,
                        gen.model_name,
                        grs.reviewer,
                        grs.status AS review_set_status,
                        grs.winner_variant_id,
                        vr.decision AS variant_decision,
                        vr.rank_in_set,
                        vr.reference_relevance_score,
                        vr.taste_quality_score,
                        vr.geometry_preservation_score,
                        vr.material_coherence_score,
                        vr.buildability_assessment,
                        vr.buildability_score,
                        vr.positive_notes,
                        vr.negative_notes,
                        COALESCE(gia.retention_consent_status, u.retention_consent_status) AS retention_consent_status,
                        acm.manifest_id AS approved_manifest_id,
                        acm.manifest_sha256,
                        p.created_at,
                        vr.reviewed_at,
                        acm.approved_at
                    FROM variant_reviews vr
                    JOIN generation_review_sets grs ON grs.review_set_id = vr.review_set_id
                    JOIN generated_variants gv ON gv.variant_id = vr.variant_id
                    JOIN generation_runs gen ON gen.run_id = gv.generation_run_id
                    JOIN projects p ON p.project_id = gv.project_id
                    LEFT JOIN uploads u ON u.project_id = p.project_id AND u.role = 'room'
                    LEFT JOIN generated_image_assets gia ON gia.variant_id = gv.variant_id
                    LEFT JOIN concept_runs cr ON cr.run_id = gen.concept_run_id
                    LEFT JOIN retrieval_runs rr ON rr.run_id = cr.retrieval_run_id
                    LEFT JOIN approved_concept_manifests acm ON acm.variant_review_id = vr.variant_review_id
                    ORDER BY vr.reviewed_at DESC
                    """
                )
            ).mappings().all()
            export_rows: list[dict[str, Any]] = []
            for row in rows:
                payload = dict(row)
                vr_id = session.scalars(
                    select(VariantReviewRow.variant_review_id).where(
                        VariantReviewRow.variant_id == payload["variant_id"],
                        VariantReviewRow.review_set_id.in_(
                            select(GenerationReviewSetRow.review_set_id).where(
                                GenerationReviewSetRow.generation_run_id
                                == payload["generation_run_id"]
                            )
                        ),
                    )
                ).first()
                labels = []
                if vr_id:
                    labels = session.scalars(
                        select(VariantReviewLabelRow).where(
                            VariantReviewLabelRow.variant_review_id == vr_id
                        )
                    ).all()
                positive_labels = [l.label_code for l in labels if l.polarity == "positive"]
                negative_labels = [l.label_code for l in labels if l.polarity == "negative"]
                payload["all_scores_json"] = json.dumps(
                    {
                        "reference_relevance": payload.pop("reference_relevance_score", None),
                        "taste_quality": payload.pop("taste_quality_score", None),
                        "geometry_preservation": payload.pop("geometry_preservation_score", None),
                        "material_coherence": payload.pop("material_coherence_score", None),
                        "buildability_score": payload.pop("buildability_score", None),
                    }
                )
                payload["positive_labels_json"] = json.dumps(positive_labels)
                payload["negative_labels_json"] = json.dumps(negative_labels)
                export_rows.append(payload)
            return export_rows

    def list_variants(self, project_id: str) -> list[GeneratedVariant]:
        with self.session() as session:
            rows = session.scalars(
                select(GeneratedVariantRow)
                .where(GeneratedVariantRow.project_id == project_id)
                .order_by(GeneratedVariantRow.rank_hint)
            ).all()
            return [self._to_variant(r) for r in rows]

    def save_feedback(self, event: FeedbackEvent) -> None:
        with self.session() as session:
            session.merge(
                ReviewEventRow(
                    feedback_id=event.feedback_id,
                    project_id=event.project_id,
                    variant_id=event.variant_id,
                    reviewer=event.reviewer,
                    decision=event.decision.value,
                    rank=event.rank,
                    reference_relevance_score=event.reference_relevance_score,
                    taste_quality_score=event.taste_quality_score,
                    geometry_preservation_score=event.geometry_preservation_score,
                    buildability_score=event.buildability_score,
                    material_coherence_score=event.material_coherence_score,
                    positive_notes=event.positive_notes,
                    negative_notes=event.negative_notes,
                    failure_tags_json=json.dumps([t.value for t in event.failure_tags]),
                    edited_concept_json=(
                        json.dumps(event.edited_concept_json)
                        if event.edited_concept_json is not None
                        else None
                    ),
                    created_at=event.created_at,
                )
            )

    def list_feedback(self, project_id: str | None = None) -> list[FeedbackEvent]:
        with self.session() as session:
            stmt = select(ReviewEventRow).order_by(ReviewEventRow.created_at.desc())
            if project_id:
                stmt = stmt.where(ReviewEventRow.project_id == project_id)
            rows = session.scalars(stmt).all()
            return [self._to_feedback(r) for r in rows]

    def counts(self) -> dict[str, int]:
        with self.session() as session:
            return {
                "projects": len(session.scalars(select(ProjectRow)).all()),
                "dataset_records": len(session.scalars(select(DatasetRecordRow)).all()),
                "retrieval_runs": len(session.scalars(select(RetrievalRunRow)).all()),
                "concept_runs": len(session.scalars(select(ConceptRunRow)).all()),
                "generation_runs": len(session.scalars(select(GenerationRunRow)).all()),
                "variants": len(session.scalars(select(GeneratedVariantRow)).all()),
                "feedback": len(session.scalars(select(ReviewEventRow)).all()),
                "review_sets": len(session.scalars(select(GenerationReviewSetRow)).all()),
                "variant_reviews": len(session.scalars(select(VariantReviewRow)).all()),
                "approved_manifests": len(session.scalars(select(ApprovedConceptManifestRow)).all()),
                "benchmark_cases": len(session.scalars(select(BenchmarkCaseRow)).all()),
                "dataset_snapshots": len(
                    session.scalars(select(retrieval_schema.CuratedDatasetSnapshotRow)).all()
                ),
                "vector_index_versions": len(
                    session.scalars(select(retrieval_schema.VectorIndexVersionRow)).all()
                ),
                "retrieval_candidates": len(
                    session.scalars(select(retrieval_schema.RetrievalCandidateRow)).all()
                ),
                "evaluation_runs": len(
                    session.scalars(select(evaluation_schema.EvaluationRunRow)).all()
                ),
                "evaluation_cases": len(
                    session.scalars(select(evaluation_schema.EvaluationCaseRow)).all()
                ),
                "evaluation_exports": len(
                    session.scalars(select(evaluation_schema.EvaluationExportRow)).all()
                ),
            }

    def ensure_prompt_version(self, name: str, content_hash: str) -> None:
        with self.session() as session:
            existing = session.scalars(
                select(PromptVersionRow).where(PromptVersionRow.name == name)
            ).first()
            if existing:
                existing.content_hash = content_hash
            else:
                session.add(
                    PromptVersionRow(
                        version_id=new_id("prompt"),
                        name=name,
                        content_hash=content_hash,
                    )
                )

    def ensure_model_version(self, provider: str, model_name: str, role: str) -> None:
        with self.session() as session:
            existing = session.scalars(
                select(ModelVersionRow).where(
                    ModelVersionRow.provider == provider,
                    ModelVersionRow.model_name == model_name,
                    ModelVersionRow.role == role,
                )
            ).first()
            if not existing:
                session.add(
                    ModelVersionRow(
                        version_id=new_id("model"),
                        provider=provider,
                        model_name=model_name,
                        role=role,
                    )
                )

    @staticmethod
    def _to_project(row: ProjectRow) -> ProjectRecord:
        return ProjectRecord(
            project_id=row.project_id,
            room_image_path=row.room_image_path,
            inspiration_image_paths=json.loads(row.inspiration_paths_json or "[]"),
            room_type=row.room_type,
            style_family=row.style_family,
            brief=row.brief,
            budget_band=row.budget_band,
            constraints=json.loads(row.constraints_json or "[]"),
            project_type=row.project_type,
            status=ProjectStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_variant(row: GeneratedVariantRow) -> GeneratedVariant:
        return GeneratedVariant(
            variant_id=row.variant_id,
            generation_run_id=row.generation_run_id,
            project_id=row.project_id,
            mode=GenerationMode(row.mode),
            kind=VariantKind(row.kind),
            image_path=row.image_path,
            rank_hint=row.rank_hint,
            review_status=VariantReviewStatus(getattr(row, "review_status", VariantReviewStatus.UNREVIEWED.value)),
            reviewed_at=getattr(row, "reviewed_at", None),
            image_asset_id=getattr(row, "image_asset_id", None),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_upload(row: UploadRow) -> UploadRecord:
        return UploadRecord(
            upload_id=row.upload_id,
            project_id=row.project_id,
            role=row.role,
            relative_path=row.relative_path,
            sha256=row.sha256,
            mime_type=row.mime_type,
            width=row.width,
            height=row.height,
            rights_status=RightsStatus(getattr(row, "rights_status", RightsStatus.USER_OWNED.value)),
            retention_consent_status=RetentionConsentStatus(
                getattr(row, "retention_consent_status", RetentionConsentStatus.PENDING.value)
            ),
            consented_by=getattr(row, "consented_by", None),
            consent_version=getattr(row, "consent_version", None),
            consented_at=getattr(row, "consented_at", None),
            consent_source=getattr(row, "consent_source", None),
            withdrawn_at=getattr(row, "withdrawn_at", None),
            created_at=row.created_at,
        )

    @staticmethod
    def _to_image_asset(row: GeneratedImageAssetRow) -> GeneratedImageAsset:
        return GeneratedImageAsset(
            asset_id=row.asset_id,
            variant_id=row.variant_id,
            storage_path=row.storage_path,
            image_sha256=row.image_sha256,
            mime_type=row.mime_type,
            width=row.width,
            height=row.height,
            file_size_bytes=row.file_size_bytes,
            rights_status=RightsStatus(row.rights_status),
            retention_consent_status=RetentionConsentStatus(row.retention_consent_status),
            consented_by=row.consented_by,
            consent_version=row.consent_version,
            consented_at=row.consented_at,
            consent_source=row.consent_source,
            created_at=row.created_at,
            deleted_at=row.deleted_at,
        )

    @staticmethod
    def _to_review_label(row: ReviewLabelRow) -> ReviewLabel:
        return ReviewLabel(
            label_code=row.label_code,
            label_group=row.label_group,
            description=row.description,
            active=row.active,
            default_polarity=LabelPolarity(row.default_polarity),
        )

    def _to_review_set(
        self, session: Session, row: GenerationReviewSetRow | None
    ) -> GenerationReviewSet | None:
        if row is None:
            return None
        variant_rows = session.scalars(
            select(VariantReviewRow).where(VariantReviewRow.review_set_id == row.review_set_id)
        ).all()
        variant_reviews: list[VariantReview] = []
        for vr in variant_rows:
            labels = [
                l.label_code
                for l in session.scalars(
                    select(VariantReviewLabelRow).where(
                        VariantReviewLabelRow.variant_review_id == vr.variant_review_id
                    )
                ).all()
            ]
            variant_reviews.append(
                VariantReview(
                    variant_review_id=vr.variant_review_id,
                    review_set_id=vr.review_set_id,
                    variant_id=vr.variant_id,
                    decision=ReviewDecision(vr.decision),
                    rank_in_set=vr.rank_in_set,
                    reference_relevance_score=vr.reference_relevance_score,
                    taste_quality_score=vr.taste_quality_score,
                    geometry_preservation_score=vr.geometry_preservation_score,
                    material_coherence_score=vr.material_coherence_score,
                    buildability_assessment=BuildabilityAssessment(vr.buildability_assessment),
                    buildability_score=vr.buildability_score,
                    positive_notes=vr.positive_notes,
                    negative_notes=vr.negative_notes,
                    labels=labels,
                    reviewed_at=vr.reviewed_at,
                )
            )
        return GenerationReviewSet(
            review_set_id=row.review_set_id,
            generation_run_id=row.generation_run_id,
            project_id=row.project_id,
            reviewer=row.reviewer,
            status=GenerationReviewSetStatus(row.status),
            winner_variant_id=row.winner_variant_id,
            overall_notes=row.overall_notes,
            revision_number=row.revision_number,
            supersedes_id=row.supersedes_id,
            created_at=row.created_at,
            submitted_at=row.submitted_at,
            variant_reviews=variant_reviews,
        )

    @staticmethod
    def _to_manifest(row: ApprovedConceptManifestRow) -> ApprovedConceptManifest:
        return ApprovedConceptManifest(
            manifest_id=row.manifest_id,
            variant_review_id=row.variant_review_id,
            variant_id=row.variant_id,
            manifest_sha256=row.manifest_sha256,
            manifest_schema_version=row.manifest_schema_version,
            export_status=ApprovedConceptExportStatus(row.export_status),
            retention_consent_status=RetentionConsentStatus(row.retention_consent_status),
            manifest_json=json.loads(row.manifest_json),
            approved_at=row.approved_at,
            exported_at=row.exported_at,
            withdrawn_at=row.withdrawn_at,
            withdrawal_reason=row.withdrawal_reason,
        )

    @staticmethod
    def _to_feedback(row: ReviewEventRow) -> FeedbackEvent:
        tags = [FailureTag(t) for t in json.loads(row.failure_tags_json or "[]")]
        edited = json.loads(row.edited_concept_json) if row.edited_concept_json else None
        return FeedbackEvent(
            feedback_id=row.feedback_id,
            project_id=row.project_id,
            variant_id=row.variant_id,
            reviewer=row.reviewer,
            decision=ReviewDecision(row.decision),
            rank=row.rank,
            reference_relevance_score=row.reference_relevance_score,
            taste_quality_score=row.taste_quality_score,
            geometry_preservation_score=row.geometry_preservation_score,
            buildability_score=row.buildability_score,
            material_coherence_score=row.material_coherence_score,
            positive_notes=row.positive_notes,
            negative_notes=row.negative_notes,
            failure_tags=tags,
            edited_concept_json=edited,
            created_at=row.created_at,
        )

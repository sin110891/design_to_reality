from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from design_dataset.domain.enums import LabelRunStatus, ReviewStatus, SourceType, UsageRightsStatus
from design_dataset.domain.models import (
    CurationRecord,
    DesignLabelDraft,
    ExpertReferenceMetadata,
    ImageRecord,
    LabelRunRecord,
    ReviewEvent,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ImageRow(Base):
    __tablename__ = "images"

    image_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    mime_type: Mapped[str | None] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(64), default=SourceType.LOCAL_FOLDER.value)
    source_url: Mapped[str | None] = mapped_column(Text)
    usage_rights_status: Mapped[str] = mapped_column(
        String(64), default=UsageRightsStatus.UNKNOWN.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LabelRunRow(Base):
    __tablename__ = "label_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("images.image_id"), nullable=False, index=True)
    rulebook_version: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_response_json: Mapped[str | None] = mapped_column(Text)
    parsed_response_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    error_type: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CurationRecordRow(Base):
    __tablename__ = "curation_records"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("label_runs.run_id"), nullable=False, unique=True)
    image_id: Mapped[str] = mapped_column(ForeignKey("images.image_id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    usage_rights_status: Mapped[str] = mapped_column(String(64), nullable=False)
    rulebook_version: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_request_id: Mapped[str | None] = mapped_column(String(128))
    draft_label_json: Mapped[str | None] = mapped_column(Text)
    final_label_json: Mapped[str | None] = mapped_column(Text)
    raw_response_json: Mapped[str | None] = mapped_column(Text)
    validation_errors_json: Mapped[str] = mapped_column(Text, default="[]")
    review_warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    review_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    curator_name: Mapped[str | None] = mapped_column(String(128))
    curator_notes: Mapped[str | None] = mapped_column(Text)
    expert_metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewEventRow(Base):
    __tablename__ = "review_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    record_id: Mapped[str] = mapped_column(
        ForeignKey("curation_records.record_id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SqliteRepository:
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
        with self.engine.begin() as conn:
            columns = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(curation_records)")).fetchall()
            }
            if "expert_metadata_json" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE curation_records "
                        "ADD COLUMN expert_metadata_json TEXT"
                    )
                )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_label_runs_success_fingerprint "
                    "ON label_runs(request_fingerprint) "
                    "WHERE status = 'succeeded'"
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

    def get_image_by_sha(self, sha256: str) -> ImageRecord | None:
        with self.session() as session:
            row = session.scalar(select(ImageRow).where(ImageRow.sha256 == sha256))
            return _to_image(row) if row else None

    def upsert_image(self, image: ImageRecord) -> tuple[ImageRecord, bool]:
        with self.session() as session:
            existing = session.scalar(select(ImageRow).where(ImageRow.sha256 == image.sha256))
            if existing:
                return _to_image(existing), False
            session.add(
                ImageRow(
                    image_id=image.image_id,
                    relative_path=image.relative_path,
                    sha256=image.sha256,
                    mime_type=image.mime_type,
                    width=image.width,
                    height=image.height,
                    source_type=image.source_type.value,
                    source_url=image.source_url,
                    usage_rights_status=image.usage_rights_status.value,
                    created_at=image.created_at,
                )
            )
            return image, True

    def list_images(self) -> list[ImageRecord]:
        with self.session() as session:
            rows = session.scalars(select(ImageRow).order_by(ImageRow.created_at)).all()
            return [_to_image(row) for row in rows]

    def find_successful_run(self, fingerprint: str) -> LabelRunRecord | None:
        with self.session() as session:
            row = session.scalar(
                select(LabelRunRow).where(
                    LabelRunRow.request_fingerprint == fingerprint,
                    LabelRunRow.status == LabelRunStatus.SUCCEEDED.value,
                )
            )
            return _to_label_run(row) if row else None

    def save_label_run(self, run: LabelRunRecord) -> LabelRunRecord:
        with self.session() as session:
            session.add(
                LabelRunRow(
                    run_id=run.run_id,
                    image_id=run.image_id,
                    rulebook_version=run.rulebook_version,
                    prompt_version=run.prompt_version,
                    provider=run.provider,
                    model_name=run.model_name,
                    request_fingerprint=run.request_fingerprint,
                    raw_response_json=run.raw_response_json,
                    parsed_response_json=json.dumps(run.parsed_response_json)
                    if run.parsed_response_json is not None
                    else None,
                    status=run.status.value,
                    error_type=run.error_type,
                    error_message=run.error_message,
                    created_at=run.created_at,
                )
            )
            return run

    def save_curation_record(self, record: CurationRecord) -> CurationRecord:
        with self.session() as session:
            session.add(
                CurationRecordRow(
                    record_id=record.record_id,
                    run_id=record.run_id,
                    image_id=record.image_id,
                    file_path=record.file_path,
                    sha256=record.sha256,
                    source_type=record.source_type.value,
                    source_url=record.source_url,
                    usage_rights_status=record.usage_rights_status.value,
                    rulebook_version=record.rulebook_version,
                    prompt_version=record.prompt_version,
                    provider=record.provider,
                    model_name=record.model_name,
                    model_request_id=record.model_request_id,
                    draft_label_json=_dump_label(record.draft_label),
                    final_label_json=_dump_label(record.final_label),
                    raw_response_json=record.raw_response_json,
                    validation_errors_json=json.dumps(record.validation_errors),
                    review_warnings_json=json.dumps(record.review_warnings),
                    review_status=record.status.value,
                    curator_name=record.curator_name,
                    curator_notes=record.curator_notes,
                    expert_metadata_json=_dump_expert_metadata(record.expert_metadata),
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    reviewed_at=record.reviewed_at,
                    approved_at=record.approved_at,
                )
            )
            return record

    def list_curation_records(
        self, *, statuses: list[ReviewStatus] | None = None
    ) -> list[CurationRecord]:
        with self.session() as session:
            stmt = select(CurationRecordRow).order_by(CurationRecordRow.created_at)
            if statuses:
                stmt = stmt.where(
                    CurationRecordRow.review_status.in_([s.value for s in statuses])
                )
            rows = session.scalars(stmt).all()
            return [_to_curation(row) for row in rows]

    def get_curation_record(self, record_id: str) -> CurationRecord | None:
        with self.session() as session:
            row = session.get(CurationRecordRow, record_id)
            return _to_curation(row) if row else None

    def update_curation_record(self, record: CurationRecord) -> CurationRecord:
        with self.session() as session:
            row = session.get(CurationRecordRow, record.record_id)
            if row is None:
                raise KeyError(record.record_id)
            row.final_label_json = _dump_label(record.final_label)
            row.source_url = record.source_url
            row.usage_rights_status = record.usage_rights_status.value
            row.review_status = record.status.value
            row.curator_name = record.curator_name
            row.curator_notes = record.curator_notes
            row.expert_metadata_json = _dump_expert_metadata(record.expert_metadata)
            row.updated_at = record.updated_at
            row.reviewed_at = record.reviewed_at
            row.approved_at = record.approved_at
            row.validation_errors_json = json.dumps(record.validation_errors)
            row.review_warnings_json = json.dumps(record.review_warnings)
            return record

    def add_review_events(self, events: list[ReviewEvent]) -> None:
        if not events:
            return
        with self.session() as session:
            for event_item in events:
                session.add(
                    ReviewEventRow(
                        event_id=event_item.event_id,
                        record_id=event_item.record_id,
                        field_name=event_item.field_name,
                        old_value=event_item.old_value,
                        new_value=event_item.new_value,
                        actor=event_item.actor,
                        created_at=event_item.created_at,
                    )
                )

    def count_images(self) -> int:
        with self.session() as session:
            return session.scalar(select(text("COUNT(*)")).select_from(ImageRow)) or 0

    def status_counts(self) -> dict[str, int]:
        with self.session() as session:
            rows = session.execute(
                text(
                    "SELECT review_status, COUNT(*) AS n FROM curation_records "
                    "GROUP BY review_status"
                )
            ).all()
            return {str(status): int(n) for status, n in rows}

    def list_failed_runs(self, failure_type: str | None = None) -> list[LabelRunRecord]:
        with self.session() as session:
            stmt = select(LabelRunRow).where(
                LabelRunRow.status.in_(
                    [
                        LabelRunStatus.PROVIDER_FAILED.value,
                        LabelRunStatus.VALIDATION_FAILED.value,
                    ]
                )
            )
            if failure_type:
                stmt = stmt.where(LabelRunRow.error_type == failure_type)
            rows = session.scalars(stmt.order_by(LabelRunRow.created_at)).all()
            return [_to_label_run(row) for row in rows]

    def get_image(self, image_id: str) -> ImageRecord | None:
        with self.session() as session:
            row = session.get(ImageRow, image_id)
            return _to_image(row) if row else None


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _dump_label(label: DesignLabelDraft | None) -> str | None:
    if label is None:
        return None
    return label.model_dump_json()


def _load_label(raw: str | None) -> DesignLabelDraft | None:
    if not raw:
        return None
    return DesignLabelDraft.model_validate_json(raw)


def _dump_expert_metadata(metadata: ExpertReferenceMetadata | None) -> str | None:
    if metadata is None:
        return None
    return metadata.model_dump_json()


def _load_expert_metadata(raw: str | None) -> ExpertReferenceMetadata | None:
    if not raw:
        return None
    return ExpertReferenceMetadata.model_validate_json(raw)


def _to_image(row: ImageRow) -> ImageRecord:
    return ImageRecord(
        image_id=row.image_id,
        relative_path=row.relative_path,
        sha256=row.sha256,
        mime_type=row.mime_type,
        width=row.width,
        height=row.height,
        source_type=SourceType(row.source_type),
        source_url=row.source_url,
        usage_rights_status=UsageRightsStatus(row.usage_rights_status),
        created_at=row.created_at,
    )


def _to_label_run(row: LabelRunRow) -> LabelRunRecord:
    parsed: dict[str, Any] | None = None
    if row.parsed_response_json:
        parsed = json.loads(row.parsed_response_json)
    return LabelRunRecord(
        run_id=row.run_id,
        image_id=row.image_id,
        rulebook_version=row.rulebook_version,
        prompt_version=row.prompt_version,
        provider=row.provider,
        model_name=row.model_name,
        request_fingerprint=row.request_fingerprint,
        raw_response_json=row.raw_response_json,
        parsed_response_json=parsed,
        status=LabelRunStatus(row.status),
        error_type=row.error_type,
        error_message=row.error_message,
        created_at=row.created_at,
    )


def _to_curation(row: CurationRecordRow) -> CurationRecord:
    return CurationRecord(
        record_id=row.record_id,
        run_id=row.run_id,
        image_id=row.image_id,
        file_path=row.file_path,
        sha256=row.sha256,
        source_type=SourceType(row.source_type),
        source_url=row.source_url,
        usage_rights_status=UsageRightsStatus(row.usage_rights_status),
        rulebook_version=row.rulebook_version,
        prompt_version=row.prompt_version,
        provider=row.provider,
        model_name=row.model_name,
        model_request_id=row.model_request_id,
        draft_label=_load_label(row.draft_label_json),
        final_label=_load_label(row.final_label_json),
        raw_response_json=row.raw_response_json,
        validation_errors=json.loads(row.validation_errors_json or "[]"),
        review_warnings=json.loads(row.review_warnings_json or "[]"),
        status=ReviewStatus(row.review_status),
        curator_name=row.curator_name,
        curator_notes=row.curator_notes,
        expert_metadata=_load_expert_metadata(row.expert_metadata_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
        reviewed_at=row.reviewed_at,
        approved_at=row.approved_at,
    )

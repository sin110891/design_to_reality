from __future__ import annotations

from datetime import datetime, timezone

from vision_engine.domain.enums import FailureTag, ProjectStatus, ReviewDecision
from vision_engine.domain.models import FeedbackEvent
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import SqliteRepository


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def record_feedback(
    *,
    repo: SqliteRepository,
    project_id: str,
    reviewer: str,
    decision: str | ReviewDecision,
    variant_id: str | None = None,
    rank: int | None = None,
    reference_relevance_score: int | None = None,
    taste_quality_score: int | None = None,
    geometry_preservation_score: int | None = None,
    buildability_score: int | None = None,
    material_coherence_score: int | None = None,
    positive_notes: str | None = None,
    negative_notes: str | None = None,
    failure_tags: list[str] | None = None,
    edited_concept_json: dict | None = None,
) -> FeedbackEvent:
    tags = [FailureTag(t) for t in (failure_tags or [])]
    event = FeedbackEvent(
        feedback_id=new_id("fb"),
        project_id=project_id,
        variant_id=variant_id,
        reviewer=reviewer,
        decision=ReviewDecision(decision),
        rank=rank,
        reference_relevance_score=reference_relevance_score,
        taste_quality_score=taste_quality_score,
        geometry_preservation_score=geometry_preservation_score,
        buildability_score=buildability_score,
        material_coherence_score=material_coherence_score,
        positive_notes=positive_notes,
        negative_notes=negative_notes,
        failure_tags=tags,
        edited_concept_json=edited_concept_json,
        created_at=utcnow(),
    )
    repo.save_feedback(event)

    project = repo.get_project(project_id)
    if project:
        project.status = ProjectStatus.REVIEWED
        project.updated_at = utcnow()
        repo.save_project(project)
    return event

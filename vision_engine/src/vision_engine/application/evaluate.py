from __future__ import annotations

from collections import Counter
from typing import Any

from vision_engine.domain.enums import ReviewDecision
from vision_engine.infrastructure.sqlite_repository import SqliteRepository


def summarise_feedback(repo: SqliteRepository) -> dict[str, Any]:
    """Aggregate Lloyd feedback for prototype success tracking."""
    events = repo.list_feedback()
    if not events:
        return {
            "feedback_count": 0,
            "preferred_decision_rate": None,
            "avg_geometry": None,
            "avg_taste": None,
            "severe_geometry_failures": 0,
            "failure_tag_counts": {},
        }

    decisions = Counter(e.decision.value for e in events)
    approved = decisions.get(ReviewDecision.APPROVED.value, 0)
    geometry_scores = [e.geometry_preservation_score for e in events if e.geometry_preservation_score]
    taste_scores = [e.taste_quality_score for e in events if e.taste_quality_score]
    severe = sum(
        1
        for e in events
        if (e.geometry_preservation_score is not None and e.geometry_preservation_score <= 2)
        or any(t.value == "geometry_failure" for t in e.failure_tags)
    )
    tag_counts: Counter[str] = Counter()
    for e in events:
        for tag in e.failure_tags:
            tag_counts[tag.value] += 1

    return {
        "feedback_count": len(events),
        "decisions": dict(decisions),
        "approval_rate": approved / len(events),
        "avg_geometry": (sum(geometry_scores) / len(geometry_scores)) if geometry_scores else None,
        "avg_taste": (sum(taste_scores) / len(taste_scores)) if taste_scores else None,
        "severe_geometry_failures": severe,
        "severe_geometry_rate": severe / len(events),
        "failure_tag_counts": dict(tag_counts),
        "targets": {
            "geometry_avg_min": 4.0,
            "severe_geometry_max_rate": 0.2,
            "curated_preference_min": 0.7,
        },
    }

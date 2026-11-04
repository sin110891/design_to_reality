from __future__ import annotations

from vision_engine.domain.models import DatasetRecord, ProjectInput
from vision_engine.domain.services import (
    hybrid_score,
    metadata_match_score,
    soft_filter_penalty,
)


class DeterministicMultimodalReranker:
    """Second-stage reranker using calibrated multimodal signals."""

    def score(
        self,
        *,
        query: ProjectInput,
        record: DatasetRecord,
        image_similarity: float,
        text_similarity: float,
        fusion_score: float,
    ) -> float:
        meta = metadata_match_score(query, record)
        quality_norm = max(0.0, min(1.0, (record.architect_quality_score - 1.0) / 4.0))
        base = hybrid_score(
            image_similarity=image_similarity,
            text_similarity=text_similarity,
            metadata_match=meta,
            architect_quality=record.architect_quality_score,
            image_weight=0.30,
            text_weight=0.25,
            metadata_weight=0.25,
            quality_weight=0.20,
        )
        rerank = 0.55 * base + 0.25 * fusion_score + 0.20 * quality_norm
        return rerank * soft_filter_penalty(query, record)

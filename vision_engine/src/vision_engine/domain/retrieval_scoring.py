from __future__ import annotations

from collections.abc import Iterable


def reciprocal_rank_fusion(
    rankings: dict[str, list[str]],
    *,
    k: int = 60,
) -> dict[str, float]:
    """Fuse ranked candidate lists using reciprocal rank fusion."""
    scores: dict[str, float] = {}
    for ids in rankings.values():
        for rank, candidate_id in enumerate(ids, start=1):
            scores[candidate_id] = scores.get(candidate_id, 0.0) + 1.0 / (k + rank)
    return scores


def ndcg_at_k(relevances: list[int], k: int) -> float:
    """Compute nDCG@K for integer relevance grades (0-3)."""
    if not relevances:
        return 0.0
    k = min(k, len(relevances))
    gains = [float(r) for r in relevances[:k]]
    discounts = [1.0 / np_log(i + 2) for i in range(k)]
    dcg = sum(g * d for g, d in zip(gains, discounts))
    ideal = sorted(relevances, reverse=True)[:k]
    idcg = sum(float(r) * d for r, d in zip(ideal, discounts))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def recall_at_k(relevant_ids: set[str], retrieved_ids: Iterable[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hits = sum(1 for rid in list(retrieved_ids)[:k] if rid in relevant_ids)
    return hits / len(relevant_ids)


def np_log(value: float) -> float:
    import math

    return math.log2(value)

from __future__ import annotations

from vision_engine.domain.retrieval_scoring import ndcg_at_k, recall_at_k, reciprocal_rank_fusion


def test_reciprocal_rank_fusion_combines_lists():
    scores = reciprocal_rank_fusion(
        {
            "image": ["a", "b", "c"],
            "text": ["b", "a", "d"],
        }
    )
    assert scores["a"] > scores["c"]
    assert scores["b"] >= scores["d"]


def test_recall_at_k():
    relevant = {"a", "b"}
    retrieved = ["a", "x", "b", "y"]
    assert recall_at_k(relevant, retrieved, 3) == 1.0
    assert recall_at_k(relevant, retrieved, 1) == 0.5


def test_ndcg_at_k_perfect_ranking():
    assert ndcg_at_k([3, 2, 1], 3) == 1.0

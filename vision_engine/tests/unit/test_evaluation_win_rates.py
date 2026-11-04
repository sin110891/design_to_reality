from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vision_engine.application.evaluation_import_selections import compute_win_proportions
from vision_engine.domain.enums import BenchmarkArm, EvaluationSelectionMethod
from vision_engine.domain.evaluation_models import EvaluationSelection


def _selection(arm: BenchmarkArm | None) -> EvaluationSelection:
    return EvaluationSelection(
        selection_id="esel_1",
        evaluation_export_id="eexp_1",
        evaluation_case_id="ecase_1",
        public_case_id="case_0001",
        evaluator_id="tester",
        winner_candidate_id="candidate_01" if arm else None,
        winner_arm=arm,
        selection_method=EvaluationSelectionMethod.CSV,
        submitted_at=datetime.now(timezone.utc),
    )


def test_compute_win_proportions():
    selections = [
        _selection(BenchmarkArm.CURATED),
        _selection(BenchmarkArm.BASELINE),
        _selection(BenchmarkArm.CURATED),
        _selection(None),
    ]
    report = compute_win_proportions(selections)
    assert report["valid_selections"] == 3
    assert report["curated_wins"] == 2
    assert report["baseline_wins"] == 1
    assert report["curated_win_rate"] == pytest.approx(2 / 3)
    assert report["baseline_win_rate"] == pytest.approx(1 / 3)

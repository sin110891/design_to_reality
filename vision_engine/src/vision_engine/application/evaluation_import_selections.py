from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vision_engine.domain.enums import BenchmarkArm, EvaluationSelectionMethod
from vision_engine.domain.evaluation_models import EvaluationSelection
from vision_engine.infrastructure.evaluation_bundle import write_json
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compute_win_proportions(selections: list[EvaluationSelection]) -> dict[str, Any]:
    valid = [s for s in selections if s.winner_arm is not None]
    curated_wins = sum(1 for s in valid if s.winner_arm == BenchmarkArm.CURATED)
    baseline_wins = sum(1 for s in valid if s.winner_arm == BenchmarkArm.BASELINE)
    total = len(valid)
    return {
        "total_selections": len(selections),
        "valid_selections": total,
        "skipped_or_unresolved": len(selections) - total,
        "curated_wins": curated_wins,
        "baseline_wins": baseline_wins,
        "curated_win_rate": (curated_wins / total) if total else 0.0,
        "baseline_win_rate": (baseline_wins / total) if total else 0.0,
    }


def import_evaluation_selections(
    *,
    repo: SqliteRepository,
    evaluation_export_id: str,
    csv_path: Path,
    evaluator_id: str = "default",
) -> tuple[list[EvaluationSelection], dict[str, Any]]:
    export = repo.get_evaluation_export(evaluation_export_id)
    if export is None:
        raise ValueError(f"Evaluation export not found: {evaluation_export_id}")

    candidates = repo.list_blind_export_candidates(evaluation_export_id)
    by_case_and_candidate: dict[tuple[str, str], object] = {
        (c.public_case_id, c.blind_candidate_id): c for c in candidates
    }
    case_id_map = {c.public_case_id: c.evaluation_case_id for c in candidates}

    selections: list[EvaluationSelection] = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            public_case_id = (row.get("case_id") or "").strip()
            winner_candidate_id = (row.get("winner_candidate_id") or "").strip() or None
            evaluation_case_id = case_id_map.get(public_case_id)
            if not evaluation_case_id:
                continue

            winner_arm = None
            if winner_candidate_id:
                candidate = by_case_and_candidate.get((public_case_id, winner_candidate_id))
                if candidate is not None:
                    winner_arm = candidate.arm

            selection = EvaluationSelection(
                selection_id=new_id("esel"),
                evaluation_export_id=evaluation_export_id,
                evaluation_case_id=evaluation_case_id,
                public_case_id=public_case_id,
                evaluator_id=evaluator_id,
                winner_candidate_id=winner_candidate_id,
                winner_arm=winner_arm,
                selection_method=EvaluationSelectionMethod.CSV,
                submitted_at=utcnow(),
            )
            repo.save_evaluation_selection(selection)
            selections.append(selection)

    report = compute_win_proportions(selections)
    report["evaluation_export_id"] = evaluation_export_id
    report["evaluator_id"] = evaluator_id
    return selections, report


def write_selection_report(report: dict[str, Any], output_path: Path) -> Path:
    write_json(output_path, report)
    return output_path

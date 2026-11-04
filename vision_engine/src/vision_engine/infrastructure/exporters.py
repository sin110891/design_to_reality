from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from vision_engine.domain.models import FeedbackEvent


def export_feedback(
    events: Iterable[FeedbackEvent],
    output: Path,
    *,
    fmt: str = "jsonl",
) -> tuple[Path, int]:
    rows: list[dict[str, Any]] = []
    for event in events:
        payload = event.model_dump(mode="json")
        payload["failure_tags"] = [t.value if hasattr(t, "value") else t for t in event.failure_tags]
        rows.append(payload)

    output.parent.mkdir(parents=True, exist_ok=True)
    fmt = fmt.lower()
    if fmt == "jsonl":
        with output.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    elif fmt == "csv":
        pd.DataFrame(rows).to_csv(output, index=False)
    elif fmt == "parquet":
        pd.DataFrame(rows).to_parquet(output, index=False)
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
    return output, len(rows)


def export_review_training_rows(
    rows: list[dict],
    output: Path,
    *,
    fmt: str = "jsonl",
) -> tuple[Path, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    fmt = fmt.lower()
    if fmt == "jsonl":
        with output.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    elif fmt == "csv":
        pd.DataFrame(rows).to_csv(output, index=False)
    elif fmt == "parquet":
        pd.DataFrame(rows).to_parquet(output, index=False)
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
    return output, len(rows)


def export_pipeline_snapshot(payload: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return output

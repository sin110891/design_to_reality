#!/usr/bin/env python3
"""Interactive-friendly walkthrough of ingest → label → export-review.

Run under the debugger (see demo/DEBUGGING.md and .vscode/launch.json):

    python demo/stepthrough_pipeline.py
    python demo/stepthrough_pipeline.py --limit 2 --persist
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from design_dataset.application.ingest import ingest_images  # noqa: E402
from design_dataset.application.label import label_images  # noqa: E402
from design_dataset.application.review import export_for_review  # noqa: E402
from design_dataset.infrastructure.sqlite_repository import SqliteRepository  # noqa: E402
from design_dataset.settings import AppSettings, clear_settings_cache  # noqa: E402


def build_settings(*, persist: bool, work_dir: Path) -> AppSettings:
    clear_settings_cache()
    db_path = ROOT / "data" / "app.db" if persist else work_dir / "demo.db"
    return AppSettings(
        model_provider="fake",
        model_name="fake-model-v1",
        database_path=db_path,
        rulebook_path=ROOT / "configs" / "rulebook.v1.yaml",
        app_config_path=ROOT / "configs" / "app.local.yaml",
        prompt_version="label_image_v1",
        project_root=ROOT,
        log_level="INFO",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=3, help="Images to label")
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Use data/app.db instead of a temporary database",
    )
    args = parser.parse_args()

    image_dir = ROOT / "data" / "raw_images" / "contemporary_europe"
    if not image_dir.exists():
        print(f"Missing image folder: {image_dir}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="design_dataset_demo_") as tmp:
        work_dir = Path(tmp)
        settings = build_settings(persist=args.persist, work_dir=work_dir)
        repo = SqliteRepository(settings.database_path)

        # BREAKPOINT HINT: step into init_db / ingest_images / label_images
        repo.init_db()
        print(f"DB: {settings.database_path}")

        ingest_report = ingest_images(
            repo=repo,
            settings=settings,
            input_dir=image_dir,
        )
        print(
            "Ingest:",
            f"discovered={ingest_report.discovered}",
            f"ingested={ingest_report.ingested}",
            f"duplicates_skipped={ingest_report.duplicates_skipped}",
        )

        label_report = label_images(
            repo=repo,
            settings=settings,
            limit=args.limit,
        )
        print(
            "Label:",
            f"labelled={label_report.labelled}",
            f"validation_failed={label_report.validation_failed}",
            f"provider_failed={label_report.provider_failed}",
            f"skipped_idempotent={label_report.skipped_idempotent}",
        )

        # Demonstrate idempotency — second pass should skip.
        label_again = label_images(repo=repo, settings=settings, limit=args.limit)
        print(
            "Label (rerun):",
            f"labelled={label_again.labelled}",
            f"skipped_idempotent={label_again.skipped_idempotent}",
        )

        review_out = (
            ROOT / "data" / "review" / "demo_batch.xlsx"
            if args.persist
            else work_dir / "demo_batch.xlsx"
        )
        export_for_review(repo=repo, output=review_out)
        print(f"Review workbook: {review_out}")
        print("Status counts:", repo.status_counts())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

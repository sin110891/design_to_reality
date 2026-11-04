#!/usr/bin/env python3
"""Full Gemini labelling walkthrough for understanding the system.

Flow:
  1. init DB
  2. ingest images
  3. label with real Gemini (rulebook + structured JSON + validation)
  4. print one draft sample
  5. export review workbook
  6. simulate curator approval (auto-approve drafts in a copy of the workbook)
  7. import review
  8. export gold JSONL

Requires GEMINI_API_KEY and a Gemini-capable MODEL_NAME in .env.

    source .venv/bin/activate
    python demo/gemini_label_flow.py
    python demo/gemini_label_flow.py --limit 2 --persist
    make demo-gemini
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

load_dotenv(ROOT / ".env")

from design_dataset.application.export import export_gold_dataset  # noqa: E402
from design_dataset.application.ingest import ingest_images  # noqa: E402
from design_dataset.application.label import label_images  # noqa: E402
from design_dataset.application.review import export_for_review, import_reviewed  # noqa: E402
from design_dataset.domain.enums import ReviewStatus  # noqa: E402
from design_dataset.infrastructure.sqlite_repository import SqliteRepository  # noqa: E402
from design_dataset.settings import AppSettings, clear_settings_cache, get_settings  # noqa: E402


def _banner(title: str, why: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print(f"Why: {why}")
    print("=" * 72)


def build_settings(*, persist: bool, work_dir: Path) -> AppSettings:
    clear_settings_cache()
    base = get_settings()
    provider = (base.model_provider or "").lower().strip()
    if provider in {"google", "gemini"}:
        provider = "gemini"
    elif provider == "fake":
        print(
            "WARNING: MODEL_PROVIDER=fake in .env — forcing gemini for this demo.",
            file=sys.stderr,
        )
        provider = "gemini"
    else:
        provider = "gemini"

    if not base.gemini_api_key:
        raise SystemExit(
            "GEMINI_API_KEY is missing in .env — cannot run the Gemini demo."
        )

    db_path = ROOT / "data" / "app.db" if persist else work_dir / "gemini_demo.db"
    return AppSettings(
        gemini_api_key=base.gemini_api_key,
        model_provider=provider,
        model_name=base.model_name,
        app_env=base.app_env,
        log_level=base.log_level,
        database_path=db_path,
        rulebook_path=ROOT / "configs" / "rulebook.v1.yaml",
        app_config_path=ROOT / "configs" / "app.local.yaml",
        prompt_version=base.prompt_version or "label_image_v1",
        project_root=ROOT,
        inference=base.inference,
        images=base.images,
        review=base.review,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=2,
        help="Images to label with Gemini (keep small; costs tokens)",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Use data/app.db and write artefacts under data/review + data/exports",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore idempotent fingerprint skip when labelling",
    )
    parser.add_argument(
        "--skip-review-sim",
        action="store_true",
        help="Stop after export-review (do not auto-approve / import / gold export)",
    )
    args = parser.parse_args()

    image_dir = ROOT / "data" / "raw_images" / "contemporary_europe"
    if not image_dir.exists():
        print(f"Missing image folder: {image_dir}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="design_dataset_gemini_") as tmp:
        work_dir = Path(tmp)
        settings = build_settings(persist=args.persist, work_dir=work_dir)
        repo = SqliteRepository(settings.database_path)

        _banner(
            "0) Configure",
            "Load .env provider/model/key so the demo uses your real Gemini setup.",
        )
        print(f"DB:            {settings.database_path}")
        print(f"Provider:      {settings.model_provider}")
        print(f"Model:         {settings.model_name}")
        print(f"Rulebook:      {settings.rulebook_path}")
        print(f"Prompt:        {settings.prompt_version}")
        print(f"Images:        {image_dir}")
        print(f"Limit:         {args.limit}")

        _banner(
            "1) init-db",
            "Create SQLite tables for images, label runs, curation records, review events.",
        )
        repo.init_db()
        print("Schema ready.")

        _banner(
            "2) ingest",
            "Hash files, skip duplicates, register unique images before any model call.",
        )
        ingest_report = ingest_images(
            repo=repo,
            settings=settings,
            input_dir=image_dir,
        )
        print(
            f"discovered={ingest_report.discovered} "
            f"ingested={ingest_report.ingested} "
            f"duplicates_skipped={ingest_report.duplicates_skipped}"
        )

        _banner(
            "3) label (Gemini)",
            "For each image: fingerprint → prompt+rulebook → Gemini structured JSON → "
            "Pydantic + vocabulary/business validation → store draft or failure.",
        )
        label_report = label_images(
            repo=repo,
            settings=settings,
            limit=args.limit,
            force=args.force,
        )
        print(
            f"labelled={label_report.labelled} "
            f"validation_failed={label_report.validation_failed} "
            f"provider_failed={label_report.provider_failed} "
            f"skipped_idempotent={label_report.skipped_idempotent} "
            f"total_tokens≈{label_report.total_tokens} "
            f"elapsed_s={label_report.elapsed_seconds:.2f}"
        )
        if label_report.labelled == 0 and label_report.skipped_idempotent == 0:
            print(
                "No drafts created. Check GEMINI_API_KEY, MODEL_NAME, and provider errors above.",
                file=sys.stderr,
            )
            return 1

        _banner(
            "4) inspect one draft",
            "Drafts are model proposals only — not gold until a curator approves them.",
        )
        drafts = repo.list_curation_records(statuses=[ReviewStatus.DRAFT])
        if drafts:
            sample = drafts[0]
            print(f"record_id:  {sample.record_id}")
            print(f"file_path:  {sample.file_path}")
            print(f"provider:   {sample.provider} / {sample.model_name}")
            print(f"warnings:   {sample.review_warnings or []}")
            if sample.draft_label:
                print(json.dumps(sample.draft_label.model_dump(), indent=2)[:2500])
                if len(json.dumps(sample.draft_label.model_dump())) > 2500:
                    print("… (truncated)")
        else:
            print("No draft rows (maybe all skipped as idempotent). Use --force to relabel.")

        # Keep review/gold artefacts on disk even when the DB is temporary.
        review_dir = ROOT / "data" / "review"
        export_dir = ROOT / "data" / "exports"
        review_dir.mkdir(parents=True, exist_ok=True)
        export_dir.mkdir(parents=True, exist_ok=True)
        review_out = review_dir / "gemini_demo_batch.xlsx"

        _banner(
            "5) export-review",
            "Spreadsheet-first human loop: curator edits status/fields offline.",
        )
        export_for_review(repo=repo, output=review_out)
        print(f"Wrote: {review_out}")

        if args.skip_review_sim:
            print("\nStopped after export-review (--skip-review-sim).")
            print("Next: edit the workbook, then make import-review / export-gold.")
            return 0

        _banner(
            "6) simulate curator approval",
            "In production Lloyd edits the XLSX. Here we auto-mark drafts approved "
            "so you can see import + gold export without manual Excel work.",
        )
        import pandas as pd

        reviewed_path = review_dir / "gemini_demo_batch_reviewed.xlsx"
        shutil.copy2(review_out, reviewed_path)
        df = pd.read_excel(reviewed_path)
        if "review_status" in df.columns:
            df["review_status"] = "approved"
        if "curator_notes" in df.columns:
            df["curator_notes"] = "Demo auto-approval for Gemini walkthrough"
        df.to_excel(reviewed_path, index=False)
        print(f"Wrote simulated review: {reviewed_path} ({len(df)} rows)")

        _banner(
            "7) import-review",
            "Re-validate edited values against the same rulebook; record field diffs; "
            "set approved/reviewed/rejected. Never trust spreadsheet values blindly.",
        )
        counts = import_reviewed(
            repo=repo,
            settings=settings,
            input_path=reviewed_path,
        )
        print(counts)

        _banner(
            "8) export-gold",
            "Emit approved records only (draft + final preserved) for downstream use.",
        )
        gold_path = export_dir / "gemini_demo_gold.jsonl"
        path, count = export_gold_dataset(
            repo=repo,
            output=gold_path,
            fmt="jsonl",
        )
        print(f"Exported {count} approved records → {path}")
        if path.exists() and count:
            first = path.read_text(encoding="utf-8").splitlines()[0]
            preview = json.loads(first)
            print(
                "Gold preview keys:",
                sorted(preview.keys())[:12],
                "…",
            )
            if preview.get("final_label"):
                print(
                    "final_label.style_family:",
                    preview["final_label"].get("style_family"),
                )
                print("final_label.mood:", preview["final_label"].get("mood"))

        print()
        print("Status counts:", repo.status_counts())
        print()
        print("Done. You have walked the full hybrid loop with real Gemini drafts.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

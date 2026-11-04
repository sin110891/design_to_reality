from __future__ import annotations

"""
Offline step-through: build index from dataset_factory gold → curated pipeline → feedback export.
"""

import argparse
import shutil
import tempfile
from pathlib import Path

from rich.console import Console

from vision_engine.application.build_index import build_index
from vision_engine.application.export_feedback import export_feedback_dataset
from vision_engine.application.record_feedback import record_feedback
from vision_engine.application.run_pipeline import run_pipeline
from vision_engine.domain.enums import GenerationMode, ReviewDecision
from vision_engine.domain.models import ProjectInput
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings, clear_settings_cache

ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT.parent / "dataset_factory"
GOLD = FACTORY / "data" / "exports" / "gemini_demo_gold.jsonl"
IMAGES = FACTORY / "data" / "raw_images" / "contemporary_europe"
console = Console()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--persist", action="store_true", help="Write into vision_engine/data")
    args = parser.parse_args()

    clear_settings_cache()
    if args.persist:
        work = ROOT / "data" / "demo_run"
        work.mkdir(parents=True, exist_ok=True)
        cleanup = None
    else:
        tmp = tempfile.TemporaryDirectory(prefix="vision_engine_demo_")
        work = Path(tmp.name)
        cleanup = tmp

    for name in ("configs", "src"):
        dest = work / name
        if not dest.exists():
            shutil.copytree(ROOT / name, dest)

    settings = AppSettings(
        model_provider="fake",
        embedding_provider="fake",
        model_name="fake-concept-v1",
        image_edit_model="fake-image-edit-v1",
        database_path=work / "vision_engine.db",
        rulebook_path=work / "configs" / "rulebook.v1.yaml",
        app_config_path=work / "configs" / "app.local.yaml",
        prompts_config_path=work / "configs" / "prompts.v1.yaml",
        project_root=work,
    )
    settings.paths.uploads = work / "uploads"
    settings.paths.generated = work / "generated"
    settings.paths.exports = work / "exports"
    settings.paths.index_path = work / "indexes" / "curated.npz"
    settings.paths.curated_images = IMAGES

    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )

    console.rule("1. Build curated index from dataset_factory gold")
    path, count = build_index(
        repo=repo,
        settings=settings,
        gold_jsonl=GOLD,
        images_dir=IMAGES,
        output=settings.paths.index_path,
    )
    console.print(f"Indexed {count} records → {path}")

    console.rule("2. Run curated pipeline (fake providers)")
    room = sorted(IMAGES.glob("*.jpg"))[0]
    room_copy = work / "room.jpg"
    shutil.copy2(room, room_copy)
    result = run_pipeline(
        repo=repo,
        settings=settings,
        file_store=file_store,
        payload=ProjectInput(
            room_image_path=str(room_copy),
            room_type="living_room",
            style_family="Contemporary Europe",
            brief="warm contemporary European, calmer lighting, retain windows and fireplace",
            budget_band="medium_high",
            constraints=["do not move walls, doors, windows, radiators, or fireplace"],
        ),
        mode=GenerationMode.CURATED,
    )
    console.print(f"Project: {result.project.project_id}")
    console.print(f"Concept: {result.design_direction.concept_title if result.design_direction else None}")
    console.print(f"References: {len(result.references)} | Variants: {len(result.variants)}")

    console.rule("3. Record feedback + export")
    record_feedback(
        repo=repo,
        project_id=result.project.project_id,
        reviewer="Lloyd Lee",
        decision=ReviewDecision.APPROVED,
        variant_id=result.variants[0].variant_id if result.variants else None,
        rank=1,
        taste_quality_score=5,
        geometry_preservation_score=4,
        positive_notes="Demo approval",
    )
    out, n = export_feedback_dataset(
        repo=repo,
        settings=settings,
        output=settings.paths.exports / "feedback.jsonl",
    )
    console.print(f"Exported {n} feedback events → {out}")
    console.print("[green]Demo complete[/green]")

    if cleanup is not None:
        cleanup.cleanup()


if __name__ == "__main__":
    main()

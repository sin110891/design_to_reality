from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import yaml

from vision_engine.application.build_index import build_index
from vision_engine.application.evaluation_workflow import (
    create_evaluation_package,
    score_blind_evaluation,
)
from vision_engine.application.evaluation_spec import load_evaluation_spec
from vision_engine.domain.enums import EvaluationCaseStatus, EvaluationRunStatus
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import AppSettings, clear_settings_cache


ROOT = Path(__file__).resolve().parents[2]
FACTORY = ROOT.parent / "dataset_factory"
SOURCE_IMAGES = FACTORY / "tests" / "fixtures" / "sample_data" / "raw_images" / "contemporary_europe"
GOLD = FACTORY / "tests" / "fixtures" / "sample_data" / "exports" / "gemini_demo_gold.jsonl"


def _settings(tmp_path: Path) -> AppSettings:
    clear_settings_cache()
    for name in ("configs", "src"):
        src = ROOT / name
        dest = tmp_path / name
        if not dest.exists():
            shutil.copytree(src, dest)
    settings = AppSettings(
        model_provider="fake",
        model_name="fake-concept-v1",
        image_edit_model="fake-image-edit-v1",
        embedding_provider="fake",
        database_path=tmp_path / "vision_engine.db",
        rulebook_path=tmp_path / "configs" / "rulebook.v1.yaml",
        app_config_path=tmp_path / "configs" / "app.local.yaml",
        prompts_config_path=tmp_path / "configs" / "prompts.v1.yaml",
        concept_prompt_version="concept_direction",
        image_edit_prompt_version="image_edit",
        project_root=tmp_path,
    )
    settings.paths.uploads = tmp_path / "uploads"
    settings.paths.generated = tmp_path / "generated"
    settings.paths.exports = tmp_path / "exports"
    settings.paths.evaluations = tmp_path / "evaluations"
    settings.paths.blind_evaluations = tmp_path / "blind_evaluations"
    settings.paths.index_path = tmp_path / "indexes" / "curated.npz"
    settings.paths.curated_images = SOURCE_IMAGES
    return settings


def _write_eval_config(tmp_path: Path, room: Path) -> Path:
    payload = {
        "evaluation": {"name": "integration-test", "repetitions": 1},
        "cases": [
            {
                "room_image_path": str(room),
                "brief": "warm contemporary European, calmer lighting, retain windows and fireplace",
                "room_type": "living_room",
                "style_family": "Contemporary Europe",
                "budget_band": "medium_high",
                "constraints": ["do not move walls, doors, windows, radiators, or fireplace"],
                "inspiration_image_paths": [],
            }
        ],
        "exports": {
            "full_output_dir": "evaluations",
            "blind_output_dir": "blind_evaluations",
        },
    }
    config = tmp_path / "evaluation.yaml"
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return config


def test_controlled_evaluation_export_and_import(tmp_path: Path):
    assert SOURCE_IMAGES.exists() and GOLD.exists()
    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )
    build_index(
        repo=repo,
        settings=settings,
        gold_jsonl=GOLD,
        images_dir=SOURCE_IMAGES,
        output=settings.paths.index_path,
    )

    room = sorted(SOURCE_IMAGES.glob("*.jpg"))[0]
    room_copy = tmp_path / "room.jpg"
    shutil.copy2(room, room_copy)
    config = _write_eval_config(tmp_path, room_copy)
    spec = load_evaluation_spec(settings=settings, config_path=config)
    staged_room = Path(spec.case_specs[0].room_image_path)
    assert staged_room.parent == settings.paths.evaluations / "_inputs"
    assert staged_room.read_bytes() == room_copy.read_bytes()

    package = create_evaluation_package(
        repo=repo,
        settings=settings,
        file_store=file_store,
        config_path=config,
        workers=2,
    )
    summary = package.summary
    assert summary.evaluation_run_id.startswith("eval_")
    assert summary.total_cases == 1
    assert summary.complete_cases == 1
    assert summary.status == EvaluationRunStatus.COMPLETED

    full_export, full_dest = package.full_export, package.full_directory
    assert (full_dest / "manifest.json").exists()
    manifest = json.loads((full_dest / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["complete_pairs"] == 1
    assert "curated" in json.dumps(manifest)

    blind_export, blind_dest = package.blind_export, package.blind_directory
    assert (blind_dest / "response_template.csv").exists()
    blind_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in blind_dest.rglob("*")
        if path.is_file() and path.suffix in {".md", ".csv", ".txt"}
    )
    assert "curated" not in blind_text.lower()
    assert "baseline" not in blind_text.lower()
    assert "proj_" not in blind_text

    response_csv = blind_dest / "response_template.csv"
    rows = list(csv.DictReader(response_csv.open(encoding="utf-8")))
    assert rows
    rows[0]["winner_candidate_id"] = next(
        path.stem for path in (blind_dest / "cases" / rows[0]["case_id"] / "candidates").glob("*.png")
    )
    filled_csv = tmp_path / "filled.csv"
    with filled_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "winner_candidate_id"])
        writer.writeheader()
        writer.writerows(rows)

    score = score_blind_evaluation(
        repo=repo,
        settings=settings,
        evaluation_export_id=blind_export.evaluation_export_id,
        csv_path=filled_csv,
        evaluator_id="tester",
    )
    assert score.report_path.exists()
    assert score.report["valid_selections"] == 1
    assert score.report["curated_wins"] + score.report["baseline_wins"] == 1

    cases = repo.list_evaluation_cases(summary.evaluation_run_id)
    assert cases[0].status == EvaluationCaseStatus.COMPLETE

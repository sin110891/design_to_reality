from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from design_dataset.application.export import export_gold_dataset
from design_dataset.application.import_v3 import import_v3_annotations
from design_dataset.application.ingest import ingest_images
from design_dataset.application.label import label_images
from design_dataset.application.review import export_for_review, import_reviewed
from design_dataset.domain.enums import ReviewStatus
from design_dataset.infrastructure.sqlite_repository import SqliteRepository
from design_dataset.settings import AppSettings, clear_settings_cache

ROOT = Path(__file__).resolve().parents[2]
SOURCE_IMAGES = ROOT / "tests" / "fixtures" / "sample_data" / "raw_images" / "contemporary_europe"


def _settings(tmp_path: Path) -> AppSettings:
    clear_settings_cache()
    db = tmp_path / "app.db"
    return AppSettings(
        model_provider="fake",
        model_name="fake-model-v1",
        database_path=db,
        rulebook_path=ROOT / "configs" / "rulebook.v1.yaml",
        app_config_path=ROOT / "configs" / "app.local.yaml",
        prompt_version="label_image_v1",
        project_root=ROOT,
    )


def test_ingest_label_review_export_idempotent(tmp_path: Path):
    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()

    # Copy a few real images into an isolated folder.
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    sources = sorted(SOURCE_IMAGES.glob("*.jpg"))[:3]
    assert sources, "expected fixture contemporary_europe images"
    for src in sources:
        shutil.copy2(src, image_dir / src.name)

    ingest_report = ingest_images(repo=repo, settings=settings, input_dir=image_dir)
    assert ingest_report.ingested == 3
    assert ingest_report.duplicates_skipped == 0

    # Second ingest is idempotent by content hash.
    ingest_again = ingest_images(repo=repo, settings=settings, input_dir=image_dir)
    assert ingest_again.ingested == 0
    assert ingest_again.duplicates_skipped == 3

    label_report = label_images(repo=repo, settings=settings, limit=3)
    assert label_report.labelled == 3
    assert label_report.validation_failed == 0
    assert label_report.provider_failed == 0

    # Idempotent skip on unchanged fingerprint.
    label_again = label_images(repo=repo, settings=settings, limit=3)
    assert label_again.labelled == 0
    assert label_again.skipped_idempotent == 3

    review_path = tmp_path / "batch.xlsx"
    export_for_review(repo=repo, output=review_path)
    df = pd.read_excel(review_path)
    assert len(df) == 3
    df["review_status"] = "approved"
    df["curator_notes"] = "Looks good"
    reviewed_path = tmp_path / "batch_reviewed.xlsx"
    df.to_excel(reviewed_path, index=False)

    counts = import_reviewed(repo=repo, settings=settings, input_path=reviewed_path)
    assert counts["approved"] == 3

    gold_path = tmp_path / "gold.jsonl"
    path, count = export_gold_dataset(repo=repo, output=gold_path, fmt="jsonl")
    assert count == 3
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    payload = json.loads(lines[0])
    assert payload["status"] == ReviewStatus.APPROVED.value
    assert payload["final_label"]["style_family"] == "Contemporary Europe"


def test_fake_client_contract():
    from design_dataset.infrastructure.model_clients.fake import FakeModelClient
    from design_dataset.domain.models import DesignLabelDraft

    client = FakeModelClient()
    image = next(SOURCE_IMAGES.glob("*.jpg"))
    payload, meta = client.label_image(
        image_path=image,
        prompt="test",
        response_schema=DesignLabelDraft.model_json_schema(),
    )
    draft = DesignLabelDraft.model_validate(payload)
    assert draft.style_family == "Contemporary Europe"
    assert meta.provider == "fake"


def test_import_v3_expert_metadata(tmp_path: Path):
    settings = _settings(tmp_path)
    repo = SqliteRepository(settings.database_path)
    repo.init_db()

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    source = sorted(SOURCE_IMAGES.glob("*.jpg"))[0]
    shutil.copy2(source, image_dir / source.name)
    ingest_images(repo=repo, settings=settings, input_dir=image_dir)
    label_images(repo=repo, settings=settings, limit=1)

    v3_path = tmp_path / "v3.xlsx"
    frame = pd.DataFrame(
        [
            {
                "project_id": "P-001",
                "room_id": "R-001",
                "image_id": source.name,
                "source_name": "Lloyd Studio",
                "source_url_or_path": "/refs/example.jpg",
                "license_status": "Owned",
                "project_type": "Domestic",
                "Typology": "House-Living Room",
                "image_type": "Reference",
                "geography": "London, UK",
                "style_family (Des)": "European Contemporary, Traditional",
                "mood (Des)": "Warm, Calm",
                "colour_palette (Obs)": "Cream, Brown",
                "Material-Floor (Obs)": "Oak",
                "Material-Wall (Obs)": "Limewash",
                "Material-Furniture (Obs)": "Linen",
                "Material-Ceiling (Obs)": "Plaster",
                "Colour Scheme (Des)": "Warm neutral",
                "material_palette (Obs) - tag elements as well.": (
                    "{{Floor:Oak},{Wall:Limewash}}"
                ),
                "lighting_type (Obs)": "Natural Light, Pendant",
                "furniture_style (Obs)": "Italian Contemporary",
                "spatial_feel (Des)": "Airy, Calm",
                "budget_band": "High",
                "build_complexity": "Medium",
                "maintenance_level": "Low",
                "likely_trades_required": "Painter, Joiner",
                "primary_trade": "Joiner",
                "secondary_trades": "Painter",
                "architect_quality_score": 5,
                "buildability_score": 4,
                "relevance_score": 5,
                "notes_on_why (descriptive)": "Strong material restraint.",
            }
        ]
    )
    with pd.ExcelWriter(v3_path) as writer:
        frame.to_excel(
            writer,
            sheet_name="Collection Example",
            startrow=1,
            index=False,
        )

    counts = import_v3_annotations(
        repo=repo,
        settings=settings,
        input_path=v3_path,
    )
    assert counts["unique_images"] == 1
    assert counts["records_updated"] == 1

    record = repo.list_curation_records()[0]
    assert record.expert_metadata is not None
    assert record.expert_metadata.project_id == "P-001"
    assert record.expert_metadata.material_floor == ["Oak"]
    assert record.expert_metadata.architect_quality_score == 5
    assert record.usage_rights_status.value == "studio_owned"

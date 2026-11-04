from __future__ import annotations

import csv
import random
from datetime import datetime, timezone
from pathlib import Path

from vision_engine.application.evaluation_report import _complete_cases
from vision_engine.domain.enums import BenchmarkArm, EvaluationExportStatus, EvaluationExportType
from vision_engine.domain.evaluation_models import BlindExportCandidate, EvaluationExport
from vision_engine.infrastructure.evaluation_bundle import copy_verified_image, manifest_sha256, write_json
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_blind_output_dir(
    settings: AppSettings, output_dir: Path | None, export_id: str
) -> Path:
    if output_dir is not None:
        base = output_dir if output_dir.is_absolute() else settings.resolve(output_dir)
    else:
        base = settings.paths.blind_evaluations
    return (base.expanduser() / f"blind_{export_id}").resolve()


def export_blind_evaluation(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    evaluation_run_id: str,
    output_dir: Path | None = None,
    seed: int | None = None,
) -> tuple[EvaluationExport, Path]:
    run = repo.get_evaluation_run(evaluation_run_id)
    if run is None:
        raise ValueError(f"Evaluation run not found: {evaluation_run_id}")

    export_id = new_id("eexp")
    dest = _resolve_blind_output_dir(settings, output_dir, export_id)
    dest.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)
    complete = _complete_cases(repo, evaluation_run_id, settings)
    if not complete:
        raise ValueError("No complete evaluation pairs available for blind export")

    template_rows: list[dict[str, str]] = []
    candidate_records: list[BlindExportCandidate] = []

    for case, curated, baseline, curated_variants, baseline_variants in complete:
        case_dir = dest / "cases" / case.public_case_id
        candidates_dir = case_dir / "candidates"
        case_dir.mkdir(parents=True, exist_ok=True)

        room_path = Path(case.input_spec_json["room_image_path"])
        copy_verified_image(
            room_path,
            case_dir / "room.png",
            case.input_spec_json["room_sha256"],
        )
        (case_dir / "brief.txt").write_text(case.input_spec_json["brief"], encoding="utf-8")

        entries: list[tuple[BenchmarkArm, object]] = []
        for variant in curated_variants:
            entries.append((BenchmarkArm.CURATED, variant))
        for variant in baseline_variants:
            entries.append((BenchmarkArm.BASELINE, variant))
        rng.shuffle(entries)

        for order, (arm, variant) in enumerate(entries, start=1):
            candidate_id = f"candidate_{case.public_case_id.removeprefix('case_')}_{order:02d}"
            image_asset = repo.get_image_asset(variant.variant_id)
            if image_asset is None:
                raise ValueError(f"Missing image asset for variant {variant.variant_id}")
            source = settings.resolve(variant.image_path)
            copy_verified_image(
                source,
                candidates_dir / f"{candidate_id}.png",
                image_asset.image_sha256,
            )
            candidate_records.append(
                BlindExportCandidate(
                    blind_candidate_id=candidate_id,
                    evaluation_export_id=export_id,
                    evaluation_case_id=case.evaluation_case_id,
                    public_case_id=case.public_case_id,
                    variant_id=variant.variant_id,
                    arm=arm,
                    image_sha256=image_asset.image_sha256,
                    display_order=order,
                )
            )

        template_rows.append(
            {
                "case_id": case.public_case_id,
                "winner_candidate_id": "",
            }
        )

    instructions = (
        "# Blind evaluation instructions\n\n"
        "Review each case folder. Compare the room image and brief with the candidate images.\n"
        "Fill in `response_template.csv` with one winner candidate ID per case.\n"
        "Use empty winner_candidate_id to skip a case.\n"
    )
    (dest / "instructions.md").write_text(instructions, encoding="utf-8")

    csv_path = dest / "response_template.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "winner_candidate_id"])
        writer.writeheader()
        writer.writerows(template_rows)

    manifest = {
        "evaluation_run_id": evaluation_run_id,
        "export_type": EvaluationExportType.BLIND.value,
        "case_count": len(template_rows),
    }
    write_json(dest / "manifest.json", manifest)
    digest = manifest_sha256(manifest)

    export = EvaluationExport(
        evaluation_export_id=export_id,
        evaluation_run_id=evaluation_run_id,
        export_type=EvaluationExportType.BLIND,
        output_directory=str(dest),
        manifest_sha256=digest,
        status=EvaluationExportStatus.COMPLETED,
        created_at=utcnow(),
    )
    repo.save_evaluation_export(export)
    for candidate in candidate_records:
        repo.save_blind_export_candidate(candidate)

    return export, dest

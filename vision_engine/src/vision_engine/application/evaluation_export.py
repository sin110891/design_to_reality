from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from vision_engine.application.evaluation_report import build_evaluation_report, write_evaluation_report
from vision_engine.domain.enums import EvaluationExportStatus, EvaluationExportType
from vision_engine.domain.evaluation_models import EvaluationExport
from vision_engine.infrastructure.evaluation_bundle import copy_verified_image, manifest_sha256, write_json
from vision_engine.infrastructure.sqlite_repository import SqliteRepository, new_id
from vision_engine.settings import AppSettings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_output_dir(settings: AppSettings, output_dir: Path | None, evaluation_run_id: str) -> Path:
    if output_dir is not None:
        dest = output_dir if output_dir.is_absolute() else settings.resolve(output_dir)
    else:
        dest = settings.paths.evaluations / evaluation_run_id
    return dest.resolve()


def export_full_evaluation(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    evaluation_run_id: str,
    output_dir: Path | None = None,
) -> tuple[EvaluationExport, Path]:
    run = repo.get_evaluation_run(evaluation_run_id)
    if run is None:
        raise ValueError(f"Evaluation run not found: {evaluation_run_id}")

    dest = _resolve_output_dir(settings, output_dir, evaluation_run_id)
    dest.mkdir(parents=True, exist_ok=True)

    report, _ = write_evaluation_report(
        repo=repo,
        settings=settings,
        evaluation_run_id=evaluation_run_id,
        output_dir=dest,
    )

    case_dirs: list[dict] = []
    for case_row in report["cases"]:
        case = repo.get_evaluation_case(case_row["evaluation_case_id"])
        if case is None:
            continue
        case_dir = dest / "cases" / f"{case.public_case_id}_rep_{case.replicate_index:03d}"
        input_dir = case_dir / "input"
        curated_dir = case_dir / "curated"
        baseline_dir = case_dir / "baseline"

        room_path = Path(case.input_spec_json["room_image_path"])
        room_dest = input_dir / "room.png"
        room_sha = case.input_spec_json["room_sha256"]
        copy_verified_image(room_path, room_dest, room_sha)

        case_manifest = {
            "evaluation_case_id": case.evaluation_case_id,
            "public_case_id": case.public_case_id,
            "replicate_index": case.replicate_index,
            "case_input_sha256": case.case_input_sha256,
            "curated_project_id": case_row["curated_project_id"],
            "baseline_project_id": case_row["baseline_project_id"],
        }
        write_json(case_dir / "case.json", case_manifest)

        for arm_name, variants, project_id in (
            ("curated", case_row["curated_variants"], case_row["curated_project_id"]),
            ("baseline", case_row["baseline_variants"], case_row["baseline_project_id"]),
        ):
            target = curated_dir if arm_name == "curated" else baseline_dir
            for idx, variant in enumerate(variants, start=1):
                source = settings.resolve(variant["image_path"])
                image_asset = repo.get_image_asset(variant["variant_id"])
                if image_asset is None:
                    raise ValueError(f"Missing image asset for variant {variant['variant_id']}")
                label = chr(ord("a") + idx - 1)
                copy_verified_image(
                    source,
                    target / f"variant_{label}.png",
                    image_asset.image_sha256,
                )

        case_dirs.append(case_manifest)

    manifest = {
        "evaluation_run_id": evaluation_run_id,
        "export_type": EvaluationExportType.FULL.value,
        "spec_sha256": run.spec_sha256,
        "spec_json": run.spec_json,
        "complete_pairs": len(case_dirs),
        "cases": case_dirs,
    }
    write_json(dest / "manifest.json", manifest)
    digest = manifest_sha256(manifest)

    export = EvaluationExport(
        evaluation_export_id=new_id("eexp"),
        evaluation_run_id=evaluation_run_id,
        export_type=EvaluationExportType.FULL,
        output_directory=str(dest),
        manifest_sha256=digest,
        status=EvaluationExportStatus.COMPLETED,
        created_at=utcnow(),
    )
    repo.save_evaluation_export(export)
    return export, dest

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from jinja2 import Template
from pydantic import ValidationError

from design_dataset.domain.enums import ErrorCategory, LabelRunStatus, ReviewStatus
from design_dataset.domain.errors import ProviderError
from design_dataset.domain.models import BatchReport, CurationRecord, DesignLabelDraft, LabelRunRecord
from design_dataset.domain.policies import validate_against_rulebook
from design_dataset.domain.rulebook import Rulebook, load_rulebook
from design_dataset.infrastructure.hashing import request_fingerprint
from design_dataset.infrastructure.model_clients import build_model_client
from design_dataset.infrastructure.sqlite_repository import SqliteRepository, new_id, utcnow
from design_dataset.settings import AppSettings

logger = logging.getLogger(__name__)


def label_images(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    limit: int | None = None,
    force: bool = False,
    image_ids: list[str] | None = None,
) -> BatchReport:
    started = time.perf_counter()
    report = BatchReport()
    rulebook = load_rulebook(settings.rulebook_path)
    client = build_model_client(settings)
    prompt_template = Template(settings.prompt_template_path.read_text(encoding="utf-8"))
    response_schema = DesignLabelDraft.model_json_schema()
    generation_settings = {
        "temperature": settings.inference.temperature,
        "timeout_seconds": settings.inference.timeout_seconds,
    }

    images = repo.list_images()
    if image_ids:
        wanted = set(image_ids)
        images = [img for img in images if img.image_id in wanted]
    if limit is not None:
        images = images[:limit]

    latencies: list[int] = []
    for image in images:
        fingerprint = request_fingerprint(
            image_sha256=image.sha256,
            rulebook_version=rulebook.version,
            prompt_version=settings.prompt_version,
            provider=settings.model_provider,
            model_name=settings.model_name,
            generation_settings=generation_settings,
        )
        if not force:
            existing = repo.find_successful_run(fingerprint)
            if existing:
                report.skipped_idempotent += 1
                logger.info(
                    "skip_idempotent",
                    extra={
                        "image_id": image.image_id,
                        "request_fingerprint": fingerprint,
                        "pipeline_stage": "label",
                    },
                )
                continue

        image_path = settings.resolve(image.relative_path)
        prompt = prompt_template.render(
            rulebook_json=json.dumps(rulebook.to_prompt_dict(), indent=2),
            response_schema=json.dumps(response_schema, indent=2),
            subset_name=rulebook.subset_name,
        )

        run_id = new_id("run")
        try:
            raw_payload, meta = client.label_image(
                image_path=image_path,
                prompt=prompt,
                response_schema=response_schema,
            )
            if meta.latency_ms:
                latencies.append(meta.latency_ms)
            if meta.total_tokens:
                report.total_tokens += meta.total_tokens

            raw_json = json.dumps(raw_payload, ensure_ascii=False)
            try:
                draft = DesignLabelDraft.model_validate(raw_payload)
            except ValidationError as exc:
                _persist_failure(
                    repo=repo,
                    image=image,
                    run_id=run_id,
                    fingerprint=fingerprint,
                    settings=settings,
                    rulebook=rulebook,
                    raw_json=raw_json,
                    error_type=ErrorCategory.VALIDATION.value,
                    error_message=str(exc),
                    status=LabelRunStatus.VALIDATION_FAILED,
                    provider=meta.provider,
                    model_name=meta.model_name,
                    request_id=meta.request_id,
                )
                report.validation_failed += 1
                continue

            validation = validate_against_rulebook(draft, rulebook)
            if not validation.ok:
                _persist_failure(
                    repo=repo,
                    image=image,
                    run_id=run_id,
                    fingerprint=fingerprint,
                    settings=settings,
                    rulebook=rulebook,
                    raw_json=raw_json,
                    error_type=ErrorCategory.BUSINESS_RULE.value
                    if any(e.startswith("business:") for e in validation.errors)
                    else ErrorCategory.VALIDATION.value,
                    error_message="; ".join(validation.errors),
                    status=LabelRunStatus.VALIDATION_FAILED,
                    provider=meta.provider,
                    model_name=meta.model_name,
                    request_id=meta.request_id,
                    parsed=raw_payload,
                )
                report.validation_failed += 1
                continue

            assert validation.label is not None
            now = utcnow()
            run = LabelRunRecord(
                run_id=run_id,
                image_id=image.image_id,
                rulebook_version=rulebook.version,
                prompt_version=settings.prompt_version,
                provider=meta.provider,
                model_name=meta.model_name,
                request_fingerprint=fingerprint,
                raw_response_json=raw_json,
                parsed_response_json=validation.label.model_dump(),
                status=LabelRunStatus.SUCCEEDED,
                error_type=None,
                error_message=None,
                created_at=now,
            )
            repo.save_label_run(run)
            record = CurationRecord(
                record_id=new_id("rec"),
                run_id=run_id,
                image_id=image.image_id,
                file_path=image.relative_path,
                sha256=image.sha256,
                source_type=image.source_type,
                source_url=image.source_url,
                usage_rights_status=image.usage_rights_status,
                rulebook_version=rulebook.version,
                prompt_version=settings.prompt_version,
                provider=meta.provider,
                model_name=meta.model_name,
                model_request_id=meta.request_id,
                draft_label=validation.label,
                final_label=None,
                raw_response_json=raw_json,
                validation_errors=[],
                review_warnings=validation.warnings,
                status=ReviewStatus.DRAFT,
                curator_name=None,
                curator_notes=None,
                created_at=now,
                updated_at=now,
                reviewed_at=None,
                approved_at=None,
            )
            repo.save_curation_record(record)
            report.labelled += 1
            logger.info(
                "label_success",
                extra={
                    "run_id": run_id,
                    "image_id": image.image_id,
                    "request_fingerprint": fingerprint,
                    "pipeline_stage": "label",
                    "latency": meta.latency_ms,
                    "attempt": meta.attempt,
                    "result_status": "draft",
                },
            )
        except ProviderError as exc:
            _persist_failure(
                repo=repo,
                image=image,
                run_id=run_id,
                fingerprint=fingerprint,
                settings=settings,
                rulebook=rulebook,
                raw_json=None,
                error_type=(
                    ErrorCategory.PROVIDER_TRANSIENT.value
                    if exc.transient
                    else ErrorCategory.PROVIDER_PERMANENT.value
                ),
                error_message=str(exc),
                status=LabelRunStatus.PROVIDER_FAILED,
                provider=settings.model_provider,
                model_name=settings.model_name,
                request_id=exc.request_id,
            )
            report.provider_failed += 1
        except Exception as exc:  # noqa: BLE001
            _persist_failure(
                repo=repo,
                image=image,
                run_id=run_id,
                fingerprint=fingerprint,
                settings=settings,
                rulebook=rulebook,
                raw_json=None,
                error_type=ErrorCategory.PROVIDER_PERMANENT.value,
                error_message=str(exc),
                status=LabelRunStatus.PROVIDER_FAILED,
                provider=settings.model_provider,
                model_name=settings.model_name,
                request_id=None,
            )
            report.provider_failed += 1

    report.elapsed_seconds = time.perf_counter() - started
    if latencies:
        report.average_latency_ms = sum(latencies) / len(latencies)
    return report


def retry_failures(
    *,
    repo: SqliteRepository,
    settings: AppSettings,
    failure_type: str,
    limit: int | None = None,
) -> BatchReport:
    failed = repo.list_failed_runs(failure_type=failure_type)
    image_ids = []
    seen: set[str] = set()
    for run in failed:
        if run.image_id in seen:
            continue
        seen.add(run.image_id)
        image_ids.append(run.image_id)
        if limit is not None and len(image_ids) >= limit:
            break
    return label_images(repo=repo, settings=settings, force=True, image_ids=image_ids)


def _persist_failure(
    *,
    repo: SqliteRepository,
    image,
    run_id: str,
    fingerprint: str,
    settings: AppSettings,
    rulebook: Rulebook,
    raw_json: str | None,
    error_type: str,
    error_message: str,
    status: LabelRunStatus,
    provider: str,
    model_name: str,
    request_id: str | None,
    parsed: dict | None = None,
) -> None:
    now = utcnow()
    run = LabelRunRecord(
        run_id=run_id,
        image_id=image.image_id,
        rulebook_version=rulebook.version,
        prompt_version=settings.prompt_version,
        provider=provider,
        model_name=model_name,
        request_fingerprint=fingerprint,
        raw_response_json=raw_json,
        parsed_response_json=parsed,
        status=status,
        error_type=error_type,
        error_message=error_message,
        created_at=now,
    )
    repo.save_label_run(run)
    if status == LabelRunStatus.VALIDATION_FAILED:
        record = CurationRecord(
            record_id=new_id("rec"),
            run_id=run_id,
            image_id=image.image_id,
            file_path=image.relative_path,
            sha256=image.sha256,
            source_type=image.source_type,
            source_url=image.source_url,
            usage_rights_status=image.usage_rights_status,
            rulebook_version=rulebook.version,
            prompt_version=settings.prompt_version,
            provider=provider,
            model_name=model_name,
            model_request_id=request_id,
            draft_label=None,
            final_label=None,
            raw_response_json=raw_json,
            validation_errors=[error_message],
            review_warnings=[],
            status=ReviewStatus.VALIDATION_FAILED,
            curator_name=None,
            curator_notes=None,
            created_at=now,
            updated_at=now,
            reviewed_at=None,
            approved_at=None,
        )
        repo.save_curation_record(record)

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml
from jinja2 import Template
from PIL import Image

from vision_engine.concept_board.domain.enums import CandidateStatus, SubstitutionPreviewStatus
from vision_engine.concept_board.domain.models import (
    ProductRecord,
    ProductVariantRecord,
    RegionGeometryRecord,
    SubstitutionPreviewRecord,
)
from vision_engine.domain.models import ModelCallMetadata
from vision_engine.infrastructure.file_store import FileStore, new_id, sha256_file
from vision_engine.infrastructure.image_edit_clients import build_image_edit_client
from vision_engine.infrastructure.sqlite_repository import utcnow
from vision_engine.settings import AppSettings
from vision_engine.virtual_staging.application.masks import (
    apply_fake_product_staging,
    normalised_bbox,
    write_product_reference_card,
    write_region_mask_png,
)
from vision_engine.virtual_staging.domain.enums import (
    EvidenceGrade,
    ImageEditRunStatus,
    StagingConditionType,
    StagingMode,
    StagingRequestStatus,
    VirtualStagingOutputType,
)
from vision_engine.virtual_staging.domain.errors import StagingError
from vision_engine.virtual_staging.domain.models import (
    ImageEditRunRecord,
    StagingConditionRecord,
    StagingRequestRecord,
    VirtualStagingOutputRecord,
)


class StagingRepository(Protocol):
    def get_region_candidate(self, region_candidate_id: str): ...

    def get_concept_version(self, concept_version_id: str): ...

    def get_primary_concept_asset(self, concept_version_id: str): ...

    def get_design_region(self, design_region_id: str): ...

    def get_region_geometry_for_version(
        self, design_region_id: str, concept_version_id: str
    ) -> RegionGeometryRecord | None: ...

    def get_product_variant_details(
        self, product_variant_id: str
    ) -> tuple[ProductRecord, ProductVariantRecord] | None: ...

    def save_region_candidate(self, record) -> None: ...

    def save_substitution_preview(self, record: SubstitutionPreviewRecord) -> None: ...

    def save_staging_request(self, record: StagingRequestRecord) -> None: ...

    def save_staging_condition(self, record: StagingConditionRecord) -> None: ...

    def save_image_edit_run(self, record: ImageEditRunRecord) -> None: ...

    def save_virtual_staging_output(self, record: VirtualStagingOutputRecord) -> None: ...

    def ensure_prompt_version(self, version: str, content_hash: str) -> None: ...

    def ensure_model_version(self, provider: str, model_name: str, task: str) -> None: ...


@dataclass(frozen=True)
class ProductStagingResult:
    substitution_preview: SubstitutionPreviewRecord
    staging_request: StagingRequestRecord
    staging_output: VirtualStagingOutputRecord


def _dimensions_text(variant: ProductVariantRecord) -> str | None:
    parts: list[str] = []
    if variant.width_mm is not None:
        parts.append(f"W {variant.width_mm:.0f} mm")
    if variant.height_mm is not None:
        parts.append(f"H {variant.height_mm:.0f} mm")
    if variant.depth_mm is not None:
        parts.append(f"D {variant.depth_mm:.0f} mm")
    return " × ".join(parts) if parts else None


def _prompt_config(settings: AppSettings) -> dict[str, Any]:
    if settings.prompts_config_path.exists():
        return yaml.safe_load(settings.prompts_config_path.read_text(encoding="utf-8")) or {}
    return {}


def build_product_staging_prompt(
    *,
    settings: AppSettings,
    region_code: str,
    region_type: str,
    display_name: str,
    geometry_json: dict[str, Any],
    product: ProductRecord,
    variant: ProductVariantRecord,
    unit_price: float | None,
) -> str:
    template = Template(settings.product_staging_prompt_path.read_text(encoding="utf-8"))
    prompts_cfg = _prompt_config(settings)
    x, y, width, height = normalised_bbox(geometry_json)
    return template.render(
        region_code=region_code,
        region_type=region_type,
        display_name=display_name,
        bbox={"x": x, "y": y, "width": width, "height": height},
        product_name=product.canonical_name,
        brand_name=product.brand_name,
        product_type=product.product_type,
        colour=variant.colour,
        finish=variant.finish,
        material=variant.material,
        dimensions_text=_dimensions_text(variant),
        unit_price=f"£{unit_price:.2f}" if unit_price is not None else None,
        geometry_lock=prompts_cfg.get("geometry_lock", ""),
        negative_constraints=prompts_cfg.get("negative_constraints", []),
    )


def _relative_uri(settings: AppSettings, path: Path) -> str:
    return str(path.relative_to(settings.project_root))


def _download_remote_image(url: str, dest: Path, *, timeout_seconds: int = 30) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "vision-engine/1.0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            dest.write_bytes(response.read())
    except URLError as exc:
        raise StagingError(f"Failed to download product image: {url}") from exc
    return dest


def _resolve_product_reference(
    *,
    settings: AppSettings,
    staging_dir: Path,
    product: ProductRecord,
    variant: ProductVariantRecord,
    attributes: dict[str, Any],
    product_image_uri: str | None = None,
) -> tuple[Path, str, dict[str, Any]]:
    image_uri = (
        product_image_uri
        or attributes.get("reference_image_uri")
        or attributes.get("image_uri")
    )
    if image_uri:
        if str(image_uri).startswith(("http://", "https://")):
            dest = staging_dir / "conditions" / "product_reference_download.png"
            _download_remote_image(
                str(image_uri),
                dest,
                timeout_seconds=settings.inference.timeout_seconds,
            )
            return dest, sha256_file(dest), {"source": "remote_catalogue_image", "uri": image_uri}
        candidate = settings.resolve(image_uri)
        if candidate.exists():
            return candidate, sha256_file(candidate), {"source": "catalogue_image", "uri": image_uri}

    card_path = staging_dir / "conditions" / "product_reference.png"
    write_product_reference_card(
        product_name=product.canonical_name,
        brand_name=product.brand_name,
        dimensions_text=_dimensions_text(variant),
        dest=card_path,
    )
    return card_path, sha256_file(card_path), {"source": "generated_reference_card"}


def run_2d_product_staging(
    *,
    repo: StagingRepository,
    settings: AppSettings,
    file_store: FileStore,
    region_candidate_id: str,
    concept_version_id: str,
    provider: str | None = None,
    model_name: str | None = None,
    prompt_version: str | None = None,
    product_image_uri: str | None = None,
    source_image_path: Path | None = None,
    chain_step: int | None = None,
    cumulative_mode: str = "single",
    cumulative_layer_count: int = 1,
    preview_candidate_id: str | None = None,
) -> ProductStagingResult:
    candidate = repo.get_region_candidate(region_candidate_id)
    if candidate is None:
        raise StagingError(f"Candidate not found: {region_candidate_id}")

    version = repo.get_concept_version(concept_version_id)
    if version is None:
        raise StagingError(f"Concept version not found: {concept_version_id}")

    region = repo.get_design_region(candidate.design_region_id)
    if region is None:
        raise StagingError("Design region not found")

    geometry = repo.get_region_geometry_for_version(
        candidate.design_region_id, concept_version_id
    )
    if geometry is None:
        raise StagingError(
            "Region geometry is required for 2D staging. Add a bounding box or mask first."
        )

    product_details = None
    unit_price = candidate.match_rationale_json.get("unit_price")
    if candidate.product_variant_id:
        product_details = repo.get_product_variant_details(candidate.product_variant_id)
    if product_details is None:
        raise StagingError("Product variant details are required for 2D staging")

    product, variant = product_details
    asset = repo.get_primary_concept_asset(concept_version_id)
    if asset is None:
        raise StagingError("Primary concept asset not found")

    provider_name = (provider or settings.model_provider).lower()
    model = model_name or settings.image_edit_model
    prompt_ver = prompt_version or settings.product_staging_prompt_version
    disclaimer = settings.virtual_staging.visual_preview_disclaimer
    now = utcnow()

    staging_dir = (
        settings.resolve(settings.paths.staging)
        / version.concept_direction_id
        / region_candidate_id
    )
    if chain_step is not None:
        staging_dir = staging_dir / f"chain_{chain_step:02d}"
    if cumulative_mode == "local_composite":
        staging_dir = staging_dir / "cumulative_local"
    conditions_dir = staging_dir / "conditions"
    outputs_dir = staging_dir / "outputs"
    conditions_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    source_path = source_image_path or settings.resolve(asset.storage_uri)
    with Image.open(source_path) as img:
        image_size = img.size

    mask_path = conditions_dir / "region_mask.png"
    write_region_mask_png(image_size=image_size, geometry_json=geometry.geometry_json, dest=mask_path)
    mask_sha256 = sha256_file(mask_path)

    reference_path, reference_sha256, reference_meta = _resolve_product_reference(
        settings=settings,
        staging_dir=staging_dir,
        product=product,
        variant=variant,
        attributes=variant.attributes_json,
        product_image_uri=product_image_uri,
    )

    prompt = build_product_staging_prompt(
        settings=settings,
        region_code=region.region_code,
        region_type=region.region_type,
        display_name=region.display_name,
        geometry_json=geometry.geometry_json,
        product=product,
        variant=variant,
        unit_price=float(unit_price) if unit_price is not None else None,
    )
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    repo.ensure_prompt_version(prompt_ver, prompt_hash)
    repo.ensure_model_version(provider_name, model, "product_staging")

    request_id = new_id("sr")
    staging_request = StagingRequestRecord(
        staging_request_id=request_id,
        concept_version_id=concept_version_id,
        design_region_id=region.design_region_id,
        region_candidate_id=region_candidate_id,
        staging_mode=StagingMode.IMAGE_EDIT_2D,
        requested_quality_level="mvp",
        status=StagingRequestStatus.RUNNING,
        disclaimer=disclaimer,
        created_at=now,
    )
    repo.save_staging_request(staging_request)

    for condition_type, artifact_json, content_sha256 in (
        (
            StagingConditionType.SOURCE_CONCEPT,
            {"uri": asset.storage_uri, "sha256": asset.asset_sha256},
            asset.asset_sha256,
        ),
        (
            StagingConditionType.REGION_MASK,
            {"uri": _relative_uri(settings, mask_path), "geometry": geometry.geometry_json},
            mask_sha256,
        ),
        (
            StagingConditionType.PRODUCT_REFERENCE,
            {"uri": _relative_uri(settings, reference_path), **reference_meta},
            reference_sha256,
        ),
        (
            StagingConditionType.PROMPT,
            {"prompt_version": prompt_ver, "sha256": prompt_hash},
            prompt_hash,
        ),
    ):
        repo.save_staging_condition(
            StagingConditionRecord(
                staging_condition_id=new_id("sc"),
                staging_request_id=request_id,
                condition_type=condition_type,
                artifact_reference_json=artifact_json,
                content_sha256=content_sha256,
                created_at=now,
            )
        )

    request_manifest = {
        "staging_request_id": request_id,
        "concept_version_id": concept_version_id,
        "region_candidate_id": region_candidate_id,
        "source_concept_sha256": sha256_file(source_path),
        "region_mask_sha256": mask_sha256,
        "product_reference_sha256": reference_sha256,
        "prompt_sha256": prompt_hash,
        "provider": provider_name,
        "model_name": model,
        "evidence_grade": EvidenceGrade.VISUAL_PREVIEW_ONLY.value,
        "cumulative_mode": cumulative_mode,
        "cumulative_layer_count": cumulative_layer_count,
        "chain_step": chain_step,
    }
    manifest_path = conditions_dir / "request_manifest.json"
    manifest_text = json.dumps(request_manifest, indent=2, sort_keys=True)
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_sha256 = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()

    edit_run_id = new_id("ier")
    output_path = outputs_dir / f"{edit_run_id}.png"
    meta: ModelCallMetadata

    if provider_name == "fake":
        apply_fake_product_staging(
            room_image_path=source_path,
            geometry_json=geometry.geometry_json,
            product_name=product.canonical_name,
            dest=output_path,
            disclaimer=disclaimer,
        )
        meta = ModelCallMetadata(
            provider="fake",
            model_name=model,
            latency_ms=1,
            attempt=1,
        )
    else:
        client = build_image_edit_client(
            provider=provider_name,
            api_key=settings.gemini_api_key,
            model_name=model,
            file_store=file_store,
            timeout_seconds=settings.inference.timeout_seconds,
            max_attempts=settings.inference.max_attempts,
            temperature=settings.inference.image_edit_temperature,
        )
        paths, meta = client.edit_room(
            room_image_path=source_path,
            reference_image_paths=[reference_path],
            design_direction={"product_name": product.canonical_name},
            output_count=1,
            prompts=[prompt],
            project_id=version.concept_direction_id,
        )
        generated = Path(paths[0])
        output_path.write_bytes(generated.read_bytes())

    output_sha256 = sha256_file(output_path)
    provenance_payload = {
        **request_manifest,
        "image_edit_run_id": edit_run_id,
        "output_sha256": output_sha256,
        "latency_ms": meta.latency_ms,
    }
    provenance_path = outputs_dir / f"{edit_run_id}_provenance.json"
    provenance_uri = _relative_uri(settings, provenance_path)
    provenance_path.write_text(
        json.dumps(provenance_payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    provenance_sha256 = sha256_file(provenance_path)

    repo.save_image_edit_run(
        ImageEditRunRecord(
            image_edit_run_id=edit_run_id,
            staging_request_id=request_id,
            provider=meta.provider,
            model_name=meta.model_name,
            model_version=model,
            prompt_version=prompt_ver,
            request_manifest_sha256=manifest_sha256,
            status=ImageEditRunStatus.COMPLETED,
            latency_ms=meta.latency_ms,
            created_at=now,
        )
    )

    output_id = new_id("vso")
    staging_output = VirtualStagingOutputRecord(
        virtual_staging_output_id=output_id,
        staging_request_id=request_id,
        image_edit_run_id=edit_run_id,
        output_type=VirtualStagingOutputType.PREVIEW_IMAGE,
        storage_uri=_relative_uri(settings, output_path),
        output_sha256=output_sha256,
        provenance_manifest_uri=provenance_uri,
        provenance_manifest_sha256=provenance_sha256,
        evidence_grade=EvidenceGrade.VISUAL_PREVIEW_ONLY,
        status="generated",
        created_at=now,
    )
    repo.save_virtual_staging_output(staging_output)

    repo.save_staging_request(
        staging_request.model_copy(update={"status": StagingRequestStatus.COMPLETED})
    )

    preview = SubstitutionPreviewRecord(
        substitution_preview_id=new_id("sp"),
        concept_version_id=concept_version_id,
        region_candidate_id=preview_candidate_id or region_candidate_id,
        preview_asset_uri=_relative_uri(settings, output_path),
        preview_asset_sha256=output_sha256,
        generation_provider=meta.provider,
        generation_model=meta.model_name,
        prompt_version=prompt_ver,
        status=SubstitutionPreviewStatus.GENERATED,
        virtual_staging_output_id=output_id,
        evidence_grade=EvidenceGrade.VISUAL_PREVIEW_ONLY,
        disclaimer=disclaimer,
        created_at=now,
    )
    repo.save_substitution_preview(preview)

    updated_candidate = candidate.model_copy(
        update={"candidate_status": CandidateStatus.PREVIEW_GENERATED}
    )
    repo.save_region_candidate(updated_candidate)

    return ProductStagingResult(
        substitution_preview=preview,
        staging_request=staging_request.model_copy(
            update={"status": StagingRequestStatus.COMPLETED}
        ),
        staging_output=staging_output,
    )


def persist_cumulative_local_preview(
    *,
    repo: StagingRepository,
    settings: AppSettings,
    region_candidate_id: str,
    concept_version_id: str,
    output_path: Path,
    cumulative_layer_count: int,
) -> ProductStagingResult:
    candidate = repo.get_region_candidate(region_candidate_id)
    if candidate is None:
        raise StagingError(f"Candidate not found: {region_candidate_id}")
    version = repo.get_concept_version(concept_version_id)
    if version is None:
        raise StagingError(f"Concept version not found: {concept_version_id}")

    now = utcnow()
    disclaimer = settings.virtual_staging.visual_preview_disclaimer
    output_sha256 = sha256_file(output_path)
    request_id = new_id("sr")
    staging_request = StagingRequestRecord(
        staging_request_id=request_id,
        concept_version_id=concept_version_id,
        design_region_id=candidate.design_region_id,
        region_candidate_id=region_candidate_id,
        staging_mode=StagingMode.IMAGE_EDIT_2D,
        requested_quality_level="mvp",
        status=StagingRequestStatus.COMPLETED,
        disclaimer=disclaimer,
        created_at=now,
    )
    repo.save_staging_request(staging_request)

    manifest = {
        "staging_request_id": request_id,
        "concept_version_id": concept_version_id,
        "region_candidate_id": region_candidate_id,
        "cumulative_mode": "local_composite",
        "cumulative_layer_count": cumulative_layer_count,
        "output_sha256": output_sha256,
    }
    staging_dir = output_path.parent
    manifest_path = staging_dir / f"{output_path.stem}_provenance.json"
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True)
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_sha256 = hashlib.sha256(manifest_text.encode("utf-8")).hexdigest()

    edit_run_id = new_id("ier")
    repo.save_image_edit_run(
        ImageEditRunRecord(
            image_edit_run_id=edit_run_id,
            staging_request_id=request_id,
            provider="local_composite",
            model_name="pil-multi-mask",
            model_version="cumulative_local",
            prompt_version="cumulative_local",
            request_manifest_sha256=manifest_sha256,
            status=ImageEditRunStatus.COMPLETED,
            latency_ms=0,
            created_at=now,
        )
    )
    output_id = new_id("vso")
    staging_output = VirtualStagingOutputRecord(
        virtual_staging_output_id=output_id,
        staging_request_id=request_id,
        image_edit_run_id=edit_run_id,
        output_type=VirtualStagingOutputType.PREVIEW_IMAGE,
        storage_uri=_relative_uri(settings, output_path),
        output_sha256=output_sha256,
        provenance_manifest_uri=_relative_uri(settings, manifest_path),
        provenance_manifest_sha256=sha256_file(manifest_path),
        evidence_grade=EvidenceGrade.VISUAL_PREVIEW_ONLY,
        status="generated",
        created_at=now,
    )
    repo.save_virtual_staging_output(staging_output)

    preview = SubstitutionPreviewRecord(
        substitution_preview_id=new_id("sp"),
        concept_version_id=concept_version_id,
        region_candidate_id=region_candidate_id,
        preview_asset_uri=_relative_uri(settings, output_path),
        preview_asset_sha256=output_sha256,
        generation_provider="local_composite",
        generation_model="pil-multi-mask",
        prompt_version="cumulative_local",
        status=SubstitutionPreviewStatus.GENERATED,
        virtual_staging_output_id=output_id,
        evidence_grade=EvidenceGrade.VISUAL_PREVIEW_ONLY,
        disclaimer=disclaimer,
        created_at=now,
    )
    repo.save_substitution_preview(preview)
    repo.save_region_candidate(
        candidate.model_copy(update={"candidate_status": CandidateStatus.PREVIEW_GENERATED})
    )
    return ProductStagingResult(
        substitution_preview=preview,
        staging_request=staging_request,
        staging_output=staging_output,
    )

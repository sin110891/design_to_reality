from __future__ import annotations

from vision_engine.concept_board.application.channel3_catalogue import (
    import_channel3_snapshot_for_region,
    refresh_channel3_product_offer,
)
from vision_engine.concept_board.domain.enums import (
    CandidateSource,
    CandidateStatus,
    CatalogueSnapshotStatus,
    ScoreType,
)
from vision_engine.concept_board.domain.errors import RetrievalError
from vision_engine.concept_board.domain.models import (
    CandidateScoreRecord,
    ProductRetrievalRunRecord,
    RegionCandidateRecord,
)
from vision_engine.concept_board.domain.validation import (
    assert_confirmed_region,
    assert_sealed_snapshot,
    product_types_for_region,
)
from vision_engine.concept_board.infrastructure.repository import ConceptBoardRepositoryMixin
from vision_engine.infrastructure.file_store import new_id
from vision_engine.infrastructure.sqlite_repository import utcnow
from vision_engine.settings import AppSettings


def _score_candidate(
    *,
    region_type: str,
    product_type: str,
    unit_price: float,
    max_budget: float | None,
    attributes: dict,
) -> tuple[float, dict]:
    allowed = product_types_for_region(region_type)
    type_score = 1.0 if product_type.lower() in allowed else 0.2
    region_types = attributes.get("region_types") or []
    region_match = 1.0 if region_type in region_types or not region_types else 0.5
    budget_score = 1.0
    if max_budget is not None and unit_price > max_budget:
        budget_score = max(0.0, 1.0 - (unit_price - max_budget) / max(max_budget, 1.0))
    overall = 0.5 * type_score + 0.3 * region_match + 0.2 * budget_score
    return overall, {
        "type_score": type_score,
        "region_match": region_match,
        "budget_score": budget_score,
    }


def _resolve_snapshot(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings | None,
    design_region_id: str,
    region,
    catalogue_snapshot_id: str | None,
    use_channel3: bool | None,
    max_budget: float | None,
) -> str:
    if catalogue_snapshot_id:
        return catalogue_snapshot_id

    should_use_channel3 = use_channel3
    if should_use_channel3 is None and settings is not None:
        should_use_channel3 = settings.catalogue_provider == "channel3"

    if should_use_channel3:
        if settings is None:
            raise RetrievalError("Channel3 retrieval requires application settings")
        snapshot, _rows = import_channel3_snapshot_for_region(
            repo=repo,
            settings=settings,
            design_region_id=design_region_id,
            region_type=region.region_type,
            display_name=region.display_name,
            max_budget=max_budget,
            snapshot_name=None,
        )
        return snapshot.catalogue_snapshot_id

    snapshot = repo.get_active_sealed_snapshot()
    if snapshot is None:
        raise RetrievalError("No sealed catalogue snapshot available")
    return snapshot.catalogue_snapshot_id


def retrieve_product_candidates(
    *,
    repo: ConceptBoardRepositoryMixin,
    design_region_id: str,
    concept_version_id: str,
    catalogue_snapshot_id: str | None = None,
    top_k: int = 10,
    max_budget: float | None = None,
    settings: AppSettings | None = None,
    use_channel3: bool | None = None,
) -> tuple[ProductRetrievalRunRecord, list[RegionCandidateRecord]]:
    region = repo.get_design_region(design_region_id)
    if region is None:
        raise RetrievalError(f"Region not found: {design_region_id}")
    assert_confirmed_region(region.lifecycle_status, "product retrieval")

    requirements = repo.list_region_requirements(design_region_id)
    for req in requirements:
        if req.requirement_type == "budget" and req.operator == "<=":
            max_budget = float(req.value_json.get("amount", max_budget or 0)) or max_budget

    resolved_snapshot_id = _resolve_snapshot(
        repo=repo,
        settings=settings,
        design_region_id=design_region_id,
        region=region,
        catalogue_snapshot_id=catalogue_snapshot_id,
        use_channel3=use_channel3,
        max_budget=max_budget,
    )

    snapshot = repo.get_catalogue_snapshot(resolved_snapshot_id)
    if snapshot is None:
        raise RetrievalError(f"Catalogue snapshot not found: {resolved_snapshot_id}")
    assert_sealed_snapshot(snapshot.status, "product retrieval")

    now = utcnow()
    candidate_source = (
        CandidateSource.CHANNEL3_SEARCH
        if snapshot.manifest_uri.startswith("channel3://")
        else CandidateSource.RULE_MATCH
    )
    run = ProductRetrievalRunRecord(
        product_retrieval_run_id=new_id("prr"),
        design_region_id=design_region_id,
        concept_version_id=concept_version_id,
        catalogue_snapshot_id=snapshot.catalogue_snapshot_id,
        query_context_json={
            "region_type": region.region_type,
            "max_budget": max_budget,
            "requirements": [r.model_dump(mode="json") for r in requirements],
            "catalogue_source": snapshot.manifest_uri,
        },
        top_k=top_k,
        created_at=now,
    )
    repo.save_product_retrieval_run(run)

    catalogue_rows = repo.list_snapshot_product_variants(snapshot.catalogue_snapshot_id)
    scored: list[tuple[float, RegionCandidateRecord, dict]] = []

    for product, variant, offer, supplier in catalogue_rows:
        score, explanation = _score_candidate(
            region_type=region.region_type,
            product_type=product.product_type,
            unit_price=offer.unit_price,
            max_budget=max_budget,
            attributes=variant.attributes_json,
        )
        candidate = RegionCandidateRecord(
            region_candidate_id=new_id("rc"),
            design_region_id=design_region_id,
            product_retrieval_run_id=run.product_retrieval_run_id,
            product_variant_id=variant.product_variant_id,
            catalogue_snapshot_id=snapshot.catalogue_snapshot_id,
            candidate_source=candidate_source,
            candidate_status=CandidateStatus.SHORTLISTED,
            match_rationale_json={
                "product_name": product.canonical_name,
                "supplier_name": supplier.supplier_name,
                "unit_price": offer.unit_price,
                "reference_image_uri": variant.attributes_json.get("reference_image_uri"),
                "product_images": variant.attributes_json.get("product_images")
                or (
                    [{"url": variant.attributes_json["reference_image_uri"], "is_cleaned_image": True}]
                    if variant.attributes_json.get("reference_image_uri")
                    else []
                ),
                "buy_url": offer.buy_url or variant.attributes_json.get("buy_url"),
                "external_provider": product.external_provider,
                "external_product_id": product.external_product_id,
                "explanation": explanation,
            },
            created_at=now,
        )
        scored.append((score, candidate, explanation))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[RegionCandidateRecord] = []
    for score, candidate, explanation in scored[:top_k]:
        repo.save_region_candidate(candidate)
        repo.save_candidate_score(
            CandidateScoreRecord(
                candidate_score_id=new_id("cs"),
                region_candidate_id=candidate.region_candidate_id,
                score_type=ScoreType.OVERALL_RERANKER,
                raw_score=score,
                normalised_score=min(1.0, max(0.0, score)),
                explanation_json=explanation,
                created_at=now,
            )
        )
        results.append(candidate)
    return run, results


def maybe_refresh_channel3_candidate(
    *,
    repo: ConceptBoardRepositoryMixin,
    settings: AppSettings,
    region_candidate_id: str,
) -> None:
    candidate = repo.get_region_candidate(region_candidate_id)
    if candidate is None or candidate.product_variant_id is None:
        return
    product_details = repo.get_product_variant_details(candidate.product_variant_id)
    if product_details is None:
        return
    product, _variant = product_details
    if product.external_provider != "channel3":
        return
    refresh_channel3_product_offer(
        repo=repo,
        settings=settings,
        product_variant_id=candidate.product_variant_id,
    )

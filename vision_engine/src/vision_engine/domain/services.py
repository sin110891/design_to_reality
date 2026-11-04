from __future__ import annotations

from typing import Iterable

from vision_engine.domain.models import DatasetRecord, ProjectInput, RetrievedReference


def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(dot / (na * nb))


def metadata_match_score(query: ProjectInput, record: DatasetRecord) -> float:
    """Soft metadata compatibility in [0, 1]."""
    checks: list[float] = []

    if query.room_type and record.room_type:
        checks.append(1.0 if query.room_type == record.room_type else 0.15)
    if query.style_family and record.style_family:
        checks.append(1.0 if query.style_family == record.style_family else 0.2)
    if query.budget_band and record.budget_band:
        checks.append(1.0 if query.budget_band == record.budget_band else 0.35)
    if query.project_type and record.project_type:
        checks.append(1.0 if query.project_type == record.project_type else 0.4)

    # Brief token overlap with mood / materials / lighting text
    brief_tokens = {t.lower() for t in query.brief.replace(",", " ").split() if len(t) > 3}
    if brief_tokens:
        corpus = " ".join(
            [
                " ".join(record.mood),
                " ".join(record.material_palette),
                record.lighting_strategy or "",
                record.positive_why_it_works or "",
                record.furniture_style or "",
            ]
        ).lower()
        hits = sum(1 for t in brief_tokens if t in corpus)
        checks.append(min(1.0, hits / max(3, len(brief_tokens) * 0.35)))

    if not checks:
        return 0.5
    return sum(checks) / len(checks)


def hybrid_score(
    *,
    image_similarity: float,
    text_similarity: float,
    metadata_match: float,
    architect_quality: float,
    image_weight: float,
    text_weight: float,
    metadata_weight: float,
    quality_weight: float,
) -> float:
    quality_norm = max(0.0, min(1.0, (architect_quality - 1.0) / 4.0))
    return (
        image_weight * image_similarity
        + text_weight * text_similarity
        + metadata_weight * metadata_match
        + quality_weight * quality_norm
    )


def passes_hard_filters(query: ProjectInput, record: DatasetRecord) -> bool:
    """Hard filters: only approved records; soft-prefer matching room/style."""
    if record.review_status.value != "approved":
        return False
    if record.usage_rights_status == "restricted":
        return False
    return True


def soft_filter_penalty(query: ProjectInput, record: DatasetRecord) -> float:
    """Return a multiplier in (0, 1] for soft mismatches."""
    penalty = 1.0
    if query.room_type and record.room_type and query.room_type != record.room_type:
        penalty *= 0.55
    if query.style_family and record.style_family and query.style_family != record.style_family:
        penalty *= 0.4
    if query.budget_band and record.budget_band and query.budget_band != record.budget_band:
        # Adjacent bands are milder
        order = ["low", "medium", "medium_high", "high"]
        try:
            dist = abs(order.index(query.budget_band) - order.index(record.budget_band))
            penalty *= max(0.45, 1.0 - 0.2 * dist)
        except ValueError:
            penalty *= 0.7
    return penalty


def diversify_references(
    candidates: list[RetrievedReference],
    *,
    final_k: int = 3,
) -> list[RetrievedReference]:
    """
    Enforce diversity: 1 direct match, 1 material/lighting, 1 composition/spatial.
    Falls back to score order when roles cannot be filled uniquely.
    """
    if len(candidates) <= final_k:
        for i, ref in enumerate(candidates):
            ref.diversity_role = ["direct_match", "material_lighting", "composition_spatial"][i] if i < 3 else "extra"
        return candidates

    selected: list[RetrievedReference] = []
    used_ids: set[str] = set()

    def take(role: str, predicate) -> None:
        for ref in candidates:
            if ref.image_id in used_ids:
                continue
            if predicate(ref):
                ref.diversity_role = role
                selected.append(ref)
                used_ids.add(ref.image_id)
                return

    # Direct: highest overall score
    take("direct_match", lambda r: True)

    # Material / lighting: overlapping materials or lighting text
    seed = selected[0].record if selected else None

    def material_fit(ref: RetrievedReference) -> bool:
        if not seed:
            return True
        overlap = set(ref.record.material_palette) & set(seed.material_palette)
        lighting_hit = bool(
            seed.lighting_strategy
            and ref.record.lighting_strategy
            and (
                seed.lighting_strategy.lower()[:40] in ref.record.lighting_strategy.lower()
                or any(
                    tok in (ref.record.lighting_strategy or "").lower()
                    for tok in (seed.lighting_strategy or "").lower().split()
                    if len(tok) > 4
                )
            )
        )
        return bool(overlap) or lighting_hit

    take("material_lighting", material_fit)

    # Composition / spatial: different focal or hierarchy text
    def composition_fit(ref: RetrievedReference) -> bool:
        if not seed:
            return True
        if ref.record.focal_point and seed.focal_point:
            return ref.record.focal_point.strip().lower() != seed.focal_point.strip().lower()
        if ref.record.visual_hierarchy and seed.visual_hierarchy:
            return ref.record.visual_hierarchy.strip().lower() != seed.visual_hierarchy.strip().lower()
        # Prefer lower image similarity to the top pick (more compositional variety proxy)
        return ref.image_similarity < (selected[0].image_similarity - 0.02 if selected else 1.0)

    take("composition_spatial", composition_fit)

    for ref in candidates:
        if len(selected) >= final_k:
            break
        if ref.image_id not in used_ids:
            ref.diversity_role = "extra"
            selected.append(ref)
            used_ids.add(ref.image_id)

    return selected[:final_k]


def build_match_rationale(
    *,
    image_similarity: float,
    text_similarity: float,
    metadata_match: float,
    architect_quality: float,
    record: DatasetRecord,
) -> str:
    parts = [
        f"image={image_similarity:.2f}",
        f"text={text_similarity:.2f}",
        f"metadata={metadata_match:.2f}",
        f"quality={architect_quality:.1f}/5",
    ]
    if record.room_type:
        parts.append(f"room={record.room_type}")
    if record.style_family:
        parts.append(f"style={record.style_family}")
    if record.material_palette:
        parts.append("materials=" + ",".join(record.material_palette[:3]))
    return "; ".join(parts)


def build_text_blob(record: DatasetRecord) -> str:
    chunks: Iterable[str | None] = [
        record.style_family,
        " ".join(record.expert_style_family),
        record.room_type,
        record.project_type,
        record.image_type,
        record.geography,
        record.budget_band,
        record.build_complexity,
        record.maintenance_level,
        record.furniture_style,
        record.colour_scheme,
        record.lighting_strategy,
        record.positive_why_it_works,
        record.negative_common_pitfalls,
        record.focal_point,
        record.circulation_strategy,
        record.visual_hierarchy,
        record.proportion_rule,
        record.material_relationship,
        " ".join(record.mood),
        " ".join(record.colour_palette),
        " ".join(record.material_palette),
        " ".join(record.material_floor),
        " ".join(record.material_wall),
        " ".join(record.material_furniture),
        " ".join(record.material_ceiling),
        " ".join(record.spatial_feel),
        " ".join(record.likely_trades_required),
        " ".join(record.secondary_trades),
        " ".join(record.appropriate_room_conditions),
    ]
    return " | ".join(c for c in chunks if c)

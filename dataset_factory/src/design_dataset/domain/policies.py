from __future__ import annotations

import re
from dataclasses import dataclass, field

from design_dataset.domain.errors import ValidationPolicyError
from design_dataset.domain.models import DesignLabelDraft
from design_dataset.domain.rulebook import Rulebook


@dataclass
class ValidationResult:
    label: DesignLabelDraft | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.label is not None and not self.errors


_STRUCTURAL_CLAIM_PATTERNS = [
    re.compile(r"\bload[- ]bearing\b", re.I),
    re.compile(r"\bstructural (wall|beam|column|integrity)\b", re.I),
    re.compile(r"\bwithout (planning|building) permission\b", re.I),
    re.compile(r"\bhidden (pipe|wiring|services)\b", re.I),
]


def normalize_label(draft: DesignLabelDraft) -> DesignLabelDraft:
    data = draft.model_dump()
    data["style_family"] = data["style_family"].strip()
    data["budget_band"] = data["budget_band"].strip().lower()
    data["primary_trade"] = data["primary_trade"].strip().lower()
    data["mood"] = _dedupe_preserve([m.strip().lower() for m in data["mood"]])
    data["material_palette"] = _dedupe_preserve(
        [m.strip().lower() for m in data["material_palette"]]
    )
    data["likely_trades_required"] = _dedupe_preserve(
        [t.strip().lower() for t in data["likely_trades_required"]]
    )
    if data.get("room_type"):
        data["room_type"] = data["room_type"].strip().lower()
    data["confidence_notes"] = data["confidence_notes"].strip()
    data["visible_uncertainties"] = [
        u.strip() for u in data.get("visible_uncertainties", []) if u and u.strip()
    ]
    return DesignLabelDraft.model_validate(data)


def validate_against_rulebook(
    draft: DesignLabelDraft,
    rulebook: Rulebook,
    *,
    raise_on_error: bool = False,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        label = normalize_label(draft)
    except Exception as exc:  # noqa: BLE001
        result = ValidationResult(label=None, errors=[f"syntax: {exc}"])
        if raise_on_error:
            raise ValidationPolicyError("; ".join(result.errors)) from exc
        return result

    _check_single(label.style_family, "style_family", rulebook, errors)
    _check_multi(label.mood, "mood", rulebook, errors)
    _check_multi(label.material_palette, "material_palette", rulebook, errors)
    _check_single(label.budget_band, "budget_band", rulebook, errors)
    _check_single(label.primary_trade, "primary_trade", rulebook, errors)
    _check_multi(label.likely_trades_required, "likely_trades_required", rulebook, errors)
    if label.room_type:
        _check_single(label.room_type, "room_type", rulebook, errors)

    if label.primary_trade not in label.likely_trades_required:
        errors.append("business: primary_trade must appear in likely_trades_required")

    specialist = {"joiner", "tiler", "electrician", "plumber", "plasterer"}
    specialists_present = specialist.intersection(label.likely_trades_required)
    if label.budget_band == "low" and len(specialists_present) >= 3:
        warnings.append(
            "review: budget_band=low with multiple specialist trades may be inconsistent"
        )

    pos = (label.positive.why_it_works or "").strip().lower()
    neg = (label.negative.why_it_fails or "").strip().lower()
    if pos and neg and _near_duplicate(pos, neg):
        errors.append("business: positive.why_it_works and negative.why_it_fails are near-duplicates")

    text_blob = " ".join(
        [
            label.confidence_notes,
            label.positive.why_it_works,
            label.negative.why_it_fails,
            label.negative.structural_violation or "",
            *label.visible_uncertainties,
        ]
    )
    for pattern in _STRUCTURAL_CLAIM_PATTERNS:
        if pattern.search(text_blob):
            warnings.append(
                "review: text appears to make structural or hidden-condition claims from image evidence"
            )
            break

    result = ValidationResult(label=label if not errors else None, errors=errors, warnings=warnings)
    if raise_on_error and errors:
        raise ValidationPolicyError("; ".join(errors))
    return result


def _check_single(value: str, field_name: str, rulebook: Rulebook, errors: list[str]) -> None:
    allowed = rulebook.allowed(field_name)
    if value not in allowed:
        errors.append(f"vocabulary: {field_name}={value!r} not in rulebook")


def _check_multi(values: list[str], field_name: str, rulebook: Rulebook, errors: list[str]) -> None:
    field = rulebook.fields[field_name]
    if field.min_items is not None and len(values) < field.min_items:
        errors.append(f"vocabulary: {field_name} has fewer than {field.min_items} items")
    if field.max_items is not None and len(values) > field.max_items:
        errors.append(f"vocabulary: {field_name} exceeds {field.max_items} items")
    allowed = rulebook.allowed(field_name)
    for value in values:
        if value not in allowed:
            errors.append(f"vocabulary: {field_name} contains {value!r} not in rulebook")


def _dedupe_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _near_duplicate(a: str, b: str, threshold: float = 0.85) -> bool:
    if a == b:
        return True
    tokens_a = set(re.findall(r"[a-z0-9]+", a))
    tokens_b = set(re.findall(r"[a-z0-9]+", b))
    if not tokens_a or not tokens_b:
        return False
    overlap = len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1)
    return overlap >= threshold

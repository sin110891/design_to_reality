from __future__ import annotations

import json
from pathlib import Path

import gradio as gr

from vision_engine.application.record_feedback import record_feedback
from vision_engine.application.review_feedback import promote_approved_concept, save_generation_review
from vision_engine.application.run_pipeline import run_pipeline
from vision_engine.ui.concept_board import build_concept_board_tab
from vision_engine.domain.enums import (
    BuildabilityAssessment,
    FailureTag,
    GenerationMode,
    GenerationReviewSetStatus,
    RetentionConsentStatus,
    ReviewDecision,
)
from vision_engine.domain.models import GenerationReviewSetInput, PipelineResult, ProjectInput, VariantReviewInput
from vision_engine.infrastructure.file_store import FileStore
from vision_engine.infrastructure.sqlite_repository import SqliteRepository
from vision_engine.settings import clear_settings_cache, get_settings


DISCLAIMER = (
    "Concept visual only — not a technical design, BoQ, or compliance guarantee."
)


def _boot():
    clear_settings_cache()
    settings = get_settings()
    repo = SqliteRepository(settings.database_path)
    repo.init_db()
    file_store = FileStore(
        uploads_dir=settings.paths.uploads,
        generated_dir=settings.paths.generated,
        root=settings.project_root,
    )
    return repo, settings, file_store


def _abs(path: str | None, settings) -> str | None:
    if not path:
        return None
    p = Path(path)
    return str(p if p.is_absolute() else settings.resolve(p))


def _format_references(result: PipelineResult) -> str:
    if not result.references:
        return "_No curated references (baseline mode or empty retrieval)._"
    lines = []
    for ref in result.references:
        lines.append(
            f"### {ref.diversity_role or 'match'} — `{ref.image_id}`\n"
            f"- score: **{ref.score:.3f}**\n"
            f"- quality: {ref.architect_quality:.1f}/5\n"
            f"- rationale: {ref.match_rationale}\n"
            f"- room: {ref.record.room_type} | style: {ref.record.style_family}\n"
            f"- materials: {', '.join(ref.record.material_palette)}\n"
            f"- why: {ref.record.positive_why_it_works or '—'}\n"
        )
    return "\n".join(lines)


def _format_concept(result: PipelineResult) -> str:
    d = result.design_direction
    if not d:
        return "_No concept generated._"
    return (
        f"## {d.concept_title}\n\n"
        f"{d.design_intent}\n\n"
        f"**Mood:** {', '.join(d.mood)}\n\n"
        f"**Colour:** {', '.join(d.colour_direction)}\n\n"
        f"**Materials:** {', '.join(d.material_palette)}\n\n"
        f"**Lighting:** {'; '.join(d.lighting_strategy)}\n\n"
        f"**Furniture:** {'; '.join(d.furniture_direction)}\n\n"
        f"**Focal point:** {d.focal_point}\n\n"
        f"**Spatial hierarchy:** {d.spatial_hierarchy}\n\n"
        f"**Preserve:** {', '.join(d.preserve)}\n\n"
        f"**Allowed changes:** {', '.join(d.allowed_changes)}\n\n"
        f"**Likely trades:** {', '.join(d.likely_trades)}\n\n"
        f"**Positive rules:** {'; '.join(d.positive_rules)}\n\n"
        f"**Warnings:** {'; '.join(d.negative_warnings)}\n\n"
        f"_{result.disclaimer}_"
    )


def generate_redesign(
    room_image,
    inspiration_1,
    inspiration_2,
    room_type,
    style_family,
    brief,
    budget_band,
    constraints_text,
    mode,
):
    repo, settings, file_store = _boot()
    if room_image is None:
        raise gr.Error("Upload a room image to continue.")
    if not brief or len(brief.strip()) < 5:
        raise gr.Error("Enter a short design brief (at least 5 characters).")

    inspiration_paths = []
    for img in (inspiration_1, inspiration_2):
        if img is not None:
            inspiration_paths.append(str(img))

    constraints = [
        c.strip() for c in (constraints_text or "").split("\n") if c.strip()
    ]
    payload = ProjectInput(
        room_image_path=str(room_image),
        inspiration_image_paths=inspiration_paths,
        room_type=room_type,
        style_family=style_family,
        brief=brief.strip(),
        budget_band=budget_band.strip() if budget_band else None,
        constraints=constraints,
    )
    try:
        result = run_pipeline(
            repo=repo,
            settings=settings,
            file_store=file_store,
            payload=payload,
            mode=GenerationMode(mode),
        )
    except Exception as exc:  # noqa: BLE001
        raise gr.Error(str(exc)) from exc

    ref_images = []
    for ref in result.references:
        path = Path(ref.image_path)
        if not path.is_absolute():
            from vision_engine.application.generate_concept import resolve_reference_path

            path = resolve_reference_path(settings, ref.image_path)
        if path.exists():
            ref_images.append(str(path))

    variant_images = []
    variant_choices = []
    for v in result.variants:
        path = settings.resolve(v.image_path)
        if path.exists():
            variant_images.append(str(path))
            variant_choices.append(f"{v.variant_id} | {v.kind.value}")

    state = {
        "project_id": result.project.project_id,
        "generation_run_id": result.generation_run_id,
        "variant_ids": [v.variant_id for v in result.variants],
        "variant_kinds": [v.kind.value for v in result.variants],
        "mode": result.mode.value,
    }
    original = settings.resolve(result.project.room_image_path)
    state_json = json.dumps(state)
    return (
        state_json,
        str(original) if original.exists() else room_image,
        ref_images,
        _format_references(result),
        _format_concept(result),
        variant_images[0] if len(variant_images) > 0 else None,
        variant_images[1] if len(variant_images) > 1 else None,
        variant_images[2] if len(variant_images) > 2 else None,
        result.project.project_id,
        result.generation_run_id or "",
        result.mode.value,
        _review_context_md(state_json, settings),
        gr.update(choices=variant_choices, value=variant_choices[0] if variant_choices else None),
        DISCLAIMER,
    )


def _review_context_md(state_json: str, settings) -> str:
    try:
        state = json.loads(state_json or "{}")
    except json.JSONDecodeError:
        return "_Generate concepts to begin review._"
    if not state.get("project_id"):
        return "_Generate concepts to begin review._"
    lines = [
        f"**Project ID:** `{state.get('project_id')}`",
        f"**Generation run ID:** `{state.get('generation_run_id', '—')}`",
        f"**Mode:** {state.get('mode', '—')}",
    ]
    for idx, (vid, kind) in enumerate(
        zip(state.get("variant_ids", []), state.get("variant_kinds", []), strict=False)
    ):
        label = chr(ord("A") + idx)
        lines.append(f"- Variant {label}: `{vid}` ({kind})")
    return "\n".join(lines)


def _winner_variant_id(state: dict, winner_choice: str) -> str | None:
    if not winner_choice or winner_choice == "none":
        return None
    idx = {"A": 0, "B": 1, "C": 2}.get(winner_choice.upper())
    variant_ids = state.get("variant_ids", [])
    if idx is None or idx >= len(variant_ids):
        return None
    return variant_ids[idx]


def _build_variant_inputs(
    state: dict,
    *,
    decisions: list[str],
    ranks: list,
    ref_scores: list,
    taste_scores: list,
    geometry_scores: list,
    material_scores: list,
    buildability_assessments: list[str],
    buildability_scores: list,
    label_sets: list[list[str]],
    positive_notes_list: list[str],
    negative_notes_list: list[str],
) -> list[VariantReviewInput]:
    inputs: list[VariantReviewInput] = []
    for idx, variant_id in enumerate(state.get("variant_ids", [])):
        rank_val = ranks[idx] if idx < len(ranks) else None
        rank = int(rank_val) if rank_val not in (None, "", 0, "0") else None
        b_score = buildability_scores[idx] if idx < len(buildability_scores) else None
        assessment = BuildabilityAssessment(
            buildability_assessments[idx]
            if idx < len(buildability_assessments)
            else BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL.value
        )
        inputs.append(
            VariantReviewInput(
                variant_id=variant_id,
                decision=ReviewDecision(decisions[idx] if idx < len(decisions) else "needs_edit"),
                rank_in_set=rank,
                reference_relevance_score=int(ref_scores[idx]) if idx < len(ref_scores) and ref_scores[idx] else None,
                taste_quality_score=int(taste_scores[idx]) if idx < len(taste_scores) and taste_scores[idx] else None,
                geometry_preservation_score=(
                    int(geometry_scores[idx]) if idx < len(geometry_scores) and geometry_scores[idx] else None
                ),
                material_coherence_score=(
                    int(material_scores[idx]) if idx < len(material_scores) and material_scores[idx] else None
                ),
                buildability_assessment=assessment,
                buildability_score=int(b_score) if assessment == BuildabilityAssessment.ASSESSABLE and b_score else None,
                labels=list(label_sets[idx]) if idx < len(label_sets) else [],
                positive_notes=positive_notes_list[idx] or None if idx < len(positive_notes_list) else None,
                negative_notes=negative_notes_list[idx] or None if idx < len(negative_notes_list) else None,
            )
        )
    return inputs


def save_review_set(
    state_json,
    reviewer_name,
    submit_action,
    winner_choice,
    overall_notes,
    rank_a,
    rank_b,
    rank_c,
    decision_a,
    decision_b,
    decision_c,
    ref_a,
    ref_b,
    ref_c,
    taste_a,
    taste_b,
    taste_c,
    geom_a,
    geom_b,
    geom_c,
    mat_a,
    mat_b,
    mat_c,
    build_assess_a,
    build_assess_b,
    build_assess_c,
    build_score_a,
    build_score_b,
    build_score_c,
    labels_a,
    labels_b,
    labels_c,
    pos_a,
    pos_b,
    pos_c,
    neg_a,
    neg_b,
    neg_c,
):
    repo, settings, _ = _boot()
    try:
        state = json.loads(state_json or "{}")
    except json.JSONDecodeError as exc:
        raise gr.Error("Generate a concept before saving review.") from exc
    project_id = state.get("project_id")
    generation_run_id = state.get("generation_run_id")
    if not project_id or not generation_run_id:
        raise gr.Error("Generate a concept before saving review.")

    status = (
        GenerationReviewSetStatus.SUBMITTED
        if submit_action == "submit"
        else GenerationReviewSetStatus.DRAFT
    )
    payload = GenerationReviewSetInput(
        generation_run_id=generation_run_id,
        project_id=project_id,
        reviewer=reviewer_name or settings.review.curator_name,
        status=status,
        winner_variant_id=_winner_variant_id(state, winner_choice),
        overall_notes=overall_notes or None,
        variants=_build_variant_inputs(
            state,
            decisions=[decision_a, decision_b, decision_c],
            ranks=[rank_a, rank_b, rank_c],
            ref_scores=[ref_a, ref_b, ref_c],
            taste_scores=[taste_a, taste_b, taste_c],
            geometry_scores=[geom_a, geom_b, geom_c],
            material_scores=[mat_a, mat_b, mat_c],
            buildability_assessments=[build_assess_a, build_assess_b, build_assess_c],
            buildability_scores=[build_score_a, build_score_b, build_score_c],
            label_sets=[labels_a or [], labels_b or [], labels_c or []],
            positive_notes_list=[pos_a, pos_b, pos_c],
            negative_notes_list=[neg_a, neg_b, neg_c],
        ),
    )
    try:
        review_set = save_generation_review(repo=repo, payload=payload)
    except Exception as exc:  # noqa: BLE001
        raise gr.Error(str(exc)) from exc
    winner = review_set.winner_variant_id or "none"
    return (
        f"Saved review set `{review_set.review_set_id}` ({review_set.status.value}). "
        f"Winner: `{winner}`."
    )


def promote_review_winner(
    state_json,
    reviewer_name,
    consent_internal,
    consent_evaluation,
    consent_training,
):
    repo, settings, _ = _boot()
    try:
        state = json.loads(state_json or "{}")
    except json.JSONDecodeError as exc:
        raise gr.Error("Generate and submit a review before promoting.") from exc
    generation_run_id = state.get("generation_run_id")
    if not generation_run_id:
        raise gr.Error("Generate and submit a review before promoting.")

    review_set = repo.get_latest_review_set(
        generation_run_id=generation_run_id,
        reviewer=reviewer_name or settings.review.curator_name,
    )
    if review_set is None or review_set.winner_variant_id is None:
        raise gr.Error("Submit a review with a winner before promoting.")

    winner_review = next(
        (v for v in review_set.variant_reviews if v.variant_id == review_set.winner_variant_id),
        None,
    )
    if winner_review is None:
        raise gr.Error("Winner variant review not found.")

    if consent_training:
        purpose = RetentionConsentStatus.MODEL_TRAINING_ALLOWED
    elif consent_evaluation:
        purpose = RetentionConsentStatus.EVALUATION_ALLOWED
    elif consent_internal:
        purpose = RetentionConsentStatus.INTERNAL_REVIEW_ONLY
    else:
        raise gr.Error("Select at least one retention consent option.")

    try:
        manifest = promote_approved_concept(
            repo=repo,
            variant_review_id=winner_review.variant_review_id,
            purpose=purpose,
            consented_by=reviewer_name or settings.review.curator_name,
            consent_version="review-consent.v1",
        )
    except Exception as exc:  # noqa: BLE001
        raise gr.Error(str(exc)) from exc
    return f"Promoted approved concept manifest `{manifest.manifest_id}`."


def save_review(
    state_json,
    decision,
    selected_variant,
    rank,
    reference_relevance,
    taste,
    geometry,
    buildability,
    material,
    positive_notes,
    negative_notes,
    failure_tags,
):
    repo, settings, _ = _boot()
    try:
        state = json.loads(state_json or "{}")
    except json.JSONDecodeError as exc:
        raise gr.Error("Generate a concept before saving feedback.") from exc
    project_id = state.get("project_id")
    if not project_id:
        raise gr.Error("Generate a concept before saving feedback.")

    variant_id = None
    if selected_variant:
        variant_id = selected_variant.split("|")[0].strip()

    event = record_feedback(
        repo=repo,
        project_id=project_id,
        reviewer=settings.review.curator_name,
        decision=decision,
        variant_id=variant_id,
        rank=int(rank) if rank else None,
        reference_relevance_score=int(reference_relevance) if reference_relevance else None,
        taste_quality_score=int(taste) if taste else None,
        geometry_preservation_score=int(geometry) if geometry else None,
        buildability_score=int(buildability) if buildability else None,
        material_coherence_score=int(material) if material else None,
        positive_notes=positive_notes or None,
        negative_notes=negative_notes or None,
        failure_tags=list(failure_tags or []),
    )
    return f"Saved feedback `{event.feedback_id}` for project `{project_id}`."


def build_ui() -> gr.Blocks:
    room_types = [
        "living_room",
        "kitchen",
        "bedroom",
        "bathroom",
        "dining_room",
        "hallway",
        "study",
        "mixed",
        "unknown",
    ]
    failure_choices = [t.value for t in FailureTag]
    label_choices = [
        "geometry_failure",
        "window_changed",
        "door_changed",
        "fireplace_changed",
        "lighting_problem",
        "material_conflict",
        "generic_ai_artifact",
        "reference_mismatch",
        "good_material_coherence",
        "good_lighting_strategy",
        "good_geometry_preservation",
        "clear_focal_point",
    ]
    buildability_choices = [a.value for a in BuildabilityAssessment]
    decision_choices = [d.value for d in ReviewDecision]

    with gr.Blocks(title="Vision Engine Prototype") as demo:
        gr.Markdown(
            "# Vision Engine Prototype\n"
            "Architect-curated retrieval → structured design direction → edited room concepts.\n\n"
            f"*{DISCLAIMER}*"
        )
        state = gr.State("{}")

        with gr.Tab("1 · Inputs"):
            with gr.Row():
                room = gr.Image(type="filepath", label="Room image", height=320)
                with gr.Column():
                    insp1 = gr.Image(type="filepath", label="Inspiration (optional)", height=150)
                    insp2 = gr.Image(type="filepath", label="Inspiration 2 (optional)", height=150)
            with gr.Row():
                room_type = gr.Dropdown(room_types, value="living_room", label="Room type")
                style_family = gr.Dropdown(
                    ["Contemporary Europe"], value="Contemporary Europe", label="Style family"
                )
                budget = gr.Dropdown(
                    ["", "low", "medium", "medium_high", "high"],
                    value="medium_high",
                    label="Budget band",
                )
                mode = gr.Dropdown(
                    ["curated", "baseline"], value="curated", label="Generation mode"
                )
            brief = gr.Textbox(
                label="Brief",
                lines=3,
                placeholder="warm contemporary European, calmer lighting, retain windows and fireplace",
            )
            constraints = gr.Textbox(
                label="Constraints (one per line)",
                lines=3,
                value="do not move walls, doors, windows, radiators, or fireplace",
            )
            generate_btn = gr.Button("Generate concepts", variant="primary")

        with gr.Tab("2 · Retrieved references"):
            ref_gallery = gr.Gallery(label="Top references", columns=3, height=280)
            ref_md = gr.Markdown()

        with gr.Tab("3 · Generated concepts"):
            with gr.Row():
                original_out = gr.Image(label="Original", height=280)
                var_a = gr.Image(label="Variant A — closest", height=280)
                var_b = gr.Image(label="Variant B — conservative", height=280)
                var_c = gr.Image(label="Variant C — expressive", height=280)
            concept_md = gr.Markdown()
            disclaimer_out = gr.Markdown()

        with gr.Tab("4 · Architect review"):
            review_context = gr.Markdown("_Generate concepts to begin review._")
            with gr.Row():
                project_id_out = gr.Textbox(label="Project ID", interactive=False)
                generation_run_out = gr.Textbox(label="Generation run ID", interactive=False)
                mode_out = gr.Textbox(label="Mode", interactive=False)
            reviewer_name = gr.Textbox(label="Reviewer", value="Lloyd Lee")
            gr.Markdown("### Set comparison")
            winner_choice = gr.Radio(
                ["A", "B", "C", "none"],
                value="none",
                label="Select best variant",
            )
            with gr.Row():
                rank_a = gr.Dropdown([0, 1, 2, 3], value=0, label="Rank A (0 = unranked)")
                rank_b = gr.Dropdown([0, 1, 2, 3], value=0, label="Rank B")
                rank_c = gr.Dropdown([0, 1, 2, 3], value=0, label="Rank C")
            overall_notes = gr.Textbox(label="Overall notes", lines=2)

            gr.Markdown("### Individual variant reviews")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("**Variant A**")
                    decision_a = gr.Dropdown(decision_choices, value="needs_edit", label="Decision A")
                    ref_a = gr.Slider(1, 5, step=1, value=4, label="Reference relevance")
                    taste_a = gr.Slider(1, 5, step=1, value=4, label="Taste")
                    geom_a = gr.Slider(1, 5, step=1, value=4, label="Geometry")
                    mat_a = gr.Slider(1, 5, step=1, value=4, label="Material coherence")
                    build_assess_a = gr.Dropdown(
                        buildability_choices,
                        value=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL.value,
                        label="Buildability assessment",
                    )
                    build_score_a = gr.Slider(1, 5, step=1, value=3, label="Buildability score")
                    labels_a = gr.CheckboxGroup(label_choices, label="Labels A")
                    pos_a = gr.Textbox(label="Positive notes A", lines=2)
                    neg_a = gr.Textbox(label="Negative notes A", lines=2)
                with gr.Column():
                    gr.Markdown("**Variant B**")
                    decision_b = gr.Dropdown(decision_choices, value="needs_edit", label="Decision B")
                    ref_b = gr.Slider(1, 5, step=1, value=4, label="Reference relevance")
                    taste_b = gr.Slider(1, 5, step=1, value=4, label="Taste")
                    geom_b = gr.Slider(1, 5, step=1, value=4, label="Geometry")
                    mat_b = gr.Slider(1, 5, step=1, value=4, label="Material coherence")
                    build_assess_b = gr.Dropdown(
                        buildability_choices,
                        value=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL.value,
                        label="Buildability assessment",
                    )
                    build_score_b = gr.Slider(1, 5, step=1, value=3, label="Buildability score")
                    labels_b = gr.CheckboxGroup(label_choices, label="Labels B")
                    pos_b = gr.Textbox(label="Positive notes B", lines=2)
                    neg_b = gr.Textbox(label="Negative notes B", lines=2)
                with gr.Column():
                    gr.Markdown("**Variant C**")
                    decision_c = gr.Dropdown(decision_choices, value="needs_edit", label="Decision C")
                    ref_c = gr.Slider(1, 5, step=1, value=4, label="Reference relevance")
                    taste_c = gr.Slider(1, 5, step=1, value=4, label="Taste")
                    geom_c = gr.Slider(1, 5, step=1, value=4, label="Geometry")
                    mat_c = gr.Slider(1, 5, step=1, value=4, label="Material coherence")
                    build_assess_c = gr.Dropdown(
                        buildability_choices,
                        value=BuildabilityAssessment.NOT_ASSESSABLE_FROM_VISUAL.value,
                        label="Buildability assessment",
                    )
                    build_score_c = gr.Slider(1, 5, step=1, value=3, label="Buildability score")
                    labels_c = gr.CheckboxGroup(label_choices, label="Labels C")
                    pos_c = gr.Textbox(label="Positive notes C", lines=2)
                    neg_c = gr.Textbox(label="Negative notes C", lines=2)

            with gr.Row():
                save_draft_btn = gr.Button("Save draft")
                submit_review_btn = gr.Button("Submit review", variant="primary")
            save_status = gr.Markdown()

            gr.Markdown("### Promote approved winner to evaluation dataset")
            consent_internal = gr.Checkbox(label="Internal architect review only")
            consent_evaluation = gr.Checkbox(label="Evaluation / quality improvement", value=True)
            consent_training = gr.Checkbox(label="Future model training")
            promote_btn = gr.Button("Promote approved winner")
            promote_status = gr.Markdown()

            gr.Markdown("### Legacy single-variant feedback")
            decision = gr.Radio(
                ["approved", "rejected", "needs_edit"], value="approved", label="Decision"
            )
            selected_variant = gr.Dropdown(label="Variant", choices=[])
            rank = gr.Slider(1, 3, step=1, value=1, label="Rank")
            with gr.Row():
                reference_relevance = gr.Slider(1, 5, step=1, value=4, label="Reference relevance")
                taste = gr.Slider(1, 5, step=1, value=4, label="Taste quality")
                geometry = gr.Slider(1, 5, step=1, value=4, label="Geometry preservation")
            with gr.Row():
                buildability = gr.Slider(1, 5, step=1, value=4, label="Buildability")
                material = gr.Slider(1, 5, step=1, value=4, label="Material coherence")
            positive_notes = gr.Textbox(label="Positive notes", lines=2)
            negative_notes = gr.Textbox(label="Negative notes", lines=2)
            failure_tags = gr.CheckboxGroup(failure_choices, label="Failure tags")
            save_btn = gr.Button("Save legacy feedback")

        generate_btn.click(
            generate_redesign,
            inputs=[
                room,
                insp1,
                insp2,
                room_type,
                style_family,
                brief,
                budget,
                constraints,
                mode,
            ],
            outputs=[
                state,
                original_out,
                ref_gallery,
                ref_md,
                concept_md,
                var_a,
                var_b,
                var_c,
                project_id_out,
                generation_run_out,
                mode_out,
                review_context,
                selected_variant,
                disclaimer_out,
            ],
        )

        review_inputs = [
            state,
            reviewer_name,
            winner_choice,
            overall_notes,
            rank_a,
            rank_b,
            rank_c,
            decision_a,
            decision_b,
            decision_c,
            ref_a,
            ref_b,
            ref_c,
            taste_a,
            taste_b,
            taste_c,
            geom_a,
            geom_b,
            geom_c,
            mat_a,
            mat_b,
            mat_c,
            build_assess_a,
            build_assess_b,
            build_assess_c,
            build_score_a,
            build_score_b,
            build_score_c,
            labels_a,
            labels_b,
            labels_c,
            pos_a,
            pos_b,
            pos_c,
            neg_a,
            neg_b,
            neg_c,
        ]

        def _save_draft(
            state_json,
            reviewer,
            winner,
            notes,
            r_a,
            r_b,
            r_c,
            d_a,
            d_b,
            d_c,
            rr_a,
            rr_b,
            rr_c,
            t_a,
            t_b,
            t_c,
            g_a,
            g_b,
            g_c,
            m_a,
            m_b,
            m_c,
            ba_a,
            ba_b,
            ba_c,
            bs_a,
            bs_b,
            bs_c,
            l_a,
            l_b,
            l_c,
            p_a,
            p_b,
            p_c,
            n_a,
            n_b,
            n_c,
        ):
            return save_review_set(
                state_json,
                reviewer,
                "draft",
                winner,
                notes,
                r_a,
                r_b,
                r_c,
                d_a,
                d_b,
                d_c,
                rr_a,
                rr_b,
                rr_c,
                t_a,
                t_b,
                t_c,
                g_a,
                g_b,
                g_c,
                m_a,
                m_b,
                m_c,
                ba_a,
                ba_b,
                ba_c,
                bs_a,
                bs_b,
                bs_c,
                l_a,
                l_b,
                l_c,
                p_a,
                p_b,
                p_c,
                n_a,
                n_b,
                n_c,
            )

        def _save_submit(*args):
            return save_review_set(
                args[0],
                args[1],
                "submit",
                *args[2:],
            )

        save_draft_btn.click(_save_draft, inputs=review_inputs, outputs=[save_status])
        submit_review_btn.click(_save_submit, inputs=review_inputs, outputs=[save_status])
        promote_btn.click(
            promote_review_winner,
            inputs=[state, reviewer_name, consent_internal, consent_evaluation, consent_training],
            outputs=[promote_status],
        )
        save_btn.click(
            save_review,
            inputs=[
                state,
                decision,
                selected_variant,
                rank,
                reference_relevance,
                taste,
                geometry,
                buildability,
                material,
                positive_notes,
                negative_notes,
                failure_tags,
            ],
            outputs=[save_status],
        )

        with gr.Tab("5 · Concept board"):
            build_concept_board_tab(pipeline_state=state)

    return demo


def launch(host: str = "127.0.0.1", port: int = 7860, share: bool = False) -> None:
    _, settings, _ = _boot()
    # Reference images live under dataset_factory/; Gradio blocks paths outside cwd
    # unless explicitly allowed.
    allowed = [
        str(settings.project_root),
        str(settings.paths.uploads),
        str(settings.paths.generated),
        str(settings.paths.concept_boards),
        str(settings.paths.exports),
        str(settings.paths.catalogue),
        str(settings.paths.staging),
        str(settings.project_root.parent / "dataset_factory" / "data" / "raw_images"),
        str(settings.project_root.parent / "dataset_factory" / "data" / "exports"),
    ]
    demo = build_ui()
    demo.launch(
        server_name=host,
        server_port=port,
        share=share,
        allowed_paths=allowed,
    )


if __name__ == "__main__":
    launch()

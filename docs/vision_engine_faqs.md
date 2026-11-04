# Vision Engine FAQs: Scaling, Retrieval, Evaluation, and Funding

**Scope:** The Vision Engine implementation in this repository as of July 2026.  
**Important:** It is a concept-design prototype. It does not produce technical drawings, guaranteed geometry, a bill of quantities (BoQ), construction pricing, or compliance advice.

---

## How can the existing system scale?

The system can scale across styles, but it needs a stronger curated-data and evaluation layer—not just more prompt wording.

## Can it capture minimalist Japanese style, industrial spaces, or other style families?

Yes. Keep the same technical schemas (`DatasetRecord`, `DesignDirection`, feedback), but expand the controlled design vocabulary upstream in `dataset_factory`.

Today the rulebook only permits `Contemporary Europe` as a style family:

```yaml
style_family:
  type: single
  allowed_values:
    - Contemporary Europe
```

Source: `vision_engine/configs/rulebook.v1.yaml`

A scalable approach:

1. Add style families such as `Japanese Minimalism`, `Industrial`, `Scandinavian`, and so on.
2. Create a versioned style profile per family:
   - visual principles;
   - material vocabulary;
   - negative rules;
   - appropriate room conditions;
   - common AI failure modes.
3. Curate and approve enough references for each style before enabling it in the app.
4. Add the same vocabulary to `dataset_factory` first, so it produces consistent approved gold records.
5. Expand the Gradio dropdown, which currently only shows one style.

Do not create separate Python schemas per style unless a style genuinely needs unique structured fields. One common `DesignDirection` schema is correct; styles should be controlled data and rules inside it.

For example:

- **Japanese minimalism:** natural timber, plaster, shoji-inspired diffuse lighting, negative space, low furniture, and restrained visual hierarchy.
- **Industrial:** exposed steel, brick/concrete, utilitarian lighting, robust joinery, with explicit warnings against turning every room into a generic loft.

The real scaling unit is not “a new prompt.” It is a **reviewed, rights-cleared, balanced style dataset plus style-specific evaluation criteria**.

### What else could the system do?

After style coverage is working, useful expansion directions are:

1. **Room and property coverage:** different room types, listed-building constraints, rental constraints, accessibility needs, climate, and regional construction norms.
2. **More accurate buildability:** curator-reviewed trade requirements, intervention levels, cost bands, and practical constraints.
3. **Supplier and product matching:** retrieve approved materials, furniture, finishes, and later available supplier products.
4. **Geometry controls:** masks, segmentation, depth maps, and post-generation checks for windows, walls, doors, radiators, and fireplaces.
5. **Preference learning:** use ranked approved/rejected variants to train a reranker or preference model.
6. **Professional workflow:** revisions, shareable boards, design handover, specification support, and project history.
7. **Commercial outcomes:** measure whether users reach an accepted concept faster, buy design services, or progress to renovation/sourcing.

---

## When an architect saves a review, are generated photos added to the golden dataset?

**Not currently.**

When an architect saves a review:

- The generated images already remain on disk under `data/generated/<project_id>/`.
- Their paths and variant type are stored in SQLite’s `generated_variants` table.
- The review is saved as a `review_events` row linked by `project_id` and optional `variant_id`.

```python
def save_feedback(self, event: FeedbackEvent) -> None:
    with self.session() as session:
        session.merge(
            ReviewEventRow(
                feedback_id=event.feedback_id,
                project_id=event.project_id,
                variant_id=event.variant_id,
                reviewer=event.reviewer,
                decision=event.decision.value,
                rank=event.rank,
                # scores, notes, and failure tags
            )
        )
```

Source: `vision_engine/src/vision_engine/infrastructure/sqlite_repository.py`

However, `export-feedback` exports only the feedback event fields—IDs, scores, notes, and tags—not the generated image files or a full training-ready manifest.

```python
def export_feedback(
    events: Iterable[FeedbackEvent],
    output: Path,
    *,
    fmt: str = "jsonl",
) -> tuple[Path, int]:
    rows: list[dict[str, Any]] = []
    for event in events:
        payload = event.model_dump(mode="json")
        rows.append(payload)
```

Source: `vision_engine/src/vision_engine/infrastructure/exporters.py`

Also, an architect approval should not automatically make an image “gold.” It should make it an **accepted generated-concept candidate**. A separate promotion workflow should export an immutable manifest containing:

- input-room image hash/path;
- selected generated-variant hash/path;
- approval and rank;
- design direction;
- retrieved reference IDs;
- prompt/model/version;
- reviewer notes; and
- rights and consent status.

That becomes a valuable preference dataset, distinct from the original curated-reference gold dataset.

---

## What techniques are used to search the approved interior-design dataset?

In curated mode, the system:

1. Loads approved reference records from `gold.jsonl`.
2. Converts every image and its design notes into numerical embeddings.
3. Stores vectors locally in NumPy.
4. Embeds the uploaded room image and the user’s brief.
5. Finds the closest visual/text candidates.
6. Scores them using a weighted hybrid formula.
7. Chooses up to three diverse references.

The current formula is:

```python
def hybrid_score(...) -> float:
    quality_norm = max(0.0, min(1.0, (architect_quality - 1.0) / 4.0))
    return (
        image_weight * image_similarity
        + text_weight * text_similarity
        + metadata_weight * metadata_match
        + quality_weight * quality_norm
    )
```

Source: `vision_engine/src/vision_engine/domain/services.py`

Default weights:

- 35% image similarity;
- 25% text similarity;
- 25% metadata match; and
- 15% quality score.

It also applies soft penalties when room type, style, or budget conflict, then intentionally diversifies the final set into:

- direct match;
- material/lighting match; and
- composition/spatial match.

---

## What is happening in curated mode?

It is not a literal Photoshop “overlay.”

The system sends the model:

- the uploaded room photo;
- up to three approved reference photos;
- the user brief;
- approved design notes from those references;
- a structured `DesignDirection`;
- geometry-preservation instructions; and
- variant-specific guidance.

The concept stage first turns the inputs into structured JSON:

```python
payload, meta = client.generate_concept(
    room_image_path=room_path,
    reference_image_paths=ref_paths,
    prompt=prompt,
    response_schema=DesignDirection.model_json_schema(),
)
```

Source: `vision_engine/src/vision_engine/application/generate_concept.py`

Then the image stage sends the original room as the base image and references as taste/material cues:

```python
parts.append(types.Part.from_text(text="ORIGINAL ROOM (edit this image):"))
parts.append(types.Part.from_bytes(data=room_image_path.read_bytes(), mime_type=mime))

for i, ref in enumerate(reference_image_paths[:3], start=1):
    parts.append(types.Part.from_text(
        text=f"REFERENCE {i} (taste/material cue only):"
    ))
    parts.append(types.Part.from_bytes(data=ref.read_bytes(), mime_type=ref_mime))

parts.append(types.Part.from_text(text=prompt))
```

Source: `vision_engine/src/vision_engine/infrastructure/image_edit_clients/gemini_image_client.py`

The model synthesises a new image conditioned on those inputs. It is image-to-image generation, not a deterministic layer-based edit.

---

## What does the image-editing prompt look like?

Its key instructions are:

```text
Edit the ORIGINAL ROOM IMAGE. This is an image-editing task, not text-to-image from scratch.

Variant {{ variant_label }} ({{ variant_kind }}):
{{ variant_guidance }}
```

Source: `vision_engine/src/vision_engine/prompts/image_edit.jinja2`

It then injects the whole design direction:

- materials;
- lighting;
- furniture;
- focal point;
- preserve list;
- allowed changes;
- positive rules;
- warnings; and
- retrieved-reference cues.

The shared geometry lock says:

```text
Preserve perspective, camera position, walls, windows, doors, ceiling lines,
fixed plumbing, fireplace, and radiators. Do not alter room proportions.
Do not add impossible openings. Do not introduce floating fixtures or distorted furniture.
Do not copy a reference image literally.
```

Source: `vision_engine/configs/prompts.v1.yaml`

---

## How is geometry maintained? Can windows, walls, and fittings be preserved perfectly?

**They cannot be preserved perfectly with the current implementation.**

Current geometry preservation is prompt-guided. The image model sees the original room photo and is instructed to preserve fixed elements, but it can still distort windows, doors, walls, radiators, fireplaces, or furniture.

The system does not yet use:

- masks defining immutable regions;
- room segmentation;
- depth estimation;
- edge/line conditioning;
- camera calibration;
- 3D reconstruction;
- object detection and pixel-level “do not change” zones; or
- post-generation geometry validation.

For a much stronger geometry stack, use:

1. segmentation masks for windows, doors, fireplaces, radiators, and walls;
2. depth/normal maps or room-layout estimation;
3. image-edit/inpainting models supporting masks and structural controls;
4. computer-vision checks comparing lines/openings before and after; and
5. human review as the final gate.

---

## Is this an image-editing model? How does that compare to fine-tuning?

Yes. The current Gemini path uses an image-conditioned generation call:

1. it attaches the uploaded room image;
2. it attaches curated reference images;
3. it supplies the design prompt; and
4. it asks the provider to return a generated image.

It does not modify a fixed pixel layer or a 3D room model. Instead, the model synthesises a new image based on the images and text it receives.

Fine-tuning is different:

- **Prompt-time conditioning / retrieval:** keeps the foundation model unchanged. It supplies selected references, rules, and an input room at generation time.
- **Fine-tuning:** changes model parameters after training on many examples.

Fine-tuning can help a model learn a consistent visual language. It does not inherently solve geometry preservation, and it requires a much larger rights-cleared dataset of accepted/rejected designs. Masks, depth, and structural controls are the more direct solution to geometry risk.

---

## Are fake embeddings used now?

Yes. The current Vision Engine configuration uses `EMBEDDING_PROVIDER=fake`.

This is suitable for offline testing and verifying that the pipeline works, but it is not a valid representation of real visual or design similarity.

### What is an embedding?

An **embedding** is a list of numbers—a vector—that represents an item such as an image or a piece of text.

The numerical values are useful because the system can compare them:

```text
Uploaded room image → vector [0.12, -0.31, 0.48, ...]
Reference image     → vector [0.09, -0.28, 0.51, ...]

closer vectors → potentially more similar images or ideas
```

In a genuine multimodal model, the embedding is learned from large amounts of image and text data. A good embedding may place:

- calm timber interiors close to other calm timber interiors;
- “warm minimal living room” text close to visually compatible room photos;
- steel-and-concrete industrial references away from soft linen-and-oak references.

The Vision Engine uses embeddings for **retrieval**, not directly to generate images. Retrieval answers: “Which approved references should be shown to the concept and image models?”

### How embeddings are used in the current system

For each approved curated record, `build-index` creates:

1. an image vector;
2. a text vector from a combined `text_blob`; and
3. a `DatasetRecord` containing metadata and design rationale.

The text blob contains fields such as:

```python
chunks = [
    record.style_family,
    record.room_type,
    record.project_type,
    record.budget_band,
    record.furniture_style,
    record.lighting_strategy,
    record.positive_why_it_works,
    record.negative_common_pitfalls,
    record.focal_point,
    # additional materials, mood, trades, and spatial fields
]
return " | ".join(c for c in chunks if c)
```

Source: `vision_engine/src/vision_engine/domain/services.py`

The numerical vectors are saved in:

```text
data/indexes/curated.npz    # image and text vector matrices
data/indexes/curated.jsonl  # matching DatasetRecord metadata
```

At query time, the engine creates:

- a room-image vector;
- a text vector from the brief, room type, style, budget, and constraints; and
- optionally blends inspiration-image vectors into the room vector.

It then uses cosine similarity—how closely vectors point in the same direction—to find candidate references.

### What “fake embeddings” actually do

The fake embedding provider does not understand rooms, styles, materials, or written language. It hashes the image bytes or text into a stable 64-number vector:

```python
def embed_image(self, image_path: Path) -> list[float]:
    data = image_path.read_bytes() if image_path.exists() else image_path.name.encode()
    return _hash_to_vec(b"img:" + data[:4096] + image_path.name.encode(), self.dim)

def embed_text(self, text: str) -> list[float]:
    return _hash_to_vec(b"txt:" + text.encode("utf-8"), self.dim)
```

Source: `vision_engine/src/vision_engine/infrastructure/embedding_clients/fake.py`

A cryptographic hash is useful because it is deterministic: the same input produces the same result. That makes tests repeatable.

But it has no semantic meaning:

```text
"oak, limewash, linen" is not mathematically close to "warm contemporary room"
because the fake embedding system understands neither phrase.
```

Therefore, when fake embeddings are active:

> Retrieval is mostly guided by explicit metadata, brief-token overlap, and heuristic quality values—not genuine visual or semantic similarity.

This is why fake mode is useful for demos and automated tests, but unsuitable for proving that architect-curated retrieval is superior.

### What does the current non-fake option do?

The current `gemini` embedding path is only partially real:

- Text embeddings are requested through Gemini’s embedding API.
- Image embeddings are **not** true multimodal image embeddings yet.
- The image path begins with the local fake/hash vector and may blend it with a text embedding based on the image filename.

That is explicitly prototype-grade. It is not sufficient as the final retrieval architecture.

### How should we change to real embeddings?

Use a proven vision-language embedding model—one designed to map images and descriptive text into a compatible semantic space.

A robust migration path:

1. **Choose a real embedding model**
   - A local/open model such as OpenCLIP or SigLIP for image/text retrieval; or
   - a commercial API with documented multimodal image and text embedding support.

2. **Create a dedicated embedding adapter**
   - Keep the existing `EmbeddingClient` interface.
   - Replace the hash logic inside `embed_image()` and `embed_text()`.
   - Ensure both index construction and query-time retrieval use the same model and embedding version.

3. **Rebuild the full index**
   - Existing fake vectors cannot be mixed with real vectors.
   - Re-embed every approved reference image and text blob.
   - Save the embedding-model identifier and index version alongside the vectors.

4. **Use a clear retrieval design**
   - Image-to-image similarity: uploaded room ↔ curated reference.
   - Text-to-text similarity: brief ↔ curated design notes.
   - Cross-modal similarity where supported: brief ↔ reference image and room ↔ reference text.
   - Metadata/rulebook score as an explicit secondary signal.

5. **Evaluate retrieval separately from generation**
   - Ask architects which references are truly relevant for a fixed set of room/brief queries.
   - Measure Recall@K: does at least one relevant reference appear in the top K?
   - Measure NDCG: are the most relevant references ranked first?
   - Compare fake, text-only, image-only, and multimodal retrieval.

6. **Add a reranker later**
   - Retrieve a broader top 20–50 set quickly.
   - Use a stronger vision-language model or architect-trained reranker to choose the final 3 references.

### What does this enable?

Real multimodal embeddings enable:

- **Better visual matching:** rooms with compatible proportion, light, material character, and furniture density can rank together even when labels differ.
- **Better brief understanding:** “quiet plaster walls with low oak joinery” can retrieve relevant images without exact field-value matches.
- **Cross-style discovery:** the system can find a Japanese-minimalism material or lighting precedent that helps a contemporary room without falsely treating it as a full style match.
- **Better inspiration use:** user-supplied inspiration images can influence retrieval meaningfully.
- **Less brittle metadata:** manual tags remain important, but retrieval no longer depends entirely on exact tag overlap.
- **Higher-quality prompts:** the image model receives more relevant precedents, which is the core mechanism behind the curated-system hypothesis.
- **Measurable retrieval quality:** the team can demonstrate that the reference-selection step improved before attributing output improvements to the generator.

Real embeddings do not replace:

- architect approval;
- controlled style vocabularies;
- rights and provenance controls;
- geometry protection; or
- careful evaluation.

They improve the quality of evidence given to the generation model.

---

## How does feedback and evaluation work?

Architect review stores:

- decision;
- rank;
- reference relevance score;
- taste quality score;
- geometry-preservation score;
- buildability score;
- material-coherence score;
- positive and negative notes; and
- failure tags.

The system can aggregate:

- approval rate;
- average geometry score;
- average taste score;
- severe geometry-failure rate; and
- failure-tag patterns.

```python
return {
    "feedback_count": len(events),
    "decisions": dict(decisions),
    "approval_rate": approved / len(events),
    "avg_geometry": (sum(geometry_scores) / len(geometry_scores))
        if geometry_scores else None,
    "avg_taste": (sum(taste_scores) / len(taste_scores))
        if taste_scores else None,
    "severe_geometry_failures": severe,
    "severe_geometry_rate": severe / len(events),
    "failure_tag_counts": dict(tag_counts),
}
```

Source: `vision_engine/src/vision_engine/application/evaluate.py`

This is useful instrumentation, but it is not proof of commercial or design advantage by itself.

---

## How can we prove curated references improve results over a baseline?

The claim is plausible, but it is not automatically true because references were added. More context can also confuse the model, make outputs derivative, increase cost and latency, or select mismatched references.

A credible evaluation:

1. Build a holdout set of 50–100 unseen room photos, across room types and styles.
2. For each room, generate the same number of variants with:
   - generic baseline;
   - baseline with style prompt;
   - user inspiration only; and
   - curated retrieval system.
3. Keep the same image model, generation settings, number of attempts, and budget.
4. Blind the reviewer: they should not know which system produced each image.
5. Ask architects and target users to make pairwise choices.
6. Measure:
   - curated preference rate;
   - geometry score;
   - taste/material coherence;
   - time to first acceptable concept;
   - retry count; and
   - cost per accepted concept.
7. Report confidence intervals, not just averages.

The strongest result is not “curated won 70% in a founder-led demo.” It is:

> In a blinded, pre-specified test, expert reviewers preferred curated concepts in X% of comparisons, with better geometry preservation and lower time-to-approval at comparable cost.

---

## Is this the fundable aspect? VC-grade assessment

The honest answer: **the architecture alone is not fundable.**

Image retrieval, structured prompts, Gemini image editing, and feedback forms can be replicated by a capable team.

The fundable thesis could be:

> Build the proprietary, rights-cleared, architect-reviewed preference and outcome dataset that improves interior-concept generation for a narrow, commercially valuable workflow—and distribute it where decisions and transactions occur.

The potential moat is:

- proprietary approved/reference/negative design knowledge;
- accumulated acceptance and rejection data linked to real rooms;
- measurable expert preference;
- style-specific, buildability-aware constraints;
- workflow integration with architects, developers, renovators, or suppliers;
- retained user/room history and a decision system—not merely output images; and
- eventual linkage between concept, specification, sourcing, cost, and execution.

VC concerns:

- 45 references are far too few to demonstrate a durable data moat;
- fake embeddings mean retrieval quality is not yet proven;
- foundation-model providers may improve their image editing rapidly;
- “beautiful concepts” is a feature unless it improves paid workflow outcomes;
- there is no evidence yet of willingness to pay, retention, distribution, or conversion; and
- geometry/buildability errors create trust and liability risk.

Pre-seed potential exists if the company focuses on one wedge, such as premium residential renovation concepts or architect-assist tooling, and proves:

1. experts prefer the outputs;
2. projects reach acceptable concepts faster;
3. the workflow captures proprietary feedback;
4. the product has a clear distribution path; and
5. a customer pays for that improvement.

---

## How should we compare the new system to other systems?

Compare against:

- the same foundation model with a generic prompt;
- the same model with a stronger hand-written style prompt;
- the same model with user inspiration only;
- the curated-retrieval pipeline; and
- ideally, a human architect’s initial concept direction.

Do not benchmark only on attractiveness. Score:

- style relevance;
- room suitability;
- material coherence;
- geometry preservation;
- buildability plausibility;
- generic-AI artifact rate;
- time to approval;
- retries; and
- cost per accepted concept.

Use blinded, pairwise evaluation wherever possible. A reviewer should see the room, brief, and two unlabeled outputs—not the system labels—and choose the stronger concept or mark a tie.

The next highest-value technical move is to replace fake embeddings, then run a blinded curated-vs-baseline study before making strong commercial claims.

---

## Related documents

- How the system works: `docs/vision_engine_how_it_works.md`
- Engineering requirements: `docs/erds/vision_engine_prototype_engineering_requirements.md`
- Operator runbook: `docs/vision_engine_overview_runbook.md`
- Dataset factory runbook: `docs/dataset_factory_overview_runbook.md`

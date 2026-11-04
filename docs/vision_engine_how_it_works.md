# How the Vision Engine Generates Room Concepts

**Audience:** everyone from a first-time user to an engineer extending the prototype.  
**Scope:** the implementation in `vision_engine/` today, not an aspirational production system.

## In one minute

The Vision Engine takes a photograph of a real room and produces concept visuals in five stages:

```text
Approved architect dataset
        ↓
Local retrieval index
        ↓
Uploaded room image + brief + constraints
        ↓
Structured design direction
        ↓
Image-to-image generation of three concepts
        ↓
Architect review and feedback
```

It does **not** measure the room, create technical drawings, calculate a bill of quantities (BoQ), or guarantee that windows, walls, and fittings are preserved perfectly. It is a design-concept prototype.

The system is designed to test one idea: whether using Lloyd's approved reference images and notes produces better concepts than a generic prompt alone.

---

## 1. The main idea in plain language

Think of the system as an interior-designer assistant with three separate jobs:

1. **Find good precedents.** It searches the approved interior-design dataset for images and design notes that suit the room and brief.
2. **Write a design plan.** A multimodal model turns the brief and precedents into a structured interior direction: palette, lighting, furniture, what to retain, and what not to do.
3. **Visualise the plan.** An image-generation model receives the original room photograph, selected references, and the design plan. It generates a new concept image while being told to retain the existing room geometry.

“Multimodal” means a model can work with more than text: here it receives both text and images.

---

## 2. Two modes: curated and baseline

| Mode | What it does | Why it exists |
|---|---|---|
| `curated` | Retrieves approved references, then gives their images and design notes to the model. | The primary prototype workflow. |
| `baseline` | Skips retrieval and asks the model to work from the room photo and brief alone. | A comparison case: does curated grounding improve the result? |

The pipeline branch is explicit:

```python
store = NumpyVectorStore()
if mode == GenerationMode.CURATED:
    store = load_index(settings)

references, retrieval_run = retrieve_references(
    repo=repo,
    settings=settings,
    embedder=embedder,
    store=store,
    project=project,
    mode=mode,
)
```

Source: `vision_engine/src/vision_engine/application/run_pipeline.py`

In baseline mode, `retrieve_references()` records an empty retrieval run and returns no references. The concept and image prompts then state that there are no curated references.

---

# Part I — Beginner level

## 3. What happens when you click “Generate concepts”

### Step 1 — The app accepts and safely stores the room image

The Gradio interface accepts:

- a room photograph
- up to two optional inspiration images
- room type
- short design brief
- budget band
- constraints, such as “do not move the fireplace”

Before storage, the application:

1. accepts only JPG, JPEG, PNG, and WebP;
2. rejects images over the configured maximum size (25 MB by default);
3. opens the image with Pillow to ensure it is a valid image;
4. calculates a SHA-256 hash; and
5. copies the upload into a project-specific local folder.

A **hash** is a fixed-length fingerprint of a file. It lets the system identify the exact uploaded image without depending on its filename.

```python
mime, width, height = validate_image(source, allowed=allowed, max_mb=max_mb)
digest = sha256_file(source)
dest = dest_dir / f"{role}_{digest[:12]}{source.suffix.lower()}"
if not dest.exists():
    shutil.copy2(source, dest)
```

Source: `vision_engine/src/vision_engine/infrastructure/file_store.py`

The input is represented by the `ProjectInput` schema:

```python
class ProjectInput(BaseModel):
    room_image_path: str
    inspiration_image_paths: list[str] = Field(default_factory=list)
    room_type: str
    style_family: str = "Contemporary Europe"
    brief: str = Field(min_length=5, max_length=2000)
    budget_band: str | None = None
    constraints: list[str] = Field(default_factory=list)
    project_type: str = "residential"
```

Source: `vision_engine/src/vision_engine/domain/models.py`

The application then adds a generated project ID, timestamps, and a status to create a `ProjectRecord`.

### Step 2 — It finds suitable approved reference projects

The app searches the local index built from `dataset_factory` gold exports. A **gold export** is a JSONL file containing architect-approved labels. `JSONL` means “JSON Lines”: one JSON object per line.

Only approved records are used in the main index. Restricted-rights images are also excluded.

```python
if record.review_status.value != "approved":
    return False
if record.usage_rights_status == "restricted":
    return False
```

Source: `vision_engine/src/vision_engine/domain/services.py`

The selected references are not copied as final designs. They are visual and descriptive evidence to influence taste, material selection, lighting, and spatial priorities.

### Step 3 — It writes a structured design direction

The system asks the concept model to return JSON, not unstructured prose. This makes the next stage predictable and inspectable.

For example, the `DesignDirection` requires:

```python
class DesignDirection(BaseModel):
    concept_title: str = Field(min_length=3, max_length=120)
    design_intent: str = Field(min_length=10, max_length=1200)
    mood: list[str] = Field(min_length=1, max_length=5)
    material_palette: list[str] = Field(min_length=1, max_length=8)
    lighting_strategy: list[str] = Field(min_length=1, max_length=8)
    furniture_direction: list[str] = Field(min_length=1, max_length=8)
    preserve: list[str] = Field(min_length=1, max_length=12)
    allowed_changes: list[str] = Field(min_length=1, max_length=12)
    likely_trades: list[str] = Field(min_length=1, max_length=8)
    positive_rules: list[str] = Field(min_length=1, max_length=8)
    negative_warnings: list[str] = Field(min_length=1, max_length=8)
```

Source: `vision_engine/src/vision_engine/domain/models.py`

This is important: the design direction becomes the shared “brief” passed into all three image variants. It is also displayed in the UI so a human can understand why the system made a suggestion.

### Step 4 — It generates three visual directions from the room photograph

The image-editing prompt describes three variants:

| Variant | Intent |
|---|---|
| A — closest | Closest to the retrieved material and style cues. |
| B — conservative | Lower intervention; subtler material and furniture changes. |
| C — expressive | Stronger design expression, while still following geometry instructions. |

Each variant starts from the same original room photograph. The system sends the original photo, up to three retrieved reference images, and a variant-specific prompt to the image model.

The central instruction is:

```text
Edit the ORIGINAL ROOM IMAGE. This is an image-editing task, not text-to-image from scratch.
```

Source: `vision_engine/src/vision_engine/prompts/image_edit.jinja2`

### Step 5 — Lloyd reviews the result

The reviewer can save:

- approve / reject / needs edit
- rank
- reference relevance score
- taste score
- geometry-preservation score
- buildability and material-coherence scores
- notes and failure tags

This feedback is stored locally and can be exported as JSONL, CSV, or Parquet for later evaluation or preference learning.

---

# Part II — How the dataset becomes searchable

## 4. From `dataset_factory` to the Vision Engine

`dataset_factory` and `vision_engine` have different roles:

```text
dataset_factory
  raw interior images
  → model draft labels
  → Lloyd review
  → approved gold.jsonl

vision_engine
  approved gold.jsonl + images
  → retrieval index
  → design concepts for a new uploaded room
```

The Vision Engine uses `gold_adapter.py` to map the nested `final_label` in the factory export into a flatter `DatasetRecord`.

### What comes directly from the gold record

| Vision Engine field | Gold source |
|---|---|
| `image_id`, `image_path` | top-level export fields |
| `room_type`, `style_family`, `mood`, `material_palette`, `budget_band` | `final_label` |
| `primary_trade`, `likely_trades_required` | `final_label` |
| `lighting_strategy`, `focal_point`, `visual_hierarchy` | `final_label.positive` |
| positive rationale | `final_label.positive.why_it_works` |
| pitfalls and failure knowledge | fields in `final_label.negative` |

### What is currently derived rather than reviewed upstream

The factory does not currently provide `furniture_style`, `architect_quality_score`, or `buildability_score` as dedicated reviewed fields. The adapter fills them with simple rules.

```python
architect = 3.5
buildability = 3.5
if positive.get("why_it_works") and len(str(positive["why_it_works"])) > 80:
    architect += 0.4
if negative.get("structural_violation"):
    buildability -= 0.8
if status == "approved":
    architect += 0.3
    buildability += 0.2
```

Source: `vision_engine/src/vision_engine/infrastructure/gold_adapter.py`

These are **prototype heuristics**, not Lloyd’s real numerical judgments. “Heuristic” means a practical rule of thumb, not a proven measurement. A later version should add these fields to the dataset-factory review schema so Lloyd can score them directly.

## 5. What is an embedding?

An **embedding** is a list of numbers that represents an item, such as an image or text, in a mathematical space.

The purpose is comparison:

```text
room image / brief  →  [numbers]
curated reference   →  [numbers]

nearer number lists → treated as more similar
```

The index stores two embeddings for each approved reference:

1. image embedding — intended to represent visual similarity;
2. text embedding — represents its labels, rationale, materials, lighting, and other metadata.

That text is assembled into a `text_blob`:

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
    # ... additional design fields
]
return " | ".join(c for c in chunks if c)
```

Source: `vision_engine/src/vision_engine/domain/services.py`

## 6. What the local index contains

For the current small dataset, the system uses NumPy rather than a hosted vector database. NumPy is a Python numerical-computing library.

The index is stored as:

```text
data/indexes/curated.npz    # two numerical matrices and IDs
data/indexes/curated.jsonl  # corresponding DatasetRecord metadata
```

The code normalises each row before saving:

```python
def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms
```

Normalisation scales every vector to length one. It lets the system compare the **direction** of two vectors rather than the magnitude of their raw values.

---

# Part III — Retrieval, explained more deeply

## 7. How a new room is searched

When a project runs, the system builds:

- an embedding of the uploaded room photo;
- an embedding of the combined text brief, room type, style, budget, and constraints;
- a blended room-image embedding if inspiration photos were supplied.

```python
room_emb = embedder.embed_image(room_path)
text_parts = [project.brief, project.room_type, project.style_family or ""]
if project.budget_band:
    text_parts.append(project.budget_band)
text_parts.extend(project.constraints)
text_emb = embedder.embed_text(" ".join(text_parts))
```

Source: `vision_engine/src/vision_engine/application/retrieve_references.py`

If inspiration images are present, the system averages their compatible image vectors with the room vector. This gives the inspiration images some influence over retrieval.

## 8. Cosine similarity

The local index uses **cosine similarity**. It measures how closely two normalised vectors point in the same direction:

```text
cosine similarity = dot product / (length of A × length of B)
```

The core search is:

```python
q = q / norm
scores = matrix @ q
```

Source: `vision_engine/src/vision_engine/infrastructure/vector_store.py`

`matrix @ q` is a fast way to calculate the similarity between the query vector and every indexed reference vector at once.

Higher is generally more similar. A negative score can occur because cosine similarity ranges from -1 to 1.

## 9. Hybrid score

The final ranking is not based on image similarity alone. It combines four factors:

```text
final score =
  0.35 × image similarity
  0.25 × text similarity
  0.25 × metadata compatibility
  0.15 × architect-quality score
```

The default weights come from `configs/app.local.yaml`:

```yaml
image_similarity_weight: 0.35
text_similarity_weight: 0.25
metadata_match_weight: 0.25
architect_quality_weight: 0.15
top_k: 8
final_k: 3
```

The implementation is:

```python
return (
    image_weight * image_similarity
    + text_weight * text_similarity
    + metadata_weight * metadata_match
    + quality_weight * quality_norm
)
```

Source: `vision_engine/src/vision_engine/domain/services.py`

### Metadata compatibility

Metadata is a soft score for fields such as:

- matching room type;
- matching style family;
- matching or nearby budget band;
- matching project type;
- overlap between brief words and materials, mood, lighting, or furniture labels.

For example, an `living_room` reference is not strictly forbidden for a `bedroom` request, but its score is reduced. This avoids losing useful material or lighting precedents while still prioritising appropriate rooms.

### Diversity reranking

After retrieving the top candidates, the system tries to avoid three nearly identical images:

1. a direct overall match;
2. a material / lighting match; and
3. a composition / spatial match.

This happens in `diversify_references()`. It is a lightweight rule-based approach, not a learned reranker.

## 10. Important: fake embeddings are not semantic AI retrieval

The application has two embedding modes:

| `EMBEDDING_PROVIDER` | Current behaviour |
|---|---|
| `fake` | Creates deterministic 64-number vectors from file bytes / text hashes. Useful for tests and plumbing, but not meaningful visual or semantic similarity. |
| `gemini` | Uses Gemini for **text** embeddings. Image embedding still begins with a local hash representation and may blend in a filename-based text embedding. This remains prototype-grade. |

The fake implementation demonstrates the limitation clearly:

```python
def embed_image(self, image_path: Path) -> list[float]:
    data = image_path.read_bytes()
    return _hash_to_vec(b"img:" + data[:4096] + image_path.name.encode(), self.dim)

def embed_text(self, text: str) -> list[float]:
    return _hash_to_vec(b"txt:" + text.encode("utf-8"), self.dim)
```

Source: `vision_engine/src/vision_engine/infrastructure/embedding_clients/fake.py`

These vectors are repeatable, which is helpful for tests, but a hash does not understand that two rooms have similar styles. Therefore:

> When `EMBEDDING_PROVIDER=fake`, retrieval is primarily being guided by labels, metadata, and the heuristic quality score—not genuine semantic image search.

For a stronger prototype, replace this adapter with a real multimodal image embedding model and keep the same `EmbeddingClient` interface.

---

# Part IV — How the new design is generated

## 11. First model call: create a design direction

The concept model receives:

- the uploaded room image;
- up to three retrieved reference images;
- the rendered concept prompt;
- an API response schema generated from `DesignDirection`.

The call is explicitly structured JSON:

```python
response = client.models.generate_content(
    model=self.model_name,
    contents=[types.Content(role="user", parts=parts)],
    config=types.GenerateContentConfig(
        temperature=self.temperature,
        response_mime_type="application/json",
        response_schema=response_schema,
        http_options=types.HttpOptions(timeout=self.timeout_seconds * 1000),
    ),
)
```

Source: `vision_engine/src/vision_engine/infrastructure/multimodal_clients/gemini_client.py`

The Pydantic validation step then rejects malformed or incomplete output:

```python
direction = DesignDirection.model_validate(payload)
```

If validation fails, the raw model response is stored for investigation and the run is marked `validation_failed`.

## 12. What the concept prompt tells the model

The prompt includes:

- user brief and constraints;
- approved reference metadata and “why it works” notes;
- an explicit rulebook;
- geometry-preservation instructions;
- negative constraints; and
- the exact JSON schema to return.

Key prompt instructions include:

```text
Preserve geometry via explicit preserve[] entries.
Allowed changes must not include structural moves.
Positive rules should reflect reference strengths when mode=curated.
Negative warnings should reflect reference pitfalls and geometry risks.
```

Source: `vision_engine/src/vision_engine/prompts/concept_direction.jinja2`

The **rulebook** is the controlled vocabulary from `configs/rulebook.v1.yaml`. It reduces drift by telling the model which style, mood, material, budget, and trade terms are expected.

## 13. Second model call: image-to-image concept generation

The actual visual generation is **image-conditioned generation**:

1. the original room photo is attached as `ORIGINAL ROOM (edit this image)`;
2. up to three curated reference images are attached as material/taste cues;
3. the variant prompt is attached as text;
4. Gemini is asked to return an image; and
5. the image bytes returned by the API are saved as a project variant.

The attachment code is:

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

The API request asks for both text and image modalities:

```python
config=types.GenerateContentConfig(
    temperature=self.temperature,
    response_modalities=["TEXT", "IMAGE"],
    http_options=types.HttpOptions(timeout=self.timeout_seconds * 1000),
)
```

The application extracts `inline_data` image bytes from the response and writes a PNG in:

```text
vision_engine/data/generated/<project_id>/
```

## 14. What “editing on top of the uploaded image” means here

In this implementation, “editing” means:

- the original room photograph is a visual input to the image model;
- the model is instructed to preserve it;
- the model synthesises a new image conditioned on the original image and prompt.

It does **not** mean the software is programmatically repainting walls, moving pixels with a layer editor, or editing a known 3D model of the room.

It also does **not yet** use:

- segmentation masks;
- depth maps;
- edge maps;
- control networks;
- camera calibration;
- detected room planes;
- object detection and pixel-level “do not change” zones;
- post-generation geometry validation.

The current geometry guard is prompt-based:

```text
Preserve perspective, camera position, walls, windows, doors, ceiling lines,
fixed plumbing, fireplace, and radiators. Do not alter room proportions.
Do not add impossible openings. Do not introduce floating fixtures or distorted furniture.
```

Source: `vision_engine/configs/prompts.v1.yaml`

That guidance often helps, but generative image models are probabilistic: they can still move or distort fixed elements. This is why Lloyd’s geometry score and failure tags are part of the review workflow.

## 15. Three variants are three independent generation calls

The current Gemini client makes one request per variant:

```python
for i in range(output_count):
    key = f"variant_{chr(ord('a') + i)}"
    paths.append(_one(prompts[i], key))
```

Source: `vision_engine/src/vision_engine/infrastructure/image_edit_clients/gemini_image_client.py`

They differ through prompt intent:

```python
kinds = [
    ("A", VariantKind.CLOSEST, "Stay closest to the curated references and material cues."),
    ("B", VariantKind.CONSERVATIVE, "Prefer lower intervention; subtler finish and furniture changes."),
    ("C", VariantKind.EXPRESSIVE, "Stronger design expression while still obeying geometry locks."),
]
```

Source: `vision_engine/src/vision_engine/application/generate_variants.py`

This is why generating three real image variants typically takes longer than generating one.

## 16. Fake image editing versus real Gemini editing

This distinction matters when testing:

| Provider | What the variants actually are |
|---|---|
| `MODEL_PROVIDER=fake` | The original image with small colour/contrast/brightness changes and a label. It proves workflow and persistence, not design generation. |
| `MODEL_PROVIDER=gemini` | The Gemini image model is sent original/reference images plus the prompt and produces new image bytes. |

The fake provider does not use the design direction, references, or prompts to draw a new interior:

```python
frame = ImageEnhance.Color(frame).enhance(color)
frame = ImageEnhance.Contrast(frame).enhance(contrast)
frame = ImageEnhance.Brightness(frame).enhance(brightness)
draw.text((24, 24), labels[i], fill=(245, 245, 245))
```

Source: `vision_engine/src/vision_engine/infrastructure/image_edit_clients/fake.py`

Use fake mode for testing. Use Gemini mode only when assessing whether the design generation is useful.

---

# Part V — Schema reference

## 17. The important schemas and their relationships

```text
dataset_factory gold.jsonl
       ↓ adapter
DatasetRecord ──→ vector index ──→ RetrievedReference

User form
       ↓
ProjectInput ──→ ProjectRecord
                       ↓
                  RetrievalRunRecord
                       ↓
                  ConceptRunRecord ──→ DesignDirection
                       ↓
                  GenerationRunRecord ──→ GeneratedVariant (A/B/C)
                       ↓
                  FeedbackEvent
```

### `DatasetRecord`

One approved curated precedent used for retrieval. It combines image location, approved design labels, rationale, pitfalls, trades, quality signals, and provenance.

### `RetrievedReference`

Wraps a `DatasetRecord` for a particular search result. It contains:

- individual image/text/metadata/quality contributions;
- final score;
- human-readable match rationale; and
- a diversity role such as `direct_match`.

### `DesignDirection`

The contract between the concept model and image generation. It is the system’s explicit answer to: “what should change and what must stay?”

### `GeneratedVariant`

Records the saved image file, its generation run, and its role: closest, conservative, or expressive.

### `FeedbackEvent`

The human-review event that makes evaluation possible. The fields are constrained: rankings are 1–3, quality scores are 1–5, and failure tags come from an enum.

---

# Part VI — Advanced implementation details

## 18. Provider abstraction

The application layer does not call Gemini directly. It asks factories to construct a client:

```text
application layer
    ↓
provider interface / factory
    ↓
fake client or Gemini client
```

This separation is called a **port-and-adapter** design:

- the **port** is the stable interface the application needs;
- the **adapter** is the provider-specific implementation.

It lets tests run offline and lets engineering swap an image model later without rewriting the project, retrieval, or feedback workflows.

## 19. Retries and error categories

Gemini requests use exponential-jitter retries for transient problems such as timeouts, rate limits, and temporary service errors.

```python
@retry(
    reraise=True,
    stop=stop_after_attempt(self.max_attempts),
    wait=wait_exponential_jitter(initial=1, max=20),
    retry=retry_if_exception(_is_transient),
)
```

“Exponential backoff” means retry waits grow between attempts. “Jitter” adds randomness so many clients do not retry at exactly the same time.

Permanent failures, malformed JSON, missing generated images, and schema validation failures are recorded rather than silently treated as successes.

## 20. Local persistence and audit trail

SQLite stores relational records in:

```text
data/database/vision_engine.db
```

Main tables:

| Table | Purpose |
|---|---|
| `projects` | User brief, local image paths, status, timestamps. |
| `uploads` | Hash, image size/type, and role for each copied image. |
| `dataset_records` | Approved curated records included in the local retrieval store. |
| `retrieval_runs` | Query text, references selected, score breakdown. |
| `concept_runs` | Prompt/model metadata, structured direction, raw response, errors. |
| `generation_runs` | Model, prompt version, reference IDs, latency, status. |
| `generated_variants` | Variant image paths and A/B/C role. |
| `review_events` | Lloyd’s decision, ranking, scores, notes, and failure tags. |
| `prompt_versions` | Prompt name and rendered content hash. |
| `model_versions` | Provider/model and role used. |

The design-direction response is also saved as a raw JSON file under:

```text
data/generated/raw/<project_id>/
```

This audit trail answers: “Which model, prompt, references, and inputs produced this image?”

## 21. Feedback and evaluation

Feedback is not only a note; it is structured data. The evaluator calculates:

- approval rate;
- average geometry score;
- average taste score;
- severe geometry failures;
- failure-tag counts.

Current targets are:

```python
"geometry_avg_min": 4.0,
"severe_geometry_max_rate": 0.2,
"curated_preference_min": 0.7,
```

Source: `vision_engine/src/vision_engine/application/evaluate.py`

The 70% curated-preference target only becomes meaningful when reviewers evaluate matched curated and baseline runs for the same rooms.

---

# Part VII — Configuration, safety, and limitations

## 22. Configuration hierarchy

| File | Role |
|---|---|
| `vision_engine/.env` | Secrets and provider/model selection. Do not commit it. |
| `vision_engine/configs/app.local.yaml` | Timeouts, retrieval weights, paths, image limits, variant count. |
| `vision_engine/configs/rulebook.v1.yaml` | Controlled interior-design vocabulary. |
| `vision_engine/configs/prompts.v1.yaml` | Shared geometry lock and negative constraints. |
| `vision_engine/src/vision_engine/prompts/*.jinja2` | Versioned concept and image-edit prompt templates. |

The current defaults allow JPG/JPEG/PNG/WebP images up to 25 MB, use three variants, retrieve up to eight candidate records, then keep three final references.

## 23. Privacy and rights

- Uploads, outputs, raw model JSON, and SQLite data are stored locally.
- Source images are only indexed when their rights status is not `restricted`.
- If `MODEL_PROVIDER=gemini`, the room photo, selected reference images, and prompts are sent to Gemini to produce the concept and output image.
- API keys belong in `.env`, never in source code or documentation.
- Delete a project’s files with the local file-store deletion capability when retention is no longer appropriate.

## 24. Known prototype limitations

1. **Geometry lock is instruction-only.** It is not a guarantee that the model will preserve the room.
2. **No real image semantic retrieval in fake mode.** Hash embeddings only provide deterministic test plumbing.
3. **Gemini image embedding is still prototype-grade.** It uses a local image-byte hash and may use a filename-oriented text embedding; it is not a dedicated image-embedding pipeline.
4. **Quality scores are partly heuristic.** They should become curator-reviewed dataset fields.
5. **No mask/depth/edge conditioning.** Future geometry work should introduce segmentation or structural conditioning.
6. **No technical validation.** The results are not construction instructions, pricing, compliance, or safety guidance.
7. **No automatic preference learning yet.** Feedback is captured and exported, but it does not currently retrain or rerank models automatically.
8. **Reference count is small.** With 45 approved records, coverage and diversity remain limited.

## 25. Recommended next technical improvements

1. Replace fake image embeddings with a proven multimodal embedding model.
2. Add curator-owned `furniture_style`, architect-quality, and buildability ratings upstream in `dataset_factory`.
3. Add masks or structural conditioning for windows, doors, fireplace, radiators, and fixed plumbing.
4. Add automated geometry checks after generation (for example, line/edge comparison and reviewer-assisted masks).
5. Persist a full input fingerprint per generation for stronger reproducibility and idempotency.
6. Run a formal curated-vs-baseline evaluation set with the same rooms and consistent review criteria.

---

## 26. Glossary

| Term | Meaning here |
|---|---|
| **Baseline** | A generic generation run with no curated references. |
| **BoQ** | Bill of Quantities: construction materials/work quantities. Out of scope. |
| **Controlled vocabulary / rulebook** | A fixed list of approved labels to prevent inconsistent terminology. |
| **Cosine similarity** | A numerical measure of how similar two embeddings are. |
| **Curated** | Grounded in architect-reviewed reference data. |
| **Embedding** | A vector (number list) representing text or an image for comparison. |
| **Geometry preservation** | Keeping fixed room elements and proportions visually stable. Currently prompt-guided, not guaranteed. |
| **Gold data** | Human-approved labels exported from `dataset_factory`. |
| **Grounding** | Giving a model specific, relevant evidence instead of relying only on its general training. |
| **Heuristic** | A useful practical rule, not a guaranteed or learned truth. |
| **Image-conditioned generation** | Generating an image while supplying another image as context. |
| **JSON schema** | A formal contract describing required fields and their types. |
| **Multimodal model** | A model that can consume or create more than one medium, such as text and images. |
| **Pydantic** | Python library used to validate and constrain structured data. |
| **Prompt** | The text instructions and context sent to a generative model. |
| **Reranking** | Selecting the best final results after an initial search. |
| **Vector index / vector store** | A saved collection of embeddings and matching metadata used for similarity search. |

---

## Related documents

- Engineering requirements: `docs/erds/vision_engine_prototype_engineering_requirements.md`
- Operator runbook: `docs/vision_engine_overview_runbook.md`
- Dataset-factory runbook: `docs/dataset_factory_overview_runbook.md`
- Dataset-factory requirements: `docs/erds/hybrid_rulebook_model_engineering_requirements.md`

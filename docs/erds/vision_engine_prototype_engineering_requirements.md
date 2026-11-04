# Vision Engine Prototype — Engineering Requirements

## 1. Purpose

Build a local-first Python prototype that:

1. accepts a room image, inspiration images, and a short design brief
2. retrieves relevant architect-curated references from Lloyd's dataset
3. converts those references into a structured design direction
4. edits the original room image while preserving core geometry
5. generates 2–3 tasteful design variants
6. shows materials, lighting, furniture direction, likely trades, and warnings
7. captures Lloyd's approve/reject/rank/edit feedback

The prototype is a **design concept tool**, not a technical design, final specification, BoQ, or compliance guarantee.

---

## 2. Primary Prototype Goal

Prove that:

> Architect-curated retrieval produces more relevant, tasteful, and consistent room redesigns than an ungrounded image-generation baseline.

The first prototype should optimise for:
- design quality
- geometry preservation
- explainability
- fast iteration
- feedback capture

It should not optimise for:
- production scale
- exact quantities
- final pricing
- technical compliance
- marketplace operations

---

## 3. User Roles

### 3.1 End User
Uploads:
- room image
- optional inspiration images
- short brief
- optional style, budget, and constraints

Receives:
- retrieved references
- design rationale
- 2–3 edited room images
- materials and likely trades summary

### 3.2 Architect Reviewer
Lloyd reviews:
- reference relevance
- concept quality
- geometry preservation
- material coherence
- likely buildability
- positive and negative design notes

### 3.3 Technical Operator
Runs:
- local indexing
- model calls
- evaluation
- export
- prototype application

---

## 4. Scope

### In Scope
- local Python application
- Gradio interface
- local dataset ingestion
- image and text embeddings
- local vector retrieval
- structured concept generation
- image editing through a pluggable provider
- feedback storage
- experiment logging
- baseline comparison
- export to JSONL, CSV, and Parquet

### Out of Scope
- final technical drawings
- guaranteed geometry reconstruction
- exact dimensions from a single image
- regulatory compliance checks
- final BoQ
- contractor marketplace
- supplier APIs
- authentication
- cloud deployment
- fine-tuning in iteration 1

---

## 5. Recommended Architecture

```text
vision_engine/
├── app/
│   ├── ui/
│   │   └── gradio_app.py
│   ├── application/
│   │   ├── create_project.py
│   │   ├── retrieve_references.py
│   │   ├── generate_concept.py
│   │   ├── generate_variants.py
│   │   └── record_feedback.py
│   ├── domain/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── enums.py
│   │   └── services.py
│   ├── infrastructure/
│   │   ├── sqlite_repository.py
│   │   ├── file_store.py
│   │   ├── vector_store.py
│   │   ├── embedding_clients/
│   │   │   ├── base.py
│   │   │   └── local_or_api.py
│   │   ├── multimodal_clients/
│   │   │   ├── base.py
│   │   │   └── gemini_client.py
│   │   └── image_edit_clients/
│   │       ├── base.py
│   │       └── gemini_image_client.py
│   ├── prompts/
│   │   ├── concept_direction.jinja2
│   │   ├── image_edit.jinja2
│   │   └── evaluation.jinja2
│   └── cli.py
├── configs/
│   ├── app.local.yaml
│   ├── rulebook.v1.yaml
│   └── prompts.v1.yaml
├── data/
│   ├── curated/
│   ├── uploads/
│   ├── generated/
│   ├── indexes/
│   ├── exports/
│   └── database/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── golden/
├── .env.example
├── pyproject.toml
├── README.md
└── Makefile
```

### Architecture Principles

- separate domain logic from model providers
- keep prompts versioned
- use provider interfaces so image-generation models can be swapped
- persist every model input and output
- keep human review as the final source of truth
- make every run reproducible

---

## 6. Core User Flow

### Step 1 — Create Project
The user provides:
- one room image
- optional inspiration images
- room type
- short brief
- optional budget band
- optional constraints

Example:

```text
Room type: living room
Brief: warm contemporary European, calmer lighting, retain windows and fireplace
Budget: medium-high
Constraints: do not move walls, doors, windows, radiators, or fireplace
```

### Step 2 — Analyse Inputs
The system creates:
- image embedding for the room
- image embeddings for inspiration images
- text embedding for the brief
- structured project metadata

### Step 3 — Retrieve Curated References
The system queries Lloyd's approved dataset.

Retrieval should combine:
- image similarity
- text similarity
- rule-based filters
- metadata compatibility

Example filters:
- room type
- style family
- budget band
- mood
- material palette
- build complexity

### Step 4 — Build Structured Design Direction
The retrieved references are converted into:

- concept title
- design intent
- mood
- colour direction
- material palette
- lighting strategy
- furniture direction
- focal point
- spatial hierarchy
- elements to preserve
- elements allowed to change
- likely trades
- positive design rules
- negative warnings

### Step 5 — Edit Original Room Image
The image-editing model receives:

- original room image
- selected curated references
- structured design direction
- geometry lock instructions
- explicit allowed and forbidden changes

The system generates 2–3 variants.

### Step 6 — Review and Compare
The UI shows:
- original room
- retrieved references
- generated variants
- design explanation
- material/trade summary
- positive and negative design logic

### Step 7 — Capture Feedback
Lloyd can:
- approve
- reject
- rank variants
- edit concept metadata
- flag geometry errors
- flag taste errors
- record why one variant is better

---

## 7. Dataset Requirements

The prototype should consume only reviewed or explicitly marked draft records.

### Minimum Required Fields

```text
image_id
image_path
project_type
room_type
style_family
mood
material_palette
lighting_strategy
furniture_style
budget_band
architect_quality_score
buildability_score
positive_why_it_works
negative_common_pitfalls
primary_trade
likely_trades_required
review_status
```

### Recommended Additional Fields

```text
focal_point
circulation_strategy
visual_hierarchy
proportion_rule
material_relationship
appropriate_room_conditions
design_failure
why_it_fails
scale_problem
material_conflict
lighting_problem
impractical_detail
generic_ai_artifact
structural_violation
```

### Dataset Status

Use:
- `draft`
- `reviewed`
- `approved`
- `rejected`

Only `approved` records should be used in the main retrieval index.

---

## 8. Retrieval Design

### 8.1 Hybrid Retrieval
Use a weighted score:

```text
final_score =
    image_similarity_weight * image_similarity
  + text_similarity_weight * text_similarity
  + metadata_match_weight * metadata_match
  + architect_quality_weight * architect_quality
```

### 8.2 Metadata Filters
Apply hard or soft filters for:
- room type
- style family
- budget band
- project type

### 8.3 Reranking
After first-stage retrieval, rerank top candidates using:
- brief fit
- inspiration fit
- Lloyd quality score
- diversity across references

### 8.4 Diversity Rule
Do not return five near-duplicate references.

At least:
- 1 strong direct match
- 1 material/lighting match
- 1 composition or spatial match

---

## 9. Concept Generation Requirements

The concept generator must return structured JSON.

Example:

```json
{
  "concept_title": "Warm Contemporary European",
  "design_intent": "Create a calm, tactile living room...",
  "mood": ["warm", "calm", "restrained"],
  "material_palette": ["oak", "limewash", "linen", "brushed brass"],
  "lighting_strategy": [
    "retain natural light",
    "add layered low-level lighting",
    "avoid flat overhead-only illumination"
  ],
  "furniture_direction": [
    "low-profile sofa",
    "natural upholstery",
    "simple sculptural side table"
  ],
  "preserve": ["windows", "fireplace", "door positions", "room proportions"],
  "allowed_changes": ["wall finish", "floor finish", "lighting", "furniture", "joinery"],
  "likely_trades": ["decorator", "electrician", "joiner"],
  "positive_rules": ["maintain restrained palette", "use tonal material contrast"],
  "negative_warnings": ["avoid oversized furniture", "avoid excessive decorative lighting"]
}
```

### Validation
Use Pydantic for:
- required fields
- enums
- list limits
- maximum text length
- invalid value rejection

---

## 10. Image Editing Requirements

### 10.1 Editing Strategy
The original room image must be used as the base image.

The system should request:
- preserve perspective
- preserve camera position
- preserve walls, windows, doors, ceiling lines, fixed plumbing, fireplace, and radiators
- alter only approved finishes, furniture, lighting, joinery, and decorative elements

### 10.2 Inputs to Image Model
- original image
- 1–3 curated references
- structured design direction
- negative constraints
- optional mask later

### 10.3 Output Variants
Generate:
- Variant A: closest to retrieved references
- Variant B: more conservative / lower intervention
- Variant C: stronger design expression

### 10.4 Negative Constraints
Include explicit instructions such as:

```text
Do not move windows, doors, structural walls, fireplaces, radiators, or plumbing.
Do not alter room proportions.
Do not add impossible openings.
Do not introduce floating fixtures or distorted furniture.
Do not copy a reference image literally.
```

### 10.5 Model Abstraction
Implement:

```python
class ImageEditClient(Protocol):
    def edit_room(
        self,
        room_image_path: str,
        reference_image_paths: list[str],
        design_direction: dict,
        output_count: int = 3,
    ) -> list[str]:
        ...
```

This allows the model provider to be replaced later.

---

## 11. UI Requirements

Use Gradio for iteration 1.

### Screen 1 — Inputs
- room image upload
- inspiration image upload
- room type
- style family
- brief
- budget band
- constraints
- generate button

### Screen 2 — Retrieved References
- top 3 references
- match rationale
- quality scores
- metadata

### Screen 3 — Generated Concepts
- original image
- Variant A/B/C
- before/after comparison
- concept rationale
- materials
- lighting
- likely trades
- warnings

### Screen 4 — Architect Review
- approve/reject
- rank variants
- free-text edit
- failure reason checkboxes
- save feedback

---

## 12. Feedback Schema

```json
{
  "project_id": "proj_001",
  "variant_id": "var_002",
  "reviewer": "lloyd",
  "decision": "approved",
  "rank": 1,
  "reference_relevance_score": 4,
  "taste_quality_score": 5,
  "geometry_preservation_score": 3,
  "buildability_score": 4,
  "material_coherence_score": 5,
  "positive_notes": "Strong restrained palette and proportion.",
  "negative_notes": "Pendant placement conflicts with ceiling condition.",
  "failure_tags": ["lighting_problem"],
  "created_at": "..."
}
```

This feedback becomes the future preference-learning dataset.

---

## 13. Baseline Evaluation

Every test project should run two modes:

### Baseline
Original image + generic prompt only

### Curated
Original image + retrieved references + Lloyd metadata + positive/negative rules

Compare both using Lloyd ratings.

### Core Evaluation Metrics

- reference relevance
- taste quality
- geometry preservation
- material coherence
- room suitability
- buildability plausibility
- generic AI artifact rate
- percentage of curated outputs preferred over baseline
- time to acceptable concept
- average number of retries

### Prototype Success Criteria

A reasonable early target:

- Lloyd prefers curated output over baseline in at least 70% of test cases
- average geometry score of at least 4/5
- at least one acceptable variant within three generations
- fewer than 20% severe geometry failures
- concept explanation matches selected references in at least 80% of tests

---

## 14. Local Technology Stack

### Required
- Python 3.11+
- Gradio
- Pydantic v2
- SQLite
- SQLAlchemy
- Pillow
- pandas or polars
- pyarrow
- PyYAML
- Jinja2
- Typer
- Rich
- tenacity
- pytest

### Retrieval
Choose one:
- FAISS
- Chroma local
- SQLite plus vector extension
- simple NumPy index for the first 60 records

For 60 records, a NumPy or FAISS index is sufficient.

---

## 15. Local Persistence

### SQLite Tables
- `projects`
- `uploads`
- `dataset_records`
- `retrieval_runs`
- `concept_runs`
- `generation_runs`
- `generated_variants`
- `review_events`
- `prompt_versions`
- `model_versions`

### File Storage
- source uploads
- curated references
- generated images
- model raw responses
- exports

---

## 16. Observability and Audit

Log:
- model provider
- model name
- prompt version
- dataset version
- retrieved reference IDs
- generation settings
- latency
- failures
- user feedback

Every output should be reproducible from:
- input image
- references
- prompt version
- config
- model name

---

## 17. Error Handling

Handle:
- invalid images
- unsupported format
- empty retrieval result
- malformed model JSON
- image model timeout
- provider quota failure
- generated image missing
- duplicate upload
- rejected dataset record

Failures should:
- be logged
- not terminate the whole app
- return a clear UI message
- preserve the raw error for debugging

---

## 18. Testing Strategy

### Unit Tests
- schema validation
- rulebook loading
- scoring logic
- retrieval filtering
- prompt rendering
- feedback validation

### Integration Tests
- upload → retrieve → concept JSON
- concept JSON → image edit
- review → SQLite persistence
- export → JSONL/CSV

### Golden Tests
Maintain 5–10 fixed room images with:
- expected retrieved references
- expected schema fields
- approved example outputs

### Mock Providers
Every provider interface must have a mock implementation to avoid API calls in tests.

---

## 19. Security and Privacy

- store API keys only in `.env`
- do not commit client room images
- maintain source and licensing metadata
- allow local deletion of projects
- do not expose raw image paths in public interfaces
- make all outputs clearly marked as concept visuals

---

## 20. Local Runbook

### 20.1 Prerequisites

```bash
python3 --version
```

Use Python 3.11 or newer.

### 20.2 Create Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 20.3 Configure Environment

Create `.env`:

```bash
APP_ENV=local
MODEL_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
DATABASE_URL=sqlite:///data/database/vision_engine.db
LOG_LEVEL=INFO
```

### 20.4 Prepare Curated Dataset

Place images in:

```text
data/curated/images/
```

Place reviewed metadata in:

```text
data/curated/metadata.csv
```

### 20.5 Build Index

```bash
python -m app.cli build-index \
  --metadata data/curated/metadata.csv \
  --images data/curated/images \
  --output data/indexes/curated.faiss
```

### 20.6 Run Prototype

```bash
python -m app.ui.gradio_app
```

Open the local URL printed by Gradio.

### 20.7 Export Feedback

```bash
python -m app.cli export-feedback \
  --output data/exports/feedback.jsonl
```

---

## 21. Development Plan

### Phase 1 — Foundation
- implement schemas
- implement SQLite
- ingest curated dataset
- create local retrieval index

### Phase 2 — Concept Layer
- upload flow
- hybrid retrieval
- structured concept generation
- display retrieved references

### Phase 3 — Image Editing
- add provider interface
- generate 2–3 room variants
- preserve geometry through prompt constraints
- log all inputs and outputs

### Phase 4 — Feedback
- Lloyd review form
- ranking
- failure tags
- export feedback dataset

### Phase 5 — Evaluation
- curated vs baseline comparison
- batch test on 10–20 rooms
- analyse failure patterns
- decide whether to expand dataset

---

## 22. Fine-Tuning Decision

Do not fine-tune the image model in iteration 1.

Fine-tuning should be considered only after collecting:
- many real room inputs
- accepted and rejected variants
- Lloyd's rankings
- reliable geometry failure labels
- consistent style and material labels

Initially, use the curated dataset for:
- retrieval
- grounding
- prompt construction
- evaluation
- feedback collection

---

## 23. Key Risks

### Taste Risk
The model may still produce generic designs.

Mitigation:
- strong reference retrieval
- explicit positive and negative rules
- Lloyd ranking loop

### Geometry Risk
The model may alter fixed elements.

Mitigation:
- explicit geometry constraints
- image-editing rather than text-to-image
- masks and depth conditioning later

### Dataset Risk
Sixty records may not cover enough variation.

Mitigation:
- restrict the prototype to one narrow style and room type
- measure retrieval confidence
- expand only where gaps are observed

### Copyright Risk
Reference images may not be reusable as training assets.

Mitigation:
- retain provenance
- use references for internal retrieval and evaluation only
- prefer licensed or studio-owned images for commercial deployment

---

## 24. Final Recommendation

Build the first prototype as:

**Gradio + Python + SQLite + local vector retrieval + Gemini for structured concept generation + a pluggable Gemini image-editing client.**

The first release should demonstrate:

```text
room upload
→ curated reference retrieval
→ structured design direction
→ 2–3 edited room concepts
→ Lloyd review and ranking
```

The primary proof is not that the system can generate an attractive image. It is that **Lloyd's curated dataset consistently improves taste, relevance, and design coherence while preserving the user's room**.

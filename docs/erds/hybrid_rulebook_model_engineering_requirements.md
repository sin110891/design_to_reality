# Hybrid Rulebook + Multimodal Model Dataset Builder
## Engineering Requirements, Architecture, Schema Strategy, and Local Runbook

**Version:** 1.0  
**Status:** Implementation specification  
**Target:** Local-first Python application  
**Primary users:** Technical founder/operator and architect curator  

---

## 1. Executive summary

This document specifies a local Python system that converts a folder of curated interior-design images into a structured, architect-reviewed dataset.

The system combines:

1. **A controlled rulebook** — approved values and definitions for fields such as style, mood, materials, budget, and trades.
2. **A multimodal model** — initially Gemini or another provider capable of understanding images and returning structured JSON.
3. **Deterministic validation** — Pydantic schemas, enums, normalization, and business rules.
4. **Human review** — Lloyd approves, edits, or rejects the model's draft labels.
5. **Versioned outputs** — local SQLite records and exportable CSV, JSONL, and Parquet files.

The model does not create ground truth. It creates a draft. The architect-reviewed record becomes the gold dataset.

---

## 2. Important schema decision

### Will schemas be created, or must they be supplied?

**Both.** The engineering implementation should create the technical schema files and validation code, but the domain content must be agreed with Lloyd.

There are three separate schema artefacts:

### 2.1 Technical record schema — created by engineering

This defines:

- field names
- types
- required versus optional fields
- list limits
- identifier formats
- timestamps
- review states
- provenance and model metadata

It should be implemented in Python using Pydantic and exported as JSON Schema.

### 2.2 Domain rulebook — supplied collaboratively

This defines the allowed design vocabulary, for example:

- approved `style_family` values
- approved moods
- approved material names
- budget-band definitions
- trade categories
- curator guidance for positive and negative assessments

Lloyd supplies the architectural meaning; engineering converts it into a machine-readable YAML rulebook.

### 2.3 Positive and negative design schema — created jointly

Engineering proposes the structure. Lloyd defines what each field means in practice and supplies examples.

Recommended positive fields:

- `design_move`
- `why_it_works`
- `focal_point`
- `material_relationship`
- `lighting_strategy`
- `proportion_rule`
- `circulation_strategy`
- `visual_hierarchy`
- `appropriate_room_conditions`

Recommended negative fields:

- `design_failure`
- `why_it_fails`
- `scale_problem`
- `material_conflict`
- `lighting_problem`
- `impractical_detail`
- `generic_ai_artifact`
- `structural_violation`

For version 1, these should be optional nested objects. They become mandatory only after the first review cycle proves that Lloyd can label them consistently.

### Decision rule

Do not ask a model to invent the ontology. Use the model to populate a human-approved ontology.

---

## 3. Goals

The local application must:

- ingest a directory of images
- detect duplicates using content hashes
- preserve source and licensing provenance
- call a multimodal model with a controlled rulebook
- request structured output
- validate every response
- retry recoverable failures safely
- preserve raw model output for audit
- allow human review in a spreadsheet-first workflow
- import reviewed records
- export approved gold data
- remain provider-agnostic
- run entirely from a local Python environment except model API calls

---

## 4. Non-goals for version 1

Do not build the following yet:

- image-generation workflow
- vector database or RAG search service
- model fine-tuning
- cloud deployment
- multi-tenant authentication
- distributed orchestration
- autonomous multi-agent loops
- a production web application
- automatic pricing or Bill of Quantities generation

The first goal is a reliable local **dataset factory**.

---

## 5. System workflow

```text
Image folder
   ↓
Ingestion and hashing
   ↓
Image registry in SQLite
   ↓
Rulebook + prompt + image
   ↓
Multimodal model draft
   ↓
Pydantic validation and normalization
   ↓
Draft record stored with audit metadata
   ↓
CSV review by Lloyd
   ↓
Reviewed CSV import
   ↓
Approved gold dataset export
```

---

## 6. Architecture principles

### 6.1 Local-first

Use local files and SQLite. Avoid cloud infrastructure until the workflow is stable.

### 6.2 Ports and adapters

Domain logic must not depend directly on Gemini, SQLite, CSV, or a specific UI.

Define interfaces for:

- model provider
- repository
- image storage
- exporter
- clock / ID generation where useful for testing

### 6.3 Deterministic shell around probabilistic core

The model is probabilistic. Everything around it should be deterministic:

- controlled inputs
- versioned prompts
- versioned rulebook
- typed output
- validation
- retries
- audit trail
- human approval

### 6.4 Human-in-the-loop by design

`approved` data must never be created directly from an unreviewed model response.

### 6.5 Idempotency

A rerun against an unchanged image, prompt version, rulebook version, and model configuration must not silently create another record.

### 6.6 Observability

Every run must report:

- number discovered
- number skipped as duplicates
- number successfully labelled
- number validation-failed
- number provider-failed
- estimated or returned token usage where available
- elapsed time

---

## 7. Recommended repository structure

```text
hybrid-design-dataset/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── Makefile
├── configs/
│   ├── app.local.yaml
│   └── rulebook.v1.yaml
├── data/
│   ├── raw_images/
│   ├── review/
│   ├── exports/
│   └── app.db
├── src/design_dataset/
│   ├── __init__.py
│   ├── cli.py
│   ├── settings.py
│   ├── domain/
│   │   ├── enums.py
│   │   ├── models.py
│   │   ├── rulebook.py
│   │   ├── policies.py
│   │   └── errors.py
│   ├── application/
│   │   ├── ingest.py
│   │   ├── label.py
│   │   ├── review.py
│   │   └── export.py
│   ├── infrastructure/
│   │   ├── sqlite_repository.py
│   │   ├── filesystem.py
│   │   ├── hashing.py
│   │   ├── exporters.py
│   │   └── model_clients/
│   │       ├── base.py
│   │       ├── gemini.py
│   │       └── fake.py
│   └── prompts/
│       └── label_image_v1.jinja2
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

Use a `src/` layout to prevent accidental imports from the repository root.

---

## 8. Domain model

### 8.1 Core enums

```python
from enum import StrEnum

class ReviewStatus(StrEnum):
    INGESTED = "ingested"
    DRAFT = "draft"
    VALIDATION_FAILED = "validation_failed"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
```

Controlled design values should be loaded from the YAML rulebook rather than hard-coded into Python where frequent domain change is expected.

### 8.2 Draft label model

```python
from pydantic import BaseModel, Field

class PositiveDesignKnowledge(BaseModel):
    design_move: str | None = None
    why_it_works: str = Field(min_length=5, max_length=800)
    focal_point: str | None = None
    material_relationship: str | None = None
    lighting_strategy: str | None = None
    proportion_rule: str | None = None
    circulation_strategy: str | None = None
    visual_hierarchy: str | None = None
    appropriate_room_conditions: list[str] = Field(default_factory=list, max_length=8)

class NegativeDesignKnowledge(BaseModel):
    design_failure: str | None = None
    why_it_fails: str = Field(min_length=5, max_length=800)
    scale_problem: str | None = None
    material_conflict: str | None = None
    lighting_problem: str | None = None
    impractical_detail: str | None = None
    generic_ai_artifact: str | None = None
    structural_violation: str | None = None

class DesignLabelDraft(BaseModel):
    style_family: str
    mood: list[str] = Field(min_length=1, max_length=5)
    material_palette: list[str] = Field(min_length=1, max_length=8)
    budget_band: str
    primary_trade: str
    likely_trades_required: list[str] = Field(min_length=1, max_length=8)
    room_type: str | None = None
    positive: PositiveDesignKnowledge
    negative: NegativeDesignKnowledge
    confidence_notes: str = Field(max_length=500)
    visible_uncertainties: list[str] = Field(default_factory=list, max_length=8)
```

### 8.3 Persisted record

The persisted record must additionally include:

- `record_id`
- `image_id`
- `file_path`
- `sha256`
- `source_type`
- `source_url`
- `usage_rights_status`
- `rulebook_version`
- `prompt_version`
- `provider`
- `model_name`
- `model_request_id`
- `raw_response_json`
- `validation_errors`
- `status`
- `curator_name`
- `curator_notes`
- `created_at`
- `updated_at`
- `approved_at`

---

## 9. Rulebook specification

Example `configs/rulebook.v1.yaml`:

```yaml
version: "1.0.0"
subset_name: "Contemporary Europe"

fields:
  style_family:
    type: single
    allowed_values:
      - Contemporary Europe
    guidance: >
      Select Contemporary Europe only when the space demonstrates restrained
      material composition, contemporary European references, controlled visual
      hierarchy, and contextually appropriate detailing.

  mood:
    type: multiple
    min_items: 1
    max_items: 5
    allowed_values:
      - warm
      - calm
      - restrained
      - tactile
      - intimate
      - bright
      - playful
      - premium
      - utilitarian

  material_palette:
    type: multiple
    min_items: 1
    max_items: 8
    allowed_values:
      - oak
      - walnut
      - ash
      - limewash
      - plaster
      - brass
      - stainless_steel
      - marble
      - terrazzo
      - ceramic_tile
      - linen
      - glass

  budget_band:
    type: single
    allowed_values:
      - low
      - medium
      - medium_high
      - high
    definitions:
      low: "Primarily decorative changes and readily available products."
      medium: "Some bespoke elements with controlled material cost."
      medium_high: "Multiple bespoke components or premium finishes."
      high: "Extensive bespoke design, specialist fabrication, or premium materials."

  primary_trade:
    type: single
    allowed_values:
      - decorator
      - joiner
      - tiler
      - electrician
      - plumber
      - plasterer
      - flooring_installer
      - general_builder
      - furniture_supplier

  likely_trades_required:
    type: multiple
    min_items: 1
    max_items: 8
    allowed_values:
      - decorator
      - joiner
      - tiler
      - electrician
      - plumber
      - plasterer
      - flooring_installer
      - general_builder
      - furniture_supplier
```

### Rulebook governance

- Lloyd owns design definitions.
- Engineering owns serialization, validation, and versioning.
- Every change requires a new semantic version.
- Never overwrite a rulebook used by previous records.
- Record the rulebook version on every inference.

---

## 10. Prompt requirements

Prompts must be files under source control and must include:

- system role
- task boundary
- rulebook values and definitions
- distinction between visible evidence and inference
- prohibition on invented categories
- requirement to expose uncertainty
- positive and negative analysis guidance
- exact structured response schema

Example prompt principles:

```text
You are producing a draft architectural curation record.
Use only evidence visible in the supplied image.
Use only allowed controlled vocabulary values.
Do not infer hidden structure, construction condition, quantities, or compliance.
For uncertain items, add an explanation to visible_uncertainties.
Return only JSON matching the supplied response schema.
```

Do not rely only on “return JSON” in natural language. Use the provider's structured-output capability and then validate again in Python.

---

## 11. Model-provider interface

```python
from typing import Protocol
from pathlib import Path

class MultimodalLabelClient(Protocol):
    def label_image(
        self,
        *,
        image_path: Path,
        prompt: str,
        response_schema: dict,
    ) -> tuple[dict, "ModelCallMetadata"]:
        ...
```

### Required implementations

- `GeminiClient`: real multimodal inference
- `FakeModelClient`: deterministic local tests

### Provider rules

- set explicit timeout
- bounded retries with exponential backoff and jitter
- retry only transient failures
- do not retry schema or business-rule failures blindly
- capture provider request IDs
- never log API keys
- make model name configurable

---

## 12. Agentic engineering approach

Do not use an open-ended autonomous agent framework for version 1.

Use an explicit state machine:

```text
DISCOVERED
  → INGESTED
  → LABEL_REQUESTED
  → DRAFT_VALIDATED
  → EXPORTED_FOR_REVIEW
  → REVIEWED
  → APPROVED or REJECTED
```

Recommended bounded agents/services:

1. **Ingestion service** — hashes and registers files.
2. **Labelling service** — makes one model call per image.
3. **Validation service** — validates and normalizes output.
4. **Review service** — exports/imports human decisions.
5. **Dataset export service** — emits approved records only.

Each service should have:

- one responsibility
- typed inputs and outputs
- no hidden side effects
- explicit failure states
- maximum retry count
- audit metadata

This is more reliable than a group of agents conversing until they decide they are finished.

---

## 13. Data storage

### SQLite tables

#### `images`

- `image_id`
- `relative_path`
- `sha256`
- `mime_type`
- `width`
- `height`
- `source_type`
- `source_url`
- `usage_rights_status`
- `created_at`

#### `label_runs`

- `run_id`
- `image_id`
- `rulebook_version`
- `prompt_version`
- `provider`
- `model_name`
- `request_fingerprint`
- `raw_response_json`
- `parsed_response_json`
- `status`
- `error_type`
- `error_message`
- `created_at`

#### `curation_records`

- `record_id`
- `run_id`
- structured label columns or normalized JSON
- `review_status`
- `curator_name`
- `curator_notes`
- `reviewed_at`
- `approved_at`

#### `review_events`

- `event_id`
- `record_id`
- `field_name`
- `old_value`
- `new_value`
- `actor`
- `created_at`

### Transaction discipline

- use explicit transactions
- enable foreign keys on each connection
- use migrations from the beginning; Alembic is appropriate if SQLAlchemy is used
- back up the SQLite file before bulk review imports

---

## 14. Idempotency and request fingerprinting

Construct a request fingerprint from:

```text
sha256(image bytes)
+ rulebook version
+ prompt version
+ provider
+ model name
+ relevant generation settings
```

Hash the combined value. If a successful record already exists for that fingerprint, skip inference unless `--force` is provided.

---

## 15. Validation policy

Validation should occur at three levels:

### Level 1 — Syntax

- response is valid JSON
- response conforms to Pydantic model

### Level 2 — Controlled vocabulary

- all controlled values are present in the active rulebook
- no unapproved synonyms
- no empty required lists

### Level 3 — Cross-field business rules

Examples:

- `primary_trade` must appear in `likely_trades_required`
- `budget_band=low` plus multiple specialist bespoke trades should trigger a review warning
- structural claims are prohibited from image-only evidence
- `positive.why_it_works` and `negative.why_it_fails` cannot be near-duplicates

Warnings should not always fail the record; distinguish hard errors from review warnings.

---

## 16. Human review workflow

### Version 1 recommendation

Use CSV/XLSX export and import because Lloyd already works with the schema in a spreadsheet.

Export columns should include:

- thumbnail or local image path
- all model-drafted fields
- `review_status`
- `curator_notes`
- per-field correction columns where useful

### Review rules

- only Lloyd-approved records enter the gold dataset
- preserve model draft and human final values separately
- record every changed field
- capture rejection reason
- use a controlled review checklist

### Recommended checklist

- style family is justified
- mood labels are not redundant
- materials are visibly supported
- budget band is a reasoned estimate, not a claim of actual cost
- trades are plausible but explicitly preliminary
- positive analysis explains causality
- negative analysis is specific and useful
- no hidden-condition or structural claims

---

## 17. CLI requirements

Use Typer for a discoverable command-line interface.

Required commands:

```bash
design-data init-db
design-data ingest --input data/raw_images
design-data label --limit 20
design-data retry-failures --failure-type provider_transient
design-data export-review --output data/review/batch_001.xlsx
design-data import-review --input data/review/batch_001_reviewed.xlsx
design-data export-gold --format jsonl --output data/exports/gold.jsonl
design-data report
```

Every command should support `--help` and return a non-zero exit code on failure.

---

## 18. Configuration

### `.env`

```dotenv
GEMINI_API_KEY=
MODEL_PROVIDER=gemini
MODEL_NAME=<configured_supported_model>
APP_ENV=local
LOG_LEVEL=INFO
DATABASE_PATH=data/app.db
```

### `configs/app.local.yaml`

```yaml
inference:
  timeout_seconds: 90
  max_attempts: 3
  concurrency: 2
  temperature: 0.1

images:
  allowed_extensions: [".jpg", ".jpeg", ".png", ".webp"]
  max_file_mb: 20

review:
  curator_name: "Lloyd Lee"
```

Do not hard-code a model ID in application code. Model availability changes; keep it in configuration.

---

## 19. Logging and metrics

Use structured logs containing:

- run ID
- image ID
- request fingerprint
- pipeline stage
- latency
- attempt number
- result status
- error category

At the end of a batch, display:

- total images found
- new images ingested
- duplicates skipped
- successful drafts
- validation failures
- provider failures
- average latency
- estimated cost if provider usage is available

Never log image bytes, API keys, or complete personal data.

---

## 20. Testing strategy

### Unit tests

- rulebook loading and version validation
- request fingerprint stability
- hash-based deduplication
- Pydantic validation
- normalization
- business rules
- status transitions

### Contract tests

- provider response maps to the domain schema
- invalid structured output produces a controlled failure
- fake client returns deterministic fixtures

### Integration tests

- image folder → SQLite registration
- fake model → draft record
- export → curator edit → import → approved record
- rerun → idempotent skip

### Golden-set regression tests

Maintain 5–10 non-sensitive images with Lloyd-approved expected labels. Model outputs need not be identical, but important fields should remain within accepted values and evaluation thresholds.

### Evaluation metrics

Track:

- schema-valid response rate
- field-level agreement with Lloyd
- exact-match rate for controlled fields
- average number of human corrections per record
- approval rate
- time to review each image
- inter-rater agreement if a second curator is added

The primary quality metric should be **field-level agreement with Lloyd after review**, not generic model confidence.

---

## 21. Security, provenance, and rights

For each image store:

- original source category
- source URL where available
- date collected
- rights / permission status
- whether it may be used for internal analysis, model input, publication, or training

Do not treat public availability as permission for every use. Keep training eligibility separate from internal curation eligibility.

Recommended values:

```text
unknown
internal_reference_only
licensed_for_analysis
licensed_for_training
studio_owned
permission_granted
restricted
```

Do not export restricted source imagery into downstream training packages.

---

## 22. Local installation runbook

### 22.1 Prerequisites

- Python 3.11 or newer
- Git
- a Gemini API key if using Gemini
- source images stored locally

### 22.2 Create project

```bash
mkdir hybrid-design-dataset
cd hybrid-design-dataset
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 22.3 Install recommended packages

```bash
pip install \
  pydantic pydantic-settings typer rich \
  sqlalchemy alembic pyyaml jinja2 pillow \
  pandas openpyxl pyarrow tenacity python-dotenv \
  google-genai pytest pytest-cov
```

Pin exact versions in `pyproject.toml` after the initial spike and commit the lock file.

### 22.4 Configure environment

```bash
cp .env.example .env
```

Populate `GEMINI_API_KEY` and the configured model name.

### 22.5 Place images

```text
data/raw_images/
├── image_001.jpg
├── image_002.png
└── image_003.webp
```

Keep original filenames, but do not depend on filenames as identifiers.

### 22.6 Initialise database

```bash
design-data init-db
```

### 22.7 Ingest images

```bash
design-data ingest --input data/raw_images
```

Verify the report shows the expected number of unique images.

### 22.8 Dry-run with fake model

```bash
MODEL_PROVIDER=fake design-data label --limit 3
```

This validates the local workflow without API calls.

### 22.9 Run a small real batch

```bash
MODEL_PROVIDER=gemini design-data label --limit 5
```

Do not process all images until the first five have been reviewed.

### 22.10 Export review workbook

```bash
design-data export-review --output data/review/batch_001.xlsx
```

### 22.11 Lloyd reviews the batch

He should:

- correct labels
- add precise positive and negative notes
- mark each row `approved`, `reviewed`, or `rejected`
- provide rejection reasons

### 22.12 Import reviewed data

```bash
design-data import-review --input data/review/batch_001_reviewed.xlsx
```

The import command must validate every edited value against the same rulebook.

### 22.13 Export gold dataset

```bash
design-data export-gold \
  --format jsonl \
  --output data/exports/gold_dataset_v1.jsonl
```

Also export Parquet for analysis:

```bash
design-data export-gold \
  --format parquet \
  --output data/exports/gold_dataset_v1.parquet
```

### 22.14 Back up

```bash
cp data/app.db "data/app_backup_$(date +%Y%m%d_%H%M%S).db"
```

---

## 23. Troubleshooting

### Model returns invalid JSON

- preserve raw response
- classify as `validation_failed`
- retry once using a repair prompt only if the provider did not enforce structured output
- otherwise require manual review or update the response schema

### Model invents labels

- confirm the provider received the rulebook
- enforce enum values in response schema
- reject out-of-rulebook values in Python
- strengthen field descriptions with positive and negative examples

### Too many inconsistent positive/negative notes

- create 10–20 Lloyd-authored gold examples
- add them as few-shot examples selectively
- shorten field definitions
- split complex fields into simpler questions

### Review takes too long

- reduce schema for the first pass
- have the model produce only visually observable fields first
- move budget/trade judgments into a second review pass
- add an assisted local review UI later

### Duplicate records appear

- inspect content hashing and request fingerprint logic
- ensure the unique database constraint covers the request fingerprint

---

## 24. Acceptance criteria for version 1

The first iteration is complete when:

- 60 supplied images can be ingested without duplicate records
- at least 95% of supported images are processed without infrastructure failure
- every model response is validated or assigned a clear failure state
- Lloyd can review and import a batch without editing the database manually
- every approved record preserves both model draft and human final values
- rulebook and prompt versions are traceable
- the approved dataset exports successfully to JSONL and Parquet
- unit and integration tests pass locally
- no API secrets or restricted image data appear in logs or exports

Do not require high model accuracy as an acceptance criterion before obtaining the first real review measurements.

---

## 25. Recommended implementation sequence

### Phase 1 — Schema workshop

- engineering drafts Pydantic and YAML schemas
- Lloyd reviews vocabulary and definitions
- agree version 1 before model calls

### Phase 2 — Local data foundation

- repository structure
- SQLite migrations
- ingestion, hashing, provenance
- fake model client

### Phase 3 — Model-assisted labelling

- Gemini client
- structured output
- validation and failure handling
- five-image evaluation batch

### Phase 4 — Human review loop

- XLSX export/import
- audit trail
- correction analytics

### Phase 5 — Full first batch

- process 60 images in controlled batches
- refine rulebook from correction patterns
- export gold dataset v1

---

## 26. Final recommendation

Build a small, explicit, auditable Python data pipeline rather than an autonomous agent system.

The system should create the **technical schemas**, while you and Lloyd must provide and approve the **domain vocabulary, definitions, and examples**. The multimodal model should draft labels only. Lloyd's reviewed values should remain the authoritative source of truth.

This creates the correct foundation for later:

- embeddings and multimodal retrieval
- RAG-based concept generation
- preference learning
- positive/negative reranking
- fine-tuning preparation
- the wider Vision Engine

---

## 27. Primary implementation references

- Google Gemini structured output documentation: <https://ai.google.dev/gemini-api/docs/structured-output>
- Pydantic documentation: <https://docs.pydantic.dev/>
- Python `sqlite3` documentation: <https://docs.python.org/3/library/sqlite3.html>
- Typer documentation: <https://typer.tiangolo.com/>


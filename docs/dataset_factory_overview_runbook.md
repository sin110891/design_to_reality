# Overview runbook

Package root: `dataset_factory/` (run all Make/CLI commands from this directory, or from repo root via the forwarding `Makefile`).

## What / how / why / so what

| | |
|---|---|
| **What** | A local pipeline that turns curated interior images into architect-reviewed gold labels. |
| **How** | Images are hashed into SQLite → a multimodal model drafts structured labels against a controlled rulebook → Lloyd reviews in Excel → only approved rows export as gold data. |
| **Why** | Models invent vocabulary and drift; ground truth must come from human curation over a fixed ontology, not raw model output. |
| **So what** | You get a versioned, auditable dataset (draft + final + provenance) ready for later retrieval, ranking, or training — without treating unreviewed model JSON as truth. |

## Input / output

| | Path / artefact |
|---|---|
| **Input** | Images under `data/raw_images/…` (default: `contemporary_europe`) + `configs/rulebook.v1.yaml` |
| **Config** | `.env` (provider, model, API key) + `configs/app.local.yaml` |
| **Working store** | `data/app.db` |
| **Review** | `data/review/*.xlsx` |
| **Gold** | `data/exports/` (`jsonl` / `parquet` / `csv`) |

## How to run (Make)

Defaults are baked into the `Makefile`. Override any variable on the command line.

```bash
make install
make init-db
make ingest
make label
make export-review
# edit the workbook → save as batch_001_reviewed.xlsx (or override REVIEW_IN)
make import-review
make export-gold
make report
```

Shortcut dry-run through review export: `make pipeline`  
Force fake model (ignore Gemini in `.env`): `make label-fake`

### What each command does

| Command | What happens |
|---|---|
| `make install` | Creates `.venv` and installs the package + dev deps. |
| `make init-db` | Creates SQLite tables/indexes at `DATABASE_PATH` (default `data/app.db`). |
| `make ingest` | Scans `INPUT` images, computes SHA-256, skips duplicates, registers unique files + provenance into SQLite. |
| `make label` | For up to `LIMIT` images: builds rulebook prompt, calls provider from `.env` (or `MODEL_PROVIDER`), validates JSON against Pydantic + rulebook, stores draft curation records; skips unchanged fingerprints unless `FORCE=1`. |
| `make label-fake` | Same as `label`, but forces `MODEL_PROVIDER=fake` (no API calls). |
| `make export-review` | Writes draft rows to `REVIEW_OUT` spreadsheet for human edit (`review_status`, notes, field corrections). |
| `make import-review` | Backs up DB, reads `REVIEW_IN`, re-validates edited values against the rulebook, records field-level audit events, sets approved/reviewed/rejected. |
| `make export-gold` | Emits **approved** records only to `GOLD_OUT` in `GOLD_FORMAT` (draft + final preserved). |
| `make report` | Prints image counts and curation status totals. |
| `make retry-failures` | Re-labels images that failed with `FAILURE_TYPE` (default `provider_transient`). |
| `make demo` | Fake dry-run: `demo/stepthrough_pipeline.py` (ingest → label → export-review). |
| `make demo-gemini` | **Real Gemini** full loop: `demo/gemini_label_flow.py` (ingest → label → review sim → import → gold). Default `DEMO_LIMIT=3`. |
| `make test` | Runs the pytest suite. |
| `make pipeline` | Chains `init-db` → `ingest` → `label` → `export-review` → `report`. |

### Files each Make command calls

Almost all pipeline targets invoke `.venv/bin/design-data` → `src/design_dataset/cli.py`, which fans out into application modules:

| Make target | Entry / files called |
|---|---|
| `make install` / `make venv` | `python3.12`, `pip`, `pyproject.toml` |
| `make init-db` | `cli.py` → `infrastructure/sqlite_repository.py` |
| `make ingest` | `cli.py` → `application/ingest.py` (+ `infrastructure/hashing.py`, `filesystem.py`) |
| `make label` / `make label-fake` / `make retry-failures` | `cli.py` → `application/label.py` (+ `infrastructure/model_clients/*`, `domain/policies.py`, `prompts/label_image_v1.jinja2`) |
| `make export-review` / `make import-review` | `cli.py` → `application/review.py` (+ `infrastructure/exporters.py`) |
| `make export-gold` | `cli.py` → `application/export.py` (+ `infrastructure/exporters.py`) |
| `make report` | `cli.py` → `infrastructure/sqlite_repository.py` |
| `make demo` | `demo/stepthrough_pipeline.py` (fake client; same app modules) |
| `make demo-gemini` | `demo/gemini_label_flow.py` → ingest/label/review/export + `model_clients/gemini.py` |
| `make test` | `tests/` via pytest |
| `make pipeline` | Same files as the chained `design-data` targets above |

Shared config loaded by those paths: `.env`, `configs/app.local.yaml`, `configs/rulebook.v1.yaml`.

### Common overrides

```bash
make ingest INPUT=data/raw_images/other USAGE_RIGHTS=internal_reference_only
make label LIMIT=10 FORCE=1
make label MODEL_PROVIDER=gemini
make export-review REVIEW_OUT=data/review/batch_002.xlsx
make import-review REVIEW_IN=data/review/batch_002_reviewed.xlsx
make export-gold GOLD_FORMAT=parquet GOLD_OUT=data/exports/gold.parquet
make retry-failures FAILURE_TYPE=provider_transient LIMIT=5
make demo DEMO_LIMIT=2 DEMO_PERSIST=1
make demo-gemini DEMO_LIMIT=2
make demo-gemini DEMO_LIMIT=2 DEMO_PERSIST=1 FORCE=1
```

## Longer references

- Full engineering spec + §22 runbook: `docs/hybrid_rulebook_model_engineering_requirements.md`
- Debugger step-through: `demo/DEBUGGING.md`
- `make help` — lists targets and override examples

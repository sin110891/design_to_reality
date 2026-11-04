# Overview runbook

Package root: `vision_engine/` (run all Make/CLI commands from this directory).

Upstream dependency: `dataset_factory/` gold exports (architect-approved labels). Build those first if you need a fresh curated set — see `docs/dataset_factory_overview_runbook.md`.

## What / how / why / so what

| | |
|---|---|
| **What** | A local prototype that redesigns a room image using Lloyd's curated references, then captures architect approve/reject/rank feedback. |
| **How** | Approved gold JSONL is indexed → hybrid image/text/metadata retrieval → structured concept JSON → pluggable image edit (fake or Gemini) → Gradio / CLI review loop. |
| **Why** | Prove that architect-curated retrieval beats an ungrounded image-generation baseline on taste, relevance, and geometry preservation. |
| **So what** | You get reproducible concept variants plus a preference-learning feedback dataset — without claiming BoQ, compliance, or final specification. |

## Input / output

| | Path / artefact |
|---|---|
| **Input (curated)** | `dataset_factory` gold JSONL (default: `../dataset_factory/data/exports/gemini_demo_gold.jsonl`) + reference images |
| **Input (user)** | Room image + short brief (+ optional inspiration / budget / constraints) |
| **Config** | `.env` (provider, model, API key) + `configs/app.local.yaml` + `configs/rulebook.v1.yaml` |
| **Working store** | `data/database/vision_engine.db` |
| **Index** | `data/indexes/curated.npz` (+ sibling `.jsonl` metadata) |
| **Generated** | `data/generated/<project_id>/…` |
| **Feedback** | `data/exports/feedback.jsonl` (also csv / parquet) |

## How to run (Make)

Defaults are baked into the `Makefile`. Override any variable on the command line.

```bash
make install
make init-db
make build-index
make run-fake
make ui
# after Lloyd reviews in the UI (or via CLI):
make export-feedback
make report
```

Shortcut dry-run: `make pipeline` (init → index → fake run → report)  
Force fake providers: `make run-fake`

### What each command does

| Command | What happens |
|---|---|
| `make install` | Creates `.venv` and installs the package + dev deps. |
| `make init-db` | Creates SQLite tables at `DATABASE_PATH` (default `data/database/vision_engine.db`). |
| `make build-index` | Loads approved gold records via `--gold`, embeds images/text, writes NumPy index to `data/indexes/curated.npz`, upserts `dataset_records`. |
| `make run` / `make run-fake` | Creates a project from `ROOM` + `BRIEF`, retrieves references (unless baseline), generates concept JSON + 2–3 variants. |
| `make compare` | Runs curated and baseline modes for the same room (evaluation aid). |
| `make ui` | Launches Gradio on `HOST:PORT` (default `127.0.0.1:7860`). |
| `make export-feedback` | Writes review events to `OUTPUT` in `FORMAT` (jsonl / csv / parquet). |
| `make report` | Prints local persistence counts. |
| `make demo` | Offline step-through: index → fake pipeline → feedback export. |
| `make test` | Runs the pytest suite. |
| `make pipeline` | Chains `init-db` → `build-index` → `run-fake` → `report`. |

### Files each Make command calls

Almost all targets invoke `.venv/bin/vision-engine` → `src/vision_engine/cli.py`:

| Make target | Entry / files called |
|---|---|
| `make install` / `make venv` | `python3.12`, `pip`, `pyproject.toml` |
| `make init-db` | `cli.py` → `infrastructure/sqlite_repository.py` |
| `make build-index` | `cli.py` → `application/build_index.py` (+ `gold_adapter.py`, embedding clients, `vector_store.py`) |
| `make run` / `make run-fake` | `cli.py` → `application/run_pipeline.py` → create / retrieve / concept / variants |
| `make compare` | `cli.py` → `run_pipeline.run_baseline_vs_curated` |
| `make ui` | `cli.py` → `ui/gradio_app.py` |
| `make export-feedback` | `cli.py` → `application/export_feedback.py` |
| `make report` | `cli.py` → `sqlite_repository.counts` |
| `make demo` | `demo/stepthrough_pipeline.py` (fake providers) |
| `make test` | `tests/` via pytest |

Shared config loaded by those paths: `.env`, `configs/app.local.yaml`, `configs/rulebook.v1.yaml`, `configs/prompts.v1.yaml`.

### Common overrides

```bash
make build-index GOLD=../dataset_factory/data/exports/gold.jsonl IMAGES=../dataset_factory/data/raw_images/contemporary_europe
make run-fake ROOM=path/to/room.jpg BRIEF='calm oak living room' ROOM_TYPE=living_room
make run MODE=baseline ROOM=path/to/room.jpg BRIEF='generic refresh'
make compare ROOM=path/to/room.jpg
make export-feedback OUTPUT=data/exports/feedback.parquet FORMAT=parquet
make ui HOST=127.0.0.1 PORT=7861
```

### CLI equivalents

```bash
vision-engine build-index --gold ../dataset_factory/data/exports/gemini_demo_gold.jsonl \
  --images ../dataset_factory/data/raw_images/contemporary_europe \
  --output data/indexes/curated.npz

vision-engine run --room ../dataset_factory/data/raw_images/contemporary_europe/01.jpg \
  --brief "warm contemporary European, calmer lighting" --room-type living_room

vision-engine record-feedback --project-id proj_… --decision approved --variant-id var_… --rank 1 --taste 5 --geometry 4
vision-engine export-feedback --output data/exports/feedback.jsonl
vision-engine ui
```

## End-to-end flow

```text
dataset_factory gold (approved only)
        ↓
build-index (embeddings + NumPy store)
        ↓
room upload + brief
        ↓
hybrid retrieval (image + text + metadata + quality)
        ↓
structured DesignDirection JSON
        ↓
2–3 edited room variants (A closest / B conservative / C expressive)
        ↓
Lloyd review (scores, rank, failure tags)
        ↓
feedback export (preference-learning dataset)
```

## Modes

| Mode | Behaviour |
|---|---|
| **curated** | Retrieve Lloyd references → ground concept + image edit prompts |
| **baseline** | Skip retrieval; generic brief-only concept/edit (for A/B evaluation) |

## Providers

| `MODEL_PROVIDER` / `EMBEDDING_PROVIDER` | Behaviour |
|---|---|
| `fake` (default) | Deterministic concept JSON + placeholder image edits; no API key |
| `gemini` | Gemini for concept JSON + image edit; requires `GEMINI_API_KEY` |

## Longer references

- Engineering spec: `docs/erds/vision_engine_prototype_engineering_requirements.md`
- Dataset factory runbook: `docs/dataset_factory_overview_runbook.md`
- Dataset factory ERD: `docs/erds/hybrid_rulebook_model_engineering_requirements.md`
- `make help` — lists targets and override examples

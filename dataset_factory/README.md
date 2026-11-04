# Dataset Factory

Local-first Python pipeline that turns curated interior images into architect-reviewed gold labels.

The multimodal model drafts labels against a controlled rulebook. Human review creates ground truth.

This package lives at `dataset_factory/` inside the Design to Reality monorepo. Run all commands from this directory.

## Quick start

```bash
cd dataset_factory
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # if needed

make init-db
make ingest
make label LIMIT=5
make export-review
make report
```

For real Gemini calls, set `GEMINI_API_KEY`, `MODEL_PROVIDER=gemini` (or `google`), and `MODEL_NAME` in `.env`.

## Commands

Prefer Make (see `make help` and `docs/overview_runbook.md`):

| Command | Purpose |
|---|---|
| `make init-db` | Create SQLite schema |
| `make ingest` | Hash + register images |
| `make label` | Draft labels via model |
| `make export-review` | Spreadsheet for curator |
| `make import-review` | Import reviewed decisions |
| `make export-gold` | Export approved gold set |
| `make report` | Status summary |
| `make demo` | Fake end-to-end dry run |
| `make demo-gemini` | Real Gemini full loop |

## Debugging

See [`demo/DEBUGGING.md`](demo/DEBUGGING.md). Cursor launch configs are in the repo-root `.vscode/launch.json` and use `dataset_factory/` as cwd.

## Layout

```text
dataset_factory/
├── configs/                 # app + rulebook YAML + JSON schemas
├── data/raw_images/         # source imagery
├── src/design_dataset/      # application package
├── tests/
├── demo/
└── docs/overview_runbook.md
```

# Debugging & step-through guide

This folder contains scripts and VS Code / Cursor launch configs for stepping through the dataset pipeline.

## Prerequisites

```bash
cd /Users/sinandjevdet/design_to_reality/dataset_factory
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Confirm the debugger can import the package:

```bash
python -c "import design_dataset; print(design_dataset.__version__)"
```

## Option A — Cursor / VS Code debugger (`launch.json`)

1. Open the **repo root** (`design_to_reality/`) in Cursor — launch configs live in `.vscode/launch.json` and use `dataset_factory/` as cwd.
2. Open **Run and Debug** (`Cmd+Shift+D`).
3. Pick a configuration:
   - **Demo: Stepthrough pipeline** — fake-model dry run (`demo/stepthrough_pipeline.py`)
   - **Demo: Gemini full labelling flow** — real Gemini end-to-end (`demo/gemini_label_flow.py`)
   - **CLI: init-db**
   - **CLI: ingest contemporary_europe**
   - **CLI: label (fake, limit 3)**
   - **CLI: report**
   - **Pytest: current file**
   - **Pytest: all tests**
4. Set breakpoints by clicking the gutter next to a line (red dot).
5. Press **F5** to start, or **Run → Start Debugging**.

### Useful debug keys

| Key | Action |
|---|---|
| `F5` | Continue |
| `F10` | Step over |
| `F11` | Step into |
| `Shift+F11` | Step out |
| `Shift+F5` | Stop |

### Watch / inspect tips

- Add watches for `report`, `fingerprint`, `validation.errors`, `image.sha256`.
- In the Debug Console, evaluate expressions such as `validation.label.mood`.
- Keep `MODEL_PROVIDER=fake` while learning the control flow so no API calls are made.

## Option B — CLI under `debugpy` (terminal)

```bash
source .venv/bin/activate
python -m debugpy --listen 5678 --wait-for-client -m design_dataset.cli label --limit 1
```

Then use **Python: Attach** (port `5678`) if you add that config, or start from a launch config that already points at the CLI module.

## Option C — Fake scripted step-through

```bash
source .venv/bin/activate
python demo/stepthrough_pipeline.py
# or: make demo
```

Tiny path with **fake** model (no API cost):

1. init DB  
2. ingest  
3. label (fake)  
4. export review workbook  
5. print status  

## Option D — Real Gemini full labelling flow

Requires `GEMINI_API_KEY` and `MODEL_NAME` in `.env` (`MODEL_PROVIDER=gemini` or `google`).

```bash
source .venv/bin/activate
python demo/gemini_label_flow.py --limit 2
# or:
make demo-gemini DEMO_LIMIT=2
```

Full hybrid loop:

1. init DB  
2. ingest  
3. **label with Gemini** (rulebook prompt + structured JSON + validation)  
4. print one draft sample  
5. export review XLSX → `data/review/gemini_demo_batch.xlsx`  
6. simulate curator approval  
7. import review  
8. export gold → `data/exports/gemini_demo_gold.jsonl`  

Useful flags: `--persist` (use `data/app.db`), `--force` (relabel), `--skip-review-sim` (stop after export-review).

Breakpoints:

- `application/label.py` → `label_images`  
- `infrastructure/model_clients/gemini.py` → `label_image`  
- `domain/policies.py` → `validate_against_rulebook`  
- `application/review.py` → `import_reviewed`  

## Recommended first debugging session

1. Launch **Demo: Stepthrough pipeline** (fake) to learn control flow.  
2. Then **Demo: Gemini full labelling flow** with `--limit 1` or `2`.  
3. Break in `label_images` / `GeminiClient.label_image` and inspect the draft.  

## Common pitfalls

- Wrong Python interpreter: select `.venv/bin/python` in the Cursor status bar.
- Stale settings cache: restart the debug session after editing `.env`.
- Gemini path: set `GEMINI_API_KEY`, `MODEL_PROVIDER=gemini` (or `google`), and a valid `MODEL_NAME`.
- Keep `--limit` small — each image is a paid multimodal call.

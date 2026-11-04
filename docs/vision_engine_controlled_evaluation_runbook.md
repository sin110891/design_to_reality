# Controlled Evaluation Runbook

## What it is

This system compares two generation paths under the same input:

- **Curated**: uses retrieved reference images.
- **Baseline**: uses no retrieved references.

Each test case generates both paths, stores all outputs in the database, and
creates a blinded package for an evaluator.

## Why it is needed

Normal UI runs are separate projects. They are hard to compare fairly.

Controlled evaluation fixes this:

```text
Same room + same brief + same structured inputs
                    ↓
          curated and baseline runs
                    ↓
        six mixed, blinded candidate images
                    ↓
           evaluator selects a winner
                    ↓
      curated vs baseline win-rate report
```

## So what

You can measure whether retrieved curated references improve image preference.
The system keeps:

- input and output SHA-256 hashes;
- mode, model, prompt, and project provenance;
- private curated/baseline mapping;
- a portable full export; and
- a blind evaluator package with no arm labels.

---

## Before you start

Run commands from `vision_engine/`.

1. Install dependencies:

```bash
make install
```

2. Build and promote the curated retrieval index. Curated evaluation needs one:

```bash
make build-retrieval-index GOLD=../dataset_factory/data/exports/gold.jsonl
```

3. Confirm it is active:

```bash
.venv/bin/vision-engine active-index
```

---

## Evaluation YAML

Start with [`configs/evaluation.example.yaml`](../vision_engine/configs/evaluation.example.yaml).

```yaml
evaluation:
  name: dark-room-v1
  repetitions: 5
cases:
  - room_image_path: path/to/room.jpg
    brief: "Dark contemporary European room"
    room_type: living_room
    style_family: Contemporary Europe
    budget_band: high
    constraints:
      - do not move walls, doors, windows, radiators, or fireplace
exports:
  full_output_dir: data/evaluations
  blind_output_dir: ~/Downloads/vision-engine-blind-evaluations
```

| Field | Meaning |
|---|---|
| `repetitions` | Number of curated/baseline pairs per case |
| `cases` | Fixed structured inputs to compare |
| `constraints` | Rules both arms must receive |
| `full_output_dir` | Internal, auditable output |
| `blind_output_dir` | Evaluator-facing output |

Do not change a YAML file mid-evaluation. A canonical hash records its exact
contents.

---

## Stage 1 — create the evaluation package

### Command

```bash
make evaluation-package CONFIG=configs/evaluation.example.yaml N=5 WORKERS=4
```

### What it does

1. Validates and hashes the YAML inputs.
2. Creates `N` curated/baseline pairs.
3. Runs pair arms in bounded parallelism.
4. Saves projects, runs, variants, modes, and image hashes to SQLite.
5. Creates the internal full export.
6. Creates the blind evaluator package.

### Output

The command prints:

```text
eval_...        # evaluation run ID
eexp_...        # blind export ID
```

Internal output:

```text
data/evaluations/eval_.../
  manifest.json
  report.json
  report.csv
  cases/
```

Blind output:

```text
~/Downloads/vision-engine-blind-evaluations/blind_eexp_.../
  instructions.md
  response_template.csv
  cases/case_0001/
    room.png
    brief.txt
    candidates/
      candidate_0001_01.png
      ...
```

Candidate names are opaque. The blind folder does not reveal curated or
baseline origin.

### When to use it

Use it whenever you want a new fair comparison set.

### Example variations

One pair for a quick smoke test:

```bash
make evaluation-package CONFIG=configs/evaluation.example.yaml N=1 WORKERS=2
```

Repeatable blind order:

```bash
make evaluation-package CONFIG=configs/evaluation.example.yaml N=5 WORKERS=4 SEED=42
```

### So what

Give the blind folder to the evaluator. Keep the full internal folder private.

---

## Stage 2 — score evaluator choices

The evaluator fills in `response_template.csv`:

```csv
case_id,winner_candidate_id
case_0001,candidate_0001_04
case_0002,candidate_0002_01
```

### Command

```bash
make evaluation-score \
  EXPORT_ID=eexp_... \
  CSV=~/Downloads/vision-engine-blind-evaluations/blind_eexp_.../response_template.csv
```

### What it does

1. Reads the evaluator CSV.
2. Resolves each opaque candidate through the private DB mapping.
3. Saves evaluator choices.
4. Calculates curated and baseline win proportions.
5. Writes an internal score report.

Default score report:

```text
data/evaluations/eval_.../selection_reports/eexp_..._default.json
```

### When to use it

Use it after the evaluator returns the completed CSV.

### Example: named evaluator

```bash
make evaluation-score \
  EXPORT_ID=eexp_... \
  CSV=returned.csv \
  EVALUATOR=architect_01
```

### So what

The report answers:

```text
How often did curated win?
How often did baseline win?
How many cases were skipped?
```

---

## Optional lower-level commands

These are useful for inspection or recovery. Normal use needs only Stage 1 and
Stage 2.

| Command | What it does | When used |
|---|---|---|
| `make evaluate ...` | Runs pairs only | Debug generation before exports |
| `make evaluation-report EVAL_ID=eval_...` | Shows complete pairs only | Inspect an existing evaluation |
| `make evaluation-export EVAL_ID=eval_...` | Recreates full internal bundle | Recover or copy an export |
| `make blind-evaluation-export EVAL_ID=eval_...` | Recreates blind package | Send a new blind package |
| `make evaluation-import-selections EXPORT_ID=eexp_... CSV=returned.csv` | Imports choices only | Debug CSV import |

## Full flow

```text
Stage 1
  YAML → make evaluation-package
       → internal export + blind export
       → evaluator receives blind folder

Stage 2
  evaluator CSV → make evaluation-score
                → internal win-rate report
```

That is the complete controlled-evaluation workflow.

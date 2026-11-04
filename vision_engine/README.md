# Vision Engine Prototype

Local-first Gradio + Python prototype that retrieves Lloyd's curated references,
builds a structured design direction, edits the user's room image into 2–3
concept variants, and captures architect feedback.

This package **consumes** gold exports from `dataset_factory/` — it does not
replace the labelling / review factory.

## Quick start

```bash
cd vision_engine
make install
cp .env.example .env   # optional; fake provider works without a key
make build-index       # indexes dataset_factory gold JSONL by default
make run-fake
make ui
```

See `docs/vision_engine_overview_runbook.md` for the full operator runbook.

## Layout

```text
vision_engine/
├── src/vision_engine/
│   ├── application/     # create → retrieve → concept → variants → feedback
│   ├── domain/          # schemas, scoring, rulebook
│   ├── infrastructure/  # SQLite, NumPy index, providers, gold adapter
│   ├── prompts/         # versioned Jinja2 templates
│   ├── ui/gradio_app.py
│   └── cli.py
├── configs/
├── data/
├── tests/
└── demo/
```

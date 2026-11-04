PYTHON ?= python3.12
VENV ?= .venv
BIN := $(VENV)/bin

# Pipeline defaults (override on the command line, e.g. make label LIMIT=10)
INPUT ?= data/raw_images/contemporary_europe
LIMIT ?= 5
FORCE ?=
REVIEW_OUT ?= data/review/batch_001.xlsx
REVIEW_IN ?= data/review/batch_001_reviewed.xlsx
V3_IN ?= $(HOME)/Downloads/curated_design_dataset_schema_for_lloyd_v3.xlsx
GOLD_FORMAT ?= jsonl
GOLD_OUT ?= data/exports/gold.jsonl
FAILURE_TYPE ?= provider_transient
USAGE_RIGHTS ?= unknown
MODEL_PROVIDER ?=
DEMO_LIMIT ?= 3
DEMO_PERSIST ?=

LABEL_ARGS := --limit $(LIMIT)
ifneq ($(strip $(FORCE)),)
LABEL_ARGS += --force
endif

INGEST_ARGS := --input $(INPUT) --usage-rights $(USAGE_RIGHTS)

RETRY_ARGS := --failure-type $(FAILURE_TYPE) --limit $(LIMIT)

DEMO_ARGS := --limit $(DEMO_LIMIT)
ifneq ($(strip $(DEMO_PERSIST)),)
DEMO_ARGS += --persist
endif

.PHONY: help venv install init-db ingest label label-fake retry-failures \
	export-review import-review import-v3 export-gold report test demo demo-gemini pipeline

help:
	@echo "Design dataset pipeline"
	@echo ""
	@echo "Setup:     make install"
	@echo "Core flow: make init-db && make ingest && make label && make export-review"
	@echo "After edit: make import-review && make export-gold && make report"
	@echo ""
	@echo "Overrides (examples):"
	@echo "  make ingest INPUT=data/raw_images/other"
	@echo "  make label LIMIT=10 FORCE=1"
	@echo "  make label MODEL_PROVIDER=fake"
	@echo "  make import-review REVIEW_IN=data/review/batch_001_reviewed.xlsx"
	@echo "  make import-v3 V3_IN=/path/to/curated_design_dataset_schema_for_lloyd_v3.xlsx"
	@echo "  make export-gold GOLD_FORMAT=parquet GOLD_OUT=data/exports/gold.parquet"
	@echo "  make demo-gemini DEMO_LIMIT=2"
	@echo "  make demo-gemini DEMO_LIMIT=2 DEMO_PERSIST=1 FORCE=1"

venv:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip

install: venv
	$(BIN)/pip install -e ".[dev]"

init-db:
	$(BIN)/design-data init-db

ingest:
	$(BIN)/design-data ingest $(INGEST_ARGS)

# Uses .env for provider/model unless MODEL_PROVIDER is overridden here.
label:
ifdef MODEL_PROVIDER
	MODEL_PROVIDER=$(MODEL_PROVIDER) $(BIN)/design-data label $(LABEL_ARGS)
else
	$(BIN)/design-data label $(LABEL_ARGS)
endif

label-fake:
	MODEL_PROVIDER=fake $(BIN)/design-data label $(LABEL_ARGS)

retry-failures:
ifdef MODEL_PROVIDER
	MODEL_PROVIDER=$(MODEL_PROVIDER) $(BIN)/design-data retry-failures $(RETRY_ARGS)
else
	$(BIN)/design-data retry-failures $(RETRY_ARGS)
endif

export-review:
	$(BIN)/design-data export-review --output $(REVIEW_OUT)

import-review:
	$(BIN)/design-data import-review --input $(REVIEW_IN)

import-v3:
	$(BIN)/design-data import-v3 --input "$(V3_IN)"

export-gold:
	$(BIN)/design-data export-gold --format $(GOLD_FORMAT) --output $(GOLD_OUT)

report:
	$(BIN)/design-data report

test:
	$(BIN)/pytest -q

demo:
	$(BIN)/python demo/stepthrough_pipeline.py $(DEMO_ARGS)

# Real Gemini end-to-end: ingest → label → review sim → import → gold.
# Overrides: make demo-gemini DEMO_LIMIT=2 DEMO_PERSIST=1
demo-gemini:
	$(BIN)/python demo/gemini_label_flow.py --limit $(DEMO_LIMIT) \
		$(if $(DEMO_PERSIST),--persist,) \
		$(if $(FORCE),--force,)

# Convenience: local dry-run through review export (no human import/gold).
pipeline: init-db ingest label export-review report

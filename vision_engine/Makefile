PYTHON ?= python3.12
VENV ?= .venv
BIN := $(VENV)/bin

GOLD ?= ../dataset_factory/data/exports/gemini_demo_gold.jsonl
IMAGES ?= ../dataset_factory/data/raw_images/contemporary_europe
ROOM ?= ../dataset_factory/data/raw_images/contemporary_europe/01.jpg
BRIEF ?= warm contemporary European, calmer lighting, retain windows and fireplace
ROOM_TYPE ?= living_room
MODE ?= curated
LIMIT ?=
FORCE ?=
OUTPUT ?= data/exports/feedback.jsonl
FORMAT ?= jsonl
HOST ?= 127.0.0.1
PORT ?= 7860

CONFIG ?= configs/evaluation.example.yaml
N ?=
WORKERS ?= 4
EVAL_ID ?=
OUT_DIR ?=
BLIND_DIR ?=
CSV ?=
SEED ?=
EXPORT_ID ?=
EVALUATOR ?= default
PROJECT_ID ?=
VARIANT_ID ?=
REGION_ID ?=
CONCEPT_VERSION_ID ?=
CANDIDATE_ID ?=
SCHEDULE_ID ?=
SNAPSHOT_NAME ?= local-v1

REGION_TYPE ?= sofa
CHANNEL3 ?=

.PHONY: help venv install init-db build-index build-retrieval-index run run-fake compare ui export-feedback \
	report test demo pipeline evaluate evaluation-report evaluation-export blind-evaluation-export \
	evaluation-import-selections evaluation-package evaluation-score concept-board-import \
	concept-board-import-channel3 concept-board-ping-channel3 channel3-ping concept-board-bootstrap \
	concept-board-status concept-board-retrieve concept-board-preview concept-board-select \
	concept-board-procurement concept-board-export concept-board-workflow

help:
	@echo "Vision engine prototype"
	@echo ""
	@echo "Setup:     make install"
	@echo "Index:     make build-index"
	@echo "Run:       make run-fake"
	@echo "UI:        make ui"
	@echo "Board UI:  make ui  (Concept board tab)"
	@echo ""
	@echo "Overrides (examples):"
	@echo "  make build-index GOLD=../dataset_factory/data/exports/gold.jsonl"
	@echo "  make run-fake ROOM=path/to/room.jpg BRIEF='calm oak living room'"
	@echo "  make compare ROOM=path/to/room.jpg"
	@echo "  make export-feedback OUTPUT=data/exports/feedback.parquet FORMAT=parquet"
	@echo "  make evaluation-package CONFIG=configs/evaluation.example.yaml N=5 WORKERS=4"
	@echo "  make evaluation-score EXPORT_ID=eexp_... CSV=returned.csv"
	@echo "  make concept-board-workflow PROJECT_ID=proj_... VARIANT_ID=var_..."

venv:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install --upgrade pip

install: venv
	$(BIN)/pip install -e ".[dev]"

init-db:
	$(BIN)/vision-engine init-db

build-index:
	$(BIN)/vision-engine build-index --gold $(GOLD) --images $(IMAGES) \
		--output data/indexes/curated.npz

build-retrieval-index:
	$(BIN)/vision-engine build-retrieval-index --gold $(GOLD) --images $(IMAGES)

run:
	$(BIN)/vision-engine run --room $(ROOM) --brief "$(BRIEF)" \
		--room-type $(ROOM_TYPE) --mode $(MODE)

run-fake:
	MODEL_PROVIDER=fake EMBEDDING_PROVIDER=fake $(BIN)/vision-engine run \
		--room $(ROOM) --brief "$(BRIEF)" --room-type $(ROOM_TYPE) --mode $(MODE)

compare:
	MODEL_PROVIDER=fake EMBEDDING_PROVIDER=fake $(BIN)/vision-engine compare \
		--room $(ROOM) --brief "$(BRIEF)" --room-type $(ROOM_TYPE)

ui:
	$(BIN)/vision-engine ui --host $(HOST) --port $(PORT)

export-feedback:
	$(BIN)/vision-engine export-feedback --output $(OUTPUT) --format $(FORMAT)

evaluate:
	$(BIN)/vision-engine evaluate --config $(CONFIG) --workers $(WORKERS) \
		$(if $(N),--repetitions $(N),)

evaluation-package:
	$(BIN)/vision-engine evaluation-package --config $(CONFIG) --workers $(WORKERS) \
		$(if $(N),--repetitions $(N),) \
		$(if $(SEED),--seed $(SEED),)

evaluation-report:
	$(BIN)/vision-engine evaluation-report --eval-id $(EVAL_ID) \
		$(if $(OUT_DIR),--output $(OUT_DIR),)

evaluation-export:
	$(BIN)/vision-engine evaluation-export --eval-id $(EVAL_ID) \
		$(if $(OUT_DIR),--output-dir $(OUT_DIR),)

blind-evaluation-export:
	$(BIN)/vision-engine blind-evaluation-export --eval-id $(EVAL_ID) \
		$(if $(BLIND_DIR),--output-dir $(BLIND_DIR),) \
		$(if $(SEED),--seed $(SEED),)

evaluation-import-selections:
	$(BIN)/vision-engine evaluation-import-selections --export-id $(EXPORT_ID) --csv $(CSV) \
		$(if $(OUT_DIR),--output $(OUT_DIR),)

evaluation-score:
	$(BIN)/vision-engine evaluation-score --export-id $(EXPORT_ID) --csv $(CSV) \
		--evaluator-id $(EVALUATOR) $(if $(OUT_DIR),--output $(OUT_DIR),)

concept-board-import:
	$(BIN)/concept-board import-catalogue --snapshot-name $(SNAPSHOT_NAME)

concept-board-import-channel3:
	$(BIN)/concept-board import-channel3 --region-type $(REGION_TYPE) \
		--region-id $(or $(REGION_ID),cli-import) $(if $(MAX_BUDGET),--max-budget $(MAX_BUDGET),)

channel3-ping: concept-board-ping-channel3

concept-board-ping-channel3:
	$(BIN)/concept-board ping-channel3 $(if $(QUERY),--query "$(QUERY)",)

concept-board-bootstrap:
	$(BIN)/concept-board bootstrap --project-id $(PROJECT_ID) --variant-id $(VARIANT_ID)

concept-board-status:
	$(BIN)/concept-board status --project-id $(PROJECT_ID)

concept-board-retrieve:
	$(BIN)/concept-board retrieve --region-id $(REGION_ID) \
		--concept-version-id $(CONCEPT_VERSION_ID) $(if $(CHANNEL3),--channel3,)

concept-board-preview:
	$(BIN)/concept-board preview --candidate-id $(CANDIDATE_ID) \
		--concept-version-id $(CONCEPT_VERSION_ID)

concept-board-select:
	$(BIN)/concept-board select --candidate-id $(CANDIDATE_ID) \
		--concept-version-id $(CONCEPT_VERSION_ID)

concept-board-procurement:
	$(BIN)/concept-board procurement --project-id $(PROJECT_ID) \
		--concept-version-id $(CONCEPT_VERSION_ID)

concept-board-export:
	$(BIN)/concept-board export --schedule-id $(SCHEDULE_ID)

concept-board-workflow:
	$(BIN)/concept-board run-workflow --project-id $(PROJECT_ID) --variant-id $(VARIANT_ID)

report:
	$(BIN)/vision-engine report

test:
	$(BIN)/pytest -q

demo:
	$(BIN)/python demo/stepthrough_pipeline.py

# Convenience: init → index from dataset_factory gold → fake run
pipeline: init-db build-index run-fake report

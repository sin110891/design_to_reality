# Concept Board Visualisation Runbook

**Purpose:** Run and validate the visual concept-board workflow on top of a generated Vision Engine concept.

The visual workspace is **Tab 5** in the existing Gradio app. It is an internal MVP for architects/operators, not a client-facing web app.

---

## 1. What the visual flow does

```text
Generate or identify a Vision Engine variant
→ open (or bootstrap) a concept board from that variant
→ detect regions from the concept image (or add regions manually)
→ confirm editable regions
→ load a sealed product catalogue (local sample or live Channel3)
→ retrieve and compare product candidates
→ preview with 2D product staging, select, and architect-approve
→ create an immutable next concept version
→ generate an approved procurement schedule
→ download the CSV export
```

**Open concept board** is smart: if a board already exists for the project, it loads it; if not, it bootstraps from the variant ID you supply (first open only).

**Region discovery** infers editable regions (bed, wardrobe, lighting, etc.) from the concept image. Use **Detect regions from concept**, then **Confirm all proposed regions** before retrieval.

**2D product staging** composites the selected product into the region mask for a visual preview. The preview is evidence-grade staging, not a photoreal render guarantee.

**Cumulative preview stacking** (optional) shows already-approved selections plus the current candidate in one preview. Choose the approach in Tab 5 or via config:

| Mode | How it works | Trade-offs |
|------|----------------|------------|
| **Single region only** | Stages only the current candidate | Fast; ignores prior approvals |
| **Local multi-mask composite** | PIL composites each product into its region mask on the base concept image | Fast, deterministic, cheap; less photoreal than Gemini |
| **Chain Gemini edits** | Runs the existing Gemini image-edit path sequentially (output → next input) | More photoreal potential; slower, drift can compound |

---

## 2. Setup

From the repository root:

```bash
cd vision_engine
make install
make init-db
```

| Command | What it does |
|---------|---------------|
| `make install` | Creates the virtual environment and installs Vision Engine, tests, and the `concept-board` CLI. |
| `make init-db` | Creates/updates the SQLite schema, including concept-board and procurement tables. |

### Environment (optional)

Add to `vision_engine/.env`:

```bash
# Live catalogue (Tab 5 checkbox or CATALOGUE_PROVIDER=channel3)
CHANNEL3_API_KEY=...

# Region detection (default: fake — deterministic for dev/tests)
REGION_DETECTION_PROVIDER=fake   # or gemini
GEMINI_API_KEY=...               # required when REGION_DETECTION_PROVIDER=gemini
```

Test Channel3 connectivity:

```bash
make channel3-ping
make channel3-ping QUERY="pendant light"
```

---

## 3. App flow — which tabs to use

Start the UI:

```bash
cd vision_engine
make ui
```

Open `http://127.0.0.1:7860`.

The app has **five tabs**. Tab 5 does not generate room concepts — it consumes an existing **Project ID** (and **Variant ID** on first open).

| Tab | Required? | What you do |
|-----|-----------|-------------|
| **1 · Inputs** | **Yes** (new runs) | Upload room, enter brief, click **Generate concepts**. |
| **2 · Retrieved references** | No (view only) | See which references were used. |
| **3 · Generated concepts** | No (view only) | See the three variants. |
| **4 · Architect review** | Recommended | Review variants; optional but good practice before product work. |
| **5 · Concept board** | **Yes** (for this runbook) | Region discovery, product matching, 2D staging, procurement. |

**Minimum path (same session):** Tab 1 → Tab 5 → **Use current session IDs** → **Open concept board**.

**Historical path (previous run):** Tab 5 only — paste Project ID (+ Variant ID on first open) → **Open concept board**.

You do **not** need to re-generate in Tab 1 if you already have valid IDs from a prior run or the CLI.

---

## 4. Tab 5 · Concept board steps

### 4.1 Open the board

1. Enter **Vision Engine project ID** (`proj_...`).
2. On **first open** for that project, also enter **Variant ID** (`var_...`).
3. Click **Open concept board**.
   - **Existing board:** loads the latest concept version and regions/selections.
   - **First open:** copies the variant image into concept-board storage, creates `v1`, records upstream provenance.

**Shortcut (same session):** after Tab 1, use **Use current session IDs** to fill project + variant from pipeline state.

4. Optionally click **Load sample catalogue** to seal `local-v1` (required for local CSV retrieval; Channel3 can be used without this).

### 4.2 Define regions

**Recommended — automatic discovery:**

1. Click **Detect regions from concept**.
2. Review the overlay on the concept image and the regions table (status, confidence).
3. Click **Confirm all proposed regions** (or enable **Auto-confirm editable detected regions** before detect).

**Fallback — manual region:**

- code: `sofa_01`, type: `sofa`, display name: `Main sofa`, budget: `3000`
- **Add and confirm region**

### 4.3 Retrieve and select products

1. Choose a **Confirmed editable region** from the dropdown.
2. Optionally tick **Search live Channel3 catalogue** (requires `CHANNEL3_API_KEY`).
3. Click **Retrieve products** — browse the candidate gallery, pick a product image angle if needed.
4. Optional cumulative controls (before **Preview in room**):
   - **Stack approved selections in preview** — include prior approved regions in the same preview.
   - **Cumulative preview mode** — `Use config default`, `Single region only`, `Local multi-mask composite`, or `Chain Gemini edits`.
5. **Preview in room** — visual check only; does not record procurement.
6. **Approve selection** — records one procurement row for that region (repeat for more regions on the same `v1`).
7. **Preview, select, and approve** — combines preview + approve in one click.

Default stacking behaviour is controlled in `vision_engine/configs/app.local.yaml`:

```yaml
virtual_staging:
  cumulative_preview_enabled_default: false
  cumulative_preview_mode: local_composite   # or gemini_chain
```

The UI checkbox and mode dropdown override these defaults per preview without restarting the app.

### 4.4 Version and procurement

1. **Create next concept version** — immutable `v2` with copied approved selections.
2. **Approve schedule and export CSV** — procurement schedule + downloadable CSV + JSON manifest under `vision_engine/data/exports/procurement/`.

---

## 5. Example IDs (verified project)

Use these to test Tab 5 without re-running Tab 1:

| Entity | ID |
|--------|-----|
| **Project** | `proj_1d61c27be1224e229f34edd2ca27e7bf` |
| **Variant A** (closest_to_references) | `var_f52987dc5fa441b1bb75b7b0454cfb26` |
| **Variant B** (conservative) | `var_f07aa91a2c5e4fbf9a4141c816f6aea0` |
| **Variant C** (expressive) | `var_fc9e6fd5d54d474b9f8c9c29647019f0` |

After bootstrap (variant B example):

| Entity | ID |
|--------|-----|
| **Concept board** | `cb_ae8c47dfabe044b689bf36678762fd26` |
| **Concept direction** | `cd_2b370e5da8c348558734f5705a3345ce` |
| **Concept version v1** | `cv_63c4fb5d77d346f4b9d544c401e61eb6` |

Generated images:

```text
vision_engine/data/generated/proj_1d61c27be1224e229f34edd2ca27e7bf/
  variant_a_attempt1.png
  variant_b_attempt2.png
  variant_c_attempt3.png
```

**Quick Tab 5 test:**

- First visit: Project + Variant B → **Open concept board**
- Return visit: Project only → **Open concept board**

---

## 6. CLI / Make workflow

The same workflow is available for deterministic testing and automation.

### Variables

```bash
PROJECT_ID=proj_1d61c27be1224e229f34edd2ca27e7bf
VARIANT_ID=var_f07aa91a2c5e4fbf9a4141c816f6aea0
CONCEPT_VERSION_ID=cv_63c4fb5d77d346f4b9d544c401e61eb6
CONCEPT_DIRECTION_ID=cd_2b370e5da8c348558734f5705a3345ce
REGION_ID=dr_...
CANDIDATE_ID=rc_...
SCHEDULE_ID=ps_...
```

### Commands

| Command | What it does |
|---------|---------------|
| `make channel3-ping` | Test Channel3 API key and connectivity. |
| `make channel3-ping QUERY="pendant light"` | Ping with a specific search query. |
| `make concept-board-import` | Imports `data/catalogue/sample_products.csv` and seals `local-v1`. |
| `make concept-board-import-channel3 REGION_TYPE=sofa` | Seals a Channel3 snapshot for a region type. |
| `make concept-board-bootstrap PROJECT_ID=... VARIANT_ID=...` | Creates a board and `v1` from an existing generated variant. |
| `make concept-board-status PROJECT_ID=...` | Shows board/version/region/selection summary. |
| `concept-board detect-regions --project-id ... --concept-version-id ...` | Detect regions from concept image. |
| `concept-board confirm-regions --direction-id ... --concept-version-id ...` | Confirm all proposed regions. |
| `make concept-board-retrieve REGION_ID=... CONCEPT_VERSION_ID=...` | Retrieves candidates (add `CHANNEL3=1` for live catalogue). |
| `make concept-board-select CANDIDATE_ID=... CONCEPT_VERSION_ID=...` | 2D preview, select, and approve. |
| `make concept-board-procurement PROJECT_ID=... CONCEPT_VERSION_ID=...` | Creates and approves procurement schedule. |
| `make concept-board-export SCHEDULE_ID=...` | Writes procurement CSV and JSON manifest. |
| `make concept-board-workflow PROJECT_ID=... VARIANT_ID=...` | End-to-end MVP using manual sofa region + sample catalogue. |

### Example: bootstrap + detect regions (CLI)

```bash
cd vision_engine
make concept-board-bootstrap \
  PROJECT_ID=proj_1d61c27be1224e229f34edd2ca27e7bf \
  VARIANT_ID=var_f07aa91a2c5e4fbf9a4141c816f6aea0

./.venv/bin/concept-board detect-regions \
  --project-id proj_1d61c27be1224e229f34edd2ca27e7bf \
  --concept-version-id cv_63c4fb5d77d346f4b9d544c401e61eb6

./.venv/bin/concept-board confirm-regions \
  --direction-id cd_2b370e5da8c348558734f5705a3345ce \
  --concept-version-id cv_63c4fb5d77d346f4b9d544c401e61eb6
```

---

## 7. Inputs and outputs

| Stage | Key input | Persistent output |
|-------|-----------|-------------------|
| Bootstrap / open | Project + variant (first time) | `concept_boards`, `concept_versions`, provenance |
| Region detection | Concept image + provider | proposed regions, masks, overlay |
| Region confirm | Proposed regions | confirmed editable regions |
| Retrieval | Region + sealed catalogue | retrieval run, candidates, score rows |
| Selection | Candidate + approver | 2D staging preview, selection, approval event |
| Version commit | Approved selections | child concept version + copied selection rows |
| Procurement | Approved current-version selections | schedule, items, scope items |
| Export | Procurement schedule | CSV + content-hashed JSON manifest |

---

## 8. Storage locations

```text
vision_engine/data/concept_boards/
  {project_id}/{board_id}/versions/{concept_version_id}/primary.png

vision_engine/data/concept_boards/
  {project_id}/{board_id}/regions/   # detection overlays and masks

vision_engine/data/exports/procurement/
  {procurement_schedule_id}.csv
  {procurement_schedule_id}.json

vision_engine/data/database/vision_engine.db
  concept-board, catalogue, selection, procurement, and export records
```

---

## 9. Current MVP limits

- **Fake region detection** (`REGION_DETECTION_PROVIDER=fake`) uses deterministic templates; **gemini** uses the concept image but still depends on model quality.
- Local retrieval is rule-based against the sample CSV; Channel3 is live search, not a visual embedding index.
- 2D staging composites product cutouts into region masks — useful for decision-making, not final photoreal rendering.
- No authentication, collaboration, supplier PO workflow, or client web app yet.

These limitations are intentional: the UI validates the decision workflow before a dedicated multi-user web product is introduced.

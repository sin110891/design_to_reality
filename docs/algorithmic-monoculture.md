# Algorithmic Monoculture and Firm-Scoped Design Memory

## The phenomenon

When many firms use the same foundation model, training priors, and common prompts, outputs converge toward similar “average-good” interiors. This is **aesthetic convergence** or **algorithmic monoculture** — not literal model collapse, but a shared visual mean.

## Counter-strategies

| Strategy | Purpose |
|----------|---------|
| Persistent style profile per firm | Encode each practice’s visual language |
| Firm-owned licensed reference library and completed projects | Retrieve from proprietary taste, not generic internet priors |
| Explicit materials, eras, suppliers, budgets, “never use” constraints | Hard and soft boundaries on generation |
| Diversity controls that penalise similarity to previous outputs | Avoid repeating the same concept within a project or across recent jobs |
| Retrieval from firm-specific references before generation | Firm memory drives direction, not default model taste |
| Human corrections remembered as preferences | Learn from approvals, rejections, and edits with evidence |

---

## Current schema coverage (`dataset_factory`)

**What exists today**

- Per-image style, mood, material labels
- Coarse budget bands
- Image provenance, hashes, basic rights status
- Draft vs curator-corrected labels
- Field-level review events
- Versioned rulebooks and gold exports

**What is missing**

- Organisations / tenant isolation
- Persistent firm style profiles
- Firm-owned reference libraries or completed projects
- Eras, preferred suppliers, explicit “never use” rules
- Firm-scoped indexes and retrieval
- Similarity against previous firm outputs
- Persistent design preference learning

`vision_engine` has runtime diversity logic and richer evaluation/feedback, but it is still **global**, not firm-scoped.

### Core `dataset_factory` files

| Layer | Path |
|-------|------|
| Domain models | `dataset_factory/src/design_dataset/domain/models.py` |
| Enums | `dataset_factory/src/design_dataset/domain/enums.py` |
| Rulebook schema | `dataset_factory/src/design_dataset/domain/rulebook.py` |
| SQLite ORM | `dataset_factory/src/design_dataset/infrastructure/sqlite_repository.py` |
| JSON schemas | `dataset_factory/configs/schemas/design_label_draft.schema.json`, `curation_record.schema.json` |
| Controlled vocabulary | `dataset_factory/configs/rulebook.v1.yaml` |
| Gold output | `dataset_factory/data/exports/gold.jsonl` |

**SQLite tables (4):** `images`, `label_runs`, `curation_records`, `review_events`

### Coverage matrix

| Capability | Status | What exists | Gaps |
|------------|--------|-------------|------|
| Persistent per-firm style profiles | ❌ Missing | Per-image `style_family`, `mood`, `material_palette`; global rulebook | No `firm_id`, no aggregated `StyleProfile`, no profile versioning |
| Firm-owned licensed reference libraries | ⚠️ Partial | `source_type`, `source_url`, `usage_rights_status`, `sha256` | No library entity, firm ownership, license document/expiry |
| Completed projects as references | ❌ Missing | — | No project entity, no link reference → delivered job |
| Explicit materials | ✅ Per-record | `material_palette[]`, positive material fields | Not a canonical catalog; no SKU/spec linkage |
| Eras / period | ❌ Missing | Style via `style_family` only | No `era` or period enum |
| Suppliers (commercial) | ❌ Missing | Trade roles only | No supplier entity or preferred vendors |
| Budgets | ⚠️ Partial | `budget_band` (low–high) | No currency amounts or firm rate tiers |
| Never-use constraints | ❌ Missing | Negative labels describe image failures | No firm-level blocklist |
| Diversity / history similarity | ❌ factory / ✅ consumer | None in factory | `vision_engine` diversity at runtime only |
| Firm-scoped retrieval | ❌ Missing | Global gold index | No tenant filter on index or queries |
| Human corrections / preferences | ⚠️ Partial | `ReviewEvent`, draft vs final label | No firm-level learned defaults |
| Tenant / licensing / consent | ⚠️ Partial | `usage_rights_status`, provenance chain | No consent records or `org_id` |

---

## Platform vs consultancy

This can be a **repeatable platform**, not a consultancy — but only if every firm follows the same workflow:

```text
import → annotate → compare → approve profile → generate → correct → learn
```

It becomes consultancy if every firm needs custom taxonomy, hand-written prompts, bespoke code, and undocumented curation.

**Concierge onboarding is fine for pilot #1** — it teaches what to productise. Repeated steps become importers, controlled vocabularies, approval screens, and profile versioning.

**Principle:** the agent proposes; the professional approves; the platform remembers the evidence.

---

## Recommended platform data model

Extend `dataset_factory` patterns (hashing, rulebook versioning, review events, sealed snapshots) with firm scope:

```text
organizations (firm_id, name, default_currency, country)
  └── org_members (user_id, role)

firm_style_profiles (profile_id, org_id, version, status)
  ├── preferred_mood[], preferred_materials[], budget_default
  ├── style_families[], era_tags[]
  ├── never_use_materials[], never_use_motifs[]
  ├── preferred_suppliers[] → suppliers
  └── rulebook_version_id → rulebooks (versioned vocab)

reference_libraries (library_id, org_id, name, rights_policy)
  └── library_assets (asset_id, image_sha256, source_type, license_ref_id)
        └── license_records (license_id, grantee_org, scope, expiry, consent_status)

completed_projects (project_id, org_id, name, delivered_at)
  └── project_reference_links (project_id, reference_asset_id, room_type)

curation_records (+ org_id, library_id?, project_id?)
label_runs, review_events (+ org_id)

reference_annotations (+ annotation_revision_id)
curated_dataset_snapshots (+ org_id)

retrieval_indexes (+ org_id, snapshot_id)

preference_events
  ├── scope: curation | generation | pricing
  ├── field_path, old/new, actor, project_id?
  └── aggregates → firm_style_profiles (learned defaults)

similarity_policy (org_id, max_history_overlap, diversity_roles[])
```

### Firm profile structure

Each profile should separate:

- **Hard rules:** never use high-gloss finishes; banned supplier; max budget
- **Soft preferences:** prefers oak, muted palettes, restrained detailing
- **Evidence:** which projects/references/corrections support each preference
- **Confidence:** how often and how recently observed
- **Project override:** this client can differ from firm default

### Design principles

1. Keep `DesignLabelDraft` as the annotation contract — extend via optional metadata, not breaking changes.
2. Scope everything with `org_id` — libraries, snapshots, indexes, profiles, preferences.
3. Separate reference catalogue from product catalogue.
4. Unify rights enums across factory, vision_engine, and platform.
5. Persist diversity/similarity **policy per org**; store retrieval outcomes in vision_engine retrieval tables.
6. Learn firm preferences from events into `firm_style_profiles`, not ad hoc config.

---

## Agent-led onboarding (repeatable)

An agent-led UI can capture firm memory without bespoke consulting:

1. Create firm workspace.
2. Import completed-project images and reference folders.
3. Record ownership, permitted use, and training consent per collection.
4. Run `dataset_factory`-style annotation: room, materials, era, design character.
5. Ask contrastive questions: “Which of these two is more like your practice, and why?”
6. Propose a style profile for human approval.
7. Build a private retrieval index for that firm.
8. Apply profile automatically on new projects.
9. Log every accept/reject/edit as a `preference_event`.
10. Periodically suggest profile updates — never silently rewrite firm taste.

**Example prompt to firm:**

> “Across 18 approved projects you frequently selected natural oak and limewash, and rejected high-gloss marble 4 times. Add high-gloss marble to ‘avoid by default’?”

Architect approves or rejects.

---

## Preventing convergence at generation time

Retrieval order:

1. Firm’s completed projects
2. Firm’s approved reference library
3. Licensed shared library (if permitted)

Then penalise concepts too similar to:

- concepts already shown in this project
- firm’s recent outputs
- generic high-frequency patterns across the platform

Goal: **diversity inside the firm’s recognisable design language**, not random difference.

---

## Related: evaluation data and client journey

### Blinded winner CSV + reasons

Each row gives:

- **Winner:** unbiased comparative preference (curated vs baseline)
- **Reason:** what quality drove the choice (geometry, composition, originality, etc.)

Uses: benchmark changes, failure taxonomy, prompt/retrieval tuning, quality gates, future reranker training, firm taste profiles.

**Note:** current CSV importer reads `case_id` and `winner_candidate_id` only; a `reasons` column should be stored explicitly when added.

With ~20 cases and one architect, this is an **evaluation/hypothesis dataset**, not proof of market taste or enough for foundation training.

### Provisional client journey (to validate in pilots)

1. Professional receives brief + room photos
2. Uploads photos, inspiration, constraints
3. Gets three genuinely distinct concepts (firm-scoped retrieval)
4. Professional corrects/refines
5. Shares controlled comparison with client
6. Client approves direction
7. Professional sources real products + export schedule
8. Indicative budget later; construction pricing separate initially

**Pilot promise:**

> “Move from room brief to client-approved, purchasable concept faster.”

Observe on 2 real projects: who operates the tool, where edits happen, who approves, what deliverable is sent, what still happens outside the product, what makes them pay again.

---

## Bottom line

`dataset_factory` is strong for **global reference curation** but not yet a **multi-firm platform**. Firm memory, licensed libraries, completed projects, never-use rules, diversity against history, and firm-scoped retrieval require new org-scoped entities above the current four-table schema. Build the platform layer once; use concierge pilots to learn which onboarding steps to automate first.

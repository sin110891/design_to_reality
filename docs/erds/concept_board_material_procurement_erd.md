# Concept Board and Material Procurement — ERD

**Status:** Engineering design  
**Scope:** Editable concept-board workflow for generated room designs, real-product/material substitution, approval, procurement, and downstream scope generation  
**Primary goal:** Allow users and professionals to select parts of a generated design, compare real supplier alternatives, swap approved products/materials into concept versions, preserve decision history, and convert final selections into procurement-ready project data.

**Related designs:**

- [Vision Engine prototype ERD](vision_engine_prototype_engineering_requirements.md) — generation pipeline upstream of the concept board
- [Vision Engine review feedback loop ERD](vision_engine_review_feedback_loop_erd.md) — variant review and approved-concept manifests
- [Vision Engine multimodal retrieval ERD](vision_engine_multimodal_retrieval_index_erd.md) — reference retrieval patterns reused for product matching
- [Hybrid rulebook ERD](hybrid_rulebook_model_engineering_requirements.md) — shared design vocabulary and validation rules

---

## 1. Product Intent

The system should support this workflow:

```text
Generated room concept
→ identify editable design regions
→ attach design intent and constraints
→ retrieve real product/material alternatives
→ compare price, dimensions, availability and lead time
→ preview substitutions
→ approve selected items
→ create a new immutable concept version
→ add approved selections to procurement schedule
→ feed approved selections into scope and quotation
```

The concept board is not only an image gallery. It is the decision workspace linking:

```text
visual intent
→ real products
→ user and architect decisions
→ procurement
→ scope
→ quote
```

---

## 1.1 Decision summary

The Vision Engine prototype already generates and reviews room concepts. This design adds the **commercial specification layer**: decompose approved concepts into editable regions, match real products/materials, preview substitutions, approve selections, and export procurement-ready data.

Key decisions:

1. **Extend, don't fork** — reuse `project_id`, asset hashing, run provenance, and `DesignDirection` from Vision Engine.
2. **Separate catalogues** — curated reference images (`dataset_factory`) and commercial product SKUs use different snapshots and retrieval indexes.
3. **Immutable decisions** — concept versions, catalogue snapshots, procurement price snapshots, and integration exports are append-only.
4. **Bounded contexts** — concept workspace, product catalogue, procurement, and integration can start in one SQLite DB and split into services for the web app.
5. **Model outputs are proposals** — region detection, product matching, and substitution previews require human approval before procurement impact.

---

## 2. Core Design Principles

### 2.1 Immutable concept versions

A concept image must never be overwritten. Every accepted edit creates a new `concept_version`.

This preserves:
- design history
- auditability
- before/after comparison
- rollback
- reviewer provenance
- downstream scope consistency

### 2.2 Regions are stable logical design elements

Editable areas should be represented as logical design regions such as:

```text
sofa
coffee_table
floor_finish
wall_finish
pendant_light
curtains
joinery
rug
```

A region may have one or more masks or polygons across different concept versions. The identity of the logical region should remain stable even when the pixels change.

### 2.3 Product identity is separate from supplier offers

A product is the canonical item. A supplier offer represents:
- who sells it
- current price
- stock
- lead time
- delivery coverage
- commercial terms

This prevents duplicate products when multiple suppliers sell the same item.

### 2.4 Approved selections drive downstream systems

Only approved selections should enter:
- procurement schedules
- scope items
- quotes
- purchase orders

Draft or rejected alternatives must remain available for audit but must not affect commercial documents.

### 2.5 Model outputs are proposals, not truth

AI may propose:
- region boundaries
- product matches
- substitution suitability
- quantity assumptions
- design rationale

Professional or user approval determines what becomes authoritative.

### 2.6 Content-addressed assets, not paths

Every concept image, region mask, product image, and substitution preview must be identified by SHA-256 content hash. Storage URIs may change; hashes identify the bytes used in decisions, exports, and downstream scope.

This mirrors `generated_image_assets.image_sha256` and `uploads.sha256` in the Vision Engine prototype.

### 2.7 Catalogue snapshots before matching

Product and material catalogues are mutable operationally but must be pinned for retrieval and procurement decisions through immutable catalogue snapshots — the same pattern as `curated_dataset_snapshots` in the retrieval ERD.

A `region_candidate` or `procurement_item` must always reference the catalogue snapshot that was active when the decision was made.

### 2.8 Bounded contexts with explicit integration

The system is split into cooperating contexts rather than one monolithic schema:

```text
Concept Workspace     — boards, versions, regions, selections, reviews
Product Catalogue     — products, materials, suppliers, offers, assets
Procurement           — schedules, items, purchase orders
Integration           — scope, quote, external ERP/PM exports
Platform              — orgs, users, permissions, comments, events
```

Each context owns its write model. Cross-context effects use explicit foreign keys plus domain events — not silent cross-table updates.

### 2.9 Reuse retrieval patterns, not tables

Product matching should reuse the **retrieval architecture** from Vision Engine (candidate recall → hard filters → rerank → provenance) but must **not** mix reference-image vectors with product-image vectors in the same index.

Reference retrieval answers: “Which curated design should guide generation?”  
Product retrieval answers: “Which real SKU fits this region and constraints?”

### 2.10 Separate curated references from commercial catalogue

`dataset_factory` gold records are architect-curated **design references**. The product catalogue is a **commercial dataset**. A product must never silently enter the reference gold dataset, and a reference image must never be treated as a purchasable SKU without explicit catalogue ingestion.

---

## 3. High-Level Architecture

```text
Vision Engine
→ concept project
→ concept board
→ concept versions
→ editable design regions
→ product/material matching
→ supplier offers
→ substitution preview
→ review and approval
→ procurement schedule
→ purchase order
→ scope and quote integrations
```

---

## 4. Bounded contexts and deployment surfaces

The same logical model must serve three deployment surfaces without schema forks:

| Surface | Primary consumers | Write scope | Read scope |
|---------|-------------------|-------------|------------|
| Vision Engine CLI / Gradio | Internal operators, architects | Concept workspace + review | Full provenance |
| Future web app | Clients, architects, procurement staff | All contexts per role | Projections + real-time comments |
| Export / integration jobs | Scope, quote, ERP, BI | Integration outbox only | Immutable snapshots |

```text
                    ┌─────────────────────────────────────┐
                    │           Platform Context           │
                    │  orgs · users · roles · comments     │
                    └─────────────────┬───────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌─────────────────┐           ┌─────────────────┐
│ Concept       │           │ Product         │           │ Procurement     │
│ Workspace     │◄─────────►│ Catalogue       │──────────►│                 │
│               │  match    │                 │  schedule │                 │
│ boards        │           │ products        │           │ items           │
│ versions      │           │ offers          │           │ POs             │
│ regions       │           │ snapshots       │           │                 │
│ selections    │           │ retrieval index │           │                 │
└───────┬───────┘           └────────┬────────┘           └────────┬────────┘
        │                            │                             │
        └────────────────────────────┼─────────────────────────────┘
                                     ▼
                          ┌─────────────────────┐
                          │ Integration Context │
                          │ scope · quote · ERP │
                          │ domain events       │
                          └─────────────────────┘
```

### 4.1 Service ownership (future web app)

Recommended service boundaries for scale. Each service owns its tables; cross-service calls use IDs and events only.

| Service | Owns | Exposes |
|---------|------|---------|
| `concept-board-api` | boards, directions, versions, regions, geometries, selections, previews, approvals | REST/GraphQL for workspace UI |
| `catalog-api` | products, variants, materials, suppliers, offers, catalogue snapshots, product assets | Search and offer lookup |
| `product-retrieval-api` | product index versions, retrieval runs, candidates, scores | Region-scoped candidate retrieval |
| `procurement-api` | schedules, items, purchase orders | Schedule export and PO workflow |
| `platform-api` | orgs, users, project membership, comments, notifications | AuthZ and collaboration |
| `integration-worker` | outbox, external refs, export manifests | Async scope/quote/ERP push |

The Vision Engine prototype may initially implement all contexts in one SQLite database with schema prefixes or table namespaces. The ERD is designed so tables can be split by service without renaming entities.

---

## 5. Integration with existing systems

### 5.1 Upstream: Vision Engine generation pipeline

The concept board is the **downstream workspace** for an approved generated concept. It does not replace generation; it extends it.

```text
Vision Engine (existing)                    Concept Board (this ERD)
─────────────────────────                   ──────────────────────────
projects                           ───────► projects (extended)
uploads                            ───────► source room assets (reference)
retrieval_runs                     ───────► concept_version_provenance
concept_runs + DesignDirection     ───────► concept_directions.design_intent_json
generation_runs                    ───────► concept_version_provenance
generated_variants                 ───────► concept_versions (seed v1)
generated_image_assets             ───────► concept_assets
generation_review_sets             ───────► approval_events (design gate)
variant_reviews                    ───────► review_decisions (concept-level)
approved_concept_manifests         ───────► concept_board bootstrap trigger
```

#### Bootstrap rule

A `concept_board` is created when **either**:

1. an operator explicitly promotes a `generated_variant` into a board; or  
2. an `approved_concept_manifest` passes validation and the project enters the substitution workflow.

The first `concept_version` for a direction must copy:

- `generated_image_assets.image_sha256` → `concept_assets.asset_sha256`
- `DesignDirection` JSON → `concept_directions.design_intent_json`
- generation provenance → `concept_version_provenance`

#### Provenance bridge table

`concept_version_provenance` links each concept version back to Vision Engine runs without merging schemas:

| Field | Maps from |
|-------|-----------|
| `project_id` | `projects.project_id` |
| `concept_version_id` | new |
| `generation_run_id` | `generation_runs.run_id` |
| `concept_run_id` | `concept_runs.run_id` |
| `retrieval_run_id` | `retrieval_runs.run_id` |
| `source_variant_id` | `generated_variants.variant_id` |
| `approved_manifest_id` | `approved_concept_manifests.manifest_id` (nullable) |
| `design_direction_json` | snapshot at version creation |
| `reference_ids_json` | retrieved reference IDs used |

This preserves full traceability from procurement back to retrieval and generation configuration.

### 5.2 Parallel: dataset_factory (reference catalogue only)

`dataset_factory` produces architect-curated **reference** records. It does **not** own product SKUs. Reuse its **patterns**, not its tables:

| dataset_factory pattern | Product catalogue equivalent |
|-------------------------|------------------------------|
| `curation_records` + review workflow | `catalogue_ingestion_records` |
| content hash on images | `product_assets.asset_sha256` |
| gold JSONL export | `catalogue_snapshot` manifest |
| rulebook + prompt versioning | `catalogue_ingestion_config_version` |
| append-only review events | `offer_price_history`, `catalogue_change_events` |

Reference images from gold exports continue to feed Vision Engine retrieval. Product images feed a **separate** product retrieval index.

### 5.3 Downstream: scope and quotation systems

`scope_items` and procurement exports are the integration boundary. External systems receive immutable manifests, not live joins:

```text
approved region_selections
+ procurement_items (price snapshots)
+ concept_version lineage
→ scope_export_manifest (JSON/CSV)
→ quote_line_inputs
→ optional ERP PO payload
```

Each export records `export_manifest_sha256`, `catalogue_snapshot_id`, and `procurement_schedule_id`.

---

## 6. Current state and gap

### 6.1 Already implemented (Vision Engine prototype)

```text
projects
uploads
retrieval_runs / retrieval_run_references
concept_runs
generation_runs
generated_variants / generated_image_assets
generation_review_sets / variant_reviews
approved_concept_manifests
DesignDirection schema
```

The prototype produces immutable generated images and structured design direction. It does **not** yet model:

- editable design regions or masks;
- product/material catalogue;
- region-scoped product retrieval;
- substitution previews;
- per-region selections and approvals;
- procurement schedules or commercial snapshots;
- scope item generation;
- collaborative comments or multi-user project roles beyond a string `reviewer`.

### 6.2 Gap this ERD closes

```text
Generation output ends at "approved concept image"
Concept board starts at "decompose image into editable regions"
Commercial workflow ends at "procurement-ready, scope-linked selections"
```

The concept board is the missing layer between **visual design approval** and **real-world specification and ordering**.

---

## 7. ERD

The diagram below is the **canonical logical model**. Implementation may use one database initially; bounded contexts in section 4 define future service splits.

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ PROJECTS : owns
    ORGANIZATIONS ||--o{ ORG_MEMBERS : has
    USERS ||--o{ ORG_MEMBERS : joins
    USERS ||--o{ PROJECT_MEMBERS : joins
    PROJECTS ||--o{ PROJECT_MEMBERS : has
    PROJECTS ||--o{ CONCEPT_BOARDS : contains
    PROJECTS ||--o{ PROCUREMENT_SCHEDULES : owns

    CONCEPT_BOARDS ||--o{ CONCEPT_DIRECTIONS : contains
    CONCEPT_BOARDS ||--o{ BOARD_COMMENT_THREADS : has
    BOARD_COMMENT_THREADS ||--o{ BOARD_COMMENTS : contains
    CONCEPT_DIRECTIONS ||--o{ CONCEPT_VERSIONS : versions
    CONCEPT_VERSIONS ||--o{ CONCEPT_ASSETS : has
    CONCEPT_VERSIONS ||--o| CONCEPT_VERSION_PROVENANCE : traced_by
    CONCEPT_DIRECTIONS ||--o{ DESIGN_REGIONS : defines
    DESIGN_REGIONS ||--o{ REGION_GEOMETRIES : represented_by
    CONCEPT_VERSIONS ||--o{ REGION_GEOMETRIES : contains
    CONCEPT_VERSIONS ||--o{ REGION_DETECTION_RUNS : analysed_by

    DESIGN_REGIONS ||--o{ REGION_REQUIREMENTS : constrained_by
    DESIGN_REGIONS ||--o{ PRODUCT_RETRIEVAL_RUNS : queries
    PRODUCT_RETRIEVAL_RUNS ||--o{ REGION_CANDIDATES : produces
    PRODUCTS ||--o{ REGION_CANDIDATES : proposed_for
    MATERIALS ||--o{ REGION_CANDIDATES : proposed_for
    REGION_CANDIDATES ||--o{ CANDIDATE_SCORES : scored_by

    CATALOGUE_SNAPSHOTS ||--o{ CATALOGUE_SNAPSHOT_ITEMS : freezes
    PRODUCTS ||--o{ CATALOGUE_SNAPSHOT_ITEMS : versioned_in
    MATERIALS ||--o{ CATALOGUE_SNAPSHOT_ITEMS : versioned_in
    PRODUCT_RETRIEVAL_RUNS ||--o{ PRODUCT_RETRIEVAL_INDEX_VERSIONS : uses
    CATALOGUE_SNAPSHOTS ||--o{ PRODUCT_RETRIEVAL_INDEX_VERSIONS : indexed_from

    PRODUCTS ||--o{ PRODUCT_VARIANTS : has
    PRODUCTS ||--o{ PRODUCT_ASSETS : illustrated_by
    MATERIALS ||--o{ MATERIAL_VARIANTS : has
    MATERIALS ||--o{ MATERIAL_ASSETS : illustrated_by
    SUPPLIERS ||--o{ SUPPLIER_OFFERS : publishes
    PRODUCT_VARIANTS ||--o{ SUPPLIER_OFFERS : sold_as
    MATERIAL_VARIANTS ||--o{ SUPPLIER_OFFERS : sold_as
    SUPPLIER_OFFERS ||--o{ OFFER_PRICE_HISTORY : tracks

    REGION_CANDIDATES ||--o{ SUBSTITUTION_PREVIEWS : generates
    CONCEPT_VERSIONS ||--o{ SUBSTITUTION_PREVIEWS : based_on
    SUBSTITUTION_PREVIEWS ||--o{ SUBSTITUTION_GENERATION_RUNS : produced_by
    SUBSTITUTION_PREVIEWS ||--o{ REVIEW_DECISIONS : reviewed_by
    USERS ||--o{ REVIEW_DECISIONS : makes

    DESIGN_REGIONS ||--o{ REGION_SELECTIONS : has
    REGION_CANDIDATES ||--o{ REGION_SELECTIONS : selected_from
    CONCEPT_VERSIONS ||--o{ REGION_SELECTIONS : effective_in
    USERS ||--o{ REGION_SELECTIONS : selected_by

    CONCEPT_VERSIONS ||--o{ APPROVAL_EVENTS : reviewed
    USERS ||--o{ APPROVAL_EVENTS : performs

    PROCUREMENT_SCHEDULES ||--o{ PROCUREMENT_ITEMS : contains
    REGION_SELECTIONS ||--o{ PROCUREMENT_ITEMS : creates
    SUPPLIER_OFFERS ||--o{ PROCUREMENT_ITEMS : priced_by
    CATALOGUE_SNAPSHOTS ||--o{ PROCUREMENT_SCHEDULES : pinned_to

    SUPPLIERS ||--o{ PURCHASE_ORDERS : receives
    PROCUREMENT_SCHEDULES ||--o{ PURCHASE_ORDERS : creates
    PURCHASE_ORDERS ||--o{ PURCHASE_ORDER_LINES : contains
    PROCUREMENT_ITEMS ||--o{ PURCHASE_ORDER_LINES : ordered_as

    PROJECTS ||--o{ SCOPE_ITEMS : has
    REGION_SELECTIONS ||--o{ SCOPE_ITEMS : informs
    PROCUREMENT_ITEMS ||--o{ SCOPE_ITEMS : specifies
    PROJECTS ||--o{ INTEGRATION_EXPORTS : exports
    PROCUREMENT_SCHEDULES ||--o{ INTEGRATION_EXPORTS : source_for

    PROJECTS ||--o{ DOMAIN_EVENTS : emits

    ORGANIZATIONS {
        uuid organization_id PK
        string organization_name UK
        string organization_type
        string default_currency_code
        string default_country_code
        datetime created_at
    }

    ORG_MEMBERS {
        uuid org_member_id PK
        uuid organization_id FK
        uuid user_id FK
        string org_role
        datetime joined_at
        datetime removed_at
    }

    PROJECTS {
        uuid project_id PK
        uuid organization_id FK
        string project_name
        string project_type
        string room_type
        string status
        string currency_code
        string country_code
        string source_vision_project_id
        datetime created_at
        datetime updated_at
    }

    USERS {
        uuid user_id PK
        string email UK
        string display_name
        string user_type
        datetime created_at
        datetime deactivated_at
    }

    PROJECT_MEMBERS {
        uuid project_member_id PK
        uuid project_id FK
        uuid user_id FK
        string role
        string permission_level
        datetime joined_at
        datetime removed_at
    }

    CONCEPT_BOARDS {
        uuid concept_board_id PK
        uuid project_id FK
        string board_name
        string status
        integer version
        datetime created_at
        datetime updated_at
    }

    CONCEPT_DIRECTIONS {
        uuid concept_direction_id PK
        uuid concept_board_id FK
        string direction_name
        string design_intent_json
        string status
        datetime created_at
        datetime archived_at
    }

    CONCEPT_VERSIONS {
        uuid concept_version_id PK
        uuid concept_direction_id FK
        uuid parent_concept_version_id FK
        integer version_number
        string version_reason
        string generation_provider
        string generation_model
        string prompt_version
        string status
        string content_sha256
        datetime created_at
        datetime approved_at
    }

    CONCEPT_ASSETS {
        uuid concept_asset_id PK
        uuid concept_version_id FK
        string asset_type
        string storage_uri
        string mime_type
        string asset_sha256 UK
        integer width
        integer height
        string rights_status
        datetime created_at
    }

    CONCEPT_VERSION_PROVENANCE {
        uuid provenance_id PK
        uuid concept_version_id FK UK
        string source_vision_project_id
        string generation_run_id
        string concept_run_id
        string retrieval_run_id
        string source_variant_id
        string approved_manifest_id
        string design_direction_json
        string reference_ids_json
        datetime created_at
    }

    BOARD_COMMENT_THREADS {
        uuid thread_id PK
        uuid concept_board_id FK
        uuid design_region_id FK
        uuid concept_version_id FK
        string thread_type
        string status
        datetime created_at
    }

    BOARD_COMMENTS {
        uuid comment_id PK
        uuid thread_id FK
        uuid author_user_id FK
        string body
        string comment_kind
        datetime created_at
        datetime edited_at
    }

    REGION_DETECTION_RUNS {
        uuid detection_run_id PK
        uuid concept_version_id FK
        string provider
        string model_name
        string prompt_version
        string status
        string output_json
        datetime created_at
    }

    CATALOGUE_SNAPSHOTS {
        uuid catalogue_snapshot_id PK
        string snapshot_name UK
        string manifest_uri
        string manifest_sha256 UK
        integer item_count
        string status
        datetime created_at
        datetime sealed_at
    }

    CATALOGUE_SNAPSHOT_ITEMS {
        uuid snapshot_item_id PK
        uuid catalogue_snapshot_id FK
        uuid product_id FK
        uuid material_id FK
        uuid product_variant_id FK
        uuid material_variant_id FK
        string item_sha256
    }

    PRODUCT_ASSETS {
        uuid product_asset_id PK
        uuid product_id FK
        string asset_sha256 UK
        string storage_uri
        string mime_type
        string asset_role
        datetime created_at
    }

    MATERIAL_ASSETS {
        uuid material_asset_id PK
        uuid material_id FK
        string asset_sha256 UK
        string storage_uri
        string mime_type
        string asset_role
        datetime created_at
    }

    OFFER_PRICE_HISTORY {
        uuid price_history_id PK
        uuid supplier_offer_id FK
        decimal unit_price
        string currency_code
        string stock_status
        datetime captured_at
    }

    PRODUCT_RETRIEVAL_INDEX_VERSIONS {
        uuid product_index_version_id PK
        uuid catalogue_snapshot_id FK
        string embedding_model_version
        string status
        string manifest_sha256
        datetime created_at
        datetime activated_at
    }

    PRODUCT_RETRIEVAL_RUNS {
        uuid product_retrieval_run_id PK
        uuid design_region_id FK
        uuid concept_version_id FK
        uuid catalogue_snapshot_id FK
        uuid product_index_version_id FK
        string query_context_json
        integer top_k
        datetime created_at
    }

    SUBSTITUTION_GENERATION_RUNS {
        uuid substitution_run_id PK
        uuid substitution_preview_id FK
        string provider
        string model_name
        string prompt_version
        integer latency_ms
        string status
        datetime created_at
    }

    INTEGRATION_EXPORTS {
        uuid export_id PK
        uuid project_id FK
        uuid procurement_schedule_id FK
        uuid catalogue_snapshot_id FK
        string export_type
        string manifest_uri
        string manifest_sha256 UK
        string status
        datetime created_at
        datetime delivered_at
    }

    DOMAIN_EVENTS {
        uuid event_id PK
        uuid project_id FK
        string aggregate_type
        string aggregate_id
        string event_type
        string payload_json
        datetime occurred_at
        datetime published_at
    }

    DESIGN_REGIONS {
        uuid design_region_id PK
        uuid concept_direction_id FK
        string region_code
        string region_type
        string display_name
        string lifecycle_status
        boolean is_fixed
        datetime created_at
        datetime retired_at
    }

    REGION_GEOMETRIES {
        uuid region_geometry_id PK
        uuid design_region_id FK
        uuid concept_version_id FK
        string geometry_type
        string geometry_json
        string mask_uri
        string mask_sha256
        float confidence
        string source
        datetime created_at
    }

    REGION_REQUIREMENTS {
        uuid region_requirement_id PK
        uuid design_region_id FK
        string requirement_type
        string operator
        string value_json
        string severity
        string source
        datetime created_at
    }

    PRODUCTS {
        uuid product_id PK
        string canonical_name
        string brand_name
        string product_type
        string description
        string manufacturer_sku
        string lifecycle_status
        datetime created_at
        datetime updated_at
    }

    PRODUCT_VARIANTS {
        uuid product_variant_id PK
        uuid product_id FK
        string variant_sku
        string colour
        string finish
        string material
        float width_mm
        float height_mm
        float depth_mm
        float weight_kg
        string attributes_json
        datetime created_at
    }

    MATERIALS {
        uuid material_id PK
        string canonical_name
        string material_category
        string description
        string application_type
        string lifecycle_status
        datetime created_at
        datetime updated_at
    }

    MATERIAL_VARIANTS {
        uuid material_variant_id PK
        uuid material_id FK
        string finish
        string colour
        string format
        string unit_of_measure
        string technical_properties_json
        string compliance_data_json
        datetime created_at
    }

    SUPPLIERS {
        uuid supplier_id PK
        string supplier_name
        string supplier_type
        string website_url
        string country_code
        string coverage_json
        string verification_status
        datetime created_at
        datetime updated_at
    }

    SUPPLIER_OFFERS {
        uuid supplier_offer_id PK
        uuid supplier_id FK
        uuid product_variant_id FK
        uuid material_variant_id FK
        string supplier_sku
        decimal unit_price
        string currency_code
        string price_basis
        string stock_status
        integer stock_quantity
        integer lead_time_days_min
        integer lead_time_days_max
        string delivery_coverage_json
        datetime price_checked_at
        datetime valid_until
    }

    REGION_CANDIDATES {
        uuid region_candidate_id PK
        uuid design_region_id FK
        uuid product_retrieval_run_id FK
        uuid product_variant_id FK
        uuid material_variant_id FK
        uuid catalogue_snapshot_id FK
        string candidate_source
        string candidate_status
        string match_rationale_json
        datetime created_at
    }

    CANDIDATE_SCORES {
        uuid candidate_score_id PK
        uuid region_candidate_id FK
        string score_type
        float raw_score
        float normalised_score
        string model_version
        string explanation_json
        datetime created_at
    }

    SUBSTITUTION_PREVIEWS {
        uuid substitution_preview_id PK
        uuid concept_version_id FK
        uuid region_candidate_id FK
        string preview_asset_uri
        string preview_asset_sha256
        string generation_provider
        string generation_model
        string prompt_version
        string status
        datetime created_at
    }

    REVIEW_DECISIONS {
        uuid review_decision_id PK
        uuid substitution_preview_id FK
        uuid reviewer_user_id FK
        string decision
        integer preference_rank
        integer taste_score
        integer realism_score
        integer fit_score
        string notes
        string rejection_reason_json
        datetime created_at
    }

    REGION_SELECTIONS {
        uuid region_selection_id PK
        uuid design_region_id FK
        uuid region_candidate_id FK
        uuid concept_version_id FK
        uuid selected_by_user_id FK
        string selection_status
        integer quantity
        string quantity_basis
        string approval_state
        datetime selected_at
        datetime approved_at
    }

    APPROVAL_EVENTS {
        uuid approval_event_id PK
        uuid concept_version_id FK
        uuid user_id FK
        string approval_type
        string decision
        string comments
        datetime created_at
    }

    PROCUREMENT_SCHEDULES {
        uuid procurement_schedule_id PK
        uuid project_id FK
        uuid catalogue_snapshot_id FK
        string schedule_name
        string status
        string currency_code
        integer version_number
        datetime created_at
        datetime approved_at
    }

    PROCUREMENT_ITEMS {
        uuid procurement_item_id PK
        uuid procurement_schedule_id FK
        uuid region_selection_id FK
        uuid supplier_offer_id FK
        string item_name
        decimal required_quantity
        string unit_of_measure
        decimal unit_price_snapshot
        decimal estimated_total
        string procurement_status
        string substitution_policy
        datetime required_by
        datetime created_at
    }

    PURCHASE_ORDERS {
        uuid purchase_order_id PK
        uuid procurement_schedule_id FK
        uuid supplier_id FK
        string purchase_order_number UK
        string status
        decimal subtotal
        decimal tax_total
        decimal delivery_total
        decimal grand_total
        string currency_code
        datetime issued_at
        datetime accepted_at
    }

    PURCHASE_ORDER_LINES {
        uuid purchase_order_line_id PK
        uuid purchase_order_id FK
        uuid procurement_item_id FK
        string supplier_sku
        decimal ordered_quantity
        string unit_of_measure
        decimal agreed_unit_price
        decimal line_total
        string line_status
    }

    SCOPE_ITEMS {
        uuid scope_item_id PK
        uuid project_id FK
        uuid region_selection_id FK
        uuid procurement_item_id FK
        string work_package_code
        string scope_description
        string inclusion_json
        string exclusion_json
        string assumption_json
        string approval_status
        datetime created_at
        datetime updated_at
    }
```

---

## 8. Entity Responsibilities

### Platform context

#### `organizations` and `org_members`
Multi-tenant foundation for the future web app. A practice, developer, or supplier org owns projects and controls default commercial settings (currency, country). Users may belong to multiple orgs with distinct roles.

#### `domain_events`
Append-only integration log for async workflows: procurement export triggered, selection approved, catalogue snapshot sealed. Consumers (integration worker, notifications, analytics) subscribe without coupling write paths.

### Concept workspace context

#### `concept_boards`
Persistent collaborative workspace for one project. Contains design directions, current concepts, comments, decisions, approved selections, and procurement status.

#### `concept_directions`
Represents a coherent design direction such as `Warm Contemporary European`, `Minimal High-Contrast`, or `Lower-Cost Conservative Option`.

#### `concept_versions`
One immutable state of a concept direction.

Example:

```text
Version 1: AI-generated base concept
Version 2: sofa replaced
Version 3: flooring replaced
Version 4: lighting revised
Version 5: architect-approved concept
```

Recommended statuses:

```text
draft
generated
under_review
client_approved
architect_approved
superseded
rejected
archived
```

#### `concept_version_provenance`
Immutable bridge from a concept version to Vision Engine generation, retrieval, and approved-manifest records. Enables traceability without duplicating the upstream schema.

#### `board_comment_threads` and `board_comments`
Collaboration layer for the web app. Threads attach to a board, region, or version. Comments support review notes, client feedback, and procurement questions without mutating authoritative selections.

#### `region_detection_runs`
Provenance for AI-proposed region boundaries. Stores model, prompt version, and raw detection output before architect confirmation writes `design_regions` and `region_geometries`.

#### `design_regions`
Stable logical element within a design direction, such as `sofa_01`, `floor_finish_01`, or `main_pendant_01`.

Use `is_fixed` for protected elements such as structural walls, windows, fireplaces, radiators, and fixed plumbing.

#### `region_geometries`
Maps a logical region to pixels or geometry in one concept version.

Supported types:

```text
polygon
bounding_box
segmentation_mask
surface_map
```

#### `region_requirements`
Stores constraints used to retrieve suitable products or materials.

Examples:

```text
maximum_width <= 2200 mm
colour_family = warm_neutral
material = linen_or_wool
budget <= £3,000
delivery_postcode = SW1
lead_time <= 42 days
fire_rating = required
```

Requirement severity:

```text
hard
soft
preference
```

### Product catalogue context

#### `catalogue_snapshots` and `catalogue_snapshot_items`
Immutable pin of the commercial catalogue at a point in time. Required for reproducible product retrieval, candidate ranking, and procurement price justification. Only `sealed` snapshots may drive production retrieval or approved schedules.

#### `products`, `product_variants`, `materials`, `material_variants`
Use `products` for canonical identity and `product_variants` for sellable variations. Materials remain separate because they require coverage, technical data, compliance information, and units of measure.

#### `product_assets` and `material_assets`
Content-addressed catalogue imagery used for visual similarity retrieval and UI display. Separate from concept assets.

#### `supplier_offers` and `offer_price_history`
Time-bound commercial offer for a product or material variant. `offer_price_history` append-only; live offer rows may update, but procurement always snapshots at decision time.

#### `product_retrieval_index_versions` and `product_retrieval_runs`
Parallel to Vision Engine reference retrieval. Indexes product assets from a sealed catalogue snapshot. Each run records query context (region crop hash, requirements, budget) and produces `region_candidates`.

#### `region_candidates`
A proposed product or material for a design region, always tied to a `product_retrieval_run_id` and `catalogue_snapshot_id`.

Candidate sources:

```text
visual_similarity
text_similarity
rule_match
architect_selection
user_search
supplier_promotion
```

#### `candidate_scores`
Persist independent score components such as:

```text
visual_similarity
style_fit
dimensional_fit
material_fit
budget_fit
stock_score
lead_time_score
architect_quality
overall_reranker
```

#### `substitution_previews` and `substitution_generation_runs`
Generated previews showing a real item or material swapped into the concept. `substitution_generation_runs` records provider, model, prompt version, and latency — mirroring `generation_runs` in Vision Engine.

#### `review_decisions`
Captures architect and user evaluations of previews. Rejection reasons should be structured: wrong scale, wrong colour, unrealistic placement, geometry damage, too expensive, out of stock.

#### `region_selections`
Authoritative selected item for a region in a specific concept version.

Lifecycle:

```text
draft
client_selected
architect_approved
procurement_approved
ordered
installed
```

### Procurement context

#### `procurement_schedules`
Versioned list of approved products and materials required for a project. Must reference the `catalogue_snapshot_id` active at schedule creation.

#### `procurement_items`
One orderable line, including selected supplier, quantity, price snapshot, required-by date, and substitution policy.

Recommended substitution policies:

```text
no_substitution
architect_approval_required
client_approval_required
equivalent_allowed
```

#### `purchase_orders`
Groups approved procurement items by supplier.

#### `scope_items`
Links visual selections to downstream work requirements and quotation.

### Integration context

#### `integration_exports`
Immutable export manifests for scope, quote, and ERP systems. Records source schedule, catalogue snapshot, and content hash for idempotent downstream ingestion.

---

## 9. Enumerations and shared vocabulary

Align enums with Vision Engine and dataset_factory where concepts overlap. Store as string enums in the database; validate in application layer.

### Region types (initial set)

```text
sofa · armchair · coffee_table · side_table · dining_table · chair
floor_finish · wall_finish · ceiling_finish · joinery · built_in
pendant_light · floor_lamp · table_lamp · curtains · blinds · rug
artwork · mirror · plant · decorative_object · structural_fixed
```

### Region lifecycle

```text
proposed · confirmed · retired
```

### Candidate and selection status

```text
draft · shortlisted · preview_generated · rejected · selected · superseded
```

### Approval types

```text
client_design_approval · architect_design_approval · technical_review
procurement_approval · commercial_approval · region_geometry_confirmation
```

### Catalogue snapshot status

```text
draft · validated · sealed · deprecated
```

### Procurement schedule status

```text
draft · under_review · approved · superseded · cancelled
```

### Integration export types

```text
scope_csv · scope_json · quote_lines · procurement_pdf · erp_purchase_order
```

### Project member roles (web app)

```text
owner · architect · client · procurement · viewer
```

---

## 10. Critical Constraints and Invariants

### 10.1 Concept immutability

```text
An approved concept_version cannot be updated.
Any change creates a child concept_version.
```

### 10.2 Single approved selection

```text
At most one active architect-approved region_selection
per design_region and concept_version.
```

### 10.3 Candidate target integrity

A `region_candidate` must reference exactly one of:

```text
product_variant_id
material_variant_id
```

Never both and never neither.

### 10.4 Supplier offer integrity

A `supplier_offer` must reference exactly one of:

```text
product_variant_id
material_variant_id
```

### 10.5 Procurement price snapshots

Once a procurement schedule is approved, these must not be changed in place:

```text
unit_price_snapshot
estimated_total
supplier_offer_id
```

Changes create a new schedule version or change event.

### 10.6 Approval separation

Recommended approval types:

```text
client_design_approval
architect_design_approval
technical_review
procurement_approval
commercial_approval
```

One approval must not imply all others.

### 10.7 Protected regions

If `design_regions.is_fixed = true`, no product candidate, substitution preview, or region selection should be permitted without an explicit privileged override.

### 10.8 Purchase-order authority

Only procurement items in an approved schedule may create purchase-order lines.

### 10.9 Catalogue snapshot pinning

```text
region_candidates.catalogue_snapshot_id must reference a sealed snapshot.

procurement_schedules.catalogue_snapshot_id must reference a sealed snapshot.

product_retrieval_runs must not query against draft or deprecated snapshots.
```

### 10.10 Provenance integrity

```text
concept_version v1 must have concept_version_provenance when bootstrapped from Vision Engine.

substitution_previews.preview_asset_sha256 must be unique per preview output.

Every region_candidate must reference the product_retrieval_run that produced it.
```

### 10.11 Asset hash uniqueness

```text
UNIQUE(concept_assets.asset_sha256) per asset_type where asset_type = primary_render
UNIQUE(product_assets.asset_sha256)
UNIQUE(material_assets.asset_sha256)
UNIQUE(integration_exports.manifest_sha256)
```

### 10.12 Cross-context write rules

```text
Procurement context must not mutate concept_versions or region_geometries.

Catalogue context must not mutate region_selections.

Integration exports are append-only; corrections create a new export_id.
```

---

## 11. Recommended Workflow

### 11.0 Bootstrap from Vision Engine

```text
approved_concept_manifest OR operator promotion
→ concept_board
→ concept_direction
→ concept_version v1 + concept_version_provenance
→ concept_asset (from generated_image_assets)
```

### 11.1 Generate base concept

```text
Vision Engine
→ concept_direction
→ concept_version v1
→ concept_asset
```

### 11.2 Detect editable regions

```text
concept image
→ segmentation/object detection
→ proposed design_regions
→ region_geometries
→ architect/operator review
```

### 11.3 Create requirements

```text
design intent
+ room constraints
+ user budget
+ dimensions
→ region_requirements
```

### 11.4 Retrieve candidates

```text
sealed catalogue_snapshot
+ region crop
+ region_requirements
+ product_retrieval_run
→ region_candidates
→ candidate_scores
→ best supplier_offer per candidate
```

### 11.5 Generate previews

```text
concept_version v1
+ selected candidate
+ region mask
→ substitution_preview
```

### 11.6 Review and select

```text
user/architect review
→ review_decision
→ region_selection
```

### 11.7 Create new concept version

```text
approved substitution
→ concept_version v2
→ updated region geometries
→ inherited unchanged selections
```

### 11.8 Approve procurement

```text
approved region selections
→ procurement schedule
→ procurement items
→ supplier selection
```

### 11.9 Generate commercial outputs

```text
procurement schedule
→ purchase orders
→ scope items
→ quote inputs
→ integration_export manifest
```

---

## 12. Product retrieval algorithm

Reuse the staged retrieval pattern from the multimodal reference ERD, applied to product assets and commercial metadata.

### 12.1 Stage 0 — hard filters

Remove variants that violate region requirements or project constraints:

```text
wrong product_type / material_category for region_type
dimension out of bounds (hard requirements)
budget band exceeded
delivery postcode not covered
lead time exceeds hard limit
discontinued lifecycle_status
```

### 12.2 Stage 1 — high-recall candidate retrieval

Query signals from a sealed `catalogue_snapshot`:

```text
region crop embedding ↔ product_asset embedding (visual similarity)
design_intent text ↔ product description / attributes (text similarity)
structured metadata match (colour, material, finish, dimensions)
supplier offer availability and price band
```

Fuse ranked lists with reciprocal-rank fusion. Persist all candidates in `region_candidates` with `candidate_scores`.

### 12.3 Stage 2 — rerank for region fit

Rerank top N candidates using:

```text
(region crop, region_requirements, design_intent, product images, variant attributes, best offer)
```

The reranker answers: “Would this real product plausibly replace this design element?”

### 12.4 Stage 3 — offer selection

For each shortlisted candidate, attach the best eligible `supplier_offer` for the project's `country_code` and delivery constraints. Offer selection is separate from visual fit.

### 12.5 Stage 4 — substitution preview generation

Only after shortlisting, invoke image edit (same client abstraction as Vision Engine `ImageEditClient`) to produce `substitution_previews`. Preview generation must record `substitution_generation_runs` provenance.

---

## 13. Storage and asset conventions

### 13.1 URI layout (local prototype)

```text
data/concept_boards/{project_id}/{concept_board_id}/
  versions/{concept_version_id}/primary.png
  versions/{concept_version_id}/masks/{design_region_id}.png
  previews/{substitution_preview_id}.png

data/catalogue/
  products/{product_id}/{asset_sha256}.jpg
  materials/{material_id}/{asset_sha256}.jpg
  snapshots/{catalogue_snapshot_id}/manifest.json

data/exports/
  procurement/{procurement_schedule_id}/schedule.csv
  integration/{export_id}/manifest.json
```

### 13.2 Web app storage (production)

Use object storage (S3/GCS) with the same hash-based identity. Serve assets via signed URLs; never expose raw filesystem paths in public APIs.

### 13.3 Shared conventions with Vision Engine

| Convention | Vision Engine | Concept board |
|------------|---------------|---------------|
| ID prefix | `proj_`, `var_`, `gen_` | `cb_`, `cv_`, `dr_`, `rc_`, `ps_` |
| Content hash | SHA-256 of file bytes | Same |
| Immutability | No overwrite of approved assets | Same |
| Provenance | run_id + prompt_version + model | Same pattern for detection, retrieval, substitution |

---

## 14. API and integration contracts

These contracts allow the Gradio prototype, future web app, and export workers to share one model.

### 14.1 Concept board API (representative)

| Operation | Input | Output |
|-----------|-------|--------|
| `POST /projects/{id}/concept-boards` | `source_variant_id` or `manifest_id` | `concept_board_id`, `concept_version_id` |
| `POST /concept-boards/{id}/regions/detect` | `concept_version_id` | `detection_run_id`, proposed regions |
| `PUT /regions/{id}/confirm` | geometry, `is_fixed` | confirmed `design_region_id` |
| `POST /regions/{id}/retrieve-products` | requirements override | `product_retrieval_run_id`, candidates |
| `POST /candidates/{id}/preview` | — | `substitution_preview_id` |
| `POST /regions/{id}/select` | `region_candidate_id`, quantity | `region_selection_id` |
| `POST /concept-versions` | parent version + applied selections | new `concept_version_id` |
| `POST /procurement-schedules` | approved selections | schedule + items |

All write endpoints emit `domain_events`. Read endpoints return stable DTOs with asset URLs, not internal paths.

### 14.2 Integration export manifest (minimum shape)

```json
{
  "export_schema_version": "procurement-scope.v1",
  "export_id": "exp_...",
  "project_id": "proj_...",
  "procurement_schedule_id": "ps_...",
  "catalogue_snapshot_id": "cs_...",
  "manifest_sha256": "...",
  "items": [
    {
      "scope_item_id": "si_...",
      "design_region_code": "sofa_01",
      "concept_version_number": 3,
      "product_name": "...",
      "supplier_name": "...",
      "supplier_sku": "...",
      "quantity": 1,
      "unit_price_snapshot": 2499.00,
      "currency_code": "GBP",
      "substitution_policy": "architect_approval_required"
    }
  ]
}
```

### 14.3 Read model for web app UI

Define a denormalised projection `concept_board_workspace_view` joining:

```text
concept_board
→ active concept_direction
→ latest approved concept_version
→ design_regions + region_geometries
→ active region_selections
→ pending substitution_previews
→ procurement_schedule summary
→ unread comment counts
```

The write model remains normalised; the projection can be rebuilt from `domain_events`.

---

## 15. MVP Scope

Build only:

- projects (extended with `source_vision_project_id`)
- concept boards, directions, versions, provenance bridge
- concept assets (content-hashed)
- manually created design regions and masks
- local product/material catalogue (no live feeds)
- one sealed catalogue snapshot
- supplier offers with manual price entry
- product retrieval (rule + visual stub acceptable in MVP)
- region candidates and scores
- substitution previews
- region selections and approval events
- procurement schedule + CSV export
- `integration_exports` for scope handoff

Defer to post-MVP:

- organizations / multi-tenant auth (use string `reviewer` like Vision Engine prototype)
- board comments
- purchase orders and supplier transactions
- product retrieval index versioning (single snapshot OK initially)
- domain event bus (direct writes acceptable in SQLite prototype)

Do not initially build:

- autonomous purchasing
- payment processing
- live multi-supplier stock synchronisation
- contractor marketplace
- automated compliance guarantees
- fully automatic quantity take-off

---

## 16. Production Evolution

### Phase 1 — Manual catalogue and review

```text
local product catalogue
manual region selection
AI-assisted matching
manual approval
CSV/PDF procurement export
```

### Phase 2 — Supplier feeds

```text
scheduled catalogue ingestion
price and stock refresh
SKU normalisation
lead-time checks
supplier baskets
```

### Phase 3 — Transaction workflow

```text
purchase orders
supplier acknowledgement
delivery tracking
substitutions
returns
commercial reconciliation
```

### Phase 4 — Learning system

Use outcomes to improve:

- product ranking
- substitution quality
- style fit
- price prediction
- approval probability
- supplier recommendation

---

## 17. Migration plan

### Phase 1 — Schema foundation (Vision Engine extension)

1. Add concept-board tables to the Vision Engine SQLite schema (or adjacent module with shared `project_id`).
2. Implement `concept_version_provenance` and bootstrap from `generated_variants` + `approved_concept_manifests`.
3. Extend Gradio with a "Open concept board" action after variant approval.
4. Keep product catalogue in separate tables; seed from CSV.

### Phase 2 — Region editing and matching

1. Add manual region drawing in Gradio (polygon/mask upload).
2. Add `region_requirements` derived from `DesignDirection` + project constraints.
3. Implement rule-based product matching; stub visual retrieval behind same `product_retrieval_runs` interface.
4. Add substitution preview via existing `ImageEditClient`.

### Phase 3 — Procurement and export

1. Implement `procurement_schedules` with catalogue snapshot pinning.
2. Add CSV/PDF export and `integration_exports`.
3. Generate `scope_items` from approved selections.

### Phase 4 — Web app and scale

1. Extract bounded contexts into services; add `organizations`, auth, comments.
2. Replace SQLite with Postgres; object storage for assets.
3. Add sealed catalogue ingestion pipeline (mirrors dataset_factory snapshot pattern).
4. Build product retrieval index with real embeddings; separate from reference index.
5. Add domain event bus and read-model projections for UI performance.

---

## 18. Test requirements

### Unit tests

- approved `concept_version` rejects in-place asset overwrite;
- bootstrap creates provenance when source variant exists;
- `region_candidate` XOR product/material variant constraint enforced;
- sealed snapshot required for production retrieval run;
- approved procurement schedule blocks price snapshot mutation;
- fixed region blocks selection without override;
- export manifest hash stable for identical inputs.

### Integration tests

```text
promote approved variant
→ create concept board
→ define regions
→ retrieve candidates from sealed snapshot
→ generate substitution preview
→ select and approve
→ create concept_version v2
→ build procurement schedule
→ export integration manifest
→ verify full lineage to generation_run_id
```

### Regression tests with Vision Engine

- concept board bootstrap does not mutate `generated_variants` or `approved_concept_manifests`;
- reference retrieval index and product retrieval index remain isolated;
- Gradio and CLI can operate on same SQLite database without schema conflict.

---

## 19. Data Captured as Strategic Moat

The system captures:

```text
design intent
→ generated concept
→ editable region
→ alternatives shown
→ alternatives rejected
→ item selected
→ architect approval
→ supplier chosen
→ price paid
→ item delivered
→ item installed
→ final project outcome
```

This creates a proprietary design-to-commerce graph.

The moat is not the image-editing model itself. It is the accumulated knowledge of:

- which real products satisfy which design intentions
- which substitutions preserve aesthetic quality
- which items fit particular rooms and budgets
- which products are approved or rejected
- which suppliers perform reliably
- which selections lead to successful completed outcomes

---

## 20. Acceptance Criteria

The ERD is successfully implemented when:

1. A generated concept can be stored as an immutable version.
2. A user can define or approve editable design regions.
3. Each region can retrieve multiple real product or material candidates.
4. Every candidate can be scored and explained.
5. A candidate can be previewed inside the concept image.
6. User and architect decisions are persisted.
7. An approved substitution creates a new concept version.
8. Approved selections can generate procurement items.
9. Supplier prices are captured as immutable commercial snapshots.
10. Procurement items can feed scope and quotation systems.
11. Every decision can be traced from concept to product, approval, supplier and purchase order.
12. Rejected and approved alternatives remain available for future preference learning.
13. A concept board can be bootstrapped from an approved Vision Engine variant with full upstream provenance.
14. Product retrieval and reference retrieval use separate indexes and snapshots.
15. Procurement exports are reproducible from pinned catalogue snapshots and immutable price snapshots.
16. The same schema supports Gradio prototype operation and future web app extraction without redesign.

---

## 21. Final Recommendation

Implement in this order:

```text
Vision Engine approved concept bootstrap
→ concept board + immutable concept versions
→ logical design regions + provenance bridge
→ sealed product/material catalogue snapshot
→ product retrieval + candidate scoring
→ substitution previews
→ client and architect approvals
→ procurement schedule + integration export
→ scope integration
→ web app platform layer (orgs, comments, auth)
→ supplier ordering
```

The most important engineering decision is to preserve the complete decision history.

The commercially valuable dataset is not simply the final room image. It is:

```text
what was generated
→ what could be swapped
→ what alternatives were considered
→ what was rejected
→ what was approved
→ what was bought
→ what was successfully installed
```

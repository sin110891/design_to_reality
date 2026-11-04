# Design to Reality

Monorepo for design-intelligence tooling.

## Packages

| Directory | Purpose |
|---|---|
| [`dataset_factory/`](dataset_factory/) | Hybrid rulebook + multimodal labelling pipeline (gold dataset builder) |

## Quick start (dataset factory)

```bash
cd dataset_factory
make install
make report
```

See [`dataset_factory/docs/overview_runbook.md`](dataset_factory/docs/overview_runbook.md) for the full Make-based runbook.

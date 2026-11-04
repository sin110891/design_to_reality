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

## Reproducible tests (Docker / CI)

Runs both packages' test suites from a clean clone with fake providers, with no API keys or local `data/` needed. Test inputs are synthetic fixtures under `*/tests/fixtures/`.

```bash
docker build -t dtr . && docker run --rm dtr
```

CI (`.github/workflows/ci.yml`) runs the same on every push to `master` and on every PR. Pinned dependency versions live in `constraints.txt`.

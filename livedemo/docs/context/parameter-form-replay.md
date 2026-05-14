# Parameter Form And Replay Context

## Scope

Milestone 6 adds editable ranking parameters for new executions, faithful replay
from old execution configs, and focused validation coverage. It does not add
evaluation helpers, the old-executions index, cross-execution comparison, or
polish from later milestones.

## Current Repository Shape

- `app/schemas.py` already defines execution request models, a
  `RankerConfigPayload`, and `normalize_ranker_config()` that constructs
  `RankerConfig` and persists a full `config_json`.
- `app/routers/executions.py` exposes rank/select/compare/list/detail/delete,
  creates execution rows, and submits work through `submit_execution()`.
- `app/services/pipeline_runner.py` runs the library pipeline in a background
  executor and persists one result row for rank/select/compare.
- The frontend is split across `frontend/src/app`, `pages`, `components`,
  `forms`, `artifacts`, and `utils`; corpus workspace owns article upload,
  inspection/decomposition, ranking controls, and execution polling.
- `frontend/src/api/client.ts` has typed API helpers for corpus/article CRUD and
  execution start/detail calls.
- Tests use `TestClient`, fake decomposition, fake embeddings, and helper
  functions in `tests/test_executions.py`.

## Library Interfaces

- `news_ranker.config.RankerConfig` is the canonical source of validation rules:
  similarity threshold must be finite and between -1 and 1, linkage is
  `average` or `single`, coverage weighting is `consensus` or `rarity`,
  profile names are non-empty, profile weights must have exactly centrality,
  coverage, density, and entity coverage keys, weights must be finite,
  non-negative, and sum to 1, `top_m` must be positive when provided,
  selection mode is `top_score` or `mmr`, and selection lambda is finite in
  `[0, 1]`.
- The live-demo schemas should expose these constraints through OpenAPI where
  practical, while still using explicit server normalization for byte-stable
  persisted config.

## Implementation Constraints

- Replay must reuse the previous `execution.config_json` verbatim unless the
  caller overrides `corpus_id`; the new execution row should have an identical
  `config_json` byte-for-byte after JSON round-trip.
- The new replay endpoint should infer the original execution kind, profile
  list, and selection `m` from the prior execution row/config.
- The parameter form should support rank, select, and compare modes, default
  configs for new runs, and read-only metadata fields.
- Frontend changes should stay inside the current compact SPA/module structure
  rather than introducing routing or state libraries beyond TanStack Query.
- Milestone 6 tests should focus on validation failures, effective default
  config persistence, replay fidelity, and alternate-corpus replay.

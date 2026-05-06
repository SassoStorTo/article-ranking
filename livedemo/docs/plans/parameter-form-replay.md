# Parameter Form And Replay Plan

## Goal

Implement only Milestone 6 from `docs/brief.md`: server-side ranker config
validation, an editable frontend parameter form, execution replay, replay
prefill, and tests proving validation and replay fidelity.

## Steps

1. Tighten execution config schemas and normalization so FastAPI/OpenAPI expose
   validation constraints and server errors cover profile keys, non-negative
   weights, weight sums, linkage, coverage weighting, selection mode,
   selection lambda, and `top_m`.
2. Replace quick execution buttons with a parameter form that handles rank,
   select, and compare modes, profile weights, clustering/coverage/selection
   controls, default config values, and read-only metadata fields.
3. Add `POST /api/executions/{id}/replay`, reusing the prior execution config
   and optionally targeting a different corpus while submitting the same kind
   of execution.
4. Wire a Replay button in execution detail so old config values prefill the
   parameter form and can be edited before creating a new run.
5. Add tests for invalid config payloads, persisted default effective config,
   byte-identical replay config, and replay on an alternate corpus.

## Verification

- Run the livedemo pytest suite.
- Run the frontend build.
- Run `make check` from the parent repository before declaring the milestone
  complete, or report the exact blocker if the environment cannot complete it.

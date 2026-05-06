# Execution Result Serialization Plan

## Goal

Implement only Milestone 5 from `docs/brief.md`: JSON result shims, execution
schemas/config normalization, a pipeline runner, rank/select/compare endpoints,
basic frontend polling/detail tables, and focused tests.

## Steps

1. Add `app/serialize.py` for `to_jsonable()` / `from_jsonable()` over result
   dataclasses, numpy arrays, `ScoreVector`, `FactUniverse`, diagnostics, rank
   entries, selection results, and profile comparisons.
2. Extend `app/schemas.py` with execution request/response/filter/detail
   models and a config payload that normalizes through `RankerConfig`.
3. Add embedder dependency wiring in `app/deps.py` and implement
   `app/services/pipeline_runner.py` to create executions, run the requested
   pipeline method, persist status/timestamps/errors, and write result rows.
4. Add `app/routers/executions.py`, mount it in `main.py`, and support POST
   rank/select/compare plus list/detail/delete.
5. Extend the frontend API client and main workspace with corpus-level run
   buttons, polling for running execution detail, and simple rank/select/compare
   result tables.
6. Add tests for serializer round-trip, successful and failed execution
   lifecycle, list filters, delete, and detail payloads.

## Verification

- Run the livedemo pytest suite.
- Run frontend type/build checks if package scripts are available.
- Run `make check` before declaring the milestone complete, or report the exact
  blocker if this environment cannot complete it.

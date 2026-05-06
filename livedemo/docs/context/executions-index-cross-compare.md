# Executions Index And Cross-Execution Compare Context

## Scope

Milestone 8 makes old executions discoverable and comparable across corpora. It
includes enriched execution list filters and list metadata, an Executions index
surface, row actions for opening, replaying, deleting, and comparing executions,
and focused API coverage for filtering and persisted compare artifacts. It does
not change provider wiring, ranking behavior, evaluation helper semantics, or
milestone 9 polish.

## Current Repository Shape

- `app/routers/executions.py` exposes rank/select/compare, detail, replay, list,
  and delete endpoints. The list endpoint currently supports corpus, kind,
  status, limit, and offset only, and returns `ExecutionSummary` without corpus
  names or evaluation-artifact presence.
- `app/routers/evaluations.py` exposes top-M overlap and rank-correlation
  endpoints that persist artifacts on the target execution id supplied in the
  path.
- `app/services/evaluators.py` already rebuilds persisted results and rejects
  unsupported shapes or non-succeeded executions with `422`-mapped
  `EvaluationError`s.
- `frontend/src/main.tsx` is a single-file SPA centered on the selected corpus.
  It has an execution detail panel and evaluation panel, but no cross-corpus old
  executions page.
- `frontend/src/api/client.ts` has typed helpers for execution list/detail,
  replay, delete is missing, and evaluation artifact creation.
- Tests already cover execution lifecycle, basic list filters, delete behavior,
  and evaluation helper persistence.

## Implementation Constraints

- The execution list response should remain backward-compatible for execution
  detail consumers while adding corpus name, profile summary, and
  `has_evaluation_artifacts` for the index table.
- Date filtering applies to `execution.created_at`, matching the old executions
  page's date-range filter.
- Profile filtering can be exact against names in the persisted `profiles` JSON
  list; the demo's small data volume makes in-process filtering acceptable after
  the database applies corpus/kind/status/date predicates.
- Cross-execution compare should call the existing top-M overlap and
  rank-correlation endpoints with the selected row as the artifact target, so
  artifacts persist on the chosen target execution as specified.
- The frontend should stay in the current compact React app without adding a
  router or test framework.

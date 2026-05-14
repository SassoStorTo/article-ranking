# Executions Index And Cross-Execution Compare Context

## Scope

Milestone 8 makes old executions discoverable and comparable across corpora. It
includes enriched execution list filters and list metadata, an Executions index
surface, row actions for opening, replaying, deleting, and navigating to a
durable comparison page. Persisted evaluation artifacts remain available from
execution detail, but the comparison page itself is non-mutating. It does not
change provider wiring, ranking behavior, evaluation helper semantics, or
milestone 9 polish.

## Current Repository Shape

- `app/routers/executions.py` exposes rank/select/compare, list, non-mutating
  comparison, detail, replay, and delete endpoints. `GET /api/executions/comparison`
  is declared before `/{execution_id}` so it is not shadowed by the dynamic route.
- `app/routers/evaluations.py` exposes artifact-producing evaluation endpoints
  used by the execution detail evaluation panel. The comparison page does not
  call these endpoints or persist artifacts.
- `app/services/evaluators.py` rebuilds persisted results for artifact creation.
  `app/services/execution_comparison.py` separately rebuilds persisted results
  into comparison sections and warning payloads for read-only page rendering.
- `frontend/src/app/App.tsx` owns the old-executions index route and the durable
  execution comparison route. `/executions/compare`,
  `/executions/compare/:leftExecutionId`, and
  `/executions/compare/:leftExecutionId/:rightExecutionId` are handled without a
  router dependency.
- `frontend/src/api/client.ts` has typed helpers for execution list/detail,
  replay, delete, evaluation artifact creation, and the comparison read model.
- Tests cover execution lifecycle, list filters, delete behavior, evaluation
  helper persistence, and backend comparison response shapes.

## Implementation Constraints

- The execution list response should remain backward-compatible for execution
  detail consumers while adding corpus name, profile summary, and
  `has_evaluation_artifacts` for the index table.
- Date filtering applies to `execution.created_at`, matching the old executions
  page's date-range filter.
- Profile filtering can be exact against names in the persisted `profiles` JSON
  list; the demo's small data volume makes in-process filtering acceptable after
  the database applies corpus/kind/status/date predicates.
- Execution index Compare action should navigate to the durable comparison page
  with the selected row as the left execution. It should be enabled for succeeded
  rank, select, and compare_profiles executions.
- The comparison page should fetch succeeded execution candidates, keep selected
  IDs in the URL path, and call the read-only comparison endpoint only when both
  IDs are present.
- The frontend should stay in the current compact React app without adding a
  router or test framework.

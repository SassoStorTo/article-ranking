# Execution Comparison Page Context

## Scope

Execution comparison is a durable, deep-linkable livedemo page for comparing two
succeeded rank, select, or compare_profiles executions. It is read-only: opening
or refreshing the page does not create evaluation artifacts, mutate executions,
or rerun ranking.

## Backend ownership

- `app/routers/executions.py` exposes `GET /api/executions/comparison` before
  `/{execution_id}` to avoid dynamic-route shadowing.
- `app/services/execution_comparison.py` loads both executions with corpus,
  result, and evaluation-artifact relationships; rejects missing executions with
  `404`; rejects unfinished or resultless executions with `422`.
- `app/schemas.py` defines comparison metadata, warnings, normalized sections,
  section pairs, and metrics response models.
- Comparison sections normalize rank/select into one section and expand
  compare_profiles into one section per profile.
- Section pairing compares one-to-one runs directly, pairs one run against every
  profile section, and pairs compare_profiles sections by profile key. Unmatched
  profiles return warning section pairs rather than server errors.
- Metrics are non-persisted payloads: top-M overlap, Kendall rank correlation
  when available, left/right cluster counts, shared cluster count, and shared
  canonical cluster texts.

## Frontend ownership

- `frontend/src/app/navigation.ts` parses and builds `/executions/compare`,
  `/executions/compare/:leftExecutionId`, and
  `/executions/compare/:leftExecutionId/:rightExecutionId`.
- `frontend/src/app/App.tsx` maps comparison route top nav to Executions and
  mounts `ExecutionComparisonPage` in the single-pane workspace.
- `frontend/src/pages/ExecutionsIndex.tsx` Compare navigates to the comparison
  route with the clicked execution as left side. It is enabled for succeeded
  rank, select, and compare_profiles executions.
- `frontend/src/pages/ExecutionComparisonPage.tsx` fetches succeeded candidates,
  lets users select left/right executions, and calls `getExecutionComparison()`
  only after both ids are present.
- `frontend/src/artifacts/ComparisonResultTables.tsx` renders side-by-side result
  tables for each section pair.
- `frontend/src/styles.css` owns comparison page, metadata, warning, metric, and
  table layout styles.

## Gotchas

- Do not replace this page with evaluation artifact endpoints; those remain for
  `EvaluationPanel` on execution detail.
- Keep comparison route parsing path-segment based; no router library is present.
- Keep comparison API read-only. If future metrics need persistence, add a
  separate artifact flow instead of mutating this endpoint.

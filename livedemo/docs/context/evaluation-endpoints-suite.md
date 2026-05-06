# Evaluation Endpoints Suite Context

## Scope

Milestone 7 exposes `news_ranker.evaluate` helpers against persisted execution
results. It includes evaluator service adapters, API endpoints, full-suite
execution with an explicit baseline, artifact persistence, the execution detail
evaluation panel, and focused tests. It does not include the executions index,
cross-execution compare modal, enriched execution filters, or milestone 9
polish.

## Current Repository Shape

- `app/db/models.py` already defines `EvaluationArtifact` and
  `EvaluationHelper`, related to `Execution` with cascade delete.
- `app/serialize.py` already round-trips `RankResult`, `SelectionResult`, and
  `ProfileComparison` JSON back into frozen library dataclasses.
- `app/routers/executions.py` exposes execution detail but currently only loads
  `execution.results`, not evaluation artifacts.
- `app/services/pipeline_runner.py` persists one `execution_result` row per
  rank, select, or compare execution.
- `frontend/src/main.tsx` renders a single execution detail panel with result
  tables and replay controls.
- `frontend/src/api/client.ts` has typed execution detail calls but no
  evaluation artifact types or API helpers.
- Tests use fake decomposition/embedding fixtures, and
  `tests/test_executions.py` has helpers to create corpora and wait for
  completed executions.

## Library Interfaces

- `top_m_overlap(left, right, m)` accepts two `RankResult` objects.
- `rank_correlation(left, right, method)` accepts two `RankResult` objects and
  `method` as `kendall` or `spearman`.
- `component_score_table(results)` accepts a `RankResult`, sequence of
  `RankResult`, or `ProfileComparison`.
- `cluster_inspection_rows(rank_result, rare_threshold)` accepts one
  `RankResult`; select executions can use their nested ranking.
- `anonymized_user_study_bundle(selection, article_materials, include_scores)`
  accepts a `SelectionResult` and article-material mapping with only `title`,
  `snippet`, and `summary` fields.

## Implementation Constraints

- Evaluation helpers must rebuild records from persisted JSON via
  `from_jsonable()` so old executions remain evaluable after process restart.
- Every helper endpoint should persist one `evaluation_artifact` row with the
  helper enum value, exact params used, and JSON-compatible payload.
- Full-suite evaluation must require `baseline_execution_id`; there is no
  implicit baseline fallback.
- Unsupported execution kinds or incompatible result shapes should return `422`
  with clear messages rather than failing as internal errors.
- Frontend changes stay in the current compact SPA and only add the evaluation
  panel to execution detail.

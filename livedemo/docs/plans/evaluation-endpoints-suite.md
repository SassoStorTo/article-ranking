# Evaluation Endpoints Suite Plan

## Goal

Implement only Milestone 7 from `docs/brief.md`: expose evaluation helpers over
persisted results, store evaluation artifacts, add a full-suite endpoint with an
explicit baseline, render those artifacts in the execution detail UI, and cover
the behavior with tests.

## Steps

1. Add `app/services/evaluators.py` with adapters that load execution results,
   rebuild dataclasses, coerce compatible rank/select/compare shapes, call each
   `news_ranker.evaluate` helper, convert outputs to JSON, and persist artifacts.
2. Add evaluation request/response schemas and `app/routers/evaluations.py`
   with per-helper routes plus `GET /api/executions/{id}/eval`.
3. Add `POST /api/executions/{id}/test-suite`, requiring
   `baseline_execution_id`, running compatible helpers, and persisting all
   produced artifacts.
4. Extend the frontend API client and execution detail panel with evaluation
   controls, baseline selection, artifact renderers, and a JSON download for
   user-study bundles.
5. Add `tests/test_evaluations.py` for each helper endpoint, artifact
   persistence, baseline requirement, unsupported-kind errors, and payload
   shapes.

## Verification

- Run the livedemo pytest suite.
- Run the frontend build.
- Run `make check` from the parent repository before declaring the milestone
  complete, or report the exact blocker if the environment cannot complete it.

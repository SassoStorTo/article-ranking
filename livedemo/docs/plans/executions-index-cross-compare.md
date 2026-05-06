# Executions Index And Cross-Execution Compare Plan

## Goal

Implement only Milestone 8 from `docs/brief.md`: enrich execution listing,
build the old-executions index, add row-level actions and a compare modal, and
cover filtering, pagination, deletion, and compare persistence.

## Steps

1. Extend execution schemas and `GET /api/executions` with created-date and
   profile filters, pagination after filtering, corpus names, profile summaries,
   and evaluation-artifact presence.
2. Extend the frontend API client with the enriched list params/response shape
   and execution deletion helper.
3. Build an Executions index view in the existing SPA with filter controls,
   result table, pagination controls, and row actions to open detail, replay,
   delete, and start compare.
4. Add a compare modal that chooses a compatible succeeded rank/select
   execution, runs top-M overlap and rank correlation against it, persists both
   artifacts on the selected target execution, and invalidates list/detail
   queries for immediate feedback.
5. Add API tests for new filters, pagination, enriched list fields, cascade
   delete behavior, and cross-execution compare artifact persistence plus
   incompatible-shape validation.

## Verification

- Run the livedemo pytest suite.
- Run the frontend build.
- Run `make check` from the parent repository before declaring the milestone
  complete, or report the exact blocker if the environment cannot complete it.

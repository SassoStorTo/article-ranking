# Corpus And Article CRUD Plan

## Goal

Implement only Milestone 3 from `docs/brief.md`: corpus CRUD, `.txt` article
upload/detail, ingestion helpers, basic frontend corpus pages, and tests.

## Steps

1. Add corpus request/response schemas plus `app/routers/corpora.py` for create,
   list, detail, and delete.
2. Add article schemas, an `app/services/ingestion.py` helper for `.txt`
   validation/title derivation/database writes, and `app/routers/articles.py`
   for upload and detail.
3. Wire both routers into `app/main.py` under `/api`.
4. Replace the frontend shell with API client helpers plus basic Corpora and
   Corpus detail views.
5. Add tests for corpus CRUD, upload, title heuristic, `.txt` validation,
   duplicate filename conflicts, article detail, and cascade deletion.

## Verification

- Run the livedemo pytest suite.
- Run frontend build/type checks.
- Run formatting/lint checks for changed files where available.
- Run the parent `make check` before declaring the milestone complete, or report
  the exact blocker if the command is unavailable or fails outside this scope.

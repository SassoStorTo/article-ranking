# Mistral Decomposition Persistence Plan

## Goal

Implement only Milestone 4 from `docs/brief.md`: Mistral client wiring,
decomposition service/persistence, article API status/detail changes, frontend
structured inspection, and tests with fake decomposition clients.

## Steps

1. Add dependency providers for effective ranker defaults and a Mistral
   decomposition client that requires `MISTRAL_API_KEY` unless overridden in
   tests.
2. Add an LLM service that builds `DecompositionConfig`, calls
   `news_ranker.decompose.decompose`, and upserts `StructuredArticle` rows with
   metadata.
3. Extend article upload/detail routes to schedule decomposition, expose manual
   `POST /api/articles/{id}/decompose`, and include decomposition status plus
   latest payload in response schemas.
4. Update the frontend API types and article detail panel to trigger manual
   decomposition and render entities, events, claims, and context from the
   persisted payload.
5. Add tests covering successful persistence, metadata upsert behavior, failed
   decomposition handling, detail payload shape, and upload-triggered background
   scheduling.

## Verification

- Run the livedemo pytest suite.
- Run frontend build/type checks.
- Run formatting/lint checks for changed files.
- Run `make check` before declaring the milestone complete, or report the exact
  blocker if the command cannot complete in this environment.

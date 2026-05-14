# Mistral Decomposition Persistence Context

## Scope

Milestone 4 adds Mistral-backed decomposition for already-uploaded articles and
persists successful `StructuredArticle` payloads for inspection. It does not add
ranking executions, result serialization, evaluation helpers, replay, or new
library behavior.

## Current repository shape

- `app/db/models.py` already defines `StructuredArticle` with the unique key
  `(article_id, llm_model, prompt_version, schema_version)`.
- `app/routers/articles.py` supports upload, article detail, article deletion,
  and manual decomposition.
- `app/services/ingestion.py` creates `Article` rows after `.txt`/`.json`
  validation and commits them atomically with any uploaded structured payloads.
- Tests use dependency overrides and in-memory SQLite through `tests/conftest.py`.
- The frontend has a single corpus workspace in `frontend/src/main.tsx` with
  article list/detail calls in `frontend/src/api/client.ts`.

## Library interfaces

- `news_ranker.decompose.DecompositionConfig` carries model, prompt version, and
  schema version.
- `news_ranker.decompose.decompose(article_mapping, client, config=...)`
  returns a `news_ranker.schemas.StructuredArticle`.
- `news_ranker.mistral.MistralDecompositionClient` raises when constructed
  without an API key.
- `news_ranker.config.RankerConfig` provides default LLM metadata:
  `llm_model_name`, `prompt_version`, and `schema_version`.

## Implementation constraints

- The app should fail fast for real runtime Mistral access when
  `MISTRAL_API_KEY` is missing, but tests must be able to override the client
  without a key.
- Successful decomposition should upsert the matching `structured_article` row
  so manual re-decompose updates the visible payload.
- Article detail and corpus article summaries expose a compact decomposition
  status plus the latest structured payload for detail views.
- `.json` uploads are validated as `news_ranker.schemas.StructuredArticle`,
  persisted immediately as `structured_article` rows with current
  `RankerConfig` LLM metadata, and returned as already decomposed in article
  detail.
- Uploaded structured payloads have `article_id` normalized to the DB article id
  before persistence so downstream ranking sees corpus article ids.
- Failed decomposition should not invent schema outside the brief's data model;
  manual failures surface as HTTP errors and background failures are handled
  without persisting partial payloads.

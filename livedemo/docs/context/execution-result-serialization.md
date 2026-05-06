# Execution Result Serialization Context

## Scope

Milestone 5 adds rank, select, and compare profile executions with durable JSON
results. It does not add replay, configurable parameter forms beyond accepting
request payloads, evaluation helpers, or the old-executions index polish from
later milestones.

## Current repository shape

- `app/db/models.py` already defines `Execution` and `ExecutionResult` with
  enum kind/status fields, JSON config/profiles/result columns, timestamps, and
  corpus cascade behavior.
- `app/routers/articles.py` and `app/routers/corpora.py` are the only routers
  currently mounted in `app/main.py`.
- Uploaded article bodies are stored in `Article`, while structured Mistral
  output is stored in `StructuredArticle.payload_json`.
- Tests use `create_app(db_engine=...)` plus dependency overrides for the DB
  session factory and fake decomposition client.
- The frontend is a compact single-file React app backed by
  `frontend/src/api/client.ts`.

## Library interfaces

- `news_ranker.pipeline.NewsRanker` requires an explicit `FactEmbedder`.
- `NewsRanker.rank`, `select`, and `compare_profiles` accept raw article
  mappings when a decomposer callable is supplied.
- `RankerConfig` is a frozen dataclass; constructing it is the canonical
  validation/normalization step for milestone 5.
- Result records are frozen dataclasses with numpy arrays in diagnostics:
  `RankResult`, `SelectionResult`, `ProfileComparison`, `RankDiagnostics`,
  `RankingEntry`, `FactUniverse`, and `ScoreVector`.

## Implementation constraints

- Persist the full effective `RankerConfig` in `execution.config_json`, plus
  selection metadata needed by the endpoint.
- Store one `ExecutionResult` row for rank/select, and one row per profile for
  compare so detail views can render profile-specific tables.
- Rebuild result records from JSON for tests and future evaluation work, casting
  fact-universe arrays back to numpy arrays.
- Tests must not download embedding models or call Mistral; the app needs an
  overridable embedder dependency and should use the existing fake decomposition
  flow.
- Execution endpoints can run synchronously under `asyncio.to_thread` while
  still exposing the pending/running/succeeded/failed lifecycle through
  persisted status fields.

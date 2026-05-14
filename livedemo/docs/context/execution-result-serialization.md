# Execution Result Serialization Context

## Scope

Milestone 5 adds rank, select, and compare profile executions with durable JSON
results. Later comparison and evaluation surfaces consume these persisted JSON
results without changing ranking or selection semantics. It does not add replay,
configurable parameter forms beyond accepting request payloads, evaluation
helpers, or the old-executions index polish from later milestones.

## Current repository shape

- `app/db/models.py` already defines `Execution` and `ExecutionResult` with
  enum kind/status fields, JSON config/profiles/result columns, timestamps, and
  corpus cascade behavior.
- `app/main.py` mounts corpus, article, execution, and evaluation routers. The
  execution router also owns the non-mutating comparison read-model endpoint.
- Uploaded article bodies are stored in `Article`; structured Mistral output
  and validated JSON-upload decompositions are stored in
  `StructuredArticle.payload_json`.
- Tests use `create_app(db_engine=...)` plus dependency overrides for the DB
  session factory and fake decomposition client.
- The frontend is split into `frontend/src/app`, `pages`, `components`,
  `forms`, `artifacts`, and `utils`, backed by `frontend/src/api/client.ts`.
  Execution result JSON is rendered in detail views and normalized into
  comparison-page section tables.

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
  compare so detail and comparison views can render profile-specific tables.
- Rebuild result records from JSON for tests, evaluation work, and comparison
  metrics, casting fact-universe arrays back to numpy arrays.
- Tests must not download embedding models or call Mistral; the app needs an
  overridable embedder dependency and should use the existing fake decomposition
  flow.
- Execution loading first uses the latest persisted `StructuredArticle` for each
  corpus article. It calls Mistral only for articles without persisted
  structured payloads, so corpora built from JSON decomposition uploads skip
  decomposition during rank/select/compare runs.
- Execution loading normalizes structured payload `article_id` to the DB
  `Article.id` before passing records to `NewsRanker`.
- Execution endpoints can run synchronously under `asyncio.to_thread` while
  still exposing the pending/running/succeeded/failed lifecycle through
  persisted status fields.

# Decomposition and Embedding Context

## Scope

This context covers current structured-article schema, fixture loading, prompt/decomposition flow, fact embedding helpers, and how those pieces feed clustering/ranking orchestration. It deliberately does not cover scoring formulas, selection/evaluation helpers, cluster implementation details beyond call boundaries, provider-specific LLM SDK integration, scraping, URL deduplication, external fact-checking, or fixture migration.

## Key files

### Source

- `news_ranker/schemas.py` — strict Pydantic schema for fixture-compatible structured articles; path-based article-ID derivation; ordered fact extraction.
- `news_ranker/prompts.py` — current-schema decomposition prompt constants and raw-article user-prompt builder.
- `news_ranker/decompose.py` — provider-agnostic `decompose()` flow with injected client, parse/validation retry, and disk cache.
- `news_ranker/embed.py` — local `SentenceTransformerEmbedder`, injected `FactEmbedder` protocol, fact embedding validation, article-vector averaging from covered cluster vectors.
- `news_ranker/pipeline.py` — `NewsRanker` input normalization and orchestration from structured/raw inputs through embedding, clustering, scoring, ranking, and selection.
- `news_ranker/cluster.py` — consumes `StructuredArticle.fact_items` and fact embeddings; returns `FactUniverse` with article IDs, cluster vectors, and coverage matrix.
- `news_ranker/config.py` — config knobs relevant here: embedding/LLM model names, prompt/schema versions, cache dir, similarity/linkage settings.
- `news_ranker/__init__.py` — public exports for `NewsRanker`, `RankerConfig`, `decompose`, and decomposition protocol/config/error.

### Tests

- `tests/test_schemas.py` — fixture schema validation, article-ID loading, strict unknown-field rejection, fact order/IDs, nullable prompt-compatible fields.
- `tests/test_prompts.py` — prompt asserts current `name`/`role` schema, JSON-only/extra-key constraints, no `canonical_name`, user-prompt metadata handling.
- `tests/test_decompose.py` — fake-client decomposition success, input validation, retry behavior, cache hits, cache key versioning, no network/provider calls.
- `tests/test_embed.py` — deterministic fake embedders, embedding shape/dtype/finite validation, cluster-vector mean behavior, shape/no-coverage errors.
- `tests/test_pipeline.py` — structured/path/raw input normalization, injected decomposer hook, fake embedder ordering, empty-fact handling, MMR use of article embeddings.
- `tests/test_cluster.py` — confirms `flatten_fact_items()` order and `build_fact_universe()` contract used by embedding/pipeline.
- `tests/test_health.py` — public import surface includes decomposition exports but not result/evaluate helpers.

### Data/docs

- `articles/trump-shooting/*.json` — current fixture schema source of truth; five already-decomposed articles, all omit `article_id`.
- `docs/brief.md` — original design doc; its entity schema is illustrative and differs from current fixture schema.
- `docs/plans/structured-json-embedding-foundation.md` — original foundation plan for schemas + embeddings, before decomposition support existed.
- `docs/plans/structured-json-decomposition.md` — plan that added current-schema prompt, provider-agnostic decomposition, retry/cache, and raw-dict pipeline hook.

## Data flow / control flow

1. Fixture loading starts with `load_structured_article(path, article_id=None)` in `news_ranker/schemas.py`. It parses JSON into `StructuredArticle` with strict Pydantic validation, then sets runtime `article_id` from explicit override, JSON `article_id`, or `derive_article_id(path)`. For `articles/trump-shooting/bbc.json`, derived ID is `trump-shooting/bbc`.
2. `StructuredArticle` stores top-level `headline_neutral`, `topic`, `entities`, `events`, `claims`, and `context`. Entities are grouped as `people`, `organizations`, and `locations`, with each entity shaped as `name` plus nullable `role`. Events and claims expose `fact_text`; article-level `fact_texts` and `fact_items` return events first, then claims, preserving IDs for diagnostics.
3. Raw article decomposition uses `decompose(article, client, config=None, cache_dir=None)`. It requires non-empty string ID, title/headline, and body/content fields before any client call. It builds user prompt from raw fields plus remaining metadata and passes that plus `DECOMPOSITION_SYSTEM_PROMPT` into injected `DecompositionClient.complete(...)`.
4. `decompose()` parses returned text with `json.loads()`, validates with `StructuredArticle.model_validate()`, then overwrites runtime `article_id` from raw article ID. On JSON parse or schema validation failure, it retries once with error context appended to user prompt. After two failed attempts, it raises `DecompositionError`.
5. Decomposition cache is optional. When `cache_dir` is set, cache path is `cache_dir/decompositions/<sha256>.json`; hash includes normalized raw article payload, model, prompt version, and schema version. Cache hit bypasses client, validates cached JSON, and still applies runtime article ID from raw input.
6. Fact embedding uses `embed_facts(facts, embedder)`. Empty fact input raises before calling embedder. Embedder output must be 2-D, `np.float32`, finite. Tests inject fake embedders; real `SentenceTransformerEmbedder` imports and constructs `SentenceTransformer` only inside its constructor.
7. Pipeline ranking via `NewsRanker.rank()` loads structured inputs with `_load_structured_articles()`. Supported inputs are directory path, file path, sequence of paths, sequence of `StructuredArticle`, or sequence of raw dicts only when `NewsRanker(..., decomposer=...)` is provided. Raw dicts without decomposer still raise `NotImplementedError`.
8. Pipeline flattens facts using `flatten_fact_items(loaded_articles)`, embeds fact texts if any exist, builds `FactUniverse`, then builds article vectors with `embed_article_from_clusters(article_id, article_ids, coverage_matrix, cluster_vectors)`. Article vectors average unique covered cluster vectors; any nonzero coverage entry counts once, so repeated coverage values do not overweight facts.
9. Empty fact corpora skip embedder calls and flow through empty `float32` arrays. If any article covers no clusters, pipeline marks centrality undefined instead of calling `embed_article_from_clusters()` for that article.

## Conventions observed

- Fixture JSON, not `docs/brief.md`, is current schema authority. Brief-style `canonical_name` entities are intentionally rejected.
- Pydantic models use `ConfigDict(extra="forbid", strict=True)`; unknown top-level and nested fields fail fast.
- Nullable scalar fields exist for prompt compatibility: `Entity.role`, `Event.when`, and `Claim.attributed_to`; event fact text omits `None` optional fields.
- `Claim.type` is restricted to `"fact"`, `"quote"`, `"estimate"`, or `"prediction"`.
- Fact order convention is stable: article/input order, then events before claims within each article.
- Runtime article IDs must be present and unique before clustering; fixture files omit IDs, loader derives them.
- Provider dependencies are injected. No Anthropic/OpenAI SDK is imported. Tests must not download models or instantiate real `SentenceTransformer`.
- Embedding arrays are `np.float32`; shape/dtype/finite checks raise explicit `ValueError` or `TypeError` messages that tests match.
- Prompt forbids prose, markdown, code fences, comments, and extra keys; user prompt explicitly says not to fetch URLs or use external sources.
- Cache invalidation depends on raw article payload plus model/prompt/schema version strings; prompt/schema constants live outside `RankerConfig` defaults.
- Public package exports currently include decomposition entries. Result/evaluation dataclasses/helpers remain submodule-only.

## Open questions

1. None.

## Suggested next step

Plan session should focus on aligning any future provider-specific decomposer adapter and cache/config wiring with current strict fixture schema and injected-dependency tests.

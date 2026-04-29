# Pipeline Public API Context

## Current source of truth

Public pipeline API is fixture-backed only. It ranks already-structured article JSON from `articles/trump-shooting/` or caller-provided `StructuredArticle` objects. It does not decompose raw articles and does not scrape, deduplicate URLs, fact-check externally, or call hosted providers.

`news_ranker.__init__` exports:

- `NewsRanker`
- `RankerConfig`
- `health`

## Accepted inputs

`NewsRanker.rank()`, `NewsRanker.select()`, and `NewsRanker.compare_profiles()` accept:

- `str` or `Path` directory containing structured `*.json` files; directory entries sort by path for deterministic order
- `str` or `Path` single structured JSON file
- sequence of paths; caller order is preserved
- sequence of already-loaded `StructuredArticle` objects; caller order is preserved

Empty inputs fail. Missing paths fail. Raw article dictionaries fail with `NotImplementedError` because decomposition is not implemented yet. This boundary is isolated in `_load_structured_articles()` and `_load_from_path()` so future `decompose.py` work can adapt raw `{id, title, body}` inputs without rewriting scoring orchestration.

Fixture IDs still come from `load_structured_article()`: files like `articles/trump-shooting/bbc.json` derive `trump-shooting/bbc` unless JSON supplies `article_id`.

## Configuration defaults

`RankerConfig` owns pipeline scoring defaults:

- `similarity_threshold=0.85`
- `linkage="average"` (`"single"` also valid)
- `coverage_weighting="consensus"` (`"rarity"` also valid)
- default profiles: `representative`, `comprehensive`, `concise`

Profile weights must define exactly these component keys:

- `centrality`
- `coverage`
- `density`
- `entity_coverage`

Weights must be finite, nonnegative, and sum to `1.0` within tolerance. Undefined weighted components are handled by `combine()` via remaining-weight renormalization.

`NewsRanker` requires explicit `FactEmbedder` injection. There is no default `SentenceTransformerEmbedder`, so tests and callers avoid surprise model downloads.

## Ranking orchestration

`NewsRanker.rank(articles, profile="representative")` composes existing modules:

1. load or pass through `StructuredArticle` inputs
2. flatten facts with `flatten_fact_items()`
3. embed fact texts via injected `FactEmbedder` and `embed_facts()`
4. build `FactUniverse` with `build_fact_universe()`
5. build article embeddings from unique covered clusters with `embed_article_from_clusters()`
6. compute `centrality`, `coverage`, `density`, and `entity_coverage`
7. combine normalized components using selected profile weights
8. sort by descending score with stable input-order tie-break

If no fact texts exist, embedder is not called. Empty fact universes use empty `float32` arrays, and undefined components stay explicit. If any article covers no clusters, centrality is marked undefined rather than fabricating fallback embeddings.

## Result dataclasses

`news_ranker/pipeline.py` defines public result records:

- `RankingEntry(article_id, rank, score, components)`
- `RankDiagnostics(fact_universe, components, article_embeddings)`
- `RankResult(profile, entries, diagnostics)`
- `SelectionResult(profile, m, selected, ranking)`
- `ProfileComparison(rankings)`

`RankingEntry.components` contains normalized component values keyed by `centrality`, `coverage`, `density`, and `entity_coverage`.

`RankDiagnostics` exposes intermediate artifacts for inspection and tests: `FactUniverse`, component `ScoreVector`s, and article embedding matrix.

## Selection and profile comparison

`NewsRanker.select(articles, m, profile="representative")` validates integer `m` with `1 <= m <= article_count`, calls `rank()`, and selects entries according to `RankerConfig.selection_mode`. `selection_mode="top_score"` returns first *M* ranked entries. `selection_mode="mmr"` applies maximal marginal relevance using `selection_lambda` and normalized article embeddings from ranking diagnostics; selected order follows MMR selection order.

`NewsRanker.compare_profiles(articles, profiles=None)` returns one `RankResult` per requested profile. `profiles=None` means all configured profiles in config order. Current implementation recomputes ranking per profile; correctness is preferred over optimization for this stage.

## Testing constraints

Pipeline tests use deterministic fake embedders. Tests must not instantiate real `SentenceTransformer` models or download model weights. Fake embedder expectations depend on `flatten_fact_items()` order: events before claims, preserving article/input order.

## Future hooks

Future `decompose.py` can plug into the private input-normalization boundary to support raw article dictionaries after prompt/provider choices are planned.

`news_ranker/select.py` owns pure selection helpers behind `NewsRanker.select()`.

Do not change fixture schema, entity schema, provider choices, or public API shape without a later plan approving that scope.

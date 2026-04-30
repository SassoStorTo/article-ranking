# Ranking Pipeline Public API Context

## Scope

This context covers the current public ranking pipeline API centered on `NewsRanker`, `RankerConfig`, result records, accepted article inputs, ranking/selection/profile comparison behavior, and tests/docs that lock those boundaries. It deliberately does not cover changing scoring formulas, clustering quality, provider-specific LLM or embedding integrations, evaluation-helper implementation details beyond their consumption of pipeline results, scraping, URL deduplication, external fact-checking, fixture schema migration, or code changes.

## Key files

### Public API and configuration

- `news_ranker/__init__.py` — top-level exports: `NewsRanker`, `RankerConfig`, decomposition protocol/config/error, `decompose`, and `health`; result/evaluate helpers are not root exports.
- `news_ranker/pipeline.py` — `NewsRanker` orchestrator, input normalization, ranking, top-score/MMR selection, and profile comparison.
- `news_ranker/config.py` — frozen `RankerConfig`, default profiles, clustering/scoring/selection knobs, metadata fields, and validation.
- `news_ranker/results.py` — frozen result dataclasses consumed by pipeline and evaluation helpers.

### Pipeline dependencies

- `news_ranker/schemas.py` — strict `StructuredArticle` fixture schema, path-derived article IDs, event/claim fact text order, and JSON loader.
- `news_ranker/decompose.py` — provider-agnostic raw article decomposition function used only when caller injects a decomposer into `NewsRanker`.
- `news_ranker/embed.py` — injected `FactEmbedder` protocol, optional `SentenceTransformerEmbedder`, fact embedding validation, and article-vector construction from covered clusters.
- `news_ranker/cluster.py` — flattened facts, `FactUniverse`, agglomerative fact clustering, canonical medoid texts, and coverage matrix.
- `news_ranker/score.py` — `ScoreVector`, centrality, coverage, density, entity coverage, and weighted component combination.
- `news_ranker/select.py` — pure `select_top_score()` and `select_mmr()` helpers called by `NewsRanker.select()`.
- `news_ranker/evaluate.py` — downstream helpers consuming `RankResult`, `SelectionResult`, and `ProfileComparison`; imported from submodule only.

### Tests and docs

- `tests/test_pipeline.py` — primary API integration tests for constructor, loading, raw decomposer hook, ranking, diagnostics, selection, MMR, profile comparison, and legacy result imports.
- `tests/test_config.py` — config defaults and validation used by pipeline.
- `tests/test_health.py` — root export boundary and submodule-only result/evaluate imports.
- `tests/test_select.py` — pure top-score/MMR behavior and validation used by pipeline.
- `tests/test_score.py`, `tests/test_cluster.py`, `tests/test_embed.py`, `tests/test_schemas.py`, `tests/test_decompose.py`, `tests/test_evaluate.py` — upstream/downstream contracts that pipeline composes.
- `README.md` — documents config knobs, MMR/top-score selection, and evaluation-helper import style.
- `docs/brief.md` — original design source for public API, config knobs, ranking formulas, and MMR selection.
- `articles/trump-shooting/*.json` — five structured fixtures used by public pipeline tests; files omit `article_id`, so loader derives IDs.

## Data flow / control flow

1. Caller constructs `NewsRanker(embedder, config=None, *, decomposer=None)`. `embedder` is required; omitting it raises `TypeError("NewsRanker requires an explicit FactEmbedder; no default embedder is used")`. Config defaults to `RankerConfig()` if omitted. No model is downloaded unless caller explicitly constructs `SentenceTransformerEmbedder` elsewhere.
2. `NewsRanker.rank(articles, profile="representative")` first checks `profile in self._config.profiles`; unknown profile raises `ValueError("unknown ranking profile: ...")` before loading facts.
3. `_load_structured_articles()` accepts a directory path, single JSON path, sequence of paths, sequence of `StructuredArticle`, or mixed sequences containing raw dictionaries when `decomposer` is injected. Directory inputs sort `*.json`; explicit sequences preserve caller order. Empty sequences and empty directories fail. Missing paths raise `FileNotFoundError`. Raw dictionaries without decomposer raise `NotImplementedError("raw article dictionaries require decomposition, which is not implemented yet")`; raw dictionaries with decomposer are converted to `StructuredArticle` and decomposer exceptions propagate.
4. Fixture loading uses `load_structured_article()`, which validates current strict schema and sets runtime `article_id` from explicit override, JSON `article_id`, or path-derived ID such as `trump-shooting/bbc`.
5. Ranking flattens facts with `flatten_fact_items(loaded_articles)`. Fact order is article/input order, then events before claims within each article. `FactEmbedder.embed()` receives exactly those fact texts if any exist. Empty fact corpora skip the embedder and use `np.empty((0, 0), dtype=np.float32)`.
6. `build_fact_universe()` receives loaded articles and fact embeddings plus `similarity_threshold=config.similarity_threshold` and `linkage=config.linkage`. It returns `FactUniverse` with article IDs, raw/canonical fact metadata, cluster vectors, cluster assignments/members, and article-by-cluster coverage.
7. Pipeline builds article embeddings in `fact_universe.article_ids` order. For covered articles, `embed_article_from_clusters()` averages unique covered cluster vectors. If fact universe is empty, embeddings are zero-width/zero vectors. If only some articles cover no clusters, those rows remain zero.
8. `_score_components()` computes four component keys: `centrality`, `coverage`, `density`, and `entity_coverage`. Centrality is marked undefined if fact universe is empty or any article covers zero clusters. Coverage uses `config.coverage_weighting`. Density uses unique covered clusters per extracted event/claim count. Entity coverage uses exact normalized current-schema entity names by group.
9. `combine(components, config.profiles[profile])` combines normalized component vectors. Undefined weighted components are skipped and remaining effective weight is renormalized by default.
10. `_rank_entries()` sorts final scores descending with stable input-index tie-break, assigns ranks starting at `1`, and copies normalized component floats into each `RankingEntry.components` mapping. Raw component vectors and the fact universe remain in `RankDiagnostics`.
11. `rank()` returns `RankResult(profile, entries, diagnostics)`, where diagnostics contain `fact_universe`, component `ScoreVector`s, and article embeddings.
12. `NewsRanker.select(articles, m=None, profile="representative")` resolves `final_m = config.top_m if m is None else m`, calls `rank()`, validates integer non-bool `m`, then enforces `1 <= m <= article_count`. Omitted `m` with `top_m=None` raises `TypeError("m must be an integer")` after ranking.
13. With `selection_mode="top_score"`, selection delegates to `select_top_score(ranking.entries, final_m)` and returns first ranked entries. With `selection_mode="mmr"`, pipeline builds scores in `fact_universe.article_ids` order, L2-normalizes diagnostic article embeddings with zero guard, calls `select_mmr(..., lambda_=config.selection_lambda)`, and maps selected indices back to existing `RankingEntry` objects. MMR selected order follows the algorithm; first selected entry is highest-scored because initial diversity penalty is zero.
14. `NewsRanker.compare_profiles(articles, profiles=None)` ranks once per requested profile and returns `ProfileComparison(rankings={profile: RankResult})`. `profiles=None` uses config mapping order. A string profile is treated as a single-profile request. Empty profile sequences fail. Current implementation recomputes loading/embedding/clustering/scoring per profile.
15. Result records live in `news_ranker.results`; `news_ranker.pipeline` imports them at module top level for legacy compatibility. Package root intentionally does not export result records.

## Conventions observed

- Public root export surface is small and tested: decomposition API, `NewsRanker`, `RankerConfig`, and `health`; no result dataclasses, score helpers, select helpers, or evaluate helpers at package root.
- `RankerConfig` is a frozen dataclass. Validation happens in `__post_init__()` and uses `TypeError` for wrong type/non-integer config values and `ValueError` for domain/range/finite failures.
- Default profiles are `representative`, `comprehensive`, and `concise`. Profile weights must define exactly `centrality`, `coverage`, `density`, and `entity_coverage`, be finite/nonnegative, and sum to `1.0` within tolerance.
- Fixture JSON/current prompt schema uses `Entity(name, role)` grouped as `people`, `organizations`, and `locations`; brief-style `canonical_name` schema is rejected.
- Determinism comes from sorted directory JSON paths, preserved explicit sequence order, deterministic fact flattening, deterministic cluster label remapping by first occurrence, stable rank tie-break by input index, and `np.argmax` lowest-index tie-breaks in MMR.
- Tests use fake embedders and fake decomposers. Public pipeline tests must not instantiate real `SentenceTransformer`, require network access, scrape URLs, or call hosted providers.
- `FactEmbedder.embed()` output must be 2-D finite `np.float32`; pipeline avoids calling `embed_facts()` on empty fact lists because `embed_facts([])` raises by design.
- Empty fact corpora are valid through ranking: embedder skipped, fact universe empty, centrality/coverage/density undefined zeros, finite final scores, and stable input-order ranking.
- Mixed empty/non-empty corpora mark centrality undefined rather than fabricating fallback article embeddings.
- Positive coverage values are treated as binary throughout article-vector construction, coverage, density, and cluster inspection.
- `SelectionResult.selected` contains `RankingEntry` objects, not IDs. For MMR, selected order may differ from rank order after the first pick.
- Evaluation helpers are downstream, pure, submodule-only consumers of pipeline result dataclasses; they do not mutate pipeline behavior.
- Docs/plans can be stale relative to current implementation: older plans mention no raw-dict support or MMR fallback, but current code/tests support injected raw decomposer and implemented MMR.

## Open questions

1. Should `NewsRanker.compare_profiles()` reuse one loaded/embedded/scored intermediate run across profiles instead of recomputing per profile?
2. Should `RankerConfig` metadata fields (`llm_model_name`, `prompt_version`, `schema_version`, `cache_dir`) be wired into injected decomposition/cache flow, or remain metadata-only for pipeline?
3. Should `embedding_model_name` ever construct/configure `SentenceTransformerEmbedder`, or should explicit embedder injection remain the only pipeline model boundary?
4. Should raw dictionary support remain an injected `decomposer` callable on `NewsRanker`, or be bridged directly to `decompose(article, client, config, cache_dir)` in a future public constructor/API?
5. Should centrality keep current undefined policy when any article covers no clusters, or should a future fallback article embedding path be implemented?
6. Should result dataclasses remain submodule-only at package root even though they are public return types?
7. `README.md` evaluation example references profile `"coverage"`, but default profiles are `"representative"`, `"comprehensive"`, and `"concise"`; should docs use an existing profile or define a custom one?

## Suggested next step

Plan session should focus on choosing whether next public-API work targets performance reuse across profiles, operational wiring for decomposition/config/cache, or cleanup of stale docs/import examples while preserving current tested result shapes and dependency-injection boundaries.

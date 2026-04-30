# Config Knobs Context

## Scope

This context covers `RankerConfig` and every current consumer of its knobs: clustering threshold/linkage, coverage weighting, scoring profiles, default top-*M* selection, MMR selection parameters, and metadata fields for model/version/cache naming. It also covers tests and docs that lock this behavior. It deliberately does not cover changing scoring formulas, clustering quality, provider-specific LLM/embedder adapters, scraping, URL deduplication, external fact-checking, fixture schema migration, or adding new public exports.

## Key files

### Config and public API

- `news_ranker/config.py` — frozen `RankerConfig`, default profiles, derived `distance_threshold`, validation helpers, and `SelectionMode` alias.
- `news_ranker/__init__.py` — top-level public exports include `RankerConfig`, `NewsRanker`, decomposition protocol/config/error, `decompose`, and `health`.
- `README.md` — documents config knobs and states model/cache fields are metadata for fixture-backed ranking.

### Pipeline consumers

- `news_ranker/pipeline.py` — consumes config for profile lookup, clustering args, coverage mode, component weights, configured `top_m`, and top-score/MMR selection.
- `news_ranker/cluster.py` — defines `Linkage` and consumes `similarity_threshold`/`linkage` through `build_fact_universe()`.
- `news_ranker/score.py` — defines `CoverageMode`; consumes `coverage_weighting` and profile weights through `coverage()` and `combine()`.
- `news_ranker/select.py` — implements `select_top_score()` and `select_mmr()` behind `selection_mode` and `selection_lambda`.
- `news_ranker/embed.py` — defines `FactEmbedder` and `SentenceTransformerEmbedder`; `RankerConfig.embedding_model_name` is not used here automatically.
- `news_ranker/decompose.py` — has separate `DecompositionConfig(model, prompt_version, schema_version)` and `cache_dir` arg; not wired to `RankerConfig`.
- `news_ranker/results.py` — result dataclasses carrying ranking, selection, and diagnostics shaped by configured behavior.

### Tests and artifacts

- `tests/test_config.py` — focused defaults and validation coverage for `RankerConfig`.
- `tests/test_pipeline.py` — verifies config integration: profile names, clustering/scoring use, `top_m`, explicit `m` precedence, MMR behavior, and profile comparison order.
- `tests/test_select.py` — verifies top-score/MMR helper behavior and validation used by pipeline.
- `tests/test_score.py` — verifies coverage modes, component normalization, combine weight handling, and undefined-component renormalization.
- `tests/test_cluster.py` — verifies clustering threshold/linkage semantics consumed from config.
- `tests/test_decompose.py` — verifies decomposition cache/model/prompt/schema behavior separate from `RankerConfig`.
- `tests/test_health.py` — locks public import surface; result/evaluate helpers remain submodule-only.
- `docs/brief.md` — source design for config knobs in §4.8, selection in §4.9, formulas, and defaults.
- `docs/plans/config-knobs.md` — original config implementation plan; stale on MMR fallback because MMR is now implemented.
- `docs/plans/best-m-selection.md` — later plan that implemented MMR and updated config context/docs.
- `docs/context/pipeline-public-api.md` — companion context for full `NewsRanker` behavior.
- `docs/context/decomposition-embedding.md` — companion context for separate decomposition/embedder config and cache behavior.
- `docs/context/fact-clustering.md` and `docs/context/scoring.md` — companion contexts for config knobs consumed by clustering/scoring.

## Data flow / control flow

1. Caller creates `RankerConfig(...)`. Because dataclass is frozen, config values are validated once in `__post_init__()` and then treated as immutable by pipeline.
2. `RankerConfig` defaults are: `similarity_threshold=0.85`, `linkage="average"`, `coverage_weighting="consensus"`, profiles `representative`/`comprehensive`/`concise`, `top_m=None`, `selection_mode="top_score"`, `selection_lambda=0.8`, `embedding_model_name="all-MiniLM-L6-v2"`, `llm_model_name="claude-3-haiku"`, `prompt_version="v1"`, `schema_version="v1"`, and `cache_dir=None`.
3. `distance_threshold` is derived read-only as `1.0 - similarity_threshold`; callers do not configure distance independently. `build_fact_universe()` independently uses `np.nextafter(1.0 - similarity_threshold, np.inf)` for sklearn cutoff behavior.
4. `NewsRanker(embedder, config=...)` stores supplied config or builds a default one. It still requires explicit `FactEmbedder`; config never constructs `SentenceTransformerEmbedder` and never downloads models.
5. `NewsRanker.rank(articles, profile)` first validates `profile in config.profiles`. It then loads/decomposes structured inputs, flattens facts, embeds facts, and calls `build_fact_universe(..., similarity_threshold=config.similarity_threshold, linkage=config.linkage)`.
6. Ranking computes components with `coverage(..., mode=config.coverage_weighting)` plus centrality/density/entity coverage. It combines normalized components via `combine(components, config.profiles[profile])`, then sorts by descending score with input-index tie-break.
7. `NewsRanker.select(articles, m=None, profile="representative")` resolves `final_m = config.top_m if m is None else m`, calls `rank()`, then validates final `m` after ranking so actual `article_count` is known. Omitted `m` with `top_m=None` raises `TypeError("m must be an integer")`; out-of-range `m` raises `ValueError("m must satisfy 1 <= m <= article_count (...)")`.
8. With `selection_mode="top_score"`, pipeline delegates to `select_top_score(ranking.entries, final_m)` and returns first ranked entries. With `selection_mode="mmr"`, pipeline builds scores in `fact_universe.article_ids` order, normalizes `ranking.diagnostics.article_embeddings`, calls `select_mmr(..., lambda_=config.selection_lambda)`, then maps selected indices back to `RankingEntry` objects. MMR selected order follows MMR, not necessarily rank order after first pick.
9. `compare_profiles(articles, profiles=None)` uses config profile mapping insertion order when `profiles` is omitted, or caller-provided profile order otherwise. It calls `rank()` once per requested profile; it does not reuse embeddings across profiles.
10. Decomposition config is separate: `decompose(article, client, config=DecompositionConfig(...), cache_dir=...)` uses its own model/prompt/schema/cache values. `RankerConfig.llm_model_name`, `prompt_version`, `schema_version`, and `cache_dir` are metadata only in current `NewsRanker` flow.

## Conventions observed

- Config object is a frozen dataclass, not a provider factory or cache initializer.
- Validation style: `TypeError` for wrong type/non-integer numeric inputs, `ValueError` for finite/range/domain failures; tests match key message substrings.
- Bool is explicitly rejected for `similarity_threshold`, `top_m`, and `selection_lambda`; tests cover these cases.
- `linkage` literals are exactly `"average"` and `"single"`; `coverage_weighting` literals are exactly `"consensus"` and `"rarity"`; `selection_mode` literals are exactly `"top_score"` and `"mmr"`.
- Profiles must be non-empty mapping keyed by non-empty profile names. Each profile must define exactly `centrality`, `coverage`, `density`, and `entity_coverage`; weights must be finite, nonnegative, and sum to `1.0` within `1e-6`.
- Undefined weighted components are handled in `combine()` by skipping them and renormalizing remaining effective weight by default.
- `cache_dir` accepts `str`, `os.PathLike`, or `None`; config validation does not create directories. Decomposition cache directory creation happens only inside `decompose()` when its own `cache_dir` arg is used.
- Tests use fake embedders and synthetic arrays. No test path should instantiate real `SentenceTransformer` or require provider/network access.
- Public root exports are intentionally limited; `RankerConfig` is exported, but result dataclasses and evaluate helpers are not.
- Docs/plans can be stale: `docs/plans/config-knobs.md` still describes an old MMR warning fallback, while code/tests/README/current contexts reflect implemented MMR.

## Open questions

1. Should `RankerConfig` metadata (`llm_model_name`, `prompt_version`, `schema_version`, `cache_dir`) be bridged to `DecompositionConfig`/`decompose()` in a future raw-dict pipeline path, or remain separate?
2. Should `embedding_model_name` ever construct or configure `SentenceTransformerEmbedder`, or remain caller metadata while `NewsRanker` requires explicit embedder injection?
3. Should profile weight validation reject bool values and non-numeric objects with custom messages, matching stricter bool rejection used by scalar config fields?
4. `README.md` evaluation example references profile `"coverage"`, but default profiles are `"representative"`, `"comprehensive"`, and `"concise"`; should docs add that custom profile or use an existing one?
5. No corpus-specific calibration evidence for default `similarity_threshold=0.85` is documented beyond tests and design rationale.

## Suggested next step

Plan session should focus on deciding whether config metadata should become operational wiring for decomposition/embedder/cache, while preserving explicit dependency injection and current public API boundaries.

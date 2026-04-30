# Scoring Context

## Scope

This context covers current scoring behavior from clustered facts to ranked outputs: `ScoreVector` semantics, component formulas in `news_ranker.score`, how `NewsRanker.rank()` builds component inputs, how config profiles and selection/evaluation consume normalized scores, and tests that lock edge cases. It deliberately does not cover changing decomposition prompts, provider SDKs, embedding quality, clustering-threshold tuning beyond scoring inputs, scraping, URL deduplication, external fact-checking, fixture schema migration, UI/storage for evaluation, or implementation changes.

## Key files

### Scoring core

- `news_ranker/score.py` — defines `ScoreVector`, min-max normalization, centrality, coverage, density, entity coverage, and component combination.
- `news_ranker/schemas.py` — defines strict `StructuredArticle`, `Event`, `Claim`, and entity structures consumed by density and entity coverage.
- `news_ranker/cluster.py` — builds `FactUniverse.coverage_matrix`, `cluster_vectors`, and `article_ids`, which are scoring inputs.
- `news_ranker/embed.py` — builds article embeddings as means of unique covered cluster vectors for centrality and MMR.

### Pipeline/config/result consumers

- `news_ranker/pipeline.py` — orchestrates loading, embedding, clustering, scoring, weighted combination, ranking, profile comparison, and selection.
- `news_ranker/config.py` — defines coverage mode, default profiles, profile-weight validation, selection mode, and top-M defaults.
- `news_ranker/results.py` — stores ranked entries plus scoring diagnostics (`FactUniverse`, component `ScoreVector`s, article embeddings).
- `news_ranker/select.py` — consumes final scores and normalized article embeddings for top-score/MMR selection after ranking.
- `news_ranker/evaluate.py` — consumes `RankingEntry.components` and diagnostics for component tables and cluster inspection.
- `news_ranker/__init__.py` — exports `NewsRanker`, `RankerConfig`, decomposition API, and `health`; result/scoring/evaluate helpers remain submodule imports.

### Tests and docs

- `tests/test_score.py` — unit tests for all scoring functions, validation, undefined/tied normalization, and fixture smoke path.
- `tests/test_pipeline.py` — integration tests for score production, profile use, empty/mixed fact handling, stable ranking, selection, and comparison.
- `tests/test_config.py` — config defaults and validation for coverage weighting, profiles, top-M, and selection knobs.
- `tests/test_select.py` — top-score/MMR behavior over final scores and embeddings.
- `tests/test_evaluate.py` — component table and diagnostics export behavior from scored rankings.
- `tests/test_cluster.py`, `tests/test_embed.py`, `tests/test_schemas.py` — upstream contracts for fact order, coverage matrix, article vectors, and schema fields used by scoring.
- `articles/trump-shooting/*.json` — five structured fixtures used by scoring, pipeline, clustering, and schema tests.
- `docs/brief.md` — original scoring formulas and defaults; current code follows most formulas but uses current `{name, role}` entity schema.
- `docs/context/fact-clustering.md`, `docs/context/decomposition-embedding.md`, `docs/context/config-knobs.md`, `docs/context/ranking-pipeline-public-api.md` — companion contexts for upstream/downstream behavior.

## Data flow / control flow

1. Structured inputs enter `NewsRanker.rank()` as paths, `StructuredArticle` objects, or raw dictionaries only when an injected decomposer is supplied. Loaded fixtures derive runtime article IDs like `trump-shooting/bbc` when JSON omits `article_id`.
2. `flatten_fact_items()` emits facts in article/input order, with events before claims per article. Pipeline embeds fact texts through injected `FactEmbedder` only when fact texts exist.
3. `build_fact_universe()` clusters fact embeddings and returns `coverage_matrix` shaped `(article_count, cluster_count)`. Coverage is binary per article/cluster even when repeated facts from one article map to same cluster.
4. Pipeline builds article embeddings in `FactUniverse.article_ids` order. For each article with covered clusters, `embed_article_from_clusters()` averages unique covered cluster vectors. Articles with no covered clusters remain zero in pipeline output.
5. Pipeline calls `_score_components()`. If fact universe is empty or any article covers zero clusters, centrality is not computed and is replaced with `ScoreVector(raw=zeros, normalized=zeros, defined=False)`. Otherwise `centrality(article_embeddings)` runs.
6. `centrality()` validates a 2-D numeric finite embedding array, converts to `float32`, L2-normalizes each row with `1e-12` epsilon guard, computes centroid, uses negative Euclidean distance to centroid as raw score, then min-max normalizes.
7. `coverage(coverage_matrix, mode)` validates 2-D numeric finite nonnegative coverage, converts positive entries to covered once, then computes weighted fact recall. `consensus` weights are document frequency divided by article count. `rarity` weights are `log((article_count + 1) / (df + 1)) + 1`. Empty article count or fact count returns undefined zeros.
8. `density(structured_articles, coverage_matrix)` validates coverage and row count, converts coverage to binary, computes unique covered clusters per article, divides by `len(events) + len(claims)` where entry count is positive, leaves zero for zero-entry articles, and marks component defined only when at least one article has entries.
9. `entity_coverage(structured_articles)` uses only `people`, `organizations`, and `locations`. It normalizes names with `casefold()` plus whitespace collapse, keeps group name in key to avoid person/location collisions, builds a binary entity matrix, applies consensus document-frequency weights, and returns undefined zeros for empty article lists or corpora with no entities. Entity roles and aliases are not used.
10. `minmax_normalize(values, defined=True)` validates 1-D numeric finite values and `float32` conversion. Undefined input or empty vectors return normalized zeros with `defined=False`. Defined tied values return normalized ones. Non-tied values scale to `[0, 1]`.
11. `combine(components, weights, renormalize_undefined=True)` validates non-empty mappings, rejects weight keys not present in components, validates component raw/normalized vectors have matching shapes and common length, validates finite nonnegative weights, and requires at least one positive total weight. It sums normalized component vectors only. With default renormalization, undefined weighted components are skipped and remaining effective weights form denominator; if all effective weight is skipped, zeros return.
12. `RankerConfig` defaults combine component scores through profiles: `representative` (`centrality=0.4`, `coverage=0.5`, `density=0.1`, `entity_coverage=0.0`), `comprehensive` (`0.2`, `0.7`, `0.1`, `0.0`), and `concise` (`0.2`, `0.4`, `0.4`, `0.0`). Each profile must define exactly `centrality`, `coverage`, `density`, and `entity_coverage`, with nonnegative finite weights summing to `1.0`.
13. Pipeline builds `RankingEntry` objects by sorting final scores descending with input-index tie-break. `RankingEntry.components` stores normalized component floats for every component key; raw component values remain in `RankDiagnostics.components`.
14. `NewsRanker.select()` calls `rank()` first. `selection_mode="top_score"` returns first ranked entries. `selection_mode="mmr"` builds scores in `fact_universe.article_ids` order, normalizes diagnostic article embeddings, calls `select_mmr()`, then maps selected indices back to existing ranking entries.
15. `NewsRanker.compare_profiles()` calls `rank()` once per requested profile. It recomputes embedding/clustering/scoring per profile rather than reusing a shared scoring run.
16. Evaluation helpers are read-only consumers: `component_score_table()` flattens normalized `RankingEntry.components`, and `cluster_inspection_rows()` uses scoring diagnostics' `FactUniverse` to expose support and rarity.

## Conventions observed

- Scoring arrays returned by score functions are `np.float32`; validation accepts integer/floating numeric inputs where appropriate and rejects nonnumeric, non-finite, wrong-dimensional, negative coverage, and values that overflow on `float32` conversion.
- Error style uses `TypeError` for nonnumeric/wrong type and `ValueError` for invalid shapes, ranges, finite checks, row-count mismatches, and unsupported modes; tests match message substrings like `"2-D"`, `"1-D"`, `"finite"`, `"float32"`, `"row count"`, `"nonnegative"`, and `"mode"`.
- Positive coverage values are treated as binary in coverage, density, article-vector construction, and cluster inspection; repeated coverage values do not inflate score components.
- Normalization distinguishes undefined from tied-defined: undefined and empty components normalize to zeros, while valid tied components normalize to ones.
- Component scores are corpus-relative. Final scores and normalized component values are meaningful within one event corpus, not calibrated across unrelated corpora.
- Pipeline marks centrality undefined for mixed empty/covered corpora instead of fabricating fallback article embeddings, even though standalone `centrality()` can score zero vectors with epsilon guard.
- Entity coverage uses exact normalized names by group. It does not merge aliases such as `Cole Allen` and `Cole Tomas Allen`, and it ignores `role` values.
- Ranking tie-break is stable by input order; MMR tie-break is lowest input index via `np.argmax` over article-ID order.
- Tests use fake embedders and synthetic arrays; no test should instantiate `SentenceTransformer` or call provider/network APIs.
- Fixture schema is current authority. The brief's `canonical_name`/alias entity shape is intentionally rejected by schema tests.
- Public root exports do not include score functions, result dataclasses, select helpers, or evaluate helpers; callers import those from submodules.

## Open questions

1. Should future scoring keep current centrality-undefined policy when any article covers no clusters, or implement a fallback embedding path mentioned in the brief?
2. Should `combine()` enforce normalized component values are within `[0, 1]`, or continue accepting any finite numeric normalized vector supplied by callers/tests?
3. Should entity coverage remain exact-name/group recall, or should future schema/prompt work support alias merging across variants like `Cole Allen` and `Cole Tomas Allen`?
4. Should profile weight validation reject bool/non-numeric values with explicit messages matching scalar config validation, or is current `float(weight)` behavior sufficient?
5. No documented corpus-specific calibration exists for default component weights or for how `coverage_weighting="rarity"` affects real rankings.

## Suggested next step

Plan session should focus on scoring edge-case policy and validation boundaries while preserving current component keys, result shapes, normalized-score consumers, and fixture-backed deterministic tests.

# Ranking Evaluation Helpers Context

## Scope

This context covers current downstream helper behavior in `news_ranker.evaluate`: profile overlap, rank correlation, component score rows, fact-cluster inspection rows, and anonymized user-study bundles built from `RankResult`, `SelectionResult`, and `ProfileComparison`. It also covers result-record ownership, pipeline paths that produce these inputs, tests/docs that lock public boundaries, and the renamed context slug; it deliberately does not cover LLM decomposition internals, embedding provider quality, scoring formula design beyond helper inputs, clustering quality beyond exported diagnostics, scraping, URL deduplication, external fact-checking, UI/persistence for studies, or code changes.

## Key files

### Evaluation helpers

- `news_ranker/evaluate.py` — defines all comparison/review helpers plus `TopMOverlap`, `RankCorrelation`, row type aliases, validation helpers, Kendall tau-a, and Spearman rho.
- `tests/test_evaluate.py` — locks helper schemas, deterministic ordering, edge cases, fixture-backed component rows, material validation, duplicate-ID validation, and error types/messages.
- `README.md` — documents import style from `news_ranker.evaluate` and example use with `NewsRanker.compare_profiles()`.

### Result records and producer flow

- `news_ranker/results.py` — owns frozen dataclasses `RankingEntry`, `RankDiagnostics`, `RankResult`, `SelectionResult`, and `ProfileComparison` consumed by evaluation helpers.
- `news_ranker/pipeline.py` — produces `RankResult`, `SelectionResult`, and `ProfileComparison`; keeps legacy result-record imports bound at module top level.
- `news_ranker/config.py` — defines default profiles `representative`, `comprehensive`, and `concise`, plus selection mode/top-M validation used before evaluation helpers consume results.
- `tests/test_pipeline.py` — verifies ranking order, stable score tie-breaks, selection behavior, profile comparison order, result-record compatibility imports, and default profile names.
- `tests/test_health.py` — verifies evaluate helpers import from `news_ranker.evaluate` only and are not top-level `news_ranker` exports.

### Data structures inspected by helpers

- `news_ranker/cluster.py` — defines `FactUniverse`, including `article_ids`, raw/canonical fact fields, `cluster_members`, and article-by-cluster `coverage_matrix` consumed by `cluster_inspection_rows()`.
- `news_ranker/score.py` — defines `ScoreVector`; normalized component floats are copied into `RankingEntry.components` by pipeline.
- `news_ranker/select.py` — implements selection primitives used by pipeline before `anonymized_user_study_bundle()` receives a `SelectionResult`.
- `news_ranker/embed.py` — builds article vectors from unique covered clusters; relevant because MMR-selected `SelectionResult` comes from these diagnostics.
- `news_ranker/schemas.py` — structured article facts and entities feed pipeline scoring/clustering before evaluation helpers receive result records.

### Related artifacts

- `docs/brief.md` — specifies `evaluate.py` purpose: top-*M* overlap, Kendall/Spearman correlation, component-score tables, cluster-inspection export, and anonymized user-study bundles.
- `docs/plans/evaluate-comparison-helpers.md` — original implementation plan; current better context slug is `ranking-evaluation-helpers.md` because helpers are broader than comparison.
- `docs/context/fact-clustering.md` — companion context for `FactUniverse` creation and cluster inspection semantics.

## Data flow / control flow

1. `NewsRanker.rank()` loads structured articles, flattens facts, embeds facts, builds a `FactUniverse`, builds article embeddings, scores components, combines profile weights, and returns `RankResult(profile, entries, diagnostics)`. Entries are sorted by descending score with stable input-index tie-break and ranks start at `1`.
2. `NewsRanker.select()` calls `rank()`, validates `m`, selects either first ranked entries (`top_score`) or MMR entries (`mmr`), and returns `SelectionResult(profile, m, selected, ranking)`. MMR keeps highest-scored article first because empty selected set has zero diversity penalty.
3. `NewsRanker.compare_profiles()` resolves requested profile names, then calls `rank()` once per profile and returns `ProfileComparison(rankings={profile: RankResult})`. Default profile order comes from config mapping insertion order.
4. `top_m_overlap(left, right, m)` validates duplicate article IDs in both rankings, validates `m` as non-bool integer in `1..min(len(left.entries), len(right.entries))`, slices top `m` entries by existing entry order, compares article-ID sets, and returns counts/fractions/Jaccard plus overlap IDs in left top-*M* order.
5. `rank_correlation(left, right, method)` validates method (`"kendall"` or `"spearman"`), duplicate article IDs, and at least two common IDs. It builds `article_id -> rank` maps, aligns common IDs in left entry order, reports left-only/right-only IDs in each ranking order, then computes Kendall tau-a over rank pair concordance or Spearman rho as Pearson correlation of rank values. No SciPy dependency.
6. `component_score_table(results)` coerces one `RankResult`, a `Sequence[RankResult]`, or a `ProfileComparison` into a tuple of rankings. It collects component names by ranking order, entry rank order, and first-seen component-key order. Rows preserve profile input order, sort each ranking by `entry.rank`, include `profile`, `article_id`, `rank`, `score`, and fill missing dynamic component columns with `None`.
7. `cluster_inspection_rows(rank_result, rare_threshold=1)` validates `rare_threshold` as non-bool integer at least `1`, reads `rank_result.diagnostics.fact_universe`, iterates `cluster_members` by cluster index, computes support article IDs from `coverage_matrix[:, cluster_index] > 0`, and returns row dicts with canonical text, support IDs/count, member raw indices/fact IDs/texts, and `is_rare = support_count <= rare_threshold`. Empty fact universes return `[]`.
8. `anonymized_user_study_bundle(selection, article_materials, include_scores=False)` first rejects unexpected material keys outside `title`, `snippet`, and `summary`. It assigns labels `article_1`, `article_2`, etc. from `selection.ranking.entries` order for selected article IDs only, validates every selected article has material, emits `profile`, `m`, `selected_article_labels` in `selection.selected` order, and maps labels to copied material dicts. With `include_scores=True`, it adds score rows for selected entries only, including label, rank, score, and copied components.

## Conventions observed

- Public result payloads are frozen dataclasses in `news_ranker.results`; pipeline keeps compatibility imports, but package root does not export result records or evaluate helpers.
- Evaluate helpers are pure downstream functions: no provider calls, no model downloads, no scraping, no file exporters, no mutation of ranking/selection behavior, and no new dependencies.
- Return payloads are built from dataclasses, tuples, dictionaries, strings, ints, floats, bools, and `None`, making later serialization straightforward but not delegated to pandas/CSV helpers.
- Ordering is deterministic: rankings use pipeline entry order, overlaps report left-order IDs, common IDs follow left ranking order, right-only IDs follow right ranking order, component columns follow first-seen component key order, cluster rows follow cluster index order, and user-study labels follow ranking order.
- Validation style matches other modules: `TypeError` for non-integer/bool numeric type errors such as `m` and `rare_threshold`; `ValueError` for invalid values such as out-of-range `m`, unknown method, duplicate article IDs, too few common IDs, missing materials, or unexpected material keys.
- Tests use synthetic `RankResult`/`FactUniverse` builders and a local fake embedder; no real embedding model or LLM is invoked in evaluate tests.
- Numerical tests use `pytest.approx()` and finite-value assertions; component-row fixture tests expect all four default component keys: `centrality`, `coverage`, `density`, and `entity_coverage`.
- Cluster support semantics are binary per article/cluster even if synthetic coverage values exceed `1`; support counts do not count repeated raw facts.
- User-study anonymization is source-ID replacement plus field filtering only; title/snippet/summary text can still identify a source, and no answer-key mapping is returned in the bundle.
- No logging is present in helper modules; failures are surfaced through explicit exceptions.

## Open questions

1. `rank_correlation()` validates duplicate article IDs but not duplicate rank numbers; Kendall implementation is tau-a without tie correction and assumes pipeline-style unique ranks.
2. `component_score_table()` type hints allow `Sequence[RankResult]`; runtime does not explicitly reject strings or non-`RankResult` sequences before attribute access.
3. `ProfileComparison.rankings` is typed as generic `Mapping`; helper row order uses `.values()`, so non-ordered mapping implementations could make profile order non-deterministic despite normal dict behavior in pipeline.
4. `cluster_inspection_rows()` relies on internally consistent `FactUniverse` shapes and indices; it does not validate `coverage_matrix`, `canonical_fact_texts`, and member index lengths before indexing.
5. `anonymized_user_study_bundle()` assumes `selection.selected` entries all appear in `selection.ranking.entries`; malformed external `SelectionResult` can produce a key lookup failure rather than a tailored validation error.
6. `README.md` example requests profile `"coverage"`, but default config profiles are `"representative"`, `"comprehensive"`, and `"concise"`; no default `"coverage"` profile exists in `RankerConfig`.

## Suggested next step

Plan session should focus on whether to harden evaluation-helper validation and README/profile naming while preserving current result shapes, import boundaries, deterministic ordering, and dependency-free pure-helper behavior.

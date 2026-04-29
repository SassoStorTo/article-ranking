# Evaluate Comparison Helpers Context

## Scope

Planned work adds pure evaluation helpers in `news_ranker/evaluate.py`. Helpers consume existing result dataclasses from `news_ranker/pipeline.py`; they do not call embedders, scrape content, deduplicate URLs, fact-check externally, or mutate ranking behavior.

No implementation exists yet. This artifact records source context for later steps and should be updated as helper record names, fields, and edge cases land.

## Relevant source files

- `news_ranker/pipeline.py`
  - Defines `RankingEntry(article_id, rank, score, components)`.
  - Defines `RankDiagnostics(fact_universe, components, article_embeddings)`.
  - Defines `RankResult(profile, entries, diagnostics)`.
  - Defines `SelectionResult(profile, m, selected, ranking)`.
  - Defines `ProfileComparison(rankings)`.
  - Ranking entries are sorted by descending score with stable input-order tie-break and ranks start at `1`.
- `news_ranker/cluster.py`
  - Defines `FactUniverse` with article IDs, raw fact article IDs/IDs/texts, canonical fact texts, cluster assignments, cluster members, cluster vectors, and coverage matrix.
  - `coverage_matrix` is article-by-cluster binary coverage in current builder behavior.
  - Cluster labels/members are remapped in first-occurrence order for deterministic inspection rows.
- `news_ranker/score.py`
  - Defines `ScoreVector(raw, normalized, defined)`.
  - Pipeline component values stored on `RankingEntry.components` are normalized floats.
- `news_ranker/select.py`
  - Selection helpers validate `m`, but planned top-M overlap validation belongs in `evaluate.py`.
- `news_ranker/__init__.py`
  - Public `__all__` is `['NewsRanker', 'RankerConfig', 'health']` and must remain unchanged until plan step 6.

## Planned helper behavior

### `top_m_overlap(left, right, m)`

Accepts two `RankResult` objects and integer `m`. Compares top-`m` article ID sets and returns overlap count, left/right top counts, Jaccard, left/right overlap fractions, and overlap article IDs. Later implementation should reject invalid `m` and duplicate article IDs.

### `rank_correlation(left, right, method='kendall' | 'spearman')`

Accepts two `RankResult` objects and compares ranks over common article IDs only. Planned result includes method, coefficient, common ID count, common article IDs, left-only article IDs, and right-only article IDs. Kendall should be tau-a without tie correction because pipeline ranks are unique. Spearman should be Pearson correlation over ranks. No SciPy dependency.

### `component_score_table(results)`

Planned rows flatten one `RankResult`, a sequence of `RankResult`, or a `ProfileComparison`. Rows should preserve profile input order, then rank order. Base columns: profile, article ID, rank, score. Component columns come from entry component keys, with missing profile/component values represented as `None`.

### `cluster_inspection_rows(rank_result, rare_threshold=1)`

Planned rows inspect `rank_result.diagnostics.fact_universe`. Rows should include cluster index, canonical fact text, support article IDs, support count, member raw indices, member fact IDs, member texts, and rare flag. Empty fact universes should return empty rows.

### `anonymized_user_study_bundle(selection, article_materials, *, include_scores=False)`

Accepts `SelectionResult` and sanitized article materials keyed by original article ID. Materials may contain only `title`, `snippet`, and/or `summary`; unexpected keys or missing selected materials should fail validation. Output should assign stable labels like `article_1` in ranking order and must not include original article IDs or answer-key mapping. Scores/components are omitted by default and included only when `include_scores=True`.

## Constraints

- No new dependencies such as SciPy or pandas.
- No top-level export change before plan step 6.
- No fixture schema migration.
- No file-writing exporters; helpers return serializable Python data.
- No provider calls or model downloads in tests.
- Keep validation explicit and deterministic, matching current modules.

## Deviations from plan

None so far. Helper implementation pending later steps.

## Verification

Step 1 verification command:

```sh
test -f docs/context/evaluate-comparison-helpers.md && uv run ruff format --check docs/context/evaluate-comparison-helpers.md
```

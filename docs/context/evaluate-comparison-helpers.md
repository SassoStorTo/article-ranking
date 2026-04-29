# Evaluate Comparison Helpers Context

## Scope

Planned work adds pure evaluation helpers in `news_ranker/evaluate.py`. Helpers consume existing result dataclasses from `news_ranker/pipeline.py`; they do not call embedders, scrape content, deduplicate URLs, fact-check externally, or mutate ranking behavior.

Step 2 implementation now exists for overlap and correlation. This artifact records source context for later steps and should be updated as helper record names, fields, and edge cases land.

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
  - Public `__all__` is `['NewsRanker', 'RankerConfig', 'health']` and remains unchanged in step 6.
- `README.md`
  - Documents evaluation helper usage via `from news_ranker.evaluate import ...` with `NewsRanker.compare_profiles()` output.

## Planned helper behavior

### `top_m_overlap(left, right, m)`

Accepts two `RankResult` objects and integer `m`. Compares top-`m` article ID sets and returns frozen `TopMOverlap(overlap_count, left_top_count, right_top_count, jaccard, left_overlap_fraction, right_overlap_fraction, overlap_article_ids)`. Overlap IDs follow left top-`m` rank order. Rejects non-integer/bool `m`, `m` outside `1 <= m <= min(left_count, right_count)`, and duplicate article IDs in either ranking.

### `rank_correlation(left, right, method='kendall' | 'spearman')`

Accepts two `RankResult` objects and compares ranks over common article IDs only. Returns frozen `RankCorrelation(method, coefficient, common_count, common_article_ids, left_only_article_ids, right_only_article_ids)`. Common IDs and left-only IDs follow left ranking order; right-only IDs follow right ranking order. Kendall is tau-a without tie correction because pipeline ranks are unique. Spearman is Pearson correlation over ranks. Rejects unknown methods, duplicate article IDs, and fewer than two common article IDs. No SciPy dependency.

### `component_score_table(results)`

Implemented rows flatten one `RankResult`, a sequence of `RankResult`, or a `ProfileComparison`. Returns `list[dict[str, str | int | float | None]]` with base columns `profile`, `article_id`, `rank`, and `score`, plus one dynamic column for each component key seen across entries. Rows preserve profile input order, then sort entries by `rank`. Component columns preserve first-seen component-key order. Missing component values are `None`.

### `cluster_inspection_rows(rank_result, rare_threshold=1)`

Implemented rows inspect `rank_result.diagnostics.fact_universe`. Returns `list[dict[str, str | int | bool | tuple[int, ...] | tuple[str, ...]]]` with `cluster_index`, `canonical_fact_text`, `support_article_ids`, `support_count`, `member_raw_indices`, `member_fact_ids`, `member_texts`, and `is_rare`. Support counts use binary article coverage (`coverage_matrix > 0`), not raw fact/member counts. Rows follow `FactUniverse.cluster_members` order. Empty fact universes return `[]`. Rejects non-integer/bool `rare_threshold` and values below `1`.

### `anonymized_user_study_bundle(selection, article_materials, *, include_scores=False)`

Implemented helper accepts `SelectionResult` and sanitized article materials keyed by original article ID. Materials may contain only `title`, `snippet`, and/or `summary`; unexpected keys or missing selected materials fail validation. Output is a plain dictionary with `profile`, `m`, `selected_article_labels`, and `article_materials`. Labels are assigned from `selection.ranking.entries` order and selected labels follow `selection.selected` order. Bundles omit original article IDs and answer-key mapping. Scores/components are omitted by default; when `include_scores=True`, bundle includes `scores` rows with anonymized `label`, `rank`, `score`, and `components`. Anonymization only replaces IDs and filters fields; caller-provided text can still identify sources.

## Constraints

- No new dependencies such as SciPy or pandas.
- No top-level export change; evaluate helpers stay importable from `news_ranker.evaluate` only.
- No fixture schema migration.
- No file-writing exporters; helpers return serializable Python data.
- No provider calls or model downloads in tests.
- Keep validation explicit and deterministic, matching current modules.

## Deviations from plan

Step 2 record names are `TopMOverlap` and `RankCorrelation`, matching planned fields. Step 3 uses dynamic row dictionaries for component columns. Step 4 uses dynamic row dictionaries for cluster inspection rows. Step 5 uses dynamic dictionary bundles for user-study materials.

Step 7 full verification initially failed on `news_ranker/evaluate.py` because mypy inferred `Any` from exponentiation in `_spearman_rho()`. The implementation now uses `math.sqrt()` for the denominator. Full verification also required ruff-formatting existing Markdown snippets in `README.md`, `docs/brief.md`, and `docs/.news_ranker_design_old.md`.

## Verification

Step 1 verification command:

```sh
test -f docs/context/evaluate-comparison-helpers.md && uv run ruff format --check docs/context/evaluate-comparison-helpers.md
```

Step 2 verification command:

```sh
uv run pytest tests/test_evaluate.py
```

Step 3 verification command:

```sh
uv run pytest tests/test_evaluate.py
```

Step 4 verification command:

```sh
uv run pytest tests/test_evaluate.py
```

Step 5 verification command:

```sh
uv run pytest tests/test_evaluate.py
```

Step 6 verification command:

```sh
uv run pytest tests/test_health.py tests/test_evaluate.py
```

Step 7 verification command:

```sh
make check
```

Result: passed. `mypy`, `ruff check`, `ruff format --check`, and full pytest suite passed with `166 passed`.

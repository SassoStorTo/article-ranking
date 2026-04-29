# Evaluate Comparison Helpers Plan

## Goal

Implement `news_ranker.evaluate` helpers for comparing scoring profiles and exporting review artifacts from existing `RankResult`, `ProfileComparison`, and `FactUniverse` data. Done means callers can compute top-*M* overlap, Kendall/Spearman rank correlation, component-score tables, cluster-inspection rows, and anonymized user-study bundles without provider calls, new dependencies, or changes to fixture-backed ranking behavior.

## Non-goals

- No scraping, URL deduplication, external fact-checking, or LLM decomposition.
- No new dependencies such as SciPy or pandas.
- No top-level `news_ranker.__all__` export change unless separately approved.
- No public shape changes to `NewsRanker.rank()`, `select()`, or `compare_profiles()`.
- No fixture schema migration.
- No file-writing exporters; helpers return serializable Python data.
- No user-study UI, persistence, random assignment service, or analytics backend.

## Approach

Add new pure module `news_ranker/evaluate.py`. Helpers consume existing pipeline result dataclasses, not raw article inputs, so evaluation stays downstream of ranking and remains deterministic. Return plain frozen dataclasses or tuples/dicts with built-in scalar types so results are easy to serialize later. Keep functions small and validation explicit, matching current modules.

Rank metrics should use article IDs as join keys. `top_m_overlap()` compares top-*M* ID sets and returns overlap count, left/right top counts, Jaccard, left/right overlap fractions, and overlap article IDs. `rank_correlation()` exposes one generic API with `method="kendall" | "spearman"`; return method, coefficient, common ID count, common IDs, and left/right-only ID diagnostics. Implement Kendall tau-a over common IDs with no tie correction because pipeline ranks are unique; implement Spearman rho as Pearson correlation over ranks. No SciPy dependency.

Component tables should flatten one or more `RankResult` objects into rows keyed by profile/article/rank/score/component values. Cluster inspection export should use `RankDiagnostics.fact_universe` and emit deterministic cluster rows: cluster index, canonical text, support count, support article IDs, member raw fact IDs/texts, and rare flag. User-study bundles should anonymize source identity by replacing article IDs with stable labels (`article_1`, etc.) assigned in ranking order. Bundle materials are strict: copy only `title`, `snippet`, and `summary`, reject extra material keys, and require material for each selected article. Returned bundle must not include original article IDs or `label_to_article_id`; caller keeps answer key separately from participant bundle. `include_scores=False` remains default, with rank/score/components included only for researcher-facing bundles. Tradeoff: no cryptographic anonymization; labels and field filtering support blind review but cannot hide identifying text inside title/snippet/summary.

## Steps

1. **Write implementation context artifact**
   - **Files touched**: `docs/context/evaluate-comparison-helpers.md`
   - **Change summary**: Create focused context artifact after implementation, documenting relevant source files, helper behavior, constraints, and verification state. Include any deviations from this plan, especially return record names/fields.
   - **Tests added or updated**: none; documentation-only step.
   - **Verification command**: `test -f docs/context/evaluate-comparison-helpers.md && uv run ruff format --check docs/context/evaluate-comparison-helpers.md`

2. **Add profile overlap and rank-correlation helpers**
   - **Files touched**: `news_ranker/evaluate.py`, `tests/test_evaluate.py`, `docs/context/evaluate-comparison-helpers.md`
   - **Change summary**: Create module with validation helpers plus `top_m_overlap(left, right, m)` and `rank_correlation(left, right, method="kendall" | "spearman")`. Functions accept `RankResult` objects, compare common `article_id`s, reject invalid `m`, unknown methods, duplicate article IDs, and fewer than two common IDs; overlap returns all denominators, while correlation returns coefficient plus ID diagnostics; update context with implemented names/edge cases.
   - **Tests added or updated**: `tests/test_evaluate.py` asserts exact top-*M* overlap counts/Jaccard/per-side fractions, overlap ID diagnostics, Kendall result for identical/reversed rankings, Spearman result for identical/reversed rankings, common-ID alignment, left/right-only diagnostics, and validation errors.
   - **Verification command**: `uv run pytest tests/test_evaluate.py`

3. **Add component-score table export**
   - **Files touched**: `news_ranker/evaluate.py`, `tests/test_evaluate.py`, `docs/context/evaluate-comparison-helpers.md`
   - **Change summary**: Add `component_score_table(results)` accepting one `RankResult`, sequence of `RankResult`, or `ProfileComparison`, returning deterministic row records with `profile`, `article_id`, `rank`, `score`, and component columns. Preserve component names from each entry and fill missing component keys with `None` where profiles differ; update context with row schema.
   - **Tests added or updated**: `tests/test_evaluate.py` asserts rows sort by profile input order then rank, include all expected component keys, accept `ProfileComparison`, and preserve finite scores/components from fixture-backed fake results.
   - **Verification command**: `uv run pytest tests/test_evaluate.py`

4. **Add cluster-inspection export**
   - **Files touched**: `news_ranker/evaluate.py`, `tests/test_evaluate.py`, `docs/context/evaluate-comparison-helpers.md`
   - **Change summary**: Add `cluster_inspection_rows(rank_result, rare_threshold=1)` returning one row per cluster from `FactUniverse`. Include cluster index, canonical fact text, support article IDs, support count, member raw indices, member fact IDs, member texts, and `is_rare` based on support count; update context with empty-universe behavior.
   - **Tests added or updated**: `tests/test_evaluate.py` builds small synthetic `FactUniverse`/`RankResult` and asserts support counts use binary article coverage, member fields remain deterministic, empty universes return empty rows, and invalid `rare_threshold` fails.
   - **Verification command**: `uv run pytest tests/test_evaluate.py`

5. **Add anonymized user-study bundle helper**
   - **Files touched**: `news_ranker/evaluate.py`, `tests/test_evaluate.py`, `docs/context/evaluate-comparison-helpers.md`
   - **Change summary**: Add `anonymized_user_study_bundle(selection, article_materials, *, include_scores=False)` where `article_materials` maps article IDs to sanitized material containing only `title`, `snippet`, and/or `summary`. Return bundle with profile, `m`, anonymized selected article labels, label-to-material mapping, optional ranks/scores/components, no original article IDs, and no answer-key map; update context with anonymization limits.
   - **Tests added or updated**: `tests/test_evaluate.py` asserts deterministic labels follow ranking order, selected labels match selected entries, original IDs are absent from material payload, missing material fails, unexpected material fields fail, and `include_scores` controls score/component inclusion.
   - **Verification command**: `uv run pytest tests/test_evaluate.py`

6. **Document module usage without changing top-level exports**
   - **Files touched**: `README.md`, `tests/test_health.py`, `docs/context/evaluate-comparison-helpers.md`
   - **Change summary**: Add short README section showing `from news_ranker.evaluate import ...` with `NewsRanker.compare_profiles()` output. Keep `news_ranker.__all__` unchanged and add/adjust health test to assert evaluate helpers are importable from submodule only; update context with public import boundary.
   - **Tests added or updated**: `tests/test_health.py` asserts selected helpers import from `news_ranker.evaluate` and `news_ranker.__all__` remains `['NewsRanker', 'RankerConfig', 'health']`.
   - **Verification command**: `uv run pytest tests/test_health.py tests/test_evaluate.py`

7. **Run full project verification and finalize context**
   - **Files touched**: `docs/context/evaluate-comparison-helpers.md`
   - **Change summary**: Run full checks after implementation, inspect diff for accidental public API or fixture changes, and record verification result in context artifact. Keep context focused on current behavior, constraints, and relevant files.
   - **Tests added or updated**: none.
   - **Verification command**: `make check`

## Risks

1. Rank correlation semantics may surprise users when profile rankings have different article sets; plan uses common IDs only and rejects fewer than two common IDs.
2. Kendall implementation without tie correction is valid for unique rank positions, but not general tied ranks.
3. Component table with differing component keys may produce `None` values; downstream CSV conversion must handle them.
4. User-study anonymization is blind-review labeling, not privacy/security anonymization. Caller must not pass source-identifying titles/snippets if true anonymity needed.
5. Strict user-study material field validation may reject useful caller data; callers must pre-sanitize material into `title`, `snippet`, and/or `summary`.
6. Omitting answer-key mapping from user-study bundles keeps participant artifacts clean but requires caller to manage label-to-ID mapping separately.
7. Plain Python return types may become public de facto API; names and field shapes should be stable once merged.
8. Adding `evaluate.py` without top-level exports may be less discoverable, but avoids unapproved `__all__` public API expansion.

## Open questions

None. Decisions for implementation:

1. `anonymized_user_study_bundle()` copies only `title`, `snippet`, and `summary`; unexpected material keys fail validation. Full article body is out of scope for v1 bundles.
2. User-study bundles omit original article IDs and omit `label_to_article_id`. Caller must keep answer key separately.
3. Expose only generic `rank_correlation(left, right, method="kendall" | "spearman")`; no `kendall_tau()` or `spearman_rho()` wrappers in v1.
4. Rank-correlation result includes coefficient plus diagnostics: method, common count, common article IDs, left-only article IDs, and right-only article IDs.
5. `top_m_overlap()` returns all useful denominators: overlap count, left/right top counts, Jaccard, left overlap fraction, right overlap fraction, and overlap article IDs.

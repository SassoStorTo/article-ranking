# Best-M Selection

## Goal

Implement `docs/brief.md` §4.9 so callers can select best *M* articles either by top composite score or by MMR diversity. Done means `news_ranker.select` contains tested `select_top_score()` and `select_mmr()` helpers, `NewsRanker.select()` honors `RankerConfig(selection_mode="mmr", selection_lambda=...)` without warning fallback, top-score behavior remains unchanged, and `make check` passes with fixture-backed deterministic tests.

## Non-goals

- No LLM decomposition, prompt work, retries, or decomposition cache.
- No raw article dictionary support, scraping, URL deduplication, or external fact-checking.
- No new dependencies.
- No public package exports change from `news_ranker.__init__`.
- No changes to ranking component formulas, profile weights, or fixture schema.
- No `evaluate.py`, rank correlation, user-study export, or cluster-inspection export.

## Approach

Add `news_ranker/select.py` as brief §4.9 module because selection logic is now distinct from pipeline orchestration. Keep it pure NumPy plus generic top-score slicing. `select_top_score(ranking, m)` should return first `m` items from already sorted ranking, preserving current behavior. `select_mmr(scores, normalized_article_embeddings, m, lambda_)` should validate inputs and return selected input indices in MMR order.

Wire MMR behind existing `NewsRanker.select()` and existing config fields. `rank()` already returns diagnostics with article embeddings in input order and ranking entries sorted by score. Pipeline can build `scores` in `fact_universe.article_ids` order, L2-normalize `diagnostics.article_embeddings` with zero-vector guard, call `select_mmr()`, then map returned indices back to existing `RankingEntry` objects by article ID. This avoids changing `RankResult`, `SelectionResult`, or public exports. If embeddings are empty-width or all-zero because facts are absent, dot-product similarities are zero, so MMR naturally reduces to score order.

Rejected option: keep warning fallback for `selection_mode="mmr"`. Brief §4.9 specifically asks for MMR selector, and config already exposes mode/lambda. Rejected adding selection diagnostics to `SelectionResult`; useful later, but public API shape change not needed for this step.

## Steps

1. **Add pure selection helpers**
   - **Files touched**: `news_ranker/select.py`, `tests/test_select.py`
   - **Change summary**: Create `select_top_score(ranking, m)` returning first `m` ranked objects and `select_mmr(scores, normalized_article_embeddings, m, lambda_)` returning input indices selected by `lambda * score - (1 - lambda) * max(0, similarity_to_selected)`. Validate `m`, `lambda_`, score shape, embedding shape, row-count match, numeric dtypes, and finite values; use stable lowest-index tie-breaks.
   - **Tests added or updated**: `tests/test_select.py` asserts top-score slicing preserves objects/order, invalid `m`/lambda/shapes/non-finite values raise, MMR first pick is highest score, MMR chooses diverse lower-similarity item when lambda allows, `lambda_=1.0` reduces to score order, and zero-width/zero-vector embeddings reduce to score order.
   - **Verification command**: `uv run pytest tests/test_select.py`

2. **Wire top-score helper into pipeline without behavior change**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Replace inline `ranking.entries[:final_m]` with `select_top_score(ranking.entries, final_m)` for `selection_mode="top_score"`. Preserve current `m` validation, configured `top_m` behavior, selected entry contents, and stable score order.
   - **Tests added or updated**: `tests/test_pipeline.py` keeps existing top-score assertions: `select(..., m=2)` equals first two ranked entries, configured `top_m` works, explicit `m` overrides config, invalid `m` values fail, and selected entries retain rank/score/component data.
   - **Verification command**: `uv run pytest tests/test_pipeline.py`

3. **Implement MMR selection mode in pipeline**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Remove runtime warning fallback. For `selection_mode="mmr"`, build scores in diagnostic article order, normalize article embeddings with epsilon guard, call `select_mmr(..., lambda_=self._config.selection_lambda)`, and return corresponding `RankingEntry` objects in MMR selection order.
   - **Tests added or updated**: `tests/test_pipeline.py` replaces warning fallback test with assertions that MMR emits no warning, first selected entry is highest ranked, selected set can differ from top-score when duplicate-like embeddings are present, `selection_lambda=1.0` matches top-score selection, and empty-fact corpora still select finite entries in score order.
   - **Verification command**: `uv run pytest tests/test_pipeline.py`

4. **Update docs for implemented selection**
   - **Files touched**: `README.md`, `docs/context/pipeline-public-api.md`, `docs/context/config-knobs.md`
   - **Change summary**: Remove docs saying MMR is unimplemented or warning fallback. Document that `selection_mode="top_score"` returns first *M* ranked entries and `selection_mode="mmr"` uses `selection_lambda` with normalized article embeddings from ranking diagnostics.
   - **Tests added or updated**: None; docs-only step.
   - **Verification command**: `uv run pytest tests/test_config.py tests/test_pipeline.py tests/test_select.py`

5. **Run full verification and inspect diff**
   - **Files touched**: none beyond prior steps
   - **Change summary**: Run full gate and fix only issues caused by selection changes. Confirm no provider/model loading, fixture migration, public export change, or weakened tests slipped in.
   - **Tests added or updated**: None.
   - **Verification command**: `make check`

## Risks

1. MMR selected order differs from ranked-score order after first pick; callers may expect `selected` sorted by rank. Existing API docs should state selected order follows selection algorithm.
2. Article embeddings in diagnostics are raw mean cluster vectors, not pre-normalized. Pipeline must normalize before calling `select_mmr()` or diversity penalty magnitude becomes provider-dependent.
3. Empty or all-zero embeddings make diversity penalty zero, causing MMR to collapse to score order. This is acceptable but should be tested.
4. Ties in MMR objective can be frequent with fake embeddings. Stable lowest-index tie-break must keep deterministic tests.
5. `selection_lambda=0.0` after first pick optimizes only diversity penalty; first pick still highest score by formula empty-set penalty zero.

## Open questions

None. Use existing `selection_mode` and `selection_lambda`; keep public result dataclasses and exports unchanged.

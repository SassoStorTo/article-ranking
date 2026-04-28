# Config Knobs Plan

## Goal

Implement brief §4.8 config surface so callers find ranking knobs in `RankerConfig`: clustering threshold/linkage, coverage weighting, profile weights, optional `top_m`, selection/diversity settings, model/version strings, and cache directory. Done means invalid configs fail early, `top_m` is validated against corpus size at `select()` call time, existing fixture-backed ranking behavior stays compatible, and `make check` passes.

## Non-goals

- No LLM decomposition, prompt file, retry loop, or decomposition cache implementation.
- No hosted embedding provider wiring or surprise model downloads.
- No MMR/diversity selection algorithm; brief §4.9 owns that.
- No fixture schema migration or raw article dictionary support.
- No new dependencies.
- No URL scraping, URL deduplication, or external fact-checking.

## Approach

Expand `RankerConfig` as dataclass-only config, not provider factory. Keep defaults deterministic and local: current profiles remain unchanged, current ranking still requires injected `FactEmbedder`, and new model/cache fields are metadata for future decomposition/cache work. Expose `distance_threshold` as derived read-only property (`1 - similarity_threshold`) instead of accepting independent threshold knobs, avoiding contradictory config.

Add optional `top_m: int | None = None`. Keep current explicit `NewsRanker.select(articles, m=...)` behavior, but allow `m=None` to use `config.top_m`; validate final `m` after articles load/rank so rule `1 <= M <= k` is checked at call time. This is backwards-compatible for existing callers but changes signature additively.

Add selection-mode validation now, but keep implementation limited to `top_score`. If `selection_mode="mmr"` is configured and `select()` is called before §4.9 lands, emit a runtime warning and fall back to top-score selection so config is accepted but diversity is not silently claimed. Considered implementing MMR here, rejected because brief splits selection into §4.9 and current request targets config only.

## Steps

1. **Add config fields and validation**
   - **Files touched**: `news_ranker/config.py`, `tests/test_config.py`
   - **Change summary**: Add config fields for `top_m`, `selection_mode`, `selection_lambda`, `embedding_model_name`, `llm_model_name`, `prompt_version`, `schema_version`, and `cache_dir`; add `distance_threshold` property. Validate similarity threshold range, profile weights, `top_m` type/positivity when present, selection mode/lambda, non-empty model/version strings, and cache path type. Keep default `embedding_model_name="all-MiniLM-L6-v2"`; callers can set `"paraphrase-multilingual-mpnet-base-v2"` explicitly.
   - **Tests added or updated**: `tests/test_config.py` asserts defaults including embedding model name, derived distance threshold, invalid similarity thresholds, invalid `top_m`, invalid selection mode/lambda, invalid model/version strings, invalid cache dir, explicit multilingual embedding model override, and existing profile validation behavior.
   - **Verification command**: `uv run pytest tests/test_config.py`

2. **Wire configured `top_m` into selection**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Change `NewsRanker.select()` to accept `m: int | None = None`; if omitted, read `self._config.top_m`. Preserve explicit `m` precedence and existing error messages where possible; validate final `m` after ranking against article count.
   - **Tests added or updated**: `tests/test_pipeline.py` adds cases where configured `top_m` is used, explicit `m` overrides configured `top_m`, omitted `m` without config fails, non-integer configured `top_m` is rejected by config, and configured `top_m > article_count` fails at call time.
   - **Verification command**: `uv run pytest tests/test_pipeline.py`

3. **Respect selection mode without implementing MMR**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Keep `selection_mode="top_score"` path identical to current first-*M* behavior. If config uses `selection_mode="mmr"`, emit a warning that MMR is not implemented yet and return top-score selection as temporary fallback.
   - **Tests added or updated**: `tests/test_pipeline.py` asserts default/top-score selection equals first *M* ranked entries and configured `mmr` mode emits the expected warning while returning first *M* ranked entries.
   - **Verification command**: `uv run pytest tests/test_pipeline.py`

4. **Update public config docs and exports sanity**
   - **Files touched**: `README.md`, `tests/test_health.py`
   - **Change summary**: Document new `RankerConfig` knobs and note that model/cache fields are metadata until decomposition/cache modules exist. Keep `news_ranker.__init__` exports unchanged unless tests reveal import regression.
   - **Tests added or updated**: `tests/test_health.py` keeps public imports stable; no new public symbols required.
   - **Verification command**: `uv run pytest tests/test_health.py`

5. **Run full project verification**
   - **Files touched**: none beyond prior steps
   - **Change summary**: Run full quality gate and fix only issues caused by config changes. Inspect diff for accidental provider downloads, API removals, or fixture changes.
   - **Tests added or updated**: none.
   - **Verification command**: `make check`

## Risks

1. Additive `select(m=None)` signature is public API change; user approved, but type-checkers and callers will still see it.
2. Allowing `selection_mode="mmr"` in config while falling back to top-score can still surprise callers if warnings are missed; warning text must be explicit that diversity was not applied.
3. Model/cache fields may look operational even though no decompose/cache module consumes them yet; docs must state metadata-only.
4. Moving config tests into `tests/test_config.py` can duplicate existing `tests/test_pipeline.py` config assertions if old tests not adjusted carefully.
5. Cache dir default path can create expectations about file creation; implementation must not create directories in config validation.

## Open questions

None. Decisions captured: `select(m=None)` approved; `selection_mode="mmr"` accepted with warning plus top-score fallback until implemented; default embedding model remains `all-MiniLM-L6-v2` while callers may configure `paraphrase-multilingual-mpnet-base-v2`.

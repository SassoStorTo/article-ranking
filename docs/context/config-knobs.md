# Config Knobs Context

## Relevant files

- `news_ranker/config.py` defines frozen `RankerConfig`, default scoring profiles, config validation helpers, and derived `distance_threshold`.
- `news_ranker/pipeline.py` consumes `RankerConfig` for ranking, scoring, and selection.
- `tests/test_config.py` covers config defaults and invalid config values.
- `tests/test_pipeline.py` covers public ranking/selection behavior, including configured `top_m` and `selection_mode` fallback.
- `tests/test_health.py` checks public imports and `__all__` stability.
- `README.md` documents public config knobs.
- `docs/plans/config-knobs.md` contains implementation plan.

## Current behavior

`RankerConfig` exposes deterministic, dataclass-only configuration. It does not create providers, load models, create cache directories, or perform decomposition/cache work.

Config fields currently include:

- `similarity_threshold` with validation for numeric finite value in `[-1.0, 1.0]`.
- Derived read-only `distance_threshold = 1.0 - similarity_threshold`.
- `linkage`, limited to `"average"` or `"single"`.
- `coverage_weighting`, limited to `"consensus"` or `"rarity"`.
- `profiles`, mapping profile names to exact component weights for `centrality`, `coverage`, `density`, and `entity_coverage`; weights must be finite, nonnegative, and sum to `1.0` within tolerance.
- Optional `top_m`, validated as positive non-bool integer when present.
- `selection_mode`, limited to `"top_score"` or `"mmr"`.
- `selection_lambda`, finite numeric value in `[0.0, 1.0]`.
- Metadata strings `embedding_model_name`, `llm_model_name`, `prompt_version`, `schema_version`, all non-empty after stripping.
- Optional `cache_dir`, accepted as string/path-like or `None`; no directory creation.

`NewsRanker.select()` accepts `m: int | None = None`. If explicit `m` is supplied, it wins. If omitted, `config.top_m` is used. Final `m` is validated after ranking so `1 <= m <= article_count` checks actual loaded corpus size. Omitted `m` with no configured `top_m` raises `TypeError("m must be an integer")`.

`selection_mode="top_score"` returns first `m` ranked entries. `selection_mode="mmr"` emits `RuntimeWarning` saying MMR is not implemented yet and falls back to top-score selection without diversity.

## Constraints

- No new dependencies.
- No provider/model loading from config metadata.
- No cache directory creation during config validation.
- No MMR/diversity algorithm in this config task.
- No scraping, URL deduplication, external fact-checking, fixture schema migration, or raw article dictionary support.
- Existing fixture-backed ranking still requires injected `FactEmbedder`.

## Verification state

Reviewer ran `make check`; result passed:

- mypy: success
- ruff check: passed
- ruff format check: passed
- pytest: 114 passed

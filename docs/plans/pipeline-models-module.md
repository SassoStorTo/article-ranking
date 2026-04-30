# Pipeline Results Module Plan

## Goal

Move public pipeline result records out of `news_ranker/pipeline.py` into `news_ranker/results.py` while keeping existing caller imports working. Done means `NewsRanker` still lives in `news_ranker.pipeline`, result records can be imported from `news_ranker.results`, legacy `news_ranker.pipeline` imports remain compatible, tests/typecheck pass.

## Non-goals

- Change ranking, selection, scoring, loading, or decomposition behavior.
- Change public package root exports in `news_ranker/__init__.py`.
- Rename public dataclasses or alter field names/types.
- Add dependencies.
- Remove legacy imports from `news_ranker.pipeline`.

## Approach

Create `news_ranker/results.py` for `RankingEntry`, `RankDiagnostics`, `RankResult`, `SelectionResult`, and `ProfileComparison`. Leave input aliases/protocols in `pipeline.py` because they describe orchestrator inputs, not result payloads. `pipeline.py` imports result records from new module so current imports like `from news_ranker.pipeline import RankResult` keep working.

Then update internal non-orchestrator consumers to import result records from `results` instead of `pipeline`. This reduces coupling without breaking callers. Rejected `models.py`: too broad and easy to confuse with article schemas. Rejected moving records into `schemas.py`: those are structured article JSON schemas, while these are ranking/selection outputs. Tradeoff: one extra module, but cleaner ownership and less import weight for evaluation helpers.

## Steps

1. **Extract pipeline models behind compatibility imports**
   - **Files touched**: `news_ranker/results.py`, `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Create new module containing result dataclasses. Remove their definitions from `pipeline.py`; import same names from `results` so legacy `news_ranker.pipeline` imports still resolve.
   - **Tests added or updated**: Update `tests/test_pipeline.py` imports only if needed; add/assert legacy import compatibility by checking `RankResult.__module__ == "news_ranker.results"` while imports from `news_ranker.pipeline` still work.
   - **Verification command**: `uv run pytest tests/test_pipeline.py`

2. **Point internal consumers at model module**
   - **Files touched**: `news_ranker/evaluate.py`, `tests/test_evaluate.py`, `tests/test_pipeline.py`, `tests/test_health.py`
   - **Change summary**: Import `ProfileComparison`, `RankingEntry`, `RankDiagnostics`, `RankResult`, and `SelectionResult` from `news_ranker.results` where code does not need `NewsRanker`. Keep `NewsRanker` imported from `news_ranker.pipeline`.
   - **Tests added or updated**: Update import lines in `tests/test_evaluate.py` and `tests/test_pipeline.py`; keep `tests/test_health.py` public-root assertions unchanged except add no root export for result records.
   - **Verification command**: `make check`

## Risks

1. Circular imports if `results.py` imports `pipeline.py`; avoid by depending only on `cluster` and `score` types.
2. Backward compatibility breaks if `pipeline.py` stops binding old result names; keep imported names at module top level.
3. Mypy may require precise numpy array typing in new module.
4. Test expectations using `__module__` may need update from `news_ranker.pipeline` to `news_ranker.results`.

## Open questions

- None.

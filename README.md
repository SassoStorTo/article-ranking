# news-ranker

A scoring library that takes *k* articles about the same news event, ranks them from best to worst, selects the best *M*, and compares alternative definitions of "best" using structured fact decomposition, embedding centrality, information coverage, and optional diversity.

## Configuration

`RankerConfig` exposes ranking and selection knobs:

- `similarity_threshold` and derived `distance_threshold` for fact clustering.
- `linkage` (`"average"` or `"single"`) for clustering.
- `coverage_weighting` (`"consensus"` or `"rarity"`) for coverage scoring.
- `profiles` for component weights (`centrality`, `coverage`, `density`, `entity_coverage`).
- `top_m` as optional default selection count. Explicit `select(..., m=...)` wins.
- `selection_mode` (`"top_score"` or `"mmr"`) and `selection_lambda` for diversity selection. `"mmr"` currently warns and falls back to top-score selection until diversity selection lands.
- `embedding_model_name`, `llm_model_name`, `prompt_version`, `schema_version`, and `cache_dir` as metadata for future decomposition/cache modules. Current fixture-backed ranking does not create caches or load models from these fields.

```python
from news_ranker import RankerConfig

config = RankerConfig(
    top_m=3,
    similarity_threshold=0.85,
    coverage_weighting="consensus",
    embedding_model_name="all-MiniLM-L6-v2",
)
```

## Commands

```sh
make install
make dev
make test
make lint
make build
make check
```

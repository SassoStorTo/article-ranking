# news-ranker

A scoring library that takes *k* articles about the same news event, ranks them from best to worst, selects the best *M*, and compares alternative definitions of "best" using structured fact decomposition, embedding centrality, information coverage, and optional diversity.

## Configuration

`RankerConfig` exposes ranking and selection knobs:

- `similarity_threshold` and derived `distance_threshold` for fact clustering.
- `linkage` (`"average"` or `"single"`) for clustering.
- `coverage_weighting` (`"consensus"` or `"rarity"`) for coverage scoring.
- `profiles` for component weights (`centrality`, `coverage`, `density`, `entity_coverage`).
- `top_m` as optional default selection count. Explicit `select(..., m=...)` wins.
- `selection_mode` (`"top_score"` or `"mmr"`) and `selection_lambda` for selection. `"top_score"` returns first *M* ranked entries. `"mmr"` selects entries by maximal marginal relevance using `selection_lambda` and normalized article embeddings from ranking diagnostics.
- `embedding_model_name`, `llm_model_name`, `prompt_version`, `schema_version`, and `cache_dir` as metadata for decomposition/cache modules. `llm_model_name` defaults to Mistral model naming, but `NewsRanker` does not create providers from config; callers must inject a decomposition client/decomposer explicitly.

```python
from news_ranker import RankerConfig

config = RankerConfig(
    top_m=3,
    similarity_threshold=0.85,
    coverage_weighting="consensus",
    embedding_model_name="all-MiniLM-L6-v2",
)
```

## Mistral decomposition

Mistral support lives in the `news_ranker.mistral` submodule and is not
re-exported from the top-level package. Create the provider client explicitly,
then pass it to `decompose()` or through the raw-dict `NewsRanker` decomposer
hook. `MistralDecompositionClient` reads `MISTRAL_API_KEY` when `api_key` is not
provided.

```python
from pathlib import Path

from news_ranker import DecompositionConfig, NewsRanker, decompose
from news_ranker.mistral import MistralDecompositionClient

client = MistralDecompositionClient()
config = DecompositionConfig(model="mistral-small-latest")
cache_dir = Path(".cache/news-ranker")

ranker = NewsRanker(
    embedder,
    decomposer=lambda article: decompose(
        article,
        client,
        config=config,
        cache_dir=cache_dir,
    ),
)
ranking = ranker.rank(raw_articles)
```

## Evaluation helpers

Comparison and review helpers live in `news_ranker.evaluate`; they are not
re-exported from the top-level package.

```python
from news_ranker import NewsRanker
from news_ranker.evaluate import component_score_table, rank_correlation, top_m_overlap

ranker = NewsRanker(embedder)
comparison = ranker.compare_profiles(
    article_dir, profiles=("representative", "coverage")
)

representative = comparison.rankings["representative"]
coverage = comparison.rankings["coverage"]
overlap = top_m_overlap(representative, coverage, m=3)
correlation = rank_correlation(representative, coverage, method="spearman")
score_rows = component_score_table(comparison)
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

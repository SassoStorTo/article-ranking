# Fact Clustering Context

## Current source of truth

Fact clustering builds on `StructuredArticle` objects from `news_ranker/schemas.py`. Callers should load fixtures with `load_structured_article()` or set `article_id` manually before clustering. Fixture JSON still omits `article_id`; runtime IDs are path-like values such as `trump-shooting/bbc`.

No scraping, URL deduplication, external fact-checking, LLM decomposition, or hosted embedding API is part of this implementation.

## Implemented clustering module

`news_ranker/cluster.py` contains:

- `RawFact`: flattened fact metadata record with `article_id`, `fact_id`, and `text`
- `FactUniverse`: clustered fact universe output record
- `flatten_fact_items(articles)`: flattens `StructuredArticle.fact_items` in article order, with events before claims
- `build_fact_universe(articles, fact_embeddings, *, similarity_threshold=0.85, linkage="average")`

`build_fact_universe()` requires fact embeddings to align row-for-row with `flatten_fact_items(articles)`. Embeddings are validated as 2-D finite numeric arrays, converted to `float32`, and rejected if any non-empty row has zero norm. Article IDs must be present, non-empty, and unique. `similarity_threshold` must be finite in `[-1.0, 1.0]`. `linkage` is limited to `"average"` and `"single"`.

Clustering uses `sklearn.cluster.AgglomerativeClustering` with cosine metric, `n_clusters=None`, and `distance_threshold` derived from `1 - similarity_threshold`. Average linkage is default; single linkage is available for high-recall chaining experiments. Sklearn labels are remapped by first raw-fact occurrence for deterministic downstream ordering.

`FactUniverse` exposes these shapes:

- `article_ids`: tuple of `k` article IDs
- `raw_fact_article_ids`, `raw_fact_ids`, `raw_fact_texts`: tuples of length `n_raw_facts`
- `canonical_fact_texts`: tuple of length `n_clusters`, using deterministic cosine medoid text nearest each cluster mean
- `cluster_vectors`: `float32` array shaped `(n_clusters, embedding_dim)`, mean of member embeddings
- `cluster_assignments`: integer array shaped `(n_raw_facts,)`
- `cluster_members`: tuple of raw-fact index tuples, one per cluster
- `coverage_matrix`: integer array shaped `(k, n_clusters)`, binary per article and cluster

Repeated raw facts from one article set coverage to `1`, not counts. Empty fact input is supported if embeddings are 2-D with zero rows; output keeps known article IDs, empty cluster records, `cluster_vectors` shaped `(0, embedding_dim)`, and `coverage_matrix` shaped `(k, 0)`.

## Fixture-level assumptions

Tests cover `articles/trump-shooting/*.json` through `load_structured_article()`. Smoke coverage uses local deterministic `np.eye(..., dtype=np.float32)` fact embeddings, not `SentenceTransformer`.

## Constraints for future pipeline work

Future pipeline work should pass loaded `StructuredArticle` objects plus already-created fact embeddings into `build_fact_universe()`. It must preserve raw fact order when pairing embeddings with facts.

Do not change fixture schema, entity schema, provider choices, or public package exports without a later plan approving that scope.

# Fact Clustering and Scoring Context

## Current source of truth

Fact clustering and scoring build on `StructuredArticle` objects from `news_ranker/schemas.py`. Callers should load fixtures with `load_structured_article()` or set `article_id` manually before clustering. Fixture JSON still omits `article_id`; runtime IDs are path-like values such as `trump-shooting/bbc`.

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

## Implemented scoring module

`news_ranker/score.py` contains:

- `ScoreVector(raw, normalized, defined)`
- `minmax_normalize(values, *, defined=True)`
- `centrality(article_embeddings)`
- `coverage(coverage_matrix, mode="consensus" | "rarity")`
- `density(structured_articles, coverage_matrix)`
- `entity_coverage(structured_articles)`
- `combine(components, weights, *, renormalize_undefined=True)`

All score arrays are returned as `float32`. Validation rejects wrong dimensions, nonnumeric data, and non-finite values. Coverage matrices must be 2-D, numeric, finite, and nonnegative. Scoring functions validate row counts where article sequences are involved.

Normalization behavior:

- defined tied values normalize to all ones
- undefined components normalize to all zeros
- empty vectors are undefined zeros

`centrality()` L2-normalizes article embeddings with an epsilon guard, computes centroid distance, uses negative distance as raw score, then min-max normalizes.

`coverage()` converts any positive coverage entry to covered once. Consensus mode weights clusters by document frequency divided by article count. Rarity mode uses positive log-based inverse-frequency weights. Empty fact universes are undefined zeros.

`density()` computes unique covered clusters divided by `len(events) + len(claims)` for each article. Articles with zero extracted entries receive raw zero; corpora with no entries are undefined zeros.

`entity_coverage()` normalizes entity names with casefolding and whitespace collapse, keeps entity groups separate (`people`, `organizations`, `locations`), and scores weighted recall with consensus document-frequency weights. Corpora with no entities are undefined zeros. Alias merging is not implemented.

`combine()` consumes normalized component values only. Weights must reference known components, be finite, nonnegative, and include at least one positive value. Component lengths must match. Undefined weighted components are skipped and remaining weights renormalized by default.

## Fixture-level assumptions

Tests cover `articles/trump-shooting/*.json` through `load_structured_article()`. Smoke coverage uses local deterministic `np.eye(..., dtype=np.float32)` fact embeddings, not `SentenceTransformer`. Article vectors for centrality can be built from `embed_article_from_clusters(article_id, universe.article_ids, universe.coverage_matrix, universe.cluster_vectors)` when each article covers at least one cluster.

## Constraints for future pipeline and selection work

Future pipeline work should pass loaded `StructuredArticle` objects plus already-created fact embeddings into `build_fact_universe()`. It must preserve raw fact order when pairing embeddings with facts.

Future selection/ranking should consume `ScoreVector.normalized` values and `combine()` output rather than re-normalizing raw component scores ad hoc. Undefined component handling should remain explicit so empty fact/entity cases do not silently distort final scores.

Do not change fixture schema, entity schema, provider choices, or public package exports without a later plan approving that scope.

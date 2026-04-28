# Scoring Context

## Current source of truth

Scoring builds on `StructuredArticle` objects from `news_ranker/schemas.py` and clustered fact universes produced by `news_ranker/cluster.py`.

No scraping, URL deduplication, external fact-checking, LLM decomposition, or hosted embedding API is part of this implementation.

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

Tests cover `articles/trump-shooting/*.json` through `load_structured_article()`. Article vectors for centrality can be built from `embed_article_from_clusters(article_id, universe.article_ids, universe.coverage_matrix, universe.cluster_vectors)` when each article covers at least one cluster.

## Constraints for future selection/ranking work

Future selection/ranking should consume `ScoreVector.normalized` values and `combine()` output rather than re-normalizing raw component scores ad hoc. Undefined component handling should remain explicit so empty fact/entity cases do not silently distort final scores.

Do not change fixture schema, entity schema, provider choices, or public package exports without a later plan approving that scope.

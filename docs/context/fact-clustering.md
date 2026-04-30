# Fact Clustering Context

## Scope

This context covers current fact-clustering behavior: structured-article fact flattening, embedding validation, agglomerative clustering, canonical text/cluster vector construction, coverage-matrix semantics, pipeline integration, config knobs, diagnostics exports, and tests that lock this behavior. It deliberately does not cover LLM decomposition internals, prompt design, scoring formulas beyond how they consume `FactUniverse`, MMR math beyond its use of article embeddings, provider-specific embedding quality, scraping, URL deduplication, external fact-checking, or fixture schema migration.

## Key files

### Core clustering and data inputs

- `news_ranker/cluster.py` — defines `RawFact`, `FactUniverse`, `flatten_fact_items()`, and `build_fact_universe()` plus validation and clustering helpers.
- `news_ranker/schemas.py` — defines strict `StructuredArticle` schema and event/claim `fact_items` order consumed by clustering.
- `news_ranker/embed.py` — validates fact embeddings before clustering and builds article vectors from unique covered cluster vectors.
- `news_ranker/config.py` — exposes `similarity_threshold`, derived `distance_threshold`, and `linkage` config passed into clustering.

### Pipeline, diagnostics, and consumers

- `news_ranker/pipeline.py` — loads articles, flattens facts, embeds fact texts, builds `FactUniverse`, derives article embeddings, and passes coverage into scoring.
- `news_ranker/results.py` — stores `FactUniverse` in `RankDiagnostics` for downstream inspection.
- `news_ranker/score.py` — consumes `coverage_matrix` for coverage and density; treats positive coverage values as binary.
- `news_ranker/evaluate.py` — `cluster_inspection_rows()` exports cluster members, support article IDs/counts, and rare flags from diagnostics.

### Tests

- `tests/test_cluster.py` — unit coverage for flatten order, article-ID validation, embedding validation, empty facts, merge/split behavior, linkage, binary coverage, medoid text, label order, and vector dtype.
- `tests/test_pipeline.py` — verifies pipeline calls clustering with flattened fact order, empty/mixed fact handling, article embedding shapes, and fixture-backed ranking.
- `tests/test_embed.py` — verifies fact embedding dtype/shape/finite checks and article-vector mean over unique covered clusters.
- `tests/test_evaluate.py` — verifies cluster inspection row fields, binary support counts, empty-universe behavior, and rare-threshold validation.
- `tests/test_schemas.py` — verifies fixture schema, derived runtime article IDs, strict validation, and event-then-claim fact order.

## Data flow / control flow

1. Article fixtures load through `load_structured_article(path)`, which validates JSON as `StructuredArticle` and sets `article_id` from JSON or path-derived ID such as `trump-shooting/bbc`.
2. `StructuredArticle.fact_items` returns `(fact_id, text)` pairs with all events first, then all claims. Event text is built from `who`, `what`, and non-null optional fields; claim text is `statement`.
3. `flatten_fact_items(articles)` validates every article has non-empty unique `article_id`, then emits `RawFact(article_id, fact_id, text)` in article input order and per-article event/claim order.
4. Pipeline builds `fact_texts = [fact.text for fact in raw_facts]`. If non-empty, `embed_facts()` calls injected `FactEmbedder` and requires a 2-D finite `np.float32` array. If empty, pipeline passes `np.empty((0, 0), dtype=np.float32)` directly into clustering.
5. `build_fact_universe()` revalidates article IDs, re-flattens facts, validates `fact_embeddings` as 2-D numeric finite data with row count equal to flattened fact count, converts to `float32`, and rejects non-empty zero-norm rows.
6. Empty fact input returns `FactUniverse` with known `article_ids`, empty raw/canonical/assignment/member records, `cluster_vectors` shaped `(0, embedding_dim)`, and `coverage_matrix` shaped `(k, 0)`.
7. Non-empty fact input runs `AgglomerativeClustering(n_clusters=None, metric="cosine", linkage=linkage, distance_threshold=np.nextafter(1.0 - similarity_threshold, np.inf))`. Single-fact input skips sklearn and assigns cluster `0`.
8. Sklearn labels are remapped by first raw-fact occurrence so cluster order is deterministic for downstream ranking, diagnostics, and tests.
9. `cluster_members` is a tuple of raw-fact index tuples by remapped cluster index. `cluster_vectors` is the mean of member embeddings, returned as `np.float32`.
10. `canonical_fact_texts` chooses a deterministic cosine medoid: raw fact closest to cluster mean. If centroid norm is zero, it falls back to first member; non-empty input rows themselves cannot have zero norm.
11. `coverage_matrix` is integer article-by-cluster coverage. Each raw fact sets its owning article/cluster cell to `1`; repeated facts from one article do not increment counts.
12. Pipeline builds article embeddings with `embed_article_from_clusters(article_id, article_ids, coverage_matrix, cluster_vectors)`. This averages unique covered cluster vectors where coverage row is nonzero. Articles with no covered clusters remain zero in pipeline output rather than calling the helper.
13. Pipeline marks centrality undefined when fact universe is empty or any article covers zero clusters. Coverage and density consume `coverage_matrix`; both convert positive entries to binary internally.
14. `RankDiagnostics.fact_universe` carries clustering artifacts into evaluation. `cluster_inspection_rows()` iterates `cluster_members`, computes `support_article_ids` from `coverage_matrix[:, cluster_index] > 0`, and returns canonical text, support count, member raw indices, member fact IDs/texts, and `is_rare = support_count <= rare_threshold`.

## Conventions observed

- Fact order is stable and tested: article input order, then events before claims inside each article.
- Runtime `article_id` must be present, non-empty, and unique before clustering; fixture JSON may omit it because loader derives it.
- Embedding arrays for clustering may start as integer or floating numeric arrays, but clustering stores vectors as `np.float32`; `embed_facts()` itself requires exact `np.float32` from injected embedders.
- Similarity threshold is numeric, finite, and within `[-1.0, 1.0]`; distance threshold is derived as `1.0 - similarity_threshold`, not configured independently.
- Supported linkage values are exactly `"average"` and `"single"`; average is default and tested to avoid chaining that single linkage permits.
- Coverage semantics are binary per article/cluster. Downstream scoring and cluster inspection also treat any positive value as covered once.
- Determinism comes from sorted fixture directory loading, preserved explicit input order, label remapping by first occurrence, stable rank tie-breaks by input index, and local fake embedders in tests.
- Error handling uses explicit `TypeError` for wrong types/dtypes and `ValueError` for invalid values/shapes; tests match key substrings such as `"row count"`, `"2-D"`, `"finite"`, `"nonzero"`, `"unique"`, and `"linkage"`.
- Tests avoid real `SentenceTransformer` model loads/downloads; clustering tests use synthetic `np.eye` or hand-built vectors.
- Empty fact corpora are valid through clustering and pipeline diagnostics; they produce empty coverage and undefined centrality/coverage/density as appropriate.

## Open questions

1. No corpus-specific calibrated value for `similarity_threshold=0.85` is documented from manual cluster inspection.
2. No implemented cache exists for fact embeddings despite brief mentioning embedding cache keys.
3. No generated canonical fact labels exist; canonical text is always medoid source text.
4. No validation in `cluster_inspection_rows()` checks internal `FactUniverse` shape consistency before indexing; callers rely on builder-created universes or well-formed synthetic tests.
5. No explicit handling exists for negative or zero similarity thresholds beyond validation range; behavior is delegated to sklearn distance threshold semantics.

## Suggested next step

Plan session should focus on any intended change to clustering quality or diagnostics while preserving flattened fact/embedding row alignment, binary coverage semantics, deterministic cluster ordering, and current empty-fact behavior.

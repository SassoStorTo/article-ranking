# Fact Clustering and Scoring

## Goal

Implement `docs/brief.md` sections 4.5 and 4.6 on top of existing fixture-based structured article and embedding foundation. Done means caller can build a deterministic `FactUniverse` from loaded `StructuredArticle` objects plus fact embeddings, get canonical fact medoids, cluster vectors, assignments, and binary coverage matrix, then compute centrality, coverage, density, entity coverage, and weighted composite scores with strict NumPy validation and unit-test coverage.

## Non-goals

- No LLM decomposition, prompt work, retries, or decomposition cache.
- No scraping, URL deduplication, external fact-checking, or hosted embedding API.
- No `pipeline.py`, `select.py`, `evaluate.py`, profile config, or public `NewsRanker` API.
- No fixture JSON migration or schema change from current `{name, role}` entities.
- No generated canonical fact labels; canonical facts will be cluster medoid texts.
- No public package exports from `news_ranker/__init__.py` unless later API plan approves them.

## Approach

Add `scikit-learn` and implement `news_ranker/cluster.py` around `sklearn.cluster.AgglomerativeClustering`, matching brief section 4.5 directly. The module will flatten `StructuredArticle.fact_items` in article order, validate that supplied fact embeddings align row-for-row with that flattened fact list, compute cosine-distance clustering with `distance_threshold=1 - similarity_threshold`, and default to average linkage. Optional single linkage remains available for high-recall experiments.

Represent clustering output as a dataclass `FactUniverse`: article IDs, raw fact article IDs, raw fact IDs, raw fact texts, canonical fact medoid texts, cluster vectors, cluster assignments, cluster members, and binary coverage matrix. Cluster vectors use mean member embeddings cast to `float32`; canonical texts use deterministic medoids nearest each cluster centroid in cosine space. Because sklearn labels are not guaranteed to be ordered by semantic position, implementation should remap labels deterministically by first raw-fact occurrence before building outputs.

Add `news_ranker/score.py` with pure NumPy functions returning a small `ScoreVector` dataclass containing raw values, normalized values, and `defined` status. Implement `minmax_normalize`, `centrality`, `coverage`, `density`, `entity_coverage`, and `combine`. Scoring functions validate shapes, finite numeric inputs, and row counts. Undefined components such as empty fact universe or no entities normalize to zeros, while tied-but-defined components normalize to ones per brief section 7.4.

Rejected alternative: custom pure-NumPy agglomerative clustering. It would avoid one dependency, but would be longer, easier to get subtly wrong, and less faithful to brief wording. Rejected generated canonical labels because that implies LLM/prompt work outside current scope.

## Steps

1. **Add sklearn dependency**
   - **Files touched**: `pyproject.toml`, `uv.lock`
   - **Change summary**: Add `scikit-learn` as runtime dependency so clustering can use `sklearn.cluster.AgglomerativeClustering` instead of custom agglomerative code.
   - **Tests added or updated**: None; dependency-only step.
   - **Verification command**: `make check`

2. **Add cluster module skeleton, records, and validation**
   - **Files touched**: `news_ranker/cluster.py`, `tests/test_cluster.py`
   - **Change summary**: Add `FactUniverse` dataclass, accepted linkage type, flattening helpers for `StructuredArticle.fact_items`, and validation for article IDs, duplicate article IDs, embedding row count, 2-D finite numeric embeddings, nonzero vector norms, and valid similarity threshold. Empty fact input with a 2-D empty embedding array returns an empty universe with coverage shape `(k, 0)`.
   - **Tests added or updated**: `tests/test_cluster.py` asserts fixture-backed articles flatten in article order, missing `article_id` fails, duplicate article IDs fail, row-count mismatch fails, non-2-D/non-finite/zero-vector embeddings fail, and empty facts return empty coverage with known article IDs.
   - **Verification command**: `make check`

3. **Implement sklearn-backed semantic fact clustering**
   - **Files touched**: `news_ranker/cluster.py`, `tests/test_cluster.py`
   - **Change summary**: Use `AgglomerativeClustering(metric="cosine", linkage="average", distance_threshold=1 - similarity_threshold, n_clusters=None)` by default, with optional `linkage="single"`. Remap sklearn labels by first occurrence, choose canonical medoid texts, compute mean cluster vectors, raw-fact assignments, cluster members, and binary coverage matrix.
   - **Tests added or updated**: `tests/test_cluster.py` asserts near-duplicate facts merge under threshold, distant facts remain split, average linkage avoids a chaining merge that single linkage permits, repeated facts from one article set coverage to `1` not counts, canonical medoid text is deterministic, label order is deterministic after remapping, and cluster vector means are `float32`.
   - **Verification command**: `make check`

4. **Add normalization and centrality scoring**
   - **Files touched**: `news_ranker/score.py`, `tests/test_score.py`
   - **Change summary**: Add `ScoreVector`, `minmax_normalize`, and `centrality(article_embeddings)`. Centrality L2-normalizes article embeddings with epsilon guard, computes raw negative distance to centroid, and min-max normalizes so higher means more central.
   - **Tests added or updated**: `tests/test_score.py` asserts min-max normal behavior, tied defined components normalize to ones, undefined components normalize to zeros, central article receives highest normalized centrality, identical embeddings tie at one, and invalid embedding shapes/non-finite values raise.
   - **Verification command**: `make check`

5. **Add fact coverage and density scoring**
   - **Files touched**: `news_ranker/score.py`, `tests/test_score.py`
   - **Change summary**: Implement `coverage(coverage_matrix, mode="consensus" | "rarity")` and `density(structured_articles, coverage_matrix)`. Coverage uses document-frequency weights from brief formulas and handles empty fact universes as undefined; density uses unique covered clusters divided by event-plus-claim entry count per article.
   - **Tests added or updated**: `tests/test_score.py` asserts full fact coverage raw score equals `1.0`, consensus weights reward high-support facts, rarity weights remain positive when all articles cover a fact, empty fact universe returns undefined zeros, density computes `unique / entries`, repeated coverage values do not inflate density, all-empty extractions are undefined zeros, and row-count mismatches raise.
   - **Verification command**: `make check`

6. **Add entity coverage and component combination**
   - **Files touched**: `news_ranker/score.py`, `tests/test_score.py`
   - **Change summary**: Implement `entity_coverage(structured_articles)` using exact normalized entity names grouped by people, organizations, and locations from current schema, with consensus weighting. Add `combine(components, weights, *, renormalize_undefined=True)` for weighted sums over normalized component vectors, including nonnegative weight and length validation.
   - **Tests added or updated**: `tests/test_score.py` asserts entity coverage handles shared and missing entities, no-entity corpora return undefined zeros, grouped entity keys avoid accidental cross-type collisions, composite scoring uses normalized component values, undefined weighted components are renormalized by default, and invalid weights or component lengths raise.
   - **Verification command**: `make check`

7. **Add fixture-level clustering-to-scoring smoke test**
   - **Files touched**: `tests/test_cluster.py`, `tests/test_score.py`
   - **Change summary**: Add a small deterministic end-to-end unit path using loaded `articles/trump-shooting/*.json`, synthetic `float32` fact embeddings, `build_fact_universe`, existing `embed_article_from_clusters`, and scoring functions. Keep fake embeddings local and deterministic; never instantiate `SentenceTransformer`.
   - **Tests added or updated**: `tests/test_cluster.py` or `tests/test_score.py` asserts five fixture articles produce a coverage matrix with five rows, article vectors can be built for articles covering clusters, centrality/coverage/density/entity coverage return length-five vectors, and `combine` returns finite length-five scores.
   - **Verification command**: `make check`

8. **Write implementation context artifact**
   - **Files touched**: `docs/context/fact-clustering-scoring.md`
   - **Change summary**: Document implemented clustering and scoring modules, sklearn dependency, public helper shapes, validation behavior, fixture-based assumptions, and constraints for future pipeline/selection work. Keep artifact focused on current state, not general notes.
   - **Tests added or updated**: None; docs-only step.
   - **Verification command**: `make check`

## Risks

1. `scikit-learn` adds runtime dependency weight and may expose version-specific `AgglomerativeClustering` parameter names; implementation should target installed/locked version.
2. Exact entity-name matching will not merge aliases like `Cole Allen` and `Cole Tomas Allen`; fixing that needs schema/prompt/entity canonicalization work outside this scope.
3. Cosine clustering requires nonzero finite vectors; bad fake or provider embeddings must fail fast.
4. Threshold `0.85` may over-split or over-merge real facts; later tuning by inspection likely needed.
5. Current `StructuredArticle.article_id` is optional in schema; clustering must reject unset IDs unless caller loaded articles through `load_structured_article()` or set IDs manually.
6. Score normalization is corpus-relative; raw final scores remain not comparable across unrelated event corpora.

## Open questions

None. User approved adding `scikit-learn` for shorter implementation closer to brief wording.

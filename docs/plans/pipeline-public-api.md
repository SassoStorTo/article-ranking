# Pipeline Public API

## Goal

Implement `docs/brief.md` section 4.7 as a fixture-backed public API. Done means a caller can instantiate `NewsRanker`, point `rank()`, `select()`, or `compare_profiles()` at `articles/trump-shooting/` or another folder of already-structured JSON files, and receive deterministic rankings, top-M selections, and per-profile comparisons built from existing schema loading, embedding, clustering, and scoring modules. The design must skip LLM decomposition for now but keep input normalization isolated so future raw-article decomposition can plug in without rewriting scoring orchestration.

## Non-goals

- No LLM decomposition, `prompts.py`, `decompose.py`, retries, decomposition cache, or raw `{id, title, body}` article processing.
- No scraping, URL deduplication, external fact-checking, hosted embedding API, or provider switch.
- No MMR/diversity implementation and no `select.py`; `select()` will use top-score selection only until brief section 4.9 is planned.
- No `evaluate.py`, rank-correlation metrics, user-study export, or cluster-inspection export.
- No fixture JSON migration and no schema change from current `{name, role}` entities.
- No generated canonical fact labels; pipeline will use existing clustering medoid texts.

## Approach

Add a small config module and a new `pipeline.py` module that compose existing building blocks instead of duplicating their logic. `NewsRanker` should load structured JSON directly from a directory or explicit file paths using `load_structured_article()`, flatten facts with `flatten_fact_items()`, embed fact texts through an injected `FactEmbedder`, build a `FactUniverse`, build article vectors from unique covered clusters, compute the four score components, combine normalized components with profile weights, and return rank-ordered public result objects.

Input handling should be deliberately narrow but future-proof. Current accepted inputs should be `Path`/`str` directory, `Path`/`str` JSON file, a sequence of paths, or a sequence of already-loaded `StructuredArticle` objects. Directory inputs sort `*.json` for deterministic ordering; explicit sequences preserve caller order. Raw article dictionaries should raise a clear `NotImplementedError` or `TypeError` saying decomposition is not implemented yet. Keep this boundary in one private loader method so future `decompose(article) -> StructuredArticle` can be added there.

Use dataclasses for public result records to satisfy mypy strict mode without adding dependencies. Export `NewsRanker` and `RankerConfig` from `news_ranker/__init__.py` because this plan implements the brief's public API surface. Prefer explicit component keys `centrality`, `coverage`, `density`, and `entity_coverage`; `combine()` accepts those names already. For now `select()` returns the first `m` ranked entries and validates `1 <= m <= k`; future MMR can live behind the same method or delegate to a later `select.py`.

Rejected alternative: implement raw article dict input now with placeholder decomposition. That would either fake decomposition or require LLM/prompt choices not approved for this repo state. Rejected adding MMR now because brief section 4.9 is separate and existing context says selection/ranking should come later without drifting into diversity.

## Steps

1. **Add pipeline configuration defaults**
   - **Files touched**: `news_ranker/config.py`, `tests/test_pipeline.py`
   - **Change summary**: Add `RankerConfig` dataclass with `similarity_threshold`, `linkage`, `coverage_weighting`, and default profile weights for `representative`, `comprehensive`, and `concise`. Validate finite threshold, supported linkage/coverage mode, nonnegative profile weights, required component keys, and profile weights summing to `1.0` within a small tolerance. Do not configure a default embedder here; `NewsRanker` will require explicit embedder injection.
   - **Tests added or updated**: `tests/test_pipeline.py` asserts default profiles exist with expected keys, invalid profile names/weights fail config validation, and invalid linkage or coverage mode fails before ranking.
   - **Verification command**: `make check`

2. **Add structured-input loading boundary for article folders**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Add `NewsRanker` skeleton requiring an explicit `FactEmbedder` argument plus private input normalization that loads sorted `*.json` files from a directory, loads a single JSON file, preserves explicit path sequence order, accepts already-loaded `StructuredArticle` objects, rejects empty inputs, and rejects raw dict inputs with a clear decomposition-not-implemented error. This isolates current fixture-backed flow from future decomposition support and avoids surprise `SentenceTransformer` downloads.
   - **Tests added or updated**: `tests/test_pipeline.py` asserts constructor without an embedder fails clearly, `articles/trump-shooting/` loads five articles with derived path-like IDs, explicit reversed path sequences preserve reversed order, already-loaded articles pass through, empty directory/input fails, and raw article dict input reports decomposition is not implemented.
   - **Verification command**: `make check`

3. **Implement rank orchestration over existing modules**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Implement `NewsRanker.rank(articles, profile="representative")` using injected `FactEmbedder`, `embed_facts()`, `build_fact_universe()`, `embed_article_from_clusters()`, `centrality()`, `coverage()`, `density()`, `entity_coverage()`, and `combine()`. Return a `RankResult` with ranked entries sorted by descending score, stable tie-break by input order, per-entry component normalized scores, and diagnostics holding `FactUniverse`, component `ScoreVector`s, and article embeddings.
   - **Tests added or updated**: `tests/test_pipeline.py` uses a deterministic fake embedder to assert folder-backed rank returns five entries, ranks are `1..5`, IDs match loaded fixture IDs, scores/components are finite, fake embedder receives exactly `flatten_fact_items()` texts in order, unknown profile fails, and tie scores keep input order.
   - **Verification command**: `make check`

4. **Handle empty or partially empty fact extraction safely**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Add orchestration guards for no fact texts and for articles with no covered clusters. If no facts exist, skip embedder calls, build an empty fact universe with a 2-D empty `float32` array, mark centrality/coverage/density as undefined where appropriate, and let `combine()` renormalize away undefined weighted components. If only some articles cover no clusters, mark centrality undefined for the corpus rather than fabricating fallback embeddings.
   - **Tests added or updated**: `tests/test_pipeline.py` asserts all-empty structured articles do not call the embedder, rank returns finite scores, diagnostics show empty coverage, and a mixed empty/non-empty corpus produces finite scores with `centrality.defined is False`.
   - **Verification command**: `make check`

5. **Implement top-score selection API**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Implement `NewsRanker.select(articles, m, profile="representative")` by calling `rank()` and returning a `SelectionResult` whose `selected` list equals the first `m` ranked entries. Validate `m` is an integer and `1 <= m <= article_count`; keep selection-mode plumbing out until `select.py`/MMR is planned.
   - **Tests added or updated**: `tests/test_pipeline.py` asserts `select(..., m=2)` equals the first two IDs from `rank()`, invalid `m` values fail, and selected entries retain rank/score/component data.
   - **Verification command**: `make check`

6. **Implement profile comparison and package exports**
   - **Files touched**: `news_ranker/pipeline.py`, `news_ranker/__init__.py`, `tests/test_pipeline.py`, `tests/test_health.py`
   - **Change summary**: Implement `NewsRanker.compare_profiles(articles, profiles=None)` returning a `ProfileComparison` with one ranking per requested profile, defaulting to all configured profiles. Export `NewsRanker` and `RankerConfig` from `news_ranker.__init__` while preserving `health()`.
   - **Tests added or updated**: `tests/test_pipeline.py` asserts default comparison includes `representative`, `comprehensive`, and `concise`, explicit profile subsets work, unknown profiles fail, and comparison rankings use same article IDs. `tests/test_health.py` keeps existing health behavior and checks public imports if useful.
   - **Verification command**: `make check`

7. **Document implemented pipeline constraints**
   - **Files touched**: `docs/context/pipeline-public-api.md`
   - **Change summary**: Add context artifact describing fixture-backed public API, accepted inputs, result dataclasses, config defaults, diagnostics, fake-embedder testing constraint, no-decomposition boundary, and future hooks for `decompose.py` and `select.py`.
   - **Tests added or updated**: None; docs-only step.
   - **Verification command**: `make check`

## Risks

1. Public API shape becomes hard to change after export; result dataclass names and method signatures should be reviewed before implementation.
2. Default `SentenceTransformerEmbedder` can download model weights if caller does not inject an embedder; tests must always inject a fake embedder.
3. Directory-backed loading only handles already-structured JSON; callers expecting raw brief input dicts will fail until decomposition is implemented.
4. Centrality becomes undefined for corpora with empty-covered articles; ranking then relies on remaining components and may differ from future fallback-embedding behavior.
5. `compare_profiles()` may recompute embeddings if implemented naively; implementation should reuse one internal run where practical, but correctness matters more than optimization for this step.
6. Profile weights using `entity_coverage` may be renormalized away when entity extraction is empty, changing effective weights by corpus.

## Open questions

None. Decisions made: `NewsRanker.__init__` requires an explicit embedder, and public results use dataclasses with simple serializable ranking-entry fields (`id`, `score`, `rank`, `components`).

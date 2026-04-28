# Structured JSON Embedding Foundation

## Goal

Implement foundation from `docs/brief.md` sections 4.1 and 4.4 while skipping all LLM/prompt/decomposition work for now. Done means project can validate already-decomposed JSON files from `articles/trump-shooting/`, extract atomic fact texts, embed those texts through a `SentenceTransformer`-style embedder, and compute article vectors from supplied fact-cluster vectors without scraping, LLM calls, or external hosted API calls.

## Non-goals

- No `prompts.py`, prompt constant, prompt tests, or prompt-version work.
- No `decompose.py` LLM client, retry loop, or cache implementation.
- No hosted embedding provider or network API calls.
- No fact clustering implementation.
- No scoring, selection, pipeline orchestration, or public `NewsRanker` API.
- No changes to article fixture JSON files.

## Approach

Add strict Pydantic schemas matching actual JSON files under `articles/trump-shooting/`, not brief's illustrative schema. Entity objects use `{ "name": ..., "role": ... }`; top-level fields are `headline_neutral`, `topic`, `entities`, `events`, `claims`, and `context`. Keep fixture JSON unchanged and derive missing `article_id` from path-like IDs during load.

Skip prompt and LLM decomposition entirely. Current implementation path starts from already-decomposed JSON files in `articles/trump-shooting/`; future work can add LLM decomposition later but must either emit this fixture schema or include explicit adapter work.

Add embedding support in `news_ranker/embed.py` using the shape of the provided `SentenceTransformerEmbedder`: a class that owns a `SentenceTransformer` model and exposes `embed(texts: list[str]) -> NDArray[np.float32]`. Keep embedding calls local via `sentence-transformers`, not hosted APIs. `embed_facts()` should accept any object/protocol with an `embed()` method so tests can use a deterministic fake embedder and avoid model downloads.

Add `embed_article_from_clusters(article_id, coverage_matrix, cluster_vectors)` using section 4.4 semantics: mean only unique cluster vectors covered by target article. This should operate on numeric arrays, validate shape mismatches, and raise an explicit exception when an article covers no clusters. Runtime dependencies `pydantic`, `numpy`, and `sentence-transformers` are approved for this implementation.

## Steps

1. **Add runtime dependencies for schemas and local embeddings**
   - **Files touched**: `pyproject.toml`, `uv.lock`
   - **Change summary**: Add `pydantic`, `numpy`, `sentence-transformers`, and needed typing support if required. This enables strict models plus `NDArray[np.float32]` embeddings matching the requested `SentenceTransformerEmbedder` shape.
   - **Tests added or updated**: None; dependency-only step.
   - **Verification command**: `make check`

2. **Add structured schemas and fixture loader**
   - **Files touched**: `news_ranker/schemas.py`, `tests/test_schemas.py`
   - **Change summary**: Add strict `Entity`, `Entities`, `Event`, `Claim`, and `StructuredArticle` models that match actual article JSON files. `Entity` has `name` and `role`; `StructuredArticle` uses `headline_neutral` rather than `article_id` as required JSON field. Loader derives missing runtime `article_id` values from path-like IDs such as `trump-shooting/bbc`.
   - **Tests added or updated**: `tests/test_schemas.py` asserts all five `articles/trump-shooting/*.json` files validate as `StructuredArticle`; missing runtime article IDs derive from path-like IDs; extra unknown top-level fields are rejected; brief-style `canonical_name` entity objects are rejected.
   - **Verification command**: `make check`

3. **Add fact text extraction helpers**
   - **Files touched**: `news_ranker/schemas.py`, `tests/test_schemas.py`
   - **Change summary**: Add methods/properties or helper functions to return ordered fact texts from `events` and `claims` for embedding input. Keep event and claim IDs stable for diagnostics.
   - **Tests added or updated**: `tests/test_schemas.py` asserts each fixture article yields `len(events) + len(claims)` fact texts and preserves path-like article IDs derived from fixture paths or JSON when available.
   - **Verification command**: `make check`

4. **Add SentenceTransformer-style embedder abstraction and fact embedding helper**
   - **Files touched**: `news_ranker/embed.py`, `tests/test_embed.py`
   - **Change summary**: Add `SentenceTransformerEmbedder` with `__init__(model_name: str = "all-MiniLM-L6-v2")` and `embed(texts: list[str]) -> NDArray[np.float32]`, modeled after provided snippet. Add `embed_facts(facts, embedder)` that accepts an injected embedder/protocol, validates empty input, dtype, finite values, and 2-D shape.
   - **Tests added or updated**: `tests/test_embed.py` uses a deterministic fake embedder to assert output shape, `np.float32` dtype, empty input behavior, and invalid output errors. Tests should not instantiate real `SentenceTransformer` or download models.
   - **Verification command**: `make check`

5. **Add article vector construction from coverage and cluster vectors**
   - **Files touched**: `news_ranker/embed.py`, `tests/test_embed.py`
   - **Change summary**: Implement `embed_article_from_clusters(article_id, article_ids, coverage_matrix, cluster_vectors)` as mean of covered unique cluster vectors using `numpy`. Validate article IDs, coverage matrix shape, cluster vector shape, and raise explicit exception when target article covers no clusters.
   - **Tests added or updated**: `tests/test_embed.py` asserts duplicate coverage cannot overweight facts, mean vector math is correct, unknown article ID errors, shape mismatch errors, and no-covered-cluster case raises explicit exception.
   - **Verification command**: `make check`

6. **Document fixture-based flow for skipped LLM work**
   - **Files touched**: `docs/context/structured-json-embedding-foundation.md`
   - **Change summary**: Add context artifact describing current JSON fixture schema as source of truth, skipped prompt/decomposition work, implemented modules, and constraints. Note future `decompose.py` must produce or adapt to same `StructuredArticle` schema.
   - **Tests added or updated**: None; docs-only step.
   - **Verification command**: `make check`

## Risks

1. Future LLM decomposition may emit brief-style schema rather than fixture schema; adapter or prompt updates will be needed then.
2. `sentence-transformers` is heavy and may slow installs or fail in constrained environments.
3. Real `SentenceTransformer` model construction can download models; tests must avoid it with fake embedders.
4. Article IDs are absent in fixture JSON; deriving path-like IDs from fixture paths is deterministic but not part of JSON contract.
5. Explicit exceptions for articles with no covered clusters make failures visible but require callers to handle invalid upstream extraction/cluster state.

## Open questions

None.

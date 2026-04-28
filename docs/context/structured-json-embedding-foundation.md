# Structured JSON Embedding Foundation Context

## Current source of truth

Fixture JSON under `articles/trump-shooting/` is current schema source of truth for this foundation. Files are already-decomposed article representations, not raw article inputs and not LLM outputs generated in this implementation.

Validated fixture shape:

- top-level fields: `headline_neutral`, `topic`, `entities`, `events`, `claims`, `context`
- optional runtime field: `article_id`
- `entities`: `people`, `organizations`, `locations`
- entity object: `name`, `role`
- event object: `id`, `when`, `who`, `what`, `where`, `why`, `how`, `depends_on`
- claim object: `id`, `statement`, `type`, `attributed_to`

Fixture files omit `article_id`. `load_structured_article()` derives path-like IDs from file paths, e.g. `articles/trump-shooting/bbc.json` becomes `trump-shooting/bbc`. If JSON includes `article_id`, loader preserves it unless caller explicitly overrides it.

## Implemented modules

`news_ranker/schemas.py` contains strict Pydantic models for fixture-compatible structured articles:

- `Entity`
- `Entities`
- `Event`
- `Claim`
- `StructuredArticle`
- `derive_article_id()`
- `load_structured_article()`

Strict validation rejects unknown fields and rejects brief-style entity objects such as `canonical_name`.

`StructuredArticle.fact_texts` returns event fact texts followed by claim statements. `StructuredArticle.fact_items` returns stable `(fact_id, text)` pairs in same order for diagnostics.

`news_ranker/embed.py` contains local embedding helpers:

- `FactEmbedder` protocol for injected embedders
- `SentenceTransformerEmbedder`, wrapping local `sentence_transformers.SentenceTransformer`
- `embed_facts()`, validating non-empty input, 2-D `float32` output, and finite values
- `embed_article_from_clusters()`, averaging unique cluster vectors covered by target article

Article-vector construction treats any nonzero coverage entry as covered once, so duplicate coverage values cannot overweight repeated facts.

## Skipped work in this foundation

Prompt and LLM decomposition work is intentionally skipped. No `prompts.py`, `decompose.py`, prompt versioning, retry loop, decomposition cache, scraping, hosted embedding API, fact clustering, scoring, selection, or pipeline orchestration exists in this step sequence.

Tests use deterministic fake embedders and must not instantiate real `SentenceTransformer` models or download model weights.

## Constraints for future work

Future `decompose.py` must produce JSON matching `StructuredArticle` or include an explicit adapter from any alternate LLM/brief-style schema to this fixture schema. In particular, future decomposition cannot emit only `canonical_name` entity objects without adapter work because current strict models expect `name` and `role`.

Future clustering should consume fact texts or fact items from `StructuredArticle`, generate cluster vectors, and build coverage matrices compatible with `embed_article_from_clusters(article_id, article_ids, coverage_matrix, cluster_vectors)`.

Keep fixture JSON unchanged unless a later plan explicitly approves fixture migration.

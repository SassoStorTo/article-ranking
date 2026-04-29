# Structured JSON Decomposition Plan

## Goal

Implement brief §§4.1–4.3 against current `articles/` JSON shape. Done means callers can validate fixture-compatible structured article JSON, use one schema-matched decomposition prompt, call a provider-agnostic `decompose(...)` flow that parses LLM JSON, validates `StructuredArticle`, retries once on malformed output, caches successful decompositions by article content plus prompt/schema/model versions, and optionally let `NewsRanker` decompose raw article dicts via injected decomposer.

## Non-goals

- No fixture migration under `articles/`.
- No brief-style `canonical_name` entity schema; current `name`/`role` stays source of truth.
- No scraping, URL retrieval, URL deduplication, or external fact-checking.
- No new LLM SDK dependency; decomposition uses injected client/protocol only.
- No hosted embedding changes.
- No full ranking/scoring behavior changes.
- No mandatory raw-dict pipeline integration; raw dict support must require explicit injected decomposer/client.

## Approach

Keep existing strict Pydantic schema, but align scalar nullability and claim typing with prompt rules while preserving current fixtures. Current article JSON uses top-level `headline_neutral`, `topic`, `entities`, `events`, `claims`, `context`; entities use `name` and `role`; events and claims use current IDs. Plan rejects brief sample entity shape (`canonical_name`, extra entity groups) because context names fixture JSON as schema source of truth.

Add prompt module with one current-schema system prompt. Improve user-provided prompt only where needed: say entities use `name`/`role`, allow `null` for unknown scalar values, keep exact top-level keys, forbid extra keys, preserve JSON-only output, and retain atomicity/neutrality/attribution/no-inference rules. Prompt version constant lives beside prompt so cache keys can change when prompt changes.

Add provider-agnostic decomposition module. Instead of importing Anthropic/OpenAI, define small protocol for injected clients, parse returned text as JSON, validate with `StructuredArticle`, and retry once with parse/validation error. Cache successful normalized JSON under `cache_dir/decompositions/` using hash of normalized article input plus prompt version, schema version, and model name. Tradeoff: no batteries-included provider yet, but tests stay deterministic and repo avoids unapproved dependency/provider choice.

Wire raw article dictionaries into `NewsRanker` only when caller injects a decomposer/client. Without one, existing `NotImplementedError` remains. This keeps structured fixture ranking stable while enabling end-to-end raw-dict workflows for callers who opt in.

Considered migrating schemas to brief sample with `canonical_name`, aliases, entity event/other groups. Rejected because current fixtures/tests/context explicitly make `articles/` JSON source of truth and strict validation intentionally rejects `canonical_name`.

## Steps

1. **Schema alignment for current JSON + prompt nulls**
   - **Files touched**: `news_ranker/schemas.py`, `tests/test_schemas.py`
   - **Change summary**: Keep current fixture schema and strict `extra="forbid"`. Add `Literal["fact", "quote", "estimate", "prediction"]` for `Claim.type`; allow `None` for unknown scalar fields emitted by prompt where needed (`Entity.role`, `Event.when`, `Claim.attributed_to`) without changing fixture JSON.
   - **Tests added or updated**: `tests/test_schemas.py` asserts all `articles/trump-shooting/*.json` still validate; `canonical_name` entities still fail; invalid claim type fails; prompt-compatible null scalars validate; unknown fields still fail.
   - **Verification command**: `uv run pytest tests/test_schemas.py`

2. **Current-schema decomposition prompt**
   - **Files touched**: `news_ranker/prompts.py`, `tests/test_prompts.py`
   - **Change summary**: Add `DECOMPOSITION_PROMPT_VERSION`, `DECOMPOSITION_SYSTEM_PROMPT`, and `build_decomposition_user_prompt(article)`. Prompt requires exact current top-level keys, `entities.people/organizations/locations`, entity objects with `name`/`role`, event/claim shapes from fixtures, JSON only, atomic facts, neutral wording, chronology, attribution, canonical names, no inference, and empty schema for empty article body.
   - **Tests added or updated**: `tests/test_prompts.py` asserts prompt mentions required keys/shapes, does not mention `canonical_name`, forbids prose/markdown/extra keys, and user-prompt builder includes `id`, `title`, `body`, and optional metadata without requiring URLs to be fetched.
   - **Verification command**: `uv run pytest tests/test_prompts.py`

3. **Provider-agnostic decomposition + retry + cache**
   - **Files touched**: `news_ranker/decompose.py`, `tests/test_decompose.py`
   - **Change summary**: Add `DecompositionClient` protocol and `decompose(article, client, config=None, cache_dir=None) -> StructuredArticle`. Validate input has usable `id`, `title`, and `body`; call injected client with system/user prompts and configured model; strip no prose beyond JSON parsing; retry once on `JSONDecodeError` or `ValidationError`; write/read cached validated JSON keyed by normalized article payload, prompt version, schema version, and model name.
   - **Tests added or updated**: `tests/test_decompose.py` uses fake clients to assert successful validation, `article_id` comes from input id, invalid JSON retries once, schema validation retries once with error context, final bad output raises deterministic exception, cache hit bypasses client, cache key changes when prompt/schema/model version changes, and no network/model download occurs.
   - **Verification command**: `uv run pytest tests/test_decompose.py`

4. **Optional raw-dict decomposition in `NewsRanker`**
   - **Files touched**: `news_ranker/pipeline.py`, `tests/test_pipeline.py`
   - **Change summary**: Extend `NewsRanker` constructor with optional decomposer dependency while preserving existing embedder/config call patterns. When `_load_structured_articles()` sees raw dicts and decomposer exists, convert each dict to `StructuredArticle`; when no decomposer exists, keep current `NotImplementedError`.
   - **Tests added or updated**: `tests/test_pipeline.py` asserts raw dicts decompose through fake decomposer, mixed raw dict/path/object input preserves order, decomposed article IDs are used, decomposer exceptions propagate, and no-decomposer raw dict behavior remains unchanged.
   - **Verification command**: `uv run pytest tests/test_pipeline.py`

5. **Package exports and compatibility checks**
   - **Files touched**: `news_ranker/__init__.py`, `tests/test_health.py`
   - **Change summary**: Export decomposition entry points and protocols only if import-safe without provider dependencies. Keep package import light; no LLM SDK import at import time.
   - **Tests added or updated**: `tests/test_health.py` or a small import test asserts `from news_ranker import decompose` or chosen export works without LLM SDK installed.
   - **Verification command**: `uv run pytest tests/test_health.py`

6. **Full project verification**
   - **Files touched**: none expected beyond prior steps
   - **Change summary**: Run full quality gate and inspect diff. If implementation diverges, update context artifact before marking done.
   - **Tests added or updated**: none; relies on full suite, lint, typecheck, build.
   - **Verification command**: `make check`

## Risks

1. Broader nullability can hide weak LLM extraction if downstream code assumes strings. Tests must cover `fact_text` formatting with `None` values.
2. Strict schema plus LLM output can cause frequent retries if prompt drifts or model adds extra keys.
3. Cache key normalization bugs can reuse stale decompositions after prompt/schema/model changes.
4. Provider protocol may not match future Anthropic/OpenAI wrapper ergonomics, requiring adapter work.
5. Optional decomposer injection can complicate `NewsRanker` constructor compatibility; tests must preserve existing positional `NewsRanker(FakeEmbedder(), config=...)` usage.
6. Raw dict decomposition inside ranking can make ranking slow and cache-sensitive if caller forgets `cache_dir`.

## Open questions

None.

# Mistral LLM Provider Plan

## Goal

Add Mistral as supported LLM provider for raw-article decomposition. Done means project declares `mistralai`, decomposition/model defaults use Mistral model naming, caller can instantiate `MistralDecompositionClient`, pass it to existing `decompose()`, then use that through existing `NewsRanker(..., decomposer=...)` raw-dict hook, without changing ranking output shapes or requiring network/provider calls in tests.

## Non-goals

- No top-level `news_ranker.__all__` export change; Mistral stays submodule-only.
- No automatic provider construction inside `NewsRanker`.
- No embedding provider changes.
- No scraping, URL fetching, URL deduplication, external fact-checking, or multilingual handling changes.
- No async public decomposition API.
- No provider usage/billing tracking.

## Approach

Add `mistralai` as a project dependency because user approved dependency addition. Keep provider behavior behind explicit injection: `MistralDecompositionClient` implements existing `DecompositionClient.complete(model, system_prompt, user_prompt) -> str`; callers still choose when to create provider client and when to wire it into `decompose()` or `NewsRanker(..., decomposer=...)`.

Align defaults with Mistral by changing `RankerConfig.llm_model_name` and `DEFAULT_DECOMPOSITION_MODEL` to `"mistral-small-latest"`. This makes config/decomposition metadata coherent, but does not make `NewsRanker` create providers or call network. Existing fake-client tests should remain fake-client tests.

Create new submodule `news_ranker/mistral.py`. It reads `MISTRAL_API_KEY` when `api_key` is omitted, calls Mistral sync chat completion, and returns response message text. Keep parsing, schema validation, retry, cache keys, prompt versions, and runtime article-ID handling inside existing `decompose()`. Mistral adapter should not parse JSON or validate schema; it only translates protocol calls into Mistral chat calls. Include small response-content normalization for SDK content variants: string content, chunk lists with `.text`, and clear empty/missing content errors.

Use plain role/content message dicts instead of `mistralai.models.SystemMessage`/`UserMessage`. Inspiration file notes SDK API/version fragility around typed message imports; dict messages reduce coupling. Use import pattern that keeps tests fakeable and avoids real provider calls.

Rejected alternatives: exporting provider at package root (widens tested public surface), wiring `RankerConfig.llm_model_name` automatically into `NewsRanker` (changes constructor behavior/API boundary), replacing injected decomposer path with provider-specific pipeline logic, or keeping Claude/default model names after adding Mistral provider (would make docs/config misleading).

## Steps

1. **Add Mistral dependency and align default model names**
   - **Files touched**: `pyproject.toml`, `uv.lock`, `news_ranker/config.py`, `news_ranker/decompose.py`, `tests/test_config.py`, `tests/test_decompose.py`
   - **Change summary**: Add `mistralai` to project dependencies via uv. Change `RankerConfig.llm_model_name` and `DEFAULT_DECOMPOSITION_MODEL` to `"mistral-small-latest"`; keep prompt/schema/cache behavior unchanged.
   - **Tests added or updated**: `tests/test_config.py` asserts default `llm_model_name == "mistral-small-latest"`. `tests/test_decompose.py` adds/updates default-model assertion using fake client so no network is called.
   - **Verification command**: `uv run pytest tests/test_config.py tests/test_decompose.py`

2. **Add low-level Mistral decomposition client**
   - **Files touched**: `news_ranker/mistral.py`, `tests/test_mistral.py`
   - **Change summary**: Add `DEFAULT_MISTRAL_MODEL = "mistral-small-latest"` and `MistralDecompositionClient` implementing `DecompositionClient.complete()`. Resolve API key from explicit arg or `MISTRAL_API_KEY`, call sync `client.chat.complete(...)`, and extract response text deterministically.
   - **Tests added or updated**: `tests/test_mistral.py` asserts missing API key raises `ValueError`, fake Mistral client receives requested model/system/user messages, and string plus chunk-list response content converts to returned text. Tests monkeypatch/fake SDK boundary and never call network.
   - **Verification command**: `uv run pytest tests/test_mistral.py`

3. **Verify Mistral client composes with existing decomposition flow**
   - **Files touched**: `tests/test_mistral.py`
   - **Change summary**: Add integration-style tests using fake Mistral SDK response containing valid current-schema JSON. Call existing `decompose()` with `MistralDecompositionClient` and default or explicit Mistral `DecompositionConfig`.
   - **Tests added or updated**: `tests/test_mistral.py` asserts `decompose()` sets raw article ID, forwards Mistral model through client, uses existing prompt/schema validation, and cache hit bypasses second fake provider call when `cache_dir` is supplied.
   - **Verification command**: `uv run pytest tests/test_mistral.py tests/test_decompose.py`

4. **Document provider usage and lock import boundary**
   - **Files touched**: `README.md`, `tests/test_health.py`
   - **Change summary**: Add short Mistral decomposition example showing `MistralDecompositionClient`, `DecompositionConfig(model="mistral-small-latest")`, optional `cache_dir`, and `NewsRanker(..., decomposer=lambda article: decompose(...))`. Clarify `RankerConfig` defaults name Mistral model but still do not auto-create providers; caller must inject Mistral client/decomposer explicitly.
   - **Tests added or updated**: `tests/test_health.py` asserts no `MistralDecompositionClient` attribute exists on package root, `news_ranker.__all__` stays unchanged, and submodule import works.
   - **Verification command**: `uv run pytest tests/test_health.py tests/test_decompose.py tests/test_mistral.py`

5. **Run full project verification**
   - **Files touched**: none beyond prior steps
   - **Change summary**: Validate formatting, lint, typecheck, tests, and build after dependency/default/provider/doc changes.
   - **Tests added or updated**: None.
   - **Verification command**: `make check`

## Risks

1. Mistral Python SDK sync API may differ by version; implementation must match uv-resolved dependency and fake tests should model that API.
2. New required dependency increases install footprint and may affect build/lock resolution.
3. Changing `DEFAULT_DECOMPOSITION_MODEL` and `RankerConfig.llm_model_name` from prior values is a backward-compatible metadata/default shift for most callers, but fake/provider tests or downstream code asserting old strings may need updates.
4. Hosted provider calls are networked and blocking; current sync protocol gives no cancellation/timeout knob.
5. Response content shapes may vary across SDK versions; extraction helper must fail clearly on empty or unknown content.
6. Provider output may include markdown fences or invalid JSON; existing `decompose()` retry handles this, but adapter should not silently alter schema semantics.
7. Cache keys depend on supplied `DecompositionConfig.model`; default model change intentionally invalidates old default-model cache entries.

## Open questions

None.

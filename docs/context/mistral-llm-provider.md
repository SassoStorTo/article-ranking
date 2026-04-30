# Mistral LLM Provider Context

## Scope

This context covers Mistral as the current provider-specific LLM adapter for raw-article decomposition: dependency declaration, default model naming, `MistralDecompositionClient`, response text normalization, fake-provider tests, README usage, and how callers wire it through existing `decompose()` and `NewsRanker(..., decomposer=...)`. It deliberately does not cover changing structured schema, prompt wording, JSON parsing/retry/cache semantics, ranking/scoring output shapes, embedding providers, scraping, URL deduplication, external fact-checking, async provider APIs, or automatic provider construction inside `NewsRanker`.

## Key files

### Provider and decomposition boundary

- `news_ranker/mistral.py` — Mistral SDK adapter implementing the existing decomposition client protocol and extracting text from SDK responses.
- `news_ranker/decompose.py` — provider-agnostic decomposition flow; default model is `"mistral-small-latest"`, but provider calls still happen only through injected clients.
- `news_ranker/prompts.py` — system/user prompt constants passed unchanged through the Mistral adapter.
- `news_ranker/schemas.py` — strict `StructuredArticle` schema validated by `decompose()` after provider output.
- `news_ranker/pipeline.py` — raw dictionary input hook accepts caller-supplied decomposer callable; it does not know about Mistral.
- `news_ranker/__init__.py` — top-level exports include generic decomposition API but do not export `MistralDecompositionClient`.

### Config, packaging, docs

- `news_ranker/config.py` — `RankerConfig.llm_model_name` default is `"mistral-small-latest"`; it remains metadata and does not construct clients.
- `pyproject.toml` — declares runtime dependency `mistralai>=2.4.4`.
- `uv.lock` — resolves `mistralai==2.4.4` plus transitive dependencies such as `httpx`, `pydantic`, `opentelemetry-api`, and `typing-inspection`.
- `README.md` — documents explicit Mistral client construction, `MISTRAL_API_KEY`, optional `DecompositionConfig`, optional cache dir, and `NewsRanker` decomposer wiring.
- `docs/plans/mistral-llm-provider.md` — completed implementation plan for this provider.

### Tests

- `tests/test_mistral.py` — fake SDK boundary tests for API-key resolution, message payloads, response text extraction, error messages, `decompose()` integration, model forwarding, and cache hit behavior.
- `tests/test_decompose.py` — fake generic client tests locking default decomposition model and provider-agnostic retry/cache behavior.
- `tests/test_config.py` — locks `RankerConfig.llm_model_name == "mistral-small-latest"`.
- `tests/test_health.py` — locks submodule-only Mistral import and unchanged `news_ranker.__all__`.
- `tests/test_pipeline.py` — locks injected raw-dict decomposer hook used by README Mistral wiring.

## Data flow / control flow

1. Packaging makes Mistral available via `mistralai>=2.4.4`; lock resolves `mistralai==2.4.4`.
2. Caller imports `MistralDecompositionClient` from `news_ranker.mistral`, not from package root.
3. Client construction resolves credentials from explicit `api_key` or `MISTRAL_API_KEY`. If no fake `client` is supplied and no key exists, constructor raises `ValueError("MISTRAL_API_KEY is required")`. Supplying a fake `client` bypasses SDK construction and API-key requirement in tests.
4. `MistralDecompositionClient.complete(model=..., system_prompt=..., user_prompt=...)` builds two plain dict messages: `{"role": "system", "content": system_prompt}` and `{"role": "user", "content": user_prompt}`. It calls `self._client.chat.complete(model=model, messages=...)` synchronously.
5. `_response_text()` reads `response.choices[0].message.content`. String content is returned if non-empty. List content is joined from chunk `.text` attrs that are strings. Missing choices/message, empty string content, unsupported content, or chunk lists without text raise clear `ValueError` messages.
6. `decompose(article, client, config=None, cache_dir=None)` remains provider-agnostic. With no config, it uses `DecompositionConfig(model="mistral-small-latest")`; tests assert that model reaches injected client. `decompose()` still validates raw article ID/title/body before provider call, builds prompts, parses JSON, validates `StructuredArticle`, retries once on parse/validation errors, writes cache, and overwrites runtime `article_id` from raw input.
7. Cache keys include raw article payload, model, prompt version, and schema version. Default model change means default cache keys now include `"mistral-small-latest"`.
8. `NewsRanker` has no provider-specific path. Caller wires Mistral through `decomposer=lambda article: decompose(article, client, config=config, cache_dir=cache_dir)`. Raw dicts without any decomposer still raise `NotImplementedError`; raw dicts with decomposer use returned `StructuredArticle` IDs in ranking.
9. Package root export boundary stays unchanged: generic decomposition API is root-exported, `MistralDecompositionClient` remains submodule-only.

## Conventions observed

- Provider adapters implement the minimal `DecompositionClient.complete(*, model, system_prompt, user_prompt) -> str` protocol; adapters do not parse JSON or validate schemas.
- Provider behavior uses explicit dependency injection. `RankerConfig.llm_model_name` and `DEFAULT_DECOMPOSITION_MODEL` name Mistral defaults, but neither `RankerConfig` nor `NewsRanker` constructs a provider.
- Tests fake the SDK boundary with objects exposing `.chat.complete(...)`; no tests call network or require real Mistral credentials.
- SDK messages are plain role/content dicts, not imported typed Mistral message classes.
- Mistral response handling is intentionally narrow and deterministic: non-empty string content or list chunks with `.text`; other shapes raise `ValueError`.
- Error tests assert exact key substrings such as `"MISTRAL_API_KEY is required"`, `"Mistral response missing choices"`, and `"Mistral response content is missing or unsupported"`.
- Public API tests compare `news_ranker.__all__` list exactly; adding root exports requires updating tests and context.
- README examples require caller-provided `embedder`; Mistral only handles decomposition, not fact embeddings.

## Open questions

1. No repo test calls the real Mistral SDK or provider, so live compatibility of `from mistralai.client import Mistral` and `client.chat.complete(...)` is not verified by local tests.
2. No timeout, retry, cancellation, usage accounting, or provider error wrapping is exposed by `MistralDecompositionClient`.
3. Response extraction supports strings and `.text` chunk lists only; other Mistral SDK content variants are not documented in repo.
4. `DEFAULT_MISTRAL_MODEL`, `DEFAULT_DECOMPOSITION_MODEL`, and `RankerConfig.llm_model_name` all repeat `"mistral-small-latest"`; no shared constant ties them together.

## Suggested next step

Plan session should focus on deciding whether to verify/lock real Mistral SDK API compatibility and provider error handling while preserving explicit injection and current root export boundary.

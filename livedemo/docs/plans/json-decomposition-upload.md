# JSON Decomposition Upload Plan

## Goal

Users can upload precomputed decomposition `.json` files into livedemo article sets through same article upload flow used for `.txt` files. Valid JSON is schema-validated, persisted as `structured_article`, skips Mistral decomposition, appears in article detail, and works with rank/select/compare executions. Existing `.txt` upload + decomposition path stays unchanged.

## Non-goals

- No DB schema changes or migrations.
- No new deps.
- No changes to `news_ranker` public APIs or schemas.
- No scraping, URL ingestion, URL dedupe, external fact-checking, or multilingual handling.
- No support for arbitrary JSON shapes beyond `news_ranker.schemas.StructuredArticle`.
- No bulk edit/delete UX beyond existing article delete.

## Approach

Use extension-based detection in existing `POST /api/corpora/{corpus_id}/articles` multipart endpoint. `.txt` keeps current behavior: create `Article`, schedule background decomposition. `.json` follows new path: decode UTF-8, parse/validate with `news_ranker.schemas.StructuredArticle`, create an `Article` row, then persist matching `StructuredArticle` row with current `RankerConfig` LLM metadata. This keeps downstream code unchanged because executions already read `latest_structured_article()` before calling Mistral.

Store raw JSON text in `Article.body` so detail view still has an inspectable source artifact. Derive JSON-upload article title from both `headline_neutral` and filename so users always see source context plus decomposition headline. Force persisted payload `article_id` to DB article id after article flush, ignoring/mending uploaded `article_id`; this preserves ranker expectations and avoids user-visible ID mismatch. Invalid JSON/schema errors become `422` with filename + missing/malformed field info.

Rejected separate `/structured-articles` upload endpoint: execution model needs `Article` rows per corpus, and adding a second API path would duplicate filename, title, deletion, and UI selection behavior. Rejected explicit upload mode selector for backend: file extension is enough, simpler for mixed multipart uploads, and acceptance criteria allow it. Frontend can still show copy making modes explicit.

## Steps

1. **Backend JSON upload service**
   - **Files touched**: `livedemo/app/services/ingestion.py`, `livedemo/app/services/decomposition.py`, `livedemo/app/routers/articles.py`, `livedemo/tests/test_corpus_articles.py`, `livedemo/tests/test_decomposition.py`
   - **Change summary**: Extend ingestion to classify `.txt` vs `.json`. For JSON uploads, decode UTF-8, validate against `news_ranker.schemas.StructuredArticle`, create `Article` rows, persist `structured_article` rows with current ranker decomposition metadata, and return same `ArticleUploadResponse`; only `.txt` articles get background decomposition tasks.
   - **Tests added or updated**: Add `upload_json()` helper in `livedemo/tests/test_corpus_articles.py`. Add tests asserting valid JSON upload creates article detail with `decomposition_status == "decomposed"`, payload `article_id` equals DB article id, title includes both `headline_neutral` and filename, duplicate JSON filenames conflict, malformed JSON returns `422`, schema-missing fields return actionable `422`, and `.txt` behavior still passes existing tests.
   - **Verification command**: `cd livedemo && uv run pytest tests/test_corpus_articles.py tests/test_decomposition.py`

2. **Execution convergence + Mistral skip coverage**
   - **Files touched**: `livedemo/tests/test_executions.py`, `livedemo/tests/test_decomposition.py`
   - **Change summary**: Add integration coverage proving corpora built from JSON decompositions run through rank/select/compare without invoking fake Mistral. Keep `pipeline_runner._load_structured_corpus()` unchanged unless tests expose an article-id normalization gap.
   - **Tests added or updated**: Add JSON corpus fixture with two valid decompositions. Assert upload and execution leave `fake_decomposition_client.calls` empty, rank execution succeeds, result entries reference DB article ids, and mixed `.txt` + `.json` corpus decomposes only `.txt` article.
   - **Verification command**: `cd livedemo && uv run pytest tests/test_decomposition.py tests/test_executions.py`

3. **Frontend upload affordance**
   - **Files touched**: `livedemo/frontend/src/api/client.ts`, `livedemo/frontend/src/pages/ArticleManagementPage.tsx`, `livedemo/frontend/src/components/ArticleList.tsx`, `livedemo/frontend/src/components/ArticleBody.tsx`, `livedemo/frontend/src/styles.css`
   - **Change summary**: Let article upload input accept `.txt` and `.json`; update copy to explain `.json` skips decomposition and recommend one upload mode per batch. Keep same `uploadArticles()` API helper. Add UI labels/status text so precomputed decompositions are recognizable through existing decomposed status and structured panel.
   - **Tests added or updated**: No frontend test harness exists. Rely on TypeScript build; backend API tests cover upload behavior.
   - **Verification command**: `cd livedemo/frontend && npm run build`

4. **Validation/error polish**
   - **Files touched**: `livedemo/app/services/ingestion.py`, `livedemo/app/routers/articles.py`, `livedemo/tests/test_corpus_articles.py`, `livedemo/tests/test_decomposition.py`
   - **Change summary**: Normalize user-facing errors for unsupported file types, bad UTF-8, invalid JSON syntax, and Pydantic schema failures. Ensure responses include filename and specific missing/malformed field path where available.
   - **Tests added or updated**: Assert `.md` remains unsupported, non-UTF-8 `.json` returns filename-specific decode error, invalid claim type mentions field path/type, and missing `entities` mentions missing field.
   - **Verification command**: `cd livedemo && uv run pytest tests/test_corpus_articles.py tests/test_decomposition.py`

5. **Full verification**
   - **Files touched**: none expected beyond prior steps
   - **Change summary**: Run full livedemo backend tests, frontend build, then parent project check per repo convention. Fix only issues caused by this feature.
   - **Tests added or updated**: No new tests beyond prior steps; this step verifies integration across existing suite.
   - **Verification command**: `cd livedemo && uv run pytest && cd frontend && npm run build && cd ../.. && make check`

6. **Context artifact review/update**
   - **Files touched**: `livedemo/docs/context/mistral-decomposition-persistence.md`, `livedemo/docs/context/corpus-article-crud.md`, `livedemo/docs/context/execution-result-serialization.md` if stale
   - **Change summary**: Review `livedemo/docs/context` after implementation and update only context artifacts whose current behavior descriptions changed: upload now accepts `.json`, JSON uploads persist structured decompositions immediately, executions skip Mistral when structured payload exists.
   - **Tests added or updated**: None; docs/context only.
   - **Verification command**: `git diff -- livedemo/docs/context`

## Risks

1. JSON upload needs an `Article.id` before persisted payload can carry correct `article_id`; flush/order bugs could leave mismatched IDs.
2. Current `create_articles()` commits atomically for all uploads; adding structured persistence must avoid partial commits when later file in same request fails.
3. Mixed `.txt`/`.json` uploads can accidentally schedule decomposition for JSON rows if upload result tracking is too coarse.
4. Pydantic strict schema rejects common external-system coercions; good for safety, but users may need to fix JSON types exactly.
5. Raw JSON stored in `Article.body` may be large/noisy in article body panel, but avoids schema change.
6. Uploaded `article_id` from external systems is overwritten to DB id; external benchmark tooling must map filenames or returned IDs.

## Open questions

- None.

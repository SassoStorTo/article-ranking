# Corpus Article Workspace Plan

## Goal

Merge article upload, article browsing, article inspection, and article deletion into corpus workspace so users manage one article set from `/corpora`. Done means top nav no longer exposes separate Articles page, selected corpus detail includes Add articles upload action reusing existing `.txt`/`.json` behavior, article detail URLs are nested under corpus routes (`/corpora/:corpusId/article/:articleId`), and legacy `/articles` paths do not strand users outside corpus workspace.

## Non-goals

- No backend upload, article detail, decomposition, or deletion API shape changes.
- No database schema changes or migrations.
- No new frontend dependencies or router library.
- No scraping, URL ingestion, URL dedupe, auth, or sharing work.
- No ranking, execution, replay, evaluation, or provider behavior changes.
- No frontend test harness setup.

## Approach

Keep existing FastAPI endpoints and client functions. Issue is UX/routing fragmentation, not API capability: upload already posts to `/api/corpora/{id}/articles`, detail/delete/decompose already work through `/api/articles/{id}`. Move upload mutation and delete-enabled article inspector into `CorpusPanel`, then remove duplicate article-management page from top-level composition.

Represent article selection as corpus workspace state: `AppRoute` for `corpora` carries optional `articleId`, and `pathForRoute` emits `/corpora/:corpusId/article/:articleId` when both ids exist. `CorpusPanel` still receives callbacks from `App`, preserving centralized route/selection ownership. Direct nested article URLs should verify article membership with `getArticle`; if id is missing or belongs to another corpus, replace URL with safe corpus workspace route instead of rendering mismatched state.

Reject adding React Router. Current local History API layer is enough, avoids dependency churn, and already owns direct-load/back-forward semantics. Also reject backend nested article endpoints for now: frontend URL nesting solves user-facing issue without duplicating API routes. Tradeoff: API URLs remain `/api/articles/:id`, but user browser URLs become corpus-scoped.

## Steps

1. **Add upload flow to corpus detail workspace**
   - **Files touched**: `livedemo/frontend/src/pages/CorpusPanel.tsx`, `livedemo/frontend/src/styles.css`
   - **Change summary**: Move existing upload mutation behavior from article management into `CorpusPanel`: file input accepts `.txt,.json,text/plain,application/json`, calls `uploadArticles(corpusId, files)`, clears input, invalidates `['corpora']` and `['corpus', corpusId]`, and shows pending/error state near corpus header. Keep execution controls and article list behavior unchanged.
   - **Tests added or updated**: None — no frontend test harness exists; build verifies imports, props, and mutation types.
   - **Verification command**: `cd livedemo/frontend && npm run build`

2. **Enable full article management inside corpus detail**
   - **Files touched**: `livedemo/frontend/src/pages/CorpusPanel.tsx`, `livedemo/frontend/src/components/ArticleBody.tsx`
   - **Change summary**: Pass an `onDeleted` callback from `CorpusPanel` into `ArticleBody` so Delete Article appears in corpus workspace and clears selected article after success. Invalidate `['corpora']`, `['corpus', corpusId]`, and selected article query after delete; keep decompose behavior unchanged.
   - **Tests added or updated**: None — no frontend test harness exists; existing backend deletion coverage remains in `livedemo/tests/test_corpus_articles.py`.
   - **Verification command**: `cd livedemo/frontend && npm run build && cd ../.. && uv run --project livedemo pytest livedemo/tests/test_corpus_articles.py`

3. **Move article detail URLs under corpus routes**
   - **Files touched**: `livedemo/frontend/src/app/navigation.ts`, `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/pages/CorpusPanel.tsx`
   - **Change summary**: Extend corpus route shape with optional `articleId`; emit and parse `/corpora/:corpusId/article/:articleId`. Update article selection in corpus workspace to navigate to nested corpus article URL and article deselection to `/corpora/:corpusId`.
   - **Tests added or updated**: None — no frontend test harness exists; TypeScript build validates route union changes.
   - **Verification command**: `cd livedemo/frontend && npm run build`

4. **Remove top-level Articles navigation and redirect legacy article paths**
   - **Files touched**: `livedemo/frontend/src/components/TopNavigation.tsx`, `livedemo/frontend/src/app/navigation.ts`, `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/pages/ArticleManagementPage.tsx`
   - **Change summary**: Remove Articles button from top nav and stop rendering `ArticleManagementPage`. Map `/articles` to `/corpora` with `replaceState`; for `/articles/:articleId`, resolve article with `getArticle`, then replace with `/corpora/:corpusId/article/:articleId` or `/corpora` on failure. Delete `ArticleManagementPage.tsx` only after no imports remain.
   - **Tests added or updated**: None — no frontend test harness exists; build catches stale imports after page removal.
   - **Verification command**: `cd livedemo/frontend && npm run build`

5. **Harden direct-load and mismatch behavior for nested article URLs**
   - **Files touched**: `livedemo/frontend/src/app/App.tsx`, `livedemo/frontend/src/app/navigation.ts`
   - **Change summary**: On `/corpora/:corpusId/article/:articleId`, set selected corpus/article IDs, fetch article detail, and verify `article.corpus_id === corpusId`. If article is missing, replace with `/corpora/:corpusId`; if article belongs to another corpus, replace with canonical `/corpora/:actualCorpusId/article/:articleId`. Guard async resolution so stale responses cannot overwrite newer route state.
   - **Tests added or updated**: None — no frontend test harness exists; route behavior is verified by build plus manual Vite path smoke.
   - **Verification command**: `cd livedemo/frontend && (npm run dev -- --host 127.0.0.1 > /tmp/livedemo-vite.log 2>&1 & pid=$!; trap 'kill $pid' EXIT; sleep 3; for path in / /corpora /corpora/new /executions /corpora/example-id /corpora/example-id/article/example-article-id /articles /articles/example-article-id; do curl -fsS "http://127.0.0.1:5173$path" | grep -q '<div id="root"></div>'; done)`

6. **Polish workspace copy and layout after merge**
   - **Files touched**: `livedemo/frontend/src/pages/CorpusPanel.tsx`, `livedemo/frontend/src/components/EmptyWorkspace.tsx`, `livedemo/frontend/src/styles.css`
   - **Change summary**: Update copy so corpus workspace describes upload, inspect, decompose, rank, and evaluate flow from one place. Adjust header/actions/upload layout only as needed to avoid crowding after adding Add articles action.
   - **Tests added or updated**: None — no frontend test harness exists; visual polish verified by successful build and browser smoke.
   - **Verification command**: `cd livedemo/frontend && npm run build`

7. **Final verification and context sync**
   - **Files touched**: `livedemo/docs/context/corpus-article-crud.md`, `livedemo/docs/context/frontend-module-split.md`, `livedemo/docs/context/frontend-ux-polish.md`, `livedemo/docs/context/polish-hardening.md`
   - **Change summary**: Review `livedemo/docs/context` files after implementation and update any stale statements about separate `/articles` page, top-level Articles nav, article detail URLs, or upload location. If only some files are stale, touch only those files.
   - **Tests added or updated**: None expected; docs/context updates need no tests.
   - **Verification command**: `cd livedemo/frontend && npm run build && cd ../.. && make check`

## Risks

1. Route union changes can break existing execution/corpus navigation if callbacks are not updated consistently.
2. Legacy `/articles/:id` redirect requires async article lookup; stale response guards needed for rapid navigation/back-forward.
3. Nested URL with mismatched corpus/article ids can show confusing state unless canonicalized or rejected.
4. Removing `ArticleManagementPage.tsx` may leave stale imports or CSS classes; TypeScript build should catch imports, not unused CSS.
5. No frontend tests means manual browser smoke remains important for upload/delete/direct-load flows.
6. Keeping API article detail under `/api/articles/:id` while browser route is corpus-scoped may surprise future contributors unless context docs are updated.

## Open questions

None. Implement with existing local History API routing and current backend endpoints.

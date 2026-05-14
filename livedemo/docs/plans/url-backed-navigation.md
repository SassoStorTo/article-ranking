# URL-Backed Navigation Plan

## Goal

Give each main live-demo frontend page and selected resource a stable browser URL. From user view, top-nav/page actions update URL (`/`, `/corpora`, `/corpora/:id`, `/corpora/new`, `/articles`, `/articles/:id`, `/executions`, `/executions/:id`), direct loading or refreshing those URLs restores matching page/resource, and browser back/forward moves through prior page/resource changes.

## Non-goals

- No backend/static-serving changes; Vite SPA fallback remains serving path support.
- No API shape changes.
- No auth, sharing, scraping, URL ingestion, or URL dedupe work.
- No frontend test-framework setup.
- No query-string-backed filters or form draft persistence.

## Approach

Use an ID-aware History API layer in `livedemo/frontend/src/main.tsx`. Existing app already centralizes top-level page state as `AppPage`; extend that to parse and emit an `AppRoute` that can carry optional selected IDs. Route table should cover static pages plus dynamic paths: `/corpora/:corpusId`, `/articles/:articleId`, and `/executions/:executionId`. `App` should initialize route state from `window.location.pathname`, expose `navigate(route)` instead of raw `setPage`, call `history.pushState` for user-initiated page/resource changes, and listen for `popstate` to restore current route from URL.

Keep routing local to `main.tsx` unless implementation becomes clearer with a small routing dependency. If adding one, update `livedemo/frontend/package.json` and lockfile, then keep public app behavior unchanged. Unknown or malformed paths should fall back safely to Home and `replaceState` to `/` so direct bad URLs do not strand app in invalid state.

## Steps

1. **Add ID-aware route parsing and History API state source**
   - **Files touched**: `livedemo/frontend/src/main.tsx`
   - **Change summary**: Replace page-only helpers with route helpers: `pathForRoute(route)`, `routeForPathname(pathname)`, and optional `routeEquals(a, b)`. Support static routes (`/`, `/corpora`, `/corpora/new`, `/articles`, `/executions`) and dynamic routes (`/corpora/:corpusId`, `/articles/:articleId`, `/executions/:executionId`). Decode path params with `decodeURIComponent`, reject empty IDs, encode emitted IDs with `encodeURIComponent`, normalize trailing slashes, and normalize unknown paths to Home with `history.replaceState`.
   - **State points**: Store parsed route in React state or store derived `page` plus selected IDs consistently. Keep top-nav selection based on route `page`.
   - **Tests added or updated**: None; `livedemo/frontend` has no test runner. Type coverage comes from `npm run build` and strict TS.
   - **Verification command**: `cd livedemo/frontend && npm run build`

2. **Resolve direct-loaded dynamic IDs into selected app state**
   - **Files touched**: `livedemo/frontend/src/main.tsx`
   - **Change summary**: On route changes, sync selected IDs from route params. `/corpora/:corpusId` sets `selectedCorpusId` and clears selected article/execution. `/articles/:articleId` sets `selectedArticleId` and resolves `corpus_id` through existing `getArticle(articleId)` so article-management page has needed `selectedCorpusId`. `/executions/:executionId` sets `selectedExecutionId` and resolves `corpus_id` through existing `getExecution(executionId)` so execution detail opens in corpus workspace.
   - **Failure handling**: If `getArticle` or `getExecution` returns 404/error for a direct dynamic route, show existing error surface where possible or navigate back to the parent page (`/articles` or `/executions`) without crashing. Clear stale selected IDs when leaving dynamic routes.
   - **Race handling**: Guard async resolution so slower response from old URL cannot overwrite newer route state after rapid back/forward.
   - **Tests added or updated**: None; build catches type regressions.
   - **Verification command**: `cd livedemo/frontend && npm run build`

3. **Route all page and resource-changing UI through one navigation callback**
   - **Files touched**: `livedemo/frontend/src/main.tsx`
   - **Change summary**: Replace direct `setPage(...)`, `setSelectedCorpusId(...)`, `setSelectedArticleId(...)`, and `setSelectedExecutionId(...)` navigation flows with `navigate(route)` where URL must change. Top nav should navigate to parent static routes and clear selected resource state. Opening a corpus pushes `/corpora/:id`; selecting a corpus in sidebars pushes `/corpora/:id` or updates current article-management state as needed; selecting an article pushes `/articles/:id`; opening/submitting/replaying an execution pushes `/executions/:id` after execution ID exists; creating a corpus should push `/corpora/:id` or `/articles` depending desired post-create UX.
   - **No-op handling**: Skip duplicate `pushState` when current route path already equals target path. Use `replaceState` only for initial unknown-path normalization and optional invalid-ID fallback.
   - **Deletion handling**: When deleting selected corpus/article/execution, clear stale selection and replace/navigate to parent URL (`/corpora`, `/articles`, or `/executions`) so URL never points at removed local state.
   - **Direct-load smoke paths**: Ensure Vite serves `/corpora/example-id`, `/articles/example-id`, and `/executions/example-id` to SPA; runtime may show API error for nonexistent IDs but app shell must mount.
   - **Tests added or updated**: None; no frontend test harness.
   - **Verification command**: `cd livedemo/frontend && (npm run dev -- --host 127.0.0.1 > /tmp/livedemo-vite.log 2>&1 & pid=$!; trap 'kill $pid' EXIT; sleep 3; for path in / /corpora /corpora/new /articles /executions /corpora/example-id /articles/example-id /executions/example-id; do curl -fsS "http://127.0.0.1:5173$path" | grep -q '<div id="root"></div>'; done)`

## Risks

1. Direct `/articles/:id` and `/executions/:id` need async API resolution before corpus context is known; stale-response guards are required.
2. Duplicate history entries can accumulate if duplicate-path guard is missed.
3. Unknown-path normalization could hide typos; acceptable for SPA v1, but future explicit 404 route may be better.
4. Vite dev server supports SPA fallback, but any future production static server must also fallback non-API paths to `index.html`.
5. Current buttons lack real `href` targets, so middle-click/open-new-tab on nav is still unavailable until nav becomes anchors.

## Open questions

None. Implement with local route helpers unless code becomes simpler with a small frontend routing dependency.

# Frontend UX Polish Context

## Scope

Improve the live demo frontend around navigation, page structure, content
management, large article display, and theme switching. The work stays inside
the existing React/Vite frontend plus the minimal API support needed for article
deletion. It does not add dependencies, authentication, scraping, URL handling,
new providers, or public ranking API changes.

## Current Behavior

- `frontend/src/main.tsx` is a single React entry point with a sidebar layout.
  Corpus creation, corpus selection, article upload, article inspection,
  execution controls, execution history, and evaluation controls all live on the
  same screen.
- `frontend/src/styles.css` uses a warm light palette and two-column grids. Large
  article bodies and wide structured payloads can force the workspace to grow
  horizontally because the app does not constrain pane heights and overflow
  consistently.
- `frontend/src/api/client.ts` already supports corpus and execution deletion,
  but not article deletion.
- `app/routers/corpora.py` has `DELETE /api/corpora/{corpus_id}` and the model
  cascade removes articles, executions, results, and evaluation artifacts for a
  deleted corpus.
- `app/routers/articles.py` exposes upload, detail, and decomposition endpoints.
  It needs `DELETE /api/articles/{article_id}` for frontend article management.

## Constraints

- Keep the frontend dependency-free; use existing React, TanStack Query, and CSS.
- Keep changes scoped to demo UX and the article delete endpoint.
- Keep corpus deletion behavior unchanged.
- Preserve existing execution and evaluation flows while making them reachable
  through clearer sections.
- Add focused tests for the new article delete API behavior.

# Frontend UX Polish Context

## Scope

Improve the live demo frontend around navigation, page structure, content
management, large article display, and theme switching. The work stays inside
the existing React/Vite frontend plus the minimal API support needed for article
deletion. It does not add dependencies, authentication, scraping, new providers,
or public ranking API changes. Later URL-backed navigation is implemented with
local History API helpers and no router dependency.

## Current Behavior

- `frontend/src/main.tsx` is now a tiny React entry point. Route/page
  composition lives in `frontend/src/app/App.tsx`, with page modules under
  `frontend/src/pages/`, reusable UI under `frontend/src/components/`, execution
  forms under `frontend/src/forms/`, and result/evaluation views under
  `frontend/src/artifacts/`.
- `frontend/src/styles.css` uses a warm light palette and two-column grids. Large
  article bodies and wide structured payloads can force the workspace to grow
  horizontally because the app does not constrain pane heights and overflow
  consistently.
- `frontend/src/api/client.ts` supports corpus, execution, and article deletion.
- `app/routers/corpora.py` has `DELETE /api/corpora/{corpus_id}` and the model
  cascade removes articles, executions, results, and evaluation artifacts for a
  deleted corpus.
- `app/routers/articles.py` exposes upload, detail, decomposition, and
  `DELETE /api/articles/{article_id}` endpoints for frontend article management.

## Constraints

- Keep the frontend dependency-free; use existing React, TanStack Query, and CSS.
- Keep changes scoped to demo UX, local URL-backed navigation, and the article
  delete endpoint.
- Keep corpus deletion behavior unchanged.
- Preserve existing execution and evaluation flows while making them reachable
  through clearer sections.
- Add focused tests for the new article delete API behavior.

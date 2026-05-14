# Corpus And Article CRUD Context

## Scope

Milestone 3 added corpus management and plain-text article ingestion. Later
milestones added Mistral decomposition, execution/ranking endpoints, evaluation
helpers, and JSON structured decomposition upload without database schema
changes beyond the existing tables.

## Current repository shape

- The FastAPI app is created in `app/main.py` and exposes health, corpus,
  article, execution, and evaluation endpoints.
- Database sessions are provided through `app.deps.get_db`.
- SQLAlchemy models already include `Corpus` and `Article`, with articles
  unique by `(corpus_id, filename)` and cascaded by the corpus relationship.
- Tests use `TestClient` with an isolated in-memory SQLite engine.
- The frontend is a Vite/TanStack Query app split across `frontend/src/app`,
  `pages`, `components`, `forms`, `artifacts`, and `utils`.

## Milestone 3 interfaces

- Corpus endpoints:
  - `POST /api/corpora`
  - `GET /api/corpora`
  - `GET /api/corpora/{id}`
  - `DELETE /api/corpora/{id}`
- Article endpoints:
  - `POST /api/corpora/{id}/articles` for multipart `.txt` and `.json` uploads
  - `GET /api/articles/{id}` for article detail and body
- Article deletion is available through `DELETE /api/articles/{id}`; corpus
  deletion still cascades related articles and execution data.

## Ingestion constraints

- Accept `.txt` and `.json` filenames only.
- Decode file bytes as UTF-8 text.
- For `.txt`, derive the title from the first non-empty line when it is shorter
  than 200 characters; otherwise use the filename stem.
- For `.json`, validate content as `news_ranker.schemas.StructuredArticle`,
  derive title from `headline_neutral` plus filename, persist a matching
  `StructuredArticle` row immediately, and skip background decomposition.
- Store uploaded bodies verbatim in SQLite, including raw JSON source text.
- Duplicate filenames within the same corpus should return a conflict instead
  of silently replacing stored article bodies.

## Frontend constraints

- Build the actual corpus landing and corpus detail surfaces, not a marketing
  page.
- Keep routing lightweight for this milestone; no new router dependency is
  required.
- Frontend should call the implemented backend endpoints and expose create,
  upload, list, article detail/decomposition, article deletion, and delete-corpus
  workflows from the corpus workspace.
- Browser article detail URLs are corpus-scoped as
  `/corpora/:corpusId/article/:articleId`; backend article APIs remain under
  `/api/articles/:id`.
- Legacy `/articles` browser paths should redirect into the corpus workspace
  instead of exposing a separate top-level Articles page.

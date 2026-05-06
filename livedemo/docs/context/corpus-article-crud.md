# Corpus And Article CRUD Context

## Scope

Milestone 3 adds corpus management and plain-text article ingestion only. It
does not add Mistral decomposition, execution/ranking endpoints, evaluation
helpers, replay, or database schema changes beyond using the existing Milestone
2 tables.

## Current repository shape

- The FastAPI app is created in `app/main.py` and currently exposes only
  `GET /api/health`.
- Database sessions are provided through `app.deps.get_db`.
- SQLAlchemy models already include `Corpus` and `Article`, with articles
  unique by `(corpus_id, filename)` and cascaded by the corpus relationship.
- Tests use `TestClient` with an isolated in-memory SQLite engine.
- The frontend is a minimal Vite app in `frontend/src/main.tsx` with TanStack
  Query already installed.

## Milestone 3 interfaces

- Corpus endpoints:
  - `POST /api/corpora`
  - `GET /api/corpora`
  - `GET /api/corpora/{id}`
  - `DELETE /api/corpora/{id}`
- Article endpoints:
  - `POST /api/corpora/{id}/articles` for multipart `.txt` uploads
  - `GET /api/articles/{id}` for article detail and body
- Article deletion is by corpus cascade only for this milestone.

## Ingestion constraints

- Accept `.txt` filenames only.
- Decode file bytes as UTF-8 text.
- Derive the title from the first non-empty line when it is shorter than 200
  characters; otherwise use the filename stem.
- Store article bodies verbatim in SQLite.
- Duplicate filenames within the same corpus should return a conflict instead
  of silently replacing stored article bodies.

## Frontend constraints

- Build the actual corpus landing and corpus detail surfaces, not a marketing
  page.
- Keep routing lightweight for this milestone; no new router dependency is
  required.
- Frontend should call the implemented backend endpoints and expose create,
  upload, list, detail, and delete-corpus workflows.

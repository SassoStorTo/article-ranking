# FastAPI DB Foundation Context

## Scope

Milestone 2 replaces the Milestone 1 health-check skeleton with backend
persistence primitives only. It does not add corpus/article CRUD routes,
Mistral decomposition, ranker execution, evaluation endpoints, or frontend UI.

## Current repository shape

- The demo package lives in `livedemo/app`.
- The public backend import path is still `livedemo.app.main:app`.
- Settings already expose `LIVEDEMO_DB_URL`, CORS origins, and dev ports.
- SQLAlchemy is already declared in `livedemo/pyproject.toml`.
- There is no `tests/` directory yet in `livedemo/`.

## Milestone 2 interfaces

- Database URL source: `Settings.livedemo_db_url`.
- SQLite is the v1 database, but the session setup should keep SQLAlchemy's
  normal engine/session abstractions so tests can inject in-memory engines.
- Startup should create all v1 tables if they do not exist.
- The existing `GET /api/health` route remains available and returns the shared
  health response schema.

## Data model constraints

- Models must match `docs/brief.md` §4:
  `corpus`, `article`, `structured_article`, `execution`, `execution_result`,
  and `evaluation_artifact`.
- Article rows are unique by `(corpus_id, filename)`.
- Structured article rows are unique by
  `(article_id, llm_model, prompt_version, schema_version)`.
- Child rows cascade when their parent corpus, article, or execution is deleted.

## Testing constraints

- Tests should use isolated in-memory SQLite and not touch the dev DB path.
- Startup/table creation should be tested through the FastAPI application path,
  not only by calling SQLAlchemy metadata directly.

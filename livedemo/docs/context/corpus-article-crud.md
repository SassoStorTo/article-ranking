# Corpus/article CRUD context

## Scope

Context for `docs/plans/corpus-article-crud.md`: backend corpus/article CRUD API, multipart `.txt` upload, upload-byte persistence, Pydantic schemas, env settings, Compose/docs wiring, and pytest coverage. Scope matches milestone 2 in `docs/brief.md`; excludes Mistral/decompose-on-upload, ranking/execution/evaluation endpoints, frontend CRUD UI, `news_ranker` changes, scraping/URL/auth work, and Alembic.

## Key files

- `docs/plans/corpus-article-crud.md`: approved implementation plan and risks.
- `docs/brief.md`: milestone/API/source-of-truth expectations.
- `app/config.py`: dataclass settings for `LIVEDEMO_DB_URL` and `LIVEDEMO_UPLOADS_DIR`.
- `app/main.py`: FastAPI app factory, lifespan DB init, router inclusion, health route.
- `app/deps.py`: request-scoped settings/session dependencies.
- `app/db/models.py`: SQLAlchemy models, relationships, uniqueness, UTC datetime type, enums.
- `app/db/session.py`: engine/session factory, SQLite FK PRAGMA, `create_all()` init.
- `app/schemas.py`: Pydantic v2 request/response schemas for corpora/articles/uploads.
- `app/routers/corpora.py`: corpus create/list/detail/delete endpoints.
- `app/routers/articles.py`: article upload/detail endpoints.
- `app/services/ingestion.py`: filename, decode, title, hash, upload-path/write helpers.
- `pyproject.toml`: backend deps incl. `python-multipart`.
- `docker-compose.yml`, `.env.example`, `README.md`, `docker/*`: runtime env, volumes, docs, backend/frontend images, nginx proxy.
- Tests: `tests/test_db_session.py`, `tests/test_health.py`, `tests/test_ingestion.py`, `tests/test_corpora.py`, `tests/test_articles.py`, `tests/test_app_startup_db.py`, `tests/test_db_models.py`.

## Data flow / control flow

- `create_app(settings=None)` loads `Settings` unless injected, creates engine/session factory in lifespan, runs `init_db(engine)`, stores `engine`, `session_factory`, `settings` on `app.state`, includes corpus/article routers, exposes `GET /api/health`.
- `get_session()` opens one sync SQLAlchemy `Session` per request from `app.state.session_factory`; `get_settings()` returns injected/loaded app settings.
- Corpus API under `/api/corpora`:
  - `POST /api/corpora` inserts `Corpus`, commits, returns `CorpusDetail` with empty/sorted article list, status `201`.
  - `GET /api/corpora` uses `outerjoin` + `count(Article.id)` + `group_by`, ordered `created_at desc, id desc`, returns `CorpusSummary[]`.
  - `GET /api/corpora/{corpus_id}` loads corpus or `404 {"detail":"Corpus not found"}`, returns detail with articles sorted by `(uploaded_at, filename)`.
  - `DELETE /api/corpora/{corpus_id}` loads corpus or `404`, deletes, commits, returns empty `204`; DB/ORM cascades rows, not raw upload files.
- Upload API `POST /api/corpora/{corpus_id}/articles`:
  - Loads corpus first; missing -> `404`.
  - Accepts multipart field `files: list[UploadFile]`.
  - For each file: validate case-insensitive `.txt`, read bytes once, UTF-8 decode, reject duplicate filename within same req before DB/file writes.
  - Creates `Article` with original filename, title from first non-empty line when stripped length `< 200` else filename stem, exact decoded body, SHA-256 of stored body text encoded UTF-8.
  - Flushes row to get `article.id`, writes original bytes to `<uploads_dir>/<corpus_id>/<article_id>.txt`, then commits all rows.
  - Same-request duplicate or DB uniqueness race/existing duplicate -> `409 {"detail":"Article filename already exists in corpus"}`.
  - Invalid extension -> `422 {"detail":"uploaded files must use .txt extension"}`; invalid UTF-8 -> `422 {"detail":"uploaded files must be valid UTF-8"}`.
  - `SQLAlchemyError` during flush/commit -> rollback, remove files written in current req, return `500 {"detail":"Database error while uploading articles"}`.
- Article detail API `GET /api/articles/{article_id}`:
  - Loads article or `404 {"detail":"Article not found"}`.
  - Returns `ArticleDetail` with body plus latest `StructuredArticle.payload_json` by `(created_at desc, id desc)`, else `null`.
- DB model highlights:
  - `Article` has `UNIQUE(corpus_id, filename)` via `uq_article_corpus_filename`.
  - FK `ondelete="CASCADE"`; relationships use `cascade="all, delete-orphan"` and SQLite FK PRAGMA enabled.
  - `UtcDateTime` normalizes timezone-aware values and restores UTC awareness after SQLite reload.
  - No upload path column; SQLite body/metadata are API source, upload volume preserves raw bytes only.
- Docker/docs/settings:
  - Defaults: DB `sqlite:////var/livedemo/db.sqlite`, uploads `/var/livedemo/uploads`.
  - Compose sets both env vars; volumes `livedemo-data:/var/livedemo` and `livedemo-uploads:/var/livedemo/uploads`.
  - README documents DB/upload volume locations, env vars, `docker compose down -v` reset.

## Conventions observed

- Backend uses sync SQLAlchemy sessions inside FastAPI deps; no async DB/files.
- App factory accepts injected `Settings` for tests; env loading stays minimal dataclass-based, not pydantic-settings.
- Startup uses `metadata.create_all()`; no Alembic.
- Public API uses Pydantic v2 schemas from `app/schemas.py`; ORM-backed response models use `from_attributes=True`.
- Error payloads are deterministic `HTTPException` details; duplicate filenames map to `409`, input validation to `422`, missing resources to `404`.
- Upload accepts only UTF-8 `.txt`, reads whole file into memory, writes original bytes, hashes decoded DB body exactly as stored.
- Tests inject temp SQLite/upload paths through `Settings`; no network/Mistral/model calls.
- Docker setup is lean versus brief: no cache/HF volumes, healthchecks, non-root runtime, or Mistral env enforcement yet.

## Open questions

- Should corpus/article deletion remove raw upload files to avoid orphaned volume data?
- Should DB-row/file-write atomicity improve beyond current best-effort cleanup on SQLAlchemy errors?
- Should upload size limits or streaming be added before UI exposure?
- Should settings move to pydantic-settings when Mistral/cache/CORS config arrives?
- Should Compose align with long-form brief later: cache/HF volumes, healthchecks, non-root image, required `MISTRAL_API_KEY`?

## Suggested next step

Run `make check` after doc rewrite if treating context refresh as review gate; then move to next plan milestone, likely Mistral wiring/decompose-on-upload context + plan.

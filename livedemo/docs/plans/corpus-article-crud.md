# Corpus + Article CRUD

## Goal

Implement milestone 2 from `docs/brief.md`: backend API lets user create/list/read/delete corpora, upload one or more plain `.txt` files into corpus, persist uploaded file bytes on uploads volume, persist article bodies/metadata in SQLite, derive titles by brief heuristic, compute `content_sha256`, and read article detail with latest structured payload when present.

## Non-goals

- No Mistral calls, decomposition-on-upload, or structured mirror creation.
- No ranking/execution/evaluation endpoints.
- No frontend UI beyond existing shell.
- No parent `news_ranker` changes.
- No scraping, URL ingestion, URL dedupe, auth, users, sharing, or multilingual UI work.
- No article update/delete endpoints unless user explicitly wants them; plan follows `docs/brief.md` §5.1 routes only.
- No Alembic/migrations; keep current `create_all()` startup path.

## Approach

Add thin FastAPI routers over existing SQLAlchemy models. Keep DB sync, using current `Session` dependency. Move reusable deps out of `app/main.py` into `app/deps.py` so routers do not import app factory internals. Add Pydantic response/request schemas in one `app/schemas.py` module for now; split later only if it grows.

Uploads use `multipart/form-data` with `UploadFile` and require `python-multipart`. Server accepts only filenames ending in `.txt`, reads bytes once, decodes as UTF-8, stores exact decoded body in DB, writes original bytes under `LIVEDEMO_UPLOADS_DIR/<corpus_id>/<article_id>.txt`, derives title from first non-empty line when shorter than 200 chars, else filename stem, and hashes body text consistently for `content_sha256`. Duplicate filenames in same corpus return conflict instead of leaking SQLAlchemy `IntegrityError`.

Rejected adding storage path column: current data model has no path field, and API can serve article body from SQLite. File-on-volume exists to satisfy milestone checkpoint and preserve raw upload bytes; DB remains query source. Rejected async DB/files: current app stack is sync SQLAlchemy, small demo uploads do not need aiofiles, and avoiding new deps keeps implementation smaller.

## Steps

1. **Add upload settings, dependency, and shared deps**
   - **Files touched**: `pyproject.toml`, `uv.lock`, `app/config.py`, `app/deps.py`, `app/main.py`, `tests/test_db_session.py`, `tests/test_health.py`
   - **Change summary**: Add `python-multipart` so FastAPI can parse multipart uploads. Extend settings with `LIVEDEMO_UPLOADS_DIR` defaulting to `/var/livedemo/uploads`, create shared `get_session()` / settings access in `app/deps.py`, and keep health route behavior unchanged.
   - **Tests added or updated**: `tests/test_db_session.py` asserts uploads dir default/override. `tests/test_health.py` asserts app still starts with injected DB/upload settings.
   - **Verification command**: `uv sync && uv run pytest tests/test_db_session.py tests/test_health.py -q && uv run mypy app && uv run ruff check app tests/test_db_session.py tests/test_health.py`

2. **Add schemas and ingestion helpers**
   - **Files touched**: `app/schemas.py`, `app/services/ingestion.py`, `app/services/__init__.py`, `tests/test_ingestion.py`
   - **Change summary**: Add Pydantic models for corpus create/list/detail, article summary/detail, and upload response. Add pure helpers for `.txt` filename validation, UTF-8 decode, title derivation, SHA-256 calculation, and upload file path creation/writes.
   - **Tests added or updated**: `tests/test_ingestion.py` asserts first-short-line title heuristic, filename-stem fallback for long/blank first line, `.txt` rejection behavior, deterministic SHA-256, UTF-8 decode failure behavior, and file bytes written under corpus/article path.
   - **Verification command**: `uv run pytest tests/test_ingestion.py -q && uv run mypy app && uv run ruff check app tests/test_ingestion.py`

3. **Implement corpus endpoints**
   - **Files touched**: `app/routers/corpora.py`, `app/routers/__init__.py`, `app/main.py`, `tests/test_corpora.py`
   - **Change summary**: Add `POST /api/corpora`, `GET /api/corpora`, `GET /api/corpora/{id}`, and `DELETE /api/corpora/{id}`. Responses include article counts on list and article summaries on detail; missing corpus returns 404; delete cascades through existing model relationships.
   - **Tests added or updated**: `tests/test_corpora.py` asserts create response, list ordering/counts, detail with articles after direct DB setup, 404 for missing corpus, and delete removes corpus/articles from DB.
   - **Verification command**: `uv run pytest tests/test_corpora.py -q && uv run mypy app && uv run ruff check app tests/test_corpora.py`

4. **Implement article upload and detail endpoints**
   - **Files touched**: `app/routers/articles.py`, `app/routers/corpora.py`, `app/main.py`, `tests/test_articles.py`
   - **Change summary**: Add `POST /api/corpora/{id}/articles` accepting multiple `.txt` multipart files and `GET /api/articles/{id}` returning body plus latest structured payload or `null`. Persist `Article` rows, save upload bytes to uploads dir, map duplicate filename to 409, missing corpus/article to 404, invalid extension/decode to 422.
   - **Tests added or updated**: `tests/test_articles.py` asserts multi-file upload creates DB rows and volume files, bodies/titles/hashes persist, duplicate filename returns 409, non-`.txt` rejected, invalid UTF-8 rejected, missing corpus returns 404, article detail includes body and latest structured payload when seeded.
   - **Verification command**: `uv run pytest tests/test_articles.py -q && uv run mypy app && uv run ruff check app tests/test_articles.py`

5. **Wire Compose upload volume and docs**
   - **Files touched**: `docker-compose.yml`, `.env.example`, `README.md`, `tests/test_app_startup_db.py`
   - **Change summary**: Add `LIVEDEMO_UPLOADS_DIR=/var/livedemo/uploads`, mount named uploads volume there, document where DB vs uploads live and reset command. Keep startup table creation test aligned with app factory signature/settings.
   - **Tests added or updated**: `tests/test_app_startup_db.py` remains startup regression; no Docker-specific pytest added.
   - **Verification command**: `docker compose config >/dev/null && uv run pytest tests/test_app_startup_db.py -q && make check`

## Risks

1. `python-multipart` is new dependency; needs user approval before implementation under `AGENTS.md`.
2. DB row + file write can diverge if commit fails after bytes written; implementation should clean up newly written files on DB error where practical.
3. Existing model has no upload path column, so orphaned volume files after article/corpus delete are possible unless delete cleanup is added later.
4. Multipart files can be large; reading whole file into memory is acceptable for demo but not streaming-safe.
5. UTF-8-only decode may reject valid `.txt` in other encodings; v1 keeps simple input contract.
6. Hash definition must stay stable; changing body normalization later could break cache-hit reporting.
7. SQLite unique constraint race can still happen under parallel uploads; catch `IntegrityError` and return deterministic 409.

## Open questions

1. Approve adding `python-multipart` dependency for FastAPI multipart upload parsing?
2. Should upload hash be computed from decoded body text exactly as stored, or original uploaded bytes?

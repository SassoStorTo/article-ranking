# Data Model

## Goal

Implement `docs/brief.md` §4 persistence foundation for livedemo: SQLite-backed SQLAlchemy models, session setup, app startup table creation, and Compose volume wiring so corpora, articles, structured decompositions, executions, execution results, and evaluation artifacts can be stored durably and tested without touching `news_ranker`.

## Non-goals

- No corpus/article HTTP CRUD beyond existing health route.
- No upload parsing, title derivation, content hashing service, or Mistral calls.
- No ranking execution runner, result serializer, replay, or evaluation helper integration.
- No frontend changes.
- No Alembic migrations unless later schema churn demands them.
- No changes to parent `news_ranker` package.
- No auth, users, scraping, URL dedupe, or multilingual UI.

## Approach

Use SQLAlchemy 2.x sync ORM with SQLite. Store UUIDs as strings for SQLite portability, enum values as strings, timestamps as UTC datetimes, and config/result/helper payloads in SQLAlchemy `JSON` columns. Enable SQLite foreign keys on connection so ORM/database cascades match brief semantics. Keep model layer small: `app/db/models.py` holds declarative models and enums; `app/db/session.py` owns engine/session creation and `create_all` init.

Add minimal settings via stdlib/env-backed `app/config.py` rather than `pydantic-settings`, avoiding extra deps beyond SQLAlchemy. Keep default DB URL pointed at `/var/livedemo/db.sqlite` for container use, while tests inject temp SQLite files or in-memory engines. App startup runs `init_db()` via FastAPI lifespan. This is acceptable for v1 because there are no migrations yet; rejected Alembic for this step because brief says only add it if schema churns.

Rejected async SQLAlchemy: current app has no async DB needs, FastAPI can use sync deps, and sync ORM keeps tests/simple SQLite behavior easier. Rejected mirroring library cache internals now: `structured_article.payload_json` stores serialized payload only; actual decomposition cache read/write belongs to later Mistral step.

## Steps

1. **Add DB dependency, settings, and session primitives**
   - **Files touched**: `pyproject.toml`, `uv.lock`, `app/config.py`, `app/db/__init__.py`, `app/db/session.py`, `tests/test_db_session.py`
   - **Change summary**: Add `sqlalchemy>=2.0` dependency and lock update. Introduce settings for `LIVEDEMO_DB_URL`, engine/session factory helpers, SQLite foreign-key PRAGMA hook, and `init_db()` placeholder using SQLAlchemy metadata.
   - **Tests added or updated**: `tests/test_db_session.py` asserts injected SQLite DB URL creates usable sessions, foreign keys are enabled, and settings default/override behavior works without touching `/var/livedemo`.
   - **Verification command**: `uv sync && uv run pytest tests/test_db_session.py -q && uv run mypy app && uv run ruff check app tests/test_db_session.py`

2. **Implement corpus/article/structured-article models**
   - **Files touched**: `app/db/models.py`, `app/db/__init__.py`, `tests/test_db_models.py`
   - **Change summary**: Define `Base`, shared timestamp/UUID helpers, `Corpus`, `Article`, and `StructuredArticle` with columns and relationships from §4. Add unique constraints for `(corpus_id, filename)` and `(article_id, llm_model, prompt_version, schema_version)`, plus cascade delete relationships.
   - **Tests added or updated**: `tests/test_db_models.py` asserts rows can be inserted/read, filename uniqueness is scoped per corpus, structured article uniqueness works, and deleting a corpus cascades to articles/structured rows.
   - **Verification command**: `uv run pytest tests/test_db_models.py -q && uv run mypy app && uv run ruff check app tests/test_db_models.py`

3. **Implement execution/result/evaluation models**
   - **Files touched**: `app/db/models.py`, `tests/test_db_models.py`
   - **Change summary**: Add `ExecutionKind`, `ExecutionStatus`, `EvaluationHelper` enums plus `Execution`, `ExecutionResult`, and `EvaluationArtifact` models from §4. Store `config_json`, `profiles`, `result_json`, `params_json`, and `payload_json` as JSON; add nullable timing/error fields and cascades from executions to results/artifacts.
   - **Tests added or updated**: `tests/test_db_models.py` asserts all execution kinds/statuses/helpers persist as expected, JSON payloads round-trip, nullable fields work, and deleting an execution cascades to results and evaluation artifacts.
   - **Verification command**: `uv run pytest tests/test_db_models.py -q && uv run mypy app && uv run ruff check app tests/test_db_models.py`

4. **Wire DB init into FastAPI startup**
   - **Files touched**: `app/main.py`, `app/db/session.py`, `tests/test_health.py`, `tests/test_app_startup_db.py`
   - **Change summary**: Refactor to `create_app(settings: Settings | None = None)` while preserving module-level `app`. Add lifespan startup that creates tables through `init_db()` and keep `/api/health` unchanged.
   - **Tests added or updated**: `tests/test_health.py` uses `create_app()` with temp DB settings and still asserts `{ok: true}`. `tests/test_app_startup_db.py` starts app with `TestClient`, then inspects temp SQLite DB and asserts all §4 tables exist.
   - **Verification command**: `uv run pytest tests/test_health.py tests/test_app_startup_db.py -q && uv run mypy app && uv run ruff check app tests/test_health.py tests/test_app_startup_db.py`

5. **Persist SQLite DB in Compose runtime**
   - **Files touched**: `docker-compose.yml`, `docker/backend.Dockerfile`, `README.md`
   - **Change summary**: Set backend `LIVEDEMO_DB_URL=sqlite:////var/livedemo/db.sqlite`, add named volume mounted at `/var/livedemo`, and ensure container creates that directory. Document DB volume location and `docker compose down -v` state reset.
   - **Tests added or updated**: No pytest update; Compose config validation covers syntax, and existing health test covers app behavior.
   - **Verification command**: `docker compose config >/dev/null && make test`

6. **Final full check and artifact alignment**
   - **Files touched**: `docs/plans/data-model.md`
   - **Change summary**: Update this plan only if implementation diverges from design, especially table names, constraints, or startup behavior. Confirm project-wide checks pass.
   - **Tests added or updated**: No new tests; this step verifies all tests from earlier steps together.
   - **Verification command**: `make check`

## Risks

1. Adding SQLAlchemy changes dependencies and lockfile; implementation needs explicit approval under `AGENTS.md` rules.
2. SQLite foreign-key cascades do nothing unless PRAGMA is enabled per connection; tests must catch this.
3. `create_all()` has no migration story. Later schema changes may need Alembic or destructive reset guidance.
4. JSON columns are flexible but weakly typed; later API/serializer layers must validate payload shapes.
5. Module-level `app` plus test-specific DB settings can leak default DB use if tests import `app` too early; prefer `create_app()` in new tests.
6. Docker volume path overlap (`/var/livedemo` plus future uploads/cache mounts) can hide files if mounted incorrectly.

## Open questions

None. Adding `sqlalchemy>=2.0` to `pyproject.toml` and `uv.lock` is approved.

# Polish Hardening Context

## Scope

Milestone 9 hardens the live demo for repeat local use and handoff. The work is
limited to deterministic and serializer snapshot coverage, cheaper readiness
checks, clearer API/frontend errors and states, README operations notes, and
final verification. It does not add new product features, providers,
dependencies, schema migrations, or changes to the parent `news_ranker`
library.

## Current Repository Shape

- `app/main.py` exposes `GET /api/health` as `{ok: true}` and initializes the
  SQLAlchemy tables, executor, embedder cache, and optional Mistral client at
  startup.
- `app/db/session.py` owns engine creation and `init_db()`. Tests pass a
  temporary SQLite engine through `create_app(db_engine=...)`.
- `tests/test_executions.py` covers execution lifecycle, failures, filters,
  replay config fidelity, and cross-execution compare artifacts, but it does
  not yet assert deterministic result payloads across repeated runs.
- `tests/test_serialize.py` round-trips rank, select, and compare payloads, but
  it does not pin exact JSON payload shape.
- API errors are mostly `404`, `409`, or `422` with string details. The
  frontend currently shows raw string errors and misses some loading/empty
  states in the executions index, baseline picker, corpus detail, and execution
  results.
- `README.md` still describes the milestone 1 skeleton and needs to become a
  handoff guide for setup, environment, common failures, reset, tests, and local
  workflow.

## Constraints

- Health readiness should stay cheap: DB connectivity and already-created app
  state are safe to inspect; loading sentence-transformer models or calling
  Mistral is not.
- Snapshot tests should be deterministic without adding a snapshot dependency.
  Inline expected payloads are sufficient for this project.
- Frontend polish should remain inside the existing single-file React app and
  compact CSS, avoiding new dependencies or a redesign.
- The final milestone commit is only for formatting, verification, and cleanup
  notes if files changed; it should not hide feature work.

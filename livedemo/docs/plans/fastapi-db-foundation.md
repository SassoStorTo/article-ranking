# FastAPI DB Foundation Plan

## Goal

Implement only Milestone 2 from `livedemo/docs/brief.md`: database session
setup, SQLAlchemy models, dependency wiring, shared schemas, and smoke tests.

## Steps

1. Add `app/db/session.py` with the declarative base, engine factory, session
   factory, and table-initialization helper driven by `LIVEDEMO_DB_URL`.
2. Add `app/db/models.py` with the six v1 persistence models from the brief's
   data model.
3. Wire app startup to initialize tables and add `app/deps.py` providers for
   settings and DB sessions.
4. Add shared Pydantic schemas for IDs, timestamps, health responses, and common
   error payloads.
5. Add pytest fixtures using in-memory SQLite and smoke tests for health and
   table creation.

## Verification

- Run the livedemo pytest suite.
- Run formatting/lint checks for the changed livedemo files.
- Run the parent `make check` before declaring the milestone complete.

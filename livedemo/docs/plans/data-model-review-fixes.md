# Data Model Review Fixes Plan

## Goal

Fix review findings for the data model implementation without changing API shapes or adding dependencies.

## Steps

1. Add cascade semantics from `Corpus` to `Execution` in SQLAlchemy/database model.
2. Add regression test proving deleting a corpus removes executions, results, and evaluation artifacts.
3. Export execution models/enums from `app.db` alongside existing model exports.
4. Replace frontend `latest` dependency specifiers with exact versions from the existing lockfile and update lock root metadata.
5. Run full project checks.

## Verification

- `make check`
- `docker compose config >/dev/null`

# GitHub Actions CI Context

## Scope

This context covers planned GitHub Actions CI for repository test surfaces. CI should validate the root `news_ranker` library tests and the `livedemo` backend tests on pull requests to the default branch and pushes to the default branch. It does not cover packaging, publishing, Docker/Compose validation, frontend npm builds, provider/network integration tests, deployment, or adding runtime dependencies.

## Current state

- No workflow files exist under `.github/workflows/`.
- Root project uses `uv`, Python `>=3.11`, hatchling, pytest, ruff, and mypy.
- Root test command from the issue scope is `uv run python -m pytest tests`.
- `Makefile` provides `make check`, but it only covers root typecheck, lint, format check, and root pytest suite.
- `livedemo/` is a separate Python project with its own `pyproject.toml` and `uv.lock`.
- `livedemo` depends on the root package through `news-ranker = { path = "..", editable = true }`.
- `livedemo` backend tests live under `livedemo/tests/` and should run from the `livedemo/` working directory with `uv run python -m pytest tests`.
- `livedemo` tests override decomposition clients and should not require real Mistral calls.

## Relevant files

- `.github/workflows/ci.yml` — target workflow file to add.
- `pyproject.toml` — root package metadata, Python requirement, and pytest root testpaths.
- `uv.lock` — root lockfile for CI dependency sync.
- `Makefile` — existing root local commands; current `make check` does not run `livedemo` tests.
- `livedemo/pyproject.toml` — livedemo package metadata, dev pytest/httpx deps, and editable root package source.
- `livedemo/uv.lock` — livedemo lockfile for CI dependency sync.
- `livedemo/tests/` — livedemo backend pytest suite.
- `tests/` — root library pytest suite.

## CI design constraints

- Trigger on `pull_request` targeting `main` and `push` to `main`.
- Use Python 3.11 to satisfy project `>=3.11` while matching local documented runtime.
- Install `uv` in workflow instead of adding repository dependencies.
- Run root and livedemo suites as separate jobs or clearly separated steps so failures identify failing surface.
- Keep commands close to issue-suggested commands:
  - root: `uv sync`, then `uv run python -m pytest tests`
  - livedemo: `uv sync`, then `uv run python -m pytest tests` from `livedemo/`
- Avoid secrets and network/provider calls beyond dependency installation.
- Avoid changing public Python APIs or adding runtime dependencies.

## Risks / considerations

- Separate jobs provide clearer pass/fail labels than two pytest commands in one job.
- `livedemo` sync depends on root package path source, so checkout must include the whole repository.
- If `uv sync --locked` fails due lockfile drift, implementation may need either lockfile update or non-locked sync decision. Prefer locked sync when current lockfiles are valid.
- Running only pytest means lint/typecheck remain local `make check` concerns unless scope expands.

## Suggested next step

Add a focused plan for `.github/workflows/ci.yml` with separate root and livedemo test reporting, then implement workflow and run local `make check` plus both pytest commands where practical.

# GitHub Actions CI Context

## Scope

This context covers GitHub Actions CI for repository test surfaces. CI validates the root `news_ranker` library tests and the `livedemo` backend tests on pull requests to `main` and pushes to `main`. It does not cover packaging, publishing, Docker/Compose validation, frontend npm builds, provider/network integration tests, deployment, or adding runtime dependencies.

## Current state

- Workflow file exists at `.github/workflows/ci.yml`.
- Workflow name is `CI` and triggers on `pull_request` targeting `main` plus `push` to `main`.
- Root project uses `uv`, Python `>=3.11`, hatchling, pytest, ruff, and mypy.
- Root CI job `library-tests` runs on `ubuntu-latest`, checks out the repo, sets up Python 3.11, installs `uv` with `astral-sh/setup-uv@v5`, runs `uv sync --locked`, then runs `uv run python -m pytest tests`.
- `Makefile` provides `make check`, but it only covers root typecheck, lint, format check, and root pytest suite.
- `livedemo/` is a separate Python project with its own `pyproject.toml` and `uv.lock`.
- `livedemo` depends on the root package through `news-ranker = { path = "..", editable = true }`.
- `livedemo` CI job `livedemo-tests` runs on `ubuntu-latest`, checks out the repo, sets up Python 3.11, installs `uv` with `astral-sh/setup-uv@v5`, then runs `uv sync --locked` and `uv run python -m pytest tests` with `working-directory: livedemo`.
- `livedemo` tests override decomposition clients and should not require real Mistral calls.

## Relevant files

- `.github/workflows/ci.yml` — CI workflow with separate root and livedemo test jobs.
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
- Keep commands close to issue-suggested commands with locked dependency sync:
  - root: `uv sync --locked`, then `uv run python -m pytest tests`
  - livedemo: `uv sync --locked`, then `uv run python -m pytest tests` from `livedemo/`
- Avoid secrets and network/provider calls beyond dependency installation.
- Avoid changing public Python APIs or adding runtime dependencies.

## Risks / considerations

- Separate jobs provide clearer pass/fail labels than two pytest commands in one job.
- `livedemo` sync depends on root package path source, so checkout must include the whole repository.
- Locked sync makes lockfile drift visible in CI rather than silently resolving new deps.
- Running only pytest means lint/typecheck remain local `make check` concerns unless scope expands.

## Suggested next step

Run workflow on GitHub and inspect job labels/logs for root versus livedemo failure clarity.

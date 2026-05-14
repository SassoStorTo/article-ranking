# GitHub Actions CI Plan

## Goal

Add GitHub Actions CI that runs both repository Python test suites on pull requests targeting `main` and pushes to `main`: root `tests/` for `news_ranker`, plus `livedemo/tests/` from the `livedemo/` project context. Failures must identify which suite failed.

## Non-goals

- No new runtime dependencies.
- No deployment, publishing, release, Docker, or Compose workflow.
- No frontend npm build or browser test job.
- No provider/secret-backed integration tests.
- No public Python API changes.
- No changes to test behavior unless existing CI commands expose lockfile or env assumptions that must be fixed.

## Approach

Create `.github/workflows/ci.yml` with two independent jobs: `library-tests` and `livedemo-tests`. Both jobs run on `ubuntu-latest`, check out the repository, set up Python 3.11, install `uv`, sync dependencies, then run pytest. Separate jobs make GitHub UI show root and livedemo failures separately. Use commands matching issue scope and project docs; prefer `uv sync --locked` if current lockfiles are valid. Limit workflow token permissions to `contents: read` because CI only needs checkout access.

## Risks / decisions

- Separate jobs duplicate setup time but give clearest failure labels.
- `livedemo` sync must run from `livedemo/` because it has separate `pyproject.toml` and `uv.lock`.
- `livedemo` path dependency on root package requires full repository checkout.
- If `uv sync --locked` fails from stale lockfiles, fix lockfiles or adjust sync plan before workflow merge; do not hide dependency drift silently.
- CI scope is pytest only; existing `make check` remains local full root gate unless scope expands.

## Steps

1. **Add workflow skeleton**
   - **Files touched**: `.github/workflows/ci.yml`
   - **Change summary**: Add workflow named `CI` with triggers `pull_request.branches: [main]`, `push.branches: [main]`, and least-privilege `permissions.contents: read`.
   - **Validation**: Inspect YAML for GitHub Actions syntax and trigger branch names.

2. **Add root library test job**
   - **Files touched**: `.github/workflows/ci.yml`
   - **Change summary**: Add `library-tests` job on `ubuntu-latest`; steps: `actions/checkout`, Python 3.11 setup, `uv` install, `uv sync --locked`, `uv run python -m pytest tests`.
   - **Validation**: Run locally from repo root: `uv sync --locked` and `uv run python -m pytest tests`.

3. **Add livedemo test job**
   - **Files touched**: `.github/workflows/ci.yml`
   - **Change summary**: Add `livedemo-tests` job on `ubuntu-latest`; steps: `actions/checkout`, Python 3.11 setup, `uv` install, `uv sync --locked`, `uv run python -m pytest tests` with `working-directory: livedemo` for sync/test steps.
   - **Validation**: Run locally from `livedemo/`: `uv sync --locked` and `uv run python -m pytest tests`.

4. **Keep CI dependency behavior explicit**
   - **Files touched**: `.github/workflows/ci.yml` if needed; lockfiles only if validation proves drift.
   - **Change summary**: Avoid adding package deps. If lockfile sync fails, update relevant `uv.lock` through `uv lock` in matching project context rather than using unpinned installs without review.
   - **Validation**: Confirm `git diff` contains workflow plus any justified lockfile changes only.

5. **Run final local checks**
   - **Files touched**: none expected.
   - **Change summary**: Run project verification before implementation handoff.
   - **Validation**: `make check`; root pytest command; livedemo pytest command.

6. **Check context artifacts and update if needed**
   - **Files touched**: `docs/context/github-actions-ci.md` and any related `docs/context/*.md` if implementation differs from this plan.
   - **Change summary**: Re-read context files after implementation; update content to match actual workflow commands, triggers, jobs, lockfile decisions, and any scope changes caused by this plan.
   - **Validation**: Confirm docs/context describes final CI behavior accurately.

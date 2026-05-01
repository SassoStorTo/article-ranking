# AGENTS.md

This file provides guidance to agents working in this repository.

## Project in one paragraph

A Python-backed, fully dockerized web application that exposes the `news_ranker` library for interactive use: upload article corpora as plain text, decompose them with Mistral, run the ranking algorithm with configurable parameters, replay and compare past executions, and run the full evaluation/comparison suite (`news_ranker.evaluate`) against those executions.

## Stack and layout

- Backend: Python 3.11+, FastAPI, Uvicorn, Pydantic v2.
- Frontend: Node 20+, React, Vite, TypeScript.
- Package managers: uv for Python, npm for frontend.
- Build: hatchling for Python package; Vite for frontend; Docker Compose for app runtime.
- Test runner: pytest.
- Formatter/linter: ruff for Python, Biome for frontend.
- Typechecker: mypy for Python, TypeScript compiler for frontend.

Layout:

```text
app/             # FastAPI backend package
tests/           # pytest tests
frontend/        # React + Vite SPA
docker/          # Dockerfiles and nginx config
docs/brief.md    # source-of-truth brief
docs/context/    # context artifacts
docs/plans/      # plan artifacts
```

## How to run things

- Install: `make install`
- Dev app: `make dev`
- Test: `make test`
- Lint/format check: `make lint`
- Typecheck: `make typecheck`
- Build: `make build`
- Full check: `make check`

Run `make check` before declaring any implementation step done.

## Workflow conventions

Use the artifact-driven pipeline for non-trivial work:

1. Context: write or update a context artifact in `docs/context/` describing relevant files, constraints, and current behavior.
2. Plan: write or update a plan artifact in `docs/plans/` before implementation.
3. Implement: make the smallest code change that satisfies the approved plan.
4. Review: run `make check`, inspect the diff, and update artifacts if implementation diverged from the plan.

Keep context and plan artifacts focused on the current task. Do not use them as general notes dumps.

## Coding rules

- Read files in full before editing.
- Prefer editing existing files over creating new ones unless new files are required.
- Ruff enforces Python formatting, import order, and selected lint rules.
- Biome enforces frontend formatting, import order, and selected lint rules.
- Mypy runs in strict mode for `app`.
- Do not change `news_ranker` itself; livedemo consumes public/submodule APIs only.
- Upload input is plain `.txt` only; no scraping or URL deduplication.

## Style

- Python: Ruff target `py311`, line length 88.
- Frontend: Biome space indentation, 2 spaces, line width 88.

## Things the agent should NOT do without asking

- Add new dependencies.
- Change public API shapes.
- Delete or weaken tests.
- Add database schemas or migrations.
- Touch deployment/infra beyond existing Docker bootstrap.
- Add authentication, user management, sharing, or collaboration.
- Implement scraping, URL deduplication, or multilingual UI.
- Change `news_ranker` library code.

## Domain glossary

TODO: define terms as implementation decisions land.

## Related artifacts

- `docs/brief.md`
- `docs/context/`
- `docs/plans/`

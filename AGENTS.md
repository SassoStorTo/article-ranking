# AGENTS.md

This file provides guidance to agents working in this repository.

## Project in one paragraph

A scoring library that takes *k* articles about the same news event, ranks them from best to worst, selects the best *M*, and compares alternative definitions of "best" using structured fact decomposition, embedding centrality, information coverage, and optional diversity.

## Stack and layout

- Language/runtime: Python 3.11+
- Package manager: uv
- Build backend: hatchling
- Test runner: pytest
- Formatter/linter: ruff
- Typechecker: mypy
- Import package: `news_ranker`
- Distribution package: `news-ranker`

Layout:

```text
news_ranker/       # library package
tests/             # pytest tests
docs/brief.md      # source-of-truth brief
docs/context/      # context artifacts
docs/plans/        # plan artifacts
```

## How to run things

- Install: `make install`
- Dev smoke check: `make dev`
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
- Ruff enforces formatting, import order, and selected lint rules.
- Mypy runs in strict mode for `news_ranker`.
- Follow brief constraints: no scraping, no URL deduplication, no external fact-checking, no multilingual handling beyond embedder support for v1.

## Style

Ruff target: Python 3.11, line length 88. Ruff format owns formatting.

## Things the agent should NOT do without asking

- Add new dependencies.
- Change public API shapes.
- Delete or weaken tests.
- Add database schemas or migrations.
- Add deployment, Docker, CI, or infra files.
- Implement scraping, URL deduplication, or external fact-checking.
- Switch LLM or embedding provider choices once configured.

## Domain glossary

TODO: define terms as implementation decisions land.

## Related artifacts

- `docs/brief.md`
- `docs/context/`
- `docs/plans/`

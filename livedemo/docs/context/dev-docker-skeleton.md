# Dev Docker Skeleton Context

## Scope

Milestone 1 creates only the live demo project shell. It proves that a FastAPI
backend and Vite frontend can run from the parent repository while importing the
local `news_ranker` package. It does not add database models, CRUD endpoints,
ranking execution, Mistral calls, or persistence behavior.

## Current repository shape

- The parent repository root contains the existing `news_ranker` package,
  `pyproject.toml`, `uv.lock`, and `.env`.
- The demo lives under `livedemo/`.
- Docker Compose is invoked from the parent root context through
  `livedemo/docker-compose.yml`.
- Runtime environment variables for Compose are read from the parent `.env`.
  `livedemo/.env.example` is only a reference template.

## Milestone 1 interfaces

- Backend import path: `livedemo.app.main:app`.
- Health route: `GET /api/health` returns `{"ok": true}`.
- Backend settings read:
  - `MISTRAL_API_KEY`
  - `LIVEDEMO_DB_URL`
  - `LIVEDEMO_CORS_ORIGINS`
  - `BACKEND_PORT`
  - `FRONTEND_PORT`
- The backend Docker image installs both the parent `news-ranker` project and
  the `livedemo` backend project from local paths.
- The frontend is a minimal Vite React shell that checks backend health at
  `http://localhost:8000/api/health`.

## Constraints

- Do not modify the parent `news_ranker` package or root project metadata.
- Do not add application tables, DB sessions, routers, schemas, Mistral clients,
  or ranking services in this milestone.
- Keep Docker and README instructions aligned with parent `.env` usage.

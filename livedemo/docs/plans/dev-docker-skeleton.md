# Dev Docker Skeleton Plan

## Goal

Implement only Milestone 1 from `livedemo/docs/brief.md`: create the live demo
backend/frontend skeleton and local Docker development stack.

## Steps

1. Add a `livedemo` backend project file with FastAPI, Uvicorn,
   Pydantic Settings, SQLAlchemy, and the parent `news-ranker` dependency.
2. Add `livedemo.app.main:app` with CORS configured from settings and a minimal
   `GET /api/health` endpoint returning `{"ok": true}`.
3. Add a backend Dockerfile built from the parent repo root so local
   `news_ranker` and `livedemo` code are installed without publishing packages.
4. Add Docker Compose for backend and frontend dev services. Compose uses the
   parent `.env` file as runtime env source.
5. Add a minimal Vite React shell that displays backend health status.
6. Add `.env.example` and README startup documentation.

## Verification

- Import the FastAPI app and call `/api/health` with a local test client.
- Run frontend package/build checks when dependencies are available.
- Run `docker compose -f livedemo/docker-compose.yml config` and, if possible,
  `docker compose -f livedemo/docker-compose.yml up --build`.
- Run `make check` from the parent repository before declaring completion.

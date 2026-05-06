# News Ranker Live Demo

This folder contains the development shell for the News Ranker live demo. It is
implemented as a FastAPI backend plus a Vite React frontend, both run through
Docker Compose from inside the parent `article-ranking` repository.

Milestone 1 only provides the app skeleton and health check. Corpus management,
database models, ranking execution, Mistral decomposition, and evaluation
features are planned for later milestones.

## Environment

Runtime environment comes from the parent repository `.env` file:

```bash
/Users/paolo/farm/swe/article-ranking/.env
```

Use `livedemo/.env.example` as the reference list of keys, but copy the values
into the parent `.env`. The Compose file reads `../.env` so local secrets stay
in one place for the whole repository.

Expected keys:

```bash
MISTRAL_API_KEY=
LIVEDEMO_DB_URL=sqlite:////var/livedemo/db.sqlite
LIVEDEMO_CORS_ORIGINS=http://localhost:5173
BACKEND_PORT=8000
FRONTEND_PORT=5173
VITE_API_BASE_URL=http://localhost:8000
```

`MISTRAL_API_KEY` can be blank for this skeleton milestone because the backend
does not construct a Mistral client yet.

## Start Development Stack

From the parent repository root:

```bash
docker compose -f livedemo/docker-compose.yml up --build
```

Then open:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/api/health`

Useful commands:

```bash
docker compose -f livedemo/docker-compose.yml logs -f backend
docker compose -f livedemo/docker-compose.yml down
```

## Backend

The backend app is exposed as:

```bash
livedemo.app.main:app
```

The dev container runs:

```bash
uvicorn livedemo.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The Docker build context is the parent repository root so the image can install
both the local `news-ranker` library and this `livedemo` backend package.

## Frontend

The frontend is a minimal Vite React shell in `livedemo/frontend`. It polls the
backend health endpoint through `VITE_API_BASE_URL`, defaulting to
`http://localhost:8000`.

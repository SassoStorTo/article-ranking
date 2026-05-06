# News Ranker Live Demo

FastAPI + React demo for running the local `news_ranker` package against
uploaded `.txt` article corpora. The app stores corpora, article bodies,
Mistral decompositions, ranking executions, replay configs, and evaluation
artifacts in SQLite.

## Setup

From the parent `article-ranking` repository, copy the example environment into
the parent `.env` file and fill in the Mistral key:

```bash
cp livedemo/.env.example .env
```

The Compose file reads `../.env` from this folder, keeping local secrets at the
repository root.

## Environment Variables

```bash
MISTRAL_API_KEY=                    # required outside tests
LIVEDEMO_DB_URL=sqlite:////var/livedemo/db.sqlite
LIVEDEMO_CORS_ORIGINS=http://localhost:5173
BACKEND_PORT=8000
FRONTEND_PORT=5173
VITE_API_BASE_URL=http://localhost:8000
```

`MISTRAL_API_KEY` is required for real article decomposition. Tests override the
decomposition client and do not call Mistral.

## Start The Dev Stack

Run from the parent repository root:

```bash
docker compose -f livedemo/docker-compose.yml up --build
```

Open:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/api/health`
- OpenAPI: `http://localhost:8000/docs`

Follow backend logs:

```bash
docker compose -f livedemo/docker-compose.yml logs -f backend
```

Stop the stack:

```bash
docker compose -f livedemo/docker-compose.yml down
```

## Development Workflow

Typical local loop:

1. Create or select a corpus.
2. Upload one or more `.txt` files.
3. Inspect decomposition output on article detail.
4. Run rank, select, or compare profiles.
5. Replay old executions or compare them from the Old Executions view.
6. Run evaluation helpers or the full test suite with an explicit baseline.

The backend container hot-reloads `livedemo/app`. The frontend container runs
Vite with HMR against `livedemo/frontend`.

## Test Commands

Backend tests from this folder:

```bash
uv run python -m pytest tests
```

Frontend build from `livedemo/frontend`:

```bash
npm run build
```

Parent project verification from the repository root:

```bash
make check
```

`make check` runs the parent library typecheck, lint, format check, and pytest
suite. Use it before declaring an implementation milestone complete.

## Reset The Local DB

The default Compose database lives in the `livedemo-db` Docker volume. To remove
all local demo state:

```bash
docker compose -f livedemo/docker-compose.yml down -v
```

Then restart the stack with `up --build`.

## Common Failures

`MISTRAL_API_KEY is required for article decomposition.`

Add the key to the parent `.env` file, then restart the backend container.

`Address already in use`

Change `BACKEND_PORT` or `FRONTEND_PORT` in `.env`, then restart Compose.

Frontend cannot reach the backend.

Make sure `VITE_API_BASE_URL` points at the host backend URL, usually
`http://localhost:8000`, and that `/api/health` returns `ok: true`.

Health returns `ok: false`.

Inspect the `checks` object from `/api/health`. `database: false` usually means
the SQLite path or Docker volume is not writable. `decomposition_client: false`
means the app could not prepare the configured Mistral client.

Uploads fail with `409`.

Filenames are unique within a corpus. Rename the duplicate `.txt` file or delete
and recreate the corpus.

Evaluation comparison fails with `422`.

Top-M overlap and rank correlation require compatible rank/select executions.
The full test suite also requires an explicit baseline execution.

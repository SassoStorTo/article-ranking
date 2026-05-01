# News Ranker Live Demo

A Python-backed, fully dockerized web application that exposes the `news_ranker` library for interactive use: upload article corpora as plain text, decompose them with Mistral, run the ranking algorithm with configurable parameters, replay and compare past executions, and run the full evaluation/comparison suite (`news_ranker.evaluate`) against those executions.

## Commands

```bash
make install
make dev
make test
make lint
make typecheck
make build
make check
```

`make dev` runs Docker Compose and serves the app at <http://localhost:8080>.

Docker Compose stores the SQLite database in the `livedemo-data` named volume,
mounted in the backend container at `/var/livedemo/db.sqlite`. To reset all
persisted app state, run `docker compose down -v`.

## Configuration

The backend reads `LIVEDEMO_DB_URL` from the environment to locate the SQLite
database (any SQLAlchemy-compatible URL). It defaults to
`sqlite:////var/livedemo/db.sqlite`, which assumes the Compose volume layout.
For local non-Compose runs, point it at a writable path, e.g.
`LIVEDEMO_DB_URL=sqlite:///./livedemo.sqlite`. Only SQLite is supported today.

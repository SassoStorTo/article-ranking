# Local Demo Control Context

The Docker backend image currently installs the full `news-ranker` dependency
graph, including `sentence-transformers` and PyTorch. That is too heavy for the
remote server's current Docker storage setup during presentation prep.

The existing skeleton backend only serves FastAPI health/CORS endpoints and
does not import `news-ranker`. A local control script can run the backend with
only `fastapi`, `pydantic-settings`, and `uvicorn`, then run the Vite frontend
with `npm`. This gives a fast presentation path without changing the package
API or weakening the later Docker path.

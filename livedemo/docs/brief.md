# News Ranker Live Demo — Design Document

> A Python-backed, fully dockerized web application that exposes the `news_ranker` library for interactive use: upload article corpora as plain text, decompose them with Mistral, run the ranking algorithm with configurable parameters, replay and compare past executions, and run the full evaluation/comparison suite (`news_ranker.evaluate`) against those executions.

---

## Table of Contents

1. [Goals](#goals)
2. [Scope & Assumptions](#scope-assumptions)
3. [Architecture](#architecture)
4. [Data Model](#data-model)
5. [Backend API](#backend-api)
6. [UI Pages](#ui-pages)
7. [Evaluation Helper Integration](#evaluation-integration)
8. [Mistral & Embedding Wiring](#provider-wiring)
9. [Repo Layout](#repo-layout)
10. [Implementation Order (Milestones)](#milestones)
11. [Docker Setup](#docker-setup)
12. [Testing Strategy](#testing-strategy)
13. [Resolved Decisions](#resolved-decisions)

---

<a id="goals"></a>

## 1. Goals

The demo site is a thin, opinionated UI on top of the existing library. It exists to:

1. **Demonstrate** the public pipeline (`NewsRanker.rank` / `select` / `compare_profiles`) end-to-end on user-supplied corpora, not just on bundled fixtures.
2. **Make decomposition cost visible** by persisting Mistral output so the same article is decomposed once per content hash, not once per run.
3. **Make experiments reproducible**: every execution stores its full input set, the `RankerConfig` parameters used, and the resulting ranking/selection so a past run can be replayed, inspected, or compared against a new one.
4. **Surface the evaluation helpers** (`top_m_overlap`, `rank_correlation`, `component_score_table`, `cluster_inspection_rows`, `anonymized_user_study_bundle`) as first-class UI features, not just library internals.

The application is **fully dockerized**: a single `docker compose up` brings up the backend, the frontend, and a persistent volume for runtime state. There is no supported "run from the host Python" path — local development also goes through Compose with bind-mounts and hot-reload (see [§11](#docker-setup)).

---

<a id="scope-assumptions"></a>

## 2. Scope & Assumptions

**Input contract.** Users upload one or more `.txt` files into a named **corpus**. Each file's first non-empty line (when shorter than 200 chars) is taken as the title; otherwise the title is the filename without extension. The body is the file content verbatim. A corpus is the unit on which `NewsRanker` runs.

**Output contract.** Each pipeline run is persisted as an **execution**: a database row holding the full effective `RankerConfig`, the kind (`rank` / `select` / `compare_profiles`), and a JSON-serialized `RankResult`, `SelectionResult`, or `ProfileComparison`. Evaluation helper outputs are persisted alongside as **evaluation artifacts** keyed to one execution.

**Out of scope (for v1):**
- Authentication beyond a single shared instance.
- Multi-user collaboration, sharing, or per-user corpora.
- Article scraping or URL deduplication (uploads are plain `.txt` only).
- Multilingual UI (the embedder still handles whatever language the user uploads).
- Any code change to `news_ranker` itself; the demo only consumes its public/submodule APIs.

**Stack:**
- Python 3.11+ (backend), Node 20+ (frontend build).
- `fastapi` + `uvicorn` — HTTP layer and OpenAPI publication.
- `pydantic` v2 — request/response validation, reused across the library boundary.
- `sqlalchemy` 2.x + SQLite — persistence of corpora, articles, executions, results, evaluation artifacts.
- `news_ranker` — the existing library, installed into the backend image from the parent path.
- `mistralai>=2.4.4` — already a `news_ranker` dep; wired through the demo via `MistralDecompositionClient`.
- `sentence-transformers` — embedding provider, loaded once at app startup.
- React + Vite + TanStack Query — minimal SPA.
- Docker + Compose — single deployment surface; named volumes for persistence.

---

<a id="architecture"></a>

## 3. Architecture

```
                       docker compose
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   ┌──────────────────┐   internal   ┌────────────────────────┐   │
│   │ frontend         │   network    │ backend                │   │
│   │ container        │ ◄──────────► │ container              │   │
│   │ (nginx serving   │              │ (uvicorn + FastAPI +   │   │
│   │  built SPA, or   │              │  news_ranker, Py 3.11) │   │
│   │  vite dev in     │              │                        │   │
│   │  dev profile)    │              │ ┌────────────────────┐ │   │
│   └────────┬─────────┘              │ │ news_ranker (in-   │ │   │
│            │ :80 / :5173            │ │  process library)  │ │   │
│            │                        │ └────────────────────┘ │   │
│            │                        │ ┌────────────────────┐ │   │
│            │                        │ │ Mistral client     │ │   │
│            │                        │ │ (injected hook)    │ │   │
│            │                        │ └────────────────────┘ │   │
│            │                        │ ┌────────────────────┐ │   │
│            │                        │ │ SQLAlchemy + SQLite│ │   │
│            │                        │ └────────────────────┘ │   │
│            │                        └──────────┬─────────────┘   │
│            │                                   │                 │
│            │                       ┌───────────▼─────────────┐   │
│            │                       │ named volumes           │   │
│            │                       │  livedemo_db            │   │
│            │                       │  livedemo_uploads       │   │
│            │                       │  livedemo_cache         │   │
│            │                       │  hf_cache (model dl)    │   │
│            │                       └─────────────────────────┘   │
│            │                                                     │
└────────────┼─────────────────────────────────────────────────────┘
             │ host port :8080
             ▼
        Browser
```

### 3.1 Backend stack

- **Web framework**: FastAPI. Tight Pydantic v2 fit (already a project dep), automatic OpenAPI for the SPA to consume, async layer that pays off for long-running Mistral calls via background tasks.
- **ORM**: SQLAlchemy 2.x with SQLite. SQLite is enough for a demo; a single-file DB simplifies reset and snapshotting. The DB file lives on a named Docker volume (`livedemo_db`) so container rebuilds do not wipe state. Alembic migrations only if the schema starts churning.
- **Background jobs**: FastAPI `BackgroundTasks` for short Mistral calls; a `concurrent.futures.ThreadPoolExecutor` wrapper for full pipeline runs so the request returns immediately with an `execution_id` while the run executes. No Celery/Redis — the demo stays single-process inside one container.
- **Library wiring**: instantiate `NewsRanker(embedder, config, decomposer=...)` per request, where:
  - `embedder` is a process-singleton `SentenceTransformerEmbedder` loaded at app startup (one model download per container life, cached on the `hf_cache` volume so rebuilds reuse it).
  - `decomposer` is `lambda article: decompose(article, mistral_client, config=DecompositionConfig(...), cache_dir=CACHE_DIR)`, also a process singleton.
  - `config` is built from the request payload (see [§5.4](#config-validation)).

> **Why FastAPI + SQLite + single-process**: the demo's load profile is one student at a time clicking "Run". The pipeline cost is dominated by Mistral latency and embedding compute, not request fan-out. A single-process app with named-volume persistence is the simplest thing that survives a container rebuild without losing uploaded corpora or past executions.

### 3.2 Frontend

A small React + Vite SPA. Pages described in [§6](#ui-pages). State lives in TanStack Query against the FastAPI endpoints; no server-side rendering. In production the SPA is built (`vite build`) into static assets and served by an nginx container that also reverse-proxies `/api/*` to the backend container; in development a `vite dev` container with HMR is used instead (see [§11.4](#compose-dev)).

---

<a id="data-model"></a>

## 4. Data Model

All persistent state lives in SQLite. The library's existing on-disk caches (decomposition JSON, future embedding `.npy` files) live under `/var/livedemo/cache/` on the `livedemo_cache` volume and are **not** mirrored into the DB except where explicitly noted — the library's caching is reused unchanged.

```
corpus
├── id              (uuid pk)
├── name            (str, user-supplied label, e.g. "trump-shooting")
├── created_at      (timestamptz)
└── notes           (str, optional)

article
├── id              (uuid pk)
├── corpus_id       (fk → corpus.id, on delete cascade)
├── filename        (str, original .txt name)
├── title           (str, derived from first line or filename)
├── body            (text, full article body)
├── content_sha256  (str, hash of normalized body — used as Mistral cache key bridge)
├── uploaded_at     (timestamptz)
└── UNIQUE(corpus_id, filename)

structured_article          # cached output of one Mistral decomposition
├── id              (uuid pk)
├── article_id      (fk → article.id, on delete cascade)
├── llm_model       (str, e.g. "mistral-small-latest")
├── prompt_version  (str)
├── schema_version  (str)
├── payload_json    (json — serialized StructuredArticle.model_dump())
├── created_at      (timestamptz)
└── UNIQUE(article_id, llm_model, prompt_version, schema_version)

execution                   # one ranker run on one corpus with one config
├── id              (uuid pk)
├── corpus_id       (fk → corpus.id)
├── kind            (enum: "rank" | "select" | "compare_profiles" | "evaluate")
├── status          (enum: "pending" | "running" | "succeeded" | "failed")
├── config_json     (json — full RankerConfig.__dict__ + selection params)
├── profiles        (json array — profile names involved)
├── m               (int, nullable — for select)
├── started_at      (timestamptz, nullable)
├── finished_at     (timestamptz, nullable)
├── error           (text, nullable)
└── created_at      (timestamptz)

execution_result            # serialized RankResult / SelectionResult / ProfileComparison
├── id              (uuid pk)
├── execution_id    (fk → execution.id, on delete cascade)
├── profile         (str, nullable — null for ProfileComparison root)
├── result_json     (json — serialized result records, see §5.3)
└── created_at      (timestamptz)

evaluation_artifact         # outputs of news_ranker.evaluate helpers
├── id              (uuid pk)
├── execution_id    (fk → execution.id)
├── helper          (enum: "top_m_overlap" | "rank_correlation" |
│                          "component_score_table" | "cluster_inspection_rows" |
│                          "anonymized_user_study_bundle")
├── params_json     (json — helper inputs, e.g. {m: 3, method: "kendall"})
├── payload_json    (json — helper output, see §7)
└── created_at      (timestamptz)
```

> **Why mirror `structured_article` in SQL when the library already caches it on disk:** two reasons. First, the UI can display extracted facts/entities without re-reading library cache files. Second, the structured payload survives a `livedemo_cache` volume wipe — only the Mistral cost is lost, not the visible decomposition history.
>
> **Why `execution.config_json` and not normalized columns:** `RankerConfig` evolves with the library; flat JSON keeps the demo schema decoupled from library-side knob changes and makes "view parameters of an old execution" a single field read. The replay endpoint uses this column verbatim.
>
> **Why `content_sha256` on `article`:** it lets the UI report cache hits ("this article will reuse a previous decomposition") without owning the on-disk cache key, which belongs to `news_ranker.decompose`.

---

<a id="backend-api"></a>

## 5. Backend API

Route shapes are sketches; the SPA pins to OpenAPI. All bodies are JSON unless stated otherwise.

### 5.1 Corpus & article management

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/corpora` | Create a corpus `{name, notes}` → `{id}` |
| `GET` | `/api/corpora` | List corpora with article counts |
| `GET` | `/api/corpora/{id}` | Corpus detail + article list |
| `DELETE` | `/api/corpora/{id}` | Cascade delete corpus + articles + executions |
| `POST` | `/api/corpora/{id}/articles` | `multipart/form-data` upload: one or more `.txt` files. Server reads each file, computes `content_sha256`, persists `article` rows, returns the new article ids. |
| `GET` | `/api/articles/{id}` | Article body + (if present) latest `structured_article` payload |
| `POST` | `/api/articles/{id}/decompose` | Force re-decompose; useful when prompt/model/schema versions change |

Title heuristic for uploaded `.txt`: first non-empty line if it is shorter than 200 chars, otherwise the filename without extension.

### 5.2 Execution endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/executions/rank` | Run `NewsRanker.rank(corpus, profile)` |
| `POST` | `/api/executions/select` | Run `NewsRanker.select(corpus, m, profile)` |
| `POST` | `/api/executions/compare` | Run `NewsRanker.compare_profiles(corpus, profiles)` |
| `GET` | `/api/executions` | List with filters: `corpus_id`, `kind`, `status`, pagination |
| `GET` | `/api/executions/{id}` | Detail: status, config, results, evaluation artifacts |
| `POST` | `/api/executions/{id}/replay` | Create a new execution that **reuses the same `config_json`** against the same (or a different) corpus |
| `DELETE` | `/api/executions/{id}` | Removes an execution and its results |

`POST /executions/rank` payload (representative):

```json
{
  "corpus_id": "…",
  "profile": "representative",
  "config": {
    "similarity_threshold": 0.85,
    "linkage": "average",
    "coverage_weighting": "consensus",
    "selection_mode": "mmr",
    "selection_lambda": 0.8,
    "top_m": 3,
    "profiles": {
      "representative": {"centrality": 0.4, "coverage": 0.5,
                         "density": 0.1, "entity_coverage": 0.0}
    }
  }
}
```

If `config` is omitted, the server uses the library default `RankerConfig()`. The full **effective** config — including library defaults filled in — is what gets persisted to `execution.config_json`, so replay is faithful.

The endpoint returns `202 Accepted` with `{execution_id, status: "pending"}`. Progress is polled via `GET /api/executions/{id}` until `status` becomes `succeeded` or `failed`.

### 5.3 Result serialization

The library's result records (`RankResult`, `SelectionResult`, `ProfileComparison`, `RankDiagnostics`, `FactUniverse`) are frozen dataclasses. The backend serializes them with a small `to_jsonable()` shim:

- Numpy arrays → nested Python lists.
- `ScoreVector` → `{values: [...], defined: bool}`.
- `FactUniverse` → `{article_ids, raw_facts, canonical_fact_texts, cluster_members, coverage_matrix}` with `coverage_matrix` cast to `int` lists.
- `RankingEntry` → `{article_id, rank, score, components}`.

Stored in `execution_result.result_json`. The same shim reverses for loading old executions back into the UI.

> **Why a dedicated shim and not `pydantic.TypeAdapter`:** the library returns frozen dataclasses with numpy fields; a manual shim keeps numpy → list conversion explicit and round-trips through SQLite without third-party serializers. Snapshot tests on this shim catch silent library schema drift.

<a id="config-validation"></a>

### 5.4 Configuration validation

Server-side validation mirrors `RankerConfig.__post_init__`: profile weights non-negative, sum to 1, all four component keys present, etc. Errors return `422` with the violated field path. The UI form ([§6.4](#parameter-form)) uses the same OpenAPI-published schema so client-side checks stay in sync.

### 5.5 Evaluation endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/executions/{id}/eval/top-m-overlap` | Body: `{other_execution_id, m}` |
| `POST` | `/api/executions/{id}/eval/rank-correlation` | Body: `{other_execution_id, method: "kendall"\|"spearman"}` |
| `POST` | `/api/executions/{id}/eval/component-table` | Body: `{}` — works on rank/compare results |
| `POST` | `/api/executions/{id}/eval/cluster-inspection` | Body: `{rare_threshold: int}` |
| `POST` | `/api/executions/{id}/eval/user-study-bundle` | Body: `{materials: {article_id: {title?, snippet?, summary?}}, include_scores: bool}` |
| `GET` | `/api/executions/{id}/eval` | Lists all `evaluation_artifact` rows for the execution |

Each call instantiates the relevant helper from `news_ranker.evaluate`, stores the result in `evaluation_artifact`, and returns it. Helpers are pure and synchronous, so these endpoints do not need background tasks.

`POST /api/executions/{id}/test-suite` runs the **entire** evaluation suite (top-M overlap and rank-correlation against a required, explicit `baseline_execution_id`, component table, cluster inspection, and a user-study bundle if materials are supplied) in one call and returns the list of created artifacts. This is what the "test the algorithm with the whole testing suite" button in [§6.4](#parameter-form) invokes. The endpoint rejects requests without a baseline so comparisons stay explicit.

---

<a id="ui-pages"></a>

## 6. UI Pages

The SPA is intentionally small. Five pages, all wired to the API above.

### 6.1 Corpora (landing)

- List of corpora with article count and last-execution timestamp.
- "New corpus" → name + notes form, then a drag-and-drop zone to upload one or more `.txt` files. Each upload row shows decompose status (queued / decomposed / cached-hit).
- Click into a corpus to see its articles.

### 6.2 Corpus detail

- Article list: filename, title, body length, decomposition status, "view structured" button.
- "View structured" opens a side panel showing the cached `StructuredArticle` (entities, events, claims) so the user can inspect Mistral output before running rankings.
- Buttons: "Run rank", "Run select", "Run compare profiles". Each opens the parameter form ([§6.4](#parameter-form)).

### 6.3 Execution detail

For a single execution:

- **Header**: kind, profile(s), status, created/finished timestamps, corpus link.
- **Parameters panel**: pretty-printed `config_json` plus a "View raw" toggle. Read-only on past executions; this is the "see parameters of an old execution" requirement.
- **Replay button**: opens the parameter form ([§6.4](#parameter-form)) **pre-filled** from `config_json`, so the user can edit and re-run.
- **Results panel**:
  - For `rank`: ranked table with article id, score, per-component scores (centrality / coverage / density / entity_coverage). Sort, filter, expand to see fact-coverage diagnostics.
  - For `select`: same table, plus a "Selected" badge on the chosen-`m` rows. MMR-selected runs also show a small order-vs-rank chart.
  - For `compare_profiles`: a side-by-side table, one column per profile, with rank-change arrows between them.
- **Evaluation panel**: buttons for each helper ([§5.5](#backend-api)), plus a required baseline picker and a single "Run full test suite" button that triggers `/test-suite` and renders the resulting artifacts inline. Each artifact has its own renderer:
  - Top-M overlap → counts + Jaccard + the overlapping article ids.
  - Rank correlation → coefficient + left-only/right-only ids.
  - Component score table → table of (profile, article_id, rank, score, components…).
  - Cluster inspection → expandable rows per cluster: canonical text, support article ids, member raw facts, `is_rare` flag.
  - User-study bundle → JSON download + an inline preview of `selected_article_labels` and the anonymized materials.

<a id="parameter-form"></a>

### 6.4 Parameter form

Used both for new runs and for replay. Fields:

- Profile picker (single or multi for `compare_profiles`) with weights editable per profile (centrality / coverage / density / entity_coverage). Weights validated client-side to sum to 1.
- Clustering knobs: `similarity_threshold`, `linkage` (average | single).
- Coverage knobs: `coverage_weighting` (consensus | rarity).
- Selection knobs (when applicable): `selection_mode` (top_score | mmr | rarity), `selection_lambda`, `top_m`. Advanced modes are exposed rather than hidden.
- Metadata knobs (read-only, since current pipeline treats them as metadata only): `llm_model_name`, `prompt_version`, `schema_version`, `embedding_model_name`.

Submit → POSTs to the matching execution endpoint and navigates to the new execution's detail page.

### 6.5 Executions index ("old executions")

- Table of every execution across all corpora: corpus name, kind, profile, status, started_at, finished_at, has-evaluation badge.
- Filters: corpus, kind, status, date range, profile.
- Actions per row: open detail, replay, delete, "compare with…" (opens a modal that lets the user pick a second execution and runs `top_m_overlap` + `rank_correlation` on the spot, persisting them as `evaluation_artifact` rows on the right-hand execution).

> **Why this page is the answer to "see the old executions":** it is the only UI surface that lists executions across corpora, and its row-level "compare with" action is the cheapest way to validate a new run against an older baseline without first navigating to the detail page.

---

<a id="evaluation-integration"></a>

## 7. Evaluation Helper Integration

The library's evaluation helpers are pure functions over result records (see `docs/context/ranking-evaluation-helpers.md`). The mapping from UI button to helper is:

| UI action | Helper call |
|---|---|
| "Top-M overlap" | `top_m_overlap(rank_a, rank_b, m)` where `rank_a`, `rank_b` are `RankResult` rebuilt from `execution_result.result_json` |
| "Rank correlation" | `rank_correlation(rank_a, rank_b, method)` |
| "Component table" | `component_score_table(rank_or_comparison)` — accepts a single `RankResult`, a list, or a `ProfileComparison` |
| "Cluster inspection" | `cluster_inspection_rows(rank_result, rare_threshold)` against `rank_result.diagnostics.fact_universe` |
| "User-study bundle" | `anonymized_user_study_bundle(selection_result, materials, include_scores)` |
| "Run full test suite" | All of the above, against a baseline execution explicitly selected by the user. No implicit fallback baseline. |

Rebuilding records from JSON: a small `from_jsonable()` mirror of [§5.3](#backend-api) re-creates the frozen dataclasses. `FactUniverse.coverage_matrix` is cast back to `np.ndarray` so `cluster_inspection_rows` can index it.

> **Why round-trip through JSON instead of caching the live dataclasses in memory:** executions outlive the process. The container can restart, the user can come back tomorrow, and the "run full test suite" button still has to work against an execution from yesterday. JSON is the only durable representation.

---

<a id="provider-wiring"></a>

## 8. Mistral & Embedding Wiring

### 8.1 Mistral

Per `docs/context/mistral-llm-provider.md`:

- App startup constructs one `MistralDecompositionClient(api_key=settings.MISTRAL_API_KEY)`, where `settings` is the `pydantic-settings` object loaded from environment (which Compose populates from `livedemo/.env`; see [§11.7](#env-loading)). Failure to find the key is a fatal startup error so the operator knows immediately.
- `decompose()` is called via the injected hook `lambda article: decompose(article, mistral_client, config=DecompositionConfig(model=cfg.llm_model_name), cache_dir=CACHE_DIR)`.
- `CACHE_DIR = /var/livedemo/cache/decompose/` on the `livedemo_cache` volume. The library's existing cache key (raw payload + model + prompt version + schema version) is unchanged; the demo just gives it a stable directory.
- Whenever the on-disk cache writes a new entry, the backend mirrors the resulting `StructuredArticle` into `structured_article` ([§4](#data-model)) for UI display. The mirror is best-effort; the disk cache remains canonical.
- The library API is synchronous, so the FastAPI handler runs it under `asyncio.to_thread` and streams progress through the `execution.status` field.

### 8.2 Embeddings

- One `SentenceTransformerEmbedder` per process, loaded at startup. Model name comes from `RankerConfig.embedding_model_name` (currently metadata in the library; the demo honors it as the actual embedder choice).
- The `news_ranker` library's existing fact-embedding cache (if/when added in the library) is reused; otherwise embeddings are recomputed per run. The demo does not introduce its own embedding cache; that is a library concern.
- The Hugging Face download lives on a named volume (`hf_cache`) so a second `docker compose up --build` does not re-download the model.

> **Why startup-time embedder construction:** model load time dominates first-request latency. Loading once at startup turns it into a cold-start cost the operator pays during deploy, not a UX cost the first user pays.

---

<a id="repo-layout"></a>

## 9. Repo Layout

The demo lives entirely under `livedemo/`. The Compose build context is the **repo root** so that the `news_ranker` package can be installed into the backend image without copying it into `livedemo/` or publishing it to a registry.

```
article-ranking/                ← repo root, also the Compose build context
├── news_ranker/                ← existing library (unchanged)
├── pyproject.toml              ← existing library project file
└── livedemo/
    ├── docs/
    │   └── brief.md            ← this document
    ├── README.md               ← "docker compose up", env vars, troubleshooting
    ├── docker-compose.yml      ← prod-style: backend + frontend + volumes
    ├── docker-compose.dev.yml  ← dev override: bind-mounts, vite HMR, --reload
    ├── .env.example            ← MISTRAL_API_KEY=, BACKEND_PORT=8000, ...
    ├── .dockerignore           ← excludes var/, node_modules/, __pycache__/, .venv
    ├── docker/
    │   ├── backend.Dockerfile
    │   ├── frontend.Dockerfile
    │   └── nginx.conf          ← serves SPA, proxies /api/* to backend:8000
    ├── pyproject.toml          ← FastAPI + SQLAlchemy + uvicorn; depends on the
    │                              parent news_ranker via a local path dep
    ├── app/
    │   ├── main.py             ← FastAPI entrypoint, startup/shutdown hooks
    │   ├── deps.py             ← shared deps: embedder, mistral client, DB session
    │   ├── config.py           ← pydantic-settings model: reads .env + os env
    │   ├── db/
    │   │   ├── models.py       ← SQLAlchemy declarative models from §4
    │   │   └── session.py
    │   ├── routers/
    │   │   ├── corpora.py
    │   │   ├── articles.py
    │   │   ├── executions.py
    │   │   └── evaluations.py
    │   ├── services/
    │   │   ├── ingestion.py    ← .txt → article rows + decompose trigger
    │   │   ├── pipeline_runner.py ← wraps NewsRanker, persists results
    │   │   └── evaluators.py   ← thin adapters over news_ranker.evaluate helpers
    │   ├── serialize.py        ← to_jsonable / from_jsonable for result records
    │   └── schemas.py          ← Pydantic request/response models
    ├── frontend/
    │   ├── package.json
    │   ├── vite.config.ts
    │   └── src/
    │       ├── pages/{Corpora,CorpusDetail,ExecutionDetail,ExecutionsIndex,ParameterForm}.tsx
    │       ├── api/client.ts   ← OpenAPI-derived
    │       └── components/{ResultTable,ComponentBars,ClusterPanel,…}.tsx
    └── tests/
        ├── conftest.py         ← fake embedder, fake decomposer, in-memory SQLite
        ├── test_corpora.py
        ├── test_articles.py
        ├── test_executions.py
        ├── test_evaluations.py
        └── test_serialize.py

# Persistent runtime state lives in named Docker volumes, NOT in the repo:
#   livedemo_db        → /var/livedemo/db.sqlite
#   livedemo_uploads   → /var/livedemo/uploads/
#   livedemo_cache     → /var/livedemo/cache/    (decompose + future embed cache)
#   hf_cache           → /root/.cache/huggingface (sentence-transformers model)
```

---

<a id="milestones"></a>

## 10. Implementation Order (Milestones)

| # | Milestone | Effort | Checkpoint |
|---|---|---|---|
| 0 | **Docker skeleton** — backend + frontend Dockerfiles, `docker-compose.yml`, `docker-compose.dev.yml`, named volumes, `.env.example` | ½ day | `docker compose up` brings up an empty backend that serves `/api/health` and the SPA shell |
| 1 | **FastAPI app, DB models, health route** wired through Compose | ½ day | `GET /api/health` returns `{ok: true}` from the running backend container |
| 2 | **Corpus + article CRUD** with `.txt` upload | 1 day | Files land on the `livedemo_uploads` volume; bodies stored in the SQLite volume |
| 3 | **Mistral wiring** + decompose-on-upload, structured mirror | 1 day | Article detail shows `StructuredArticle`; second upload of same body hits the on-volume cache |
| 4 | **Execution endpoints** (`rank`, `select`, `compare`) + result serialization | 1½ days | Can run all three kinds end-to-end inside the container |
| 5 | **Parameter form** with full `RankerConfig` validation + replay | ½ day | Replay produces a new execution with byte-identical `config_json` |
| 6 | **Evaluation endpoints** + full-suite button | 1 day | Each helper round-trips through the UI; full-suite runs against a chosen baseline |
| 7 | **Executions index** + cross-execution compare modal | ½ day | "Old executions" view filterable; modal-driven `top_m_overlap` + `rank_correlation` work |
| 8 | **Polish** — prod nginx config, healthchecks, deterministic-replay test, README | ½ day | `docker compose up -d` from a fresh clone yields a working app behind `localhost:8080` |

**Total: ~7 working days.**

---

<a id="docker-setup"></a>

## 11. Docker Setup

The application ships as two containers orchestrated by Compose. Persistent state is on **named volumes**, not bind-mounts, so a `git clean -fdx` does not nuke uploaded corpora or the SQLite DB.

### 11.1 Backend image — `livedemo/docker/backend.Dockerfile`

Multi-stage to keep the runtime image small. The build context is the repo root (`article-ranking/`), so the image can install both the parent `news_ranker` package and the `livedemo` app from local paths.

```dockerfile
# ---- builder ----------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv for fast, lockfile-aware installs
RUN pip install --no-cache-dir uv

WORKDIR /build

# Copy only what is needed to resolve dependencies first (better layer cache)
COPY pyproject.toml uv.lock ./
COPY news_ranker ./news_ranker
COPY livedemo/pyproject.toml ./livedemo/pyproject.toml

# Install parent library + livedemo app into a venv we can copy into the runtime
RUN uv venv /opt/venv \
 && . /opt/venv/bin/activate \
 && uv pip install --no-cache-dir -e . \
 && uv pip install --no-cache-dir -e ./livedemo

# Now bring in the actual livedemo source
COPY livedemo/app ./livedemo/app

# ---- runtime ----------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    LIVEDEMO_VAR_DIR=/var/livedemo \
    HF_HOME=/root/.cache/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --uid 1000 livedemo \
    && mkdir -p /var/livedemo /root/.cache/huggingface \
    && chown -R livedemo:livedemo /var/livedemo /root/.cache/huggingface

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/livedemo /app/livedemo
COPY --from=builder /build/news_ranker /app/news_ranker

WORKDIR /app
USER livedemo

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "livedemo.app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
```

> **Why multi-stage with a copied venv:** the builder needs `build-essential` and `git` for any wheel that needs compiling; the runtime does not. Copying `/opt/venv` gives the runtime image the Python deps without dragging the toolchain along, which keeps the final image around 350–500 MB depending on the `torch` wheel pulled by `sentence-transformers`.
>
> **Why `libgomp1`:** the only system runtime dep needed by `sentence-transformers`/`torch` in the slim image. Without it imports fail with a clear `libgomp.so.1: cannot open shared object file` error at startup.
>
> **Why `HF_HOME` on a volume:** the embedding model is several hundred MB. Pinning the cache to `hf_cache` means a `docker compose up --build` rebuild reuses the download instead of pulling it again.

### 11.2 Frontend image — `livedemo/docker/frontend.Dockerfile`

```dockerfile
# ---- builder ----------------------------------------------------------------
FROM node:20-alpine AS builder
WORKDIR /app
COPY livedemo/frontend/package.json livedemo/frontend/package-lock.json ./
RUN npm ci
COPY livedemo/frontend ./
RUN npm run build   # → /app/dist

# ---- runtime ----------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime
COPY livedemo/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null || exit 1
```

`livedemo/docker/nginx.conf` serves the SPA and reverse-proxies `/api/*` to the backend service over the Compose network:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;   # long-running pipeline runs
    }
}
```

### 11.3 Compose — production

`livedemo/docker-compose.yml`:

```yaml
name: livedemo

services:
  backend:
    build:
      context: ..
      dockerfile: livedemo/docker/backend.Dockerfile
    image: livedemo-backend:latest
    # Compose interpolates ${...} from livedemo/.env at `up` time, AND
    # passes the file into the container via env_file so pydantic-settings
    # can also read it directly. Either path alone would work; we use both
    # so dev overrides (compose interpolation) and runtime reads
    # (settings.MISTRAL_API_KEY) stay in sync. See §11.7.
    env_file:
      - .env
    environment:
      # Required, fail-fast if missing in .env
      MISTRAL_API_KEY: ${MISTRAL_API_KEY:?MISTRAL_API_KEY is required in livedemo/.env}
      # Container-internal paths — fixed regardless of .env
      LIVEDEMO_DB_URL: sqlite:////var/livedemo/db.sqlite
      LIVEDEMO_UPLOADS_DIR: /var/livedemo/uploads
      LIVEDEMO_CACHE_DIR: /var/livedemo/cache
      # Optional, falls back if .env omits it
      LIVEDEMO_CORS_ORIGINS: ${LIVEDEMO_CORS_ORIGINS:-http://localhost:8080}
    volumes:
      - livedemo_db:/var/livedemo
      - livedemo_uploads:/var/livedemo/uploads
      - livedemo_cache:/var/livedemo/cache
      - hf_cache:/root/.cache/huggingface
    expose:
      - "8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  frontend:
    build:
      context: ..
      dockerfile: livedemo/docker/frontend.Dockerfile
    image: livedemo-frontend:latest
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "${FRONTEND_PORT:-8080}:80"
    restart: unless-stopped

volumes:
  livedemo_db:
  livedemo_uploads:
  livedemo_cache:
  hf_cache:
```

Operator workflow:

```bash
cp livedemo/.env.example livedemo/.env       # fill in MISTRAL_API_KEY
docker compose -f livedemo/docker-compose.yml up -d --build
# → http://localhost:8080
docker compose -f livedemo/docker-compose.yml logs -f backend
docker compose -f livedemo/docker-compose.yml down            # keeps volumes
docker compose -f livedemo/docker-compose.yml down -v         # nukes state
```

<a id="compose-dev"></a>

### 11.4 Compose — development override

`livedemo/docker-compose.dev.yml` is layered on top of the prod file (`docker compose -f docker-compose.yml -f docker-compose.dev.yml up`). It:

- Bind-mounts `livedemo/app` into the backend container and runs `uvicorn --reload` for hot-reload of Python.
- Replaces the nginx frontend with a `node:20-alpine` container running `npm run dev -- --host 0.0.0.0`, exposed on `:5173`, with `livedemo/frontend` bind-mounted and a named volume for `node_modules` to avoid host/container ABI mismatches.
- Sets `LIVEDEMO_CORS_ORIGINS=http://localhost:5173` so the dev SPA can hit the backend directly.
- Exposes `:8000` on the host so `pytest`-driven smoke tests on the host can also hit the running backend.

### 11.5 Running tests in Docker

`livedemo/docker-compose.test.yml` defines a one-shot `backend-test` service that builds the same image with `--target=builder`, mounts the test directory, and runs `pytest -q livedemo/tests`. CI calls:

```bash
docker compose -f livedemo/docker-compose.test.yml run --rm backend-test
```

Tests use the in-memory SQLite engine and the library's fake embedder/decomposer fixtures, so this stage does not need network access or `MISTRAL_API_KEY`.

### 11.6 Image hardening checklist

- Non-root runtime user (`livedemo`, uid 1000).
- Slim base + multi-stage build → final backend image around 350–500 MB depending on `torch` wheel pulled by `sentence-transformers`.
- Read-only root filesystem can be enabled in Compose with `read_only: true` + tmpfs on `/tmp`; left off by default to keep first-run friction low. Recommended once the image stabilizes.
- `MISTRAL_API_KEY` is passed only via env, never baked into a layer.
- `.dockerignore` excludes `var/`, `node_modules/`, `__pycache__/`, `.venv/`, `.git/`, and editor caches so the build context stays small and secret-free.

---

<a id="testing-strategy"></a>

## 12. Testing Strategy

- **Backend unit tests** with `pytest`. Use the library's own fake embedder/fake decomposer fixtures from `tests/test_pipeline.py` so the demo's API tests do not download models or call Mistral.
- **HTTP tests** via `httpx.AsyncClient(app=app)` covering: corpus + article CRUD, upload, rank/select/compare execution lifecycle, replay equivalence (a replay's `config_json` must equal the source's), every evaluation endpoint, and the full-suite endpoint.
- **Determinism check.** Run `rank` twice on the same corpus with the same config and assert identical `result_json`. Library tests already cover ordering determinism; this just ensures the serialization round-trip preserves it.
- **Migration safety.** Snapshot tests on `to_jsonable()` / `from_jsonable()` for `RankResult` and `SelectionResult` so library schema additions surface as test failures, not silent data loss.
- **Docker test stage.** `docker-compose.test.yml` (see [§11.5](#docker-setup)) so CI runs the same tests in the same image stack as production.

> **Why determinism is its own test:** the library is already deterministic; this test exists to catch the demo introducing non-determinism via `dict` ordering, JSON encoder choices, or numpy/list round-trips. It is the cheapest signal that "replay" actually replays.

---

<a id="resolved-decisions"></a>

## 13. Resolved Decisions

1. Full-suite evaluation always requires an explicit baseline execution. No default to "most recent run on the same corpus".
2. Advanced ranking/selection knobs are exposed in the UI, including `selection_mode="rarity"` and `linkage="single"`.
3. Keep the `structured_article` DB mirror; do not replace it with disk-cache reads only.
4. Keep v1 single-tenant. No user model or per-user corpora.
5. User-study bundle export is downloaded JSON only. No shareable read-only links in v1.

---

*End of design document.*

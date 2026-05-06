# News Ranker Live Demo — Design Document

> A Python-backed web application that lives in the `livedemo/` folder of the parent `article-ranking` project and exposes the local `news_ranker` library for interactive use: upload article corpora as plain text, decompose them with Mistral, run the ranking algorithm with configurable parameters, replay and compare past executions, and run the full evaluation/comparison suite (`news_ranker.evaluate`) against those executions.

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
10. [Development Docker Setup](#docker-setup)
11. [Testing Strategy](#testing-strategy)
12. [Resolved Decisions](#resolved-decisions)
13. [Implementation Order (Milestones)](#milestones)

---

<a id="goals"></a>

## 1. Goals

The demo site is a thin, opinionated UI on top of the existing library. It exists to:

1. **Demonstrate** the public pipeline (`NewsRanker.rank` / `select` / `compare_profiles`) end-to-end on user-supplied corpora, not just on bundled fixtures.
2. **Make decomposition output visible** by persisting Mistral structured results in SQLite for inspection.
3. **Make experiments reproducible**: every execution stores its full input set, the `RankerConfig` parameters used, and the resulting ranking/selection so a past run can be replayed, inspected, or compared against a new one.
4. **Surface the evaluation helpers** (`top_m_overlap`, `rank_correlation`, `component_score_table`, `cluster_inspection_rows`, `anonymized_user_study_bundle`) as first-class UI features, not just library internals.

The application lives entirely under `livedemo/` inside the parent repository. The Compose build context is the project root so the backend can install and import the local `news_ranker` package without publishing it. Local development uses Compose with bind-mounts and hot-reload (see [§10](#docker-setup)).

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
- Docker + Compose — development runtime with bind-mounts and hot-reload.

---

<a id="architecture"></a>

## 3. Architecture

```
article-ranking/ repo root
├── news_ranker/                 # imported library
└── livedemo/                    # demo app
    ├── backend container         # uvicorn + FastAPI + news_ranker
    │   ├── Mistral client
    │   ├── SentenceTransformerEmbedder
    │   └── SQLAlchemy + SQLite DB
    └── frontend dev container    # Vite dev server with HMR

Browser ── :5173 ──► frontend ── /api ──► backend ──► SQLite
```

The app is project-aware: `livedemo/` is a subproject, while the Compose build context remains the parent repo root so imports and editable installs use the local `news_ranker` package.

### 3.1 Backend stack

- **Web framework**: FastAPI. Tight Pydantic v2 fit (already a project dep), automatic OpenAPI for the SPA to consume, async layer that pays off for long-running Mistral calls via background tasks.
- **ORM**: SQLAlchemy 2.x with SQLite. SQLite is enough for a demo; one DB file stores corpora, articles, decompositions, executions, results, and evaluation artifacts. Alembic migrations only if the schema starts churning.
- **Background jobs**: FastAPI `BackgroundTasks` for short Mistral calls; a `concurrent.futures.ThreadPoolExecutor` wrapper for full pipeline runs so the request returns immediately with an `execution_id` while the run executes. No Celery/Redis — the demo stays single-process inside one container.
- **Library wiring**: instantiate `NewsRanker(embedder, config, decomposer=...)` per request, where:
  - `embedder` is a process-singleton `SentenceTransformerEmbedder` loaded at app startup.
  - `decomposer` is `lambda article: decompose(article, mistral_client, config=DecompositionConfig(...))`, also a process singleton.
  - `config` is built from the request payload (see [§5.4](#config-validation)).

> **Why FastAPI + SQLite + single-process**: the demo's load profile is one student at a time clicking "Run". The pipeline cost is dominated by Mistral latency and embedding compute, not request fan-out. A single-process app with one SQLite DB is simplest.

### 3.2 Frontend

A small React + Vite SPA. Pages described in [§6](#ui-pages). State lives in TanStack Query against the FastAPI endpoints; no server-side rendering. Development uses a `vite dev` container with HMR (see [§10](#docker-setup)).

---

<a id="data-model"></a>

## 4. Data Model

All persistent state lives in one SQLite DB.

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
├── uploaded_at     (timestamptz)
└── UNIQUE(corpus_id, filename)

structured_article          # persisted output of one Mistral decomposition
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

> **Why persist `structured_article` in SQL:** the UI can display extracted facts/entities and all demo state stays in one DB.
>
> **Why `execution.config_json` and not normalized columns:** `RankerConfig` evolves with the library; flat JSON keeps the demo schema decoupled from library-side knob changes and makes "view parameters of an old execution" a single field read. The replay endpoint uses this column verbatim.

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
| `POST` | `/api/corpora/{id}/articles` | `multipart/form-data` upload: one or more `.txt` files. Server reads each file, persists `article` rows, returns the new article ids. |
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
- "New corpus" → name + notes form, then a drag-and-drop zone to upload one or more `.txt` files. Each upload row shows decompose status (queued / decomposed / failed).
- Click into a corpus to see its articles.

### 6.2 Corpus detail

- Article list: filename, title, body length, decomposition status, "view structured" button.
- "View structured" opens a side panel showing the persisted `StructuredArticle` (entities, events, claims) so the user can inspect Mistral output before running rankings.
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

> **Why round-trip through JSON instead of keeping live dataclasses in memory:** executions outlive the process. The container can restart, the user can come back tomorrow, and the "run full test suite" button still has to work against an execution from yesterday. JSON is the durable DB representation.

---

<a id="provider-wiring"></a>

## 8. Mistral & Embedding Wiring

### 8.1 Mistral

Per `docs/context/mistral-llm-provider.md`:

- App startup constructs one `MistralDecompositionClient(api_key=settings.MISTRAL_API_KEY)`, where `settings` is the `pydantic-settings` object loaded from environment (which Compose populates from `livedemo/.env`). Failure to find the key is a fatal startup error.
- `decompose()` is called via the injected hook `lambda article: decompose(article, mistral_client, config=DecompositionConfig(model=cfg.llm_model_name))`.
- Resulting `StructuredArticle` payloads are persisted directly in `structured_article` for UI display.
- The library API is synchronous, so the FastAPI handler runs it under `asyncio.to_thread` and streams progress through the `execution.status` field.

### 8.2 Embeddings

- One `SentenceTransformerEmbedder` per process, loaded at app startup.
- Model name comes from `RankerConfig.embedding_model_name` (currently metadata in the library; the demo honors it as the actual embedder choice).
- Embeddings are computed by the library/embedder path; the demo adds no separate embedding store.

> **Why startup-time embedder construction:** model load time dominates first-request latency. Loading once at startup turns it into a cold-start cost, not a first-user cost.

---

<a id="repo-layout"></a>

## 9. Repo Layout

The demo lives entirely under `livedemo/`. The Compose build context is the **repo root** so the backend can install the parent `news_ranker` package from local paths.

```
article-ranking/                ← repo root, also Compose build context
├── news_ranker/                ← existing library (unchanged)
├── pyproject.toml              ← existing library project file
└── livedemo/
    ├── docs/
    │   └── brief.md            ← this document
    ├── README.md               ← dev startup, env vars, troubleshooting
    ├── docker-compose.yml      ← dev stack: backend + Vite frontend
    ├── .env.example            ← MISTRAL_API_KEY=, BACKEND_PORT=8000, ...
    ├── docker/
    │   └── backend.Dockerfile
    ├── pyproject.toml          ← FastAPI + SQLAlchemy + uvicorn; depends on parent news_ranker
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
    │   │   └── evaluators.py   ← adapters over news_ranker.evaluate helpers
    │   ├── serialize.py        ← to_jsonable / from_jsonable for result records
    │   └── schemas.py          ← Pydantic request/response models
    ├── frontend/
    │   ├── package.json
    │   ├── vite.config.ts
    │   └── src/
    │       ├── pages/{Corpora,CorpusDetail,ExecutionDetail,ExecutionsIndex,ParameterForm}.tsx
    │       ├── api/client.ts
    │       └── components/{ResultTable,ComponentBars,ClusterPanel,…}.tsx
    └── tests/
        ├── conftest.py         ← fake embedder, fake decomposer, in-memory SQLite
        ├── test_corpora.py
        ├── test_articles.py
        ├── test_executions.py
        ├── test_evaluations.py
        └── test_serialize.py
```

Runtime state: one SQLite DB file. Uploaded article bodies are also stored in DB.

---

<a id="docker-setup"></a>

## 10. Development Docker Setup

Compose is for local development only. It runs backend and Vite frontend with bind-mounts and hot reload.

### 10.1 Backend service

- Build context: repo root (`article-ranking/`) so image can install parent `news_ranker` and `livedemo` from local paths.
- Command: `uvicorn livedemo.app.main:app --host 0.0.0.0 --port 8000 --reload`.
- Bind-mounts: `livedemo/app` for hot reload.
- Env: `MISTRAL_API_KEY`, `LIVEDEMO_DB_URL=sqlite:////var/livedemo/db.sqlite`, `LIVEDEMO_CORS_ORIGINS=http://localhost:5173`.
- State: one SQLite DB file.

### 10.2 Frontend dev service

- Image: `node:20-alpine`.
- Command: `npm run dev -- --host 0.0.0.0`.
- Bind-mount: `livedemo/frontend`.
- Port: `5173`.
- API calls hit backend directly at `http://localhost:8000/api`.

### 10.3 Operator workflow

```bash
cp livedemo/.env.example livedemo/.env       # fill in MISTRAL_API_KEY
docker compose -f livedemo/docker-compose.yml up --build
# frontend → http://localhost:5173
# backend  → http://localhost:8000/api/health
docker compose -f livedemo/docker-compose.yml logs -f backend
docker compose -f livedemo/docker-compose.yml down
```

### 10.4 Running tests in Docker

`livedemo/docker-compose.test.yml` can define a one-shot backend test service that mounts tests and runs:

```bash
pytest -q livedemo/tests
```

Tests use in-memory SQLite and fake embedder/decomposer fixtures, so they do not need network access or `MISTRAL_API_KEY`.

---

<a id="testing-strategy"></a>

## 11. Testing Strategy

- **Backend unit tests** with `pytest`. Use fake embedder/fake decomposer fixtures so API tests do not download models or call Mistral.
- **HTTP tests** via `httpx.AsyncClient(app=app)` covering: corpus + article CRUD, upload, rank/select/compare execution lifecycle, replay equivalence, every evaluation endpoint, and full-suite endpoint.
- **Determinism check.** Run `rank` twice on same corpus with same config and assert identical `result_json`.
- **Migration safety.** Snapshot tests on `to_jsonable()` / `from_jsonable()` for `RankResult` and `SelectionResult` so library schema additions surface as test failures.
- **Docker test stage.** Optional Compose test service runs same pytest suite inside backend image.

> **Why determinism is its own test:** catches demo-introduced non-determinism via `dict` ordering, JSON encoder choices, or numpy/list round-trips.

---

<a id="resolved-decisions"></a>

## 12. Resolved Decisions

1. Full-suite evaluation always requires an explicit baseline execution. No default to "most recent run on the same corpus".
2. Advanced ranking/selection knobs are exposed in the UI, including `selection_mode="rarity"` and `linkage="single"`.
3. Store `StructuredArticle` in SQLite.
4. Keep v1 single-tenant. No user model or per-user corpora.
5. User-study bundle export is downloaded JSON only. No shareable read-only links in v1.

---

<a id="milestones"></a>

## 13. Implementation Order (Milestones)

Each milestone is intended to become its own implementation plan. "Proposed commits" use Conventional Commits (`feat(scope): summary`, `test(scope): summary`, `docs(scope): summary`, `chore(scope): summary`). They are logical commits and may be squashed by an implementation plan.

### Milestone 1 — Dev Docker skeleton

**Goal:** Create the `livedemo/` project shell and prove backend + frontend can run from inside the parent repo.

**Spec refs:** §2 Stack, §3 Architecture, §9 Repo Layout, §10 Development Docker Setup.

**Implement/change:**

- Create `livedemo/pyproject.toml` with backend deps and a local path dependency on the parent `news_ranker` package, matching §2 Stack and §9 Repo Layout.
- Add `livedemo/app/main.py` with a minimal FastAPI app and `GET /api/health`, matching §5 backend route style.
- Add `livedemo/app/config.py` with environment loading for `MISTRAL_API_KEY`, DB URL, CORS origins, and dev ports, matching §8 Mistral wiring and §10 Docker setup.
- Add `livedemo/docker/backend.Dockerfile` using repo root as build context so the backend installs parent package + livedemo package, matching §3 Architecture and §9 Repo Layout.
- Add `livedemo/docker-compose.yml` for backend + Vite frontend dev services with bind-mounts and hot reload, matching §10 Development Docker Setup.
- Add `livedemo/.env.example` with required and optional settings.
- Add minimal `livedemo/frontend` Vite/React app shell that calls or links to `/api/health`, matching §6 UI Pages baseline.
- Add initial README instructions for dev startup.

**Proposed commits:**

1. `feat(livedemo): add backend package skeleton and health app`
2. `chore(livedemo): add dev Dockerfile and compose stack`
3. `feat(frontend): add Vite shell for live demo`
4. `docs(livedemo): document local dev startup`

**Checkpoint:** `docker compose -f livedemo/docker-compose.yml up --build` starts backend and frontend; `GET /api/health` returns `{ok: true}`.

### Milestone 2 — FastAPI app foundation and DB models

**Goal:** Replace skeleton with real app structure and SQLite persistence primitives.

**Spec refs:** §3.1 Backend stack, §4 Data Model, §5 Backend API, §11 Testing Strategy.

**Implement/change:**

- Create `app/db/session.py` with SQLAlchemy engine/session setup driven by `LIVEDEMO_DB_URL`, matching §3.1 Backend stack.
- Create `app/db/models.py` with `corpus`, `article`, `structured_article`, `execution`, `execution_result`, and `evaluation_artifact` models exactly from §4 Data Model.
- Add startup hook that creates tables for v1 if they do not exist.
- Add dependency providers in `app/deps.py` for settings and DB sessions.
- Add shared Pydantic schemas in `app/schemas.py` for IDs, timestamps, health response, and common error responses, matching §5 API JSON contract.
- Add test fixtures for isolated in-memory SQLite sessions, matching §11 Testing Strategy.
- Add smoke tests for app startup, health route, and table creation.

**Proposed commits:**

1. `feat(db): add SQLAlchemy session and models`
2. `feat(api): wire dependencies and table startup`
3. `feat(api): add shared schemas`
4. `test(db): cover health route and schema creation`

**Checkpoint:** backend starts through Compose, creates SQLite tables, and tests can run against in-memory SQLite.

### Milestone 3 — Corpus and article CRUD

**Goal:** Support corpus management and `.txt` article ingestion with article bodies stored in SQLite.

**Spec refs:** §2 Input contract, §4 Data Model, §5.1 Corpus & article management, §6.1 Corpora, §6.2 Corpus detail.

**Implement/change:**

- Add `app/routers/corpora.py` with create/list/detail/delete corpus endpoints from §5.1.
- Add `app/routers/articles.py` with article upload, article detail, and delete-by-corpus behavior from §5.1.
- Add `app/services/ingestion.py` with `.txt` validation, title heuristic, body decoding, duplicate filename handling, and DB writes, matching §2 Input contract and §5.1 title heuristic.
- Add Pydantic request/response schemas for corpus summaries, corpus detail, upload responses, and article detail, matching §5 API shapes.
- Wire routers into `main.py` under `/api`.
- Add frontend API client functions for corpora/articles.
- Implement basic Corpora landing page and Corpus detail page from §6.1 and §6.2.
- Add tests for corpus CRUD, article upload, title heuristic, non-`.txt` rejection, duplicate filename behavior, and cascade delete.

**Proposed commits:**

1. `feat(api): add corpus endpoints and schemas`
2. `feat(api): add article ingestion and upload endpoints`
3. `feat(frontend): add corpora and corpus detail pages`
4. `test(api): cover corpus CRUD and article uploads`

**Checkpoint:** user can create a corpus, upload `.txt` files, view article list/detail, and see bodies persisted in SQLite.

### Milestone 4 — Mistral decomposition persistence

**Goal:** Decompose uploaded articles with Mistral and persist `StructuredArticle` payloads in SQLite for UI inspection.

**Spec refs:** §4 `structured_article`, §5.1 article detail/decompose endpoints, §6.2 structured side panel, §8.1 Mistral.

**Implement/change:**

- Add Mistral client provider in `app/deps.py`, failing fast when `MISTRAL_API_KEY` is missing outside test mode, matching §8.1.
- Add service function that builds `DecompositionConfig` from effective ranker settings and calls `decompose(article, mistral_client, config=...)`, matching §8.1.
- Persist resulting `StructuredArticle.model_dump()` into `structured_article` with model/prompt/schema metadata, matching §4.
- Trigger decomposition after upload via background task and expose manual `POST /api/articles/{id}/decompose`, matching §5.1.
- Extend article detail endpoint with latest structured payload and decomposition status, matching §6.2.
- Add frontend side panel for persisted entities/events/claims from §6.2.
- Add fake decomposer fixtures for tests.
- Add tests for decompose endpoint, persistence metadata, failed decomposition status/error handling, and article detail payload shape.

**Proposed commits:**

1. `feat(llm): add Mistral decomposition service`
2. `feat(db): persist structured article payloads`
3. `feat(api): expose decomposition endpoints and status`
4. `feat(frontend): render structured article inspection panel`
5. `test(llm): cover decomposition persistence paths`

**Checkpoint:** article detail shows persisted `StructuredArticle`; manual re-decompose updates visible structured output.

### Milestone 5 — Execution endpoints and result serialization

**Goal:** Run `rank`, `select`, and `compare_profiles` end-to-end and persist durable JSON results.

**Spec refs:** §4 execution/result models, §5.2 Execution endpoints, §5.3 Result serialization, §8.2 Embeddings, §6.3 Execution detail.

**Implement/change:**

- Add `app/serialize.py` with `to_jsonable()` and `from_jsonable()` for library dataclasses, numpy arrays, `ScoreVector`, `FactUniverse`, and ranking entries, matching §5.3.
- Add execution schemas for rank/select/compare requests, status responses, result detail, and filters, matching §5.2.
- Add config normalization that stores full effective `RankerConfig` plus selection params in `execution.config_json`, matching §5.2 and §5.4.
- Add `app/services/pipeline_runner.py` to load corpus articles, build `NewsRanker`, run requested method in a worker thread, update status timestamps/errors, and write `execution_result` rows, matching §3.1 and §5.2.
- Add `app/routers/executions.py` with POST rank/select/compare, list, detail, delete from §5.2.
- Add fake embedder/decomposer execution fixtures, matching §11.
- Add frontend execution polling and basic Execution detail result table for rank/select/compare from §6.3.
- Add tests for serialization round-trip, successful execution lifecycle, failed execution status, listing filters, and result detail payloads.

**Proposed commits:**

1. `feat(serialization): add result JSON shims`
2. `feat(api): add execution schemas and config normalization`
3. `feat(pipeline): implement runner service`
4. `feat(api): expose rank select compare endpoints`
5. `feat(frontend): render execution polling and result tables`
6. `test(pipeline): cover execution lifecycle and serialization`

**Checkpoint:** user can run rank/select/compare in container, poll status, reload page, and still view persisted results.

### Milestone 6 — Parameter form and replay

**Goal:** Provide editable ranking parameters for new runs and faithful replay of old executions.

**Spec refs:** §5.2 replay endpoint, §5.4 Configuration validation, §6.3 Replay button, §6.4 Parameter form.

**Implement/change:**

- Add server-side validation mirroring `RankerConfig.__post_init__`, including component keys, non-negative weights, weight sums, linkage values, coverage mode, selection mode, and `top_m` constraints, matching §5.4.
- Publish validation schema through FastAPI/OpenAPI response models, matching §5.4.
- Implement frontend Parameter form with profile weights, clustering knobs, coverage knobs, selection knobs, and read-only metadata knobs, matching §6.4.
- Add prefill from default config for new runs and from `execution.config_json` for replay, matching §6.3 and §6.4.
- Add `POST /api/executions/{id}/replay` to create a new execution from prior config, optionally against a different corpus, matching §5.2.
- Add UI Replay button from Execution detail, matching §6.3.
- Add tests for validation failures, default effective config persistence, byte-identical replay config, and replay against alternate corpus.

**Proposed commits:**

1. `feat(config): add ranker config validation`
2. `feat(frontend): build parameter form`
3. `feat(api): add execution replay endpoint`
4. `feat(frontend): wire replay prefill flow`
5. `test(config): cover validation and replay fidelity`

**Checkpoint:** replay creates a new execution with byte-identical `config_json`; edited form values create new valid executions.

### Milestone 7 — Evaluation endpoints and full-suite button

**Goal:** Expose `news_ranker.evaluate` helpers against persisted execution results.

**Spec refs:** §5.5 Evaluation endpoints, §6.3 Evaluation panel, §7 Evaluation Helper Integration, §4 `evaluation_artifact`.

**Implement/change:**

- Add `app/services/evaluators.py` that rebuilds result records from `execution_result.result_json` and calls `top_m_overlap`, `rank_correlation`, `component_score_table`, `cluster_inspection_rows`, and `anonymized_user_study_bundle`, matching §7.
- Add `app/routers/evaluations.py` with per-helper endpoints and `GET /api/executions/{id}/eval`, matching §5.5.
- Add `POST /api/executions/{id}/test-suite` requiring explicit `baseline_execution_id`, matching §5.5 and §7.
- Persist all helper outputs in `evaluation_artifact` with helper name, params, and payload JSON, matching §4.
- Add frontend Evaluation panel renderers for top-M overlap, rank correlation, component table, cluster inspection, and user-study bundle JSON download, matching §6.3.
- Add full-suite button with required baseline picker, matching §6.3.
- Add tests for each helper endpoint, artifact persistence, baseline requirement, unsupported execution-kind errors, and JSON payload shapes.

**Proposed commits:**

1. `feat(evaluation): add evaluator service adapters`
2. `feat(api): expose evaluation artifact endpoints`
3. `feat(api): add full-suite evaluation endpoint`
4. `feat(frontend): render evaluation panel and artifacts`
5. `test(evaluation): cover helpers and persistence`

**Checkpoint:** each helper round-trips through UI; full-suite runs only with chosen baseline and stores artifacts.

### Milestone 8 — Executions index and cross-execution compare

**Goal:** Make old executions discoverable and comparable across corpora.

**Spec refs:** §5.2 execution list/delete endpoints, §5.5 comparison endpoints, §6.5 Executions index.

**Implement/change:**

- Extend execution list endpoint with filters for corpus, kind, status, date range, profile, and pagination, matching §5.2 and §6.5.
- Include corpus name, profile summary, status, timestamps, and evaluation artifact presence in list response, matching §6.5.
- Implement Executions index page with filter controls and result table, matching §6.5.
- Add row actions: open detail, replay, delete, and compare with another execution, matching §6.5.
- Add compare modal that selects a second compatible execution and triggers top-M overlap + rank correlation, matching §6.5 and §5.5.
- Persist compare artifacts on the chosen target execution and show immediate UI feedback, matching §4 and §6.5.
- Add tests for filtering, pagination, delete behavior, compare modal API calls, and compatibility validation.

**Proposed commits:**

1. `feat(api): enrich execution list filters`
2. `feat(frontend): build executions index page`
3. `feat(frontend): add cross-execution compare modal`
4. `test(executions): cover filtering and compare flow`

**Checkpoint:** "Old executions" page is filterable; user can compare two executions without leaving the page.

### Milestone 9 — Polish, docs, and hardening

**Goal:** Make the demo reliable enough for repeat local use and handoff.

**Spec refs:** §10 Development Docker Setup, §11 Testing Strategy, §12 Resolved Decisions, all API/UI sections above.

**Implement/change:**

- Add healthcheck coverage for DB connectivity and dependency readiness where cheap, matching §10 dev workflow.
- Add deterministic replay test that runs same corpus/config twice and asserts identical `result_json`, matching §11 Testing Strategy.
- Add snapshot tests for serializer payloads, matching §11 Testing Strategy and §5.3.
- Add README sections for setup, env vars, common failures, reset DB, test commands, and development workflow, matching §10.
- Add frontend loading/empty/error states for major pages from §6.
- Review API errors for clear `422`/`404`/`409` responses, matching §5.
- Run formatting/lint/type/test checks for livedemo and parent project as applicable.

**Proposed commits:**

1. `test(livedemo): add deterministic and serializer snapshot tests`
2. `feat(api): improve health checks and error handling`
3. `feat(frontend): polish loading and empty states`
4. `docs(livedemo): document operations and troubleshooting`
5. `chore(livedemo): run final lint test and cleanup`

**Checkpoint:** fresh dev Compose startup yields a working app; tests pass; README can guide a new developer through setup.

---

*End of design document.*

from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine
from sqlalchemy import text

from livedemo.app.config import get_settings
from livedemo.app.db.session import engine as default_engine
from livedemo.app.db.session import init_db
from livedemo.app.deps import create_mistral_client, should_initialize_mistral
from livedemo.app.routers.articles import router as articles_router
from livedemo.app.routers.corpora import router as corpora_router
from livedemo.app.routers.evaluations import router as evaluations_router
from livedemo.app.routers.executions import router as executions_router
from livedemo.app.schemas import HealthResponse


def create_app(db_engine: Engine = default_engine) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db_engine = db_engine
        app.state.executor = ThreadPoolExecutor(max_workers=1)
        app.state.embedders = {}
        init_db(db_engine)
        app.state.mistral_client = (
            create_mistral_client(settings)
            if should_initialize_mistral(settings)
            else None
        )
        try:
            yield
        finally:
            app.state.executor.shutdown(wait=True)

    app = FastAPI(
        title="News Ranker Live Demo",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        checks = {
            "database": _database_ready(db_engine),
            "executor": hasattr(request.app.state, "executor"),
            "embedder_cache": isinstance(
                getattr(request.app.state, "embedders", None),
                dict,
            ),
            "decomposition_client": (
                getattr(request.app.state, "mistral_client", None) is not None
                or not should_initialize_mistral(settings)
            ),
        }
        return HealthResponse(ok=all(checks.values()), checks=checks)

    app.include_router(articles_router, prefix="/api")
    app.include_router(corpora_router, prefix="/api")
    app.include_router(executions_router, prefix="/api")
    app.include_router(evaluations_router, prefix="/api")

    return app


app = create_app()


def _database_ready(db_engine: Engine) -> bool:
    try:
        with db_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True

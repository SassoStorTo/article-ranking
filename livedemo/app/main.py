from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from livedemo.app.config import get_settings
from livedemo.app.db.session import engine as default_engine
from livedemo.app.db.session import init_db
from livedemo.app.routers.corpora import router as corpora_router
from livedemo.app.schemas import HealthResponse


def create_app(db_engine: Engine = default_engine) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db_engine = db_engine
        init_db(db_engine)
        yield

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
    def health() -> HealthResponse:
        return HealthResponse(ok=True)

    app.include_router(corpora_router, prefix="/api")

    return app


app = create_app()

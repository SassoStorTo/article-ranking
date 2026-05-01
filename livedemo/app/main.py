from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, load_settings
from app.db.session import init_db, make_engine, make_session_factory
from app.routers import articles, corpora


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = load_settings() if settings is None else settings

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(app_settings.db_url)
        init_db(engine)
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        app.state.settings = app_settings
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="News Ranker Live Demo", lifespan=lifespan)
    app.include_router(corpora.router)
    app.include_router(articles.router)

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    return app


app = create_app()

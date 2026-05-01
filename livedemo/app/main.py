from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy.orm import Session

from app.config import Settings, load_settings
from app.db.session import init_db, make_engine, make_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = load_settings() if settings is None else settings

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(app_settings.db_url)
        init_db(engine)
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="News Ranker Live Demo", lifespan=lifespan)

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    return app


def get_session(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session


app = create_app()

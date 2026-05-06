from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from livedemo.app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="News Ranker Live Demo", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    return app


app = create_app()

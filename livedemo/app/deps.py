from collections.abc import Generator
from collections.abc import Callable
from concurrent.futures import Executor
from sys import modules
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from livedemo.app.config import Settings
from livedemo.app.config import get_settings as load_settings
from livedemo.app.db.session import SessionLocal, iter_db
from news_ranker.config import RankerConfig
from news_ranker.decompose import DecompositionClient
from news_ranker.embed import FactEmbedder, SentenceTransformerEmbedder
from news_ranker.mistral import MistralDecompositionClient


def get_settings() -> Settings:
    return load_settings()


def get_db() -> Generator[Session]:
    yield from iter_db()


SettingsDep = Annotated[Settings, Depends(get_settings)]
EmbedderProvider = Callable[[str], FactEmbedder]


def get_session_factory() -> sessionmaker[Session]:
    return SessionLocal


def get_ranker_config() -> RankerConfig:
    return RankerConfig()


def get_embedder_provider(request: Request) -> EmbedderProvider:
    embedders = getattr(request.app.state, "embedders", None)
    if embedders is None:
        embedders = {}
        request.app.state.embedders = embedders

    def provider(model_name: str) -> FactEmbedder:
        if model_name not in embedders:
            embedders[model_name] = SentenceTransformerEmbedder(model_name)
        return embedders[model_name]

    return provider


def get_executor(request: Request) -> Executor:
    return request.app.state.executor


def is_test_mode() -> bool:
    return "pytest" in modules


def should_initialize_mistral(settings: Settings) -> bool:
    return bool(settings.mistral_api_key) or not is_test_mode()


def create_mistral_client(settings: Settings) -> MistralDecompositionClient:
    if not settings.mistral_api_key:
        raise RuntimeError("MISTRAL_API_KEY is required for article decomposition.")
    return MistralDecompositionClient(api_key=settings.mistral_api_key)


def get_mistral_client(
    request: Request,
    settings: SettingsDep,
) -> DecompositionClient:
    client = getattr(request.app.state, "mistral_client", None)
    if client is not None:
        return client
    return create_mistral_client(settings)

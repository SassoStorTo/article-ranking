import json
from collections.abc import Generator
from pathlib import Path

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from numpy.typing import NDArray
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from livedemo.app.db.session import create_session_factory
from livedemo.app.deps import (
    get_db,
    get_embedder_provider,
    get_mistral_client,
    get_session_factory,
)
from livedemo.app.main import create_app


class FakeDecompositionClient:
    def __init__(self) -> None:
        self.fail = False
        self.headline = "Neutral headline"
        self.context: list[str] | str | None = ["Background context"]
        self.calls: list[dict[str, str]] = []

    def complete(self, *, model: str, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        })
        if self.fail:
            return "{"
        return json.dumps({
            "headline_neutral": self.headline,
            "topic": "test topic",
            "entities": {
                "people": [{"name": "Alice", "role": "source"}],
                "organizations": [],
                "locations": [{"name": "Rome", "role": "dateline"}],
            },
            "events": [
                {
                    "id": "event-1",
                    "when": None,
                    "who": ["Alice"],
                    "what": "reported the event",
                    "where": "Rome",
                    "why": None,
                    "how": None,
                    "depends_on": [],
                }
            ],
            "claims": [
                {
                    "id": "claim-1",
                    "statement": "Alice described the event.",
                    "type": "fact",
                    "attributed_to": "Alice",
                }
            ],
            "context": self.context,
        })


class FakeEmbedder:
    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        vectors = []
        for index, text in enumerate(texts, start=1):
            length = max(len(text), 1)
            checksum = sum(ord(char) for char in text) % 997
            vectors.append([float(length), float(checksum + index)])
        return np.asarray(vectors, dtype=np.float32)


@pytest.fixture
def db_engine(tmp_path: Path) -> Generator[Engine]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'livedemo-test.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    yield engine
    engine.dispose()


@pytest.fixture
def db_session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(db_engine)


@pytest.fixture
def fake_decomposition_client() -> FakeDecompositionClient:
    return FakeDecompositionClient()


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def app(
    db_engine: Engine,
    db_session_factory: sessionmaker[Session],
    fake_decomposition_client: FakeDecompositionClient,
    fake_embedder: FakeEmbedder,
) -> FastAPI:
    app = create_app(db_engine=db_engine)

    def override_get_db() -> Generator[Session]:
        with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    app.dependency_overrides[get_mistral_client] = lambda: fake_decomposition_client
    app.dependency_overrides[get_embedder_provider] = lambda: (
        lambda _model_name: fake_embedder
    )
    return app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client

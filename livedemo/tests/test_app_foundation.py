from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect


def test_health_route(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_startup_stores_db_engine(
    app: FastAPI, client: TestClient, db_engine: Engine
) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert app.state.db_engine is db_engine


def test_startup_creates_v1_tables(client: TestClient, db_engine: Engine) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    inspector = inspect(db_engine)
    assert {
        "corpus",
        "article",
        "structured_article",
        "execution",
        "execution_result",
        "evaluation_artifact",
    } <= set(inspector.get_table_names())

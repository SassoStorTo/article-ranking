from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import Settings
from app.db.session import make_engine
from app.main import create_app


def test_app_startup_creates_database_tables(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'startup.sqlite'}"
    app = create_app(Settings(db_url=db_url))

    with TestClient(app) as client:
        response = client.get("/api/health")

    engine = make_engine(db_url)
    try:
        table_names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert response.status_code == 200
    assert {
        "article",
        "corpus",
        "evaluation_artifact",
        "execution",
        "execution_result",
        "structured_article",
    } <= table_names

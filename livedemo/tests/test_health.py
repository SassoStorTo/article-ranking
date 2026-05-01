from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health(tmp_path: Path) -> None:
    app = create_app(
        Settings(
            db_url=f"sqlite:///{tmp_path / 'health.sqlite'}",
            uploads_dir=str(tmp_path / "uploads"),
        ),
    )

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}

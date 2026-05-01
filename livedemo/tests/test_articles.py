from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.db.models import Article, Corpus, StructuredArticle
from app.main import create_app
from app.services.ingestion import content_sha256, upload_file_path


def make_client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            db_url=f"sqlite:///{tmp_path / 'articles.sqlite'}",
            uploads_dir=str(tmp_path / "uploads"),
        ),
    )
    return TestClient(app)


def create_corpus(client: TestClient) -> dict[str, object]:
    response = client.post("/api/corpora", json={"name": "corpus"})
    assert response.status_code == 201
    return response.json()


def test_multi_file_upload_creates_db_rows_and_volume_files(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        corpus = create_corpus(client)
        response = client.post(
            f"/api/corpora/{corpus['id']}/articles",
            files=[
                ("files", ("one.txt", b"First title\nBody", "text/plain")),
                ("files", ("two.txt", b"\nSecond title\nBody", "text/plain")),
            ],
        )

        with client.app.state.session_factory() as session:
            articles = session.scalars(
                select(Article).order_by(Article.filename),
            ).all()

    assert response.status_code == 201
    data = response.json()
    assert [article["filename"] for article in data["articles"]] == [
        "one.txt",
        "two.txt",
    ]
    assert len(articles) == 2
    assert articles[0].body == "First title\nBody"
    assert articles[0].title == "First title"
    assert articles[0].content_sha256 == content_sha256("First title\nBody")
    assert articles[1].body == "\nSecond title\nBody"
    assert articles[1].title == "Second title"
    assert articles[1].content_sha256 == content_sha256("\nSecond title\nBody")
    first_path = upload_file_path(tmp_path / "uploads", corpus["id"], articles[0].id)
    second_path = upload_file_path(tmp_path / "uploads", corpus["id"], articles[1].id)
    assert first_path.read_bytes() == b"First title\nBody"
    assert second_path.read_bytes() == b"\nSecond title\nBody"


def test_duplicate_filename_returns_409(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        corpus = create_corpus(client)
        first_response = client.post(
            f"/api/corpora/{corpus['id']}/articles",
            files=[("files", ("story.txt", b"Story", "text/plain"))],
        )
        duplicate_response = client.post(
            f"/api/corpora/{corpus['id']}/articles",
            files=[("files", ("story.txt", b"Other", "text/plain"))],
        )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "Article filename already exists in corpus",
    }


def test_non_txt_upload_rejected(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        corpus = create_corpus(client)
        response = client.post(
            f"/api/corpora/{corpus['id']}/articles",
            files=[("files", ("story.md", b"Story", "text/markdown"))],
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "uploaded files must use .txt extension"}


def test_invalid_utf8_upload_rejected(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        corpus = create_corpus(client)
        response = client.post(
            f"/api/corpora/{corpus['id']}/articles",
            files=[("files", ("story.txt", b"\xff", "text/plain"))],
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "uploaded files must be valid UTF-8"}


def test_missing_corpus_upload_returns_404(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/corpora/missing/articles",
            files=[("files", ("story.txt", b"Story", "text/plain"))],
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Corpus not found"}


def test_article_detail_includes_body_and_latest_structured_payload(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        with client.app.state.session_factory() as session:
            corpus = Corpus(name="corpus")
            article = Article(
                corpus=corpus,
                filename="story.txt",
                title="Story",
                body="Story body",
                content_sha256=content_sha256("Story body"),
            )
            session.add_all(
                [
                    corpus,
                    article,
                    StructuredArticle(
                        article=article,
                        llm_model="mistral-small",
                        prompt_version="v1",
                        schema_version="v1",
                        payload_json={"facts": ["old"]},
                        created_at=datetime.now(UTC) - timedelta(hours=1),
                    ),
                    StructuredArticle(
                        article=article,
                        llm_model="mistral-large",
                        prompt_version="v1",
                        schema_version="v1",
                        payload_json={"facts": ["new"]},
                        created_at=datetime.now(UTC),
                    ),
                ],
            )
            session.commit()
            article_id = article.id

        response = client.get(f"/api/articles/{article_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == article_id
    assert data["filename"] == "story.txt"
    assert data["body"] == "Story body"
    assert data["structured_payload"] == {"facts": ["new"]}


def test_missing_article_detail_returns_404(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/articles/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Article not found"}

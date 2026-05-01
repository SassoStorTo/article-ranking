from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import Settings
from app.db.models import Article, Corpus
from app.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            db_url=f"sqlite:///{tmp_path / 'corpora.sqlite'}",
            uploads_dir=str(tmp_path / "uploads"),
        ),
    )
    return TestClient(app)


def make_article(corpus: Corpus, filename: str = "article.txt") -> Article:
    return Article(
        corpus=corpus,
        filename=filename,
        title="Article title",
        body="Article body",
        content_sha256="a" * 64,
    )


def test_create_corpus_response(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/corpora",
            json={"name": "Election", "notes": "swing-state coverage"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["id"]
    assert data["name"] == "Election"
    assert data["notes"] == "swing-state coverage"
    assert data["created_at"]
    assert data["articles"] == []


def test_list_corpora_orders_newest_first_with_article_counts(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        older = client.post("/api/corpora", json={"name": "older"}).json()
        newer = client.post("/api/corpora", json={"name": "newer"}).json()

        with client.app.state.session_factory() as session:
            older_corpus = session.get(Corpus, older["id"])
            newer_corpus = session.get(Corpus, newer["id"])
            assert older_corpus is not None
            assert newer_corpus is not None
            session.add_all(
                [
                    make_article(older_corpus, "one.txt"),
                    make_article(older_corpus, "two.txt"),
                    make_article(newer_corpus, "three.txt"),
                ],
            )
            session.commit()

        response = client.get("/api/corpora")

    assert response.status_code == 200
    data = response.json()
    assert [corpus["name"] for corpus in data] == ["newer", "older"]
    assert [corpus["article_count"] for corpus in data] == [1, 2]


def test_corpus_detail_includes_article_summaries(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post("/api/corpora", json={"name": "corpus"}).json()

        with client.app.state.session_factory() as session:
            corpus = session.get(Corpus, created["id"])
            assert corpus is not None
            session.add(make_article(corpus, filename="story.txt"))
            session.commit()

        response = client.get(f"/api/corpora/{created['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created["id"]
    assert data["name"] == "corpus"
    assert data["articles"] == [
        {
            "id": data["articles"][0]["id"],
            "corpus_id": created["id"],
            "filename": "story.txt",
            "title": "Article title",
            "content_sha256": "a" * 64,
            "uploaded_at": data["articles"][0]["uploaded_at"],
        },
    ]
    assert data["articles"][0]["id"]
    assert data["articles"][0]["uploaded_at"]


def test_missing_corpus_returns_404(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        detail_response = client.get("/api/corpora/missing")
        delete_response = client.delete("/api/corpora/missing")

    assert detail_response.status_code == 404
    assert detail_response.json() == {"detail": "Corpus not found"}
    assert delete_response.status_code == 404
    assert delete_response.json() == {"detail": "Corpus not found"}


def test_delete_corpus_removes_corpus_and_articles_from_db(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post("/api/corpora", json={"name": "corpus"}).json()

        with client.app.state.session_factory() as session:
            corpus = session.get(Corpus, created["id"])
            assert corpus is not None
            session.add(make_article(corpus))
            session.commit()

        response = client.delete(f"/api/corpora/{created['id']}")

        with client.app.state.session_factory() as session:
            corpus_count = session.scalar(select(func.count()).select_from(Corpus))
            article_count = session.scalar(select(func.count()).select_from(Article))

    assert response.status_code == 204
    assert response.content == b""
    assert corpus_count == 0
    assert article_count == 0

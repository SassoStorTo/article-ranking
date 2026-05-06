from fastapi.testclient import TestClient


def create_corpus(client: TestClient, name: str = "event") -> str:
    response = client.post("/api/corpora", json={"name": name, "notes": "notes"})

    assert response.status_code == 201
    return str(response.json()["id"])


def upload_txt(
    client: TestClient,
    corpus_id: str,
    *,
    filename: str = "story.txt",
    body: str = "A clear title\n\nBody text",
) -> str:
    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={"files": (filename, body.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 201
    article_ids = response.json()["article_ids"]
    assert len(article_ids) == 1
    return str(article_ids[0])


def test_corpus_crud_flow(client: TestClient) -> None:
    corpus_id = create_corpus(client, "trump-shooting")

    list_response = client.get("/api/corpora")
    assert list_response.status_code == 200
    corpus = list_response.json()[0]
    assert corpus["id"] == corpus_id
    assert corpus["name"] == "trump-shooting"
    assert corpus["article_count"] == 0

    detail_response = client.get(f"/api/corpora/{corpus_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "trump-shooting"
    assert detail_response.json()["articles"] == []

    delete_response = client.delete(f"/api/corpora/{corpus_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/corpora/{corpus_id}").status_code == 404


def test_article_upload_persists_body_and_detail(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    article_id = upload_txt(client, corpus_id, body="First title\n\nFull body")

    corpus_response = client.get(f"/api/corpora/{corpus_id}")
    assert corpus_response.status_code == 200
    articles = corpus_response.json()["articles"]
    assert len(articles) == 1
    assert articles[0]["id"] == article_id
    assert articles[0]["filename"] == "story.txt"
    assert articles[0]["title"] == "First title"
    assert articles[0]["body_length"] == len("First title\n\nFull body")

    article_response = client.get(f"/api/articles/{article_id}")
    assert article_response.status_code == 200
    assert article_response.json()["body"] == "First title\n\nFull body"


def test_title_heuristic_falls_back_to_filename_for_long_first_line(
    client: TestClient,
) -> None:
    corpus_id = create_corpus(client)
    long_line = "x" * 200
    article_id = upload_txt(
        client,
        corpus_id,
        filename="fallback-title.txt",
        body=f"{long_line}\nBody",
    )

    article_response = client.get(f"/api/articles/{article_id}")
    assert article_response.status_code == 200
    assert article_response.json()["title"] == "fallback-title"


def test_upload_rejects_non_txt_files(client: TestClient) -> None:
    corpus_id = create_corpus(client)

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={"files": ("story.md", b"# headline", "text/markdown")},
    )

    assert response.status_code == 422
    assert "not a .txt" in response.json()["detail"]


def test_upload_rejects_duplicate_filename(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    upload_txt(client, corpus_id, filename="dupe.txt")

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={"files": ("dupe.txt", b"New body", "text/plain")},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_upload_rejects_duplicate_filename_within_same_request(
    client: TestClient,
) -> None:
    corpus_id = create_corpus(client)

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files=[
            ("files", ("same.txt", b"First", "text/plain")),
            ("files", ("same.txt", b"Second", "text/plain")),
        ],
    )

    assert response.status_code == 409
    detail_response = client.get(f"/api/corpora/{corpus_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["articles"] == []


def test_corpus_delete_cascades_articles(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    article_id = upload_txt(client, corpus_id)

    delete_response = client.delete(f"/api/corpora/{corpus_id}")

    assert delete_response.status_code == 204
    assert client.get(f"/api/articles/{article_id}").status_code == 404

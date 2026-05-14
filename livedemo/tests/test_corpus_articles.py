import json
from typing import Any

from fastapi.testclient import TestClient


def create_corpus(client: TestClient, name: str = "event") -> str:
    response = client.post("/api/corpora", json={"name": name, "notes": "notes"})

    assert response.status_code == 201
    return str(response.json()["id"])


def valid_structured_payload(article_id: str | None = "external-id") -> dict[str, Any]:
    return {
        "article_id": article_id,
        "headline_neutral": "Uploaded neutral headline",
        "topic": "upload topic",
        "entities": {
            "people": [{"name": "Bob", "role": "witness"}],
            "organizations": [],
            "locations": [{"name": "Paris", "role": "dateline"}],
        },
        "events": [
            {
                "id": "event-1",
                "when": None,
                "who": ["Bob"],
                "what": "described an upload",
                "where": "Paris",
                "why": None,
                "how": None,
                "depends_on": [],
            }
        ],
        "claims": [
            {
                "id": "claim-1",
                "statement": "Bob described the upload.",
                "type": "fact",
                "attributed_to": "Bob",
            }
        ],
        "context": ["Precomputed context"],
    }


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


def upload_json(
    client: TestClient,
    corpus_id: str,
    *,
    filename: str = "structured.json",
    payload: dict[str, Any] | None = None,
) -> str:
    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={
            "files": (
                filename,
                json.dumps(payload or valid_structured_payload()).encode("utf-8"),
                "application/json",
            )
        },
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


def test_json_upload_persists_decomposed_detail(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    article_id = upload_json(client, corpus_id, filename="source.json")

    article_response = client.get(f"/api/articles/{article_id}")

    assert article_response.status_code == 200
    detail = article_response.json()
    structured = detail["structured_article"]
    assert detail["filename"] == "source.json"
    assert detail["title"] == "Uploaded neutral headline (source.json)"
    assert detail["decomposition_status"] == "decomposed"
    assert structured["article_id"] == article_id
    assert structured["llm_model"] == "mistral-small-latest"
    assert structured["prompt_version"] == "v1"
    assert structured["schema_version"] == "v1"
    assert structured["payload_json"]["article_id"] == article_id
    assert structured["payload_json"]["headline_neutral"] == (
        "Uploaded neutral headline"
    )


def test_upload_rejects_non_txt_or_json_files(client: TestClient) -> None:
    corpus_id = create_corpus(client)

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={"files": ("story.md", b"# headline", "text/markdown")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "story.md" in detail
    assert "unsupported file type .md" in detail
    assert "Upload a .txt or .json file" in detail


def test_upload_rejects_duplicate_filename(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    upload_txt(client, corpus_id, filename="dupe.txt")

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={"files": ("dupe.txt", b"New body", "text/plain")},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_json_upload_rejects_duplicate_filename(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    upload_json(client, corpus_id, filename="dupe.json")

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={"files": ("dupe.json", b"{}", "application/json")},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_json_upload_rejects_malformed_json(client: TestClient) -> None:
    corpus_id = create_corpus(client)

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={"files": ("broken.json", b"{", "application/json")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "broken.json" in detail
    assert "malformed JSON" in detail
    assert "line 1" in detail
    assert "column 2" in detail


def test_json_upload_rejects_non_utf8_content(client: TestClient) -> None:
    corpus_id = create_corpus(client)

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={"files": ("latin1.json", b"{\xff}", "application/json")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "latin1.json" in detail
    assert "UTF-8" in detail
    assert "byte 1" in detail


def test_json_upload_rejects_invalid_claim_type(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    payload = valid_structured_payload()
    payload["claims"][0]["type"] = "rumor"

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={
            "files": (
                "bad-claim.json",
                json.dumps(payload).encode("utf-8"),
                "application/json",
            )
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "bad-claim.json" in detail
    assert "claims.0.type" in detail
    assert "literal_error" in detail


def test_json_upload_rejects_schema_missing_entities(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    payload = valid_structured_payload()
    del payload["entities"]

    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files={
            "files": (
                "missing-entities.json",
                json.dumps(payload).encode("utf-8"),
                "application/json",
            )
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "missing-entities.json" in detail
    assert "StructuredArticle schema" in detail
    assert "entities" in detail
    assert "missing" in detail


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


def test_article_delete_removes_article_from_corpus(client: TestClient) -> None:
    corpus_id = create_corpus(client)
    article_id = upload_txt(client, corpus_id)

    delete_response = client.delete(f"/api/articles/{article_id}")

    assert delete_response.status_code == 204
    assert client.get(f"/api/articles/{article_id}").status_code == 404
    corpus_response = client.get(f"/api/corpora/{corpus_id}")
    assert corpus_response.status_code == 200
    assert corpus_response.json()["articles"] == []


def test_article_delete_returns_not_found_for_missing_article(
    client: TestClient,
) -> None:
    response = client.delete("/api/articles/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404

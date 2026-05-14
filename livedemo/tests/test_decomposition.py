import json

from fastapi.testclient import TestClient
from tests.conftest import FakeDecompositionClient
from tests.test_corpus_articles import (
    create_corpus,
    upload_json,
    upload_txt,
    valid_structured_payload,
)


def test_upload_triggers_decomposition_and_detail_payload_shape(
    client: TestClient,
    fake_decomposition_client: FakeDecompositionClient,
) -> None:
    corpus_id = create_corpus(client)
    article_id = upload_txt(client, corpus_id)

    assert len(fake_decomposition_client.calls) == 1
    detail_response = client.get(f"/api/articles/{article_id}")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    structured = detail["structured_article"]
    assert detail["decomposition_status"] == "decomposed"
    assert structured["article_id"] == article_id
    assert structured["llm_model"] == "mistral-small-latest"
    assert structured["prompt_version"] == "v1"
    assert structured["schema_version"] == "v1"
    assert structured["payload_json"]["article_id"] == article_id
    assert structured["payload_json"]["entities"]["people"][0]["name"] == "Alice"
    assert structured["payload_json"]["events"][0]["what"] == "reported the event"
    assert structured["payload_json"]["claims"][0]["type"] == "fact"


def test_json_upload_skips_background_decomposition(
    client: TestClient,
    fake_decomposition_client: FakeDecompositionClient,
) -> None:
    corpus_id = create_corpus(client)
    article_id = upload_json(client, corpus_id)

    assert fake_decomposition_client.calls == []
    detail = client.get(f"/api/articles/{article_id}").json()
    assert detail["decomposition_status"] == "decomposed"
    assert detail["structured_article"]["payload_json"]["article_id"] == article_id


def test_mixed_txt_json_upload_decomposes_only_txt_article(
    client: TestClient,
    fake_decomposition_client: FakeDecompositionClient,
) -> None:
    corpus_id = create_corpus(client)
    response = client.post(
        f"/api/corpora/{corpus_id}/articles",
        files=[
            (
                "files",
                (
                    "structured.json",
                    json.dumps(valid_structured_payload()).encode("utf-8"),
                    "application/json",
                ),
            ),
            ("files", ("story.txt", b"Story title\n\nBody text", "text/plain")),
        ],
    )

    assert response.status_code == 201
    json_id, txt_id = [str(article_id) for article_id in response.json()["article_ids"]]
    assert len(fake_decomposition_client.calls) == 1
    json_detail = client.get(f"/api/articles/{json_id}").json()
    txt_detail = client.get(f"/api/articles/{txt_id}").json()
    assert json_detail["decomposition_status"] == "decomposed"
    assert txt_detail["decomposition_status"] == "decomposed"
    assert json_detail["structured_article"]["payload_json"]["article_id"] == json_id
    assert txt_detail["structured_article"]["payload_json"]["article_id"] == txt_id


def test_manual_decompose_upserts_matching_metadata_row(
    client: TestClient,
    fake_decomposition_client: FakeDecompositionClient,
) -> None:
    corpus_id = create_corpus(client)
    article_id = upload_txt(client, corpus_id)
    initial_detail = client.get(f"/api/articles/{article_id}").json()
    initial_structured_id = initial_detail["structured_article"]["id"]

    fake_decomposition_client.headline = "Updated neutral headline"
    response = client.post(f"/api/articles/{article_id}/decompose")

    assert response.status_code == 200
    structured = response.json()
    assert structured["id"] == initial_structured_id
    assert structured["payload_json"]["headline_neutral"] == (
        "Updated neutral headline"
    )

    detail = client.get(f"/api/articles/{article_id}").json()
    assert detail["structured_article"]["id"] == initial_structured_id
    assert detail["structured_article"]["payload_json"]["headline_neutral"] == (
        "Updated neutral headline"
    )


def test_decompose_normalizes_string_context_from_provider(
    client: TestClient,
    fake_decomposition_client: FakeDecompositionClient,
) -> None:
    corpus_id = create_corpus(client)
    fake_decomposition_client.context = "Provider returned a single paragraph."
    article_id = upload_txt(client, corpus_id)

    detail = client.get(f"/api/articles/{article_id}").json()

    assert detail["decomposition_status"] == "decomposed"
    assert detail["structured_article"]["payload_json"]["context"] == [
        "Provider returned a single paragraph."
    ]


def test_manual_decompose_reports_failure_without_replacing_payload(
    client: TestClient,
    fake_decomposition_client: FakeDecompositionClient,
) -> None:
    corpus_id = create_corpus(client)
    article_id = upload_txt(client, corpus_id)
    existing = client.get(f"/api/articles/{article_id}").json()["structured_article"]

    fake_decomposition_client.fail = True
    response = client.post(f"/api/articles/{article_id}/decompose")

    assert response.status_code == 502
    assert "decomposition failed" in response.json()["detail"]

    detail = client.get(f"/api/articles/{article_id}").json()
    assert detail["structured_article"] == existing


def test_manual_decompose_missing_article_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/articles/00000000-0000-0000-0000-000000000000/decompose"
    )

    assert response.status_code == 404

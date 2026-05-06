import time
from typing import Any

from fastapi.testclient import TestClient
from tests.test_corpus_articles import create_corpus, upload_txt


def wait_for_execution(client: TestClient, execution_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 5
    detail: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        response = client.get(f"/api/executions/{execution_id}")
        assert response.status_code == 200
        detail = response.json()
        if detail["status"] not in {"pending", "running"}:
            return detail
        time.sleep(0.05)
    raise AssertionError(f"execution did not finish: {detail}")


def create_corpus_with_articles(client: TestClient) -> str:
    corpus_id = create_corpus(client)
    upload_txt(
        client,
        corpus_id,
        filename="first.txt",
        body="First title\n\nBody text",
    )
    upload_txt(
        client,
        corpus_id,
        filename="second.txt",
        body="Second title\n\nMore body text",
    )
    return corpus_id


def start_execution(
    client: TestClient,
    path: str,
    payload: dict[str, Any],
) -> str:
    response = client.post(path, json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    return str(body["execution_id"])


def test_rank_execution_lifecycle_and_detail_payload(client: TestClient) -> None:
    corpus_id = create_corpus_with_articles(client)
    execution_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )

    detail = wait_for_execution(client, execution_id)

    assert detail["kind"] == "rank"
    assert detail["status"] == "succeeded"
    assert detail["profiles"] == ["representative"]
    assert detail["config_json"]["similarity_threshold"] == 0.85
    assert detail["config_json"]["selection_mode"] == "top_score"
    assert detail["results"][0]["profile"] == "representative"
    result = detail["results"][0]["result_json"]
    assert result["__type__"] == "rank_result"
    assert result["profile"] == "representative"
    assert [entry["rank"] for entry in result["entries"]] == [1, 2]


def test_select_execution_persists_selected_rows(client: TestClient) -> None:
    corpus_id = create_corpus_with_articles(client)
    execution_id = start_execution(
        client,
        "/api/executions/select",
        {"corpus_id": corpus_id, "profile": "representative", "m": 1},
    )

    detail = wait_for_execution(client, execution_id)

    assert detail["kind"] == "select"
    assert detail["m"] == 1
    assert detail["status"] == "succeeded"
    result = detail["results"][0]["result_json"]
    assert result["__type__"] == "selection_result"
    assert result["m"] == 1
    assert len(result["selected"]) == 1
    assert result["ranking"]["__type__"] == "rank_result"


def test_compare_profiles_execution_persists_profile_comparison(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    execution_id = start_execution(
        client,
        "/api/executions/compare",
        {
            "corpus_id": corpus_id,
            "profiles": ["representative", "comprehensive"],
        },
    )

    detail = wait_for_execution(client, execution_id)

    assert detail["kind"] == "compare_profiles"
    assert detail["status"] == "succeeded"
    result = detail["results"][0]["result_json"]
    assert result["__type__"] == "profile_comparison"
    assert set(result["rankings"]) == {"representative", "comprehensive"}


def test_execution_failure_status_is_persisted(client: TestClient) -> None:
    corpus_id = create_corpus_with_articles(client)
    execution_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "missing-profile"},
    )

    detail = wait_for_execution(client, execution_id)

    assert detail["status"] == "failed"
    assert "unknown ranking profile" in detail["error"]
    assert detail["results"] == []


def test_execution_list_filters_and_delete(client: TestClient) -> None:
    corpus_id = create_corpus_with_articles(client)
    rank_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    select_id = start_execution(
        client,
        "/api/executions/select",
        {"corpus_id": corpus_id, "profile": "representative", "m": 1},
    )
    wait_for_execution(client, rank_id)
    wait_for_execution(client, select_id)

    response = client.get(
        "/api/executions",
        params={"corpus_id": corpus_id, "kind": "select", "status": "succeeded"},
    )

    assert response.status_code == 200
    executions = response.json()
    assert [execution["id"] for execution in executions] == [select_id]

    delete_response = client.delete(f"/api/executions/{select_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/executions/{select_id}").status_code == 404

import json
import time
from typing import Any

import pytest
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
    assert set(detail["config_json"]["profiles"]) == {
        "representative",
        "comprehensive",
        "concise",
    }
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


def test_compare_profiles_accepts_parameter_form_config(client: TestClient) -> None:
    corpus_id = create_corpus_with_articles(client)
    execution_id = start_execution(
        client,
        "/api/executions/compare",
        {
            "corpus_id": corpus_id,
            "profiles": ["representative", "comprehensive", "concise"],
            "config": {
                "similarity_threshold": 0.85,
                "linkage": "average",
                "coverage_weighting": "consensus",
                "profiles": {
                    "representative": {
                        "centrality": 0.4,
                        "coverage": 0.5,
                        "density": 0.1,
                        "entity_coverage": 0.0,
                    },
                    "comprehensive": {
                        "centrality": 0.2,
                        "coverage": 0.7,
                        "density": 0.1,
                        "entity_coverage": 0.0,
                    },
                    "concise": {
                        "centrality": 0.2,
                        "coverage": 0.4,
                        "density": 0.4,
                        "entity_coverage": 0.0,
                    },
                },
                "top_m": 3,
                "selection_mode": "top_score",
                "selection_lambda": 0.8,
                "embedding_model_name": "all-MiniLM-L6-v2",
                "llm_model_name": "mistral-small-latest",
                "prompt_version": "v1",
                "schema_version": "v1",
            },
        },
    )

    detail = wait_for_execution(client, execution_id)

    assert detail["status"] == "succeeded"
    assert detail["profiles"] == ["representative", "comprehensive", "concise"]
    assert detail["config_json"]["profiles"]["concise"]["density"] == 0.4


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
    compare_id = start_execution(
        client,
        "/api/executions/compare",
        {
            "corpus_id": corpus_id,
            "profiles": ["representative", "comprehensive"],
        },
    )
    rank = wait_for_execution(client, rank_id)
    wait_for_execution(client, select_id)
    wait_for_execution(client, compare_id)

    response = client.get(
        "/api/executions",
        params={"corpus_id": corpus_id, "kind": "select", "status": "succeeded"},
    )

    assert response.status_code == 200
    executions = response.json()
    assert [execution["id"] for execution in executions] == [select_id]
    assert executions[0]["corpus_name"]
    assert executions[0]["profile_summary"] == "representative"
    assert executions[0]["has_evaluation_artifacts"] is False

    profile_response = client.get(
        "/api/executions",
        params={"profile": "comprehensive"},
    )
    assert profile_response.status_code == 200
    assert [execution["id"] for execution in profile_response.json()] == [compare_id]

    date_response = client.get(
        "/api/executions",
        params={"created_from": rank["created_at"], "limit": 10},
    )
    assert date_response.status_code == 200
    assert {execution["id"] for execution in date_response.json()} >= {
        rank_id,
        select_id,
        compare_id,
    }

    first_page = client.get("/api/executions", params={"limit": 1, "offset": 0})
    second_page = client.get("/api/executions", params={"limit": 1, "offset": 1})
    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert len(first_page.json()) == 1
    assert len(second_page.json()) == 1
    assert first_page.json()[0]["id"] != second_page.json()[0]["id"]

    delete_response = client.delete(f"/api/executions/{select_id}")
    assert delete_response.status_code == 204
    assert client.get(f"/api/executions/{select_id}").status_code == 404


def test_cross_execution_compare_artifacts_persist_on_target(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    source_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    target_id = start_execution(
        client,
        "/api/executions/select",
        {"corpus_id": corpus_id, "profile": "representative", "m": 1},
    )
    wait_for_execution(client, source_id)
    wait_for_execution(client, target_id)

    overlap_response = client.post(
        f"/api/executions/{target_id}/eval/top-m-overlap",
        json={"other_execution_id": source_id, "m": 1},
    )
    correlation_response = client.post(
        f"/api/executions/{target_id}/eval/rank-correlation",
        json={"other_execution_id": source_id, "method": "kendall"},
    )

    assert overlap_response.status_code == 200
    assert correlation_response.status_code == 200
    artifacts_response = client.get(f"/api/executions/{target_id}/eval")
    assert artifacts_response.status_code == 200
    assert [artifact["helper"] for artifact in artifacts_response.json()] == [
        "top_m_overlap",
        "rank_correlation",
    ]
    list_response = client.get(
        "/api/executions",
        params={"corpus_id": corpus_id, "profile": "representative"},
    )
    assert list_response.status_code == 200
    target_row = next(
        execution for execution in list_response.json() if execution["id"] == target_id
    )
    assert target_row["has_evaluation_artifacts"] is True


def test_rank_correlation_rejects_executions_without_common_articles(
    client: TestClient,
) -> None:
    source_corpus_id = create_corpus_with_articles(client)
    target_corpus_id = create_corpus_with_articles(client)
    source_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": source_corpus_id, "profile": "representative"},
    )
    target_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": target_corpus_id, "profile": "representative"},
    )
    wait_for_execution(client, source_id)
    wait_for_execution(client, target_id)

    response = client.post(
        f"/api/executions/{target_id}/eval/rank-correlation",
        json={"other_execution_id": source_id, "method": "kendall"},
    )

    assert response.status_code == 422
    assert "at least two common article IDs" in response.json()["detail"]


def test_cross_execution_compare_rejects_incompatible_shapes(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    rank_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    compare_id = start_execution(
        client,
        "/api/executions/compare",
        {
            "corpus_id": corpus_id,
            "profiles": ["representative", "comprehensive"],
        },
    )
    wait_for_execution(client, rank_id)
    wait_for_execution(client, compare_id)

    response = client.post(
        f"/api/executions/{compare_id}/eval/top-m-overlap",
        json={"other_execution_id": rank_id, "m": 1},
    )

    assert response.status_code == 422
    assert "rank or select execution" in response.json()["detail"]


@pytest.mark.parametrize(
    "config",
    [
        {"linkage": "complete"},
        {"coverage_weighting": "frequency"},
        {"selection_mode": "rarity"},
        {"top_m": 0},
        {
            "profiles": {
                "representative": {
                    "centrality": 0.4,
                    "coverage": 0.5,
                    "density": 0.1,
                }
            }
        },
        {
            "profiles": {
                "representative": {
                    "centrality": -0.1,
                    "coverage": 0.9,
                    "density": 0.2,
                    "entity_coverage": 0.0,
                }
            }
        },
        {
            "profiles": {
                "representative": {
                    "centrality": 0.5,
                    "coverage": 0.5,
                    "density": 0.5,
                    "entity_coverage": 0.0,
                }
            }
        },
    ],
)
def test_ranker_config_validation_failures(
    client: TestClient,
    config: dict[str, Any],
) -> None:
    corpus_id = create_corpus_with_articles(client)

    response = client.post(
        "/api/executions/rank",
        json={
            "corpus_id": corpus_id,
            "profile": "representative",
            "config": config,
        },
    )

    assert response.status_code == 422


def test_replay_persists_byte_identical_config(client: TestClient) -> None:
    corpus_id = create_corpus_with_articles(client)
    execution_id = start_execution(
        client,
        "/api/executions/select",
        {
            "corpus_id": corpus_id,
            "profile": "representative",
            "m": 1,
            "config": {
                "similarity_threshold": 0.75,
                "selection_mode": "mmr",
                "selection_lambda": 0.65,
                "top_m": 1,
            },
        },
    )
    source = wait_for_execution(client, execution_id)

    response = client.post(f"/api/executions/{execution_id}/replay", json={})

    assert response.status_code == 202
    replay_id = response.json()["execution_id"]
    replay = wait_for_execution(client, replay_id)
    assert replay["status"] == "succeeded"
    assert replay["kind"] == source["kind"]
    assert replay["m"] == source["m"]
    assert json.dumps(replay["config_json"], sort_keys=True) == json.dumps(
        source["config_json"],
        sort_keys=True,
    )


def test_replay_can_target_alternate_corpus(client: TestClient) -> None:
    source_corpus_id = create_corpus_with_articles(client)
    alternate_corpus_id = create_corpus_with_articles(client)
    execution_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": source_corpus_id, "profile": "representative"},
    )
    source = wait_for_execution(client, execution_id)

    response = client.post(
        f"/api/executions/{execution_id}/replay",
        json={"corpus_id": alternate_corpus_id},
    )

    assert response.status_code == 202
    replay = wait_for_execution(client, response.json()["execution_id"])
    assert replay["status"] == "succeeded"
    assert replay["corpus_id"] == alternate_corpus_id
    assert replay["profiles"] == ["representative"]
    assert replay["config_json"] == source["config_json"]

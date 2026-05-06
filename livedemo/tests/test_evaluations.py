from typing import Any

from fastapi.testclient import TestClient
from tests.test_executions import (
    create_corpus_with_articles,
    start_execution,
    wait_for_execution,
)


def completed_execution(
    client: TestClient,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    execution_id = start_execution(client, path, payload)
    detail = wait_for_execution(client, execution_id)
    assert detail["status"] == "succeeded"
    return detail


def article_materials(client: TestClient, corpus_id: str) -> dict[str, dict[str, str]]:
    response = client.get(f"/api/corpora/{corpus_id}")
    assert response.status_code == 200
    return {
        article["id"]: {
            "title": article["title"],
            "snippet": article["filename"],
        }
        for article in response.json()["articles"]
    }


def test_top_m_overlap_and_rank_correlation_artifacts_persist(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    baseline = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    candidate = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )

    overlap_response = client.post(
        f"/api/executions/{candidate['id']}/eval/top-m-overlap",
        json={"other_execution_id": baseline["id"], "m": 1},
    )
    correlation_response = client.post(
        f"/api/executions/{candidate['id']}/eval/rank-correlation",
        json={"other_execution_id": baseline["id"], "method": "spearman"},
    )

    assert overlap_response.status_code == 200
    overlap = overlap_response.json()
    assert overlap["helper"] == "top_m_overlap"
    assert overlap["params_json"] == {"other_execution_id": baseline["id"], "m": 1}
    assert overlap["payload_json"]["overlap_count"] == 1
    assert overlap["payload_json"]["jaccard"] == 1.0

    assert correlation_response.status_code == 200
    correlation = correlation_response.json()
    assert correlation["helper"] == "rank_correlation"
    assert correlation["payload_json"]["method"] == "spearman"
    assert correlation["payload_json"]["common_count"] == 2
    assert correlation["payload_json"]["coefficient"] == 1.0

    list_response = client.get(f"/api/executions/{candidate['id']}/eval")
    assert list_response.status_code == 200
    assert [artifact["helper"] for artifact in list_response.json()] == [
        "top_m_overlap",
        "rank_correlation",
    ]

    detail_response = client.get(f"/api/executions/{candidate['id']}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["evaluation_artifacts"]) == 2


def test_component_table_and_cluster_inspection_payload_shapes(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    rank = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    comparison = completed_execution(
        client,
        "/api/executions/compare",
        {
            "corpus_id": corpus_id,
            "profiles": ["representative", "comprehensive"],
        },
    )

    component_response = client.post(
        f"/api/executions/{comparison['id']}/eval/component-table",
        json={},
    )
    cluster_response = client.post(
        f"/api/executions/{rank['id']}/eval/cluster-inspection",
        json={"rare_threshold": 1},
    )

    assert component_response.status_code == 200
    component_rows = component_response.json()["payload_json"]["rows"]
    assert {row["profile"] for row in component_rows} == {
        "representative",
        "comprehensive",
    }
    assert {"article_id", "rank", "score", "centrality", "coverage"}.issubset(
        component_rows[0]
    )

    assert cluster_response.status_code == 200
    cluster_rows = cluster_response.json()["payload_json"]["rows"]
    assert cluster_rows
    assert {
        "cluster_index",
        "canonical_fact_text",
        "support_article_ids",
        "support_count",
        "member_fact_ids",
        "member_texts",
        "is_rare",
    }.issubset(cluster_rows[0])


def test_user_study_bundle_requires_select_and_returns_download_payload(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    selection = completed_execution(
        client,
        "/api/executions/select",
        {"corpus_id": corpus_id, "profile": "representative", "m": 1},
    )

    response = client.post(
        f"/api/executions/{selection['id']}/eval/user-study-bundle",
        json={
            "materials": article_materials(client, corpus_id),
            "include_scores": True,
        },
    )

    assert response.status_code == 200
    artifact = response.json()
    assert artifact["helper"] == "anonymized_user_study_bundle"
    assert artifact["payload_json"]["selected_article_labels"] == ["article_1"]
    assert set(artifact["payload_json"]["article_materials"]) == {"article_1"}
    assert artifact["payload_json"]["scores"][0]["label"] == "article_1"


def test_full_suite_requires_baseline_and_stores_created_artifacts(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    baseline = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    candidate = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )

    missing_baseline = client.post(
        f"/api/executions/{candidate['id']}/test-suite",
        json={"m": 1},
    )
    assert missing_baseline.status_code == 422

    response = client.post(
        f"/api/executions/{candidate['id']}/test-suite",
        json={
            "baseline_execution_id": baseline["id"],
            "m": 1,
            "method": "kendall",
            "rare_threshold": 1,
        },
    )

    assert response.status_code == 200
    helpers = [artifact["helper"] for artifact in response.json()]
    assert helpers == [
        "top_m_overlap",
        "rank_correlation",
        "component_score_table",
        "cluster_inspection_rows",
    ]
    persisted = client.get(f"/api/executions/{candidate['id']}/eval")
    assert persisted.status_code == 200
    assert [artifact["helper"] for artifact in persisted.json()] == helpers


def test_unsupported_execution_shapes_return_422(client: TestClient) -> None:
    corpus_id = create_corpus_with_articles(client)
    rank = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    comparison = completed_execution(
        client,
        "/api/executions/compare",
        {
            "corpus_id": corpus_id,
            "profiles": ["representative", "comprehensive"],
        },
    )

    user_study_response = client.post(
        f"/api/executions/{rank['id']}/eval/user-study-bundle",
        json={"materials": {}, "include_scores": False},
    )
    cluster_response = client.post(
        f"/api/executions/{comparison['id']}/eval/cluster-inspection",
        json={"rare_threshold": 1},
    )

    assert user_study_response.status_code == 422
    assert "select execution" in user_study_response.json()["detail"]
    assert cluster_response.status_code == 422
    assert "rank or select execution" in cluster_response.json()["detail"]

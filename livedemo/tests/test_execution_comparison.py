from typing import Any

from fastapi.testclient import TestClient
from tests.test_evaluations import completed_execution
from tests.test_executions import (
    create_corpus_with_articles,
    start_execution,
    wait_for_execution,
)


def get_comparison(
    client: TestClient,
    left_execution_id: str,
    right_execution_id: str,
) -> dict[str, Any]:
    response = client.get(
        "/api/executions/comparison",
        params={
            "left_execution_id": left_execution_id,
            "right_execution_id": right_execution_id,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_rank_vs_select_comparison_returns_metadata_sections_and_metrics(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    rank = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    selection = completed_execution(
        client,
        "/api/executions/select",
        {"corpus_id": corpus_id, "profile": "representative", "m": 1},
    )

    comparison = get_comparison(client, rank["id"], selection["id"])

    assert comparison["left"]["id"] == rank["id"]
    assert comparison["left"]["kind"] == "rank"
    assert comparison["left"]["config_json"]["similarity_threshold"] == 0.85
    assert comparison["right"]["id"] == selection["id"]
    assert comparison["right"]["kind"] == "select"
    assert comparison["right"]["config_json"]["m"] == 1

    assert comparison["warnings"] == []
    assert len(comparison["section_pairs"]) == 1
    pair = comparison["section_pairs"][0]
    assert pair["left"]["result_type"] == "rank_result"
    assert pair["right"]["result_type"] == "selection_result"
    assert pair["right"]["selected_article_ids"]
    assert pair["left"]["cluster_count"] == len(pair["left"]["cluster_inspection_rows"])
    assert pair["left"]["cluster_inspection_rows"]
    assert {
        "cluster_index",
        "canonical_fact_text",
        "support_article_ids",
        "support_count",
        "member_fact_ids",
        "member_texts",
        "is_rare",
    }.issubset(pair["left"]["cluster_inspection_rows"][0])
    assert pair["metrics"]["top_m_overlap"]["overlap_count"] == 2
    assert pair["metrics"]["rank_correlation"]["coefficient"] == 1.0
    assert pair["metrics"]["left_cluster_count"] >= 1
    assert pair["metrics"]["right_cluster_count"] >= 1
    assert pair["metrics"]["shared_cluster_count"] >= 1

    artifacts_response = client.get(f"/api/executions/{selection['id']}/eval")
    assert artifacts_response.status_code == 200
    assert artifacts_response.json() == []


def test_compare_profiles_vs_compare_profiles_expands_and_warns_unmatched_profiles(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    left = completed_execution(
        client,
        "/api/executions/compare",
        {
            "corpus_id": corpus_id,
            "profiles": ["representative", "comprehensive"],
        },
    )
    right = completed_execution(
        client,
        "/api/executions/compare",
        {"corpus_id": corpus_id, "profiles": ["representative", "concise"]},
    )

    comparison = get_comparison(client, left["id"], right["id"])

    assert comparison["left"]["kind"] == "compare_profiles"
    assert comparison["right"]["kind"] == "compare_profiles"
    assert {pair["key"] for pair in comparison["section_pairs"]} == {
        "comprehensive",
        "concise",
        "representative__representative",
    }
    representative = next(
        pair
        for pair in comparison["section_pairs"]
        if pair["key"] == "representative__representative"
    )
    assert representative["left"]["profile"] == "representative"
    assert representative["right"]["profile"] == "representative"
    assert representative["metrics"]["top_m_overlap"]["overlap_count"] == 2
    unmatched = [pair for pair in comparison["section_pairs"] if pair["warnings"]]
    assert {pair["key"] for pair in unmatched} == {"comprehensive", "concise"}
    assert {pair["warnings"][0]["code"] for pair in unmatched} == {"unmatched_section"}


def test_rank_vs_compare_profiles_pairs_single_section_against_each_profile(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    rank = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    profiles = completed_execution(
        client,
        "/api/executions/compare",
        {
            "corpus_id": corpus_id,
            "profiles": ["representative", "comprehensive"],
        },
    )

    comparison = get_comparison(client, rank["id"], profiles["id"])

    assert [pair["right"]["profile"] for pair in comparison["section_pairs"]] == [
        "comprehensive",
        "representative",
    ]
    assert all(
        pair["left"]["profile"] == "representative"
        for pair in comparison["section_pairs"]
    )
    assert all(pair["metrics"]["top_m_overlap"] for pair in comparison["section_pairs"])


def test_missing_and_unfinished_executions_return_clear_errors(
    client: TestClient,
) -> None:
    corpus_id = create_corpus_with_articles(client)
    rank = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "representative"},
    )
    failed_id = start_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": corpus_id, "profile": "missing-profile"},
    )
    failed = wait_for_execution(client, failed_id)
    assert failed["status"] == "failed"

    missing_response = client.get(
        "/api/executions/comparison",
        params={
            "left_execution_id": rank["id"],
            "right_execution_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    failed_response = client.get(
        "/api/executions/comparison",
        params={"left_execution_id": rank["id"], "right_execution_id": failed_id},
    )

    assert missing_response.status_code == 404
    assert "was not found" in missing_response.json()["detail"]
    assert failed_response.status_code == 422
    assert "succeeded executions" in failed_response.json()["detail"]


def test_incompatible_rank_correlation_returns_warning_payload_not_500(
    client: TestClient,
) -> None:
    left_corpus_id = create_corpus_with_articles(client)
    right_corpus_id = create_corpus_with_articles(client)
    left = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": left_corpus_id, "profile": "representative"},
    )
    right = completed_execution(
        client,
        "/api/executions/rank",
        {"corpus_id": right_corpus_id, "profile": "representative"},
    )

    response = client.get(
        "/api/executions/comparison",
        params={"left_execution_id": left["id"], "right_execution_id": right["id"]},
    )

    assert response.status_code == 200
    pair = response.json()["section_pairs"][0]
    assert pair["metrics"]["top_m_overlap"]["overlap_count"] == 0
    assert pair["metrics"]["rank_correlation"] is None

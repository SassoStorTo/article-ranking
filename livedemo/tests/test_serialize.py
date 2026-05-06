import numpy as np

from livedemo.app.serialize import from_jsonable, to_jsonable
from news_ranker.cluster import FactUniverse
from news_ranker.results import (
    ProfileComparison,
    RankDiagnostics,
    RankingEntry,
    RankResult,
    SelectionResult,
)
from news_ranker.score import ScoreVector

RANK_RESULT_SNAPSHOT = {
    "__type__": "rank_result",
    "profile": "representative",
    "entries": [
        {
            "__type__": "ranking_entry",
            "article_id": "article-a",
            "rank": 1,
            "score": 0.9,
            "components": {"centrality": 1.0, "coverage": 1.0},
        },
        {
            "__type__": "ranking_entry",
            "article_id": "article-b",
            "rank": 2,
            "score": 0.4,
            "components": {"centrality": 0.0, "coverage": 1.0},
        },
    ],
    "diagnostics": {
        "__type__": "rank_diagnostics",
        "fact_universe": {
            "__type__": "fact_universe",
            "article_ids": ["article-a", "article-b"],
            "raw_fact_article_ids": ["article-a", "article-b"],
            "raw_fact_ids": ["event-1", "claim-1"],
            "raw_fact_texts": ["event text", "claim text"],
            "canonical_fact_texts": ["event text", "claim text"],
            "cluster_vectors": [[1.0, 0.0], [0.0, 1.0]],
            "cluster_assignments": [0, 1],
            "cluster_members": [[0], [1]],
            "coverage_matrix": [[1, 0], [0, 1]],
        },
        "components": {
            "centrality": {
                "__type__": "score_vector",
                "raw": [0.20000000298023224, 0.10000000149011612],
                "normalized": [1.0, 0.0],
                "defined": True,
            },
            "coverage": {
                "__type__": "score_vector",
                "raw": [1.0, 1.0],
                "normalized": [1.0, 1.0],
                "defined": True,
            },
        },
        "article_embeddings": [[1.0, 0.0], [0.0, 1.0]],
    },
}

SELECTION_RESULT_SNAPSHOT = {
    "__type__": "selection_result",
    "profile": "representative",
    "m": 1,
    "selected": [RANK_RESULT_SNAPSHOT["entries"][0]],
    "ranking": RANK_RESULT_SNAPSHOT,
}


def make_rank_result(profile: str = "representative") -> RankResult:
    fact_universe = FactUniverse(
        article_ids=("article-a", "article-b"),
        raw_fact_article_ids=("article-a", "article-b"),
        raw_fact_ids=("event-1", "claim-1"),
        raw_fact_texts=("event text", "claim text"),
        canonical_fact_texts=("event text", "claim text"),
        cluster_vectors=np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        cluster_assignments=np.asarray([0, 1], dtype=np.int_),
        cluster_members=((0,), (1,)),
        coverage_matrix=np.asarray([[1, 0], [0, 1]], dtype=np.int_),
    )
    components = {
        "centrality": ScoreVector(
            raw=np.asarray([0.2, 0.1], dtype=np.float32),
            normalized=np.asarray([1.0, 0.0], dtype=np.float32),
            defined=True,
        ),
        "coverage": ScoreVector(
            raw=np.asarray([1.0, 1.0], dtype=np.float32),
            normalized=np.asarray([1.0, 1.0], dtype=np.float32),
            defined=True,
        ),
    }
    return RankResult(
        profile=profile,
        entries=(
            RankingEntry(
                article_id="article-a",
                rank=1,
                score=0.9,
                components={"centrality": 1.0, "coverage": 1.0},
            ),
            RankingEntry(
                article_id="article-b",
                rank=2,
                score=0.4,
                components={"centrality": 0.0, "coverage": 1.0},
            ),
        ),
        diagnostics=RankDiagnostics(
            fact_universe=fact_universe,
            components=components,
            article_embeddings=np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        ),
    )


def test_rank_result_round_trip_restores_arrays_and_entries() -> None:
    result = make_rank_result()

    restored = from_jsonable(to_jsonable(result))

    assert isinstance(restored, RankResult)
    assert restored.entries == result.entries
    np.testing.assert_array_equal(
        restored.diagnostics.fact_universe.coverage_matrix,
        result.diagnostics.fact_universe.coverage_matrix,
    )
    np.testing.assert_array_equal(
        restored.diagnostics.components["centrality"].normalized,
        result.diagnostics.components["centrality"].normalized,
    )


def test_rank_result_json_payload_matches_snapshot() -> None:
    result = make_rank_result()

    assert to_jsonable(result) == RANK_RESULT_SNAPSHOT


def test_selection_result_round_trip_restores_nested_ranking() -> None:
    ranking = make_rank_result()
    result = SelectionResult(
        profile="representative",
        m=1,
        selected=(ranking.entries[0],),
        ranking=ranking,
    )

    restored = from_jsonable(to_jsonable(result))

    assert isinstance(restored, SelectionResult)
    assert restored.selected == result.selected
    assert restored.ranking.entries == result.ranking.entries


def test_selection_result_json_payload_matches_snapshot() -> None:
    ranking = make_rank_result()
    result = SelectionResult(
        profile="representative",
        m=1,
        selected=(ranking.entries[0],),
        ranking=ranking,
    )

    assert to_jsonable(result) == SELECTION_RESULT_SNAPSHOT


def test_profile_comparison_round_trip_restores_rankings() -> None:
    comparison = ProfileComparison(
        rankings={
            "representative": make_rank_result("representative"),
            "comprehensive": make_rank_result("comprehensive"),
        }
    )

    restored = from_jsonable(to_jsonable(comparison))

    assert isinstance(restored, ProfileComparison)
    assert set(restored.rankings) == {"representative", "comprehensive"}
    assert restored.rankings["comprehensive"].profile == "comprehensive"

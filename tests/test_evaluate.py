from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from news_ranker.cluster import FactUniverse
from news_ranker.evaluate import (
    anonymized_user_study_bundle,
    cluster_inspection_rows,
    component_score_table,
    rank_correlation,
    top_m_overlap,
)
from news_ranker.pipeline import NewsRanker
from news_ranker.results import (
    ProfileComparison,
    RankDiagnostics,
    RankingEntry,
    RankResult,
    SelectionResult,
)

ARTICLE_DIR = Path(__file__).resolve().parents[1] / "articles" / "trump-shooting"
EXPECTED_COMPONENT_KEYS = {"centrality", "coverage", "density", "entity_coverage"}


class FakeEmbedder:
    def embed(self, texts: list[str]) -> NDArray[np.float32]:
        return np.ones((len(texts), 2), dtype=np.float32)


def test_top_m_overlap_reports_counts_fractions_and_ids() -> None:
    left = _rank_result("left", ["a", "b", "c", "d"])
    right = _rank_result("right", ["b", "c", "e", "a"])

    result = top_m_overlap(left, right, 3)

    assert result.overlap_count == 2
    assert result.left_top_count == 3
    assert result.right_top_count == 3
    assert result.jaccard == pytest.approx(0.5)
    assert result.left_overlap_fraction == pytest.approx(2 / 3)
    assert result.right_overlap_fraction == pytest.approx(2 / 3)
    assert result.overlap_article_ids == ("b", "c")


def test_rank_correlation_kendall_identical_and_reversed_rankings() -> None:
    left = _rank_result("left", ["a", "b", "c", "d"])
    identical = _rank_result("same", ["a", "b", "c", "d"])
    reversed_ = _rank_result("reversed", ["d", "c", "b", "a"])

    assert rank_correlation(left, identical).coefficient == pytest.approx(1.0)
    result = rank_correlation(left, reversed_, method="kendall")

    assert result.method == "kendall"
    assert result.coefficient == pytest.approx(-1.0)
    assert result.common_count == 4
    assert result.common_article_ids == ("a", "b", "c", "d")


def test_rank_correlation_spearman_identical_and_reversed_rankings() -> None:
    left = _rank_result("left", ["a", "b", "c", "d"])
    identical = _rank_result("same", ["a", "b", "c", "d"])
    reversed_ = _rank_result("reversed", ["d", "c", "b", "a"])

    assert rank_correlation(left, identical, method="spearman").coefficient == (
        pytest.approx(1.0)
    )
    assert rank_correlation(left, reversed_, method="spearman").coefficient == (
        pytest.approx(-1.0)
    )


def test_rank_correlation_aligns_common_ids_and_reports_only_diagnostics() -> None:
    left = _rank_result("left", ["a", "b", "c", "left-only"])
    right = _rank_result("right", ["right-only", "c", "a", "b"])

    result = rank_correlation(left, right, method="kendall")

    assert result.common_count == 3
    assert result.common_article_ids == ("a", "b", "c")
    assert result.left_only_article_ids == ("left-only",)
    assert result.right_only_article_ids == ("right-only",)
    assert result.coefficient == pytest.approx(-1 / 3)


def test_component_score_table_sorts_by_profile_input_order_then_rank() -> None:
    first = _rank_result(
        "first",
        ["b", "a"],
        {
            "b": {"coverage": 0.7},
            "a": {"coverage": 0.2, "density": 0.4},
        },
    )
    second = _rank_result(
        "second",
        ["c"],
        {"c": {"entity_coverage": 1.0}},
    )

    rows = component_score_table([first, second])

    assert [row["profile"] for row in rows] == ["first", "first", "second"]
    assert [row["article_id"] for row in rows] == ["b", "a", "c"]
    assert [row["rank"] for row in rows] == [1, 2, 1]
    assert set(rows[0]) == {
        "profile",
        "article_id",
        "rank",
        "score",
        "coverage",
        "density",
        "entity_coverage",
    }
    assert rows[0]["coverage"] == pytest.approx(0.7)
    assert rows[0]["density"] is None
    assert rows[0]["entity_coverage"] is None
    assert rows[1]["density"] == pytest.approx(0.4)
    assert rows[2]["coverage"] is None
    assert rows[2]["entity_coverage"] == pytest.approx(1.0)


def test_component_score_table_accepts_single_result_and_profile_comparison() -> None:
    first = _rank_result("first", ["a"], {"a": {"coverage": 1.0}})
    second = _rank_result("second", ["b"], {"b": {"density": 0.5}})

    assert component_score_table(first) == [
        {
            "profile": "first",
            "article_id": "a",
            "rank": 1,
            "score": 0.0,
            "coverage": 1.0,
        }
    ]

    rows = component_score_table(
        ProfileComparison(rankings={"first": first, "second": second})
    )

    assert [row["profile"] for row in rows] == ["first", "second"]
    assert rows[0]["coverage"] == pytest.approx(1.0)
    assert rows[0]["density"] is None
    assert rows[1]["coverage"] is None
    assert rows[1]["density"] == pytest.approx(0.5)


def test_component_score_table_preserves_fixture_backed_scores_and_components() -> None:
    result = NewsRanker(FakeEmbedder()).rank(ARTICLE_DIR)

    rows = component_score_table(result)

    assert len(rows) == len(result.entries)
    assert [row["rank"] for row in rows] == [entry.rank for entry in result.entries]
    for row in rows:
        assert row["profile"] == "representative"
        assert isinstance(row["article_id"], str)
        assert np.isfinite(row["score"])
        assert EXPECTED_COMPONENT_KEYS < set(row)
        assert all(np.isfinite(row[name]) for name in EXPECTED_COMPONENT_KEYS)


def test_cluster_inspection_rows_report_deterministic_cluster_fields() -> None:
    fact_universe = FactUniverse(
        article_ids=("a", "b", "c"),
        raw_fact_article_ids=("a", "a", "b", "c"),
        raw_fact_ids=("a-1", "a-2", "b-1", "c-1"),
        raw_fact_texts=("shared from a", "rare from a", "shared from b", "c fact"),
        canonical_fact_texts=("shared from a", "rare from a", "c fact"),
        cluster_vectors=np.ones((3, 2), dtype=np.float32),
        cluster_assignments=np.asarray([0, 1, 0, 2], dtype=np.int_),
        cluster_members=((0, 2), (1,), (3,)),
        coverage_matrix=np.asarray(
            [
                [2, 1, 0],
                [1, 0, 0],
                [0, 0, 1],
            ],
            dtype=np.int_,
        ),
    )
    result = _rank_result("profile", ["a", "b", "c"], fact_universe=fact_universe)

    rows = cluster_inspection_rows(result, rare_threshold=1)

    assert rows == [
        {
            "cluster_index": 0,
            "canonical_fact_text": "shared from a",
            "support_article_ids": ("a", "b"),
            "support_count": 2,
            "member_raw_indices": (0, 2),
            "member_fact_ids": ("a-1", "b-1"),
            "member_texts": ("shared from a", "shared from b"),
            "is_rare": False,
        },
        {
            "cluster_index": 1,
            "canonical_fact_text": "rare from a",
            "support_article_ids": ("a",),
            "support_count": 1,
            "member_raw_indices": (1,),
            "member_fact_ids": ("a-2",),
            "member_texts": ("rare from a",),
            "is_rare": True,
        },
        {
            "cluster_index": 2,
            "canonical_fact_text": "c fact",
            "support_article_ids": ("c",),
            "support_count": 1,
            "member_raw_indices": (3,),
            "member_fact_ids": ("c-1",),
            "member_texts": ("c fact",),
            "is_rare": True,
        },
    ]


def test_cluster_inspection_rows_return_empty_for_empty_fact_universe() -> None:
    result = _rank_result("profile", ["a", "b"])

    assert cluster_inspection_rows(result) == []


@pytest.mark.parametrize("rare_threshold", [0, -1])
def test_cluster_inspection_rows_reject_invalid_rare_threshold(
    rare_threshold: int,
) -> None:
    result = _rank_result("profile", ["a"])

    with pytest.raises(ValueError, match="rare_threshold"):
        cluster_inspection_rows(result, rare_threshold=rare_threshold)


@pytest.mark.parametrize("rare_threshold", [1.0, True])
def test_cluster_inspection_rows_reject_non_integer_rare_threshold(
    rare_threshold: object,
) -> None:
    result = _rank_result("profile", ["a"])

    with pytest.raises(TypeError, match="integer"):
        cluster_inspection_rows(result, rare_threshold=rare_threshold)  # type: ignore[arg-type]


def test_anonymized_user_study_bundle_uses_ranking_order_labels() -> None:
    ranking = _rank_result(
        "profile",
        ["source-a", "source-b", "source-c"],
        {
            "source-a": {"coverage": 1.0},
            "source-b": {"coverage": 0.5},
            "source-c": {"density": 0.25},
        },
    )
    selection = SelectionResult(
        profile="profile",
        m=2,
        selected=(ranking.entries[2], ranking.entries[0]),
        ranking=ranking,
    )

    bundle = anonymized_user_study_bundle(
        selection,
        {
            "source-a": {"title": "Alpha", "snippet": "Alpha summary"},
            "source-c": {"summary": "Charlie summary"},
        },
    )

    assert bundle == {
        "profile": "profile",
        "m": 2,
        "selected_article_labels": ("article_3", "article_1"),
        "article_materials": {
            "article_3": {"summary": "Charlie summary"},
            "article_1": {"title": "Alpha", "snippet": "Alpha summary"},
        },
    }
    assert "source-a" not in repr(bundle)
    assert "source-c" not in repr(bundle)


def test_anonymized_user_study_bundle_include_scores_controls_score_payload() -> None:
    ranking = _rank_result(
        "profile",
        ["a", "b"],
        {"a": {"coverage": 1.0}, "b": {"density": 0.25}},
    )
    selection = SelectionResult(
        profile="profile",
        m=2,
        selected=ranking.entries,
        ranking=ranking,
    )
    article_materials = {
        "a": {"title": "Alpha"},
        "b": {"snippet": "Bravo"},
    }

    without_scores = anonymized_user_study_bundle(selection, article_materials)
    with_scores = anonymized_user_study_bundle(
        selection, article_materials, include_scores=True
    )

    assert "scores" not in without_scores
    assert set(with_scores["article_materials"]) == {"article_1", "article_2"}
    assert with_scores["scores"] == (
        {
            "label": "article_1",
            "rank": 1,
            "score": 1.0,
            "components": {"coverage": 1.0},
        },
        {
            "label": "article_2",
            "rank": 2,
            "score": 0.0,
            "components": {"density": 0.25},
        },
    )


def test_anonymized_user_study_bundle_rejects_missing_material() -> None:
    ranking = _rank_result("profile", ["a", "b"])
    selection = SelectionResult(
        profile="profile",
        m=2,
        selected=ranking.entries,
        ranking=ranking,
    )

    with pytest.raises(ValueError, match="missing article material"):
        anonymized_user_study_bundle(selection, {"a": {"title": "Alpha"}})


def test_anonymized_user_study_bundle_rejects_unexpected_material_fields() -> None:
    ranking = _rank_result("profile", ["a"])
    selection = SelectionResult(
        profile="profile",
        m=1,
        selected=ranking.entries,
        ranking=ranking,
    )

    with pytest.raises(ValueError, match="unexpected material fields"):
        anonymized_user_study_bundle(
            selection,
            {"a": {"title": "Alpha", "source": "Publisher"}},
        )


@pytest.mark.parametrize("m", [0, 4])
def test_top_m_overlap_rejects_out_of_range_m(m: int) -> None:
    left = _rank_result("left", ["a", "b", "c"])
    right = _rank_result("right", ["a", "b", "c"])

    with pytest.raises(ValueError, match="m"):
        top_m_overlap(left, right, m)


def test_top_m_overlap_rejects_non_integer_m() -> None:
    left = _rank_result("left", ["a"])
    right = _rank_result("right", ["a"])

    with pytest.raises(TypeError, match="integer"):
        top_m_overlap(left, right, 1.0)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="integer"):
        top_m_overlap(left, right, True)  # type: ignore[arg-type]


def test_rank_correlation_rejects_unknown_method() -> None:
    left = _rank_result("left", ["a", "b"])
    right = _rank_result("right", ["a", "b"])

    with pytest.raises(ValueError, match="method"):
        rank_correlation(left, right, method="pearson")  # type: ignore[arg-type]


def test_rank_correlation_rejects_fewer_than_two_common_ids() -> None:
    left = _rank_result("left", ["a", "b"])
    right = _rank_result("right", ["a", "c"])

    with pytest.raises(ValueError, match="at least two common"):
        rank_correlation(left, right)


def test_helpers_reject_duplicate_article_ids() -> None:
    left = _rank_result("left", ["a", "a", "b"])
    right = _rank_result("right", ["a", "b", "c"])

    with pytest.raises(ValueError, match="duplicate article_id"):
        top_m_overlap(left, right, 2)
    with pytest.raises(ValueError, match="duplicate article_id"):
        rank_correlation(left, right)


def _rank_result(
    profile: str,
    article_ids: list[str],
    components_by_article_id: dict[str, dict[str, float]] | None = None,
    fact_universe: FactUniverse | None = None,
) -> RankResult:
    entries = tuple(
        RankingEntry(
            article_id=article_id,
            rank=rank,
            score=float(len(article_ids) - rank),
            components=(components_by_article_id or {}).get(article_id, {}),
        )
        for rank, article_id in enumerate(article_ids, start=1)
    )
    if fact_universe is None:
        fact_universe = FactUniverse(
            article_ids=tuple(article_ids),
            raw_fact_article_ids=(),
            raw_fact_ids=(),
            raw_fact_texts=(),
            canonical_fact_texts=(),
            cluster_vectors=np.empty((0, 0), dtype=np.float32),
            cluster_assignments=np.empty((0,), dtype=np.int_),
            cluster_members=(),
            coverage_matrix=np.zeros((len(article_ids), 0), dtype=np.int_),
        )
    return RankResult(
        profile=profile,
        entries=entries,
        diagnostics=RankDiagnostics(
            fact_universe=fact_universe,
            components={},
            article_embeddings=np.empty((len(article_ids), 0), dtype=np.float32),
        ),
    )

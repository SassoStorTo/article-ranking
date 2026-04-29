import numpy as np
import pytest

from news_ranker.cluster import FactUniverse
from news_ranker.evaluate import rank_correlation, top_m_overlap
from news_ranker.pipeline import RankDiagnostics, RankingEntry, RankResult


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


def _rank_result(profile: str, article_ids: list[str]) -> RankResult:
    entries = tuple(
        RankingEntry(
            article_id=article_id,
            rank=rank,
            score=float(len(article_ids) - rank),
            components={},
        )
        for rank, article_id in enumerate(article_ids, start=1)
    )
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

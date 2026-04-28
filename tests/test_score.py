from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from news_ranker.schemas import Claim, Entities, StructuredArticle
from news_ranker.score import centrality, coverage, density, minmax_normalize


def test_minmax_normalize_scales_values_to_unit_interval() -> None:
    scores = minmax_normalize(np.asarray([2.0, 4.0, 6.0], dtype=np.float32))

    np.testing.assert_allclose(scores.raw, [2.0, 4.0, 6.0])
    np.testing.assert_allclose(scores.normalized, [0.0, 0.5, 1.0])
    assert scores.defined is True


def test_tied_defined_components_normalize_to_ones() -> None:
    scores = minmax_normalize(np.asarray([3.0, 3.0, 3.0], dtype=np.float32))

    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 1.0])
    assert scores.defined is True


def test_undefined_components_normalize_to_zeros() -> None:
    scores = minmax_normalize(
        np.asarray([3.0, 3.0, 3.0], dtype=np.float32), defined=False
    )

    np.testing.assert_allclose(scores.normalized, [0.0, 0.0, 0.0])
    assert scores.defined is False


def test_central_article_receives_highest_normalized_centrality() -> None:
    article_embeddings = np.asarray(
        [
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    scores = centrality(article_embeddings)

    assert scores.defined is True
    assert int(np.argmax(scores.normalized)) == 1
    assert scores.normalized[1] == pytest.approx(1.0)
    assert scores.raw[1] > scores.raw[0]
    assert scores.raw[1] > scores.raw[2]


def test_identical_embeddings_tie_at_one() -> None:
    scores = centrality(np.ones((3, 2), dtype=np.float32))

    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 1.0])
    assert scores.defined is True


def test_full_fact_coverage_raw_score_equals_one() -> None:
    scores = coverage(np.ones((3, 4), dtype=np.int_))

    np.testing.assert_allclose(scores.raw, [1.0, 1.0, 1.0])
    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 1.0])
    assert scores.defined is True


def test_consensus_weights_reward_high_support_facts() -> None:
    coverage_matrix = np.asarray(
        [
            [1, 0],
            [1, 0],
            [0, 1],
        ],
        dtype=np.int_,
    )

    scores = coverage(coverage_matrix, mode="consensus")

    assert scores.raw[0] == pytest.approx(2.0 / 3.0)
    assert scores.raw[1] == pytest.approx(2.0 / 3.0)
    assert scores.raw[2] == pytest.approx(1.0 / 3.0)
    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 0.0])


def test_rarity_weights_remain_positive_when_all_articles_cover_fact() -> None:
    scores = coverage(np.ones((3, 1), dtype=np.int_), mode="rarity")

    np.testing.assert_allclose(scores.raw, [1.0, 1.0, 1.0])
    np.testing.assert_allclose(scores.normalized, [1.0, 1.0, 1.0])
    assert scores.defined is True


def test_empty_fact_universe_returns_undefined_coverage_zeros() -> None:
    scores = coverage(np.zeros((3, 0), dtype=np.int_))

    np.testing.assert_allclose(scores.raw, [0.0, 0.0, 0.0])
    np.testing.assert_allclose(scores.normalized, [0.0, 0.0, 0.0])
    assert scores.defined is False


def test_density_computes_unique_clusters_per_extracted_entry() -> None:
    articles = [_article("a", 2), _article("b", 4), _article("c", 0)]
    coverage_matrix = np.asarray(
        [
            [1, 1, 0],
            [1, 1, 1],
            [0, 0, 0],
        ],
        dtype=np.int_,
    )

    scores = density(articles, coverage_matrix)

    np.testing.assert_allclose(scores.raw, [1.0, 0.75, 0.0])
    np.testing.assert_allclose(scores.normalized, [1.0, 0.75, 0.0])
    assert scores.defined is True


def test_repeated_coverage_values_do_not_inflate_density() -> None:
    scores = density([_article("a", 2)], np.asarray([[2, 0, 3]], dtype=np.int_))

    np.testing.assert_allclose(scores.raw, [1.0])
    np.testing.assert_allclose(scores.normalized, [1.0])
    assert scores.defined is True


def test_all_empty_extractions_return_undefined_density_zeros() -> None:
    scores = density(
        [_article("a", 0), _article("b", 0)], np.zeros((2, 0), dtype=np.int_)
    )

    np.testing.assert_allclose(scores.raw, [0.0, 0.0])
    np.testing.assert_allclose(scores.normalized, [0.0, 0.0])
    assert scores.defined is False


def test_density_row_count_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="row count"):
        density([_article("a", 1), _article("b", 1)], np.ones((1, 1), dtype=np.int_))


@pytest.mark.parametrize(
    ("article_embeddings", "error_type", "match"),
    [
        (np.ones((2,), dtype=np.float32), ValueError, "2-D"),
        (np.array([[np.nan, 1.0]], dtype=np.float32), ValueError, "finite"),
        (np.array([[object()]], dtype=object), TypeError, "numeric"),
    ],
)
def test_invalid_centrality_embeddings_raise(
    article_embeddings: NDArray[Any], error_type: type[Exception], match: str
) -> None:
    with pytest.raises(error_type, match=match):
        centrality(article_embeddings)


def _article(article_id: str, entry_count: int) -> StructuredArticle:
    return StructuredArticle(
        article_id=article_id,
        headline_neutral="Neutral headline",
        topic="test",
        entities=Entities(people=[], organizations=[], locations=[]),
        events=[],
        claims=[
            Claim(
                id=f"c{index}",
                statement=f"claim {index}",
                type="fact",
                attributed_to="fixture",
            )
            for index in range(entry_count)
        ],
        context=[],
    )

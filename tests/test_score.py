from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from news_ranker.score import centrality, minmax_normalize


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
